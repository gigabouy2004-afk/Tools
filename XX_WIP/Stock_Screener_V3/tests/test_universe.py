from __future__ import annotations

from pathlib import Path
import unittest

from stock_screener_v3.universe import deterministic_sample, filter_records, load_universe_records, normalize_yahoo_symbol


ROOT = Path(__file__).resolve().parents[1]


class UniverseLoaderTests(unittest.TestCase):
    def test_load_us_master_preserves_metadata_and_dedupes(self) -> None:
        records = load_universe_records(ROOT / "data" / "samples" / "us_master_sample.csv")

        self.assertEqual([record.yahoo_symbol for record in records], ["NVDA", "XOM", "PNR"])
        nvda = records[0]
        self.assertEqual(nvda.symbol, "NVDA")
        self.assertEqual(nvda.company_name, "NVIDIA Corporation - Common Stock")
        self.assertEqual(nvda.exchange, "Q")
        self.assertEqual(nvda.sector, "Technology")
        self.assertEqual(nvda.industry, "Semiconductors")
        self.assertEqual(nvda.instrument_type, "N")
        self.assertEqual(nvda.market_cap, 5689041183540.0)
        self.assertEqual(nvda.avg_daily_volume, 25000000.0)
        self.assertEqual(nvda.last_profile_refresh_date.isoformat(), "2026-06-01")

    def test_nse_master_symbols_are_normalized_to_yahoo_suffix(self) -> None:
        records = load_universe_records(ROOT / "data" / "samples" / "nse_equity_sample.csv")

        self.assertEqual([record.yahoo_symbol for record in records], ["RELIANCE.NS", "TCS.NS"])
        self.assertEqual(records[0].company_name, "Reliance Industries Limited")

    def test_normalize_yahoo_symbol_adds_ns_only_for_nse(self) -> None:
        self.assertEqual(normalize_yahoo_symbol("RELIANCE", source_is_nse=True), "RELIANCE.NS")
        self.assertEqual(normalize_yahoo_symbol("AAPL", exchange="NASDAQ"), "AAPL")
        self.assertEqual(normalize_yahoo_symbol("TCS.NS", exchange="NSE"), "TCS.NS")
        self.assertEqual(normalize_yahoo_symbol("TCS", exchange="BSE"), "TCS.BO")
        self.assertEqual(normalize_yahoo_symbol("TCS.BO", exchange="BSE"), "TCS.BO")

    def test_mixed_exchange_csv_preserves_codes_and_normalizes_yahoo_symbols(self) -> None:
        records = load_universe_records(ROOT / "data" / "samples" / "mixed_exchange_sample.csv")

        self.assertEqual(
            [(record.symbol, record.exchange, record.yahoo_symbol) for record in records],
            [
                ("RELIANCE", "NSE", "RELIANCE.NS"),
                ("TCS", "BSE", "TCS.BO"),
                ("AAPL", "NASDAQ", "AAPL"),
                ("XOM", "NYSE", "XOM"),
            ],
        )

    def test_filter_records_by_sector_preserves_metadata(self) -> None:
        records = load_universe_records(ROOT / "data" / "samples" / "us_master_sample.csv")

        filtered = filter_records(records, sectors=("Technology", "Energy"))

        self.assertEqual([record.yahoo_symbol for record in filtered], ["NVDA", "XOM"])
        self.assertEqual(filtered[0].sector, "Technology")

    def test_deterministic_sample_is_reproducible(self) -> None:
        records = load_universe_records(ROOT / "data" / "samples" / "us_master_sample.csv")

        first = deterministic_sample(records, sample_size=2, random_seed=20260602)
        second = deterministic_sample(records, sample_size=2, random_seed=20260602)

        self.assertEqual([record.yahoo_symbol for record in first], [record.yahoo_symbol for record in second])
        self.assertEqual(len(first), 2)


if __name__ == "__main__":
    unittest.main()
