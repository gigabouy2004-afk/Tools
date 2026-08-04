import argparse
import csv
import hashlib
import json
import shutil
import statistics
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

import Momentum_Detector_V8 as engine
from Backtest_Momentum_Detector_V8_Directional import directional_metrics


ROOT = Path(__file__).resolve().parent
DEFAULT_CONFIG = Path("config/V8_MACD_Research_Config.json")
DEFAULT_OUTPUT_ROOT = Path("backtests/V8_MACD_Research/runs")


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_value(*args):
    try:
        return subprocess.check_output(
            ["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "UNKNOWN"


def load_price(path):
    frame = pd.read_csv(path, parse_dates=["Date"], index_col="Date")
    frame.index = pd.to_datetime(frame.index).tz_localize(None).normalize()
    return frame


def parse_quarter(value):
    period = pd.Period(str(value), freq="Q")
    return period.start_time.normalize(), period.end_time.normalize()


def write_csv(rows, path):
    fields = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_checksums(run_dir):
    checksum_path = run_dir / "checksums.sha256"
    lines = []
    for path in sorted(run_dir.rglob("*")):
        if path.is_file() and path != checksum_path:
            lines.append(f"{sha256_file(path)}  {path.relative_to(run_dir).as_posix()}")
    checksum_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(lines)


def variant_macd(price, variant):
    return engine.calculate_macd(
        price["Close"],
        fast_period=variant["Fast"],
        slow_period=variant["Slow"],
        signal_period=variant["Signal"],
    )


def event_dates(state, quarter_start, quarter_end, price, max_horizon):
    starts = state & ~state.shift(1, fill_value=False)
    dates = []
    for signal_date in state.index[starts]:
        if signal_date < quarter_start or signal_date > quarter_end:
            continue
        position = price.index.get_loc(signal_date)
        if not isinstance(position, int):
            position = int(position[0])
        if position + max_horizon >= len(price):
            continue
        if price.index[position + max_horizon] <= quarter_end:
            dates.append(signal_date)
    return dates


def next_v8_active_date(execution, ticker, signal_date):
    candidates = execution.loc[
        execution["Ticker"].eq(ticker)
        & execution["Final_Decision"].eq("MOMENTUM_ACTIVE")
        & (pd.to_datetime(execution["Signal_Date"]) >= signal_date)
    ]
    if candidates.empty:
        return None
    return pd.to_datetime(candidates["Signal_Date"]).min().normalize()


def bool_rate(rows, field):
    return 100.0 * sum(bool(row[field]) for row in rows) / len(rows) if rows else None


def mean_value(rows, field):
    return sum(float(row[field]) for row in rows) / len(rows) if rows else None


def parse_args():
    parser = argparse.ArgumentParser(description="V8 configurable MACD episode research")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    return parser.parse_args()


def main():
    args = parse_args()
    config_path = args.config.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    source_run = (ROOT / config["Source_Run"]).resolve()
    source_manifest = json.loads((source_run / "run_manifest.json").read_text(encoding="utf-8"))
    execution = pd.read_csv(source_run / "outputs/execution_log.csv")
    execution["Signal_Date"] = pd.to_datetime(execution["Signal_Date"])
    tickers = source_manifest["Selected_Stocks"]
    quarter_start, quarter_end = parse_quarter(config["Quarter"])
    same_date = pd.Timestamp(config["Same_Date_Comparison"])
    horizons = [int(value) for value in config["Persistence_Horizons"]]
    max_horizon = max(horizons)
    variants = config["Variants"]
    for variant in variants:
        engine.validate_macd_periods(variant["Fast"], variant["Slow"], variant["Signal"])

    started = datetime.now(timezone.utc)
    run_id = f"V8MACD_{started.strftime('%Y%m%dT%H%M%SZ')}_{git_value('rev-parse', '--short', 'HEAD')}"
    run_dir = args.output_root.resolve() / run_id
    outputs_dir = run_dir / "outputs"
    validation_dir = run_dir / "validation"
    source_dir = run_dir / "source_snapshot"
    for directory in [outputs_dir, validation_dir, source_dir]:
        directory.mkdir(parents=True, exist_ok=True)
    console_path = outputs_dir / "execution.log"

    def log(message):
        print(message, flush=True)
        with open(console_path, "a", encoding="utf-8") as file:
            file.write(str(message) + "\n")

    log(f"Run_ID={run_id}")
    log(f"Source_Run={source_manifest['Run_ID']}")
    log(f"Quarter={config['Quarter']} Same_Date={same_date.date()}")
    log(f"Signal_Rule={config['Signal_Rule']}")

    for source in [
        ROOT / "Momentum_Detector_V8.py",
        ROOT / "Backtest_Momentum_Detector_V8_MACD.py",
        ROOT / "Validate_Momentum_Detector_V8_MACD.py",
        ROOT / "tests/test_v8_macd.py",
        config_path,
    ]:
        relative = source.relative_to(ROOT) if source.is_relative_to(ROOT) else Path(source.name)
        destination = source_dir / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    shutil.copy2(source_run / "checksums.sha256", run_dir / "source_run_checksums.sha256")

    prices = {ticker: load_price(source_run / f"inputs/prices/{ticker}.csv") for ticker in tickers}
    event_rows = []
    same_date_rows = []

    for variant in variants:
        name = variant["Name"]
        for ticker in tickers:
            price = prices[ticker]
            macd = variant_macd(price, variant)
            ema200 = price["Close"].ewm(span=200, adjust=False, min_periods=200).mean()
            above_ema200 = price["Close"] > ema200
            state = macd["MACD_Bullish_Positive"].fillna(False).astype(bool) & above_ema200.fillna(False)
            starts = state & ~state.shift(1, fill_value=False)
            for signal_date in event_dates(state, quarter_start, quarter_end, price, max_horizon):
                next_active = next_v8_active_date(execution, ticker, signal_date)
                row = {
                    "Run_ID": run_id,
                    "Variant": name,
                    "Fast": variant["Fast"],
                    "Slow": variant["Slow"],
                    "Signal": variant["Signal"],
                    "Ticker": ticker,
                    "Signal_Date": signal_date.date().isoformat(),
                    "MACD_Line": macd.at[signal_date, "MACD_Line"],
                    "MACD_Signal_Line": macd.at[signal_date, "MACD_Signal_Line"],
                    "MACD_Histogram": macd.at[signal_date, "MACD_Histogram"],
                    "MACD_Bullish_Positive": bool(macd.at[signal_date, "MACD_Bullish_Positive"]),
                    "EMA_200": ema200.at[signal_date],
                    "Close_Above_EMA200": bool(above_ema200.at[signal_date]),
                    "Foundation_State": bool(state.at[signal_date]),
                    "Foundation_Episode_Start": bool(starts.at[signal_date]),
                    "V8_Next_Active_Date": next_active.date().isoformat() if next_active is not None else "",
                    "Lead_To_V8_Active_Calendar_Days": (next_active - signal_date).days if next_active is not None else "",
                    **directional_metrics(price, signal_date, horizons),
                }
                event_rows.append(row)

            if same_date in price.index:
                source_row = execution.loc[
                    execution["Ticker"].eq(ticker)
                    & execution["Signal_Date"].eq(same_date)
                ].iloc[0]
                same_date_rows.append(
                    {
                        "Run_ID": run_id,
                        "Variant": name,
                        "Fast": variant["Fast"],
                        "Slow": variant["Slow"],
                        "Signal": variant["Signal"],
                        "Ticker": ticker,
                        "Comparison_Date": same_date.date().isoformat(),
                        "MACD_Line": macd.at[same_date, "MACD_Line"],
                        "MACD_Signal_Line": macd.at[same_date, "MACD_Signal_Line"],
                        "MACD_Histogram": macd.at[same_date, "MACD_Histogram"],
                        "MACD_Bullish_Positive": bool(macd.at[same_date, "MACD_Bullish_Positive"]),
                        "EMA_200": ema200.at[same_date],
                        "Close_Above_EMA200": bool(above_ema200.at[same_date]),
                        "Foundation_State": bool(state.at[same_date]),
                        "Foundation_Episode_Start": bool(starts.at[same_date]),
                        "V8_Final_Decision": source_row["Final_Decision"],
                        "V8_Score": source_row["Score"],
                        **directional_metrics(price, same_date, horizons),
                    }
                )
        log(f"VARIANT_DONE name={name} episodes={sum(row['Variant'] == name for row in event_rows)}")

    summaries = []
    min_events = int(config["Minimum_Comparable_Episodes"])
    min_tickers = int(config["Minimum_Comparable_Tickers"])
    for variant in variants:
        rows = [row for row in event_rows if row["Variant"] == variant["Name"]]
        leads = [float(row["Lead_To_V8_Active_Calendar_Days"]) for row in rows if row["Lead_To_V8_Active_Calendar_Days"] != ""]
        summary = {
            "Variant": variant["Name"],
            "Fast": variant["Fast"],
            "Slow": variant["Slow"],
            "Signal": variant["Signal"],
            "Episodes": len(rows),
            "Unique_Tickers": len({row["Ticker"] for row in rows}),
            "D1_Pass_Rate_Pct": bool_rate(rows, "D1_Direction_Pass"),
            "D1_Mean_Move_Pct": mean_value(rows, "D1_Close_vs_D_Close_Pct"),
            "D5_Pass_Rate_Pct": bool_rate(rows, "D5_Persistence_Pass"),
            "D5_Mean_Move_Pct": mean_value(rows, "D5_Close_vs_D_Close_Pct"),
            "D8_Pass_Rate_Pct": bool_rate(rows, "D8_Persistence_Pass"),
            "D8_Mean_Move_Pct": mean_value(rows, "D8_Close_vs_D_Close_Pct"),
            "Median_Lead_To_V8_Active_Calendar_Days": statistics.median(leads) if leads else "",
            "Comparable_Sample": len(rows) >= min_events and len({row["Ticker"] for row in rows}) >= min_tickers,
        }
        summaries.append(summary)

    comparable = [row for row in summaries if row["Comparable_Sample"]]
    ranked = sorted(
        comparable,
        key=lambda row: (
            -row["D1_Pass_Rate_Pct"],
            -row["D5_Pass_Rate_Pct"],
            -row["D8_Pass_Rate_Pct"],
            -row["Episodes"],
            row["Variant"],
        ),
    )
    for rank, row in enumerate(ranked, start=1):
        row["Descriptive_Rank"] = rank
    for row in summaries:
        row.setdefault("Descriptive_Rank", "")

    write_csv(event_rows, outputs_dir / "macd_episode_results.csv")
    write_csv(same_date_rows, outputs_dir / "same_date_comparison.csv")
    write_csv(summaries, outputs_dir / "variant_summary.csv")
    aggregate = {
        "Run_ID": run_id,
        "Source_Run": source_manifest["Run_ID"],
        "Quarter": config["Quarter"],
        "Same_Date_Comparison": config["Same_Date_Comparison"],
        "Variants_Tested": len(variants),
        "Total_Episodes": len(event_rows),
        "Signal_Rule": config["Signal_Rule"],
        "Primary_Outcome": config["Primary_Outcome"],
        "Descriptive_Leader": ranked[0]["Variant"] if ranked else None,
        "Production_Score_Changed": False,
        "Conclusion_Limit": "SAME_QUARTER_RESEARCH_NOT_OUT_OF_SAMPLE_PROOF",
    }
    (outputs_dir / "aggregate_summary.json").write_text(json.dumps(aggregate, indent=2), encoding="utf-8")
    manifest = {
        **aggregate,
        "Started_UTC": started.isoformat(),
        "Completed_UTC": datetime.now(timezone.utc).isoformat(),
        "Git_Commit": git_value("rev-parse", "HEAD"),
        "Git_Worktree_Dirty": bool(git_value("status", "--porcelain")),
        "Config_SHA256": sha256_file(config_path),
        "Engine_SHA256": sha256_file(ROOT / "Momentum_Detector_V8.py"),
        "Known_Limitations": [
            "The five variants and ranking are evaluated on one quarter and ten stocks.",
            "The MACD episode rule is research-only and does not alter V8 Score or Final_Decision.",
            "Repeated variant comparisons create selection risk; an untouched holdout is required.",
            "MACD is derived only from price and cannot prove a fundamental corporate change.",
        ],
    }
    (run_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (run_dir / "README.md").write_text(
        f"# {run_id}\n\nConfigurable V8 MACD research across {len(variants)} predeclared variants.\n",
        encoding="utf-8",
    )

    validator = ROOT / "Validate_Momentum_Detector_V8_MACD.py"
    result = subprocess.run(
        [sys.executable, str(validator), str(run_dir), "--skip-checksums"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    (validation_dir / "validator_console.txt").write_text(result.stdout + result.stderr, encoding="utf-8")
    if result.returncode:
        raise RuntimeError(f"MACD validator failed: {result.stdout}{result.stderr}")
    log("VALIDATION_PASS")
    log(f"RUN_COMPLETE run_dir={run_dir}")
    count = write_checksums(run_dir)
    print(f"CHECKSUMS_WRITTEN entries={count}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
