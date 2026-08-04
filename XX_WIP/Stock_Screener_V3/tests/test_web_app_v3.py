from __future__ import annotations

import unittest

import web_app_v3


class WebAppV3RenderTests(unittest.TestCase):
    def test_results_table_marks_bear_crossover_as_exit_review(self) -> None:
        html = web_app_v3.render_results_table(
            (
                {
                    "Symbol": "AAA",
                    "CandidateState": "PRE_BEAR_CROSSOVER",
                    "CandidateClass": "SELECTED",
                    "StageFamily": "CROSSOVER",
                    "TotalScore": "81.0",
                },
            )
        )

        self.assertIn("ReviewIntent", html)
        self.assertIn("Exit / preservation", html)
        self.assertIn('class="row-exit"', html)
        self.assertIn('class="chip exit"', html)

    def test_review_split_counts_entry_exit_and_bear_risk_separately(self) -> None:
        html = web_app_v3.render_review_split(
            (
                {"CandidateState": "PRE_BULL_CROSSOVER"},
                {"CandidateState": "PRE_BEAR_CROSSOVER"},
                {"CandidateState": "BEARISH_DIVERGENCE"},
            )
        )

        self.assertIn("Bullish entry / re-entry", html)
        self.assertIn("Exit / preservation", html)
        self.assertIn("Bearish risk review", html)
        self.assertIn('<div class="intent-card entry"><span class="intent-count">1</span>', html)
        self.assertIn('<div class="intent-card exit"><span class="intent-count">1</span>', html)
        self.assertIn('<div class="intent-card bear"><span class="intent-count">1</span>', html)

    def test_results_table_groups_by_family_and_sorts_by_weighted_score(self) -> None:
        html = web_app_v3.render_results_table(
            (
                {"Symbol": "LOW", "StageFamily": "CROSSOVER", "CandidateState": "PRE_BULL_CROSSOVER", "WeightedScore": "60"},
                {"Symbol": "MID", "StageFamily": "MOMENTUM_SETUP", "CandidateState": "BULL_PULLBACK_REENTRY", "WeightedScore": "70"},
                {"Symbol": "HIGH", "StageFamily": "CROSSOVER", "CandidateState": "PRE_BEAR_CROSSOVER", "WeightedScore": "90"},
            )
        )

        self.assertIn("CROSSOVER | 2 rows | sorted by WeightedScore descending", html)
        self.assertIn("MOMENTUM_SETUP | 1 rows | sorted by WeightedScore descending", html)
        self.assertLess(html.index("HIGH"), html.index("LOW"))
        self.assertLess(html.index("LOW"), html.index("MOMENTUM_SETUP | 1 rows"))

    def test_results_table_does_not_truncate_after_one_hundred_rows(self) -> None:
        rows = tuple(
            {
                "Symbol": f"SYM{index:03d}",
                "StageFamily": "CROSSOVER",
                "CandidateState": "PRE_BULL_CROSSOVER",
                "WeightedScore": str(index),
            }
            for index in range(101)
        )

        html = web_app_v3.render_results_table(rows)

        self.assertIn("SYM000", html)
        self.assertIn("SYM100", html)


if __name__ == "__main__":
    unittest.main()
