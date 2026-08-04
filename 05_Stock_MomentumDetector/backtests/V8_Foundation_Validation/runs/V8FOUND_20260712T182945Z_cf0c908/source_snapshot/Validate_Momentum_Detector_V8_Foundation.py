import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd


FOUNDATION_VALID = "FOUNDATION_VALID"
FOUNDATION_MACD_RESET = "FOUNDATION_TREND_VALID_MACD_RESET"
FOUNDATION_BELOW_EMA200 = "FOUNDATION_INVALID_BELOW_EMA200"
FOUNDATION_INSUFFICIENT_DATA = "FOUNDATION_INSUFFICIENT_DATA"


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bool_value(value):
    return str(value).strip().lower() in ("true", "1", "yes")


def close_enough(left, right, tolerance=1e-9):
    if pd.isna(left) and pd.isna(right):
        return True
    return abs(float(left) - float(right)) <= tolerance


def calculate_outcome(frame, signal_date, horizon):
    position = frame.index.get_loc(signal_date)
    if not isinstance(position, int):
        position = int(position[0])
    entry = float(frame.iloc[position + 1]["Open"])
    exit_price = float(frame.iloc[position + horizon]["Close"])
    return ((exit_price / entry) - 1.0) * 100.0


def recompute_foundation(frame, signal_date, fast, slow, signal):
    history = frame.loc[:signal_date]
    close = history["Close"]
    ema200 = close.ewm(span=200, adjust=False, min_periods=200).mean()
    fast_ema = close.ewm(span=fast, adjust=False, min_periods=fast).mean()
    slow_ema = close.ewm(span=slow, adjust=False, min_periods=slow).mean()
    line = fast_ema - slow_ema
    signal_line = line.ewm(span=signal, adjust=False, min_periods=signal).mean()
    values = {
        "Close": close.iloc[-1],
        "EMA_200": ema200.iloc[-1],
        "MACD_Line": line.iloc[-1],
        "MACD_Signal_Line": signal_line.iloc[-1],
        "MACD_Histogram": line.iloc[-1] - signal_line.iloc[-1],
    }
    sufficient = all(pd.notna(value) for value in values.values())
    above = sufficient and values["Close"] > values["EMA_200"]
    bullish = above and values["MACD_Line"] > values["MACD_Signal_Line"] and values["MACD_Line"] > 0
    if not sufficient:
        status = FOUNDATION_INSUFFICIENT_DATA
    elif not above:
        status = FOUNDATION_BELOW_EMA200
    elif not bullish:
        status = FOUNDATION_MACD_RESET
    else:
        status = FOUNDATION_VALID
    return {**values, "Foundation_Status": status, "Foundation_Qualified": bullish}


def validate_checksums(run_dir):
    failures = []
    checksum_path = run_dir / "checksums.sha256"
    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", 1)
        path = run_dir / relative
        if not path.is_file() or sha256_file(path) != expected:
            failures.append(relative)
    return failures


def parse_args():
    parser = argparse.ArgumentParser(description="Independently validate a frozen V8 foundation run")
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--skip-checksums", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    run_dir = args.run_dir.resolve()
    manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    config_path = next((run_dir / "inputs").glob("V8_Foundation_Validation_Config.json"))
    config = json.loads(config_path.read_text(encoding="utf-8"))
    execution = pd.read_csv(run_dir / "outputs" / "execution_log.csv", dtype=str).fillna("")
    regression = pd.read_csv(run_dir / "outputs" / "regression_comparison.csv", dtype=str).fillna("")
    mappings = pd.read_csv(run_dir / "outputs" / "etf_mapping_validation.csv", dtype=str).fillna("")
    stocks = config["Seed_Stocks"]
    dates = config["Signal_Dates"]
    fast = int(config["MACD"]["Fast"])
    slow = int(config["MACD"]["Slow"])
    signal = int(config["MACD"]["Signal"])
    horizons = [int(value) for value in config["Forward_Horizons_Sessions"]]
    failures = []
    checks = {
        "Exactly_20_Stocks": execution["Ticker"].nunique() == 20 == len(stocks),
        "Exactly_4_Dates": execution["Signal_Date"].nunique() == 4 == len(dates),
        "Exactly_80_Rows": len(execution) == 80,
        "Complete_Stock_Date_Grid": len(execution[["Ticker", "Signal_Date"]].drop_duplicates()) == 80,
        "MACD_8_21_5": set(execution["MACD_Fast_Period"]) == {"8"}
        and set(execution["MACD_Slow_Period"]) == {"21"}
        and set(execution["MACD_Signal_Period"]) == {"5"},
        "Foundation_Policy_Enforced": set(execution["Foundation_Policy"]) == {"ENFORCE"},
    }
    recomputed_rows = []
    price_cache = {}
    benchmark_path = run_dir / "inputs" / "prices" / f"{config['Benchmark']}.csv"
    benchmark = pd.read_csv(benchmark_path, parse_dates=["Date"]).set_index("Date")
    for record in execution.to_dict("records"):
        stock = record["Ticker"]
        signal_date = pd.Timestamp(record["Signal_Date"])
        if stock not in price_cache:
            price_cache[stock] = pd.read_csv(
                run_dir / "inputs" / "prices" / f"{stock}.csv", parse_dates=["Date"]
            ).set_index("Date")
        frame = price_cache[stock]
        independent = recompute_foundation(frame, signal_date, fast, slow, signal)
        row_failures = []
        if record["Foundation_Status"] != independent["Foundation_Status"]:
            row_failures.append("Foundation_Status")
        if bool_value(record["Foundation_Qualified"]) != independent["Foundation_Qualified"]:
            row_failures.append("Foundation_Qualified")
        for field in ("Close", "EMA_200", "MACD_Line", "MACD_Signal_Line", "MACD_Histogram"):
            if not close_enough(record[field], independent[field]):
                row_failures.append(field)
        for horizon in horizons:
            actual = float(record[f"D{horizon}_Return_Pct"])
            expected = calculate_outcome(frame, signal_date, horizon)
            if not close_enough(actual, expected):
                row_failures.append(f"D{horizon}_Return_Pct")
            actual_spy = float(record[f"SPY_D{horizon}_Return_Pct"])
            expected_spy = calculate_outcome(benchmark, signal_date, horizon)
            if not close_enough(actual_spy, expected_spy):
                row_failures.append(f"SPY_D{horizon}_Return_Pct")
        valid = independent["Foundation_Status"] == FOUNDATION_VALID
        if not valid and (
            record["Final_Decision"] == "MOMENTUM_ACTIVE" or float(record["Score"]) != 0.0
        ):
            row_failures.append("Foundation_Short_Circuit")
        if valid and not bool_value(record["Setup_Momentum_Analyzed"]):
            row_failures.append("Valid_Setup_Not_Analyzed")
        recomputed_rows.append(
            {
                "Ticker": stock,
                "Signal_Date": record["Signal_Date"],
                **independent,
                "Validation_Status": "PASS" if not row_failures else "FAIL",
                "Validation_Failures": ";".join(row_failures),
            }
        )
        failures.extend(f"{stock}/{record['Signal_Date']}/{field}" for field in row_failures)

    checks.update(
        {
            "Independent_Foundation_And_Outcome_Recompute": not failures,
            "Valid_Row_Regression": all(
                bool_value(value) for value in regression["Valid_Row_Regression_Pass"]
            ),
            "Invalid_Row_Short_Circuit": all(
                bool_value(value) for value in regression["Invalid_Row_Short_Circuit_Pass"]
            ),
            "ETF_Same_Quarter_Acceptance_Strict": all(
                (not bool_value(row["Historical_Mapping_Accepted"]))
                or (
                    row["Validation_Status"] == "PASS"
                    and row["Validation_Quarter"] == config["Quarter"]
                    and bool_value(row["Same_Quarter_2026Q2"])
                )
                for row in mappings.to_dict("records")
            ),
            "Score_Invariance": all(bool_value(value) for value in execution["Score_Invariance_Pass"]),
            "Manifest_Counts_Match": int(manifest["Total_Rows"]) == len(execution)
            and int(manifest["Stocks_Tested"]) == execution["Ticker"].nunique(),
        }
    )
    if not args.skip_checksums:
        checks["Checksums"] = not validate_checksums(run_dir)

    validation_dir = run_dir / "validation"
    validation_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(recomputed_rows).to_csv(
        validation_dir / "independently_recomputed_rows.csv", index=False
    )
    summary = {
        "Validation_Status": "PASS" if all(checks.values()) else "FAIL",
        "Checks": checks,
        "Recomputed_Rows": len(recomputed_rows),
        "Recompute_Failures": failures,
        "Checksum_Validation_Skipped": bool(args.skip_checksums),
    }
    (validation_dir / "validation_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    return 0 if summary["Validation_Status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
