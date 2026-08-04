import unittest

import pandas as pd

from Validate_Momentum_Detector_V8_Foundation import calculate_outcome, recompute_foundation


class V8FoundationBacktestTests(unittest.TestCase):
    def price_frame(self, values):
        index = pd.bdate_range("2024-01-01", periods=len(values))
        return pd.DataFrame(
            {
                "Open": values,
                "High": [value + 1 for value in values],
                "Low": [value - 1 for value in values],
                "Close": [value + 0.5 for value in values],
                "Volume": [1_000_000] * len(values),
            },
            index=index,
        )

    def test_independent_foundation_is_prefix_only(self):
        frame = self.price_frame([100 + value * 0.3 for value in range(320)])
        cutoff = frame.index[280]
        before = recompute_foundation(frame.loc[:cutoff], cutoff, 8, 21, 5)
        changed = frame.copy()
        changed.loc[changed.index > cutoff, "Close"] = 10_000
        after = recompute_foundation(changed, cutoff, 8, 21, 5)
        self.assertEqual(before, after)

    def test_independent_outcome_uses_next_open_and_horizon_close(self):
        frame = self.price_frame([100 + value for value in range(30)])
        result = calculate_outcome(frame, frame.index[0], 5)
        expected = ((frame.iloc[5]["Close"] / frame.iloc[1]["Open"]) - 1) * 100
        self.assertAlmostEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
