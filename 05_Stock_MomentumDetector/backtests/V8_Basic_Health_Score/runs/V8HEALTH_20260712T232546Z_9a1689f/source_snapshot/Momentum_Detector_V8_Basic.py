import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import ta
import yfinance as yf


ROOT = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = ROOT / "config" / "V8_Basic_Foundation_Config.json"
DEFAULT_SNAPSHOT_PATH = ROOT / "Processed_Data" / "V8_Basic_Health_Score_Snapshot.csv"
DEFAULT_LOG_PATH = ROOT / "Processed_Data" / "V8_Basic_Health_Score_Execution_Log.csv"

ENGINE_VERSION = "V8_BASIC_HEALTH_SCORE_1"

DATA_VALID = "DATA_VALID"
DATA_INSUFFICIENT = "DATA_INSUFFICIENT_HISTORY"

FOUNDATION_ELIGIBLE = "FOUNDATION_ELIGIBLE_BULLISH_POSITIVE_MACD"
FOUNDATION_BELOW_EMA = "FOUNDATION_NOT_ELIGIBLE_BELOW_OR_AT_EMA"
FOUNDATION_MACD_POSITIVE_PULLBACK = "FOUNDATION_NOT_ELIGIBLE_MACD_POSITIVE_PULLBACK"
FOUNDATION_MACD_EARLY_RECOVERY = "FOUNDATION_NOT_ELIGIBLE_MACD_EARLY_RECOVERY_BELOW_ZERO"
FOUNDATION_MACD_NEGATIVE_WEAKENING = "FOUNDATION_NOT_ELIGIBLE_MACD_NEGATIVE_WEAKENING"
FOUNDATION_INSUFFICIENT = "FOUNDATION_INSUFFICIENT_DATA"

INDICATOR_MODULE_EXECUTED = "EXECUTED_FOUNDATION_ELIGIBLE"
INDICATOR_MODULE_NOT_RUN = "NOT_RUN_FOUNDATION_INELIGIBLE"
HEALTH_SCORE_EXECUTED = "EXECUTED_DMI_ELIGIBLE"
HEALTH_SCORE_NOT_RUN_FOUNDATION = "NOT_RUN_FOUNDATION_INELIGIBLE"
HEALTH_SCORE_NOT_RUN_DMI = "NOT_RUN_DMI_INELIGIBLE"

OUTPUT_FIELDS = [
    "Engine_Version",
    "Configuration_ID",
    "Decision_Scope",
    "Indicator_Set_ID",
    "Indicator_Authority",
    "Indicator_Module_Status",
    "Indicator_Module_Reason",
    "Ticker",
    "Evaluated_At_UTC",
    "As_Of_Date",
    "First_Price_Date",
    "Bars_Used",
    "Minimum_History_Bars",
    "Data_Status",
    "Foundation_Eligible",
    "Foundation_State",
    "Foundation_Reason",
    "Close",
    "EMA_Period",
    "EMA_Value",
    "MACD_Fast_Period",
    "MACD_Slow_Period",
    "MACD_Signal_Period",
    "MACD_Line",
    "MACD_Signal_Line",
    "MACD_Histogram",
    "RSI_Period",
    "RSI",
    "RSI_Authority",
    "RSI_Limit_Status",
    "RSI_Operational_Use_Approved",
    "RSI_Score",
    "RSI_Score_Status",
    "RSI_Score_Message",
    "ADX_Period",
    "ADX",
    "ADX_Authority",
    "ADX_Limit_Status",
    "ADX_Operational_Use_Approved",
    "ADX_Score",
    "ADX_Score_Status",
    "ADX_Score_Message",
    "DMI_Positive",
    "DMI_Negative",
    "DMI_Authority",
    "DMI_Limit_Status",
    "DMI_Operational_Use_Approved",
    "DMI_Eligible",
    "DMI_Status",
    "DMI_Message",
    "True_Range",
    "ATR_Period",
    "ATR",
    "ATR_Pct",
    "ATR_Authority",
    "OBV",
    "OBV_EMA_Period",
    "OBV_EMA",
    "OBV_Authority",
    "OBV_Limit_Status",
    "OBV_Operational_Use_Approved",
    "OBV_Fresh_Cross",
    "OBV_Score",
    "OBV_Score_Status",
    "OBV_Score_Message",
    "Aroon_Period",
    "Aroon_Up",
    "Aroon_Down",
    "Aroon_Authority",
    "Health_Score_Module_Status",
    "Health_Score_Authority",
    "Health_Score_Limit_Status",
    "Health_Score_Operational_Use_Approved",
    "Health_Score_Probability_Calibrated",
    "Raw_Health_Score",
    "Maximum_Health_Score",
    "Health_Score_Pct_Of_Maximum",
    "Health_Score_Threshold",
    "Health_Qualified",
    "Health_Qualification_State",
    "Health_Qualification_Message",
    "Price_Adjustment",
]

LOG_FIELDS = ["Run_ID", *OUTPUT_FIELDS]


def clean_number(value):
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    if isinstance(value, (float, int)) and not math.isfinite(float(value)):
        return ""
    return value


def validate_periods(ema_period, fast_period, slow_period, signal_period, minimum_history_bars):
    values = tuple(
        int(value)
        for value in (
            ema_period,
            fast_period,
            slow_period,
            signal_period,
            minimum_history_bars,
        )
    )
    if any(value < 1 for value in values):
        raise ValueError("EMA, MACD, and minimum-history periods must be positive integers")
    ema_period, fast_period, slow_period, signal_period, minimum_history_bars = values
    if fast_period >= slow_period:
        raise ValueError("MACD fast period must be smaller than MACD slow period")
    minimum_required = max(ema_period, slow_period + signal_period - 1)
    if minimum_history_bars < minimum_required:
        raise ValueError(
            f"Minimum_History_Bars must be at least {minimum_required} for the configured indicators"
        )
    return values


def load_config(config_path=DEFAULT_CONFIG_PATH, overrides=None):
    path = Path(config_path)
    config = json.loads(path.read_text(encoding="utf-8"))
    config = dict(config)
    config["MACD"] = dict(config["MACD"])
    config["Indicators"] = dict(config["Indicators"])
    config["Indicator_Rules"] = dict(config["Indicator_Rules"])
    for name in ("DMI", "RSI", "ADX", "OBV", "ATR", "Aroon"):
        config["Indicator_Rules"][name] = dict(config["Indicator_Rules"][name])
    config["Health_Score"] = dict(config["Health_Score"])
    for key, value in (overrides or {}).items():
        if value is None:
            continue
        if key.startswith("MACD."):
            config["MACD"][key.split(".", 1)[1]] = int(value)
        elif key.startswith("Indicators."):
            config["Indicators"][key.split(".", 1)[1]] = int(value)
        elif key.startswith("Health_Score."):
            config["Health_Score"][key.split(".", 1)[1]] = int(value)
        else:
            config[key] = value
    validate_periods(
        config["EMA_Period"],
        config["MACD"]["Fast"],
        config["MACD"]["Slow"],
        config["MACD"]["Signal"],
        config["Minimum_History_Bars"],
    )
    if config.get("Schema_Version") != ENGINE_VERSION:
        raise ValueError(
            f"unsupported basic Foundation schema: {config.get('Schema_Version')!r}"
        )
    if config.get("Decision_Scope") != "FOUNDATION_THEN_DMI_THEN_V1_COMPOSITE_HEALTH_SCORE":
        raise ValueError(
            "basic configuration must use FOUNDATION_THEN_DMI_THEN_V1_COMPOSITE_HEALTH_SCORE"
        )
    if config.get("Indicator_Authority") != "USER_APPROVED_RESEARCH_COMPOSITE_SCORE":
        raise ValueError(
            "basic indicator layer must use USER_APPROVED_RESEARCH_COMPOSITE_SCORE authority"
        )
    indicator_periods = [int(value) for value in config["Indicators"].values()]
    if any(value < 1 for value in indicator_periods):
        raise ValueError("indicator periods must be positive integers")
    rsi_rule = config["Indicator_Rules"]["RSI"]
    if not (
        float(rsi_rule["Minimum"])
        < float(rsi_rule["Preferred_Lower"])
        <= float(rsi_rule["Preferred_Upper"])
        < float(rsi_rule["Maximum"])
    ):
        raise ValueError("RSI Health Score boundaries are not ordered")
    adx_rule = config["Indicator_Rules"]["ADX"]
    if not (
        float(adx_rule["Minimum"])
        < float(adx_rule["Preferred_Lower"])
        <= float(adx_rule["Preferred_Upper"])
        < float(adx_rule["High_Upper"])
    ):
        raise ValueError("ADX Health Score boundaries are not ordered")
    obv_rule = config["Indicator_Rules"]["OBV"]
    if int(obv_rule["EMA_Period"]) != int(config["Indicators"]["OBV_EMA_Period"]):
        raise ValueError("OBV rule EMA period must match the calculated OBV EMA period")
    if int(obv_rule["Cross_Lookback_Sessions"]) < 1:
        raise ValueError("OBV cross lookback must be positive")
    health = config["Health_Score"]
    if health.get("Components") != ["RSI", "ADX", "OBV"]:
        raise ValueError("Health Score components must be exactly RSI, ADX, and OBV")
    maximum = int(health["Maximum_Positive_Score"])
    threshold = int(health["Research_Qualification_Threshold"])
    if maximum != 30 or not 0 <= threshold <= maximum:
        raise ValueError("Health Score maximum must be 30 and threshold must be within 0..30")
    if health.get("Probability_Calibrated") is not False:
        raise ValueError("research Health Score must not claim probability calibration")
    research_rules = [
        config["Indicator_Rules"][name] for name in ("DMI", "RSI", "ADX", "OBV")
    ] + [health]
    for rule in research_rules:
        if rule.get("Limit_Status") != "USER_APPROVED_RESEARCH_NOT_OPERATIONAL":
            raise ValueError("research Score rules must retain research-only limit status")
        if rule.get("Operational_Use_Approved") is not False:
            raise ValueError("research Score rules are not approved for operational use")
    if any(value is not None for value in (overrides or {}).values()):
        config["Configuration_ID"] = (
            f"{config['Configuration_ID']}__OVERRIDE_"
            f"EMA{int(config['EMA_Period'])}_"
            f"MACD{int(config['MACD']['Fast'])}_{int(config['MACD']['Slow'])}_{int(config['MACD']['Signal'])}_"
            f"RSI{int(config['Indicators']['RSI_Period'])}_"
            f"ADX{int(config['Indicators']['ADX_Period'])}_"
            f"ATR{int(config['Indicators']['ATR_Period'])}_"
            f"OBVEMA{int(config['Indicators']['OBV_EMA_Period'])}_"
            f"AROON{int(config['Indicators']['Aroon_Period'])}_"
            f"SCOREMIN{threshold}_"
            f"HIST{int(config['Minimum_History_Bars'])}"
        )
    return config


def score_rsi_value(value, rule):
    if value is None or pd.isna(value):
        return 0, "RSI_UNAVAILABLE", "RSI is unavailable; zero points assigned"
    value = float(value)
    if float(rule["Preferred_Lower"]) <= value <= float(rule["Preferred_Upper"]):
        score, status = int(rule["Score_Preferred_Range"]), "RSI_PREFERRED_RANGE"
    elif float(rule["Minimum"]) <= value < float(rule["Preferred_Lower"]):
        score, status = int(rule["Score_Minimum_To_Preferred"]), "RSI_MINIMUM_TO_PREFERRED"
    elif float(rule["Preferred_Upper"]) < value <= float(rule["Maximum"]):
        score, status = int(rule["Score_Preferred_To_Maximum"]), "RSI_PREFERRED_TO_MAXIMUM"
    elif value > float(rule["Maximum"]):
        score, status = int(rule["Score_Above_Maximum"]), "RSI_ABOVE_MAXIMUM"
    else:
        score, status = int(rule["Score_Below_Minimum"]), "RSI_BELOW_MINIMUM"
    return score, status, f"RSI {value:.2f} produced {score:+d} Health Score points ({status})"


def score_adx_value(value, rule):
    if value is None or pd.isna(value):
        return 0, "ADX_UNAVAILABLE", "ADX is unavailable; zero points assigned"
    value = float(value)
    if float(rule["Preferred_Lower"]) <= value <= float(rule["Preferred_Upper"]):
        score, status = int(rule["Score_Preferred_Range"]), "ADX_PREFERRED_RANGE"
    elif (
        float(rule["Minimum"]) <= value < float(rule["Preferred_Lower"])
        or float(rule["Preferred_Upper"]) < value <= float(rule["High_Upper"])
    ):
        score, status = int(rule["Score_Minimum_Or_High"]), "ADX_PARTIAL_RANGE"
    elif value > float(rule["High_Upper"]):
        score, status = int(rule["Score_Above_High"]), "ADX_ABOVE_HIGH"
    else:
        score, status = int(rule["Score_Below_Minimum"]), "ADX_BELOW_MINIMUM"
    return score, status, f"ADX {value:.2f} produced {score:+d} Health Score points ({status})"


def score_obv_frame(frame, rule):
    lookback = int(rule["Cross_Lookback_Sessions"])
    for offset in range(1, lookback + 1):
        if len(frame) <= offset:
            continue
        row = frame.iloc[-offset]
        previous = frame.iloc[-(offset + 1)]
        if row["OBV"] >= row["OBV_EMA"] and previous["OBV"] < previous["OBV_EMA"]:
            score = int(rule["Score_Fresh_Cross"])
            return score, True, "OBV_FRESH_CROSS", (
                f"OBV crossed above its EMA within {lookback} sessions; "
                f"{score:+d} Health Score points"
            )
    latest = frame.iloc[-1]
    previous = frame.iloc[-2]
    if latest["Close"] > previous["Close"] and latest["OBV"] < previous["OBV"]:
        score = int(rule["Score_Price_Up_OBV_Down"])
        return score, False, "OBV_NEGATIVE_DIVERGENCE", (
            f"Price rose while OBV fell; {score:+d} Health Score points"
        )
    score = int(rule["Score_Otherwise"])
    return score, False, "OBV_NO_SCORING_EVENT", (
        f"No configured OBV scoring event; {score:+d} Health Score points"
    )


def normalize_price_frame(price_df):
    if not isinstance(price_df, pd.DataFrame):
        raise TypeError("price data must be a pandas DataFrame")
    required_columns = ["Open", "High", "Low", "Close", "Volume"]
    missing = [column for column in required_columns if column not in price_df.columns]
    if missing:
        raise ValueError(f"price data is missing required columns: {', '.join(missing)}")
    frame = price_df.copy()
    index = pd.to_datetime(frame.index, errors="raise")
    if getattr(index, "tz", None) is not None:
        index = index.tz_convert(None)
    frame.index = index.normalize()
    if frame.index.has_duplicates:
        raise ValueError("price data contains duplicate trading dates")
    frame = frame.sort_index()
    for column in required_columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    if frame[required_columns].isna().any().any():
        raise ValueError("price data contains missing or non-numeric OHLCV values")
    if (frame[["Open", "High", "Low", "Close"]] <= 0).any().any():
        raise ValueError("price data contains non-positive OHLC values")
    if (frame["Volume"] < 0).any():
        raise ValueError("price data contains negative Volume values")
    return frame


def calculate_foundation_frame(price_df, config):
    frame = normalize_price_frame(price_df)
    close = frame["Close"]
    ema_period = int(config["EMA_Period"])
    fast_period = int(config["MACD"]["Fast"])
    slow_period = int(config["MACD"]["Slow"])
    signal_period = int(config["MACD"]["Signal"])
    validate_periods(
        ema_period,
        fast_period,
        slow_period,
        signal_period,
        config["Minimum_History_Bars"],
    )

    frame["EMA_Value"] = close.ewm(
        span=ema_period, adjust=False, min_periods=ema_period
    ).mean()
    fast_ema = close.ewm(
        span=fast_period, adjust=False, min_periods=fast_period
    ).mean()
    slow_ema = close.ewm(
        span=slow_period, adjust=False, min_periods=slow_period
    ).mean()
    frame["MACD_Line"] = fast_ema - slow_ema
    frame["MACD_Signal_Line"] = frame["MACD_Line"].ewm(
        span=signal_period, adjust=False, min_periods=signal_period
    ).mean()
    frame["MACD_Histogram"] = frame["MACD_Line"] - frame["MACD_Signal_Line"]
    return frame


def calculate_indicator_frame(foundation_frame, config, *, foundation_eligible):
    """Calculate post-Foundation indicators only after eligibility is confirmed."""
    if foundation_eligible is not True:
        raise RuntimeError(
            "post-Foundation indicator module requires confirmed Foundation eligibility"
        )
    required_foundation_columns = {
        "EMA_Value",
        "MACD_Line",
        "MACD_Signal_Line",
        "MACD_Histogram",
    }
    missing = required_foundation_columns.difference(foundation_frame.columns)
    if missing:
        raise ValueError(
            "indicator module requires a completed Foundation frame; missing: "
            + ", ".join(sorted(missing))
        )
    frame = foundation_frame.copy()
    high = frame["High"]
    low = frame["Low"]
    close = frame["Close"]
    volume = frame["Volume"]
    periods = config["Indicators"]

    rsi_period = int(periods["RSI_Period"])
    adx_period = int(periods["ADX_Period"])
    atr_period = int(periods["ATR_Period"])
    obv_ema_period = int(periods["OBV_EMA_Period"])
    aroon_period = int(periods["Aroon_Period"])

    frame["RSI"] = ta.momentum.rsi(close, window=rsi_period, fillna=False)
    adx = ta.trend.ADXIndicator(
        high=high, low=low, close=close, window=adx_period, fillna=False
    )
    frame["ADX"] = adx.adx()
    frame["DMI_Positive"] = adx.adx_pos()
    frame["DMI_Negative"] = adx.adx_neg()

    previous_close = close.shift(1)
    frame["True_Range"] = pd.concat(
        [
            high - low,
            (high - previous_close).abs(),
            (low - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    frame["ATR"] = ta.volatility.average_true_range(
        high=high, low=low, close=close, window=atr_period, fillna=False
    )
    frame["ATR_Pct"] = (frame["ATR"] / close) * 100.0

    frame["OBV"] = ta.volume.on_balance_volume(close, volume, fillna=False)
    frame["OBV_EMA"] = ta.trend.ema_indicator(
        frame["OBV"], window=obv_ema_period, fillna=False
    )

    aroon = ta.trend.AroonIndicator(
        high=high, low=low, window=aroon_period, fillna=False
    )
    frame["Aroon_Up"] = aroon.aroon_up()
    frame["Aroon_Down"] = aroon.aroon_down()
    return frame


def classify_foundation_values(
    close,
    ema_value,
    macd_line,
    macd_signal_line,
    bars_used,
    minimum_history_bars,
):
    required = (close, ema_value, macd_line, macd_signal_line)
    if int(bars_used) < int(minimum_history_bars) or any(pd.isna(value) for value in required):
        return {
            "Data_Status": DATA_INSUFFICIENT,
            "Foundation_Eligible": False,
            "Foundation_State": FOUNDATION_INSUFFICIENT,
            "Foundation_Reason": (
                f"insufficient history: {int(bars_used)} bars available; "
                f"{int(minimum_history_bars)} required"
            ),
        }
    if float(close) <= float(ema_value):
        return {
            "Data_Status": DATA_VALID,
            "Foundation_Eligible": False,
            "Foundation_State": FOUNDATION_BELOW_EMA,
            "Foundation_Reason": "close is at or below the configured long-term EMA",
        }
    if float(macd_line) > float(macd_signal_line) and float(macd_line) > 0:
        return {
            "Data_Status": DATA_VALID,
            "Foundation_Eligible": True,
            "Foundation_State": FOUNDATION_ELIGIBLE,
            "Foundation_Reason": (
                "close is above EMA and MACD line is above both signal line and zero"
            ),
        }
    if float(macd_line) > 0:
        return {
            "Data_Status": DATA_VALID,
            "Foundation_Eligible": False,
            "Foundation_State": FOUNDATION_MACD_POSITIVE_PULLBACK,
            "Foundation_Reason": (
                "close is above EMA and MACD is positive, but MACD line is at or below signal line"
            ),
        }
    if float(macd_line) > float(macd_signal_line):
        return {
            "Data_Status": DATA_VALID,
            "Foundation_Eligible": False,
            "Foundation_State": FOUNDATION_MACD_EARLY_RECOVERY,
            "Foundation_Reason": (
                "close is above EMA and MACD line is improving above signal, but remains at or below zero"
            ),
        }
    return {
        "Data_Status": DATA_VALID,
        "Foundation_Eligible": False,
        "Foundation_State": FOUNDATION_MACD_NEGATIVE_WEAKENING,
        "Foundation_Reason": (
            "close is above EMA but MACD line is at or below both signal line and zero"
        ),
    }


def evaluate_foundation(ticker, price_df, config, as_of=None, evaluated_at=None):
    frame = normalize_price_frame(price_df)
    if as_of is not None:
        as_of_stamp = pd.Timestamp(as_of)
        if as_of_stamp.tzinfo is not None:
            as_of_stamp = as_of_stamp.tz_convert(None)
        frame = frame.loc[frame.index <= as_of_stamp.normalize()]
    bars_used = len(frame)
    evaluated_at = evaluated_at or datetime.now(timezone.utc)
    rules = config["Indicator_Rules"]
    health = config["Health_Score"]
    base = {
        "Engine_Version": ENGINE_VERSION,
        "Configuration_ID": config["Configuration_ID"],
        "Decision_Scope": config["Decision_Scope"],
        "Indicator_Set_ID": config["Indicator_Set_ID"],
        "Indicator_Authority": config["Indicator_Authority"],
        "Indicator_Module_Status": INDICATOR_MODULE_NOT_RUN,
        "Indicator_Module_Reason": "Foundation eligibility was not confirmed",
        "Ticker": str(ticker).strip().upper(),
        "Evaluated_At_UTC": evaluated_at.isoformat(),
        "As_Of_Date": frame.index[-1].date().isoformat() if bars_used else "",
        "First_Price_Date": frame.index[0].date().isoformat() if bars_used else "",
        "Bars_Used": bars_used,
        "Minimum_History_Bars": int(config["Minimum_History_Bars"]),
        "Close": "",
        "EMA_Period": int(config["EMA_Period"]),
        "EMA_Value": "",
        "MACD_Fast_Period": int(config["MACD"]["Fast"]),
        "MACD_Slow_Period": int(config["MACD"]["Slow"]),
        "MACD_Signal_Period": int(config["MACD"]["Signal"]),
        "MACD_Line": "",
        "MACD_Signal_Line": "",
        "MACD_Histogram": "",
        "RSI_Period": int(config["Indicators"]["RSI_Period"]),
        "RSI": "",
        "RSI_Authority": rules["RSI"]["Authority"],
        "RSI_Limit_Status": rules["RSI"]["Limit_Status"],
        "RSI_Operational_Use_Approved": rules["RSI"]["Operational_Use_Approved"],
        "RSI_Score": "",
        "RSI_Score_Status": "NOT_EVALUATED_FOUNDATION_INELIGIBLE",
        "RSI_Score_Message": "RSI Score was not evaluated because Foundation eligibility was not confirmed",
        "ADX_Period": int(config["Indicators"]["ADX_Period"]),
        "ADX": "",
        "ADX_Authority": rules["ADX"]["Authority"],
        "ADX_Limit_Status": rules["ADX"]["Limit_Status"],
        "ADX_Operational_Use_Approved": rules["ADX"]["Operational_Use_Approved"],
        "ADX_Score": "",
        "ADX_Score_Status": "NOT_EVALUATED_FOUNDATION_INELIGIBLE",
        "ADX_Score_Message": "ADX Score was not evaluated because Foundation eligibility was not confirmed",
        "DMI_Positive": "",
        "DMI_Negative": "",
        "DMI_Authority": rules["DMI"]["Authority"],
        "DMI_Limit_Status": rules["DMI"]["Limit_Status"],
        "DMI_Operational_Use_Approved": rules["DMI"]["Operational_Use_Approved"],
        "DMI_Eligible": "",
        "DMI_Status": "NOT_EVALUATED_FOUNDATION_INELIGIBLE",
        "DMI_Message": "DMI eligibility was not evaluated because Foundation eligibility was not confirmed",
        "True_Range": "",
        "ATR_Period": int(config["Indicators"]["ATR_Period"]),
        "ATR": "",
        "ATR_Pct": "",
        "ATR_Authority": rules["ATR"]["Authority"],
        "OBV": "",
        "OBV_EMA_Period": int(config["Indicators"]["OBV_EMA_Period"]),
        "OBV_EMA": "",
        "OBV_Authority": rules["OBV"]["Authority"],
        "OBV_Limit_Status": rules["OBV"]["Limit_Status"],
        "OBV_Operational_Use_Approved": rules["OBV"]["Operational_Use_Approved"],
        "OBV_Fresh_Cross": "",
        "OBV_Score": "",
        "OBV_Score_Status": "NOT_EVALUATED_FOUNDATION_INELIGIBLE",
        "OBV_Score_Message": "OBV Score was not evaluated because Foundation eligibility was not confirmed",
        "Aroon_Period": int(config["Indicators"]["Aroon_Period"]),
        "Aroon_Up": "",
        "Aroon_Down": "",
        "Aroon_Authority": rules["Aroon"]["Authority"],
        "Health_Score_Module_Status": HEALTH_SCORE_NOT_RUN_FOUNDATION,
        "Health_Score_Authority": health["Authority"],
        "Health_Score_Limit_Status": health["Limit_Status"],
        "Health_Score_Operational_Use_Approved": health["Operational_Use_Approved"],
        "Health_Score_Probability_Calibrated": health["Probability_Calibrated"],
        "Raw_Health_Score": "",
        "Maximum_Health_Score": int(health["Maximum_Positive_Score"]),
        "Health_Score_Pct_Of_Maximum": "",
        "Health_Score_Threshold": int(health["Research_Qualification_Threshold"]),
        "Health_Qualified": False,
        "Health_Qualification_State": "FOUNDATION_NOT_ELIGIBLE",
        "Health_Qualification_Message": "Health Score was not calculated because Foundation eligibility was not confirmed",
        "Price_Adjustment": config["Price_Adjustment"],
    }
    if not bars_used:
        classification = classify_foundation_values(
            float("nan"),
            float("nan"),
            float("nan"),
            float("nan"),
            0,
            config["Minimum_History_Bars"],
        )
    else:
        foundation = calculate_foundation_frame(frame, config)
        latest = foundation.iloc[-1]
        base.update(
            {
                "Close": latest["Close"],
                "EMA_Value": latest["EMA_Value"],
                "MACD_Line": latest["MACD_Line"],
                "MACD_Signal_Line": latest["MACD_Signal_Line"],
                "MACD_Histogram": latest["MACD_Histogram"],
            }
        )
        classification = classify_foundation_values(
            latest["Close"],
            latest["EMA_Value"],
            latest["MACD_Line"],
            latest["MACD_Signal_Line"],
            bars_used,
            config["Minimum_History_Bars"],
        )
        if classification["Foundation_Eligible"]:
            calculated = calculate_indicator_frame(
                foundation,
                config,
                foundation_eligible=True,
            )
            latest = calculated.iloc[-1]
            base.update(
                {
                    "Indicator_Module_Status": INDICATOR_MODULE_EXECUTED,
                    "Indicator_Module_Reason": (
                        "Foundation eligibility confirmed before indicator calculation"
                    ),
                    "RSI": latest["RSI"],
                    "ADX": latest["ADX"],
                    "DMI_Positive": latest["DMI_Positive"],
                    "DMI_Negative": latest["DMI_Negative"],
                    "True_Range": latest["True_Range"],
                    "ATR": latest["ATR"],
                    "ATR_Pct": latest["ATR_Pct"],
                    "OBV": latest["OBV"],
                    "OBV_EMA": latest["OBV_EMA"],
                    "Aroon_Up": latest["Aroon_Up"],
                    "Aroon_Down": latest["Aroon_Down"],
                }
            )
            dmi_eligible = bool(latest["DMI_Positive"] > latest["DMI_Negative"])
            base.update(
                {
                    "DMI_Eligible": dmi_eligible,
                    "DMI_Status": (
                        "DMI_ELIGIBLE_POSITIVE_DOMINANCE"
                        if dmi_eligible
                        else "DMI_NOT_ELIGIBLE_POSITIVE_NOT_GREATER_THAN_NEGATIVE"
                    ),
                    "DMI_Message": (
                        f"+DI {float(latest['DMI_Positive']):.2f} is greater than "
                        f"-DI {float(latest['DMI_Negative']):.2f}; Health Score calculation is allowed"
                        if dmi_eligible
                        else f"+DI {float(latest['DMI_Positive']):.2f} is not greater than "
                        f"-DI {float(latest['DMI_Negative']):.2f}; Health Score calculation is not allowed"
                    ),
                }
            )
            if not dmi_eligible:
                base.update(
                    {
                        "Health_Score_Module_Status": HEALTH_SCORE_NOT_RUN_DMI,
                        "RSI_Score_Status": "NOT_EVALUATED_DMI_INELIGIBLE",
                        "RSI_Score_Message": "RSI Score was not evaluated because DMI eligibility failed",
                        "ADX_Score_Status": "NOT_EVALUATED_DMI_INELIGIBLE",
                        "ADX_Score_Message": "ADX Score was not evaluated because DMI eligibility failed",
                        "OBV_Score_Status": "NOT_EVALUATED_DMI_INELIGIBLE",
                        "OBV_Score_Message": "OBV Score was not evaluated because DMI eligibility failed",
                        "Health_Qualification_State": "NOT_QUALIFIED_DMI_INELIGIBLE",
                        "Health_Qualification_Message": "Health Score was not calculated because +DI is not greater than -DI",
                    }
                )
            else:
                rsi_score, rsi_status, rsi_message = score_rsi_value(
                    latest["RSI"], rules["RSI"]
                )
                adx_score, adx_status, adx_message = score_adx_value(
                    latest["ADX"], rules["ADX"]
                )
                obv_score, obv_cross, obv_status, obv_message = score_obv_frame(
                    calculated, rules["OBV"]
                )
                raw_score = rsi_score + adx_score + obv_score
                threshold = int(health["Research_Qualification_Threshold"])
                maximum = int(health["Maximum_Positive_Score"])
                qualified = raw_score >= threshold
                base.update(
                    {
                        "Health_Score_Module_Status": HEALTH_SCORE_EXECUTED,
                        "RSI_Score": rsi_score,
                        "RSI_Score_Status": rsi_status,
                        "RSI_Score_Message": rsi_message,
                        "ADX_Score": adx_score,
                        "ADX_Score_Status": adx_status,
                        "ADX_Score_Message": adx_message,
                        "OBV_Fresh_Cross": obv_cross,
                        "OBV_Score": obv_score,
                        "OBV_Score_Status": obv_status,
                        "OBV_Score_Message": obv_message,
                        "Raw_Health_Score": raw_score,
                        "Health_Score_Pct_Of_Maximum": 100.0 * raw_score / maximum,
                        "Health_Qualified": qualified,
                        "Health_Qualification_State": (
                            "RESEARCH_HEALTH_QUALIFIED"
                            if qualified
                            else "NOT_QUALIFIED_HEALTH_SCORE"
                        ),
                        "Health_Qualification_Message": (
                            f"Raw Health Score {raw_score}/{maximum} meets research threshold {threshold}"
                            if qualified
                            else f"Raw Health Score {raw_score}/{maximum} is below research threshold {threshold}"
                        ),
                    }
                )
    base.update(classification)
    return {field: clean_number(base.get(field, "")) for field in OUTPUT_FIELDS}


def download_daily(ticker, period="5y"):
    frame = yf.download(
        ticker,
        period=period,
        interval="1d",
        auto_adjust=False,
        actions=False,
        progress=False,
        threads=False,
    )
    if isinstance(frame.columns, pd.MultiIndex):
        frame.columns = frame.columns.get_level_values(0)
    if frame.empty:
        raise RuntimeError("no daily price data returned")
    return frame


def timestamped_path(path):
    path = Path(path)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return path.with_name(f"{path.stem}_{stamp}{path.suffix}")


def initialize_log(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file() and path.stat().st_size:
        with path.open("r", encoding="utf-8", newline="") as file:
            header = next(csv.reader(file), [])
        if header == LOG_FIELDS:
            return path
        path = timestamped_path(path)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=LOG_FIELDS)
        writer.writeheader()
    return path


def append_log(path, run_id, row):
    with Path(path).open("a", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=LOG_FIELDS)
        writer.writerow(
            {"Run_ID": run_id, **{field: clean_number(row.get(field, "")) for field in OUTPUT_FIELDS}}
        )


def write_snapshot(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: clean_number(row.get(field, "")) for field in OUTPUT_FIELDS})
    return path


def parse_args():
    parser = argparse.ArgumentParser(
        description="V8 Foundation, DMI eligibility, and V1 composite Health Score research engine",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("tickers", nargs="+", help="US ticker symbols to evaluate")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--period", default="5y", help="Daily history requested from yfinance")
    parser.add_argument("--as-of", help="Optional historical cutoff date YYYY-MM-DD")
    parser.add_argument("--ema-period", type=int)
    parser.add_argument("--macd-fast", type=int)
    parser.add_argument("--macd-slow", type=int)
    parser.add_argument("--macd-signal", type=int)
    parser.add_argument("--minimum-history", type=int)
    parser.add_argument("--rsi-period", type=int)
    parser.add_argument("--adx-period", type=int)
    parser.add_argument("--atr-period", type=int)
    parser.add_argument("--obv-ema-period", type=int)
    parser.add_argument("--aroon-period", type=int)
    parser.add_argument("--health-score-threshold", type=int)
    parser.add_argument("--output", type=Path, default=DEFAULT_SNAPSHOT_PATH)
    parser.add_argument("--log-output", type=Path, default=DEFAULT_LOG_PATH)
    return parser.parse_args()


def main():
    args = parse_args()
    overrides = {
        "EMA_Period": args.ema_period,
        "MACD.Fast": args.macd_fast,
        "MACD.Slow": args.macd_slow,
        "MACD.Signal": args.macd_signal,
        "Minimum_History_Bars": args.minimum_history,
        "Indicators.RSI_Period": args.rsi_period,
        "Indicators.ADX_Period": args.adx_period,
        "Indicators.ATR_Period": args.atr_period,
        "Indicators.OBV_EMA_Period": args.obv_ema_period,
        "Indicators.Aroon_Period": args.aroon_period,
        "Health_Score.Research_Qualification_Threshold": args.health_score_threshold,
    }
    try:
        config = load_config(args.config, overrides)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Configuration error: {exc}")

    run_id = datetime.now(timezone.utc).strftime("V8BASIC_%Y%m%dT%H%M%S%fZ")
    log_path = initialize_log(args.log_output)
    rows = []
    for ticker in list(dict.fromkeys(value.strip().upper() for value in args.tickers if value.strip())):
        try:
            prices = download_daily(ticker, args.period)
            row = evaluate_foundation(ticker, prices, config, args.as_of)
        except Exception as exc:
            row = {
                field: "" for field in OUTPUT_FIELDS
            }
            row.update(
                {
                    "Engine_Version": ENGINE_VERSION,
                    "Configuration_ID": config["Configuration_ID"],
                    "Decision_Scope": config["Decision_Scope"],
                    "Indicator_Set_ID": config["Indicator_Set_ID"],
                    "Indicator_Authority": config["Indicator_Authority"],
                    "Ticker": ticker,
                    "Evaluated_At_UTC": datetime.now(timezone.utc).isoformat(),
                    "Minimum_History_Bars": config["Minimum_History_Bars"],
                    "Data_Status": "DATA_ERROR",
                    "Foundation_Eligible": False,
                    "Foundation_State": "FOUNDATION_DATA_ERROR",
                    "Foundation_Reason": str(exc),
                    "EMA_Period": config["EMA_Period"],
                    "MACD_Fast_Period": config["MACD"]["Fast"],
                    "MACD_Slow_Period": config["MACD"]["Slow"],
                    "MACD_Signal_Period": config["MACD"]["Signal"],
                    "RSI_Period": config["Indicators"]["RSI_Period"],
                    "RSI_Authority": config["Indicator_Rules"]["RSI"]["Authority"],
                    "RSI_Limit_Status": config["Indicator_Rules"]["RSI"]["Limit_Status"],
                    "RSI_Operational_Use_Approved": config["Indicator_Rules"]["RSI"]["Operational_Use_Approved"],
                    "RSI_Score_Status": "NOT_EVALUATED_DATA_ERROR",
                    "RSI_Score_Message": "RSI Score was not evaluated because price data failed",
                    "ADX_Period": config["Indicators"]["ADX_Period"],
                    "ADX_Authority": config["Indicator_Rules"]["ADX"]["Authority"],
                    "ADX_Limit_Status": config["Indicator_Rules"]["ADX"]["Limit_Status"],
                    "ADX_Operational_Use_Approved": config["Indicator_Rules"]["ADX"]["Operational_Use_Approved"],
                    "ADX_Score_Status": "NOT_EVALUATED_DATA_ERROR",
                    "ADX_Score_Message": "ADX Score was not evaluated because price data failed",
                    "DMI_Authority": config["Indicator_Rules"]["DMI"]["Authority"],
                    "DMI_Limit_Status": config["Indicator_Rules"]["DMI"]["Limit_Status"],
                    "DMI_Operational_Use_Approved": config["Indicator_Rules"]["DMI"]["Operational_Use_Approved"],
                    "DMI_Status": "NOT_EVALUATED_DATA_ERROR",
                    "DMI_Message": "DMI eligibility was not evaluated because price data failed",
                    "ATR_Period": config["Indicators"]["ATR_Period"],
                    "ATR_Authority": config["Indicator_Rules"]["ATR"]["Authority"],
                    "OBV_EMA_Period": config["Indicators"]["OBV_EMA_Period"],
                    "OBV_Authority": config["Indicator_Rules"]["OBV"]["Authority"],
                    "OBV_Limit_Status": config["Indicator_Rules"]["OBV"]["Limit_Status"],
                    "OBV_Operational_Use_Approved": config["Indicator_Rules"]["OBV"]["Operational_Use_Approved"],
                    "OBV_Score_Status": "NOT_EVALUATED_DATA_ERROR",
                    "OBV_Score_Message": "OBV Score was not evaluated because price data failed",
                    "Aroon_Period": config["Indicators"]["Aroon_Period"],
                    "Aroon_Authority": config["Indicator_Rules"]["Aroon"]["Authority"],
                    "Health_Score_Module_Status": "NOT_RUN_DATA_ERROR",
                    "Health_Score_Authority": config["Health_Score"]["Authority"],
                    "Health_Score_Limit_Status": config["Health_Score"]["Limit_Status"],
                    "Health_Score_Operational_Use_Approved": config["Health_Score"]["Operational_Use_Approved"],
                    "Health_Score_Probability_Calibrated": config["Health_Score"]["Probability_Calibrated"],
                    "Maximum_Health_Score": config["Health_Score"]["Maximum_Positive_Score"],
                    "Health_Score_Threshold": config["Health_Score"]["Research_Qualification_Threshold"],
                    "Health_Qualified": False,
                    "Health_Qualification_State": "DATA_ERROR",
                    "Health_Qualification_Message": "Health Score was not calculated because price data failed",
                    "Price_Adjustment": config["Price_Adjustment"],
                }
            )
        row = {field: clean_number(row.get(field, "")) for field in OUTPUT_FIELDS}
        rows.append(row)
        append_log(log_path, run_id, row)
        print(
            f"{ticker}: {row['Foundation_State']} | eligible={row['Foundation_Eligible']} | "
            f"dmi_eligible={row['DMI_Eligible']} | raw_health_score={row['Raw_Health_Score']} | "
            f"health_qualified={row['Health_Qualified']} | "
            f"health_message={row['Health_Qualification_Message']}"
        )
    snapshot_path = write_snapshot(args.output, rows)
    print(f"Snapshot: {snapshot_path.resolve()}")
    print(f"Append-only log: {log_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
