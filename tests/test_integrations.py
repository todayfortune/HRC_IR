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

if __name__ == "__main__":
    unittest.main()
