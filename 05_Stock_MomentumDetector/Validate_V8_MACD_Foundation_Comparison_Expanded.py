import argparse
import hashlib
import json
import math
from pathlib import Path

import pandas as pd

import Validate_V8_V1_V3_Indicator_Baseline as independent


NUMERIC_MAP = {
    "Close": "Close",
    "EMA_Value": "EMA_200",
    "MACD_Line": "MACD_Line",
    "MACD_Signal_Line": "MACD_Signal",
    "RSI": "RSI",
    "ADX": "ADX",
    "DMI_Positive": "DMI_Positive",
    "DMI_Negative": "DMI_Negative",
    "OBV": "OBV",
    "OBV_EMA": "OBV_EMA_20",
    "ATR": "ATR_14",
}


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize(value):
    if pd.isna(value) or value == "":
        return ""
    text = str(value).strip()
    if text.lower() in {"true", "false"}:
        return text.lower() == "true"
    try:
        number = float(text)
        return int(number) if number.is_integer() else number
    except ValueError:
        return text


def numeric_equal(left, right, tolerance=1e-9):
    left_blank = pd.isna(left) or left == ""
    right_blank = pd.isna(right) or right == ""
    if left_blank or right_blank:
        return left_blank and right_blank
    return math.isclose(float(left), float(right), rel_tol=tolerance, abs_tol=tolerance)


def verify_checksums(run_dir):
    failures = []
    checked = 0
    for line in (run_dir / "checksums.sha256").read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", 1)
        path = run_dir / relative
        checked += 1
        if not path.is_file() or sha256_file(path) != expected:
            failures.append(f"checksum mismatch: {relative}")
    return checked, failures


def validate(run_dir, skip_checksums=False):
    failures = []
    experiment = json.loads(
        (run_dir / "inputs" / "V8_MACD_Foundation_Comparison_Expanded_Config.json").read_text(
            encoding="utf-8"
        )
    )
    universe = json.loads(
        (run_dir / "inputs" / "Universe_Experiment_Config.json").read_text(encoding="utf-8")
    )
    baseline_config = json.loads(
        (run_dir / "inputs" / "V8_V1_V3_Indicator_Baseline_Config.json").read_text(
            encoding="utf-8"
        )
    )
    results = pd.read_csv(run_dir / "outputs" / "macd_comparison_results.csv", keep_default_na=False)
    stock_pairs = [
        (ticker, sector)
        for sector, tickers in universe["Sector_Stocks"].items()
        for ticker in tickers
    ]
    variants = experiment["MACD_Variants"]
    expected_rows = len(stock_pairs) * len(universe["Signal_Dates"]) * len(variants)
    if len(results) != expected_rows:
        failures.append(f"row count {len(results)} != {expected_rows}")
    if experiment.get("No_Indicator_Or_Score_Tuning_During_Run") is not True:
        failures.append("experiment tuning guard is not true")
    if set(variants) != {"STANDARD_12_26_9", "FIBONACCI_8_21_5"}:
        failures.append("MACD variants are not the declared pair")

    independent_rows = []
    for ticker, sector in stock_pairs:
        prices = pd.read_csv(
            run_dir / "inputs" / "prices" / f"{ticker}.csv", parse_dates=["Date"]
        ).set_index("Date")
        for signal_date in universe["Signal_Dates"]:
            for variant_name, periods in variants.items():
                selected = results.loc[
                    (results["Ticker"] == ticker)
                    & (results["As_Of_Date"] == signal_date)
                    & (results["MACD_Variant"] == variant_name)
                ]
                if len(selected) != 1:
                    failures.append(f"missing/non-unique {ticker} {signal_date} {variant_name}")
                    continue
                actual = selected.iloc[0]
                config = json.loads(json.dumps(baseline_config))
                config["MACD"] = periods
                expected = independent.independent_row(prices, signal_date, "V1", config)
                changed = []
                for actual_field, expected_field in NUMERIC_MAP.items():
                    if not numeric_equal(actual[actual_field], expected[expected_field]):
                        changed.append(actual_field)
                exact_map = {
                    "Foundation_Eligible": "Foundation_Eligible",
                    "Foundation_State": "Foundation_State",
                    "DMI_Eligible": "DMI_Dominance_Pass",
                }
                for actual_field, expected_field in exact_map.items():
                    if normalize(actual[actual_field]) != normalize(expected[expected_field]):
                        changed.append(actual_field)
                dmi_pass = expected["DMI_Dominance_Pass"] is True
                if dmi_pass:
                    score_map = {
                        "RSI_Score": "RSI_Score",
                        "RSI_Score_Status": "RSI_Status",
                        "ADX_Score": "ADX_Score",
                        "ADX_Score_Status": "ADX_Status",
                        "OBV_Score": "OBV_Score",
                        "OBV_Score_Status": "OBV_Status",
                        "OBV_Fresh_Cross": "OBV_Fresh_Cross",
                        "Raw_Health_Score": "Total_Momentum_Score",
                        "Health_Qualified": "V1_V3_Qualified",
                    }
                    for actual_field, expected_field in score_map.items():
                        if normalize(actual[actual_field]) != normalize(expected[expected_field]):
                            changed.append(actual_field)
                elif actual["Raw_Health_Score"] != "":
                    changed.append("score executed without DMI eligibility")
                for horizon in experiment["Forward_Horizons_Sessions"]:
                    entry_date, exit_date, return_pct = independent.outcome(
                        prices, signal_date, int(horizon)
                    )
                    if actual[f"D{horizon}_Entry_Date"] != entry_date:
                        changed.append(f"D{horizon}_Entry_Date")
                    if actual[f"D{horizon}_Exit_Date"] != exit_date:
                        changed.append(f"D{horizon}_Exit_Date")
                    if not numeric_equal(actual[f"D{horizon}_Return_Pct"], return_pct):
                        changed.append(f"D{horizon}_Return_Pct")
                if changed:
                    failures.append(
                        f"{ticker} {signal_date} {variant_name}: {', '.join(changed)}"
                    )
                independent_rows.append(
                    {
                        "Ticker": ticker,
                        "Sector": sector,
                        "As_Of_Date": signal_date,
                        "MACD_Variant": variant_name,
                        "Foundation_Eligible": expected["Foundation_Eligible"],
                        "DMI_Eligible": expected["DMI_Dominance_Pass"],
                        "Raw_Health_Score": expected["Total_Momentum_Score"] if dmi_pass else "",
                        "Health_Qualified": expected["V1_V3_Qualified"],
                        "Comparison_Pass": not changed,
                    }
                )
    validation_dir = run_dir / "validation"
    validation_dir.mkdir(exist_ok=True)
    pd.DataFrame(independent_rows).to_csv(
        validation_dir / "independently_recomputed_rows.csv", index=False
    )
    chart_files = [
        run_dir / "charts" / "false_positive_rate_comparison.png",
        run_dir / "charts" / "selection_count_comparison.png",
        run_dir / "charts" / "macd_line_signal_disagreement_examples.png",
        run_dir / "charts" / "chart_manifest.json",
    ]
    for chart in chart_files:
        if not chart.is_file() or chart.stat().st_size == 0:
            failures.append(f"missing/empty chart evidence: {chart.name}")
    checksum_count = 0
    if not skip_checksums:
        checksum_count, checksum_failures = verify_checksums(run_dir)
        failures.extend(checksum_failures)
    summary = {
        "Validation_Status": "PASS" if not failures else "FAIL",
        "Rows_Checked": len(independent_rows),
        "Expected_Rows": expected_rows,
        "Independent_Dual_MACD_Foundation_Recalculation": True,
        "Independent_DMI_Component_Score_And_Outcome_Recalculation": True,
        "D1_D3_Outcomes_Checked": True,
        "Chart_Evidence_Checked": True,
        "Checksums_Checked": checksum_count,
        "Failures": failures,
    }
    (validation_dir / "validation_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    return summary


def main():
    parser = argparse.ArgumentParser(description="Validate expanded dual-MACD comparison")
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--skip-checksums", action="store_true")
    args = parser.parse_args()
    summary = validate(args.run_dir.resolve(), args.skip_checksums)
    print(json.dumps(summary, indent=2))
    return 0 if summary["Validation_Status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
