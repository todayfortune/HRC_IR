from __future__ import annotations

import sys
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.market.hana_exchange import build_exchange_snapshot, save_exchange_snapshot


def main() -> None:
    today = datetime.now(ZoneInfo("Asia/Seoul")).date()
    target = ROOT / "data" / "exchange_latest.json"
    existing = json.loads(target.read_text(encoding="utf-8")) if target.exists() else {}
    result = build_exchange_snapshot(today, existing)
    if result != existing:
        save_exchange_snapshot(result, target)
    print("하나은행 USD/EUR 15:30 이후 최초 고시 확정 완료")


if __name__ == "__main__":
    main()
