from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from telethon.sessions import StringSession

from app.services.telegram.service import classify_messages, excerpt, normalize, session_value
from scripts.update_telegram import main as update_telegram


class TelegramFilterTests(unittest.TestCase):
    def setUp(self):
        self.messages = [
            {"channel":"SHINHANRESEARCH","message_id":10,"source":"신한리서치","date":"2026-09-24T17:00+09:00","text":"국내  주식\n마감 시황\n삼성전자와 SK하이닉스 강세","link":"https://t.me/SHINHANRESEARCH/10"},
            {"channel":"SHINHANRESEARCH","message_id":10,"source":"신한리서치","date":"2026-09-24T17:00+09:00","text":"중복","link":"https://t.me/SHINHANRESEARCH/10"},
            {"channel":"DAISHINSTRATEGY","message_id":20,"source":"대신증권","date":"2026-09-23T17:00+09:00","text":"삼성전자 이전 날짜","link":"https://t.me/DAISHINSTRATEGY/20"},
        ]

    def test_normalize_ignores_space_and_case(self):
        self.assertEqual(normalize(" Market  CLOSE\n"), "marketclose")

    def test_classifies_deduplicates_and_filters_kst_date(self):
        result = classify_messages(self.messages, ["삼성전자","SK하이닉스"], ["국내주식 마감시황"], "2026-09-24", 700)
        self.assertEqual(len(result["closing"]), 1)
        self.assertEqual(len(result["stock_news"]), 1)
        self.assertEqual(result["stock_news"][0]["stocks"], ["삼성전자","SK하이닉스"])
        self.assertEqual(result["closing"][0]["message_id"], 10)

    def test_excerpt_prefers_a_boundary(self):
        value = "첫 문장입니다.\n" + ("긴내용" * 100)
        result = excerpt(value, 80)
        self.assertTrue(result.endswith("…"))
        self.assertLessEqual(len(result), 81)

    def test_github_actions_requires_string_session(self):
        valid = StringSession.save(StringSession())
        with patch.dict("os.environ", {"GITHUB_ACTIONS":"true"}):
            self.assertIsInstance(session_value(valid), StringSession)
            with self.assertRaises(RuntimeError):
                session_value("local-file.session")


class TelegramUpdateScriptTests(unittest.TestCase):
    @patch("scripts.update_telegram.TelegramService")
    @patch("scripts.update_telegram.ReportService")
    def test_does_not_save_when_feed_is_unchanged(self, report_service, telegram_service):
        reports = report_service.return_value
        current = {"telegram_feed":{"closing":[], "stock_news":[]}}
        reports.load.return_value = current
        telegram_service.return_value.update.return_value = current
        update_telegram()
        reports.save.assert_not_called()

    @patch("scripts.update_telegram.TelegramService")
    @patch("scripts.update_telegram.ReportService")
    def test_saves_when_feed_changes(self, report_service, telegram_service):
        reports = report_service.return_value
        current = {"telegram_feed":{"closing":[], "stock_news":[]}}
        updated = {"telegram_feed":{"closing":[{"message_id":1}], "stock_news":[]}}
        reports.load.return_value = current
        telegram_service.return_value.update.return_value = updated
        update_telegram()
        reports.save.assert_called_once_with(updated)


if __name__ == "__main__":
    unittest.main()
