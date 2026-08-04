import unittest

import pandas as pd

import Momentum_Detector_V8 as engine


class V8MACDTests(unittest.TestCase):
    def price_frame(self, close):
        close = pd.Series(close, index=pd.bdate_range("2024-01-01", periods=len(close)), dtype=float)
        return pd.DataFrame(
            {
                "Open": close - 0.2,
                "High": close + 1.0,
                "Low": close - 1.0,
                "Close": close,
                "Volume": 2_000_000,
            },
            index=close.index,
        )

    def test_production_defaults_are_fibonacci_foundation_periods(self):
        self.assertEqual(
            (
                engine.DEFAULT_MACD_FAST_PERIOD,
                engine.DEFAULT_MACD_SLOW_PERIOD,
                engine.DEFAULT_MACD_SIGNAL_PERIOD,
            ),
            (8, 21, 5),
        )
        self.assertEqual(engine.DEFAULT_FOUNDATION_POLICY, "enforce")

    def test_standard_and_fibonacci_settings_are_configurable(self):
        close = pd.Series(
            [100 + value * 0.5 + (value % 7) for value in range(80)],
            index=pd.bdate_range("2026-01-01", periods=80),
            dtype=float,
        )
        standard = engine.calculate_macd(close, 12, 26, 9)
        fibonacci = engine.calculate_macd(close, 8, 21, 5)
        self.assertFalse(standard["MACD_Line"].equals(fibonacci["MACD_Line"]))
        self.assertFalse(standard["MACD_Signal_Line"].equals(fibonacci["MACD_Signal_Line"]))

    def test_macd_matches_independent_ewm_formula(self):
        close = pd.Series(range(1, 81), dtype=float)
        result = engine.calculate_macd(close, 8, 21, 5)
        fast = close.ewm(span=8, adjust=False, min_periods=8).mean()
        slow = close.ewm(span=21, adjust=False, min_periods=21).mean()
        expected_line = fast - slow
        expected_signal = expected_line.ewm(span=5, adjust=False, min_periods=5).mean()
        pd.testing.assert_series_equal(result["MACD_Line"], expected_line, check_names=False)
        pd.testing.assert_series_equal(result["MACD_Signal_Line"], expected_signal, check_names=False)

    def test_invalid_periods_are_rejected(self):
        with self.assertRaises(ValueError):
            engine.validate_macd_periods(21, 8, 5)
        with self.assertRaises(ValueError):
            engine.validate_macd_periods(8, 21, 0)

    def test_indicator_frame_records_selected_periods(self):
        index = pd.bdate_range("2024-01-01", periods=320)
        close = pd.Series([100 + value * 0.2 for value in range(320)], index=index)
        frame = pd.DataFrame(
            {
                "Open": close - 0.2,
                "High": close + 1.0,
                "Low": close - 1.0,
                "Close": close,
                "Volume": 2_000_000,
            },
            index=index,
        )
        result = engine.calculate_v5_indicators(
            frame,
            frame,
            macd_fast_period=8,
            macd_slow_period=21,
            macd_signal_period=5,
        )
        self.assertEqual(result.iloc[-1]["MACD_Fast_Period"], 8)
        self.assertEqual(result.iloc[-1]["MACD_Slow_Period"], 21)
        self.assertEqual(result.iloc[-1]["MACD_Signal_Period"], 5)
        self.assertIn("MACD_Histogram", result.columns)

    def test_future_prices_do_not_change_prior_macd(self):
        close = pd.Series(
            range(1, 101), index=pd.bdate_range("2026-01-01", periods=100), dtype=float
        )
        cutoff = close.index[70]
        before = engine.calculate_macd(close.loc[:cutoff], 8, 21, 5).loc[cutoff]
        changed = close.copy()
        changed.loc[changed.index > cutoff] = 10_000
        after = engine.calculate_macd(changed, 8, 21, 5).loc[cutoff]
        pd.testing.assert_series_equal(before, after)

    def test_foundation_valid_requires_close_above_ema_and_bullish_positive_macd(self):
        frame = self.price_frame([100 + value * 0.25 for value in range(320)])
        result = engine.calculate_foundation_indicators(frame)
        row = result.iloc[-1]
        self.assertEqual(row["Foundation_Status"], engine.FOUNDATION_VALID)
        self.assertTrue(bool(row["Foundation_Qualified"]))
        self.assertGreater(row["Close"], row["EMA_200"])
        self.assertGreater(row["MACD_Line"], row["MACD_Signal_Line"])
        self.assertGreater(row["MACD_Line"], 0)

    def test_foundation_below_ema_is_invalid(self):
        values = [200 - value * 0.25 for value in range(320)]
        row = engine.calculate_foundation_indicators(self.price_frame(values)).iloc[-1]
        self.assertEqual(row["Foundation_Status"], engine.FOUNDATION_BELOW_EMA200)
        self.assertFalse(bool(row["Foundation_Qualified"]))

    def test_macd_reset_stops_as_wait_without_setup_score(self):
        values = [100 + value * 0.3 for value in range(300)] + [190 - value * 0.15 for value in range(20)]
        row = engine.calculate_foundation_indicators(self.price_frame(values)).iloc[-1]
        self.assertGreater(row["Close"], row["EMA_200"])
        self.assertEqual(row["Foundation_Status"], engine.FOUNDATION_MACD_RESET)
        output = engine.build_foundation_status_row("TEST", row)
        self.assertEqual(output["Final_Decision"], "MOMENTUM_PRESENT_WAIT_CONFIRMATION")
        self.assertEqual(output["Score"], 0)
        self.assertIn("skipped", output["Score_Message"])


if __name__ == "__main__":
    unittest.main()
