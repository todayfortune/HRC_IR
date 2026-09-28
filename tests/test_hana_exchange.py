from __future__ import annotations

import unittest
from datetime import date
from pathlib import Path
from unittest.mock import Mock, patch

from app.services.market.hana_exchange import (
    HANA_RATE_URL,
    HanaRateError,
    NoAnnouncementError,
    build_exchange_snapshot,
    fetch_hana_usd_rate,
    parse_hana_usd_html,
    save_exchange_snapshot,
)


FIXTURE = Path(__file__).parent / "fixtures" / "hana_exchange_20260923.html"


class HanaExchangeTests(unittest.TestCase):
    def setUp(self):
        self.html = FIXTURE.read_text(encoding="utf-8")

    def test_verified_20260923_value(self):
        result = parse_hana_usd_html(self.html, "2026-09-23")
        self.assertEqual(result["announcementNumber"], 524)
        self.assertEqual(result["announcementTime"], "15:30:28")
        self.assertEqual(result["value"], 1358.40)
        self.assertEqual(result["rateType"], "매매기준율")

    def test_multiple_matches_choose_earliest_announcement(self):
        result = parse_hana_usd_html(self.html, "2026-09-23")
        self.assertEqual((result["announcementTime"], result["announcementNumber"]), ("15:30:28", 524))

    def test_out_of_window_rows_are_excluded(self):
        result = parse_hana_usd_html(self.html, "2026-09-23")
        self.assertNotEqual(result["announcementNumber"], 523)
        self.assertNotEqual(result["announcementNumber"], 528)

    def test_no_matching_window_fails(self):
        outside = self.html.replace("15:30:", "14:30:").replace("15:31:", "14:31:").replace("15:33:", "14:33:")
        with self.assertRaisesRegex(NoAnnouncementError, "고시가 없습니다"):
            parse_hana_usd_html(outside, "2026-09-23")

    def test_first_after_1533_is_allowed(self):
        html = self.html.replace("15:30:", "14:30:").replace("15:31:", "14:31:")
        self.assertEqual(parse_hana_usd_html(html, "2026-09-23")["announcementTime"], "15:33:34")

    def test_both_currencies_previous_date_and_freeze(self):
        def fetch(day, currency):
            if day == date(2026, 9, 27):
                raise NoAnnouncementError()
            return {"referenceDate": day.isoformat(), "value": 1358.4 if currency == "USD" else 1590.0, "selectionPolicy": "first-at-or-after-15:30"}
        result = build_exchange_snapshot(date(2026, 9, 28), {}, fetch)
        self.assertEqual(result["rates"]["EUR"]["previous"]["referenceDate"], "2026-09-26")
        never = Mock(side_effect=AssertionError("Fixed rates must not be fetched again"))
        self.assertEqual(build_exchange_snapshot(date(2026, 9, 28), result, never), result)

    def test_html_structure_change_fails(self):
        with self.assertRaisesRegex(HanaRateError, "환율 표 헤더"):
            parse_hana_usd_html("<html><table><tr><td>changed</td></tr></table></html>", "2026-09-23")

    @patch("app.services.market.hana_exchange.save_exchange_snapshot")
    @patch("app.services.market.hana_exchange.requests.post")
    def test_failed_fetch_preserves_existing_snapshot(self, post: Mock, save: Mock):
        response = Mock()
        response.text = "<html>broken</html>"
        response.raise_for_status.return_value = None
        post.return_value = response
        with self.assertRaises(HanaRateError):
            result = fetch_hana_usd_rate(date(2026, 9, 23))
            save_exchange_snapshot(result, Path("data/exchange_latest.json"))
        save.assert_not_called()
        self.assertEqual(post.call_args.args[0], HANA_RATE_URL)
        self.assertEqual(post.call_args.kwargs["data"]["curCd"], "USD")


if __name__ == "__main__":
    unittest.main()
