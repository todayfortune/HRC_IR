from __future__ import annotations

import json
from copy import deepcopy
from datetime import date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT / "data"
STOCKS_FILE = ROOT / "config" / "stocks.json"
MARKET_LATEST_FILE = DATA_DIR / "market_latest.json"
SEOUL = ZoneInfo("Asia/Seoul")


class ReportService:
    def __init__(self) -> None:
        DATA_DIR.mkdir(exist_ok=True)

    @staticmethod
    def _valid_date(value: str | None) -> str:
        if not value:
            return datetime.now(SEOUL).date().isoformat()
        return date.fromisoformat(value).isoformat()

    def path_for(self, report_date: str) -> Path:
        return DATA_DIR / f"{self._valid_date(report_date)}.json"

    def blank(self, report_date: str | None = None) -> dict[str, Any]:
        day = self._valid_date(report_date)
        stocks = json.loads(STOCKS_FILE.read_text(encoding="utf-8"))["stocks"]
        return {
            "date": day,
            "status": None,
            "updatedAt": None,
            "updated_at": None,
            "market_status": "업데이트 전",
            "telegram_status": "업데이트 전",
            "indicators": [
                {"group":"국내","name":"KOSPI"}, {"group":"국내","name":"KOSDAQ"},
                {"group":"미국","name":"S&P500"}, {"group":"미국","name":"NASDAQ"},
                {"group":"환율","name":"USD"}, {"group":"환율","name":"EUR"}
            ],
            "stocks": stocks,
            "comments": {"미국증시":"", "국내증시":"", "방산":"", "현대로템":"", "반도체":"", "USD/KRW":""},
            "telegram": {key: [] for key in ["현대로템","방산","반도체","미국증시","환율"]},
            "telegram_feed": {"closing": [], "stock_news": []}
        }

    def load(self, report_date: str | None = None) -> dict[str, Any]:
        report = self.blank(report_date)
        path = self.path_for(report["date"])
        if not path.exists():
            if MARKET_LATEST_FILE.exists():
                latest = json.loads(MARKET_LATEST_FILE.read_text(encoding="utf-8"))
                if latest.get("date") == report["date"]:
                    for key in ("status","updatedAt","updated_at","market_status","indicators","stocks"):
                        if key in latest:
                            report[key] = latest[key]
            return report
        stored = json.loads(path.read_text(encoding="utf-8"))
        for key in ("status","updatedAt","updated_at","market_status","telegram_status","indicators","stocks","comments","telegram","telegram_feed"):
            if key in stored:
                report[key] = stored[key]
        return report

    def save(self, payload: dict[str, Any]) -> dict[str, Any]:
        report_date = self._valid_date(str(payload.get("date", "")))
        current = self.load(report_date)
        allowed = {"status","updatedAt","updated_at","market_status","telegram_status","indicators","stocks","comments","telegram","telegram_feed"}
        for key in allowed:
            if key in payload:
                current[key] = deepcopy(payload[key])
        current["date"] = report_date
        current["saved_at"] = datetime.now(SEOUL).isoformat(timespec="seconds")
        target = self.path_for(report_date)
        temporary = target.with_suffix(".tmp")
        temporary.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(target)
        return current

    def save_market_snapshot(self, report: dict[str, Any]) -> None:
        snapshot = {key: deepcopy(report[key]) for key in ("date","status","updatedAt","updated_at","market_status","indicators","stocks")}
        temporary = MARKET_LATEST_FILE.with_suffix(".tmp")
        temporary.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(MARKET_LATEST_FILE)
