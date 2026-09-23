from __future__ import annotations

import unittest

from app.services.telegram.service import classify_messages, excerpt, normalize


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


if __name__ == "__main__":
    unittest.main()
