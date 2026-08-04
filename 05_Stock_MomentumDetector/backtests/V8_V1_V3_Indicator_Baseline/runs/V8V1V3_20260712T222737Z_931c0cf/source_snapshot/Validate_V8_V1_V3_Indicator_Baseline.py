import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import pandas as pd
import ta


EXPECTED_PROFILES = {"V1", "V2", "V3"}
NUMERIC_FIELDS = [
    "Close",
    "EMA_200",
    "MACD_Line",
    "MACD_Signal",
    "RSI",
    "ADX",
    "DMI_Positive",
    "DMI_Negative",
    "OBV",
    "OBV_EMA_20",
    "ATR_14",
    "Aroon_Up",
    "Aroon_Down",
]
EXACT_FIELDS = [
    "Bars_Used",
    "Foundation_Eligible",
    "Foundation_State",
    "Indicator_Module_Status",
    "DMI_Dominance_Pass",
    "RSI_Status",
    "RSI_Score",
    "ADX_Status",
    "ADX_Score",
    "OBV_Status",
    "OBV_Fresh_Cross",
    "OBV_Score",
    "Aroon_Status",
    "Aroon_Score",
    "Opening_Structure_Pass",
    "Opening_Structure_Status",
    "Opening_Structure_Score",
    "Minimum_Momentum_Score",
    "Total_Momentum_Score",
    "V1_V3_Qualified",
    "Qualification_State",
]


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_checksums(run_dir):
    checksum_path = run_dir / "checksums.sha256"
    failures = []
    checked = 0
    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", 1)
        path = run_dir / relative
        checked += 1
        if not path.is_file():
            failures.append(f"missing checksum target: {relative}")
        elif sha256_file(path) != expected:
            failures.append(f"checksum mismatch: {relative}")
    return checked, failures


def as_bool(value):
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "1"}:
        return True
    if text in {"false", "0"}:
        return False
    return ""


def normalize_exact(value):
    if pd.isna(value) or value == "":
        return ""
    if isinstance(value, bool):
        return value
    text = str(value).strip()
    if text.lower() in {"true", "false"}:
        return text.lower() == "true"
    try:
        number = float(text)
        if number.is_integer():
            return int(number)
    except ValueError:
        pass
    return text


def numeric_equal(actual, expected, tolerance=1e-9):
    actual_blank = pd.isna(actual) or actual == ""
    expected_blank = expected is None or pd.isna(expected) or expected == ""
    if actual_blank or expected_blank:
        return actual_blank and expected_blank
    return math.isclose(
        float(actual), float(expected), rel_tol=tolerance, abs_tol=tolerance
    )


def score_rsi(value, rule):
    value = float(value)
    if float(rule["Preferred_Lower"]) <= value <= float(rule["Preferred_Upper"]):
        return int(rule["Score_Preferred_Range"]), "RSI_PREFERRED_RANGE"
    if float(rule["Minimum"]) <= value < float(rule["Preferred_Lower"]):
        return int(rule["Score_Minimum_To_Preferred"]), "RSI_MINIMUM_TO_PREFERRED"
    if float(rule["Preferred_Upper"]) < value <= float(rule["Maximum"]):
        return int(rule["Score_Preferred_To_Maximum"]), "RSI_PREFERRED_TO_MAXIMUM"
    if value > float(rule["Maximum"]):
        return int(rule["Score_Above_Maximum"]), "RSI_ABOVE_MAXIMUM"
    return int(rule["Score_Below_Minimum"]), "RSI_BELOW_MINIMUM"


def score_adx(value, rule):
    value = float(value)
    if float(rule["Preferred_Lower"]) <= value <= float(rule["Preferred_Upper"]):
        return int(rule["Score_Preferred_Range"]), "ADX_PREFERRED_RANGE"
    if (
        float(rule["Minimum"]) <= value < float(rule["Preferred_Lower"])
        or float(rule["Preferred_Upper"]) < value <= float(rule["High_Upper"])
    ):
        return int(rule["Score_Minimum_Or_High"]), "ADX_PARTIAL_RANGE"
    if value > float(rule["High_Upper"]):
        return int(rule["Score_Above_High"]), "ADX_ABOVE_HIGH"
    return int(rule["Score_Below_Minimum"]), "ADX_BELOW_MINIMUM"


def score_obv(frame, rule):
    for offset in range(1, int(rule["Cross_Lookback_Sessions"]) + 1):
        row = frame.iloc[-offset]
        previous = frame.iloc[-(offset + 1)]
        if row["OBV"] >= row["OBV_EMA"] and previous["OBV"] < previous["OBV_EMA"]:
            return int(rule["Score_Fresh_Cross"]), True, "OBV_FRESH_CROSS"
    latest = frame.iloc[-1]
    previous = frame.iloc[-2]
    if latest["Close"] > previous["Close"] and latest["OBV"] < previous["OBV"]:
        return int(rule["Score_Price_Up_OBV_Down"]), False, "OBV_NEGATIVE_DIVERGENCE"
    return int(rule["Score_Otherwise"]), False, "OBV_NO_SCORING_EVENT"


def score_aroon(up, down, rule):
    if up > float(rule["Strong_Up_Minimum_Exclusive"]) and down < float(
        rule["Strong_Down_Maximum_Exclusive"]
    ):
        return int(rule["Score_Strong"]), "AROON_STRONG"
    if up > float(rule["Moderate_Up_Minimum_Exclusive"]) and down < float(
        rule["Moderate_Down_Maximum_Exclusive"]
    ):
        return int(rule["Score_Moderate"]), "AROON_MODERATE"
    if up < float(rule["Bearish_Up_Maximum_Exclusive"]) and down > float(
        rule["Bearish_Down_Minimum_Exclusive"]
    ):
        return int(rule["Score_Bearish"]), "AROON_BEARISH"
    return int(rule["Score_Otherwise"]), "AROON_NEUTRAL"


def independent_row(price_frame, signal_date, profile_name, config):
    profile = config["Profiles"][profile_name]
    frame = price_frame.loc[price_frame.index <= pd.Timestamp(signal_date)].copy()
    close = frame["Close"]
    ema = close.ewm(
        span=int(config["EMA_Period"]),
        adjust=False,
        min_periods=int(config["EMA_Period"]),
    ).mean()
    fast = close.ewm(
        span=int(config["MACD"]["Fast"]),
        adjust=False,
        min_periods=int(config["MACD"]["Fast"]),
    ).mean()
    slow = close.ewm(
        span=int(config["MACD"]["Slow"]),
        adjust=False,
        min_periods=int(config["MACD"]["Slow"]),
    ).mean()
    macd_line = fast - slow
    macd_signal = macd_line.ewm(
        span=int(config["MACD"]["Signal"]),
        adjust=False,
        min_periods=int(config["MACD"]["Signal"]),
    ).mean()
    bars = len(frame)
    latest_close = close.iloc[-1]
    latest_ema = ema.iloc[-1]
    latest_line = macd_line.iloc[-1]
    latest_signal = macd_signal.iloc[-1]
    if bars < int(config["Minimum_History_Bars"]):
        state = "FOUNDATION_INSUFFICIENT_DATA"
        eligible = False
    elif latest_close <= latest_ema:
        state = "FOUNDATION_NOT_ELIGIBLE_BELOW_OR_AT_EMA"
        eligible = False
    elif latest_line > latest_signal and latest_line > 0:
        state = "FOUNDATION_ELIGIBLE_BULLISH_POSITIVE_MACD"
        eligible = True
    elif latest_line > 0:
        state = "FOUNDATION_NOT_ELIGIBLE_MACD_POSITIVE_PULLBACK"
        eligible = False
    elif latest_line > latest_signal:
        state = "FOUNDATION_NOT_ELIGIBLE_MACD_EARLY_RECOVERY_BELOW_ZERO"
        eligible = False
    else:
        state = "FOUNDATION_NOT_ELIGIBLE_MACD_NEGATIVE_WEAKENING"
        eligible = False
    result = {
        "Bars_Used": bars,
        "Foundation_Eligible": eligible,
        "Foundation_State": state,
        "Indicator_Module_Status": (
            "EXECUTED_FOUNDATION_ELIGIBLE"
            if eligible
            else "NOT_RUN_FOUNDATION_INELIGIBLE"
        ),
        "DMI_Dominance_Pass": "",
        "Close": latest_close,
        "EMA_200": latest_ema,
        "MACD_Line": latest_line,
        "MACD_Signal": latest_signal,
        "RSI": "",
        "RSI_Status": "",
        "RSI_Score": 0,
        "ADX": "",
        "DMI_Positive": "",
        "DMI_Negative": "",
        "ADX_Status": "",
        "ADX_Score": 0,
        "OBV": "",
        "OBV_EMA_20": "",
        "OBV_Status": "",
        "OBV_Fresh_Cross": "",
        "OBV_Score": 0,
        "ATR_14": "",
        "Aroon_Up": "",
        "Aroon_Down": "",
        "Aroon_Status": "NOT_USED_IN_PROFILE",
        "Aroon_Score": 0,
        "Opening_Structure_Pass": "",
        "Opening_Structure_Status": "NOT_USED_IN_PROFILE",
        "Opening_Structure_Score": 0,
        "Minimum_Momentum_Score": int(profile["Minimum_Momentum_Score"]),
        "Total_Momentum_Score": 0,
        "V1_V3_Qualified": False,
        "Qualification_State": state,
    }
    if not eligible:
        return result

    periods = config["Indicators"]
    frame["RSI"] = ta.momentum.rsi(
        close, window=int(periods["RSI_Period"]), fillna=False
    )
    adx = ta.trend.ADXIndicator(
        frame["High"],
        frame["Low"],
        close,
        window=int(periods["ADX_Period"]),
        fillna=False,
    )
    frame["ADX"] = adx.adx()
    frame["DMI_Positive"] = adx.adx_pos()
    frame["DMI_Negative"] = adx.adx_neg()
    frame["ATR"] = ta.volatility.average_true_range(
        frame["High"],
        frame["Low"],
        close,
        window=int(periods["ATR_Period"]),
        fillna=False,
    )
    frame["OBV"] = ta.volume.on_balance_volume(close, frame["Volume"], fillna=False)
    frame["OBV_EMA"] = ta.trend.ema_indicator(
        frame["OBV"], window=int(periods["OBV_EMA_Period"]), fillna=False
    )
    aroon = ta.trend.AroonIndicator(
        frame["High"], frame["Low"], window=int(periods["Aroon_Period"]), fillna=False
    )
    frame["Aroon_Up"] = aroon.aroon_up()
    frame["Aroon_Down"] = aroon.aroon_down()
    latest = frame.iloc[-1]
    dmi_pass = bool(latest["DMI_Positive"] > latest["DMI_Negative"])
    result.update(
        {
            "DMI_Dominance_Pass": dmi_pass,
            "RSI": latest["RSI"],
            "ADX": latest["ADX"],
            "DMI_Positive": latest["DMI_Positive"],
            "DMI_Negative": latest["DMI_Negative"],
            "OBV": latest["OBV"],
            "OBV_EMA_20": latest["OBV_EMA"],
            "ATR_14": latest["ATR"],
        }
    )
    if profile["Use_Aroon"]:
        result["Aroon_Up"] = latest["Aroon_Up"]
        result["Aroon_Down"] = latest["Aroon_Down"]
    if not dmi_pass:
        result["Qualification_State"] = "NOT_QUALIFIED_DMI_DOMINANCE"
        return result

    rules = config["Indicator_Rules"]
    rsi_score, rsi_status = score_rsi(latest["RSI"], rules["RSI"])
    adx_score, adx_status = score_adx(latest["ADX"], rules["ADX"])
    obv_score, obv_cross, obv_status = score_obv(frame, rules["OBV"])
    aroon_score = 0
    aroon_status = "NOT_USED_IN_PROFILE"
    if profile["Use_Aroon"]:
        aroon_score, aroon_status = score_aroon(
            latest["Aroon_Up"], latest["Aroon_Down"], rules["Aroon"]
        )
    structure_score = 0
    structure_pass = ""
    structure_status = "NOT_USED_IN_PROFILE"
    if profile["Use_Opening_Structure"]:
        structure_pass = bool(frame["Open"].iloc[-1] > frame["Open"].iloc[-2])
        structure_score = int(
            rules["Opening_Structure"][
                "Score_Pass" if structure_pass else "Score_Fail"
            ]
        )
        structure_status = (
            "OPEN_ABOVE_PRIOR_OPEN" if structure_pass else "OPEN_NOT_ABOVE_PRIOR_OPEN"
        )
    total = rsi_score + adx_score + obv_score + aroon_score + structure_score
    qualified = total >= int(profile["Minimum_Momentum_Score"])
    result.update(
        {
            "RSI_Status": rsi_status,
            "RSI_Score": rsi_score,
            "ADX_Status": adx_status,
            "ADX_Score": adx_score,
            "OBV_Status": obv_status,
            "OBV_Fresh_Cross": obv_cross,
            "OBV_Score": obv_score,
            "Aroon_Status": aroon_status,
            "Aroon_Score": aroon_score,
            "Opening_Structure_Pass": structure_pass,
            "Opening_Structure_Status": structure_status,
            "Opening_Structure_Score": structure_score,
            "Total_Momentum_Score": total,
            "V1_V3_Qualified": qualified,
            "Qualification_State": (
                "V1_V3_QUALIFIED" if qualified else "NOT_QUALIFIED_SCORE"
            ),
        }
    )
    return result


def outcome(frame, signal_date, horizon):
    location = frame.index.get_loc(pd.Timestamp(signal_date))
    entry = frame.iloc[location + 1]
    exit_row = frame.iloc[location + int(horizon)]
    return (
        entry.name.date().isoformat(),
        exit_row.name.date().isoformat(),
        ((float(exit_row["Close"]) / float(entry["Open"])) - 1) * 100,
    )


def validate(run_dir, skip_checksums=False):
    failures = []
    config = json.loads(
        next((run_dir / "inputs").glob("V8_V1_V3_Indicator_Baseline_Config.json")).read_text(
            encoding="utf-8"
        )
    )
    experiment = json.loads(
        (run_dir / "inputs" / "Experiment_Config.json").read_text(encoding="utf-8")
    )
    results = pd.read_csv(run_dir / "outputs" / "profile_results.csv", keep_default_na=False)
    expected_rows = (
        len(experiment["Seed_Stocks"])
        * len(experiment["Signal_Dates"])
        * len(config["Profiles"])
    )
    if set(config["Profiles"]) != EXPECTED_PROFILES:
        failures.append("profiles are not exactly V1, V2, V3")
    if config["Limit_Status"] != "RESEARCH_CANDIDATE_NOT_OPERATIONAL":
        failures.append("limit status is not research-only")
    if config["Operational_Use_Approved"] is not False:
        failures.append("operational use must remain false")
    if len(results) != expected_rows:
        failures.append(f"row count {len(results)} != expected {expected_rows}")
    keys = results[["Ticker", "As_Of_Date", "Profile"]]
    if keys.duplicated().any() or len(keys.drop_duplicates()) != expected_rows:
        failures.append("result grid is incomplete or contains duplicate keys")

    independent_rows = []
    for ticker in experiment["Seed_Stocks"]:
        price_path = run_dir / "inputs" / "prices" / f"{ticker}.csv"
        prices = pd.read_csv(price_path, parse_dates=["Date"]).set_index("Date")
        prices.index = prices.index.normalize()
        for signal_date in experiment["Signal_Dates"]:
            for profile in sorted(EXPECTED_PROFILES):
                selected = results.loc[
                    (results["Ticker"] == ticker)
                    & (results["As_Of_Date"] == signal_date)
                    & (results["Profile"] == profile)
                ]
                if len(selected) != 1:
                    failures.append(f"missing/non-unique row {ticker} {signal_date} {profile}")
                    continue
                actual = selected.iloc[0]
                expected = independent_row(prices, signal_date, profile, config)
                row_failures = []
                for field in NUMERIC_FIELDS:
                    if not numeric_equal(actual[field], expected[field]):
                        row_failures.append(field)
                for field in EXACT_FIELDS:
                    if normalize_exact(actual[field]) != normalize_exact(expected[field]):
                        row_failures.append(field)
                for horizon in config["Forward_Horizons_Sessions"]:
                    entry_date, exit_date, return_pct = outcome(prices, signal_date, horizon)
                    if actual[f"D{horizon}_Entry_Date"] != entry_date:
                        row_failures.append(f"D{horizon}_Entry_Date")
                    if actual[f"D{horizon}_Exit_Date"] != exit_date:
                        row_failures.append(f"D{horizon}_Exit_Date")
                    if not numeric_equal(actual[f"D{horizon}_Return_Pct"], return_pct):
                        row_failures.append(f"D{horizon}_Return_Pct")
                    if as_bool(actual[f"D{horizon}_Positive"]) != (return_pct > 0):
                        row_failures.append(f"D{horizon}_Positive")
                if row_failures:
                    failures.append(
                        f"{ticker} {signal_date} {profile}: " + ", ".join(row_failures)
                    )
                independent_rows.append(
                    {
                        "Ticker": ticker,
                        "As_Of_Date": signal_date,
                        "Profile": profile,
                        "Foundation_Eligible": expected["Foundation_Eligible"],
                        "DMI_Dominance_Pass": expected["DMI_Dominance_Pass"],
                        "Total_Momentum_Score": expected["Total_Momentum_Score"],
                        "V1_V3_Qualified": expected["V1_V3_Qualified"],
                        "Comparison_Pass": not row_failures,
                    }
                )

    v1 = results.loc[results["Profile"] == "V1"].sort_values(["Ticker", "As_Of_Date"])
    v2 = results.loc[results["Profile"] == "V2"].sort_values(["Ticker", "As_Of_Date"])
    identity_fields = NUMERIC_FIELDS + EXACT_FIELDS
    identity_fields = [field for field in identity_fields if not field.startswith("Aroon")]
    for field in identity_fields:
        left = [normalize_exact(value) for value in v1[field].tolist()]
        right = [normalize_exact(value) for value in v2[field].tolist()]
        if left != right:
            failures.append(f"V1/V2 technical identity failed for {field}")

    validation_dir = run_dir / "validation"
    validation_dir.mkdir(exist_ok=True)
    pd.DataFrame(independent_rows).to_csv(
        validation_dir / "independently_recomputed_rows.csv", index=False
    )
    checksum_count = 0
    if not skip_checksums:
        checksum_count, checksum_failures = verify_checksums(run_dir)
        failures.extend(checksum_failures)
    summary = {
        "Validation_Status": "PASS" if not failures else "FAIL",
        "Independent_Formula_Recalculation": True,
        "Rows_Checked": len(independent_rows),
        "Expected_Rows": expected_rows,
        "Checksums_Checked": checksum_count,
        "V1_V2_Technical_Identity_Checked": True,
        "Research_Only_Guard_Checked": True,
        "Failures": failures,
    }
    (validation_dir / "validation_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    return summary


def main():
    parser = argparse.ArgumentParser(description="Independently validate a V1-V3 baseline run")
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--skip-checksums", action="store_true")
    args = parser.parse_args()
    summary = validate(args.run_dir.resolve(), args.skip_checksums)
    print(json.dumps(summary, indent=2))
    return 0 if summary["Validation_Status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
