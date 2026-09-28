from __future__ import annotations

import asyncio
import json
import os
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo

from telethon import TelegramClient
from telethon.sessions import StringSession

from integrations.env import load_env, require_env


ROOT = Path(__file__).resolve().parents[3]
SEOUL = ZoneInfo("Asia/Seoul")


def session_value(value: str):
    if os.getenv("GITHUB_ACTIONS") == "true":
        try:
            return StringSession(value)
        except Exception as exc:
            raise RuntimeError("GitHub Actions에서는 유효한 Telegram StringSession이 필요합니다.") from exc
    if len(value) > 100 and not any(char in value for char in ("/", "\\")):
        return StringSession(value)
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return str(path)


def normalize(value: str) -> str:
    return re.sub(r"\s+", "", value).casefold()


def excerpt(value: str, limit: int) -> str:
    text = value.strip()
    if len(text) <= limit:
        return text
    candidate = text[:limit]
    floor = max(int(limit * 0.65), 1)
    breaks = [candidate.rfind(mark) for mark in ("\n", ". ", "다.", "요.", "!", "?")]
    cut = max(breaks)
    if cut < floor:
        cut = limit
    elif candidate[cut:cut + 2] in ("다.", "요."):
        cut += 2
    else:
        cut += 1
    return text[:cut].rstrip() + "…"


def classify_messages(
    messages: Iterable[dict[str, Any]], stock_names: list[str], closing_keywords: list[str],
    target_date: str, excerpt_length: int,
) -> dict[str, list[dict[str, Any]]]:
    seen: set[tuple[str, int]] = set()
    closing: list[dict[str, Any]] = []
    stock_news: list[dict[str, Any]] = []
    normalized_closing = [normalize(word) for word in closing_keywords]
    for raw in messages:
        key = (str(raw["channel"]), int(raw["message_id"]))
        if key in seen or str(raw.get("date", ""))[:10] != target_date:
            continue
        seen.add(key)
        text = str(raw.get("text", "")).strip()
        if not text:
            continue
        related = [name for name in stock_names if name in text]
        item = {
            "channel": key[0], "message_id": key[1], "source": raw["source"],
            "date": raw["date"], "excerpt": excerpt(text, excerpt_length),
            "link": raw.get("link"), "stocks": related,
        }
        if any(word in normalize(text) for word in normalized_closing):
            closing.append(item)
        if related:
            stock_news.append(item)
    ordering = lambda item: item.get("date") or ""
    closing.sort(key=ordering, reverse=True)
    stock_news.sort(key=ordering, reverse=True)
    return {"closing": closing, "stock_news": stock_news}


class TelegramService:
    def __init__(self) -> None:
        load_env()
        api_id, api_hash, session = require_env("TELEGRAM_API_ID", "TELEGRAM_API_HASH", "TELEGRAM_SESSION")
        self.api_id, self.api_hash, self.session = int(api_id), api_hash, session_value(session)
        config = json.loads((ROOT / "config" / "telegram_channels.json").read_text(encoding="utf-8"))
        self.channels = config["channels"]
        self.message_limit = int(config.get("message_limit_per_channel", 100))
        self.excerpt_length = int(config.get("excerpt_length", 700))
        self.closing_keywords = list(config.get("closing_keywords", []))

    async def _fetch(self) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []
        client = TelegramClient(self.session, self.api_id, self.api_hash)
        await client.connect()
        try:
            if not await client.is_user_authorized():
                raise RuntimeError("Telegram 세션 미인증: scripts/create_telegram_session.py를 먼저 실행하세요.")
            for channel in self.channels:
                username = str(channel["username"]).lstrip("@")
                entity = await client.get_entity(username)
                async for message in client.iter_messages(entity, limit=self.message_limit):
                    text = (message.message or "").strip()
                    if not text or not message.date:
                        continue
                    timestamp = message.date.astimezone(SEOUL)
                    messages.append({
                        "channel": username, "message_id": message.id, "source": channel["source"],
                        "date": timestamp.isoformat(timespec="minutes"), "text": text,
                        "link": f"https://t.me/{username}/{message.id}",
                    })
            return messages
        finally:
            await client.disconnect()

    def update(self, report: dict[str, Any]) -> dict[str, Any]:
        target_date = str(report.get("date") or date.today().isoformat())
        stock_names = [str(item["name"]) for item in report.get("stocks", [])]
        messages = asyncio.run(self._fetch())
        for channel in self.channels:
            rows = [m for m in messages if m["channel"] == channel["username"].lstrip("@")]
            latest = max((m["date"] for m in rows), default="none")
            print(f"Telegram channel={channel['username']} fetched={len(rows)} latest={latest}")
        report["telegram_feed"] = classify_messages(
            messages, stock_names, self.closing_keywords,
            target_date, self.excerpt_length,
        )
        keywords = json.loads((ROOT / "config" / "news_keywords.json").read_text(encoding="utf-8"))
        report["telegram"] = keyword_references(messages, keywords, target_date)
        count = sum(str(m.get("date", ""))[:10] == target_date for m in messages)
        report["telegram_status"] = f"Telegram 확인 {datetime.now(SEOUL).strftime('%Y-%m-%d %H:%M')} KST · 당일 원문 {count}건"
        print(f"Telegram fetched={len(messages)} target_date={target_date} today={count} closing={len(report['telegram_feed']['closing'])} stocks={len(report['telegram_feed']['stock_news'])}")
        return report


def keyword_references(messages, keywords, target_date):
    result = {}
    for category, words in keywords.items():
        seen = set()
        items = []
        for message in sorted(messages, key=lambda m: m.get("date", ""), reverse=True):
            key = (message["channel"], message["message_id"])
            if key in seen or message["date"][:10] != target_date:
                continue
            seen.add(key)
            if any(normalize(word) in normalize(message["text"]) for word in words):
                items.append({"date": message["date"], "channel": message["source"], "text": excerpt(message["text"], 200), "link": message.get("link")})
        result[category] = items[:3]
    return result
