import unittest
from datetime import datetime, timezone
from unittest import mock

import pandas as pd

import V8_V1_V3_Indicator_Baseline as baseline
import Momentum_Detector_V8_Basic as basic


class V1V3IndicatorBaselineTests(unittest.TestCase):
    def setUp(self):
        self.config = baseline.load_config()
        self.fixed_time = datetime(2026, 7, 13, tzinfo=timezone.utc)

    def frame(self, close_values):
        close = pd.Series(
            close_values,
            index=pd.bdate_range("2024-01-01", periods=len(close_values)),
            dtype=float,
        )
        return pd.DataFrame(
            {
                "Open": close - 0.25,
                "High": close + 1.0,
                "Low": close - 1.0,
                "Close": close,
                "Volume": [1_000_000 + (index % 7) * 100_000 for index in range(len(close))],
            },
            index=close.index,
        )

    def test_source_periods_and_values_are_frozen_in_configuration(self):
        self.assertEqual(self.config["EMA_Period"], 200)
        self.assertEqual(self.config["MACD"], {"Fast": 12, "Slow": 26, "Signal": 9})
        self.assertEqual(
            self.config["Indicators"],
            {
                "RSI_Period": 14,
                "ADX_Period": 14,
                "ATR_Period": 14,
                "OBV_EMA_Period": 20,
                "Aroon_Period": 14,
            },
        )
        self.assertEqual(self.config["Limit_Status"], "RESEARCH_CANDIDATE_NOT_OPERATIONAL")
        self.assertFalse(self.config["Operational_Use_Approved"])

    def test_rsi_source_boundaries(self):
        rule = self.config["Indicator_Rules"]["RSI"]
        cases = [
            (54.99, 0, "RSI_BELOW_MINIMUM"),
            (55.0, 5, "RSI_MINIMUM_TO_PREFERRED"),
            (55.99, 5, "RSI_MINIMUM_TO_PREFERRED"),
            (56.0, 10, "RSI_PREFERRED_RANGE"),
            (68.0, 10, "RSI_PREFERRED_RANGE"),
            (68.01, 5, "RSI_PREFERRED_TO_MAXIMUM"),
            (75.0, 5, "RSI_PREFERRED_TO_MAXIMUM"),
            (75.01, -10, "RSI_ABOVE_MAXIMUM"),
        ]
        for value, score, status in cases:
            with self.subTest(value=value):
                self.assertEqual(baseline.score_rsi(value, rule), (score, status))

    def test_adx_source_boundaries(self):
        rule = self.config["Indicator_Rules"]["ADX"]
        cases = [
            (19.99, 0, "ADX_BELOW_MINIMUM"),
            (20.0, 5, "ADX_PARTIAL_RANGE"),
            (25.99, 5, "ADX_PARTIAL_RANGE"),
            (26.0, 10, "ADX_PREFERRED_RANGE"),
            (40.0, 10, "ADX_PREFERRED_RANGE"),
            (40.01, 5, "ADX_PARTIAL_RANGE"),
            (60.0, 5, "ADX_PARTIAL_RANGE"),
            (60.01, -5, "ADX_ABOVE_HIGH"),
        ]
        for value, score, status in cases:
            with self.subTest(value=value):
                self.assertEqual(baseline.score_adx(value, rule), (score, status))

    def test_obv_fresh_cross_and_divergence(self):
        rule = self.config["Indicator_Rules"]["OBV"]
        cross = pd.DataFrame(
            {
                "Close": [100, 99, 101, 102],
                "OBV": [8, 9, 11, 12],
                "OBV_EMA": [10, 10, 10, 11],
            }
        )
        self.assertEqual(
            baseline.score_obv(cross, rule),
            (10, True, "OBV_FRESH_CROSS"),
        )
        divergence = pd.DataFrame(
            {
                "Close": [100, 101],
                "OBV": [10, 9],
                "OBV_EMA": [8, 8],
            }
        )
        self.assertEqual(
            baseline.score_obv(divergence, rule),
            (-5, False, "OBV_NEGATIVE_DIVERGENCE"),
        )

    def test_aroon_and_opening_structure_source_rules(self):
        rule = self.config["Indicator_Rules"]["Aroon"]
        self.assertEqual(baseline.score_aroon(71, 29, rule), (10, "AROON_STRONG"))
        self.assertEqual(baseline.score_aroon(51, 49, rule), (5, "AROON_MODERATE"))
        self.assertEqual(baseline.score_aroon(29, 71, rule), (-5, "AROON_BEARISH"))
        frame = self.frame([100, 102])
        score, passed, status = baseline.score_opening_structure(
            frame, self.config["Indicator_Rules"]["Opening_Structure"]
        )
        self.assertEqual((score, passed, status), (5, True, "OPEN_ABOVE_PRIOR_OPEN"))

    def test_v1_and_v2_profiles_are_technically_identical(self):
        frame = self.frame([100 + index * 0.3 for index in range(330)])
        as_of = frame.index[-1]
        v1 = baseline.evaluate_profile("TEST", frame, as_of, "V1", self.config, self.fixed_time)
        v2 = baseline.evaluate_profile("TEST", frame, as_of, "V2", self.config, self.fixed_time)
        for key in v1:
            if key != "Profile":
                self.assertEqual(v1[key], v2[key], key)

    def test_foundation_ineligible_never_enters_indicator_module(self):
        frame = self.frame([500 - index for index in range(330)])
        with mock.patch.object(
            basic,
            "calculate_indicator_frame",
            side_effect=AssertionError("indicator module must not run"),
        ) as indicator_module:
            result = baseline.evaluate_profile(
                "TEST", frame, frame.index[-1], "V3", self.config, self.fixed_time
            )
        self.assertFalse(result["Foundation_Eligible"])
        indicator_module.assert_not_called()
        self.assertEqual(result["Indicator_Module_Status"], "NOT_RUN_FOUNDATION_INELIGIBLE")


if __name__ == "__main__":
    unittest.main()
