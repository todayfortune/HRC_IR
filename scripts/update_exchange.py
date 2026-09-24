from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.market.hana_exchange import fetch_hana_usd_rate, save_exchange_snapshot


def main() -> None:
    today = datetime.now(ZoneInfo("Asia/Seoul")).date()
    result = fetch_hana_usd_rate(today)
    save_exchange_snapshot(result, ROOT / "data" / "exchange_latest.json")
    print(
        "하나은행 USD 매매기준율 저장 완료: "
        f"{result['referenceDate']} {result['announcementTime']} "
        f"{result['announcementNumber']}회차"
    )


if __name__ == "__main__":
    main()
