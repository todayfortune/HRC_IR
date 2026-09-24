from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class StaticPagesTests(unittest.TestCase):
    def test_frontend_has_no_backend_api_calls(self):
        app = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        self.assertNotIn("/api/", app)
        self.assertIn("market_latest.json", app)
        self.assertIn("dailyTrendComments:", app)
        self.assertIn("../data/", app)
        self.assertIn("exchange_latest.json", app)
        self.assertIn("Object.assign(usd,{current:null", app)

    def test_market_turnover_and_stock_volume_use_distinct_formatters(self):
        app = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        page = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        self.assertIn("const turnover = value", app)
        self.assertIn("Math.round(Number(value)/1000)", app)
        self.assertIn("turnover(row.turnover)", app)
        self.assertNotIn("volume(row.volume,'억')", app)
        self.assertIn("<th>거래대금</th>", page)
        self.assertEqual(page.count("<th>개인</th>"), 2)
        self.assertIn("tradingDate", app)
        self.assertIn("하나은행 · 매매기준율", app)
        self.assertIn("announcementTime", app)

    def test_euwang_telegram_section_titles_and_photo(self):
        page = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        self.assertIn("으왕 마감시황", page)
        self.assertIn("으왕 종목뉴스", page)
        self.assertEqual(page.count('src="assets/euwang-profile.jpg"'), 2)
        self.assertTrue((ROOT / "web" / "assets" / "euwang-profile.jpg").is_file())

    def test_pages_workflow_deploys_web_and_data(self):
        workflow = (ROOT / ".github" / "workflows" / "deploy-pages.yml").read_text(encoding="utf-8")
        for expected in (
            "workflow_dispatch:", "workflow_run:", "KIS Daily Market Update",
            "Telegram Research Update", "actions/configure-pages@v5",
            "actions/upload-pages-artifact@v3", "actions/deploy-pages@v4",
            "cp -R web/. _site/", "_site/data/market_latest.json",
            "_site/data/exchange_latest.json",
        ):
            self.assertIn(expected, workflow)


if __name__ == "__main__":
    unittest.main()
