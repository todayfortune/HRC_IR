from __future__ import annotations

import time
from copy import deepcopy
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from integrations.env import load_env, require_env
from integrations.kis import KisReadOnlyClient


SEOUL = ZoneInfo("Asia/Seoul")


def number(value: Any, default: int | float | None = None):
    if value in (None, ""):
        return default
    try:
        return float(value) if "." in str(value) else int(value)
    except (TypeError, ValueError):
        return default


class MarketService:
    """Read-only KIS market-data collector. No trading endpoints exist here."""

    def __init__(self) -> None:
        load_env()
        app_key, app_secret = require_env("KIS_APP_KEY", "KIS_APP_SECRET")
        self.client = KisReadOnlyClient(app_key, app_secret, timeout=15)

    def update(self, report: dict[str, Any]) -> dict[str, Any]:
        # Authenticate once for this process. The token remains in memory only.
        self.client.authenticate()
        indicators: list[dict[str, Any]] = []
        errors: list[str] = []
        for group, name, code in (("국내","KOSPI","0001"), ("국내","KOSDAQ","1001")):
            try:
                raw = self.client.get_domestic_index(code)
                current = number(raw.get("bstp_nmix_prpr"))
                if current in (None, 0):
                    raise RuntimeError("KIS가 유효한 현재값을 반환하지 않았습니다.")
                change = number(raw.get("bstp_nmix_prdy_vrss"), 0)
                indicators.append({
                    "group":group, "name":name, "previous": current - change if current is not None else None,
                    "current":current, "market_cap":number(raw.get("bstp_nmix_avls")), "change":change,
                    "change_rate":number(raw.get("bstp_nmix_prdy_ctrt")), "volume":number(raw.get("acml_vol")),
                    "foreign":None, "institution":None, "other":None
                })
            except Exception:
                errors.append(name)

        today = datetime.now(SEOUL).date()
        start, end = (today - timedelta(days=14)).strftime("%Y%m%d"), today.strftime("%Y%m%d")
        global_targets = (("미국","S&P500","N","SPX"),("미국","NASDAQ","N","COMP"),("환율","USD","X","FX@KRW"))
        for group, name, market_code, item_code in global_targets:
            try:
                raw = self.client.get_global_chart(market_code, item_code, start, end)
                current = number(raw.get("ovrs_nmix_prpr"))
                if current in (None, 0):
                    raise RuntimeError("KIS가 유효한 현재값을 반환하지 않았습니다.")
                previous_value = number(raw.get("ovrs_nmix_prdy_clpr"))
                change = number(raw.get("ovrs_nmix_prdy_vrss"))
                indicators.append({"group":group,"name":name,"previous":previous_value,"current":current,"market_cap":None,
                    "change":change,"change_rate":number(raw.get("prdy_ctrt")),"volume":number(raw.get("acml_vol")),
                    "foreign":None,"institution":None,"other":None})
            except Exception as exc:
                errors.append(f"{name} ({exc})")
        indicators.append({"group":"환율","name":"EUR"})

        stocks: list[dict[str, Any]] = []
        for configured in report["stocks"]:
            row = {key: configured.get(key) for key in ("sector","name","code","highlight")}
            try:
                raw = self.client.get_domestic_quote_raw(row["code"])
                current = number(raw.get("stck_prpr"))
                if current in (None, 0):
                    raise RuntimeError("KIS가 유효한 현재값을 반환하지 않았습니다.")
                change = number(raw.get("prdy_vrss"), 0)
                investor = self.client.get_domestic_investor(row["code"])
                foreign = number(investor.get("frgn_ntby_qty"), 0)
                institution = number(investor.get("orgn_ntby_qty"), 0)
                volume = number(raw.get("acml_vol"), 0)
                row.update({
                    "previous": current - change if current is not None else None, "current":current,
                    "market_cap": number(raw.get("hts_avls")), "change":change,
                    "change_rate":number(raw.get("prdy_ctrt")), "volume":volume,
                    "foreign":foreign, "institution":institution,
                    "other":volume - foreign - institution if volume is not None else None
                })
            except Exception:
                errors.append(row["name"])
            stocks.append(row)
            time.sleep(0.12)

        if errors:
            raise RuntimeError(f"KIS 데이터 갱신 실패: {', '.join(errors)}")

        updated = deepcopy(report)
        completed_at = datetime.now(SEOUL).isoformat(timespec="seconds")
        updated["indicators"] = indicators
        updated["stocks"] = stocks
        updated["status"] = "success"
        updated["updatedAt"] = completed_at
        updated["updated_at"] = completed_at
        updated["market_status"] = "KIS 업데이트 완료"
        return updated
