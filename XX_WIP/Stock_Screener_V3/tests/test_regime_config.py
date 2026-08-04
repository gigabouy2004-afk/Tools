from __future__ import annotations

import unittest

from stock_screener_v3.models import UniverseRecord
from stock_screener_v3.regime_config import RegimeBenchmarkConfig


class RegimeConfigTests(unittest.TestCase):
    def test_default_config_maps_us_exchange_and_sector(self) -> None:
        config = RegimeBenchmarkConfig.default()
        record = UniverseRecord(symbol="NVDA", yahoo_symbol="NVDA", exchange="NASDAQ", sector="Technology")

        self.assertEqual(config.market_symbol_for(record), "QQQ")
        self.assertEqual(config.sector_symbol_for(record), "XLK")

    def test_default_config_maps_basic_materials_alias(self) -> None:
        config = RegimeBenchmarkConfig.default()
        record = UniverseRecord(symbol="LIN", yahoo_symbol="LIN", exchange="NASDAQ", sector="Basic Materials")

        self.assertEqual(config.sector_symbol_for(record), "XLB")

    def test_default_config_maps_telecom_alias(self) -> None:
        config = RegimeBenchmarkConfig.default()
        record = UniverseRecord(symbol="TMUS", yahoo_symbol="TMUS", exchange="NASDAQ", sector="Telecom")

        self.assertEqual(config.sector_symbol_for(record), "XLC")

    def test_default_config_maps_us_exchange_codes(self) -> None:
        config = RegimeBenchmarkConfig.default()

        self.assertEqual(config.market_symbol_for(UniverseRecord(symbol="AAA", yahoo_symbol="AAA", exchange="Q")), "QQQ")
        self.assertEqual(config.market_symbol_for(UniverseRecord(symbol="BBB", yahoo_symbol="BBB", exchange="N")), "SPY")

    def test_default_config_maps_india_exchange(self) -> None:
        config = RegimeBenchmarkConfig.default()
        record = UniverseRecord(symbol="RELIANCE", yahoo_symbol="RELIANCE.NS", exchange="NSE", sector="Energy")

        self.assertEqual(config.market_symbol_for(record), "^NSEI")

    def test_custom_config_supports_themes(self) -> None:
        config = RegimeBenchmarkConfig(theme_benchmarks={"AI": "BOTZ"})

        self.assertEqual(config.theme_symbol_for("ai"), "BOTZ")


if __name__ == "__main__":
    unittest.main()
