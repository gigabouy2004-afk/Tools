import unittest

import pandas as pd

from Backtest_Momentum_Detector_V8_Directional import directional_metrics, select_signal_date


class V8DirectionalPersistenceTests(unittest.TestCase):
    def test_directional_metrics_use_d_close_as_primary_baseline(self):
        index = pd.bdate_range("2026-04-30", periods=10)
        frame = pd.DataFrame(
            {
                "Open": [100, 101, 102, 103, 104, 105, 106, 107, 108, 109],
                "Close": [100, 102, 101, 104, 103, 106, 105, 107, 108, 110],
            },
            index=index,
        )
        result = directional_metrics(frame, index[0], (5, 8))
        self.assertTrue(result["D1_Direction_Pass"])
        self.assertAlmostEqual(result["D1_Close_vs_D_Close_Pct"], 2.0)
        self.assertAlmostEqual(result["D1_Close_vs_D1_Open_Pct"], (102 / 101 - 1) * 100)
        self.assertTrue(result["D5_Persistence_Pass"])
        self.assertTrue(result["D8_Persistence_Pass"])

    def test_date_selection_uses_active_count_and_earliest_tie(self):
        rows = pd.DataFrame(
            [
                {"Signal_Date": "2026-04-01", "Final_Decision": "MOMENTUM_ACTIVE"},
                {"Signal_Date": "2026-04-01", "Final_Decision": "REJECT"},
                {"Signal_Date": "2026-04-02", "Final_Decision": "MOMENTUM_ACTIVE"},
                {"Signal_Date": "2026-04-02", "Final_Decision": "MOMENTUM_ACTIVE"},
                {"Signal_Date": "2026-04-03", "Final_Decision": "MOMENTUM_ACTIVE"},
                {"Signal_Date": "2026-04-03", "Final_Decision": "MOMENTUM_ACTIVE"},
            ]
        )
        selected, count = select_signal_date(rows, "2026-04")
        self.assertEqual(selected.date().isoformat(), "2026-04-02")
        self.assertEqual(count, 2)


if __name__ == "__main__":
    unittest.main()
