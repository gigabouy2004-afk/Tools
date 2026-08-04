import argparse
import hashlib
import json
import math
from pathlib import Path

import pandas as pd


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


def as_bool(value):
    return str(value).strip().lower() in {"true", "1"}


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
    config = json.loads((run_dir / "inputs" / "V8_Basic_Foundation_Config.json").read_text(encoding="utf-8"))
    experiment = json.loads((run_dir / "inputs" / "Experiment_Config.json").read_text(encoding="utf-8"))
    source_validation = json.loads((run_dir / "inputs" / "Source_Validation_Summary.json").read_text(encoding="utf-8"))
    results = pd.read_csv(run_dir / "outputs" / "health_score_results.csv", keep_default_na=False)
    reference = pd.read_csv(run_dir / "inputs" / "Validated_V1_Reference.csv", keep_default_na=False)
    expected_rows = sum(len(values) for values in experiment["Sector_Stocks"].values()) * len(experiment["Signal_Dates"])
    if source_validation.get("Validation_Status") != "PASS":
        failures.append("validated V1 source evidence is not PASS")
    if len(results) != expected_rows or len(reference) != expected_rows:
        failures.append(f"row count mismatch: result={len(results)} reference={len(reference)} expected={expected_rows}")
    if config.get("Decision_Scope") != "FOUNDATION_THEN_DMI_THEN_V1_COMPOSITE_HEALTH_SCORE":
        failures.append("wrong integrated decision scope")
    if config["Health_Score"].get("Operational_Use_Approved") is not False:
        failures.append("research Health Score incorrectly claims operational approval")
    if config["Health_Score"].get("Probability_Calibrated") is not False:
        failures.append("research Health Score incorrectly claims probability calibration")

    reference_by_key = {
        (row["Ticker"], row["As_Of_Date"]): row for _, row in reference.iterrows()
    }
    difference_rows = []
    for _, actual in results.iterrows():
        key = (actual["Ticker"], actual["As_Of_Date"])
        expected = reference_by_key.get(key)
        changed = []
        if expected is None:
            changed.append("missing reference")
        else:
            if as_bool(actual["Foundation_Eligible"]) != as_bool(expected["Foundation_Eligible"]):
                changed.append("Foundation_Eligible")
            if actual["Foundation_State"] != expected["Foundation_State"]:
                changed.append("Foundation_State")
            for actual_field, reference_field in NUMERIC_MAP.items():
                if not numeric_equal(actual[actual_field], expected[reference_field]):
                    changed.append(actual_field)
            reference_dmi = as_bool(expected["DMI_Dominance_Pass"]) if expected["DMI_Dominance_Pass"] != "" else ""
            actual_dmi = as_bool(actual["DMI_Eligible"]) if actual["DMI_Eligible"] != "" else ""
            if actual_dmi != reference_dmi:
                changed.append("DMI_Eligible")
            if actual_dmi is True:
                exact_map = {
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
                for actual_field, reference_field in exact_map.items():
                    left = str(actual[actual_field]).strip().lower()
                    right = str(expected[reference_field]).strip().lower()
                    if left != right:
                        changed.append(actual_field)
            else:
                if actual["Raw_Health_Score"] != "" or actual["RSI_Score"] != "":
                    changed.append("score executed before DMI eligibility")
            for horizon in experiment["Forward_Horizons_Sessions"]:
                for suffix in ("Entry_Date", "Exit_Date"):
                    field = f"D{horizon}_{suffix}"
                    if actual[field] != expected[field]:
                        changed.append(field)
                field = f"D{horizon}_Return_Pct"
                if not numeric_equal(actual[field], expected[field]):
                    changed.append(field)
        if changed:
            difference_rows.append(
                {"Ticker": key[0], "As_Of_Date": key[1], "Differences": ";".join(changed)}
            )
            failures.append(f"{key[0]} {key[1]}: {', '.join(changed)}")

    validation_dir = run_dir / "validation"
    validation_dir.mkdir(exist_ok=True)
    pd.DataFrame(
        difference_rows or [{"Ticker": "", "As_Of_Date": "", "Differences": ""}]
    ).to_csv(validation_dir / "reference_differences.csv", index=False)
    checksum_count = 0
    if not skip_checksums:
        checksum_count, checksum_failures = verify_checksums(run_dir)
        failures.extend(checksum_failures)
    summary = {
        "Validation_Status": "PASS" if not failures else "FAIL",
        "Rows_Checked": len(results),
        "Expected_Rows": expected_rows,
        "Validated_V1_Reference_Parity": not difference_rows,
        "Foundation_DMI_Component_Score_Total_And_Outcome_Parity": not difference_rows,
        "Research_Only_Guard_Checked": True,
        "Checksums_Checked": checksum_count,
        "Failures": failures,
    }
    (validation_dir / "validation_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main():
    parser = argparse.ArgumentParser(description="Validate integrated V8 Basic Health Score replay")
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--skip-checksums", action="store_true")
    args = parser.parse_args()
    summary = validate(args.run_dir.resolve(), args.skip_checksums)
    print(json.dumps(summary, indent=2))
    return 0 if summary["Validation_Status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
