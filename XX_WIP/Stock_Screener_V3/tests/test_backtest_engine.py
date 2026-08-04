from __future__ import annotations

from datetime import date
import unittest

import pandas as pd

from stock_screener_v3.backtest_engine import BacktestEngine, InMemoryPriceProvider, summarize_result
from stock_screener_v3.models import (
    BacktestRunConfig,
    CandidateClass,
    PriceDataBundle,
    ReviewPriority,
    ScoreResult,
    StageEvaluation,
    UniverseRecord,
)
from stock_screener_v3.regime_config import RegimeBenchmarkConfig


class SymbolListEvaluator:
    def __init__(self, selected_symbols: set[str], cutoff_date: date):
        self.selected_symbols = selected_symbols
        self.cutoff_date = cutoff_date

    def evaluate(self, record: UniverseRecord, prices: PriceDataBundle) -> StageEvaluation:
        self.assert_no_future_rows(prices)
        selected = record.yahoo_symbol in self.selected_symbols
        return StageEvaluation(
            symbol=record.yahoo_symbol,
            candidate_state="MOCK_SELECTED" if selected else "STATUS_QUO",
            candidate_class=CandidateClass.SELECTED if selected else CandidateClass.STATUS_QUO,
            review_priority=ReviewPriority.B if selected else ReviewPriority.NONE,
            confidence="MEDIUM" if selected else "LOW",
            score=ScoreResult(total_score=75.0 if selected else 0.0),
            reason_codes=("MOCK_ROUTE",) if selected else ("MOCK_NO_SIGNAL",),
        )

    def assert_no_future_rows(self, prices: PriceDataBundle) -> None:
        max_date = pd.Timestamp(prices.daily.index.max()).date()
        if max_date > self.cutoff_date:
            raise AssertionError("Evaluator received future rows.")


class BacktestEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.records = [
            UniverseRecord(symbol="AAA", yahoo_symbol="AAA", sector="Technology", exchange="NASDAQ"),
            UniverseRecord(symbol="BBB", yahoo_symbol="BBB", sector="Energy", exchange="NYSE"),
            UniverseRecord(symbol="CCC", yahoo_symbol="CCC", sector="Industrials", exchange="NYSE"),
        ]
        index = pd.to_datetime(["2026-02-10", "2026-02-11", "2026-02-12", "2026-02-13", "2026-02-18"])
        self.provider = InMemoryPriceProvider(
            {
                "AAA": pd.DataFrame({"High": [101.0, 102.0, 104.0, 105.0, 107.0], "Low": [99.0, 100.0, 102.0, 103.0, 105.0], "Close": [100.0, 101.0, 103.0, 104.0, 106.0]}, index=index),
                "BBB": pd.DataFrame({"High": [51.0, 50.0, 49.0, 48.0, 47.0], "Low": [49.0, 48.0, 47.0, 46.0, 45.0], "Close": [50.0, 49.0, 48.0, 47.0, 46.0]}, index=index),
                "CCC": pd.DataFrame({"High": [21.0, 21.0, 21.0, 22.0, 23.0], "Low": [19.0, 19.0, 19.0, 20.0, 21.0], "Close": [20.0, 20.0, 20.0, 21.0, 22.0]}, index=index),
                "MKT": pd.DataFrame({"Open": [90.0, 91.0, 92.0, 93.0, 94.0], "High": [91.0, 92.0, 93.0, 94.0, 95.0], "Low": [89.0, 90.0, 91.0, 92.0, 93.0], "Close": [90.0, 91.0, 92.0, 93.0, 94.0], "Volume": [1_000_000] * 5}, index=index),
                "SECT": pd.DataFrame({"Open": [80.0, 81.0, 82.0, 83.0, 84.0], "High": [81.0, 82.0, 83.0, 84.0, 85.0], "Low": [79.0, 80.0, 81.0, 82.0, 83.0], "Close": [80.0, 81.0, 82.0, 83.0, 84.0], "Volume": [1_000_000] * 5}, index=index),
            }
        )

    def test_backtest_engine_reports_candidate_density_and_forward_returns(self) -> None:
        engine = BacktestEngine(
            self.provider,
            SymbolListEvaluator({"AAA", "CCC"}, cutoff_date=date(2026, 2, 11)),
        )
        config = BacktestRunConfig(
            universe_file="memory",
            d_date=date(2026, 2, 11),
            stage_families=("MOCK",),
            forward_days=(1, 2),
        )

        result = engine.run(self.records, config)

        self.assertEqual(result.symbols_attempted, 3)
        self.assertEqual(result.symbols_processed, 3)
        self.assertEqual(result.candidates_found, 2)
        self.assertAlmostEqual(result.candidate_density, 2 / 3)
        aaa = next(row for row in result.detail_rows if row["Symbol"] == "AAA")
        self.assertEqual(aaa["CandidateClass"], "SELECTED")
        self.assertEqual(aaa["OutcomeCategory"], "POSITIVE_FOLLOW_THROUGH")
        self.assertEqual(aaa["FailureCategory"], "")
        self.assertEqual(aaa["DPlus1ReturnPct"], 1.9802)
        self.assertEqual(aaa["DPlus1WorstLowReturnPct"], 0.9901)
        self.assertEqual(aaa["DPlus1BestHighReturnPct"], 2.9703)
        self.assertEqual(aaa["DPlus2ReturnPct"], 2.9703)
        self.assertEqual(aaa["DPlus2WorstLowReturnPct"], 0.9901)
        self.assertEqual(aaa["DPlus2BestHighReturnPct"], 3.9604)

    def test_backtest_engine_applies_sector_filter_before_evaluation(self) -> None:
        engine = BacktestEngine(
            self.provider,
            SymbolListEvaluator({"AAA", "CCC"}, cutoff_date=date(2026, 2, 11)),
        )
        config = BacktestRunConfig(
            universe_file="memory",
            d_date=date(2026, 2, 11),
            stage_families=("MOCK",),
            sector_filters=("Technology",),
        )

        result = engine.run(self.records, config)

        self.assertEqual(result.symbols_attempted, 1)
        self.assertEqual(result.symbols_processed, 1)
        self.assertEqual(result.candidates_found, 1)
        self.assertEqual(result.detail_rows[0]["Sector"], "Technology")

    def test_summarize_result_reports_hit_rates(self) -> None:
        engine = BacktestEngine(
            self.provider,
            SymbolListEvaluator({"AAA", "BBB"}, cutoff_date=date(2026, 2, 11)),
        )
        config = BacktestRunConfig(
            universe_file="memory",
            d_date=date(2026, 2, 11),
            stage_families=("MOCK",),
            forward_days=(1,),
        )

        summary = summarize_result(engine.run(self.records, config))

        self.assertEqual(summary["candidates_found"], 2)
        self.assertEqual(summary["d_plus_1_evaluated"], 2)
        self.assertEqual(summary["d_plus_1_positive"], 1)
        self.assertAlmostEqual(summary["d_plus_1_hit_rate"], 1 / 2)
        self.assertEqual(summary["d_plus_1_average_return_pct"], -0.0303)
        self.assertEqual(summary["d_plus_1_median_return_pct"], -0.0303)
        self.assertEqual(summary["failure_categories"], {"STRUCTURE_FAILURE": 1})
        self.assertEqual(summary["score_buckets"], {"70-79": 2})
        self.assertEqual(summary["score_bucket_outcomes"]["70-79"]["d_plus_1_positive"], 1)
        self.assertEqual(summary["sector_outcomes"]["Technology"]["d_plus_1_positive"], 1)
        self.assertEqual(summary["sector_outcomes"]["Energy"]["d_plus_1_positive"], 0)
        self.assertEqual(summary["review_priority_outcomes"]["B"]["candidates"], 2)

    def test_backtest_engine_loads_configured_benchmarks(self) -> None:
        class BenchmarkEchoEvaluator:
            def evaluate(self, record: UniverseRecord, prices: PriceDataBundle) -> StageEvaluation:
                return StageEvaluation(
                    symbol=record.yahoo_symbol,
                    candidate_state="STATUS_QUO",
                    candidate_class=CandidateClass.STATUS_QUO,
                    review_priority=ReviewPriority.NONE,
                    confidence="LOW",
                    score=ScoreResult(total_score=0.0),
                    diagnostics={
                        "BenchmarkKeys": ",".join(sorted(prices.benchmarks.keys())),
                        "MarketRows": len(prices.benchmarks["market"]),
                        "SectorRows": len(prices.benchmarks["sector"]),
                    },
                )

        engine = BacktestEngine(
            self.provider,
            BenchmarkEchoEvaluator(),
            regime_config=RegimeBenchmarkConfig(
                market_benchmarks_by_exchange={"NASDAQ": "MKT"},
                sector_benchmarks={"TECHNOLOGY": "SECT"},
            ),
        )
        config = BacktestRunConfig(
            universe_file="memory",
            d_date=date(2026, 2, 11),
            stage_families=("MOCK",),
        )

        result = engine.run([self.records[0]], config)

        self.assertEqual(result.detail_rows[0]["BenchmarkKeys"], "market,sector")
        self.assertEqual(result.detail_rows[0]["MarketRows"], 2)
        self.assertEqual(result.detail_rows[0]["SectorRows"], 2)


if __name__ == "__main__":
    unittest.main()
