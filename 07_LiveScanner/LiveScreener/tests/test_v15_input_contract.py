import unittest

from Live_Scanner_v15 import parse_direct_ticker_codes


class DirectTickerInputContractTests(unittest.TestCase):
    def test_compact_comma_separated_string(self):
        self.assertEqual(
            parse_direct_ticker_codes(["ETN,VRT,PWR,GEV,CAT,PH"]),
            ["ETN", "VRT", "PWR", "GEV", "CAT", "PH"],
        )

    def test_comma_and_leading_space_string(self):
        self.assertEqual(
            parse_direct_ticker_codes(["ETN, VRT, PWR, GEV, CAT, PH"]),
            ["ETN", "VRT", "PWR", "GEV", "CAT", "PH"],
        )

    def test_space_segmented_arguments_remain_supported(self):
        self.assertEqual(
            parse_direct_ticker_codes(["ETN", "VRT", "PWR"]),
            ["ETN", "VRT", "PWR"],
        )

    def test_mixed_segments_are_normalized_and_deduplicated(self):
        self.assertEqual(
            parse_direct_ticker_codes(
                [" etn, VRT ", "PWR,ETN", "", " XNSE:RELIANCE "]
            ),
            ["ETN", "VRT", "PWR", "RELIANCE.NS"],
        )

    def test_empty_segments_are_ignored(self):
        self.assertEqual(
            parse_direct_ticker_codes([",", "  ", "CAT,,PH,"]),
            ["CAT", "PH"],
        )


if __name__ == "__main__":
    unittest.main()
