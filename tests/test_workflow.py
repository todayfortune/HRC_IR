from pathlib import Path
import unittest


class WorkflowTests(unittest.TestCase):
    def test_daily_kst_schedule_and_secret_references(self):
        workflow = (Path(__file__).resolve().parents[1] / ".github" / "workflows" / "kis-daily-update.yml").read_text(encoding="utf-8")
        self.assertIn('cron: "0 21 * * *"', workflow)
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("secrets.KIS_APP_KEY", workflow)
        self.assertIn("secrets.KIS_APP_SECRET", workflow)


if __name__ == "__main__":
    unittest.main()
