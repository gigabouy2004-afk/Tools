from __future__ import annotations

from datetime import date
from pathlib import Path
import tempfile
import unittest

import pandas as pd

from stock_screener_v3.backtest_engine import InMemoryPriceProvider
from stock_screener_v3.models import CandidateClass, PriceDataBundle, ReviewPriority, ScoreResult, StageEvaluation, UniverseRecord
from stock_screener_v3.runner import run_backtest, run_backtest_pack


class AlwaysSelectedEvaluator:
    def evaluate(self, record: UniverseRecord, prices: PriceDataBundle) -> StageEvaluation:
        return StageEvaluation(
            symbol=record.yahoo_symbol,
            candidate_state="PRE_BULL_CROSSOVER",
            candidate_class=CandidateClass.SELECTED,
            review_priority=ReviewPriority.B,
            confidence="MEDIUM",
            score=ScoreResult(total_score=70.0, route_score=30.0),
            reason_codes=("TEST_ROUTE",),
            diagnostics={"MACD_1D_CrossoverState": "BULL_CROSS", "WeightedScore": 70.0},
        )


class RunnerTests(unittest.TestCase):
    def test_run_backtest_writes_separate_csv_summary_and_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            universe = root / "universe.csv"
            universe.write_text("Symbol,Exchange,Sector\nAAA,NASDAQ,Technology\n", encoding="utf-8")
            index = pd.to_datetime(["2026-02-10", "2026-02-11", "2026-02-12"])
            provider = InMemoryPriceProvider(
                {"AAA": pd.DataFrame({"Close": [100.0, 101.0, 103.0]}, index=index)}
            )

            run = run_backtest(
                workspace_root=root,
                universe_file=universe,
                d_date=date(2026, 2, 11),
                forward_days=(1,),
                price_provider=provider,
                evaluator=AlwaysSelectedEvaluator(),
            )

            self.assertTrue(run.paths.details_output.exists())
            self.assertTrue(run.paths.summary_output.exists())
            self.assertTrue(run.paths.log_file.exists())
            self.assertNotEqual(run.paths.details_output, run.paths.log_file)
            self.assertIn("PRE_BULL_CROSSOVER", run.paths.details_output.read_text(encoding="utf-8"))
            self.assertIn("V3 run completed", run.paths.log_file.read_text(encoding="utf-8"))

    def test_run_backtest_pack_writes_aggregate_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            universe = root / "universe.csv"
            universe.write_text("Symbol,Exchange,Sector\nAAA,NASDAQ,Technology\n", encoding="utf-8")
            index = pd.to_datetime(["2026-02-10", "2026-02-11", "2026-02-12", "2026-03-10", "2026-03-11", "2026-03-12"])
            provider = InMemoryPriceProvider(
                {"AAA": pd.DataFrame({"Close": [100.0, 101.0, 103.0, 104.0, 105.0, 106.0]}, index=index)}
            )

            run = run_backtest_pack(
                workspace_root=root,
                universe_file=universe,
                d_dates=(date(2026, 2, 11), date(2026, 3, 11)),
                forward_days=(1,),
                run_label="pack_test",
                price_provider=provider,
                evaluator=AlwaysSelectedEvaluator(),
            )

            self.assertEqual(len(run.runs), 2)
            self.assertTrue(run.summary_output.exists())
            self.assertIn("V3 Multi-Date Backtest Summary", run.summary_output.read_text(encoding="utf-8"))
            self.assertTrue((root / "validation" / "runs" / "pack_test_20260211_details.csv").exists())
            self.assertTrue((root / "validation" / "runs" / "pack_test_20260311_details.csv").exists())


if __name__ == "__main__":
    unittest.main()

