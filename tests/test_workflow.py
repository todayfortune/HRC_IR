from pathlib import Path
import unittest


class WorkflowTests(unittest.TestCase):
    def test_daily_kst_schedule_and_secret_references(self):
        workflow = (Path(__file__).resolve().parents[1] / ".github" / "workflows" / "kis-daily-update.yml").read_text(encoding="utf-8")
        self.assertIn('cron: "0 21 * * *"', workflow)
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("secrets.KIS_APP_KEY", workflow)
        self.assertIn("secrets.KIS_APP_SECRET", workflow)
        self.assertIn("refresh_market:", workflow)
        self.assertIn("default: false", workflow)
        self.assertEqual(workflow.count("github.event_name == 'schedule' || inputs.refresh_market == true"), 2)

    def test_telegram_schedule_and_secret_references(self):
        workflow = (Path(__file__).resolve().parents[1] / ".github" / "workflows" / "telegram-update.yml").read_text(encoding="utf-8")
        self.assertIn('cron: "0 0,3,6,7 * * *"', workflow)
        self.assertIn("workflow_dispatch:", workflow)
        for name in ("TELEGRAM_API_ID", "TELEGRAM_API_HASH", "TELEGRAM_SESSION"):
            self.assertIn(f"secrets.{name}", workflow)
        self.assertIn("python scripts/update_telegram.py", workflow)

    def test_hana_exchange_schedule_has_no_kis_authentication(self):
        workflow = (Path(__file__).resolve().parents[1] / ".github" / "workflows" / "hana-exchange-update.yml").read_text(encoding="utf-8")
        self.assertIn('cron: "35 6 * * 1-5"', workflow)
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("python scripts/update_exchange.py", workflow)
        for forbidden in ("KIS_APP_KEY", "KIS_APP_SECRET", "update_market.py", "tokenP"):
            self.assertNotIn(forbidden, workflow)


if __name__ == "__main__":
    unittest.main()
