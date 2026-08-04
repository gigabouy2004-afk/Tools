import unittest

import pandas as pd

import Backtest_V8_MACD_Foundation_Comparison_Expanded as comparison


class V8MACDComparisonExpandedTests(unittest.TestCase):
    def test_classification_counts_nonpositive_selected_as_false_positive(self):
        rows = [
            {"Foundation_Eligible": True, "Health_Qualified": True, "D1_Return_Pct": 1.0, "D3_Return_Pct": 2.0},
            {"Foundation_Eligible": True, "Health_Qualified": True, "D1_Return_Pct": 0.0, "D3_Return_Pct": -1.0},
            {"Foundation_Eligible": False, "Health_Qualified": False, "D1_Return_Pct": 1.0, "D3_Return_Pct": 1.0},
        ]
        metrics = comparison.selection_metrics(rows, "Foundation_Eligible", [1, 3])
        self.assertEqual(metrics["Selected"], 2)
        self.assertEqual(metrics["D1_False_Positive"], 1)
        self.assertEqual(metrics["D1_False_Negative"], 1)
        self.assertEqual(metrics["D1_Selected_Positive_Rate_Pct"], 50.0)

    def test_transition_labels_are_symmetric(self):
        self.assertEqual(comparison.transition_label(True, True), "BOTH")
        self.assertEqual(comparison.transition_label(True, False), "STANDARD_ONLY")
        self.assertEqual(comparison.transition_label(False, True), "FIBONACCI_ONLY")
        self.assertEqual(comparison.transition_label(False, False), "NEITHER")


if __name__ == "__main__":
    unittest.main()
