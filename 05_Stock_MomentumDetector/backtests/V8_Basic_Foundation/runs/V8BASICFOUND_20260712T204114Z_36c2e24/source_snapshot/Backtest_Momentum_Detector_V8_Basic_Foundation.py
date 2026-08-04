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

import Momentum_Detector_V8_Basic as basic


ROOT = Path(__file__).resolve().parent
DEFAULT_SOURCE_RUN = (
    ROOT
    / "backtests"
    / "V8_Foundation_Validation"
    / "runs"
    / "V8FOUND_20260712T182945Z_cf0c908"
)
DEFAULT_OUTPUT_ROOT = ROOT / "backtests" / "V8_Basic_Foundation" / "runs"


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as file:
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


def write_csv(rows, path):
    fields = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    with Path(path).open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_checksums(run_dir):
    excluded = {
        "checksums.sha256",
        "validation/validation_summary.json",
        "validation/validator_console.txt",
    }
    lines = []
    for path in sorted(run_dir.rglob("*")):
        relative = path.relative_to(run_dir).as_posix()
        if path.is_file() and relative not in excluded:
            lines.append(f"{sha256_file(path)}  {relative}")
    (run_dir / "checksums.sha256").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    return len(lines)


def calculate_outcome(frame, signal_date, horizon):
    signal_date = pd.Timestamp(signal_date).normalize()
    position = frame.index.get_loc(signal_date)
    if not isinstance(position, int):
        position = int(position[0])
    entry_position = position + 1
    exit_position = position + int(horizon)
    entry_open = float(frame.iloc[entry_position]["Open"])
    exit_close = float(frame.iloc[exit_position]["Close"])
    return {
        "Entry_Date": frame.index[entry_position].date().isoformat(),
        "Exit_Date": frame.index[exit_position].date().isoformat(),
        "Return_Pct": ((exit_close / entry_open) - 1.0) * 100.0,
    }


def parse_args():
    parser = argparse.ArgumentParser(description="Frozen replay of the minimal V8 Foundation engine")
    parser.add_argument("--source-run", type=Path, default=DEFAULT_SOURCE_RUN)
    parser.add_argument("--config", type=Path, default=basic.DEFAULT_CONFIG_PATH)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    return parser.parse_args()


def main():
    args = parse_args()
    source_run = args.source_run.resolve()
    basic_config = basic.load_config(args.config)
    experiment_config = json.loads(
        (source_run / "inputs" / "V8_Foundation_Validation_Config.json").read_text(
            encoding="utf-8"
        )
    )
    stocks = experiment_config["Seed_Stocks"]
    dates = [pd.Timestamp(value).normalize() for value in experiment_config["Signal_Dates"]]
    horizons = experiment_config["Forward_Horizons_Sessions"]
    started = datetime.now(timezone.utc)
    run_id = (
        f"V8BASICFOUND_{started.strftime('%Y%m%dT%H%M%SZ')}_"
        f"{git_value('rev-parse', '--short', 'HEAD')}"
    )
    run_dir = args.output_root.resolve() / run_id
    inputs_dir = run_dir / "inputs"
    prices_dir = inputs_dir / "prices"
    outputs_dir = run_dir / "outputs"
    validation_dir = run_dir / "validation"
    source_dir = run_dir / "source_snapshot"
    for path in (prices_dir, outputs_dir, validation_dir, source_dir / "config", source_dir / "tests"):
        path.mkdir(parents=True, exist_ok=True)

    shutil.copy2(args.config.resolve(), inputs_dir / "V8_Basic_Foundation_Config.json")
    shutil.copy2(
        source_run / "inputs" / "V8_Foundation_Validation_Config.json",
        inputs_dir / "Experiment_Config.json",
    )
    for stock in stocks:
        shutil.copy2(source_run / "inputs" / "prices" / f"{stock}.csv", prices_dir)
    source_files = [
        ROOT / "Momentum_Detector_V8_Basic.py",
        ROOT / "Backtest_Momentum_Detector_V8_Basic_Foundation.py",
        ROOT / "Validate_Momentum_Detector_V8_Basic_Foundation.py",
        ROOT / "tests" / "test_v8_basic_foundation.py",
    ]
    for source in source_files:
        if source.is_file():
            destination = source_dir / source.relative_to(ROOT)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
    shutil.copy2(args.config.resolve(), source_dir / "config" / args.config.name)

    log_lines = []

    def log(message):
        line = f"{datetime.now(timezone.utc).isoformat()} {message}"
        log_lines.append(line)
        print(line, flush=True)

    rows = []
    log(f"RUN_START run_id={run_id} stocks={len(stocks)} dates={len(dates)}")
    for stock in stocks:
        frame = pd.read_csv(prices_dir / f"{stock}.csv", parse_dates=["Date"]).set_index("Date")
        for signal_date in dates:
            result = basic.evaluate_foundation(
                stock,
                frame,
                basic_config,
                as_of=signal_date,
                evaluated_at=started,
            )
            row = {"Run_ID": run_id, **result}
            for horizon in horizons:
                outcome = calculate_outcome(frame, signal_date, horizon)
                row[f"D{horizon}_Entry_Date"] = outcome["Entry_Date"]
                row[f"D{horizon}_Exit_Date"] = outcome["Exit_Date"]
                row[f"D{horizon}_Return_Pct"] = outcome["Return_Pct"]
                row[f"D{horizon}_Positive"] = outcome["Return_Pct"] > 0
            rows.append(row)
            log(
                f"EVALUATE ticker={stock} date={signal_date.date()} "
                f"state={result['Foundation_State']} eligible={result['Foundation_Eligible']} "
                f"d1={row['D1_Return_Pct']:.4f} d5={row['D5_Return_Pct']:.4f} "
                f"d8={row['D8_Return_Pct']:.4f}"
            )

    write_csv(rows, outputs_dir / "foundation_results.csv")
    states = sorted({row["Foundation_State"] for row in rows})
    state_summary = []
    for state in states:
        group = [row for row in rows if row["Foundation_State"] == state]
        summary_row = {
            "Foundation_State": state,
            "Rows": len(group),
            "Eligible_Rows": sum(bool(row["Foundation_Eligible"]) for row in group),
        }
        for horizon in horizons:
            values = [float(row[f"D{horizon}_Return_Pct"]) for row in group]
            summary_row[f"D{horizon}_Positive"] = sum(value > 0 for value in values)
            summary_row[f"D{horizon}_Positive_Rate_Pct"] = 100 * sum(
                value > 0 for value in values
            ) / len(values)
            summary_row[f"D{horizon}_Mean_Return_Pct"] = sum(values) / len(values)
        state_summary.append(summary_row)
    write_csv(state_summary, outputs_dir / "state_summary.csv")

    eligible = [row for row in rows if bool(row["Foundation_Eligible"])]
    aggregate = {
        "Run_ID": run_id,
        "Engine_Version": basic.ENGINE_VERSION,
        "Configuration_ID": basic_config["Configuration_ID"],
        "Stocks": len(stocks),
        "Dates": len(dates),
        "Rows": len(rows),
        "Eligible_Rows": len(eligible),
        "State_Counts": {
            state: sum(row["Foundation_State"] == state for row in rows)
            for state in states
        },
        "Eligible_Directional": {
            f"D{horizon}_Positive": sum(
                float(row[f"D{horizon}_Return_Pct"]) > 0 for row in eligible
            )
            for horizon in horizons
        },
        "Forbidden_Output_Fields_Present": sorted(
            set(rows[0]).intersection(
                {"Score", "Benchmark_Ticker", "ETF_Ticker", "Weekly_Trend", "ATR_Pct"}
            )
        ),
    }
    (outputs_dir / "aggregate_summary.json").write_text(
        json.dumps(aggregate, indent=2), encoding="utf-8"
    )
    (outputs_dir / "execution.log").write_text(
        "\n".join(log_lines) + "\n", encoding="utf-8"
    )
    manifest = {
        **aggregate,
        "Started_UTC": started.isoformat(),
        "Completed_UTC": datetime.now(timezone.utc).isoformat(),
        "Git_Commit": git_value("rev-parse", "HEAD"),
        "Git_Worktree_Dirty": bool(git_value("status", "--porcelain")),
        "Source_Run": str(source_run),
        "Source_Run_Checksums_SHA256": sha256_file(source_run / "checksums.sha256"),
        "Decision_Scope": "FOUNDATION_ONLY_NO_SCORE",
        "Known_Limitations": [
            "Purposeful 20-stock technology sample in one calendar quarter.",
            "No transaction costs, stops, position sizing, or intraday evidence.",
            "This run validates the basic Foundation baseline and does not approve later indicators.",
        ],
    }
    (run_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (run_dir / "command.txt").write_text(
        "python Backtest_Momentum_Detector_V8_Basic_Foundation.py\n", encoding="utf-8"
    )
    (run_dir / "README.md").write_text(
        f"# {run_id}\n\nMinimal V8 EMA/MACD Foundation-only frozen replay. No Score, benchmark, ETF, or post-Foundation indicator authority.\n",
        encoding="utf-8",
    )

    validator = ROOT / "Validate_Momentum_Detector_V8_Basic_Foundation.py"
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
