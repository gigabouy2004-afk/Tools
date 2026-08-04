import csv
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

import V8_V1_V3_Indicator_Baseline as baseline


ROOT = Path(__file__).resolve().parent
DEFAULT_SOURCE_RUN = (
    ROOT
    / "backtests"
    / "V8_Foundation_Validation"
    / "runs"
    / "V8FOUND_20260712T182945Z_cf0c908"
)
DEFAULT_OUTPUT_ROOT = ROOT / "backtests" / "V8_V1_V3_Indicator_Baseline" / "runs"


def git_value(*args):
    try:
        return subprocess.check_output(
            ["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "UNKNOWN"


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
    position = frame.index.get_loc(pd.Timestamp(signal_date))
    if not isinstance(position, int):
        position = int(position[0])
    entry = frame.iloc[position + 1]
    exit_row = frame.iloc[position + int(horizon)]
    return {
        "Entry_Date": entry.name.date().isoformat(),
        "Exit_Date": exit_row.name.date().isoformat(),
        "Return_Pct": ((float(exit_row["Close"]) / float(entry["Open"])) - 1) * 100,
    }


def mean(values):
    return sum(values) / len(values) if values else None


def main():
    config = baseline.load_config()
    source_run = DEFAULT_SOURCE_RUN.resolve()
    experiment = json.loads(
        (source_run / "inputs" / "V8_Foundation_Validation_Config.json").read_text(
            encoding="utf-8"
        )
    )
    stocks = experiment["Seed_Stocks"]
    dates = [pd.Timestamp(value).normalize() for value in experiment["Signal_Dates"]]
    horizons = [int(value) for value in config["Forward_Horizons_Sessions"]]
    started = datetime.now(timezone.utc)
    run_id = (
        f"V8V1V3_{started.strftime('%Y%m%dT%H%M%SZ')}_"
        f"{git_value('rev-parse', '--short', 'HEAD')}"
    )
    run_dir = DEFAULT_OUTPUT_ROOT.resolve() / run_id
    inputs_dir = run_dir / "inputs"
    prices_dir = inputs_dir / "prices"
    outputs_dir = run_dir / "outputs"
    validation_dir = run_dir / "validation"
    source_dir = run_dir / "source_snapshot"
    for path in (
        prices_dir,
        outputs_dir,
        validation_dir,
        source_dir / "config",
        source_dir / "tests",
    ):
        path.mkdir(parents=True, exist_ok=True)

    shutil.copy2(baseline.DEFAULT_CONFIG_PATH, inputs_dir / baseline.DEFAULT_CONFIG_PATH.name)
    shutil.copy2(
        source_run / "inputs" / "V8_Foundation_Validation_Config.json",
        inputs_dir / "Experiment_Config.json",
    )
    for stock in stocks:
        shutil.copy2(source_run / "inputs" / "prices" / f"{stock}.csv", prices_dir)
    source_files = [
        ROOT / "V8_V1_V3_Indicator_Baseline.py",
        ROOT / "Backtest_V8_V1_V3_Indicator_Baseline.py",
        ROOT / "Validate_V8_V1_V3_Indicator_Baseline.py",
        ROOT / "tests" / "test_v8_v1_v3_indicator_baseline.py",
    ]
    for source in source_files:
        if source.is_file():
            destination = source_dir / source.relative_to(ROOT)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
    shutil.copy2(
        baseline.DEFAULT_CONFIG_PATH,
        source_dir / "config" / baseline.DEFAULT_CONFIG_PATH.name,
    )

    log_lines = []

    def log(message):
        line = f"{datetime.now(timezone.utc).isoformat()} {message}"
        log_lines.append(line)
        print(line, flush=True)

    rows = []
    log(
        f"RUN_START run_id={run_id} stocks={len(stocks)} dates={len(dates)} "
        f"profiles={len(config['Profiles'])}"
    )
    for stock in stocks:
        frame = pd.read_csv(prices_dir / f"{stock}.csv", parse_dates=["Date"]).set_index("Date")
        for signal_date in dates:
            for profile in config["Profiles"]:
                result = baseline.evaluate_profile(
                    stock,
                    frame,
                    signal_date,
                    profile,
                    config,
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
                    f"EVALUATE profile={profile} ticker={stock} date={signal_date.date()} "
                    f"foundation={result['Foundation_Eligible']} dmi={result['DMI_Dominance_Pass']} "
                    f"score={result['Total_Momentum_Score']} qualified={result['V1_V3_Qualified']}"
                )

    write_csv(rows, outputs_dir / "profile_results.csv")
    profile_summary = []
    for profile in config["Profiles"]:
        group = [row for row in rows if row["Profile"] == profile]
        qualified = [row for row in group if row["V1_V3_Qualified"] is True]
        summary = {
            "Profile": profile,
            "Rows": len(group),
            "Foundation_Eligible": sum(row["Foundation_Eligible"] is True for row in group),
            "DMI_Dominance_Pass": sum(row["DMI_Dominance_Pass"] is True for row in group),
            "Qualified": len(qualified),
            "Mean_Total_Score_Foundation_Eligible": mean(
                [
                    float(row["Total_Momentum_Score"])
                    for row in group
                    if row["Foundation_Eligible"] is True
                ]
            ),
        }
        for horizon in horizons:
            returns = [float(row[f"D{horizon}_Return_Pct"]) for row in qualified]
            summary[f"Qualified_D{horizon}_Positive"] = sum(value > 0 for value in returns)
            summary[f"Qualified_D{horizon}_Positive_Rate_Pct"] = (
                100 * sum(value > 0 for value in returns) / len(returns) if returns else None
            )
            summary[f"Qualified_D{horizon}_Mean_Return_Pct"] = mean(returns)
        profile_summary.append(summary)
    write_csv(profile_summary, outputs_dir / "profile_summary.csv")

    v1 = {
        (row["Ticker"], row["As_Of_Date"]): row
        for row in rows
        if row["Profile"] == "V1"
    }
    v2 = {
        (row["Ticker"], row["As_Of_Date"]): row
        for row in rows
        if row["Profile"] == "V2"
    }
    comparison_fields = [
        "Foundation_Eligible",
        "Foundation_State",
        "DMI_Dominance_Pass",
        "RSI",
        "RSI_Score",
        "ADX",
        "ADX_Score",
        "OBV_Score",
        "ATR_14",
        "Total_Momentum_Score",
        "V1_V3_Qualified",
    ]
    v1_v2_differences = []
    for key, left in v1.items():
        changed = [field for field in comparison_fields if str(left[field]) != str(v2[key][field])]
        if changed:
            v1_v2_differences.append({"Ticker": key[0], "As_Of_Date": key[1], "Fields": ";".join(changed)})
    write_csv(v1_v2_differences or [{"Ticker": "", "As_Of_Date": "", "Fields": ""}], outputs_dir / "v1_v2_differences.csv")

    aggregate = {
        "Run_ID": run_id,
        "Configuration_ID": config["Configuration_ID"],
        "Limit_Status": config["Limit_Status"],
        "Operational_Use_Approved": config["Operational_Use_Approved"],
        "Stocks": len(stocks),
        "Dates": len(dates),
        "Profiles": len(config["Profiles"]),
        "Rows": len(rows),
        "V1_V2_Technical_Differences": len(v1_v2_differences),
        "Profile_Summary": profile_summary,
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
        "Known_Limitations": [
            "Purposeful 20-stock technology sample and four dates in one quarter.",
            "V1 and V2 have identical technical values; their historical difference was data handling.",
            "Original 260d request was replaced by 300 minimum bars for reliable point-in-time calculation.",
            "No transaction costs, stops, sizing, intraday overrides, or operational authority.",
        ],
    }
    (run_dir / "run_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    (run_dir / "README.md").write_text(
        f"# {run_id}\n\nFrozen V1-V3 historical indicator-value replay. Research candidate only; not operationally approved.\n",
        encoding="utf-8",
    )
    (run_dir / "command.txt").write_text(
        "python Backtest_V8_V1_V3_Indicator_Baseline.py\n", encoding="utf-8"
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
