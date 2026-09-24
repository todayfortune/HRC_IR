from __future__ import annotations
from copy import deepcopy
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.services.report import ReportService
from app.services.telegram import TelegramService

def main() -> None:
    reports = ReportService()
    current = reports.load()
    previous_feed = deepcopy(current.get("telegram_feed"))
    updated = TelegramService().update(current)
    if updated.get("telegram_feed") == previous_feed:
        print("새 Telegram 메시지가 없어 저장하지 않았습니다.")
        return
    reports.save(updated)
    count = sum(len(items) for items in updated["telegram_feed"].values())
    print(f"Telegram 원문 {count}건 저장 완료")

if __name__ == "__main__":
    main()
