from __future__ import annotations
import argparse
import asyncio
import os
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from integrations.env import load_env, require_env
from integrations.telegram import recent_channel_messages

async def run(channel: str) -> None:
    load_env()
    api_id, api_hash, session = require_env("TELEGRAM_API_ID", "TELEGRAM_API_HASH", "TELEGRAM_SESSION")
    print("Telegram 연결 및 세션 확인 중... (인증정보는 출력하지 않음)")
    messages = await recent_channel_messages(int(api_id), api_hash, session, channel, limit=20)
    print(f"최근 메시지 {len(messages)}개:")
    for message in messages:
        text = " ".join(message.text.split())[:160] or "(텍스트 없음)"
        date = message.date.isoformat(timespec="seconds") if message.date else "-"
        print(f"- [{date}] #{message.id} {text}")

def main() -> None:
    load_env()
    parser = argparse.ArgumentParser(description="Telegram 채널 최근 20개 메시지 조회")
    parser.add_argument("channel", nargs="?", default=os.getenv("TELEGRAM_CHANNEL"), help="@채널명 또는 공개 채널 URL")
    args = parser.parse_args()
    if not args.channel:
        parser.error("채널을 지정하세요: python scripts/test_telegram.py @channel_name")
    asyncio.run(run(args.channel))

if __name__ == "__main__":
    main()
