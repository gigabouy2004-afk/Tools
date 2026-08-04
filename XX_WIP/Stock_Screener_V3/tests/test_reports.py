from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
import tempfile
import unittest

from stock_screener_v3.models import BacktestResult, BacktestRunConfig
from stock_screener_v3.output_contracts import V2_COMPAT_EXPORT_COLUMNS
from stock_screener_v3.reports import (
    render_cross_sector_calibration_markdown,
    render_integrated_calibration_markdown,
    render_multi_date_summary_markdown,
    render_stage_family_calibration_markdown,
    render_summary_markdown,
    render_symbol_failure_markdown,
    write_detail_csv,
    write_summary_markdown,
)


class ReportTests(unittest.TestCase):
    def test_render_summary_markdown_includes_density_and_forward_table(self) -> None:
        result = BacktestResult(
            config=BacktestRunConfig(universe_file="memory", d_date=date(2026, 2, 11), stage_families=("MOCK",), forward_days=(1,)),
            generated_at=datetime(2026, 6, 2),
            symbols_attempted=2,
            symbols_processed=2,
            symbols_skipped=0,
            candidates_found=1,
            detail_rows=(
                {
                    "Symbol": "AAA",
                    "CandidateClass": "SELECTED",
                    "StageFamily": "CROSSOVER",
                    "TotalScore": 72.0,
                    "RiskTags": "BELOW_EMA200",
                    "DPlus1ReturnPct": 2.0,
                    "DPlus1WorstLowReturnPct": -3.0,
                    "DPlus1BestHighReturnPct": 4.0,
                    "CandidateStateRaw": "PRE_BULL_CROSSOVER",
                    "RankingCandidateStates": "CROSSOVER:PRE_BULL_CROSSOVER|MOMENTUM_SETUP:STATUS_QUO|DIVERGENCE:BULLISH_DIVERGENCE",
                },
                {"Symbol": "BBB", "CandidateClass": "STATUS_QUO", "DPlus1ReturnPct": -1.0},
            ),
        )

        markdown = render_summary_markdown(result)

        self.assertIn("Candidate density: 0.5000", markdown)
        self.assertIn("| D+1 | 1 | 1 | 100.00% |", markdown)
        self.assertIn("2.00%", markdown)
        self.assertIn("## Score Buckets", markdown)
        self.assertIn("| 70-79 | 1 |", markdown)
        self.assertIn("## Score Bucket Outcomes D+1", markdown)
        self.assertIn("## Stage Family Outcomes D+1", markdown)
        self.assertIn("| CROSSOVER | 1 | 1 | 1 | 100.00% | 2.00% | 2.00% |", markdown)
        self.assertIn("## Stage Family Path Outcomes D+1", markdown)
        self.assertIn("| CROSSOVER | 1 | 1 | -3.00% | -3.00% | 4.00% | 4.00% |", markdown)
        self.assertIn("## Candidate State Path Outcomes D+1", markdown)
        self.assertIn("| PRE_BULL_CROSSOVER | 1 | 1 | -3.00% | -3.00% | 4.00% | 4.00% |", markdown)
        self.assertIn("## Sector Outcomes D+1", markdown)
        self.assertIn("## Review Priority Outcomes D+1", markdown)
        self.assertIn("## Risk Tag Outcomes D+1", markdown)
        self.assertIn("| BELOW_EMA200 | 1 | 1 | 1 | 100.00% | 2.00% | 2.00% |", markdown)
        self.assertIn("## Ranking Collision Buckets", markdown)
        self.assertIn("| CROSSOVER+DIVERGENCE | 1 |", markdown)

    def test_render_summary_markdown_includes_failure_categories(self) -> None:
        result = BacktestResult(
            config=BacktestRunConfig(universe_file="memory", d_date=date(2026, 2, 11), stage_families=("MOCK",), forward_days=(1,)),
            generated_at=datetime(2026, 6, 2),
            symbols_attempted=1,
            symbols_processed=1,
            symbols_skipped=0,
            candidates_found=1,
            detail_rows=(
                {
                    "Symbol": "AAA",
                    "CandidateClass": "SELECTED",
                    "TotalScore": 65.0,
                    "FailureCategory": "PARTICIPATION_FAILURE",
                    "DPlus1ReturnPct": -2.0,
                },
            ),
        )

        markdown = render_summary_markdown(result)

        self.assertIn("## Failure Categories", markdown)
        self.assertIn("- PARTICIPATION_FAILURE: 1", markdown)

    def test_render_multi_date_summary_markdown_includes_aggregate_metrics(self) -> None:
        first = BacktestResult(
            config=BacktestRunConfig(universe_file="memory", d_date=date(2026, 2, 11), stage_families=("MOCK",), forward_days=(1,)),
            generated_at=datetime(2026, 6, 2),
            symbols_attempted=1,
            symbols_processed=1,
            symbols_skipped=0,
            candidates_found=1,
            detail_rows=(
                {
                    "Symbol": "AAA",
                    "CandidateClass": "SELECTED",
                    "StageFamily": "CROSSOVER",
                    "CandidateStateRaw": "PRE_BEAR_CROSSOVER",
                    "DPlus1ReturnPct": 2.0,
                    "DPlus1WorstLowReturnPct": -4.0,
                    "DPlus1BestHighReturnPct": 5.0,
                    "RankingCandidateStates": "CROSSOVER:PRE_BULL_CROSSOVER|MOMENTUM_SETUP:STATUS_QUO",
                },
            ),
        )
        second = BacktestResult(
            config=BacktestRunConfig(universe_file="memory", d_date=date(2026, 3, 11), stage_families=("MOCK",), forward_days=(1,)),
            generated_at=datetime(2026, 6, 2),
            symbols_attempted=1,
            symbols_processed=1,
            symbols_skipped=0,
            candidates_found=1,
            detail_rows=(
                {
                    "Symbol": "BBB",
                    "CandidateClass": "WATCH",
                    "StageFamily": "MOMENTUM_SETUP",
                    "CandidateStateRaw": "BULL_PULLBACK_REENTRY",
                    "DPlus1ReturnPct": -1.0,
                    "DPlus1WorstLowReturnPct": -6.0,
                    "DPlus1BestHighReturnPct": 1.0,
                    "RankingCandidateStates": "CROSSOVER:STATUS_QUO|MOMENTUM_SETUP:BULL_PULLBACK_REENTRY",
                },
            ),
        )

        markdown = render_multi_date_summary_markdown((first, second))

        self.assertIn("# V3 Multi-Date Backtest Summary", markdown)
        self.assertIn("| 2026-02-11 | 1 | 0 | 1 | 1.0000 |", markdown)
        self.assertIn("| D+1 | 2 | 1 | 50.00% | 0.50% | 0.50% |", markdown)
        self.assertIn("## Aggregate Forward Path Outcomes", markdown)
        self.assertIn("| D+1 | 2 | -5.00% | -5.00% | 3.00% | 3.00% |", markdown)
        self.assertIn("## Stage Family Path Outcomes D+1", markdown)
        self.assertIn("| CROSSOVER | 1 | 1 | -4.00% | -4.00% | 5.00% | 5.00% |", markdown)
        self.assertIn("| MOMENTUM_SETUP | 1 | 1 | -6.00% | -6.00% | 1.00% | 1.00% |", markdown)
        self.assertIn("## Candidate State Path Outcomes D+1", markdown)
        self.assertIn("| PRE_BEAR_CROSSOVER | 1 | 1 | -4.00% | -4.00% | 5.00% | 5.00% |", markdown)
        self.assertIn("## Ranking Collision Buckets", markdown)
        self.assertIn("| CROSSOVER | 1 |", markdown)
        self.assertIn("| MOMENTUM_SETUP | 1 |", markdown)

    def test_write_reports_creates_files(self) -> None:
        result = BacktestResult(
            config=BacktestRunConfig(universe_file="memory", d_date=date(2026, 2, 11), stage_families=("MOCK",), forward_days=(1,)),
            generated_at=datetime(2026, 6, 2),
            symbols_attempted=1,
            symbols_processed=1,
            symbols_skipped=0,
            candidates_found=1,
            detail_rows=({"Symbol": "AAA", "CandidateClass": "SELECTED", "DPlus1ReturnPct": 2.0},),
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            detail = Path(tmpdir) / "details.csv"
            summary = Path(tmpdir) / "summary.md"

            write_detail_csv(result, detail)
            write_summary_markdown(result, summary)

            self.assertIn("Symbol", detail.read_text(encoding="utf-8"))
            self.assertIn("V3 Backtest Summary", summary.read_text(encoding="utf-8"))

    def test_detail_csv_preserves_v2_compatible_header_order(self) -> None:
        result = BacktestResult(
            config=BacktestRunConfig(universe_file="memory", d_date=date(2026, 2, 11), stage_families=("MOCK",)),
            generated_at=datetime(2026, 6, 2),
            symbols_attempted=1,
            symbols_processed=1,
            symbols_skipped=0,
            candidates_found=1,
            detail_rows=({"Symbol": "AAA", "CandidateClass": "SELECTED", "CustomDiagnostic": "kept"},),
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            detail = Path(tmpdir) / "details.csv"

            write_detail_csv(result, detail)

            header = detail.read_text(encoding="utf-8").splitlines()[0].split(",")
            self.assertEqual(V2_COMPAT_EXPORT_COLUMNS, header[: len(V2_COMPAT_EXPORT_COLUMNS)])
            self.assertIn("CandidateClass", header)
            self.assertIn("CustomDiagnostic", header)

    def test_detail_csv_writes_headers_even_when_no_rows(self) -> None:
        result = BacktestResult(
            config=BacktestRunConfig(universe_file="memory", d_date=date(2026, 2, 11), stage_families=("MOCK",)),
            generated_at=datetime(2026, 6, 2),
            symbols_attempted=1,
            symbols_processed=1,
            symbols_skipped=0,
            candidates_found=0,
            detail_rows=(),
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            detail = Path(tmpdir) / "empty.csv"

            write_detail_csv(result, detail)

            header = detail.read_text(encoding="utf-8").splitlines()[0].split(",")
            self.assertEqual(V2_COMPAT_EXPORT_COLUMNS, header[: len(V2_COMPAT_EXPORT_COLUMNS)])

    def test_render_cross_sector_calibration_markdown_from_detail_csvs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            detail = Path(tmpdir) / "sector_pack_20260211_details.csv"
            detail.write_text(
                "\n".join(
                    [
                        "Symbol,Sector,CandidateStateRaw,CandidateState,CandidateClass,ReviewPriority,CrossoverOpportunityType,DPlus20ReturnPct,DPlus20WorstLowReturnPct,DPlus20BestHighReturnPct",
                        "AAA,Technology,PRE_BEAR_CROSSOVER,PRE_BEAR_CROSSOVER,SELECTED,A,BEARISH_NEAR_TRANSITION,-5,-12,4",
                        "BBB,Technology,PRE_BEAR_CROSSOVER,PRE_BEAR_CROSSOVER,WATCH,B,BEARISH_BELOW_SIGNAL_DETERIORATING,3,-8,9",
                        "CCC,Utilities,STATUS_QUO,STATUS_QUO,STATUS_QUO,NONE,NO_CROSSOVER_ROUTE,-1,-2,1",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            markdown = render_cross_sector_calibration_markdown((detail,), horizon_days=20)

            self.assertIn("# V3 Cross-Sector PRE_BEAR_CROSSOVER Calibration Report", markdown)
            self.assertIn("| Technology | 2 | 50.00% | -1.00% | -1.00% | -10.00% | -10.00% | 50.00% | 0.00% | 6.50% | 6.50% |", markdown)
            self.assertIn("## Opportunity Type Split", markdown)
            self.assertIn("| AAA |", markdown)

    def test_render_symbol_failure_markdown_reports_repeated_weak_symbols(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            first = Path(tmpdir) / "pack_20260211_details.csv"
            second = Path(tmpdir) / "pack_20260311_details.csv"
            header = "Symbol,Sector,CandidateStateRaw,CandidateClass,ReviewPriority,ReasonCodes,DPlus20ReturnPct,DPlus20WorstLowReturnPct,DPlus20BestHighReturnPct"
            first.write_text(
                "\n".join(
                    [
                        header,
                        "AAA,Basic Materials,PRE_BULL_CROSSOVER,SELECTED,A,DAILY_MACD_NEAR_BULL_TRANSITION,-10,-15,2",
                        "BBB,Basic Materials,PRE_BEAR_CROSSOVER,WATCH,B,DAILY_MACD_BEAR_CROSS,4,-3,8",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            second.write_text(
                "\n".join(
                    [
                        header,
                        "AAA,Basic Materials,PRE_BEAR_CROSSOVER,WATCH,B,DAILY_MACD_NEAR_BEAR_TRANSITION,-6,-11,1",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            markdown = render_symbol_failure_markdown((first, second), horizon_days=20, limit=5)

            self.assertIn("# V3 Symbol-Level Failure Report", markdown)
            self.assertIn("| 2026-02-11 | AAA | Basic Materials | PRE_BULL_CROSSOVER | SELECTED | A | -10.00% | -15.00% | 2.00% |", markdown)
            self.assertIn("## Repeated Weak Symbols", markdown)
            self.assertIn("| AAA | 2 | -8.00% | -10.00% | -6.00% | 2026-02-11, 2026-03-11 |", markdown)

    def test_render_symbol_failure_markdown_applies_stage_family_filter(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            detail = Path(tmpdir) / "pack_20260211_details.csv"
            detail.write_text(
                "\n".join(
                    [
                        "Symbol,Sector,StageFamily,CandidateStateRaw,CandidateClass,ReviewPriority,ReasonCodes,DPlus20ReturnPct,DPlus20WorstLowReturnPct,DPlus20BestHighReturnPct",
                        "AAA,Technology,MOMENTUM_SETUP,BULL_PULLBACK_REENTRY,WATCH,B,BULL_PULLBACK_REENTRY_ROUTE,-7,-12,3",
                        "BBB,Technology,CROSSOVER,PRE_BEAR_CROSSOVER,WATCH,B,DAILY_MACD_BEAR_CROSS,-9,-10,2",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            markdown = render_symbol_failure_markdown((detail,), horizon_days=20, stage_family="MOMENTUM_SETUP")

            self.assertIn("- Stage family filter: MOMENTUM_SETUP", markdown)
            self.assertIn("| 2026-02-11 | AAA | Technology | BULL_PULLBACK_REENTRY | WATCH | B | -7.00% | -12.00% | 3.00% |", markdown)
            self.assertNotIn("PRE_BEAR_CROSSOVER", markdown)

    def test_render_stage_family_calibration_markdown_splits_divergence(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            detail = Path(tmpdir) / "sector_pack_20260211_details.csv"
            detail.write_text(
                "\n".join(
                    [
                        "Symbol,Sector,StageFamily,CandidateStateRaw,CandidateClass,ReviewPriority,DivergenceDirection,DivergenceType,DivergenceOpportunityType,ReasonCodes,DPlus20ReturnPct,DPlus20WorstLowReturnPct,DPlus20BestHighReturnPct",
                        "AAA,Misc,DIVERGENCE,BULLISH_DIVERGENCE,WATCH,B,BULLISH,REGULAR,BULLISH_REGULAR_DIVERGENCE,BULLISH_REGULAR_DIVERGENCE_ROUTE,-4,-8,5",
                        "BBB,Misc,DIVERGENCE,HIDDEN_BEARISH_DIVERGENCE,SELECTED,A,BEARISH,HIDDEN,HIDDEN_BEARISH_CONTINUATION,HIDDEN_BEARISH_DIVERGENCE_ROUTE,6,-3,9",
                        "CCC,Misc,CROSSOVER,PRE_BEAR_CROSSOVER,SELECTED,A,,,,DAILY_MACD_BEAR_CROSS,-2,-5,2",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            markdown = render_stage_family_calibration_markdown((detail,), stage_family="DIVERGENCE", horizon_days=20)

            self.assertIn("# V3 DIVERGENCE Calibration Report", markdown)
            self.assertIn("## Divergence Direction Outcomes", markdown)
            self.assertIn("| BULLISH | 1 | 0.00% | -4.00% | -4.00% | -8.00% | -8.00% | 5.00% | 5.00% |", markdown)
            self.assertIn("| HIDDEN_BEARISH_DIVERGENCE | 1 | 100.00% | 6.00% | 6.00% | -3.00% | -3.00% | 9.00% | 9.00% |", markdown)
            self.assertNotIn("PRE_BEAR_CROSSOVER", markdown)

    def test_render_stage_family_calibration_markdown_splits_momentum_setup(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            detail = Path(tmpdir) / "sector_pack_20260211_details.csv"
            detail.write_text(
                "\n".join(
                    [
                        "Symbol,Sector,StageFamily,CandidateStateRaw,CandidateClass,ReviewPriority,MomentumSetupOpportunityType,ReasonCodes,DPlus20ReturnPct,DPlus20WorstLowReturnPct,DPlus20BestHighReturnPct",
                        "AAA,Technology,MOMENTUM_SETUP,BULL_PULLBACK_REENTRY,WATCH,B,BULLISH_PULLBACK_REENTRY,BULL_PULLBACK_REENTRY_ROUTE,-7,-12,3",
                        "BBB,Technology,MOMENTUM_SETUP,BULL_CONTINUATION_MOMENTUM,SELECTED,A,BULLISH_CONTINUATION_MOMENTUM,BULL_CONTINUATION_ROUTE,8,-2,11",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            markdown = render_stage_family_calibration_markdown((detail,), stage_family="MOMENTUM_SETUP", horizon_days=20)

            self.assertIn("# V3 MOMENTUM_SETUP Calibration Report", markdown)
            self.assertIn("## Momentum Opportunity Outcomes", markdown)
            self.assertIn("| BULLISH_PULLBACK_REENTRY | 1 | 0.00% | -7.00% | -7.00% | -12.00% | -12.00% | 3.00% | 3.00% |", markdown)

    def test_render_integrated_calibration_markdown_splits_ranking_and_risk(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            detail = Path(tmpdir) / "integrated_20260211_details.csv"
            detail.write_text(
                "\n".join(
                    [
                        "Symbol,Sector,StageFamily,CandidateStateRaw,CandidateClass,ReviewPriority,RiskTags,RankingCandidateStates,DPlus20ReturnPct,DPlus20WorstLowReturnPct,DPlus20BestHighReturnPct",
                        "AAA,Technology,CROSSOVER,PRE_BEAR_CROSSOVER,SELECTED,A,,CROSSOVER:PRE_BEAR_CROSSOVER|MOMENTUM_SETUP:STATUS_QUO|DIVERGENCE:BULLISH_DIVERGENCE,-4,-8,3",
                        "BBB,Technology,MOMENTUM_SETUP,BULL_PULLBACK_REENTRY,WATCH,NEEDS_MANUAL_REVIEW,BELOW_EMA200,CROSSOVER:STATUS_QUO|MOMENTUM_SETUP:BULL_PULLBACK_REENTRY|DIVERGENCE:STATUS_QUO,5,-2,9",
                        "CCC,Technology,CROSSOVER,STATUS_QUO,STATUS_QUO,NONE,,CROSSOVER:STATUS_QUO|MOMENTUM_SETUP:STATUS_QUO|DIVERGENCE:STATUS_QUO,-1,-3,2",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            markdown = render_integrated_calibration_markdown((detail,), horizon_days=20)

            self.assertIn("# V3 Integrated Holistic Calibration Report", markdown)
            self.assertIn("## Stage Family Outcomes", markdown)
            self.assertIn("| CROSSOVER | 1 | 0.00% | -4.00% | -4.00% | -8.00% | -8.00% | 3.00% | 3.00% |", markdown)
            self.assertIn("## Risk Tag Outcomes", markdown)
            self.assertIn("| BELOW_EMA200 | 1 | 100.00% | 5.00% | 5.00% | -2.00% | -2.00% | 9.00% | 9.00% |", markdown)
            self.assertIn("## Ranking Collision Outcomes", markdown)
            self.assertIn("| CROSSOVER+DIVERGENCE | 1 | 0.00% | -4.00% | -4.00% | -8.00% | -8.00% | 3.00% | 3.00% |", markdown)
            self.assertIn("## Winner Family vs Ranking Collision", markdown)
            self.assertIn("| CROSSOVER+DIVERGENCE | CROSSOVER | 1 | 0.00% | -4.00% | -4.00% | -8.00% | -8.00% | 3.00% | 3.00% |", markdown)
            self.assertNotIn("| 2026-02-11 | CCC |", markdown)


if __name__ == "__main__":
    unittest.main()
