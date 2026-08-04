import unittest

from Live_Scanner_v14_Enhanced import (
    is_confirmed_positive_macd_crossover,
    is_confirmed_positive_histogram_expansion,
    is_sustained_positive_histogram_contraction,
)


class PositiveMacdCrossoverTests(unittest.TestCase):
    def test_gloster_pre_cross_values_are_not_confirmed(self):
        self.assertFalse(
            is_confirmed_positive_macd_crossover(
                previous_macd=0.686,
                previous_signal=1.845,
                current_macd=1.544,
                current_signal=1.785,
            )
        )

    def test_fresh_crossover_above_zero_is_confirmed(self):
        self.assertTrue(
            is_confirmed_positive_macd_crossover(
                previous_macd=1.40,
                previous_signal=1.50,
                current_macd=1.70,
                current_signal=1.60,
            )
        )

    def test_crossover_below_zero_is_not_confirmed(self):
        self.assertFalse(
            is_confirmed_positive_macd_crossover(
                previous_macd=-1.50,
                previous_signal=-1.40,
                current_macd=-1.10,
                current_signal=-1.20,
            )
        )

    def test_existing_bullish_alignment_is_continuation_not_fresh_cross(self):
        self.assertFalse(
            is_confirmed_positive_macd_crossover(
                previous_macd=1.70,
                previous_signal=1.60,
                current_macd=1.80,
                current_signal=1.65,
            )
        )


class PositiveHistogramRegimeTests(unittest.TestCase):
    def test_three_positive_expanding_bars_are_confirmed(self):
        self.assertTrue(
            is_confirmed_positive_histogram_expansion([0.10, 0.20, 0.35])
        )

    def test_negative_histogram_improvement_is_not_positive_expansion(self):
        self.assertFalse(
            is_confirmed_positive_histogram_expansion([-1.72, -1.16, -0.24])
        )

    def test_two_positive_bars_after_crossover_confirm_continuation(self):
        self.assertTrue(
            is_confirmed_positive_histogram_expansion([-0.10, 0.05, 0.15])
        )

    def test_one_bar_improvement_does_not_override_three_bar_pattern(self):
        self.assertFalse(
            is_confirmed_positive_histogram_expansion([0.30, 0.10, 0.20])
        )

    def test_positive_contraction_is_cooling(self):
        self.assertTrue(
            is_sustained_positive_histogram_contraction([0.35, 0.20, 0.10])
        )

    def test_contraction_that_ends_negative_is_not_positive_cooling(self):
        self.assertFalse(
            is_sustained_positive_histogram_contraction([0.10, 0.05, -0.01])
        )


if __name__ == "__main__":
    unittest.main()
