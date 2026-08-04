import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf

import V8_V1_V3_Indicator_Baseline as baseline
from Backtest_V8_V1_V3_Indicator_Baseline import (
    calculate_outcome,
    git_value,
    mean,
    write_checksums,
    write_csv,
)


ROOT = Path(__file__).resolve().parent
DEFAULT_EXPERIMENT_CONFIG = (
    ROOT / "config" / "V8_V1_V3_Composite_Score_Expanded_Config.json"
)
DEFAULT_OUTPUT_ROOT = (
    ROOT / "backtests" / "V8_V1_V3_Composite_Score_Expanded" / "runs"
)


def chunks(values, size):
    for offset in range(0, len(values), size):
        yield values[offset : offset + size]


def download_batch(tickers, start, end):
    downloaded = yf.download(
        tickers,
        start=start,
        end=end,
        auto_adjust=False,
        actions=False,
        progress=False,
        threads=True,
        group_by="ticker",
    )
    frames = {}
    for ticker in tickers:
        try:
            if isinstance(downloaded.columns, pd.MultiIndex):
                if ticker in downloaded.columns.get_level_values(0):
                    frame = downloaded[ticker].copy()
                else:
                    frame = downloaded.xs(ticker, axis=1, level=1).copy()
            else:
                frame = downloaded.copy()
            frame = frame.dropna(subset=["Open", "High", "Low", "Close", "Volume"])
            frame.index = pd.to_datetime(frame.index).tz_localize(None).normalize()
            frames[ticker] = frame
        except (KeyError, TypeError, ValueError):
            frames[ticker] = pd.DataFrame()
    return frames


def frame_has_complete_scope(frame, dates, horizons, minimum_bars):
    if frame.empty:
        return False, "no daily OHLCV returned"
    maximum_horizon = max(horizons)
    for date in dates:
        stamp = pd.Timestamp(date)
        if stamp not in frame.index:
            return False, f"signal date {date} is missing"
        location = frame.index.get_loc(stamp)
        if not isinstance(location, int):
            return False, f"signal date {date} is not unique"
        if location + maximum_horizon >= len(frame):
            return False, f"D+{maximum_horizon} outcome unavailable for {date}"
        if location + 1 < int(minimum_bars):
            return False, f"fewer than {minimum_bars} bars at {date}"
    return True, "complete"


def median(values):
    return float(pd.Series(values, dtype="float64").median()) if values else None


def cohort_metrics(rows, horizons):
    output = {"Rows": len(rows)}
    for horizon in horizons:
        values = [float(row[f"D{horizon}_Return_Pct"]) for row in rows]
        output[f"D{horizon}_Positive"] = sum(value > 0 for value in values)
        output[f"D{horizon}_Positive_Rate_Pct"] = (
            100 * sum(value > 0 for value in values) / len(values) if values else None
        )
        output[f"D{horizon}_Mean_Return_Pct"] = mean(values)
        output[f"D{horizon}_Median_Return_Pct"] = median(values)
    return output


def score_analysis(rows, profiles, sectors, horizons):
    exact_rows = []
    threshold_rows = []
    correlation_rows = []
    for profile in profiles:
        for sector in ["ALL", *sectors]:
            group = [
                row
                for row in rows
                if row["Profile"] == profile
                and (sector == "ALL" or row["Sector"] == sector)
                and row["Foundation_Eligible"] is True
                and row["DMI_Dominance_Pass"] is True
            ]
            scores = sorted({int(row["Total_Momentum_Score"]) for row in group})
            for score in scores:
                cohort = [row for row in group if int(row["Total_Momentum_Score"]) == score]
                exact_rows.append(
                    {
                        "Profile": profile,
                        "Sector": sector,
                        "Exact_Score": score,
                        **cohort_metrics(cohort, horizons),
                    }
                )
            for cutoff in scores:
                cohort = [row for row in group if int(row["Total_Momentum_Score"]) >= cutoff]
                threshold_rows.append(
                    {
                        "Profile": profile,
                        "Sector": sector,
                        "Minimum_Score": cutoff,
                        **cohort_metrics(cohort, horizons),
                    }
                )
            correlation = {"Profile": profile, "Sector": sector, "Rows": len(group)}
            score_series = pd.Series(
                [float(row["Total_Momentum_Score"]) for row in group], dtype="float64"
            )
            for horizon in horizons:
                returns = pd.Series(
                    [float(row[f"D{horizon}_Return_Pct"]) for row in group],
                    dtype="float64",
                )
                correlation[f"D{horizon}_Score_Spearman"] = (
                    score_series.rank().corr(returns.rank())
                    if len(group) > 1 and score_series.nunique() > 1
                    else None
                )
            correlation_rows.append(correlation)
    return exact_rows, threshold_rows, correlation_rows


def parse_args():
    parser = argparse.ArgumentParser(
        description="Expanded V1-V3 composite Score backtest"
    )
    parser.add_argument("--experiment-config", type=Path, default=DEFAULT_EXPERIMENT_CONFIG)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    return parser.parse_args()


def main():
    args = parse_args()
    baseline_config = baseline.load_config()
    requested_experiment = json.loads(
        args.experiment_config.read_text(encoding="utf-8")
    )
    if requested_experiment.get("No_Tuning_During_Run") is not True:
        raise ValueError("expanded Score experiment must prohibit tuning during the run")
    profiles = requested_experiment["Profiles"]
    if profiles != ["V1", "V2", "V3"]:
        raise ValueError("profiles must remain V1, V2, V3")
    dates = requested_experiment["Signal_Dates"]
    horizons = [int(value) for value in requested_experiment["Forward_Horizons_Sessions"]]
    requested_pairs = [
        (ticker, sector)
        for sector, tickers in requested_experiment["Sector_Stocks"].items()
        for ticker in tickers
    ]
    if len({ticker for ticker, _ in requested_pairs}) != len(requested_pairs):
        raise ValueError("a ticker appears more than once in the expanded universe")

    started = datetime.now(timezone.utc)
    run_id = (
        f"V8SCORE_{started.strftime('%Y%m%dT%H%M%SZ')}_"
        f"{git_value('rev-parse', '--short', 'HEAD')}"
    )
    run_dir = args.output_root.resolve() / run_id
    inputs_dir = run_dir / "inputs"
    prices_dir = inputs_dir / "prices"
    outputs_dir = run_dir / "outputs"
    validation_dir = run_dir / "validation"
    source_dir = run_dir / "source_snapshot"
    for path in (prices_dir, outputs_dir, validation_dir, source_dir / "config"):
        path.mkdir(parents=True, exist_ok=True)

    log_lines = []

    def log(message):
        line = f"{datetime.now(timezone.utc).isoformat()} {message}"
        log_lines.append(line)
        print(line, flush=True)

    log(f"RUN_START run_id={run_id} requested_stocks={len(requested_pairs)} dates={len(dates)}")
    sector_by_ticker = dict(requested_pairs)
    successful = {}
    failures = []
    for batch in chunks([ticker for ticker, _ in requested_pairs], 10):
        log(f"DOWNLOAD_BATCH tickers={','.join(batch)}")
        frames = download_batch(
            batch,
            requested_experiment["Price_Start"],
            requested_experiment["Price_End_Exclusive"],
        )
        for ticker in batch:
            frame = frames[ticker]
            complete, reason = frame_has_complete_scope(
                frame, dates, horizons, baseline_config["Minimum_History_Bars"]
            )
            if complete:
                frozen_path = prices_dir / f"{ticker}.csv"
                frame.reset_index(names="Date").to_csv(frozen_path, index=False)
                successful[ticker] = pd.read_csv(
                    frozen_path, parse_dates=["Date"]
                ).set_index("Date")
            else:
                failures.append(
                    {"Ticker": ticker, "Sector": sector_by_ticker[ticker], "Reason": reason}
                )
                log(f"DOWNLOAD_REJECT ticker={ticker} reason={reason}")

    successful_by_sector = {
        sector: [
            ticker
            for ticker in tickers
            if ticker in successful
        ]
        for sector, tickers in requested_experiment["Sector_Stocks"].items()
    }
    minimum = int(requested_experiment["Minimum_Successful_Stocks_Per_Sector"])
    for sector, tickers in successful_by_sector.items():
        if len(tickers) < minimum:
            raise RuntimeError(
                f"{sector} has {len(tickers)} successful stocks; {minimum} required"
            )

    frozen_experiment = dict(requested_experiment)
    frozen_experiment["Sector_Stocks"] = successful_by_sector
    frozen_experiment["Requested_Stocks"] = len(requested_pairs)
    frozen_experiment["Successful_Stocks"] = sum(
        len(values) for values in successful_by_sector.values()
    )
    (inputs_dir / "Experiment_Config.json").write_text(
        json.dumps(frozen_experiment, indent=2), encoding="utf-8"
    )
    shutil.copy2(args.experiment_config, inputs_dir / "Requested_Experiment_Config.json")
    shutil.copy2(baseline.DEFAULT_CONFIG_PATH, inputs_dir / baseline.DEFAULT_CONFIG_PATH.name)
    write_csv(
        failures or [{"Ticker": "", "Sector": "", "Reason": ""}],
        outputs_dir / "download_failures.csv",
    )

    rows = []
    maximum_scores = {"V1": 30, "V2": 30, "V3": 45}
    for sector, tickers in successful_by_sector.items():
        for ticker in tickers:
            frame = successful[ticker]
            for signal_date in dates:
                for profile in profiles:
                    result = baseline.evaluate_profile(
                        ticker,
                        frame,
                        signal_date,
                        profile,
                        baseline_config,
                        evaluated_at=started,
                    )
                    row = {
                        "Run_ID": run_id,
                        "Sector": sector,
                        **result,
                        "Score_Maximum_Positive": maximum_scores[profile],
                        "Score_Pct_Of_Profile_Maximum": (
                            100
                            * float(result["Total_Momentum_Score"])
                            / maximum_scores[profile]
                        ),
                    }
                    for horizon in horizons:
                        measured = calculate_outcome(frame, signal_date, horizon)
                        row[f"D{horizon}_Entry_Date"] = measured["Entry_Date"]
                        row[f"D{horizon}_Exit_Date"] = measured["Exit_Date"]
                        row[f"D{horizon}_Return_Pct"] = measured["Return_Pct"]
                        row[f"D{horizon}_Positive"] = measured["Return_Pct"] > 0
                    rows.append(row)
            log(f"EVALUATED ticker={ticker} sector={sector} rows={len(dates) * len(profiles)}")
    write_csv(rows, outputs_dir / "profile_results.csv")

    sectors = list(successful_by_sector)
    summary_rows = []
    for profile in profiles:
        for sector in ["ALL", *sectors]:
            group = [
                row
                for row in rows
                if row["Profile"] == profile
                and (sector == "ALL" or row["Sector"] == sector)
            ]
            foundation = [row for row in group if row["Foundation_Eligible"] is True]
            dmi = [row for row in foundation if row["DMI_Dominance_Pass"] is True]
            qualified = [row for row in group if row["V1_V3_Qualified"] is True]
            summary_rows.append(
                {
                    "Profile": profile,
                    "Sector": sector,
                    "Rows": len(group),
                    "Foundation_Eligible": len(foundation),
                    "DMI_Dominance_Pass": len(dmi),
                    "Qualified": len(qualified),
                    **{
                        f"Qualified_{key}": value
                        for key, value in cohort_metrics(qualified, horizons).items()
                        if key != "Rows"
                    },
                }
            )
    write_csv(summary_rows, outputs_dir / "profile_sector_summary.csv")
    exact, thresholds, correlations = score_analysis(rows, profiles, sectors, horizons)
    write_csv(exact, outputs_dir / "exact_score_summary.csv")
    write_csv(thresholds, outputs_dir / "score_threshold_summary.csv")
    write_csv(correlations, outputs_dir / "score_return_correlations.csv")

    aggregate = {
        "Run_ID": run_id,
        "Experiment_ID": requested_experiment["Experiment_ID"],
        "Configuration_ID": baseline_config["Configuration_ID"],
        "Limit_Status": baseline_config["Limit_Status"],
        "Operational_Use_Approved": baseline_config["Operational_Use_Approved"],
        "Requested_Stocks": len(requested_pairs),
        "Successful_Stocks_By_Sector": {
            sector: len(tickers) for sector, tickers in successful_by_sector.items()
        },
        "Dates": len(dates),
        "Profiles": len(profiles),
        "Rows": len(rows),
        "Download_Failures": len(failures),
        "Profile_Sector_Summary": summary_rows,
        "Score_Return_Correlations": correlations,
    }
    (outputs_dir / "aggregate_summary.json").write_text(
        json.dumps(aggregate, indent=2), encoding="utf-8"
    )
    (outputs_dir / "execution.log").write_text(
        "\n".join(log_lines) + "\n", encoding="utf-8"
    )

    source_files = [
        ROOT / "V8_V1_V3_Indicator_Baseline.py",
        ROOT / "Backtest_V8_V1_V3_Indicator_Baseline.py",
        ROOT / "Backtest_V8_V1_V3_Composite_Score_Expanded.py",
        ROOT / "Validate_V8_V1_V3_Indicator_Baseline.py",
        ROOT / "tests" / "test_v8_v1_v3_indicator_baseline.py",
    ]
    for source in source_files:
        destination = source_dir / source.relative_to(ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    shutil.copy2(
        baseline.DEFAULT_CONFIG_PATH,
        source_dir / "config" / baseline.DEFAULT_CONFIG_PATH.name,
    )
    shutil.copy2(
        args.experiment_config,
        source_dir / "config" / args.experiment_config.name,
    )
    manifest = {
        **aggregate,
        "Started_UTC": started.isoformat(),
        "Completed_UTC": datetime.now(timezone.utc).isoformat(),
        "Git_Commit": git_value("rev-parse", "HEAD"),
        "Git_Worktree_Dirty": bool(git_value("status", "--porcelain")),
        "Known_Limitations": [
            "Purposeful current master-list sample creates survivorship and universe-selection limitations.",
            "Historical sector membership and index constituency were not reconstructed.",
            "Existing V1-V3 periods, values, weights, and thresholds were not tuned during this run.",
            "No transaction costs, stops, position sizing, or intraday override were modeled.",
            "A composite Score describes configured technical health; it is not a calibrated probability.",
        ],
    }
    (run_dir / "run_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    (run_dir / "README.md").write_text(
        f"# {run_id}\n\nExpanded V1-V3 composite Score replay. Research only.\n",
        encoding="utf-8",
    )
    (run_dir / "command.txt").write_text(
        "python Backtest_V8_V1_V3_Composite_Score_Expanded.py\n", encoding="utf-8"
    )

    validator = ROOT / "Validate_V8_V1_V3_Indicator_Baseline.py"
    initial = subprocess.run(
        [sys.executable, str(validator), str(run_dir), "--skip-checksums"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    if initial.returncode:
        raise RuntimeError(initial.stdout + initial.stderr)
    checksum_count = write_checksums(run_dir)
    final = subprocess.run(
        [sys.executable, str(validator), str(run_dir)],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    (validation_dir / "validator_console.txt").write_text(
        final.stdout + final.stderr, encoding="utf-8"
    )
    if final.returncode:
        raise RuntimeError(final.stdout + final.stderr)
    print(f"CHECKSUMS_WRITTEN entries={checksum_count}")
    print(f"RUN_COMPLETE run_dir={run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
