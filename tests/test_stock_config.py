import json
from pathlib import Path
import unittest


class StockConfigTests(unittest.TestCase):
    def test_hyundai_steel_and_engineering_are_in_universe(self):
        path = Path(__file__).resolve().parents[1] / "config" / "stocks.json"
        stocks = json.loads(path.read_text(encoding="utf-8"))["stocks"]
        configured = {(item["name"], item["code"], item["sector"]) for item in stocks}

        self.assertIn(("현대제철", "004020", "그룹사"), configured)
        self.assertIn(("현대건설", "000720", "그룹사"), configured)

    def test_market_update_uses_configured_universe(self):
        path = Path(__file__).resolve().parents[1] / "scripts" / "update_market.py"
        script = path.read_text(encoding="utf-8")
        self.assertIn('report["stocks"] = reports.blank(report["date"])["stocks"]', script)


if __name__ == "__main__":
    unittest.main()
