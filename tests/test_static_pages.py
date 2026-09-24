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

    def test_pages_workflow_deploys_web_and_data(self):
        workflow = (ROOT / ".github" / "workflows" / "deploy-pages.yml").read_text(encoding="utf-8")
        for expected in (
            "workflow_dispatch:", "workflow_run:", "KIS Daily Market Update",
            "Telegram Research Update", "actions/configure-pages@v5",
            "actions/upload-pages-artifact@v3", "actions/deploy-pages@v4",
            "cp -R web/. _site/", "_site/data/market_latest.json",
        ):
            self.assertIn(expected, workflow)


if __name__ == "__main__":
    unittest.main()
