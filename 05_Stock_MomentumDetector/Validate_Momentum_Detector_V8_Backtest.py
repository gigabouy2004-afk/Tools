import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

import pandas as pd


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_price(path):
    frame = pd.read_csv(path, parse_dates=["Date"], index_col="Date")
    frame.index = pd.to_datetime(frame.index).tz_localize(None).normalize()
    return frame


def outcome(frame, signal_date, horizon):
    signal_date = pd.Timestamp(signal_date).normalize()
    position = frame.index.get_loc(signal_date)
    if not isinstance(position, int):
        position = int(position[0])
    entry = float(frame.iloc[position + 1]["Open"])
    exit_price = float(frame.iloc[position + int(horizon)]["Close"])
    return ((exit_price / entry) - 1.0) * 100.0


def verify_checksums(run_dir):
    checksum_path = run_dir / "checksums.sha256"
    if not checksum_path.exists():
        return ["checksums.sha256 is missing"]
    failures = []
    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", 1)
        path = run_dir / relative
        if not path.exists():
            failures.append(f"missing checksum target: {relative}")
        elif sha256_file(path) != expected:
            failures.append(f"checksum mismatch: {relative}")
    return failures


def close_enough(actual, expected, tolerance=1e-9):
    return math.isclose(float(actual), float(expected), rel_tol=tolerance, abs_tol=tolerance)


def validate_run(run_dir, skip_checksums=False):
    manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    quarter = manifest["Quarter"]
    horizons = [int(value) for value in manifest["Horizon_Sessions"]]
    random_rows = list(csv.DictReader(open(run_dir / "outputs/random_date_results.csv", encoding="utf-8")))
    mapping_rows = list(csv.DictReader(open(run_dir / "outputs/etf_mapping_validation.csv", encoding="utf-8")))
    execution_rows = list(csv.DictReader(open(run_dir / "outputs/execution_log.csv", encoding="utf-8")))
    details = []
    failures = [] if skip_checksums else verify_checksums(run_dir)

    selected_stocks = manifest["Selected_Stocks"]
    if len(selected_stocks) < 10 or len(set(selected_stocks)) != len(selected_stocks):
        failures.append("selected stock count/uniqueness requirement failed")
    if len(random_rows) != len(selected_stocks):
        failures.append("one random row per stock requirement failed")

    price_cache = {}
    for row in random_rows:
        ticker = row["Ticker"]
        signal_date = row["Signal_Date"]
        price_cache.setdefault(ticker, load_price(run_dir / f"inputs/prices/{ticker}.csv"))
        for horizon in horizons:
            expected = outcome(price_cache[ticker], signal_date, horizon)
            actual = float(row[f"Forward_{horizon}D_Return_Pct"])
            passed = close_enough(actual, expected)
            details.append(
                {
                    "Ticker": ticker,
                    "Signal_Date": signal_date,
                    "Check": f"RECOMPUTE_{horizon}D_RETURN",
                    "Expected": expected,
                    "Actual": actual,
                    "Pass": passed,
                }
            )
            if not passed:
                failures.append(f"{ticker} {signal_date} {horizon}D return mismatch")
            exit_date = pd.Timestamp(row[f"Forward_{horizon}D_Exit_Date"])
            if f"{exit_date.year}Q{exit_date.quarter}" != quarter:
                failures.append(f"{ticker} {horizon}D exit falls outside {quarter}")

    for row in execution_rows:
        score = float(row["Score"])
        decision = row["Final_Decision"]
        cap = 100.0 if decision == "MOMENTUM_ACTIVE" else 84.0 if decision == "MOMENTUM_PRESENT_WAIT_CONFIRMATION" else 49.0
        if score < 0 or score > cap:
            failures.append(f"score contract failed: {row['Ticker']} {row['Signal_Date']}")
        if row["Score_Invariance_Pass"].lower() != "true" or row["Score_Before_ETF"] != row["Score_After_ETF"]:
            failures.append(f"ETF score invariance failed: {row['Ticker']} {row['Signal_Date']}")

    eligible_mapping_stocks = set()
    for row in mapping_rows:
        if row["Same_Quarter_Eligible"].lower() == "true":
            eligible_mapping_stocks.add(row["Stock_Code"])
            if row["Validation_Status"] != "PASS" or row["Validation_Quarter"] != quarter:
                failures.append(f"same-quarter mapping contract failed: {row['Stock_Code']} {row['ETF_Ticker']}")
    if not set(selected_stocks).issubset(eligible_mapping_stocks):
        failures.append("one or more selected stocks lack same-quarter verified ETF mapping")

    validation_dir = run_dir / "validation"
    validation_dir.mkdir(parents=True, exist_ok=True)
    with open(validation_dir / "independently_recomputed_rows.csv", "w", encoding="utf-8", newline="") as file:
        fieldnames = ["Ticker", "Signal_Date", "Check", "Expected", "Actual", "Pass"]
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(details)
    summary = {
        "Run_ID": manifest["Run_ID"],
        "Validation_Status": "PASS" if not failures else "FAIL",
        "Stocks_Checked": len(selected_stocks),
        "Random_Rows_Checked": len(random_rows),
        "Forward_Returns_Recomputed": len(details),
        "Execution_Rows_Contract_Checked": len(execution_rows),
        "Same_Quarter_Eligible_Mapping_Stocks": len(eligible_mapping_stocks),
        "Failure_Count": len(failures),
        "Failures": failures,
    }
    (validation_dir / "validation_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    return summary


def parse_args():
    parser = argparse.ArgumentParser(description="Validate frozen V8 comprehensive backtest artifacts")
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--skip-checksums", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    summary = validate_run(args.run_dir.resolve(), skip_checksums=args.skip_checksums)
    print(json.dumps(summary, indent=2))
    return 0 if summary["Validation_Status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
