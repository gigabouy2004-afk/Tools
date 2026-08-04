import csv
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

import Momentum_Detector_V8_Basic as basic
from Backtest_Momentum_Detector_V8_Basic_Foundation import (
    calculate_outcome,
    git_value,
    write_checksums,
    write_csv,
)


ROOT = Path(__file__).resolve().parent
DEFAULT_SOURCE_RUN = (
    ROOT
    / "backtests"
    / "V8_V1_V3_Composite_Score_Expanded"
    / "runs"
    / "V8SCORE_20260712T230552Z_2fcd424"
)
DEFAULT_OUTPUT_ROOT = ROOT / "backtests" / "V8_Basic_Health_Score" / "runs"


def cohort_metrics(rows, horizons):
    output = {"Rows": len(rows)}
    for horizon in horizons:
        values = [float(row[f"D{horizon}_Return_Pct"]) for row in rows]
        output[f"D{horizon}_Positive"] = sum(value > 0 for value in values)
        output[f"D{horizon}_Positive_Rate_Pct"] = (
            100 * sum(value > 0 for value in values) / len(values) if values else None
        )
        output[f"D{horizon}_Mean_Return_Pct"] = (
            sum(values) / len(values) if values else None
        )
    return output


def main():
    config = basic.load_config()
    source_run = DEFAULT_SOURCE_RUN.resolve()
    experiment = json.loads(
        (source_run / "inputs" / "Experiment_Config.json").read_text(encoding="utf-8")
    )
    source_validation = json.loads(
        (source_run / "validation" / "validation_summary.json").read_text(encoding="utf-8")
    )
    if source_validation["Validation_Status"] != "PASS":
        raise RuntimeError("expanded V1 reference run is not independently validated")
    started = datetime.now(timezone.utc)
    run_id = (
        f"V8HEALTH_{started.strftime('%Y%m%dT%H%M%SZ')}_"
        f"{git_value('rev-parse', '--short', 'HEAD')}"
    )
    run_dir = DEFAULT_OUTPUT_ROOT / run_id
    inputs_dir = run_dir / "inputs"
    prices_dir = inputs_dir / "prices"
    outputs_dir = run_dir / "outputs"
    validation_dir = run_dir / "validation"
    source_dir = run_dir / "source_snapshot"
    for path in (prices_dir, outputs_dir, validation_dir, source_dir / "config", source_dir / "tests"):
        path.mkdir(parents=True, exist_ok=True)

    shutil.copy2(basic.DEFAULT_CONFIG_PATH, inputs_dir / basic.DEFAULT_CONFIG_PATH.name)
    shutil.copy2(source_run / "inputs" / "Experiment_Config.json", inputs_dir / "Experiment_Config.json")
    shutil.copy2(source_run / "validation" / "validation_summary.json", inputs_dir / "Source_Validation_Summary.json")
    source_results = pd.read_csv(source_run / "outputs" / "profile_results.csv", keep_default_na=False)
    reference = source_results.loc[source_results["Profile"] == "V1"].copy()
    reference.to_csv(inputs_dir / "Validated_V1_Reference.csv", index=False)

    sector_pairs = [
        (ticker, sector)
        for sector, tickers in experiment["Sector_Stocks"].items()
        for ticker in tickers
    ]
    for ticker, _ in sector_pairs:
        shutil.copy2(source_run / "inputs" / "prices" / f"{ticker}.csv", prices_dir)

    log_lines = []

    def log(message):
        line = f"{datetime.now(timezone.utc).isoformat()} {message}"
        log_lines.append(line)
        print(line, flush=True)

    dates = experiment["Signal_Dates"]
    horizons = [int(value) for value in experiment["Forward_Horizons_Sessions"]]
    rows = []
    log(f"RUN_START run_id={run_id} stocks={len(sector_pairs)} dates={len(dates)}")
    for ticker, sector in sector_pairs:
        frame = pd.read_csv(prices_dir / f"{ticker}.csv", parse_dates=["Date"]).set_index("Date")
        for signal_date in dates:
            result = basic.evaluate_foundation(
                ticker, frame, config, as_of=signal_date, evaluated_at=started
            )
            row = {"Run_ID": run_id, "Sector": sector, **result}
            for horizon in horizons:
                measured = calculate_outcome(frame, pd.Timestamp(signal_date), horizon)
                row[f"D{horizon}_Entry_Date"] = measured["Entry_Date"]
                row[f"D{horizon}_Exit_Date"] = measured["Exit_Date"]
                row[f"D{horizon}_Return_Pct"] = measured["Return_Pct"]
                row[f"D{horizon}_Positive"] = measured["Return_Pct"] > 0
            rows.append(row)
        log(f"EVALUATED ticker={ticker} sector={sector} rows={len(dates)}")
    write_csv(rows, outputs_dir / "health_score_results.csv")
    (outputs_dir / "execution.log").write_text("\n".join(log_lines) + "\n", encoding="utf-8")

    summaries = []
    for sector in ["ALL", *experiment["Sector_Stocks"]]:
        group = [row for row in rows if sector == "ALL" or row["Sector"] == sector]
        foundation = [row for row in group if row["Foundation_Eligible"] is True]
        dmi = [row for row in foundation if row["DMI_Eligible"] is True]
        qualified = [row for row in dmi if row["Health_Qualified"] is True]
        summaries.append(
            {
                "Sector": sector,
                "Rows": len(group),
                "Foundation_Eligible": len(foundation),
                "DMI_Eligible": len(dmi),
                "Health_Qualified": len(qualified),
                **{
                    f"Qualified_{key}": value
                    for key, value in cohort_metrics(qualified, horizons).items()
                    if key != "Rows"
                },
            }
        )
    write_csv(summaries, outputs_dir / "sector_summary.csv")
    aggregate = {
        "Run_ID": run_id,
        "Configuration_ID": config["Configuration_ID"],
        "Engine_Version": basic.ENGINE_VERSION,
        "Decision_Scope": config["Decision_Scope"],
        "Stocks": len(sector_pairs),
        "Dates": len(dates),
        "Rows": len(rows),
        "Health_Score_Maximum": config["Health_Score"]["Maximum_Positive_Score"],
        "Research_Qualification_Threshold": config["Health_Score"]["Research_Qualification_Threshold"],
        "Operational_Use_Approved": config["Health_Score"]["Operational_Use_Approved"],
        "Sector_Summary": summaries,
    }
    (outputs_dir / "aggregate_summary.json").write_text(json.dumps(aggregate, indent=2), encoding="utf-8")

    source_files = [
        ROOT / "Momentum_Detector_V8_Basic.py",
        ROOT / "Backtest_V8_Basic_Health_Score.py",
        ROOT / "Validate_V8_Basic_Health_Score.py",
        ROOT / "tests" / "test_v8_basic_foundation.py",
    ]
    for source in source_files:
        if source.is_file():
            destination = source_dir / source.relative_to(ROOT)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
    shutil.copy2(basic.DEFAULT_CONFIG_PATH, source_dir / "config" / basic.DEFAULT_CONFIG_PATH.name)
    manifest = {
        **aggregate,
        "Started_UTC": started.isoformat(),
        "Completed_UTC": datetime.now(timezone.utc).isoformat(),
        "Git_Commit": git_value("rev-parse", "HEAD"),
        "Git_Worktree_Dirty": bool(git_value("status", "--porcelain")),
        "Validated_Reference_Run": str(source_run),
        "Known_Limitations": [
            "Research qualification only; no operational trade authority.",
            "The Health Score is not a calibrated probability or linear rank.",
            "Purposeful current-universe sample retains survivorship and selection limitations.",
            "MACD 12/26/9 is used because that is the integrated configuration validated with the V1 Score.",
        ],
    }
    (run_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (run_dir / "README.md").write_text(
        f"# {run_id}\n\nIntegrated V8 Basic V1 Health Score replay. Research only.\n",
        encoding="utf-8",
    )
    (run_dir / "command.txt").write_text("python Backtest_V8_Basic_Health_Score.py\n", encoding="utf-8")

    validator = ROOT / "Validate_V8_Basic_Health_Score.py"
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
    (validation_dir / "validator_console.txt").write_text(final.stdout + final.stderr, encoding="utf-8")
    if final.returncode:
        raise RuntimeError(final.stdout + final.stderr)
    print(f"CHECKSUMS_WRITTEN entries={checksum_count}")
    print(f"RUN_COMPLETE run_dir={run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
