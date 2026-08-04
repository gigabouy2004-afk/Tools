import unittest

import pandas as pd

from Live_Scanner_v15 import (
    STATUS_BUY_SIGNAL,
    STATUS_ERROR,
    STATUS_HOLD,
    STATUS_IGNORE,
    apply_v15_shadow_entry_state,
    build_v15_shadow_momentum_assessment,
    percentage_change_over_lookback,
)


def shadow_assessment(**overrides):
    values = {
        "primary_regime_passed": True,
        "ema50_slope_20_pct": 3.0,
        "ema200_slope_60_pct": 4.0,
        "return_20d_pct": 5.0,
        "return_60d_pct": 10.0,
        "return_120d_pct": 20.0,
        "adx_value": 25.0,
        "adx_plus_di": 30.0,
        "adx_minus_di": 15.0,
        "adx_change_5": 2.0,
        "price_pct_52w_high": 95.0,
        "volume_ratio": 1.2,
        "ema50_distance_atr": 2.0,
    }
    values.update(overrides)
    return build_v15_shadow_momentum_assessment(**values)


def classified_result(**overrides):
    values = {
        "status": STATUS_BUY_SIGNAL,
        "classification": "BUY#3",
        "output_signal": "Buy_Momentum_Extension",
        **shadow_assessment(),
    }
    values.update(overrides)
    return values


class PercentageChangeTests(unittest.TestCase):
    def test_percentage_change_uses_completed_observation_lookback(self):
        values = pd.Series([100.0, 110.0, 121.0])
        self.assertAlmostEqual(
            percentage_change_over_lookback(values, 2),
            21.0,
        )

    def test_percentage_change_returns_none_for_insufficient_history(self):
        self.assertIsNone(
            percentage_change_over_lookback(pd.Series([100.0, 101.0]), 2)
        )

    def test_percentage_change_returns_none_for_zero_base(self):
        self.assertIsNone(
            percentage_change_over_lookback(pd.Series([0.0, 5.0]), 1)
        )


class MomentumQualityStateTests(unittest.TestCase):
    def test_complete_quality_evidence_is_leader(self):
        result = shadow_assessment()
        self.assertEqual(result["momentum_state"], "LEADER")
        self.assertEqual(result["momentum_quality_score"], 10)
        self.assertTrue(result["adx_rising_5"])

    def test_failed_primary_regime_is_never_momentum(self):
        result = shadow_assessment(primary_regime_passed=False)
        self.assertEqual(result["momentum_state"], "NONE")
        self.assertEqual(result["momentum_quality_score"], 10)

    def test_six_checks_is_developing(self):
        result = shadow_assessment(
            return_20d_pct=-1.0,
            return_60d_pct=-1.0,
            return_120d_pct=-1.0,
            volume_ratio=0.9,
        )
        self.assertEqual(result["momentum_quality_score"], 6)
        self.assertEqual(result["momentum_state"], "DEVELOPING")

    def test_fewer_than_six_checks_is_weak(self):
        result = shadow_assessment(
            ema50_slope_20_pct=-1.0,
            ema200_slope_60_pct=-1.0,
            return_20d_pct=-1.0,
            return_60d_pct=-1.0,
            return_120d_pct=-1.0,
        )
        self.assertEqual(result["momentum_state"], "WEAK")


class ShadowEntryStateTests(unittest.TestCase):
    def test_confirmed_shadow_buy_does_not_change_v14_fields(self):
        original = classified_result()
        result = apply_v15_shadow_entry_state(original)

        self.assertEqual(result["entry_state"], "CONFIRMED")
        self.assertEqual(result["shadow_recommended_status"], STATUS_BUY_SIGNAL)
        self.assertFalse(result["v15_classification_active"])
        self.assertEqual(result["status"], STATUS_BUY_SIGNAL)
        self.assertEqual(result["classification"], "BUY#3")
        self.assertEqual(
            result["output_signal"],
            "Buy_Momentum_Extension",
        )

    def test_failed_regime_is_no_entry(self):
        result = apply_v15_shadow_entry_state(
            classified_result(v15_primary_regime_passed=False)
        )
        self.assertEqual(result["entry_state"], "NO_ENTRY")
        self.assertEqual(result["shadow_recommended_status"], STATUS_IGNORE)

    def test_extension_wait_has_priority(self):
        result = apply_v15_shadow_entry_state(
            classified_result(entry_extension_safe=False)
        )
        self.assertEqual(result["entry_state"], "WAIT_EXTENDED")
        self.assertEqual(result["shadow_recommended_status"], STATUS_HOLD)

    def test_adx_wait_precedes_volume_and_leadership(self):
        result = apply_v15_shadow_entry_state(
            classified_result(
                adx_directional_bullish=False,
                volume_at_or_above_average=False,
                momentum_state="DEVELOPING",
            )
        )
        self.assertEqual(result["entry_state"], "WAIT_ADX")

    def test_volume_wait_precedes_leadership(self):
        result = apply_v15_shadow_entry_state(
            classified_result(
                volume_at_or_above_average=False,
                momentum_state="DEVELOPING",
            )
        )
        self.assertEqual(result["entry_state"], "WAIT_VOLUME")

    def test_developing_momentum_waits_for_leadership(self):
        result = apply_v15_shadow_entry_state(
            classified_result(momentum_state="DEVELOPING")
        )
        self.assertEqual(result["entry_state"], "WAIT_LEADERSHIP")

    def test_non_buy_leader_waits_for_v14_trigger(self):
        result = apply_v15_shadow_entry_state(
            classified_result(status=STATUS_HOLD)
        )
        self.assertEqual(result["entry_state"], "WAIT_TRIGGER")
        self.assertEqual(result["shadow_recommended_status"], STATUS_HOLD)

    def test_error_is_not_applicable(self):
        result = apply_v15_shadow_entry_state(
            classified_result(status=STATUS_ERROR)
        )
        self.assertEqual(result["entry_state"], "NOT_APPLICABLE")
        self.assertEqual(result["shadow_recommended_status"], STATUS_ERROR)


if __name__ == "__main__":
    unittest.main()
