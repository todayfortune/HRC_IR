from pathlib import Path
import unittest


class WorkflowTests(unittest.TestCase):
    def test_kis_external_dispatch_inputs_and_secret_references(self):
        workflow = (Path(__file__).resolve().parents[1] / ".github" / "workflows" / "kis-daily-update.yml").read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("secrets.KIS_APP_KEY", workflow)
        self.assertIn("secrets.KIS_APP_SECRET", workflow)
        self.assertIn("refresh_market:", workflow)
        self.assertIn("allow_initial_token:", workflow)
        self.assertIn("inputs.refresh_market == true", workflow)
        self.assertIn("inputs.allow_initial_token == true", workflow)
        self.assertNotIn("schedule:", workflow)
        self.assertNotIn("github.event.schedule", workflow)
        self.assertIn('actions/cache/restore@v4', workflow)
        self.assertIn('actions/cache/save@v4', workflow)
        self.assertIn('runner.temp', workflow)
        self.assertIn('Unexpected tracked changes remain after market commit.', workflow)

    def test_market_script_only_saves_public_market_snapshot(self):
        script = (Path(__file__).resolve().parents[1] / "scripts" / "update_market.py").read_text(encoding="utf-8")
        self.assertIn("reports.save_market_snapshot(updated)", script)
        self.assertNotIn("reports.save(updated)", script)

    def test_telegram_external_dispatch_and_secret_references(self):
        workflow = (Path(__file__).resolve().parents[1] / ".github" / "workflows" / "telegram-update.yml").read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotIn("schedule:", workflow)
        for name in ("TELEGRAM_API_ID", "TELEGRAM_API_HASH", "TELEGRAM_SESSION"):
            self.assertIn(f"secrets.{name}", workflow)
        self.assertIn("python scripts/update_telegram.py", workflow)

    def test_hana_exchange_external_dispatch_has_no_kis_authentication(self):
        workflow = (Path(__file__).resolve().parents[1] / ".github" / "workflows" / "hana-exchange-update.yml").read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotIn("schedule:", workflow)
        self.assertIn("python scripts/update_exchange.py", workflow)
        for forbidden in ("KIS_APP_KEY", "KIS_APP_SECRET", "update_market.py", "tokenP"):
            self.assertNotIn(forbidden, workflow)


if __name__ == "__main__":
    unittest.main()
