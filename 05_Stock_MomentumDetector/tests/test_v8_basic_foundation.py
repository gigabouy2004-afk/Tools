import csv
import json
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

    def eligible_frame(self):
        return self.price_frame([100 + value * 0.3 + (value % 7) * 0.2 for value in range(320)])

    def test_default_foundation_and_score_values_match_approved_research_package(self):
        self.assertEqual(self.config["MACD"], {"Fast": 12, "Slow": 26, "Signal": 9})
        self.assertEqual(self.config["Decision_Scope"], "FOUNDATION_THEN_DMI_THEN_V1_COMPOSITE_HEALTH_SCORE")
        self.assertEqual(self.config["Health_Score"]["Maximum_Positive_Score"], 30)
        self.assertEqual(self.config["Health_Score"]["Research_Qualification_Threshold"], 20)
        self.assertEqual(self.config["Health_Score"]["Components"], ["RSI", "ADX", "OBV"])
        self.assertFalse(self.config["Health_Score"]["Operational_Use_Approved"])
        self.assertFalse(self.config["Health_Score"]["Probability_Calibrated"])

    def test_formula_matches_independent_ewm_calculation(self):
        frame = self.eligible_frame()
        result = basic.calculate_foundation_frame(frame, self.config)
        close = frame["Close"]
        ema = close.ewm(span=200, adjust=False, min_periods=200).mean()
        fast = close.ewm(span=12, adjust=False, min_periods=12).mean()
        slow = close.ewm(span=26, adjust=False, min_periods=26).mean()
        line = fast - slow
        signal = line.ewm(span=9, adjust=False, min_periods=9).mean()
        pd.testing.assert_series_equal(result["EMA_Value"], ema, check_names=False)
        pd.testing.assert_series_equal(result["MACD_Line"], line, check_names=False)
        pd.testing.assert_series_equal(result["MACD_Signal_Line"], signal, check_names=False)

    def test_indicators_match_ta_formulas(self):
        frame = self.eligible_frame()
        foundation = basic.calculate_foundation_frame(frame, self.config)
        result = basic.calculate_indicator_frame(foundation, self.config, foundation_eligible=True)
        high, low, close, volume = frame["High"], frame["Low"], frame["Close"], frame["Volume"]
        pd.testing.assert_series_equal(result["RSI"], ta.momentum.rsi(close, window=14), check_names=False)
        adx = ta.trend.ADXIndicator(high, low, close, window=14)
        pd.testing.assert_series_equal(result["ADX"], adx.adx(), check_names=False)
        pd.testing.assert_series_equal(result["DMI_Positive"], adx.adx_pos(), check_names=False)
        pd.testing.assert_series_equal(result["DMI_Negative"], adx.adx_neg(), check_names=False)
        expected_obv = ta.volume.on_balance_volume(close, volume)
        pd.testing.assert_series_equal(result["OBV"], expected_obv, check_names=False)
        pd.testing.assert_series_equal(
            result["OBV_EMA"], ta.trend.ema_indicator(expected_obv, window=20), check_names=False
        )

    def test_indicator_module_requires_foundation(self):
        frame = self.eligible_frame()
        foundation = basic.calculate_foundation_frame(frame, self.config)
        with self.assertRaisesRegex(RuntimeError, "requires confirmed Foundation eligibility"):
            basic.calculate_indicator_frame(foundation, self.config, foundation_eligible=False)

    def test_foundation_ineligible_stops_before_indicators_and_score(self):
        frame = self.price_frame([500 - value for value in range(320)])
        with mock.patch.object(basic, "calculate_indicator_frame", side_effect=AssertionError("must not run")) as module:
            result = basic.evaluate_foundation("TEST", frame, self.config, evaluated_at=self.fixed_time)
        module.assert_not_called()
        self.assertFalse(result["Foundation_Eligible"])
        self.assertEqual(result["Indicator_Module_Status"], basic.INDICATOR_MODULE_NOT_RUN)
        self.assertEqual(result["Health_Score_Module_Status"], basic.HEALTH_SCORE_NOT_RUN_FOUNDATION)
        self.assertEqual(result["Raw_Health_Score"], "")
        self.assertFalse(result["Health_Qualified"])

    def test_dmi_ineligible_stops_before_component_scores(self):
        frame = self.eligible_frame()
        foundation = basic.calculate_foundation_frame(frame, self.config)
        calculated = basic.calculate_indicator_frame(foundation, self.config, foundation_eligible=True)
        calculated["DMI_Positive"] = 10.0
        calculated["DMI_Negative"] = 20.0
        with mock.patch.object(basic, "calculate_indicator_frame", return_value=calculated):
            result = basic.evaluate_foundation("TEST", frame, self.config, evaluated_at=self.fixed_time)
        self.assertTrue(result["Foundation_Eligible"])
        self.assertFalse(result["DMI_Eligible"])
        self.assertEqual(result["Health_Score_Module_Status"], basic.HEALTH_SCORE_NOT_RUN_DMI)
        self.assertEqual(result["Raw_Health_Score"], "")
        self.assertEqual(result["RSI_Score"], "")
        self.assertEqual(result["Health_Qualification_State"], "NOT_QUALIFIED_DMI_INELIGIBLE")

    def test_dmi_eligible_executes_combined_health_score(self):
        frame = self.eligible_frame()
        result = basic.evaluate_foundation("TEST", frame, self.config, evaluated_at=self.fixed_time)
        self.assertTrue(result["Foundation_Eligible"])
        self.assertTrue(result["DMI_Eligible"])
        self.assertEqual(result["Health_Score_Module_Status"], basic.HEALTH_SCORE_EXECUTED)
        self.assertEqual(
            result["Raw_Health_Score"],
            result["RSI_Score"] + result["ADX_Score"] + result["OBV_Score"],
        )
        self.assertEqual(
            result["Health_Qualified"], result["Raw_Health_Score"] >= 20
        )
        self.assertIn(f"{result['Raw_Health_Score']}/30", result["Health_Qualification_Message"])

    def test_rsi_score_boundaries(self):
        rule = self.config["Indicator_Rules"]["RSI"]
        cases = [(54.99, 0), (55, 5), (55.99, 5), (56, 10), (68, 10), (68.01, 5), (75, 5), (75.01, -10)]
        for value, expected in cases:
            with self.subTest(value=value):
                score, _, message = basic.score_rsi_value(value, rule)
                self.assertEqual(score, expected)
                self.assertIn(f"RSI {value:.2f}", message)

    def test_adx_score_boundaries(self):
        rule = self.config["Indicator_Rules"]["ADX"]
        cases = [(19.99, 0), (20, 5), (25.99, 5), (26, 10), (40, 10), (40.01, 5), (60, 5), (60.01, -5)]
        for value, expected in cases:
            with self.subTest(value=value):
                score, _, message = basic.score_adx_value(value, rule)
                self.assertEqual(score, expected)
                self.assertIn(f"ADX {value:.2f}", message)

    def test_obv_score_fresh_cross_and_divergence(self):
        rule = self.config["Indicator_Rules"]["OBV"]
        fresh = pd.DataFrame(
            {"Close": [10, 10, 10, 10], "OBV": [5, 7, 12, 13], "OBV_EMA": [10, 10, 10, 11]}
        )
        score, crossed, status, _ = basic.score_obv_frame(fresh, rule)
        self.assertEqual((score, crossed, status), (10, True, "OBV_FRESH_CROSS"))
        divergence = pd.DataFrame(
            {"Close": [10, 11], "OBV": [10, 9], "OBV_EMA": [8, 8]}
        )
        score, crossed, status, _ = basic.score_obv_frame(divergence, rule)
        self.assertEqual((score, crossed, status), (-5, False, "OBV_NEGATIVE_DIVERGENCE"))

    def test_all_foundation_states_have_explicit_boundaries(self):
        cases = [
            (110, 100, 2, 1, basic.FOUNDATION_ELIGIBLE, True),
            (100, 100, 2, 1, basic.FOUNDATION_BELOW_EMA, False),
            (110, 100, 2, 2, basic.FOUNDATION_MACD_POSITIVE_PULLBACK, False),
            (110, 100, 0, -1, basic.FOUNDATION_MACD_EARLY_RECOVERY, False),
            (110, 100, 0, 0, basic.FOUNDATION_MACD_NEGATIVE_WEAKENING, False),
        ]
        for close, ema, line, signal, state, eligible in cases:
            result = basic.classify_foundation_values(close, ema, line, signal, 300, 300)
            self.assertEqual((result["Foundation_State"], result["Foundation_Eligible"]), (state, eligible))

    def test_insufficient_history_has_no_fabricated_score(self):
        frame = self.price_frame([100 + value for value in range(299)])
        result = basic.evaluate_foundation("TEST", frame, self.config, evaluated_at=self.fixed_time)
        self.assertEqual(result["Data_Status"], basic.DATA_INSUFFICIENT)
        self.assertEqual(result["Raw_Health_Score"], "")
        self.assertFalse(result["Health_Qualified"])

    def test_historical_evaluation_is_prefix_only(self):
        frame = self.price_frame([100 + value * 0.2 + (value % 7) for value in range(340)])
        cutoff = frame.index[310]
        before = basic.evaluate_foundation("TEST", frame, self.config, cutoff, self.fixed_time)
        changed = frame.copy()
        changed.loc[changed.index > cutoff, "Close"] = 10_000
        after = basic.evaluate_foundation("TEST", changed, self.config, cutoff, self.fixed_time)
        self.assertEqual(before, after)

    def test_output_exposes_components_total_and_research_boundary(self):
        result = basic.evaluate_foundation("TEST", self.eligible_frame(), self.config, evaluated_at=self.fixed_time)
        self.assertEqual(set(result), set(basic.OUTPUT_FIELDS))
        for required in ("RSI_Score", "ADX_Score", "OBV_Score", "Raw_Health_Score", "Health_Qualified"):
            self.assertIn(required, result)
        for forbidden in ("Score", "Benchmark_Ticker", "ETF_Ticker", "Weekly_Trend_Score"):
            self.assertNotIn(forbidden, result)
        self.assertEqual(result["Maximum_Health_Score"], 30)
        self.assertEqual(result["Health_Score_Threshold"], 20)
        self.assertFalse(result["Health_Score_Operational_Use_Approved"])
        self.assertFalse(result["Health_Score_Probability_Calibrated"])
        self.assertEqual(result["Aroon_Authority"], "CALCULATION_ONLY_EXCLUDED_FROM_V1_SCORE")

    def test_invalid_periods_and_history_are_rejected(self):
        with self.assertRaises(ValueError):
            basic.validate_periods(200, 26, 12, 9, 300)
        with self.assertRaises(ValueError):
            basic.validate_periods(200, 12, 26, 9, 199)

    def test_overrides_are_visible_and_threshold_is_configurable(self):
        config = basic.load_config(
            overrides={
                "MACD.Fast": 8,
                "MACD.Slow": 21,
                "MACD.Signal": 5,
                "Health_Score.Research_Qualification_Threshold": 15,
            }
        )
        self.assertEqual(config["MACD"], {"Fast": 8, "Slow": 21, "Signal": 5})
        self.assertEqual(config["Health_Score"]["Research_Qualification_Threshold"], 15)
        self.assertIn("MACD8_21_5", config["Configuration_ID"])
        self.assertIn("SCOREMIN15", config["Configuration_ID"])

    def test_research_rules_cannot_claim_operational_approval(self):
        config = json.loads(basic.DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))
        config["Health_Score"]["Operational_Use_Approved"] = True
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "invalid.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "not approved for operational use"):
                basic.load_config(path)

    def test_duplicate_dates_are_rejected(self):
        frame = self.price_frame([100, 101, 102])
        frame.index = pd.DatetimeIndex([frame.index[0], frame.index[0], frame.index[2]])
        with self.assertRaises(ValueError):
            basic.normalize_price_frame(frame)

    def test_append_only_log_rotates_old_schema(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "basic_log.csv"
            path.write_text("Old,Header\n1,2\n", encoding="utf-8")
            selected = basic.initialize_log(path)
            self.assertNotEqual(selected, path)
            with selected.open("r", encoding="utf-8", newline="") as file:
                self.assertEqual(next(csv.reader(file)), basic.LOG_FIELDS)


if __name__ == "__main__":
    unittest.main()
