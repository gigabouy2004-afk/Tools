import csv
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import pandas as pd
import ta

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
        return pd.DataFrame(
            {
                "Open": close - 0.2,
                "High": close + 1.0,
                "Low": close - 1.0,
                "Close": close,
                "Volume": [1_000_000 + (value % 11) * 10_000 for value in range(len(close))],
            },
            index=close.index,
        )

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

    def test_calculation_only_indicators_match_original_ta_formulas(self):
        frame = self.price_frame([100 + value * 0.2 + (value % 9) for value in range(320)])
        foundation = basic.calculate_foundation_frame(frame, self.config)
        result = basic.calculate_indicator_frame(
            foundation, self.config, foundation_eligible=True
        )
        high, low, close, volume = (
            frame["High"],
            frame["Low"],
            frame["Close"],
            frame["Volume"],
        )
        pd.testing.assert_series_equal(
            result["RSI"], ta.momentum.rsi(close, window=14, fillna=False), check_names=False
        )
        adx = ta.trend.ADXIndicator(high, low, close, window=14, fillna=False)
        pd.testing.assert_series_equal(result["ADX"], adx.adx(), check_names=False)
        pd.testing.assert_series_equal(
            result["DMI_Positive"], adx.adx_pos(), check_names=False
        )
        pd.testing.assert_series_equal(
            result["DMI_Negative"], adx.adx_neg(), check_names=False
        )
        expected_atr = ta.volatility.average_true_range(
            high, low, close, window=14, fillna=False
        )
        pd.testing.assert_series_equal(result["ATR"], expected_atr, check_names=False)
        pd.testing.assert_series_equal(
            result["ATR_Pct"], expected_atr / close * 100.0, check_names=False
        )
        expected_obv = ta.volume.on_balance_volume(close, volume, fillna=False)
        pd.testing.assert_series_equal(result["OBV"], expected_obv, check_names=False)
        pd.testing.assert_series_equal(
            result["OBV_EMA"],
            ta.trend.ema_indicator(expected_obv, window=20, fillna=False),
            check_names=False,
        )
        aroon = ta.trend.AroonIndicator(high, low, window=14, fillna=False)
        pd.testing.assert_series_equal(
            result["Aroon_Up"], aroon.aroon_up(), check_names=False
        )
        pd.testing.assert_series_equal(
            result["Aroon_Down"], aroon.aroon_down(), check_names=False
        )

    def test_true_range_matches_independent_definition(self):
        frame = self.price_frame([100, 103, 101, 106] + [106 + value for value in range(316)])
        foundation = basic.calculate_foundation_frame(frame, self.config)
        result = basic.calculate_indicator_frame(
            foundation, self.config, foundation_eligible=True
        )
        previous = frame["Close"].shift(1)
        expected = pd.concat(
            [
                frame["High"] - frame["Low"],
                (frame["High"] - previous).abs(),
                (frame["Low"] - previous).abs(),
            ],
            axis=1,
        ).max(axis=1)
        pd.testing.assert_series_equal(result["True_Range"], expected, check_names=False)

    def test_indicator_module_rejects_execution_without_foundation_eligibility(self):
        frame = self.price_frame([100 + value * 0.2 for value in range(320)])
        foundation = basic.calculate_foundation_frame(frame, self.config)
        with self.assertRaisesRegex(RuntimeError, "requires confirmed Foundation eligibility"):
            basic.calculate_indicator_frame(
                foundation, self.config, foundation_eligible=False
            )

    def test_ineligible_stock_never_enters_indicator_module(self):
        frame = self.price_frame([500 - value for value in range(320)])
        with mock.patch.object(
            basic,
            "calculate_indicator_frame",
            side_effect=AssertionError("indicator module must not run"),
        ) as indicator_module:
            result = basic.evaluate_foundation(
                "TEST", frame, self.config, evaluated_at=self.fixed_time
            )
        self.assertFalse(result["Foundation_Eligible"])
        indicator_module.assert_not_called()
        self.assertEqual(
            result["Indicator_Module_Status"], basic.INDICATOR_MODULE_NOT_RUN
        )
        self.assertEqual(result["RSI_Range_Status"], basic.RSI_NOT_EVALUATED)
        self.assertEqual(result["RSI_Allows_Further_Processing"], "")
        self.assertIn("Foundation eligibility was not confirmed", result["RSI_Message"])
        for field in (
            "RSI",
            "ADX",
            "DMI_Positive",
            "DMI_Negative",
            "True_Range",
            "ATR",
            "ATR_Pct",
            "OBV",
            "OBV_EMA",
            "Aroon_Up",
            "Aroon_Down",
        ):
            self.assertEqual(result[field], "", field)

    def test_eligible_stock_enters_indicator_module_after_foundation(self):
        frame = self.price_frame([100 + value * 0.3 for value in range(320)])
        original = basic.calculate_indicator_frame
        with mock.patch.object(
            basic, "calculate_indicator_frame", wraps=original
        ) as indicator_module:
            result = basic.evaluate_foundation(
                "TEST", frame, self.config, evaluated_at=self.fixed_time
            )
        self.assertTrue(result["Foundation_Eligible"])
        indicator_module.assert_called_once()
        self.assertTrue(indicator_module.call_args.kwargs["foundation_eligible"])
        self.assertEqual(
            result["Indicator_Module_Status"], basic.INDICATOR_MODULE_EXECUTED
        )
        self.assertNotEqual(result["RSI"], "")
        self.assertEqual(result["RSI_Range_Status"], basic.RSI_ABOVE_RANGE)
        self.assertFalse(result["RSI_Allows_Further_Processing"])
        self.assertIn(f"RSI {float(result['RSI']):.2f}", result["RSI_Message"])

    def test_rsi_limits_are_inclusive_and_messages_show_actual_value(self):
        cases = [
            (29.99, basic.RSI_BELOW_RANGE, False, "below lower limit 30"),
            (30.0, basic.RSI_WITHIN_RANGE, True, "RSI 30.00"),
            (45.0, basic.RSI_WITHIN_RANGE, True, "RSI 45.00"),
            (65.0, basic.RSI_WITHIN_RANGE, True, "RSI 65.00"),
            (65.01, basic.RSI_ABOVE_RANGE, False, "above upper limit 65"),
        ]
        for value, expected_status, expected_pass, message_text in cases:
            with self.subTest(value=value):
                result = basic.evaluate_rsi_value(value, 30, 65)
                self.assertEqual(result["RSI_Range_Status"], expected_status)
                self.assertEqual(
                    result["RSI_Allows_Further_Processing"], expected_pass
                )
                self.assertIn(message_text, result["RSI_Message"])

    def test_rsi_unavailable_stops_further_processing(self):
        result = basic.evaluate_rsi_value(float("nan"), 30, 65)
        self.assertEqual(result["RSI_Range_Status"], basic.RSI_UNAVAILABLE)
        self.assertFalse(result["RSI_Allows_Further_Processing"])

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
        for forbidden in ("Score", "Benchmark_Ticker", "ETF_Ticker", "Weekly_Trend"):
            self.assertNotIn(forbidden, result)
        self.assertEqual(
            result["Decision_Scope"], "FOUNDATION_THEN_RSI_CONTINUATION_NO_SCORE"
        )
        self.assertEqual(
            result["Indicator_Authority"], "RSI_GATE_OTHER_CALCULATION_ONLY"
        )
        self.assertEqual(result["RSI_Authority"], "CONTINUATION_GATE")
        self.assertEqual(result["RSI_Lower_Limit"], 30.0)
        self.assertEqual(result["RSI_Upper_Limit"], 65.0)
        self.assertIn("RSI", result)
        self.assertIn("ADX", result)
        self.assertIn("ATR", result)
        self.assertIn("OBV", result)
        self.assertIn("Aroon_Up", result)

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

    def test_indicator_period_and_rsi_limit_overrides_are_visible(self):
        config = basic.load_config(
            overrides={
                "Indicators.RSI_Period": 10,
                "Indicators.ADX_Period": 12,
                "Indicators.ATR_Period": 16,
                "Indicators.OBV_EMA_Period": 30,
                "Indicators.Aroon_Period": 20,
                "RSI_Rule.Lower_Limit": 35,
                "RSI_Rule.Upper_Limit": 60,
            }
        )
        self.assertEqual(
            config["Indicators"],
            {
                "RSI_Period": 10,
                "ADX_Period": 12,
                "ATR_Period": 16,
                "OBV_EMA_Period": 30,
                "Aroon_Period": 20,
            },
        )
        self.assertEqual(
            config["Indicator_Authority"], "RSI_GATE_OTHER_CALCULATION_ONLY"
        )
        self.assertEqual(config["Indicator_Rules"]["RSI"]["Lower_Limit"], 35.0)
        self.assertEqual(config["Indicator_Rules"]["RSI"]["Upper_Limit"], 60.0)
        self.assertIn("RSI10_RSILIM35_60_ADX12_ATR16", config["Configuration_ID"])
        self.assertIn("OBVEMA30_AROON20", config["Configuration_ID"])
        self.assertIn("RSILIM35_60", config["Configuration_ID"])

    def test_invalid_rsi_limits_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "RSI lower limit"):
            basic.load_config(
                overrides={
                    "RSI_Rule.Lower_Limit": 65,
                    "RSI_Rule.Upper_Limit": 30,
                }
            )

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
