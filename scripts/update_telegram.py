from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.services.report import ReportService
from app.services.telegram import TelegramService

def main() -> None:
    reports = ReportService()
    updated = TelegramService().update(reports.load())
    reports.save(updated)
    count = sum(len(items) for items in updated["telegram"].values())
    print(f"Telegram 원문 {count}건 저장 완료")

if __name__ == "__main__":
    main()
