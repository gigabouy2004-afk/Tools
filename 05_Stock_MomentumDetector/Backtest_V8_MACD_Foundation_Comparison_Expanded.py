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
DEFAULT_EXPERIMENT_CONFIG = ROOT / "config" / "V8_MACD_Foundation_Comparison_Expanded_Config.json"
DEFAULT_OUTPUT_ROOT = ROOT / "backtests" / "V8_MACD_Foundation_Comparison_Expanded" / "runs"


def transition_label(standard_selected, fibonacci_selected):
    if standard_selected and fibonacci_selected:
        return "BOTH"
    if standard_selected:
        return "STANDARD_ONLY"
    if fibonacci_selected:
        return "FIBONACCI_ONLY"
    return "NEITHER"


def selection_metrics(rows, selected_field, horizons):
    selected = [row for row in rows if row[selected_field] is True]
    not_selected = [row for row in rows if row[selected_field] is not True]
    output = {"Rows": len(rows), "Selected": len(selected), "Not_Selected": len(not_selected)}
    for horizon in horizons:
        selected_returns = [float(row[f"D{horizon}_Return_Pct"]) for row in selected]
        rejected_returns = [float(row[f"D{horizon}_Return_Pct"]) for row in not_selected]
        positive = sum(value > 0 for value in selected_returns)
        false_positive = sum(value <= 0 for value in selected_returns)
        false_negative = sum(value > 0 for value in rejected_returns)
        output.update(
            {
                f"D{horizon}_Selected_Positive": positive,
                f"D{horizon}_Selected_Positive_Rate_Pct": (
                    100 * positive / len(selected_returns) if selected_returns else None
                ),
                f"D{horizon}_False_Positive": false_positive,
                f"D{horizon}_False_Positive_Rate_Pct": (
                    100 * false_positive / len(selected_returns) if selected_returns else None
                ),
                f"D{horizon}_False_Negative": false_negative,
                f"D{horizon}_False_Negative_Rate_Among_Not_Selected_Pct": (
                    100 * false_negative / len(rejected_returns) if rejected_returns else None
                ),
                f"D{horizon}_Selected_Mean_Return_Pct": (
                    sum(selected_returns) / len(selected_returns) if selected_returns else None
                ),
            }
        )
    return output


def main():
    experiment = json.loads(DEFAULT_EXPERIMENT_CONFIG.read_text(encoding="utf-8"))
    if experiment.get("No_Indicator_Or_Score_Tuning_During_Run") is not True:
        raise ValueError("dual-MACD experiment must prohibit indicator and Score tuning")
    source_run = (ROOT / experiment["Source_Run"]).resolve()
    source_experiment = json.loads(
        (source_run / "inputs" / "Experiment_Config.json").read_text(encoding="utf-8")
    )
    dates = source_experiment["Signal_Dates"]
    sector_pairs = [
        (ticker, sector)
        for sector, tickers in source_experiment["Sector_Stocks"].items()
        for ticker in tickers
    ]
    horizons = [int(value) for value in experiment["Forward_Horizons_Sessions"]]
    variants = experiment["MACD_Variants"]
    variant_configs = {}
    for name, periods in variants.items():
        if name == "STANDARD_12_26_9":
            config = basic.load_config()
        else:
            config = basic.load_config(
                overrides={
                    "MACD.Fast": periods["Fast"],
                    "MACD.Slow": periods["Slow"],
                    "MACD.Signal": periods["Signal"],
                }
            )
        variant_configs[name] = config

    started = datetime.now(timezone.utc)
    run_id = f"V8MACDCMP_{started.strftime('%Y%m%dT%H%M%SZ')}_{git_value('rev-parse', '--short', 'HEAD')}"
    run_dir = DEFAULT_OUTPUT_ROOT / run_id
    inputs_dir = run_dir / "inputs"
    prices_dir = inputs_dir / "prices"
    outputs_dir = run_dir / "outputs"
    charts_dir = run_dir / "charts"
    validation_dir = run_dir / "validation"
    source_dir = run_dir / "source_snapshot"
    for path in (prices_dir, outputs_dir, charts_dir, validation_dir, source_dir / "config", source_dir / "tests"):
        path.mkdir(parents=True, exist_ok=True)
    shutil.copy2(DEFAULT_EXPERIMENT_CONFIG, inputs_dir / DEFAULT_EXPERIMENT_CONFIG.name)
    shutil.copy2(source_run / "inputs" / "Experiment_Config.json", inputs_dir / "Universe_Experiment_Config.json")
    shutil.copy2(basic.DEFAULT_CONFIG_PATH, inputs_dir / basic.DEFAULT_CONFIG_PATH.name)
    shutil.copy2(
        ROOT / "config" / "V8_V1_V3_Indicator_Baseline_Config.json",
        inputs_dir / "V8_V1_V3_Indicator_Baseline_Config.json",
    )
    for ticker, _ in sector_pairs:
        shutil.copy2(source_run / "inputs" / "prices" / f"{ticker}.csv", prices_dir)

    log_lines = []

    def log(message):
        line = f"{datetime.now(timezone.utc).isoformat()} {message}"
        log_lines.append(line)
        print(line, flush=True)

    rows = []
    log(f"RUN_START run_id={run_id} stocks={len(sector_pairs)} dates={len(dates)} variants={len(variants)}")
    for ticker, sector in sector_pairs:
        frame = pd.read_csv(prices_dir / f"{ticker}.csv", parse_dates=["Date"]).set_index("Date")
        for signal_date in dates:
            for variant_name, config in variant_configs.items():
                result = basic.evaluate_foundation(
                    ticker, frame, config, as_of=signal_date, evaluated_at=started
                )
                row = {"Run_ID": run_id, "Sector": sector, "MACD_Variant": variant_name, **result}
                for horizon in horizons:
                    measured = calculate_outcome(frame, pd.Timestamp(signal_date), horizon)
                    row[f"D{horizon}_Entry_Date"] = measured["Entry_Date"]
                    row[f"D{horizon}_Exit_Date"] = measured["Exit_Date"]
                    row[f"D{horizon}_Return_Pct"] = measured["Return_Pct"]
                    row[f"D{horizon}_Positive"] = measured["Return_Pct"] > 0
                rows.append(row)
        log(f"EVALUATED ticker={ticker} sector={sector} rows={len(dates) * len(variants)}")
    write_csv(rows, outputs_dir / "macd_comparison_results.csv")
    (outputs_dir / "execution.log").write_text("\n".join(log_lines) + "\n", encoding="utf-8")

    summary_rows = []
    stage_fields = {"FOUNDATION": "Foundation_Eligible", "HEALTH_QUALIFIED": "Health_Qualified"}
    for variant_name in variants:
        for sector in ["ALL", *source_experiment["Sector_Stocks"]]:
            group = [
                row
                for row in rows
                if row["MACD_Variant"] == variant_name
                and (sector == "ALL" or row["Sector"] == sector)
            ]
            for stage, selected_field in stage_fields.items():
                summary_rows.append(
                    {
                        "MACD_Variant": variant_name,
                        "Sector": sector,
                        "Stage": stage,
                        **selection_metrics(group, selected_field, horizons),
                    }
                )
    write_csv(summary_rows, outputs_dir / "selection_summary.csv")

    standard = {
        (row["Ticker"], row["As_Of_Date"]): row
        for row in rows
        if row["MACD_Variant"] == "STANDARD_12_26_9"
    }
    fibonacci = {
        (row["Ticker"], row["As_Of_Date"]): row
        for row in rows
        if row["MACD_Variant"] == "FIBONACCI_8_21_5"
    }
    transition_rows = []
    transition_summary = []
    for stage, selected_field in stage_fields.items():
        for key, standard_row in standard.items():
            fibonacci_row = fibonacci[key]
            transition_rows.append(
                {
                    "Stage": stage,
                    "Sector": standard_row["Sector"],
                    "Ticker": key[0],
                    "As_Of_Date": key[1],
                    "Transition": transition_label(
                        standard_row[selected_field] is True,
                        fibonacci_row[selected_field] is True,
                    ),
                    "Standard_MACD_Line": standard_row["MACD_Line"],
                    "Standard_MACD_Signal": standard_row["MACD_Signal_Line"],
                    "Fibonacci_MACD_Line": fibonacci_row["MACD_Line"],
                    "Fibonacci_MACD_Signal": fibonacci_row["MACD_Signal_Line"],
                    **{
                        f"D{horizon}_Return_Pct": standard_row[f"D{horizon}_Return_Pct"]
                        for horizon in horizons
                    },
                }
            )
        for sector in ["ALL", *source_experiment["Sector_Stocks"]]:
            scoped = [
                row
                for row in transition_rows
                if row["Stage"] == stage and (sector == "ALL" or row["Sector"] == sector)
            ]
            for transition in ("BOTH", "STANDARD_ONLY", "FIBONACCI_ONLY", "NEITHER"):
                cohort = [row for row in scoped if row["Transition"] == transition]
                item = {"Stage": stage, "Sector": sector, "Transition": transition, "Rows": len(cohort)}
                for horizon in horizons:
                    values = [float(row[f"D{horizon}_Return_Pct"]) for row in cohort]
                    item[f"D{horizon}_Positive_Rate_Pct"] = (
                        100 * sum(value > 0 for value in values) / len(values) if values else None
                    )
                    item[f"D{horizon}_Mean_Return_Pct"] = (
                        sum(values) / len(values) if values else None
                    )
                transition_summary.append(item)
    write_csv(transition_rows, outputs_dir / "transition_rows.csv")
    write_csv(transition_summary, outputs_dir / "transition_summary.csv")

    aggregate = {
        "Run_ID": run_id,
        "Experiment_ID": experiment["Experiment_ID"],
        "Stocks": len(sector_pairs),
        "Dates": len(dates),
        "Variants": len(variants),
        "Rows": len(rows),
        "Horizons": horizons,
        "False_Positive_Definition": experiment["False_Positive_Definition"],
        "False_Negative_Definition": experiment["False_Negative_Definition"],
        "Selection_Summary": summary_rows,
        "Transition_Summary": transition_summary,
    }
    (outputs_dir / "aggregate_summary.json").write_text(json.dumps(aggregate, indent=2), encoding="utf-8")

    source_files = [
        ROOT / "Momentum_Detector_V8_Basic.py",
        ROOT / "Backtest_V8_MACD_Foundation_Comparison_Expanded.py",
        ROOT / "Validate_V8_MACD_Foundation_Comparison_Expanded.py",
        ROOT / "Plot_V8_MACD_Foundation_Comparison.py",
        ROOT / "tests" / "test_v8_macd_foundation_comparison_expanded.py",
    ]
    for source in source_files:
        if source.is_file():
            destination = source_dir / source.relative_to(ROOT)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
    shutil.copy2(DEFAULT_EXPERIMENT_CONFIG, source_dir / "config" / DEFAULT_EXPERIMENT_CONFIG.name)
    shutil.copy2(basic.DEFAULT_CONFIG_PATH, source_dir / "config" / basic.DEFAULT_CONFIG_PATH.name)
    shutil.copy2(
        ROOT / "config" / "V8_V1_V3_Indicator_Baseline_Config.json",
        source_dir / "config" / "V8_V1_V3_Indicator_Baseline_Config.json",
    )

    plotter = ROOT / "Plot_V8_MACD_Foundation_Comparison.py"
    plotted = subprocess.run([sys.executable, str(plotter), str(run_dir)], cwd=ROOT, text=True, capture_output=True)
    if plotted.returncode:
        raise RuntimeError(plotted.stdout + plotted.stderr)
    (charts_dir / "plotter_console.txt").write_text(plotted.stdout + plotted.stderr, encoding="utf-8")

    manifest = {
        **aggregate,
        "Started_UTC": started.isoformat(),
        "Completed_UTC": datetime.now(timezone.utc).isoformat(),
        "Git_Commit": git_value("rev-parse", "HEAD"),
        "Git_Worktree_Dirty": bool(git_value("status", "--porcelain")),
        "Source_Run": str(source_run),
        "Known_Limitations": [
            "Purposeful current-universe sample retains survivorship and selection limitations.",
            "A positive forward return is a directional test, not a complete trade simulation.",
            "False positive means selected with return <=0 from D+1 open to the stated horizon close.",
            "No sector benchmark, ETF mapping, indicator value, component point, or threshold was changed.",
        ],
    }
    (run_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (run_dir / "README.md").write_text(
        f"# {run_id}\n\nMACD 12/26/9 versus 8/21/5 Foundation and Health Score comparison.\n",
        encoding="utf-8",
    )
    (run_dir / "command.txt").write_text(
        "python Backtest_V8_MACD_Foundation_Comparison_Expanded.py\n", encoding="utf-8"
    )

    validator = ROOT / "Validate_V8_MACD_Foundation_Comparison_Expanded.py"
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
        [sys.executable, str(validator), str(run_dir)], cwd=ROOT, text=True, capture_output=True
    )
    (validation_dir / "validator_console.txt").write_text(final.stdout + final.stderr, encoding="utf-8")
    if final.returncode:
        raise RuntimeError(final.stdout + final.stderr)
    print(f"CHECKSUMS_WRITTEN entries={checksum_count}")
    print(f"RUN_COMPLETE run_dir={run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
