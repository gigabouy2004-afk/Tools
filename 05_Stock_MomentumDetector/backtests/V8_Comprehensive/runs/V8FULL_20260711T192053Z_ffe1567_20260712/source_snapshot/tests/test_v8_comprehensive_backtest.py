import unittest

import pandas as pd

import Backtest_Momentum_Detector_V8 as backtest


class V8ComprehensiveBacktestTests(unittest.TestCase):
    def price_frame(self, periods=80):
        index = pd.bdate_range("2026-04-01", periods=periods)
        values = [100.0 + value for value in range(periods)]
        return pd.DataFrame(
            {
                "Open": values,
                "High": [value + 1 for value in values],
                "Low": [value - 1 for value in values],
                "Close": [value + 0.5 for value in values],
                "Volume": [1_000_000] * periods,
            },
            index=index,
        )

    def test_parse_quarter(self):
        label, start, end = backtest.parse_quarter("2026Q2")
        self.assertEqual(label, "2026Q2")
        self.assertEqual(start.date().isoformat(), "2026-04-01")
        self.assertEqual(end.date().isoformat(), "2026-06-30")

    def test_forward_outcome_uses_next_open_and_horizon_close(self):
        frame = self.price_frame()
        signal_date = frame.index[0]
        result = backtest.calculate_outcome(frame, signal_date, 5)
        expected = ((frame.iloc[5]["Close"] / frame.iloc[1]["Open"]) - 1) * 100
        self.assertAlmostEqual(result["Return_Pct"], expected)
        self.assertEqual(result["Entry_Date"], frame.index[1].date().isoformat())
        self.assertEqual(result["Exit_Date"], frame.index[5].date().isoformat())

    def test_random_date_is_reproducible_and_keeps_exit_in_quarter(self):
        frame = self.price_frame()
        _, start, end = backtest.parse_quarter("2026Q2")
        eligible = backtest.eligible_random_dates(frame, start, end, 21)
        first = backtest.deterministic_date(eligible, 20260712, "TEST")
        second = backtest.deterministic_date(eligible, 20260712, "TEST")
        self.assertEqual(first, second)
        outcome = backtest.calculate_outcome(frame, first, 21)
        self.assertLessEqual(pd.Timestamp(outcome["Exit_Date"]), end)


if __name__ == "__main__":
    unittest.main()
