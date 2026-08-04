from __future__ import annotations

import unittest

import pandas as pd

from stock_screener_v3.data_provider import YahooFinancePriceProvider, YahooPriceProvider, normalize_price_columns


class DataProviderTests(unittest.TestCase):
    def test_yahoo_price_provider_alias_remains_available(self) -> None:
        self.assertIs(YahooPriceProvider, YahooFinancePriceProvider)

    def test_normalize_price_columns_flattens_multiindex(self) -> None:
        frame = pd.DataFrame(
            [[1, 2, 0.5, 1.5, 1000, 99]],
            columns=pd.MultiIndex.from_tuples(
                [
                    ("Open", "AAA"),
                    ("High", "AAA"),
                    ("Low", "AAA"),
                    ("Close", "AAA"),
                    ("Volume", "AAA"),
                    ("Ignored", "AAA"),
                ]
            ),
        )

        normalized = normalize_price_columns(frame)

        self.assertEqual(list(normalized.columns), ["Open", "High", "Low", "Close", "Volume"])
        self.assertEqual(float(normalized["Close"].iloc[0]), 1.5)

    def test_normalize_price_columns_capitalizes_common_columns(self) -> None:
        frame = pd.DataFrame({"open": [1], "high": [2], "low": [0.5], "close": [1.5], "volume": [1000]})

        normalized = normalize_price_columns(frame)

        self.assertEqual(list(normalized.columns), ["Open", "High", "Low", "Close", "Volume"])


if __name__ == "__main__":
    unittest.main()
