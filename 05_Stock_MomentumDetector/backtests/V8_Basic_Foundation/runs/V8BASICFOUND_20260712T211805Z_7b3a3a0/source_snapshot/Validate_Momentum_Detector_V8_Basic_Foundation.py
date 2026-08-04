import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd
import ta


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
    forbidden = {"Score", "Benchmark_Ticker", "ETF_Ticker", "Weekly_Trend"}
    schema_version = config["Schema_Version"]
    validate_indicators = schema_version in {
        "V8_BASIC_FOUNDATION_2",
        "V8_BASIC_FOUNDATION_3",
    }
    foundation_gated_indicators = schema_version == "V8_BASIC_FOUNDATION_3"
    indicator_fields = [
        "RSI",
        "ADX",
        "DMI_Positive",
        "DMI_Negative",
        "True_Range",
        "ATR",
        "ATR_Pct",
        "OBV",
        "OBV_EMA",
        "Aroon_Up",
        "Aroon_Down",
    ]
    checks = {
        "Exactly_20_Stocks": results["Ticker"].nunique() == 20,
        "Exactly_4_Dates": results["As_Of_Date"].nunique() == 4,
        "Exactly_80_Rows": len(results) == 80,
        "Complete_Grid": len(results[["Ticker", "As_Of_Date"]].drop_duplicates()) == 80,
        "Foundation_Only_Schema": not bool(forbidden.intersection(results.columns)),
        "No_Score_Output": "Score" not in results.columns,
    }
    if validate_indicators:
        checks["Calculation_Only_Authority"] = (
            set(results["Indicator_Authority"]) == {"CALCULATION_ONLY"}
        )
    if foundation_gated_indicators:
        eligible_mask = results["Foundation_Eligible"].map(bool_value)
        checks["Foundation_Gate_Enforced"] = bool(
            (
                results.loc[eligible_mask, "Indicator_Module_Status"]
                == "EXECUTED_FOUNDATION_ELIGIBLE"
            ).all()
            and (
                results.loc[~eligible_mask, "Indicator_Module_Status"]
                == "NOT_RUN_FOUNDATION_INELIGIBLE"
            ).all()
            and (results.loc[~eligible_mask, indicator_fields] == "").all().all()
        )
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
        if validate_indicators and (not foundation_gated_indicators or eligible):
            periods = config["Indicators"]
            high, low, volume = history["High"], history["Low"], history["Volume"]
            adx = ta.trend.ADXIndicator(
                high,
                low,
                close,
                window=int(periods["ADX_Period"]),
                fillna=False,
            )
            atr = ta.volatility.average_true_range(
                high,
                low,
                close,
                window=int(periods["ATR_Period"]),
                fillna=False,
            )
            obv = ta.volume.on_balance_volume(close, volume, fillna=False)
            aroon = ta.trend.AroonIndicator(
                high,
                low,
                window=int(periods["Aroon_Period"]),
                fillna=False,
            )
            previous_close = close.shift(1)
            true_range = pd.concat(
                [
                    high - low,
                    (high - previous_close).abs(),
                    (low - previous_close).abs(),
                ],
                axis=1,
            ).max(axis=1)
            values.update(
                {
                    "RSI": ta.momentum.rsi(
                        close,
                        window=int(periods["RSI_Period"]),
                        fillna=False,
                    ).iloc[-1],
                    "ADX": adx.adx().iloc[-1],
                    "DMI_Positive": adx.adx_pos().iloc[-1],
                    "DMI_Negative": adx.adx_neg().iloc[-1],
                    "True_Range": true_range.iloc[-1],
                    "ATR": atr.iloc[-1],
                    "ATR_Pct": (atr / close * 100.0).iloc[-1],
                    "OBV": obv.iloc[-1],
                    "OBV_EMA": ta.trend.ema_indicator(
                        obv,
                        window=int(periods["OBV_EMA_Period"]),
                        fillna=False,
                    ).iloc[-1],
                    "Aroon_Up": aroon.aroon_up().iloc[-1],
                    "Aroon_Down": aroon.aroon_down().iloc[-1],
                }
            )
        row_failures = []
        if state != record["Foundation_State"]:
            row_failures.append("Foundation_State")
        if eligible != bool_value(record["Foundation_Eligible"]):
            row_failures.append("Foundation_Eligible")
        for field, expected in values.items():
            if not close_enough(record[field], expected):
                row_failures.append(field)
        if foundation_gated_indicators:
            expected_module_status = (
                "EXECUTED_FOUNDATION_ELIGIBLE"
                if eligible
                else "NOT_RUN_FOUNDATION_INELIGIBLE"
            )
            if record["Indicator_Module_Status"] != expected_module_status:
                row_failures.append("Indicator_Module_Status")
            if not eligible:
                for field in indicator_fields:
                    if record[field] != "":
                        row_failures.append(f"{field}_MUST_BE_BLANK_WHEN_INELIGIBLE")
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
                "Indicator_Module_Status": (
                    "EXECUTED_FOUNDATION_ELIGIBLE"
                    if eligible and foundation_gated_indicators
                    else (
                        "NOT_RUN_FOUNDATION_INELIGIBLE"
                        if foundation_gated_indicators
                        else "LEGACY_NOT_APPLICABLE"
                    )
                ),
                "Validation_Status": "PASS" if not row_failures else "FAIL",
                "Validation_Failures": ";".join(row_failures),
            }
        )
    checks["Independent_Formula_And_Outcome_Recompute"] = not failures
    regression_path = run_dir / "outputs" / "foundation_regression.csv"
    if regression_path.is_file():
        regression = pd.read_csv(regression_path, dtype=str).fillna("")
        checks["Foundation_Regression_Unchanged"] = (
            len(regression) == 80
            and set(regression["Regression_Status"]) == {"PASS"}
        )
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
