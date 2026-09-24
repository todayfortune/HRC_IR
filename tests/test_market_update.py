from __future__ import annotations

import copy
import unittest
from unittest.mock import patch

from app.services.market.service import MarketService


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
        return {"bstp_nmix_prpr":"2700", "bstp_nmix_prdy_vrss":"10", "bstp_nmix_prdy_ctrt":"0.37", "acml_vol":"100"}

    def get_global_chart(self, market_code, item_code, start, end):
        self.global_codes.append(item_code)
        return {"ovrs_nmix_prpr":"5000", "ovrs_nmix_prdy_clpr":"4990", "ovrs_nmix_prdy_vrss":"10", "prdy_ctrt":"0.2", "acml_vol":"100"}

    def get_domestic_quote_raw(self, code):
        if self.fail_on == code:
            raise RuntimeError("query failed")
        return {"stck_prpr":"70000", "prdy_vrss":"1000", "prdy_ctrt":"1.45", "acml_vol":"10000", "hts_avls":"4000000"}

    def get_domestic_investor(self, code):
        return {"frgn_ntby_qty":"100", "orgn_ntby_qty":"200"}


def service_with(client):
    service = MarketService.__new__(MarketService)
    service.client = client
    return service


class MarketUpdateTests(unittest.TestCase):
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
        self.assertEqual(client.global_codes, ["SPX", "COMP", "FX@KRW"])

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
