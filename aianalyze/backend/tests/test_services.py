import os
import unittest
from unittest.mock import patch

from services.ai_analyst import AIConfigurationError, _call_qwen
from services import market_data
from services.news_scraper import _format_timestamp


class FakeFrame:
    def __init__(self, records):
        self.records = records

    def to_dict(self, orient):
        if orient != "records":
            raise AssertionError("unexpected orientation")
        return self.records


class FakeAkshare:
    def stock_board_industry_name_em(self):
        return FakeFrame([
            {"板块名称": "半导体", "涨跌幅": 2.345, "最新价": 1234.56},
            {"板块名称": "银行", "涨跌幅": -0.5, "最新价": 998.1},
        ])

    def stock_board_industry_cons_em(self, symbol):
        self.requested_sector = symbol
        return FakeFrame([
            {"代码": "688981", "名称": "中芯国际", "最新价": 99.8, "涨跌幅": 1.2, "成交量": 1000},
        ])

    def stock_zh_a_hist(self, **kwargs):
        self.history_args = kwargs
        return FakeFrame([
            {"日期": "2026-08-01", "开盘": 10, "最高": 12, "最低": 9, "收盘": 11, "成交量": 1200},
            {"日期": "2026-08-04", "开盘": 11, "最高": 13, "最低": 10, "收盘": 12, "成交量": 1500},
        ])


class MarketDataTests(unittest.TestCase):
    def setUp(self):
        market_data._cache.clear()
        self.akshare = FakeAkshare()
        self.patcher = patch.object(market_data, "_get_akshare", return_value=self.akshare)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def test_hot_sectors_are_normalized_and_sorted(self):
        result = market_data.get_hot_sectors_a()
        self.assertEqual(result[0]["板块名称"], "半导体")
        self.assertEqual(result[0]["涨跌幅"], 2.35)

    def test_sector_constituents_are_normalized(self):
        result = market_data.get_sector_stocks("半导体")
        self.assertEqual(result[0]["code"], "688981")
        self.assertEqual(result[0]["name"], "中芯国际")

    def test_a_share_history_requires_six_digit_code(self):
        with self.assertRaises(ValueError):
            market_data.get_stock_detail_a("NVDA")

    def test_a_share_history_is_serializable(self):
        result = market_data.get_stock_detail_a("600519")
        self.assertEqual(result["history"][-1]["close"], 12.0)
        self.assertEqual(result["history"][-1]["date"], "2026-08-04")


class AIConfigurationTests(unittest.TestCase):
    def test_missing_key_fails_before_network_call(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(AIConfigurationError):
                _call_qwen("test")


class NewsFormattingTests(unittest.TestCase):
    def test_unix_timestamp_is_human_readable(self):
        result = _format_timestamp("1767225600")
        self.assertRegex(result, r"^\d{2}-\d{2} \d{2}:\d{2}$")

    def test_rss_date_is_preserved(self):
        self.assertEqual(_format_timestamp("Tue, 04 Aug 2026"), "Tue, 04 Aug 2026")


if __name__ == "__main__":
    unittest.main()
