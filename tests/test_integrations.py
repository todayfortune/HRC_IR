from __future__ import annotations
import os
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from integrations.env import load_env
from integrations.kis import KisReadOnlyClient

class EnvTests(unittest.TestCase):
    def test_loader_does_not_overwrite_existing_value(self):
        path = Path(__file__).parent / "fixtures" / "sample.env"
        with patch.dict(os.environ, {"SAFE_KEY": "process-value"}, clear=False):
            load_env(path)
            self.assertEqual(os.environ["SAFE_KEY"], "process-value")

class KisTests(unittest.TestCase):
    @patch("integrations.kis.requests.get")
    @patch("integrations.kis.requests.post")
    def test_auth_and_quote_mapping(self, post: Mock, get: Mock):
        post.return_value.json.return_value = {"access_token":"hidden-token"}
        post.return_value.raise_for_status.return_value = None
        get.return_value.json.return_value = {"rt_cd":"0","output":{"stck_prpr":"74200","prdy_vrss":"900","prdy_ctrt":"1.23","acml_vol":"123456"}}
        get.return_value.raise_for_status.return_value = None
        client = KisReadOnlyClient("key", "secret")
        client.authenticate()
        quote = client.get_domestic_quote()
        self.assertEqual((quote.code, quote.price, quote.volume), ("005930",74200,123456))
        post.assert_called_once_with(
            "https://openapi.koreainvestment.com:9443/oauth2/tokenP",
            json={"grant_type":"client_credentials","appkey":"key","appsecret":"secret"},
            timeout=10.0,
        )
        self.assertEqual(get.call_args.kwargs["headers"]["authorization"], "Bearer hidden-token")

    @patch("integrations.kis.requests.get")
    def test_query_error_contains_safe_diagnostics(self, get: Mock):
        get.return_value.ok = False
        get.return_value.status_code = 400
        get.return_value.json.return_value = {"rt_cd":"1", "msg_cd":"TEST001", "msg1":"invalid symbol"}
        client = KisReadOnlyClient("key", "secret")
        client._access_token = "hidden-token"
        with self.assertRaisesRegex(RuntimeError, "http_status=400, msg_cd=TEST001, msg1=invalid symbol"):
            client.get_global_chart("N", "BAD", "20260901", "20260924")

    @patch("integrations.kis.requests.get")
    def test_global_chart_uses_dated_closed_rows(self, get: Mock):
        get.return_value.ok = True
        get.return_value.status_code = 200
        get.return_value.json.return_value = {
            "rt_cd":"0",
            "output1":{"ovrs_nmix_prpr":"1368.3"},
            "output2":[
                {"stck_bsop_date":"20260923","ovrs_nmix_prpr":"1366.0"},
                {"stck_bsop_date":"20260922","ovrs_nmix_prpr":"1355.0"},
            ],
        }
        client = KisReadOnlyClient("key", "secret")
        client._access_token = "hidden-token"
        result = client.get_global_chart("X", "FX@KRW", "20260901", "20260924")
        self.assertEqual(result["stck_bsop_date"], "20260923")
        self.assertEqual(result["ovrs_nmix_prpr"], "1366.0")
        self.assertEqual(result["ovrs_nmix_prdy_clpr"], 1355.0)
        self.assertEqual(result["ovrs_nmix_prdy_vrss"], 11.0)
        self.assertAlmostEqual(result["prdy_ctrt"], 0.811808, places=5)

if __name__ == "__main__":
    unittest.main()
