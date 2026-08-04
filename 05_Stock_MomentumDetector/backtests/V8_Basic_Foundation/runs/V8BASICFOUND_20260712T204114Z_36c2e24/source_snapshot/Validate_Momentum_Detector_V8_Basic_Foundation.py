import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd


ELIGIBLE = "FOUNDATION_ELIGIBLE_BULLISH_POSITIVE_MACD"
BELOW_EMA = "FOUNDATION_NOT_ELIGIBLE_BELOW_OR_AT_EMA"
POSITIVE_PULLBACK = "FOUNDATION_NOT_ELIGIBLE_MACD_POSITIVE_PULLBACK"
EARLY_RECOVERY = "FOUNDATION_NOT_ELIGIBLE_MACD_EARLY_RECOVERY_BELOW_ZERO"
NEGATIVE_WEAKENING = "FOUNDATION_NOT_ELIGIBLE_MACD_NEGATIVE_WEAKENING"
INSUFFICIENT = "FOUNDATION_INSUFFICIENT_DATA"


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bool_value(value):
    return str(value).strip().lower() in ("true", "1", "yes")


def close_enough(left, right, tolerance=1e-9):
    return abs(float(left) - float(right)) <= tolerance


def classify(close, ema, line, signal, bars, minimum):
    if bars < minimum or any(pd.isna(value) for value in (close, ema, line, signal)):
        return INSUFFICIENT, False
    if close <= ema:
        return BELOW_EMA, False
    if line > signal and line > 0:
        return ELIGIBLE, True
    if line > 0:
        return POSITIVE_PULLBACK, False
    if line > signal:
        return EARLY_RECOVERY, False
    return NEGATIVE_WEAKENING, False


def calculate_outcome(frame, signal_date, horizon):
    position = frame.index.get_loc(signal_date)
    if not isinstance(position, int):
        position = int(position[0])
    entry = float(frame.iloc[position + 1]["Open"])
    exit_close = float(frame.iloc[position + horizon]["Close"])
    return ((exit_close / entry) - 1.0) * 100.0


def validate_checksums(run_dir):
    failures = []
    for line in (run_dir / "checksums.sha256").read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", 1)
        path = run_dir / relative
        if not path.is_file() or sha256_file(path) != expected:
            failures.append(relative)
    return failures


def parse_args():
    parser = argparse.ArgumentParser(description="Independent validator for basic V8 Foundation replay")
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--skip-checksums", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    run_dir = args.run_dir.resolve()
    config = json.loads(
        (run_dir / "inputs" / "V8_Basic_Foundation_Config.json").read_text(
            encoding="utf-8"
        )
    )
    experiment = json.loads(
        (run_dir / "inputs" / "Experiment_Config.json").read_text(encoding="utf-8")
    )
    results = pd.read_csv(run_dir / "outputs" / "foundation_results.csv", dtype=str).fillna("")
    ema_period = int(config["EMA_Period"])
    fast = int(config["MACD"]["Fast"])
    slow = int(config["MACD"]["Slow"])
    signal_period = int(config["MACD"]["Signal"])
    minimum = int(config["Minimum_History_Bars"])
    horizons = [int(value) for value in experiment["Forward_Horizons_Sessions"]]
    failures = []
    recomputed = []
    forbidden = {"Score", "Benchmark_Ticker", "ETF_Ticker", "Weekly_Trend", "ATR_Pct"}
    checks = {
        "Exactly_20_Stocks": results["Ticker"].nunique() == 20,
        "Exactly_4_Dates": results["As_Of_Date"].nunique() == 4,
        "Exactly_80_Rows": len(results) == 80,
        "Complete_Grid": len(results[["Ticker", "As_Of_Date"]].drop_duplicates()) == 80,
        "Foundation_Only_Schema": not bool(forbidden.intersection(results.columns)),
        "No_Score_Output": "Score" not in results.columns,
    }
    cache = {}
    for record in results.to_dict("records"):
        ticker = record["Ticker"]
        signal_date = pd.Timestamp(record["As_Of_Date"])
        if ticker not in cache:
            cache[ticker] = pd.read_csv(
                run_dir / "inputs" / "prices" / f"{ticker}.csv", parse_dates=["Date"]
            ).set_index("Date")
        frame = cache[ticker]
        history = frame.loc[:signal_date]
        close = history["Close"]
        ema = close.ewm(span=ema_period, adjust=False, min_periods=ema_period).mean()
        fast_ema = close.ewm(span=fast, adjust=False, min_periods=fast).mean()
        slow_ema = close.ewm(span=slow, adjust=False, min_periods=slow).mean()
        line = fast_ema - slow_ema
        signal_line = line.ewm(
            span=signal_period, adjust=False, min_periods=signal_period
        ).mean()
        values = {
            "Close": close.iloc[-1],
            "EMA_Value": ema.iloc[-1],
            "MACD_Line": line.iloc[-1],
            "MACD_Signal_Line": signal_line.iloc[-1],
            "MACD_Histogram": line.iloc[-1] - signal_line.iloc[-1],
        }
        state, eligible = classify(
            values["Close"],
            values["EMA_Value"],
            values["MACD_Line"],
            values["MACD_Signal_Line"],
            len(history),
            minimum,
        )
        row_failures = []
        if state != record["Foundation_State"]:
            row_failures.append("Foundation_State")
        if eligible != bool_value(record["Foundation_Eligible"]):
            row_failures.append("Foundation_Eligible")
        for field, expected in values.items():
            if not close_enough(record[field], expected):
                row_failures.append(field)
        for horizon in horizons:
            expected = calculate_outcome(frame, signal_date, horizon)
            if not close_enough(record[f"D{horizon}_Return_Pct"], expected):
                row_failures.append(f"D{horizon}_Return_Pct")
        failures.extend(
            f"{ticker}/{signal_date.date()}/{failure}" for failure in row_failures
        )
        recomputed.append(
            {
                "Ticker": ticker,
                "As_Of_Date": signal_date.date().isoformat(),
                **values,
                "Foundation_State": state,
                "Foundation_Eligible": eligible,
                "Validation_Status": "PASS" if not row_failures else "FAIL",
                "Validation_Failures": ";".join(row_failures),
            }
        )
    checks["Independent_Formula_And_Outcome_Recompute"] = not failures
    if not args.skip_checksums:
        checks["Checksums"] = not validate_checksums(run_dir)
    validation_dir = run_dir / "validation"
    validation_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(recomputed).to_csv(
        validation_dir / "independently_recomputed_rows.csv", index=False
    )
    summary = {
        "Validation_Status": "PASS" if all(checks.values()) else "FAIL",
        "Checks": checks,
        "Rows_Recomputed": len(recomputed),
        "Failures": failures,
    }
    (validation_dir / "validation_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    return 0 if summary["Validation_Status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
