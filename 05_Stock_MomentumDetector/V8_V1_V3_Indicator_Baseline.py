import json
import math
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

import Momentum_Detector_V8_Basic as basic


ROOT = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = ROOT / "config" / "V8_V1_V3_Indicator_Baseline_Config.json"
ENGINE_VERSION = "V8_V1_V3_BASELINE_1"


def load_config(path=DEFAULT_CONFIG_PATH):
    config = json.loads(Path(path).read_text(encoding="utf-8"))
    if config.get("Schema_Version") != ENGINE_VERSION:
        raise ValueError(f"unsupported V1-V3 baseline schema: {config.get('Schema_Version')!r}")
    if config.get("Limit_Status") != "RESEARCH_CANDIDATE_NOT_OPERATIONAL":
        raise ValueError("V1-V3 historical values must remain research candidates")
    if config.get("Operational_Use_Approved") is not False:
        raise ValueError("V1-V3 historical values are not approved for operational use")
    basic.validate_periods(
        config["EMA_Period"],
        config["MACD"]["Fast"],
        config["MACD"]["Slow"],
        config["MACD"]["Signal"],
        config["Minimum_History_Bars"],
    )
    if set(config["Profiles"]) != {"V1", "V2", "V3"}:
        raise ValueError("profiles must be exactly V1, V2, and V3")
    if config["Profiles"]["V1"] != config["Profiles"]["V2"]:
        raise ValueError("V1 and V2 historical technical profiles must be identical")
    periods = config["Indicators"]
    if any(int(value) < 1 for value in periods.values()):
        raise ValueError("all indicator periods must be positive")
    rsi = config["Indicator_Rules"]["RSI"]
    if not (
        float(rsi["Minimum"])
        < float(rsi["Preferred_Lower"])
        <= float(rsi["Preferred_Upper"])
        < float(rsi["Maximum"])
    ):
        raise ValueError("RSI historical boundaries are not ordered")
    adx = config["Indicator_Rules"]["ADX"]
    if not (
        float(adx["Minimum"])
        < float(adx["Preferred_Lower"])
        <= float(adx["Preferred_Upper"])
        < float(adx["High_Upper"])
    ):
        raise ValueError("ADX historical boundaries are not ordered")
    return config


def score_rsi(value, rule):
    if value is None or pd.isna(value):
        return 0, "RSI_UNAVAILABLE"
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
    if value is None or pd.isna(value):
        return 0, "ADX_UNAVAILABLE"
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
    lookback = int(rule["Cross_Lookback_Sessions"])
    for offset in range(1, lookback + 1):
        if len(frame) <= offset:
            continue
        row = frame.iloc[-offset]
        previous = frame.iloc[-(offset + 1)]
        if (
            row["OBV"] >= row["OBV_EMA"]
            and previous["OBV"] < previous["OBV_EMA"]
        ):
            return int(rule["Score_Fresh_Cross"]), True, "OBV_FRESH_CROSS"
    latest = frame.iloc[-1]
    previous = frame.iloc[-2] if len(frame) >= 2 else None
    if (
        previous is not None
        and latest["Close"] > previous["Close"]
        and latest["OBV"] < previous["OBV"]
    ):
        return int(rule["Score_Price_Up_OBV_Down"]), False, "OBV_NEGATIVE_DIVERGENCE"
    return int(rule["Score_Otherwise"]), False, "OBV_NO_SCORING_EVENT"


def score_aroon(aroon_up, aroon_down, rule):
    if pd.isna(aroon_up) or pd.isna(aroon_down):
        return 0, "AROON_UNAVAILABLE"
    if (
        float(aroon_up) > float(rule["Strong_Up_Minimum_Exclusive"])
        and float(aroon_down) < float(rule["Strong_Down_Maximum_Exclusive"])
    ):
        return int(rule["Score_Strong"]), "AROON_STRONG"
    if (
        float(aroon_up) > float(rule["Moderate_Up_Minimum_Exclusive"])
        and float(aroon_down) < float(rule["Moderate_Down_Maximum_Exclusive"])
    ):
        return int(rule["Score_Moderate"]), "AROON_MODERATE"
    if (
        float(aroon_up) < float(rule["Bearish_Up_Maximum_Exclusive"])
        and float(aroon_down) > float(rule["Bearish_Down_Minimum_Exclusive"])
    ):
        return int(rule["Score_Bearish"]), "AROON_BEARISH"
    return int(rule["Score_Otherwise"]), "AROON_NEUTRAL"


def score_opening_structure(frame, rule):
    if len(frame) < 2:
        return int(rule["Score_Fail"]), False, "OPENING_STRUCTURE_UNAVAILABLE"
    passed = bool(frame["Open"].iloc[-1] > frame["Open"].iloc[-2])
    return (
        int(rule["Score_Pass"] if passed else rule["Score_Fail"]),
        passed,
        "OPEN_ABOVE_PRIOR_OPEN" if passed else "OPEN_NOT_ABOVE_PRIOR_OPEN",
    )


def _clean(value):
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


def evaluate_profile(ticker, price_df, as_of, profile_name, config, evaluated_at=None):
    if profile_name not in config["Profiles"]:
        raise ValueError(f"unknown profile: {profile_name}")
    profile = config["Profiles"][profile_name]
    frame = basic.normalize_price_frame(price_df)
    cutoff = pd.Timestamp(as_of).normalize()
    frame = frame.loc[frame.index <= cutoff]
    evaluated_at = evaluated_at or datetime.now(timezone.utc)
    bars = len(frame)
    result = {
        "Engine_Version": ENGINE_VERSION,
        "Configuration_ID": config["Configuration_ID"],
        "Limit_Status": config["Limit_Status"],
        "Operational_Use_Approved": config["Operational_Use_Approved"],
        "Profile": profile_name,
        "Ticker": str(ticker).upper(),
        "As_Of_Date": cutoff.date().isoformat(),
        "Evaluated_At_UTC": evaluated_at.isoformat(),
        "Bars_Used": bars,
        "Foundation_Eligible": False,
        "Foundation_State": basic.FOUNDATION_INSUFFICIENT,
        "Foundation_Reason": "insufficient history",
        "Indicator_Module_Status": "NOT_RUN_FOUNDATION_INELIGIBLE",
        "DMI_Dominance_Pass": "",
        "Close": "",
        "EMA_200": "",
        "MACD_Line": "",
        "MACD_Signal": "",
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
        "Qualification_State": "FOUNDATION_NOT_ELIGIBLE",
        "Qualification_Reason": "Foundation eligibility was not confirmed",
    }
    if bars:
        foundation = basic.calculate_foundation_frame(frame, config)
        latest = foundation.iloc[-1]
        classification = basic.classify_foundation_values(
            latest["Close"],
            latest["EMA_Value"],
            latest["MACD_Line"],
            latest["MACD_Signal_Line"],
            bars,
            config["Minimum_History_Bars"],
        )
        result.update(
            {
                "Foundation_Eligible": classification["Foundation_Eligible"],
                "Foundation_State": classification["Foundation_State"],
                "Foundation_Reason": classification["Foundation_Reason"],
                "Close": latest["Close"],
                "EMA_200": latest["EMA_Value"],
                "MACD_Line": latest["MACD_Line"],
                "MACD_Signal": latest["MACD_Signal_Line"],
                "Qualification_State": classification["Foundation_State"],
                "Qualification_Reason": classification["Foundation_Reason"],
            }
        )
        if classification["Foundation_Eligible"]:
            calculated = basic.calculate_indicator_frame(
                foundation, config, foundation_eligible=True
            )
            latest = calculated.iloc[-1]
            dmi_pass = bool(latest["DMI_Positive"] > latest["DMI_Negative"])
            result.update(
                {
                    "Indicator_Module_Status": "EXECUTED_FOUNDATION_ELIGIBLE",
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
                result.update(
                    {
                        "Qualification_State": "NOT_QUALIFIED_DMI_DOMINANCE",
                        "Qualification_Reason": "+DI is not greater than -DI",
                    }
                )
            else:
                rsi_score, rsi_status = score_rsi(
                    latest["RSI"], config["Indicator_Rules"]["RSI"]
                )
                adx_score, adx_status = score_adx(
                    latest["ADX"], config["Indicator_Rules"]["ADX"]
                )
                obv_score, obv_cross, obv_status = score_obv(
                    calculated, config["Indicator_Rules"]["OBV"]
                )
                aroon_score = 0
                aroon_status = "NOT_USED_IN_PROFILE"
                if profile["Use_Aroon"]:
                    aroon_score, aroon_status = score_aroon(
                        latest["Aroon_Up"],
                        latest["Aroon_Down"],
                        config["Indicator_Rules"]["Aroon"],
                    )
                structure_score = 0
                structure_pass = ""
                structure_status = "NOT_USED_IN_PROFILE"
                if profile["Use_Opening_Structure"]:
                    structure_score, structure_pass, structure_status = score_opening_structure(
                        calculated, config["Indicator_Rules"]["Opening_Structure"]
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
                        "Qualification_Reason": (
                            f"score {total} meets minimum {profile['Minimum_Momentum_Score']}"
                            if qualified
                            else f"score {total} below minimum {profile['Minimum_Momentum_Score']}"
                        ),
                    }
                )
    return {key: _clean(value) for key, value in result.items()}
