from __future__ import annotations

import copy
import unittest
from unittest.mock import patch

from app.services.market.service import MarketService, dated_prices


class FakeKisClient:
    def __init__(self, fail_on: str | None = None):
        self.fail_on = fail_on
        self.authenticated = False
        self.global_codes = []

    def authenticate(self):
        if self.fail_on == "auth":
            raise RuntimeError("authentication failed")
        self.authenticated = True

    def get_domestic_index(self, code):
        if self.fail_on == code:
            raise RuntimeError("query failed")
        return {"bstp_nmix_prpr":"2700", "bstp_nmix_prdy_vrss":"10", "bstp_nmix_prdy_ctrt":"0.37", "acml_vol":"999999", "acml_tr_pbmn":"1234500"}

    def get_market_investor_daily(self, index_code, market_code, trading_date):
        return {"stck_bsop_date":"20260923", "frgn_ntby_tr_pbmn":"-498704", "orgn_ntby_tr_pbmn":"323347", "prsn_ntby_tr_pbmn":"-1454311"}

    def get_domestic_daily(self, code, start, end, index=False):
        field = 'bstp_nmix_prpr' if index else 'stck_clpr'
        return [
            {'stck_bsop_date':'20260923', field:'2700' if index else '70000', 'acml_vol':'10000', 'acml_tr_pbmn':'1234500'},
            {'stck_bsop_date':'20260922', field:'2690' if index else '69000'},
        ]

    def get_global_chart(self, market_code, item_code, start, end):
        self.global_codes.append(item_code)
        return {"stck_bsop_date":"20260923", "ovrs_nmix_prpr":"5000", "ovrs_nmix_prdy_clpr":"4990", "ovrs_nmix_prdy_vrss":"10", "prdy_ctrt":"0.2", "acml_vol":"100"}

    def get_domestic_quote_raw(self, code):
        if self.fail_on == code:
            raise RuntimeError("query failed")
        return {"stck_prpr":"70000", "prdy_vrss":"1000", "prdy_ctrt":"1.45", "acml_vol":"10000", "hts_avls":"4000000"}

    def get_domestic_investor(self, code):
        return {"stck_bsop_date":"20260923", "frgn_ntby_qty":"100", "orgn_ntby_qty":"200", "prsn_ntby_qty":"-350"}


def service_with(client):
    service = MarketService.__new__(MarketService)
    service.client = client
    return service


class MarketUpdateTests(unittest.TestCase):
    def test_preopen_holiday_ignores_future_placeholder_and_keeps_previous_session(self):
        rows = [
            {'stck_bsop_date':'20260928', 'stck_clpr':'70000'},
            {'stck_bsop_date':'20260925', 'stck_clpr':'69000'},
            {'stck_bsop_date':'20260924', 'stck_clpr':'68000'},
        ]
        current, previous = dated_prices(rows, 'stck_clpr', '20260927')
        self.assertEqual((current['stck_bsop_date'], previous['stck_bsop_date']), ('20260925', '20260924'))
        current, previous = dated_prices(rows, 'stck_clpr', '20260928')
        self.assertEqual((current['stck_clpr'], previous['stck_clpr']), ('70000', '69000'))

    def setUp(self):
        self.report = {"date":"2026-09-24", "stocks":[{"sector":"반도체", "name":"삼성전자", "code":"005930", "highlight":True}]}

    @patch("app.services.market.service.time.sleep", return_value=None)
    def test_success_sets_kst_status_after_authentication(self, _sleep):
        client = FakeKisClient()
        updated = service_with(client).update(self.report)
        self.assertTrue(client.authenticated)
        self.assertEqual(updated["status"], "success")
        self.assertRegex(updated["updatedAt"], r"^2026-|^20\d\d-")
        self.assertEqual(updated["updatedAt"], updated["updated_at"])
        self.assertEqual(updated["stocks"][0]["current"], 70000)
        self.assertEqual(updated["stocks"][0]["previous"], 69000)
        self.assertEqual(updated["stocks"][0]["previousTradingDate"], '2026-09-22')
        self.assertEqual(updated["indicators"][0]["previous"], 2690)
        self.assertEqual(updated["stocks"][0]["volume"], 10000)
        self.assertEqual(updated["stocks"][0]["personal"], -350)
        self.assertEqual(updated["stocks"][0]["tradingDate"], "2026-09-23")
        self.assertEqual(updated["indicators"][0]["turnover"], 12345)
        self.assertEqual(updated["indicators"][0]["foreign"], -4987.04)
        self.assertEqual(updated["indicators"][0]["institution"], 3233.47)
        self.assertEqual(updated["indicators"][0]["personal"], -14543.11)
        self.assertEqual(updated["indicators"][0]["tradingDate"], "2026-09-23")
        self.assertIsNone(updated["indicators"][2]["turnover"])
        self.assertEqual(client.global_codes, ["SPX", "COMP"])
        usd = next(row for row in updated["indicators"] if row["name"] == "USD")
        self.assertIsNone(usd["current"])

    def test_auth_failure_does_not_mutate_existing_report(self):
        before = copy.deepcopy(self.report)
        with self.assertRaises(RuntimeError):
            service_with(FakeKisClient("auth")).update(self.report)
        self.assertEqual(self.report, before)

    @patch("app.services.market.service.time.sleep", return_value=None)
    def test_query_failure_does_not_mutate_existing_report(self, _sleep):
        before = copy.deepcopy(self.report)
        with self.assertRaises(RuntimeError):
            service_with(FakeKisClient("005930")).update(self.report)
        self.assertEqual(self.report, before)


if __name__ == "__main__":
    unittest.main()
