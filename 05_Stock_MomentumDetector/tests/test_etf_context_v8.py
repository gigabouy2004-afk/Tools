import csv
import tempfile
import unittest
from pathlib import Path

import ETF_Context_V8 as etf_context


def make_row(exchange, ticker, name, weight):
    return (
        f'<tr data-rowkey="{exchange}:{ticker}">'
        f'<td><a class="tickerNameBox">{ticker}</a>'
        f'<a class="tickerDescription">{name}</a></td>'
        f'<td>1.0 B USD</td><td>{weight}%</td><td>Issuer</td></tr>'
    )


class ETFContextV8Tests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.stock_master = self.root / "stocks.csv"
        self.etf_master = self.root / "etfs.csv"
        self.cache_path = self.root / "cache.json"
        with open(self.stock_master, "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=["Ticker", "Listing Exchange"])
            writer.writeheader()
            writer.writerow({"Ticker": "TEST", "Listing Exchange": "NASDAQ"})
        with open(self.etf_master, "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=["Ticker", "Security Name", "Listing Exchange", "Strategy", "Theme", "Category Flags"],
            )
            writer.writeheader()
            writer.writerow({"Ticker": "AAA", "Security Name": "AAA Fund", "Listing Exchange": "NYSE ARCA"})
            writer.writerow({"Ticker": "BBB", "Security Name": "BBB Fund", "Listing Exchange": "NASDAQ"})
            writer.writerow(
                {
                    "Ticker": "LEV",
                    "Security Name": "Leveraged 3x Fund",
                    "Listing Exchange": "NYSE ARCA",
                    "Category Flags": "Leveraged",
                }
            )
        etf_context.load_stock_exchange_map.cache_clear()
        etf_context.load_us_etf_metadata.cache_clear()
        etf_context.load_message_templates.cache_clear()

    def tearDown(self):
        self.temp_dir.cleanup()

    def fixture_html(self):
        return "<table>" + "".join(
            [
                make_row("AMEX", "AAA", "AAA Provider Name", "15.25"),
                make_row("NASDAQ", "BBB", "BBB Provider Name", "8.50"),
                make_row("AMEX", "LEV", "Leveraged 3x Fund", "25.00"),
                make_row("LSE", "FOREIGN", "Foreign Fund", "30.00"),
            ]
        ) + "</table>"

    def fake_fetcher(self, url, timeout_seconds):
        return {
            "Body": self.fixture_html(),
            "HTTP_Status": 200,
            "Latency_Ms": 12.5,
            "Last_Modified": "",
            "Body_SHA256": "fixture-hash",
        }

    def test_parser_extracts_ticker_name_exchange_and_weight(self):
        rows = etf_context.parse_direct_exposure_rows(self.fixture_html())
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[0]["ETF_Ticker"], "AAA")
        self.assertEqual(rows[0]["ETF_Name"], "AAA Provider Name")
        self.assertEqual(rows[0]["ETF_Exchange_Provider"], "AMEX")
        self.assertEqual(rows[0]["Holding_Weight_Pct"], 15.25)

    def test_strict_filter_requires_us_nonleveraged_and_proven_top10(self):
        rows = etf_context.parse_direct_exposure_rows(self.fixture_html())
        accepted, rejected = etf_context.filter_verified_top10_mappings(rows, self.etf_master)
        self.assertEqual([row["ETF_Ticker"] for row in accepted], ["AAA"])
        reasons = {row["ETF_Ticker"]: row["Eligibility_Reason"] for row in rejected}
        self.assertEqual(reasons["BBB"], "TOP10_NOT_PROVEN_BY_CONSERVATIVE_WEIGHT_TEST")
        self.assertEqual(reasons["LEV"], "LEVERAGED_OR_INVERSE_EXCLUDED")
        self.assertEqual(reasons["FOREIGN"], "NOT_IN_LOCAL_US_ETF_MASTER")

    def test_context_uses_one_direct_fetch_and_cache(self):
        calls = []

        def counted_fetcher(url, timeout_seconds):
            calls.append(url)
            return self.fake_fetcher(url, timeout_seconds)

        first = etf_context.get_etf_mapping_context(
            "TEST",
            stock_master_path=self.stock_master,
            etf_master_path=self.etf_master,
            cache_path=self.cache_path,
            fetcher=counted_fetcher,
        )
        second = etf_context.get_etf_mapping_context(
            "TEST",
            stock_master_path=self.stock_master,
            etf_master_path=self.etf_master,
            cache_path=self.cache_path,
            fetcher=counted_fetcher,
        )
        self.assertEqual(len(calls), 1)
        self.assertEqual(first["ETF_Status"], "OK")
        self.assertFalse(first["Cache_Hit"])
        self.assertTrue(second["Cache_Hit"])

    def test_postprocessor_trigger_and_score_invariance(self):
        active = {"Ticker": "TEST", "Final_Decision": "MOMENTUM_ACTIVE", "Score": 85}
        context = etf_context.apply_etf_postprocessor(
            active,
            active_threshold=85,
            stock_master_path=self.stock_master,
            etf_master_path=self.etf_master,
            cache_path=self.cache_path,
            fetcher=self.fake_fetcher,
        )
        self.assertEqual(active["Score"], 85)
        self.assertEqual(context["Verified_Top10_Count"], 1)
        self.assertIn("AAA 15.25%", active["Score_Message"])

        waiting = {"Ticker": "TEST", "Final_Decision": "MOMENTUM_PRESENT_WAIT_CONFIRMATION", "Score": 84}
        self.assertIsNone(
            etf_context.apply_etf_postprocessor(
                waiting,
                active_threshold=85,
                stock_master_path=self.stock_master,
                etf_master_path=self.etf_master,
                cache_path=self.cache_path,
                fetcher=self.fake_fetcher,
            )
        )
        self.assertNotIn("Score_Message", waiting)

    def test_top_three_are_sorted_by_weight_descending(self):
        rows = [
            {"ETF_Ticker": "AAA", "ETF_Name": "A", "ETF_Exchange_Provider": "AMEX", "Holding_Weight_Pct": 11.0},
            {"ETF_Ticker": "BBB", "ETF_Name": "B", "ETF_Exchange_Provider": "NASDAQ", "Holding_Weight_Pct": 12.0},
        ]
        with open(self.etf_master, "a", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=["Ticker", "Security Name", "Listing Exchange", "Strategy", "Theme", "Category Flags"],
            )
            writer.writerow({"Ticker": "CCC", "Security Name": "C", "Listing Exchange": "NYSE ARCA"})
            writer.writerow({"Ticker": "DDD", "Security Name": "D", "Listing Exchange": "NYSE ARCA"})
        etf_context.load_us_etf_metadata.cache_clear()
        rows.extend(
            [
                {"ETF_Ticker": "CCC", "ETF_Name": "C", "ETF_Exchange_Provider": "AMEX", "Holding_Weight_Pct": 14.0},
                {"ETF_Ticker": "DDD", "ETF_Name": "D", "ETF_Exchange_Provider": "AMEX", "Holding_Weight_Pct": 13.0},
            ]
        )
        accepted, rejected = etf_context.filter_verified_top10_mappings(rows, self.etf_master, max_mappings=3)
        self.assertEqual([row["ETF_Ticker"] for row in accepted], ["CCC", "DDD", "BBB"])
        self.assertEqual(rejected[0]["ETF_Ticker"], "AAA")
        self.assertEqual(rejected[0]["Eligibility_Reason"], "OMITTED_BY_TOP3_LIMIT")


if __name__ == "__main__":
    unittest.main()
