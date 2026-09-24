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


def iso_date(value: Any) -> str | None:
    text = str(value or "")
    if len(text) == 8 and text.isdigit():
        return f"{text[:4]}-{text[4:6]}-{text[6:]}"
    return None


def million_krw_to_eok(value: Any) -> float | None:
    """KIS *_tr_pbmn and index acml_tr_pbmn fields are in KRW millions."""
    raw = number(value)
    return round(raw / 100, 2) if raw is not None else None


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
        today = datetime.now(SEOUL).date()
        query_date = today.strftime("%Y%m%d")
        for group, name, code, market_code in (("국내","KOSPI","0001","KSP"), ("국내","KOSDAQ","1001","KSQ")):
            try:
                raw = self.client.get_domestic_index(code)
                current = number(raw.get("bstp_nmix_prpr"))
                if current in (None, 0):
                    raise RuntimeError("KIS가 유효한 현재값을 반환하지 않았습니다.")
                change = number(raw.get("bstp_nmix_prdy_vrss"), 0)
                investor = self.client.get_market_investor_daily(code, market_code, query_date)
                trading_date = iso_date(investor.get("stck_bsop_date"))
                if not trading_date:
                    raise RuntimeError("KIS 시장 수급 응답에 기준 거래일이 없습니다.")
                indicators.append({
                    "group":group, "name":name, "previous": current - change if current is not None else None,
                    "current":current, "market_cap":number(raw.get("bstp_nmix_avls")), "change":change,
                    "change_rate":number(raw.get("bstp_nmix_prdy_ctrt")),
                    "turnover":million_krw_to_eok(raw.get("acml_tr_pbmn")),
                    "foreign":million_krw_to_eok(investor.get("frgn_ntby_tr_pbmn")),
                    "institution":million_krw_to_eok(investor.get("orgn_ntby_tr_pbmn")),
                    "personal":million_krw_to_eok(investor.get("prsn_ntby_tr_pbmn")),
                    "tradingDate":trading_date,
                    "unit":{"turnover":"억원","flow":"억원"}
                })
            except Exception:
                errors.append(name)

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
                    "change":change,"change_rate":number(raw.get("prdy_ctrt")),"turnover":None,
                    "foreign":None,"institution":None,"personal":None,
                    "tradingDate":iso_date(raw.get("stck_bsop_date")),
                    "unit":{"turnover":"억원","flow":"억원"}})
            except Exception as exc:
                errors.append(f"{name} ({exc})")
        indicators.append({
            "group":"환율","name":"EUR","previous":None,"current":None,"market_cap":None,
            "change":None,"change_rate":None,"turnover":None,"foreign":None,"institution":None,
            "personal":None,"tradingDate":None,"unit":None
        })

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
                personal = number(investor.get("prsn_ntby_qty"), 0)
                volume = number(raw.get("acml_vol"), 0)
                row.update({
                    "previous": current - change if current is not None else None, "current":current,
                    "market_cap": number(raw.get("hts_avls")), "change":change,
                    "change_rate":number(raw.get("prdy_ctrt")), "volume":volume,
                    "foreign":foreign, "institution":institution,
                    "personal":personal, "tradingDate":iso_date(investor.get("stck_bsop_date")),
                    "unit":{"volume":"주","flow":"주"}
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
