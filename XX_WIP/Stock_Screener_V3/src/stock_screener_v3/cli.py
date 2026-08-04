from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from stock_screener_v3.reports import (
    write_cross_sector_calibration_report,
    write_integrated_calibration_report,
    write_stage_family_calibration_report,
    write_symbol_failure_report,
)
from stock_screener_v3.runner import run_backtest, run_backtest_pack


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stock Screener V3 engine runner.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    backtest = subparsers.add_parser("backtest", help="Run the V3 engine as of a historical D date.")
    backtest.add_argument("--workspace-root", default=str(Path.cwd()), help="Workspace root for input/output paths.")
    backtest.add_argument("--universe-file", required=True, help="CSV universe file inside the workspace.")
    backtest.add_argument("--d-date", required=True, help="Engine execution date in YYYY-MM-DD format.")
    backtest.add_argument("--sector", default="", help="Comma-separated sector filters.")
    backtest.add_argument("--exchange", default="", help="Comma-separated exchange filters.")
    backtest.add_argument("--sample-size", type=int, default=None, help="Optional deterministic random sample size.")
    backtest.add_argument("--random-seed", type=int, default=None, help="Optional deterministic random seed.")
    backtest.add_argument("--forward-days", default="1,2,5", help="Comma-separated forward validation horizons.")
    backtest.add_argument("--stage-family", default="CROSSOVER,MOMENTUM_SETUP,DIVERGENCE", help="Comma-separated stage families.")
    backtest.add_argument("--run-label", default="v3_backtest", help="Artifact filename prefix.")
    backtest.add_argument("--details-output", default=None, help="Optional detail CSV path.")
    backtest.add_argument("--summary-output", default=None, help="Optional summary markdown path.")
    backtest.add_argument("--log-file", default=None, help="Optional execution summary log path.")
    pack = subparsers.add_parser("backtest-pack", help="Run the V3 engine across multiple historical D dates.")
    pack.add_argument("--workspace-root", default=str(Path.cwd()), help="Workspace root for input/output paths.")
    pack.add_argument("--universe-file", required=True, help="CSV universe file inside the workspace.")
    pack.add_argument("--d-dates", required=True, help="Comma-separated engine execution dates in YYYY-MM-DD format.")
    pack.add_argument("--sector", default="", help="Comma-separated sector filters.")
    pack.add_argument("--exchange", default="", help="Comma-separated exchange filters.")
    pack.add_argument("--sample-size", type=int, default=None, help="Optional deterministic random sample size.")
    pack.add_argument("--random-seed", type=int, default=None, help="Optional deterministic random seed.")
    pack.add_argument("--forward-days", default="1,2,5", help="Comma-separated forward validation horizons.")
    pack.add_argument("--stage-family", default="CROSSOVER,MOMENTUM_SETUP,DIVERGENCE", help="Comma-separated stage families.")
    pack.add_argument("--run-label", default="v3_backtest_pack", help="Artifact filename prefix.")
    pack.add_argument("--aggregate-summary-output", default=None, help="Optional multi-date summary markdown path.")
    cross_sector = subparsers.add_parser("cross-sector-report", help="Generate a cross-sector calibration report from detail CSV files.")
    cross_sector.add_argument("--details", required=True, help="Comma-separated detail CSV paths.")
    cross_sector.add_argument("--output", required=True, help="Markdown output path.")
    cross_sector.add_argument("--horizon-days", type=int, default=20, help="Forward horizon to summarize.")
    cross_sector.add_argument("--candidate-state", default="PRE_BEAR_CROSSOVER", help="Candidate state to include.")
    symbol_failure = subparsers.add_parser("symbol-failure-report", help="Generate a symbol-level failure report from detail CSV files.")
    symbol_failure.add_argument("--details", required=True, help="Comma-separated detail CSV paths.")
    symbol_failure.add_argument("--output", required=True, help="Markdown output path.")
    symbol_failure.add_argument("--horizon-days", type=int, default=20, help="Forward horizon to summarize.")
    symbol_failure.add_argument("--limit", type=int, default=15, help="Maximum rows per failure table.")
    symbol_failure.add_argument("--stage-family", default="", help="Optional stage-family filter.")
    symbol_failure.add_argument("--candidate-state", default="", help="Optional candidate-state filter.")
    symbol_failure.add_argument("--sector", default="", help="Optional sector filter.")
    stage_family = subparsers.add_parser("stage-family-report", help="Generate a stage-family calibration report from detail CSV files.")
    stage_family.add_argument("--details", required=True, help="Comma-separated detail CSV paths.")
    stage_family.add_argument("--output", required=True, help="Markdown output path.")
    stage_family.add_argument("--stage-family", required=True, help="Stage family to include, e.g. DIVERGENCE or MOMENTUM_SETUP.")
    stage_family.add_argument("--horizon-days", type=int, default=20, help="Forward horizon to summarize.")
    integrated = subparsers.add_parser("integrated-report", help="Generate an integrated ranking and calibration report from detail CSV files.")
    integrated.add_argument("--details", required=True, help="Comma-separated detail CSV paths.")
    integrated.add_argument("--output", required=True, help="Markdown output path.")
    integrated.add_argument("--horizon-days", type=int, default=20, help="Forward horizon to summarize.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "backtest":
        result = run_backtest(
            workspace_root=args.workspace_root,
            universe_file=args.universe_file,
            d_date=date.fromisoformat(args.d_date),
            sectors=_split_csv(args.sector),
            exchanges=_split_csv(args.exchange),
            sample_size=args.sample_size,
            random_seed=args.random_seed,
            forward_days=tuple(int(value) for value in _split_csv(args.forward_days)),
            stage_families=_split_csv(args.stage_family),
            run_label=args.run_label,
            details_output=args.details_output,
            summary_output=args.summary_output,
            log_file=args.log_file,
        )
        print(f"Processed: {result.result.symbols_processed}")
        print(f"Candidates: {result.result.candidates_found}")
        print(f"Output CSV: {result.paths.details_output}")
        print(f"Summary: {result.paths.summary_output}")
        print(f"Log: {result.paths.log_file}")
        return 0
    if args.command == "backtest-pack":
        result = run_backtest_pack(
            workspace_root=args.workspace_root,
            universe_file=args.universe_file,
            d_dates=tuple(date.fromisoformat(value) for value in _split_csv(args.d_dates)),
            sectors=_split_csv(args.sector),
            exchanges=_split_csv(args.exchange),
            sample_size=args.sample_size,
            random_seed=args.random_seed,
            forward_days=tuple(int(value) for value in _split_csv(args.forward_days)),
            stage_families=_split_csv(args.stage_family),
            run_label=args.run_label,
            aggregate_summary_output=args.aggregate_summary_output,
        )
        print(f"Runs: {len(result.runs)}")
        print(f"Aggregate summary: {result.summary_output}")
        for run in result.runs:
            print(f"{run.result.config.d_date.isoformat()}: processed={run.result.symbols_processed} candidates={run.result.candidates_found}")
        return 0
    if args.command == "cross-sector-report":
        write_cross_sector_calibration_report(
            _split_csv(args.details),
            args.output,
            horizon_days=args.horizon_days,
            candidate_state=args.candidate_state,
        )
        print(f"Cross-sector report: {args.output}")
        return 0
    if args.command == "symbol-failure-report":
        write_symbol_failure_report(
            _split_csv(args.details),
            args.output,
            horizon_days=args.horizon_days,
            limit=args.limit,
            stage_family=args.stage_family,
            candidate_state=args.candidate_state,
            sector=args.sector,
        )
        print(f"Symbol failure report: {args.output}")
        return 0
    if args.command == "stage-family-report":
        write_stage_family_calibration_report(
            _split_csv(args.details),
            args.output,
            stage_family=args.stage_family,
            horizon_days=args.horizon_days,
        )
        print(f"Stage-family report: {args.output}")
        return 0
    if args.command == "integrated-report":
        write_integrated_calibration_report(
            _split_csv(args.details),
            args.output,
            horizon_days=args.horizon_days,
        )
        print(f"Integrated report: {args.output}")
        return 0
    raise AssertionError(f"Unhandled command: {args.command}")


def _split_csv(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(",") if part.strip())


if __name__ == "__main__":
    raise SystemExit(main())

