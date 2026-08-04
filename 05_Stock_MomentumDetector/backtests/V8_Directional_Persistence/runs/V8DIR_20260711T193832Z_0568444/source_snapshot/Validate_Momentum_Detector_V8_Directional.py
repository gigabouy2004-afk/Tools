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


def verify_checksums(run_dir):
    failures = []
    for line in (run_dir / "checksums.sha256").read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", 1)
        path = run_dir / relative
        if not path.exists() or sha256_file(path) != expected:
            failures.append(f"checksum failure: {relative}")
    return failures


def load_price(path):
    frame = pd.read_csv(path, parse_dates=["Date"], index_col="Date")
    frame.index = pd.to_datetime(frame.index).tz_localize(None).normalize()
    return frame


def expected_metrics(frame, signal_date):
    signal_date = pd.Timestamp(signal_date)
    position = frame.index.get_loc(signal_date)
    d = float(frame.iloc[position]["Close"])
    d1_open = float(frame.iloc[position + 1]["Open"])
    d1_close = float(frame.iloc[position + 1]["Close"])
    d5 = float(frame.iloc[position + 5]["Close"])
    d8 = float(frame.iloc[position + 8]["Close"])
    return {
        "D1_Open_vs_D_Close_Pct": ((d1_open / d) - 1) * 100,
        "D1_Close_vs_D_Close_Pct": ((d1_close / d) - 1) * 100,
        "D1_Close_vs_D1_Open_Pct": ((d1_close / d1_open) - 1) * 100,
        "D1_Direction_Pass": d1_close > d,
        "D5_Close_vs_D_Close_Pct": ((d5 / d) - 1) * 100,
        "D5_Persistence_Pass": d5 > d,
        "D8_Close_vs_D_Close_Pct": ((d8 / d) - 1) * 100,
        "D8_Persistence_Pass": d8 > d,
    }


def validate(run_dir, skip_checksums=False):
    manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    source_run = run_dir.parents[2] / "V8_Comprehensive/runs" / manifest["Source_Run"]
    rows = list(csv.DictReader(open(run_dir / "outputs/all_stock_results.csv", encoding="utf-8")))
    failures = [] if skip_checksums else verify_checksums(run_dir)
    details = []
    if len(rows) != 10:
        failures.append(f"expected 10 stock rows, found {len(rows)}")
    for row in rows:
        ticker = row["Ticker"]
        frame = load_price(source_run / f"inputs/prices/{ticker}.csv")
        expected = expected_metrics(frame, manifest["Signal_Date"])
        for field, expected_value in expected.items():
            actual_text = row[field]
            if isinstance(expected_value, bool):
                passed = actual_text.lower() == str(expected_value).lower()
            else:
                passed = math.isclose(float(actual_text), expected_value, rel_tol=1e-9, abs_tol=1e-9)
            details.append(
                {
                    "Ticker": ticker,
                    "Field": field,
                    "Expected": expected_value,
                    "Actual": actual_text,
                    "Pass": passed,
                }
            )
            if not passed:
                failures.append(f"{ticker} mismatch: {field}")
    validation_dir = run_dir / "validation"
    with open(validation_dir / "independently_recomputed_metrics.csv", "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["Ticker", "Field", "Expected", "Actual", "Pass"])
        writer.writeheader()
        writer.writerows(details)
    summary = {
        "Run_ID": manifest["Run_ID"],
        "Validation_Status": "PASS" if not failures else "FAIL",
        "Stocks_Checked": len(rows),
        "Metrics_Recomputed": len(details),
        "Failure_Count": len(failures),
        "Failures": failures,
    }
    (validation_dir / "validation_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--skip-checksums", action="store_true")
    args = parser.parse_args()
    summary = validate(args.run_dir.resolve(), args.skip_checksums)
    print(json.dumps(summary, indent=2))
    return 0 if summary["Validation_Status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
