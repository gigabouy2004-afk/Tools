import csv
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

import Momentum_Detector_V8_Basic as basic


class V8BasicFoundationTests(unittest.TestCase):
    def setUp(self):
        self.config = basic.load_config()
        self.fixed_time = datetime(2026, 7, 13, tzinfo=timezone.utc)

    def price_frame(self, values):
        close = pd.Series(
            values,
            index=pd.bdate_range("2024-01-01", periods=len(values)),
            dtype=float,
        )
        return pd.DataFrame({"Close": close}, index=close.index)

    def test_formula_matches_independent_ewm_calculation(self):
        frame = self.price_frame([100 + value * 0.2 + (value % 9) for value in range(320)])
        result = basic.calculate_foundation_frame(frame, self.config)
        close = frame["Close"]
        ema = close.ewm(span=200, adjust=False, min_periods=200).mean()
        fast = close.ewm(span=8, adjust=False, min_periods=8).mean()
        slow = close.ewm(span=21, adjust=False, min_periods=21).mean()
        line = fast - slow
        signal = line.ewm(span=5, adjust=False, min_periods=5).mean()
        pd.testing.assert_series_equal(result["EMA_Value"], ema, check_names=False)
        pd.testing.assert_series_equal(result["MACD_Line"], line, check_names=False)
        pd.testing.assert_series_equal(result["MACD_Signal_Line"], signal, check_names=False)
        pd.testing.assert_series_equal(
            result["MACD_Histogram"], line - signal, check_names=False
        )

    def test_all_foundation_states_have_explicit_boundaries(self):
        cases = [
            (110, 100, 2, 1, basic.FOUNDATION_ELIGIBLE, True),
            (100, 100, 2, 1, basic.FOUNDATION_BELOW_EMA, False),
            (110, 100, 2, 2, basic.FOUNDATION_MACD_POSITIVE_PULLBACK, False),
            (110, 100, 0, -1, basic.FOUNDATION_MACD_EARLY_RECOVERY, False),
            (110, 100, 0, 0, basic.FOUNDATION_MACD_NEGATIVE_WEAKENING, False),
            (110, 100, -2, -1, basic.FOUNDATION_MACD_NEGATIVE_WEAKENING, False),
        ]
        for close, ema, line, signal, state, eligible in cases:
            with self.subTest(state=state, line=line, signal=signal):
                result = basic.classify_foundation_values(
                    close, ema, line, signal, 300, 300
                )
                self.assertEqual(result["Foundation_State"], state)
                self.assertEqual(result["Foundation_Eligible"], eligible)

    def test_insufficient_history_has_no_fabricated_eligibility(self):
        frame = self.price_frame([100 + value for value in range(299)])
        result = basic.evaluate_foundation(
            "TEST", frame, self.config, evaluated_at=self.fixed_time
        )
        self.assertEqual(result["Data_Status"], basic.DATA_INSUFFICIENT)
        self.assertEqual(result["Foundation_State"], basic.FOUNDATION_INSUFFICIENT)
        self.assertFalse(result["Foundation_Eligible"])

    def test_historical_evaluation_is_prefix_only(self):
        frame = self.price_frame([100 + value * 0.2 + (value % 7) for value in range(340)])
        cutoff = frame.index[310]
        before = basic.evaluate_foundation(
            "TEST", frame, self.config, cutoff, self.fixed_time
        )
        changed = frame.copy()
        changed.loc[changed.index > cutoff, "Close"] = 10_000
        after = basic.evaluate_foundation(
            "TEST", changed, self.config, cutoff, self.fixed_time
        )
        self.assertEqual(before, after)

    def test_basic_output_contains_no_score_benchmark_or_etf_fields(self):
        frame = self.price_frame([100 + value * 0.3 for value in range(320)])
        result = basic.evaluate_foundation(
            "TEST", frame, self.config, evaluated_at=self.fixed_time
        )
        self.assertEqual(set(result), set(basic.OUTPUT_FIELDS))
        for forbidden in ("Score", "Benchmark_Ticker", "ETF_Ticker", "Weekly_Trend", "ATR_Pct"):
            self.assertNotIn(forbidden, result)
        self.assertEqual(result["Decision_Scope"], "FOUNDATION_ONLY_NO_SCORE")

    def test_invalid_periods_and_history_are_rejected(self):
        with self.assertRaises(ValueError):
            basic.validate_periods(200, 21, 8, 5, 300)
        with self.assertRaises(ValueError):
            basic.validate_periods(200, 8, 21, 5, 199)

    def test_overrides_are_visible_in_configuration_id(self):
        config = basic.load_config(
            overrides={"MACD.Fast": 12, "MACD.Slow": 26, "MACD.Signal": 9}
        )
        self.assertEqual(config["MACD"], {"Fast": 12, "Slow": 26, "Signal": 9})
        self.assertIn("MACD12_26_9", config["Configuration_ID"])

    def test_duplicate_dates_are_rejected(self):
        frame = self.price_frame([100, 101, 102])
        frame.index = pd.DatetimeIndex([frame.index[0], frame.index[0], frame.index[2]])
        with self.assertRaises(ValueError):
            basic.normalize_price_frame(frame)

    def test_append_only_log_rotates_an_old_schema(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "basic_log.csv"
            path.write_text("Old,Header\n1,2\n", encoding="utf-8")
            selected = basic.initialize_log(path)
            self.assertNotEqual(selected, path)
            self.assertEqual(path.read_text(encoding="utf-8"), "Old,Header\n1,2\n")
            with selected.open("r", encoding="utf-8", newline="") as file:
                self.assertEqual(next(csv.reader(file)), basic.LOG_FIELDS)


if __name__ == "__main__":
    unittest.main()
