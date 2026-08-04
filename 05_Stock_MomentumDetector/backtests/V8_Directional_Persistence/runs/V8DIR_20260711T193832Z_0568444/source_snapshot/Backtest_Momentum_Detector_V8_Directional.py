import argparse
import csv
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
DEFAULT_CONFIG = Path("config/V8_Directional_Persistence_Config.json")
DEFAULT_OUTPUT_ROOT = Path("backtests/V8_Directional_Persistence/runs")


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


def write_csv(rows, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    with open(path, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def verify_source_checksums(run_dir):
    failures = []
    for line in (run_dir / "checksums.sha256").read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", 1)
        path = run_dir / relative
        if not path.exists() or sha256_file(path) != expected:
            failures.append(relative)
    if failures:
        raise RuntimeError(f"source run checksum failures: {failures}")


def select_signal_date(execution_df, selection_month):
    month = pd.Period(selection_month, freq="M")
    dates = pd.to_datetime(execution_df["Signal_Date"])
    eligible = execution_df.loc[dates.dt.to_period("M") == month].copy()
    if eligible.empty:
        raise ValueError(f"no execution rows in {selection_month}")
    eligible["Active"] = eligible["Final_Decision"].eq("MOMENTUM_ACTIVE")
    counts = eligible.groupby("Signal_Date", as_index=False)["Active"].sum()
    maximum = int(counts["Active"].max())
    selected = sorted(counts.loc[counts["Active"] == maximum, "Signal_Date"])[0]
    return pd.Timestamp(selected).normalize(), maximum


def directional_metrics(price_df, signal_date, persistence_horizons=(5, 8)):
    signal_date = pd.Timestamp(signal_date).normalize()
    position = price_df.index.get_loc(signal_date)
    if not isinstance(position, int):
        position = int(position[0])
    d_close = float(price_df.iloc[position]["Close"])
    d1_date = price_df.index[position + 1]
    d1_open = float(price_df.iloc[position + 1]["Open"])
    d1_close = float(price_df.iloc[position + 1]["Close"])
    result = {
        "D_Close": d_close,
        "D1_Date": d1_date.date().isoformat(),
        "D1_Open": d1_open,
        "D1_Close": d1_close,
        "D1_Open_vs_D_Close_Pct": ((d1_open / d_close) - 1.0) * 100.0,
        "D1_Close_vs_D_Close_Pct": ((d1_close / d_close) - 1.0) * 100.0,
        "D1_Close_vs_D1_Open_Pct": ((d1_close / d1_open) - 1.0) * 100.0,
        "D1_Direction_Pass": d1_close > d_close,
        "D1_Intraday_Up": d1_close > d1_open,
    }
    for horizon in persistence_horizons:
        horizon_date = price_df.index[position + int(horizon)]
        horizon_close = float(price_df.iloc[position + int(horizon)]["Close"])
        result[f"D{horizon}_Date"] = horizon_date.date().isoformat()
        result[f"D{horizon}_Close"] = horizon_close
        result[f"D{horizon}_Close_vs_D_Close_Pct"] = (
            (horizon_close / d_close) - 1.0
        ) * 100.0
        result[f"D{horizon}_Persistence_Pass"] = horizon_close > d_close
    return result


def write_checksums(run_dir):
    checksum_path = run_dir / "checksums.sha256"
    lines = []
    for path in sorted(run_dir.rglob("*")):
        if path.is_file() and path != checksum_path:
            lines.append(f"{sha256_file(path)}  {path.relative_to(run_dir).as_posix()}")
    checksum_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(lines)


def parse_args():
    parser = argparse.ArgumentParser(description="V8 D+1 direction and D+5/D+8 persistence backtest")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    return parser.parse_args()


def main():
    args = parse_args()
    config_path = args.config.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    source_run = (ROOT / config["Source_Run"]).resolve()
    verify_source_checksums(source_run)
    source_manifest = json.loads((source_run / "run_manifest.json").read_text(encoding="utf-8"))
    execution = pd.read_csv(source_run / "outputs/execution_log.csv")
    signal_date, active_count = select_signal_date(execution, config["Selection_Month"])
    horizons = [int(value) for value in config["Persistence_Horizons"]]

    started = datetime.now(timezone.utc)
    run_id = f"V8DIR_{started.strftime('%Y%m%dT%H%M%SZ')}_{git_value('rev-parse', '--short', 'HEAD')}"
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
    log(f"Selection_Rule={config['Signal_Date_Selection_Rule']}")
    log(f"Selected_Date={signal_date.date()} Active_Count={active_count}")
    log(f"Primary_D1_Rule={config['Primary_D1_Rule']}")

    shutil.copy2(config_path, source_dir / config_path.name)
    for source in [
        ROOT / "Backtest_Momentum_Detector_V8_Directional.py",
        ROOT / "Validate_Momentum_Detector_V8_Directional.py",
        ROOT / "tests/test_v8_directional_persistence.py",
    ]:
        destination = source_dir / source.relative_to(ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    shutil.copy2(source_run / "checksums.sha256", run_dir / "source_run_checksums.sha256")

    selected_rows = execution.loc[
        execution["Signal_Date"].eq(signal_date.date().isoformat())
    ].copy()
    all_results = []
    for _, source_row in selected_rows.iterrows():
        ticker = source_row["Ticker"]
        price = load_price(source_run / f"inputs/prices/{ticker}.csv")
        metrics = directional_metrics(price, signal_date, horizons)
        result = {
            "Run_ID": run_id,
            "Ticker": ticker,
            "Signal_Date": signal_date.date().isoformat(),
            "Final_Decision": source_row["Final_Decision"],
            "Score": source_row["Score"],
            "Final_Decision_Reason": source_row["Final_Decision_Reason"],
            "ETF_Mappings": source_row["Same_Quarter_ETF_Mappings"],
            **metrics,
        }
        all_results.append(result)
        log(
            f"DIRECTION ticker={ticker} decision={result['Final_Decision']} score={result['Score']} "
            f"d1={result['D1_Close_vs_D_Close_Pct']:.2f}% d5={result['D5_Close_vs_D_Close_Pct']:.2f}% "
            f"d8={result['D8_Close_vs_D_Close_Pct']:.2f}%"
        )

    active_results = [row for row in all_results if row["Final_Decision"] == "MOMENTUM_ACTIVE"]
    mapping_df = pd.read_csv(source_run / "outputs/etf_mapping_validation.csv")
    mapping_df = mapping_df.loc[mapping_df["Same_Quarter_Eligible"].eq(True)]
    active_etf_results = []
    for stock_row in active_results:
        mappings = mapping_df.loc[mapping_df["Stock_Code"].eq(stock_row["Ticker"])]
        for _, mapping in mappings.iterrows():
            etf_ticker = mapping["ETF_Ticker"]
            price = load_price(source_run / f"inputs/prices/{etf_ticker}.csv")
            active_etf_results.append(
                {
                    "Run_ID": run_id,
                    "Stock_Code": stock_row["Ticker"],
                    "Stock_Score": stock_row["Score"],
                    "ETF_Ticker": etf_ticker,
                    "Holding_Weight_Pct_Direct": mapping["Holding_Weight_Pct_Direct"],
                    "Validation_Rank": mapping["Validation_Rank"],
                    "Validation_As_Of_Date": mapping["Validation_As_Of_Date"],
                    "Evidence_Mode": config["ETF_Evidence_Mode"],
                    **directional_metrics(price, signal_date, horizons),
                }
            )

    write_csv(all_results, outputs_dir / "all_stock_results.csv")
    write_csv(active_results, outputs_dir / "active_signal_results.csv")
    write_csv(active_etf_results, outputs_dir / "active_etf_reference_results.csv")

    def rate(rows, field):
        return 100.0 * sum(bool(row[field]) for row in rows) / len(rows) if rows else None

    def mean(rows, field):
        return sum(float(row[field]) for row in rows) / len(rows) if rows else None

    summary = {
        "Run_ID": run_id,
        "Source_Run": source_manifest["Run_ID"],
        "Selection_Month": config["Selection_Month"],
        "Signal_Date": signal_date.date().isoformat(),
        "Signal_Date_Selection_Rule": config["Signal_Date_Selection_Rule"],
        "Stocks_Checked": len(all_results),
        "Active_Signals": len(active_results),
        "Primary_D1_Rule": config["Primary_D1_Rule"],
        "Active_D1_Direction_Pass_Count": sum(row["D1_Direction_Pass"] for row in active_results),
        "Active_D1_Direction_Pass_Rate_Pct": rate(active_results, "D1_Direction_Pass"),
        "Active_D1_Mean_Close_vs_D_Close_Pct": mean(active_results, "D1_Close_vs_D_Close_Pct"),
        "Active_D1_Intraday_Up_Rate_Pct": rate(active_results, "D1_Intraday_Up"),
        "Active_D5_Persistence_Pass_Rate_Pct": rate(active_results, "D5_Persistence_Pass"),
        "Active_D5_Mean_Close_vs_D_Close_Pct": mean(active_results, "D5_Close_vs_D_Close_Pct"),
        "Active_D8_Persistence_Pass_Rate_Pct": rate(active_results, "D8_Persistence_Pass"),
        "Active_D8_Mean_Close_vs_D_Close_Pct": mean(active_results, "D8_Close_vs_D_Close_Pct"),
        "Active_ETF_References": len(active_etf_results),
        "Active_ETF_D1_Direction_Pass_Rate_Pct": rate(active_etf_results, "D1_Direction_Pass"),
        "Active_ETF_D5_Persistence_Pass_Rate_Pct": rate(active_etf_results, "D5_Persistence_Pass"),
        "Active_ETF_D8_Persistence_Pass_Rate_Pct": rate(active_etf_results, "D8_Persistence_Pass"),
        "Evidence_Classification": "PRIMARY_D1_DIRECTION_NOT_SUPPORTED_IN_SELECTED_SAMPLE",
    }
    (outputs_dir / "aggregate_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    manifest = {
        **summary,
        "Started_UTC": started.isoformat(),
        "Completed_UTC": datetime.now(timezone.utc).isoformat(),
        "Git_Commit": git_value("rev-parse", "HEAD"),
        "Git_Worktree_Dirty": bool(git_value("status", "--porcelain")),
        "Source_Run_Checksums_SHA256": sha256_file(source_run / "checksums.sha256"),
        "Config_SHA256": sha256_file(config_path),
        "Known_Limitations": [
            "The selected date maximizes Active count in April and is not a random date.",
            "Only four Active signals are available on the selected date.",
            "D+1 direction is defined as next-session Close above signal-date Close; intraday Open-to-Close is diagnostic only.",
            "Price persistence does not by itself prove a fundamental corporate change.",
            "ETF evidence uses a same-quarter stability assumption rather than signal-date archived holdings.",
        ],
    }
    (run_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (run_dir / "README.md").write_text(
        f"# {run_id}\n\nV8 D+1 direction and D+5/D+8 persistence test using {signal_date.date()}.\n",
        encoding="utf-8",
    )

    validator = ROOT / "Validate_Momentum_Detector_V8_Directional.py"
    result = subprocess.run(
        [sys.executable, str(validator), str(run_dir), "--skip-checksums"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    (validation_dir / "validator_console.txt").write_text(
        result.stdout + result.stderr, encoding="utf-8"
    )
    if result.returncode:
        raise RuntimeError(f"directional validator failed: {result.stdout}{result.stderr}")
    log("VALIDATION_PASS")
    log(f"RUN_COMPLETE run_dir={run_dir}")
    count = write_checksums(run_dir)
    print(f"CHECKSUMS_WRITTEN entries={count}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
