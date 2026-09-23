from __future__ import annotations
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.services.market import MarketService
from app.services.report import ReportService

def main() -> None:
    reports = ReportService()
    report = reports.load(datetime.now(ZoneInfo("Asia/Seoul")).date().isoformat())
    updated = MarketService().update(report)
    reports.save(updated)
    reports.save_market_snapshot(updated)
    successful = sum(1 for row in updated["stocks"] if row.get("current") is not None)
    index_successful = sum(1 for row in updated["indicators"] if row.get("current") is not None)
    print(f"시장 데이터 저장 완료: 주요지표 {index_successful}/6, 국내종목 {successful}/{len(updated['stocks'])}")
    print(updated["market_status"])

if __name__ == "__main__":
    main()
