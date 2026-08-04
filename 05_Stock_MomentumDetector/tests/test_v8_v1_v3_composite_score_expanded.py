import unittest

import pandas as pd

import Backtest_V8_V1_V3_Composite_Score_Expanded as expanded


class V1V3CompositeScoreExpandedTests(unittest.TestCase):
    def test_scope_requires_signal_dates_history_and_forward_horizon(self):
        index = pd.bdate_range("2022-01-03", periods=320)
        frame = pd.DataFrame(
            {
                "Open": 100.0,
                "High": 101.0,
                "Low": 99.0,
                "Close": 100.5,
                "Volume": 1_000_000,
            },
            index=index,
        )
        signal = index[305].date().isoformat()
        complete, reason = expanded.frame_has_complete_scope(
            frame, [signal], [1, 5, 8], 300
        )
        self.assertTrue(complete, reason)
        missing, _ = expanded.frame_has_complete_scope(
            frame, ["2024-01-02"], [1, 5, 8], 300
        )
        self.assertFalse(missing)

    def test_score_analysis_uses_combined_score_thresholds(self):
        rows = []
        for score, returns in [(10, (-1.0, -2.0, -3.0)), (20, (1.0, 2.0, 3.0))]:
            rows.append(
                {
                    "Profile": "V1",
                    "Sector": "Technology",
                    "Foundation_Eligible": True,
                    "DMI_Dominance_Pass": True,
                    "Total_Momentum_Score": score,
                    "D1_Return_Pct": returns[0],
                    "D5_Return_Pct": returns[1],
                    "D8_Return_Pct": returns[2],
                }
            )
        exact, thresholds, correlations = expanded.score_analysis(
            rows, ["V1"], ["Technology"], [1, 5, 8]
        )
        combined = [
            row
            for row in thresholds
            if row["Sector"] == "ALL" and row["Minimum_Score"] == 20
        ][0]
        self.assertEqual(combined["Rows"], 1)
        self.assertEqual(combined["D1_Positive_Rate_Pct"], 100.0)
        self.assertEqual({row["Exact_Score"] for row in exact}, {10, 20})
        self.assertEqual(len(correlations), 2)


if __name__ == "__main__":
    unittest.main()
