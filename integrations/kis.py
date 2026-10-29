from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import os
from pathlib import Path
import requests

PROD_BASE_URL = "https://openapi.koreainvestment.com:9443"

@dataclass(frozen=True)
class KisQuote:
    code: str
    name: str
    price: int
    change: int
    change_rate: float
    volume: int

class KisReadOnlyClient:
    """Minimal KIS REST client. This class intentionally exposes no order methods."""
    def __init__(self, app_key: str, app_secret: str, timeout: float = 10.0):
        self._app_key, self._app_secret, self._timeout = app_key, app_secret, timeout
        self._access_token: str | None = None

    def authenticate(self) -> None:
        # Repeated calls in one update run reuse the in-memory bearer token.
        if self._access_token:
            return
        cache_path = os.getenv('KIS_TOKEN_CACHE_PATH')
        if cache_path:
            from integrations.kis_token import cached_token
            self._access_token = cached_token(self._app_key, self._app_secret, cache_path, self._timeout)
            return
        if os.getenv('GITHUB_ACTIONS') == 'true':
            raise RuntimeError('KIS_TOKEN_CACHE_PATH is required in Actions; refusing uncached token issuance.')
        from integrations.kis_token import cached_token
        local_path = Path(os.getenv('LOCALAPPDATA') or Path.home()) / 'HRC_IR' / 'kis-private' / 'token.enc'
        self._access_token = cached_token(self._app_key, self._app_secret, local_path, self._timeout, prepare=True)

    def get_domestic_quote(self, code: str = "005930") -> KisQuote:
        data = self.get_domestic_quote_raw(code)
        return KisQuote(code, "삼성전자" if code == "005930" else code, int(data["stck_prpr"]), int(data["prdy_vrss"]), float(data["prdy_ctrt"]), int(data["acml_vol"]))

    def _request(self, path: str, tr_id: str, params: dict[str, str]) -> dict[str, Any]:
        if not self._access_token:
            raise RuntimeError("먼저 authenticate()를 호출해야 합니다.")
        response = requests.get(
            f"{PROD_BASE_URL}{path}",
            headers={"authorization":f"Bearer {self._access_token}","appkey":self._app_key,"appsecret":self._app_secret,"tr_id":tr_id,"custtype":"P"},
            params=params, timeout=self._timeout)
        try:
            payload: dict[str, Any] = response.json()
        except ValueError:
            payload = {}
        if not response.ok or payload.get("rt_cd") != "0":
            raise RuntimeError(
                "KIS 조회 실패: "
                f"http_status={response.status_code}, "
                f"msg_cd={payload.get('msg_cd', '-')}, "
                f"msg1={payload.get('msg1', '응답 메시지 없음')}"
            )
        return payload

    def _get(self, path: str, tr_id: str, params: dict[str, str]) -> Any:
        payload = self._request(path, tr_id, params)
        return payload.get("output")

    def get_domestic_quote_raw(self, code: str) -> dict[str, Any]:
        return self._get("/uapi/domestic-stock/v1/quotations/inquire-price", "FHKST01010100", {"FID_COND_MRKT_DIV_CODE":"J","FID_INPUT_ISCD":code})

    def get_domestic_investor(self, code: str) -> dict[str, Any]:
        output = self._get("/uapi/domestic-stock/v1/quotations/inquire-investor", "FHKST01010900", {"FID_COND_MRKT_DIV_CODE":"J","FID_INPUT_ISCD":code})
        return output[0] if isinstance(output, list) and output else {}

    def get_domestic_index(self, code: str) -> dict[str, Any]:
        return self._get("/uapi/domestic-stock/v1/quotations/inquire-index-price", "FHPUP02100000", {"FID_COND_MRKT_DIV_CODE":"U","FID_INPUT_ISCD":code})

    def get_domestic_daily(self, code: str, start: str, end: str, *, index=False):
        params = {"FID_COND_MRKT_DIV_CODE":"U" if index else "J", "FID_INPUT_ISCD":code,
                  "FID_INPUT_DATE_1":start, "FID_INPUT_DATE_2":end, "FID_PERIOD_DIV_CODE":"D"}
        if not index:
            params['FID_ORG_ADJ_PRC'] = '0'
        payload = self._request(
            '/uapi/domestic-stock/v1/quotations/' + ('inquire-daily-indexchartprice' if index else 'inquire-daily-itemchartprice'),
            'FHKUP03500100' if index else 'FHKST03010100', params)
        return payload.get('output2') or []

    def get_market_investor_daily(self, index_code: str, market_code: str, trading_date: str) -> dict[str, Any]:
        """Return the KOSPI/KOSDAQ cash-market investor totals for one trading day."""
        output = self._get(
            "/uapi/domestic-stock/v1/quotations/inquire-investor-daily-by-market",
            "FHPTJ04040000",
            {
                "FID_COND_MRKT_DIV_CODE": "U",
                "FID_INPUT_ISCD": index_code,
                "FID_INPUT_DATE_1": trading_date,
                "FID_INPUT_ISCD_1": market_code,
                "FID_INPUT_DATE_2": trading_date,
                "FID_INPUT_ISCD_2": index_code,
            },
        )
        return output[0] if isinstance(output, list) and output else {}

    def get_global_chart(self, market_code: str, item_code: str, start: str, end: str) -> dict[str, Any]:
        payload = self._request(
            "/uapi/overseas-price/v1/quotations/inquire-daily-chartprice", "FHKST03030100",
            {"FID_COND_MRKT_DIV_CODE":market_code,"FID_INPUT_ISCD":item_code,"FID_INPUT_DATE_1":start,"FID_INPUT_DATE_2":end,"FID_PERIOD_DIV_CODE":"D"})
        daily = payload.get("output2") or []
        daily = sorted((row for row in daily if row.get('stck_bsop_date') and row['stck_bsop_date'] <= end and float(row.get('ovrs_nmix_prpr') or 0) > 0), key=lambda row: row['stck_bsop_date'], reverse=True)
        if len(daily) < 2:
            raise RuntimeError('KIS overseas daily data requires current and previous trading sessions.')
        latest = daily[0] if isinstance(daily, list) and daily else {}
        previous = daily[1] if isinstance(daily, list) and len(daily) > 1 else {}
        # output1 can be an undated intraday value (notably FX). Use dated daily rows so
        # the value and tradingDate always describe the same completed market session.
        result = dict(latest)
        result['previousTradingDate'] = previous['stck_bsop_date']
        try:
            current_value = float(latest.get("ovrs_nmix_prpr"))
            previous_value = float(previous.get("ovrs_nmix_prpr"))
            change = round(current_value - previous_value, 6)
            result["ovrs_nmix_prdy_clpr"] = previous_value
            result["ovrs_nmix_prdy_vrss"] = change
            result["prdy_ctrt"] = round(change / previous_value * 100, 6) if previous_value else None
        except (TypeError, ValueError):
            pass
        if str(result.get("ovrs_nmix_prpr", "0")) in ("", "0", "0.0", "0.00"):
            raise RuntimeError(
                "KIS 해외 데이터 없음: "
                f"http_status=200, msg_cd={payload.get('msg_cd', '-')}, "
                f"msg1={payload.get('msg1', '응답 메시지 없음')}, item_code={item_code}"
            )
        return result
