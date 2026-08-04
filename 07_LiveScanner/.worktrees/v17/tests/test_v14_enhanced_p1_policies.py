import unittest

from Live_Scanner_v14_Enhanced import (
    STATUS_BUY_SIGNAL,
    STATUS_HOLD,
    apply_buy_quality_policies,
    get_config,
    has_supportive_volume,
)


def buy_result(
    *,
    turnover=2_000_000.0,
    distance_atr=2.0,
):
    return {
        "status": STATUS_BUY_SIGNAL,
        "output_signal": "Buy_Momentum_Extension",
        "setup_type": "MOMENTUM_CONTINUATION",
        "classification": "BUY#3",
        "reason": "Momentum continuation",
        "OUT_MESSAGE": "BUY#3",
        "output_message": "BUY#3",
        "message": "BUY#3",
        "message_details": "BaseSignal=True",
        "risk_level": "Controlled",
        "average_daily_turnover_20": turnover,
        "ema50_distance_atr": distance_atr,
    }


class CurrentVolumeFloorTests(unittest.TestCase):
    def setUp(self):
        self.config = get_config("balanced")

    def test_historical_percentile_cannot_override_sub_floor_volume(self):
        self.assertFalse(has_supportive_volume(0.599, 100.0, self.config))

    def test_floor_allows_historical_percentile_support_path(self):
        self.assertTrue(has_supportive_volume(0.60, 60.0, self.config))

    def test_floor_does_not_replace_existing_support_requirement(self):
        self.assertFalse(has_supportive_volume(0.60, 59.99, self.config))


class BuyQualityPolicyTests(unittest.TestCase):
    def setUp(self):
        self.config = get_config("balanced")

    def test_us_buy_below_turnover_floor_is_withheld(self):
        result = apply_buy_quality_policies(
            buy_result(turnover=999_999.99),
            "US",
            self.config,
        )

        self.assertEqual(result["status"], STATUS_HOLD)
        self.assertEqual(
            result["output_signal"],
            "Hold_Buy_Liquidity_Below_Minimum",
        )
        self.assertEqual(result["classification"], "NO_BUY")
        self.assertFalse(result["liquidity_floor_passed"])

    def test_us_buy_at_turnover_floor_is_retained(self):
        result = apply_buy_quality_policies(
            buy_result(turnover=1_000_000.0),
            "US",
            self.config,
        )

        self.assertEqual(result["status"], STATUS_BUY_SIGNAL)
        self.assertTrue(result["liquidity_floor_passed"])

    def test_international_buy_has_no_absolute_turnover_gate(self):
        result = apply_buy_quality_policies(
            buy_result(turnover=10_000.0),
            "NSE",
            self.config,
        )

        self.assertEqual(result["status"], STATUS_BUY_SIGNAL)
        self.assertIsNone(result["minimum_adv20_turnover"])
        self.assertIsNone(result["liquidity_floor_passed"])

    def test_buy_beyond_five_atr_is_relabelled_for_review(self):
        result = apply_buy_quality_policies(
            buy_result(distance_atr=5.001),
            "US",
            self.config,
        )

        self.assertEqual(result["status"], STATUS_BUY_SIGNAL)
        self.assertEqual(result["classification"], "BUY_EXTENDED_REVIEW")
        self.assertTrue(result["extreme_extension_review"])

    def test_buy_at_five_atr_keeps_normal_classification(self):
        result = apply_buy_quality_policies(
            buy_result(distance_atr=5.0),
            "US",
            self.config,
        )

        self.assertEqual(result["classification"], "BUY#3")
        self.assertFalse(result["extreme_extension_review"])

    def test_liquidity_withholding_takes_priority_over_review_label(self):
        result = apply_buy_quality_policies(
            buy_result(turnover=50_000.0, distance_atr=8.0),
            "US",
            self.config,
        )

        self.assertEqual(result["status"], STATUS_HOLD)
        self.assertEqual(result["classification"], "NO_BUY")
        self.assertTrue(result["extreme_extension_review"])


if __name__ == "__main__":
    unittest.main()
