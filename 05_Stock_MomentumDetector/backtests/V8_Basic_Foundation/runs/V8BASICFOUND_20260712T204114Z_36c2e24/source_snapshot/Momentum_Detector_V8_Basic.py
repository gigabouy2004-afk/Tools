import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf


ROOT = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = ROOT / "config" / "V8_Basic_Foundation_Config.json"
DEFAULT_SNAPSHOT_PATH = ROOT / "Processed_Data" / "V8_Basic_Foundation_Snapshot.csv"
DEFAULT_LOG_PATH = ROOT / "Processed_Data" / "V8_Basic_Foundation_Execution_Log.csv"

ENGINE_VERSION = "V8_BASIC_FOUNDATION_1"

DATA_VALID = "DATA_VALID"
DATA_INSUFFICIENT = "DATA_INSUFFICIENT_HISTORY"

FOUNDATION_ELIGIBLE = "FOUNDATION_ELIGIBLE_BULLISH_POSITIVE_MACD"
FOUNDATION_BELOW_EMA = "FOUNDATION_NOT_ELIGIBLE_BELOW_OR_AT_EMA"
FOUNDATION_MACD_POSITIVE_PULLBACK = "FOUNDATION_NOT_ELIGIBLE_MACD_POSITIVE_PULLBACK"
FOUNDATION_MACD_EARLY_RECOVERY = "FOUNDATION_NOT_ELIGIBLE_MACD_EARLY_RECOVERY_BELOW_ZERO"
FOUNDATION_MACD_NEGATIVE_WEAKENING = "FOUNDATION_NOT_ELIGIBLE_MACD_NEGATIVE_WEAKENING"
FOUNDATION_INSUFFICIENT = "FOUNDATION_INSUFFICIENT_DATA"

OUTPUT_FIELDS = [
    "Engine_Version",
    "Configuration_ID",
    "Decision_Scope",
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
    for key, value in (overrides or {}).items():
        if value is None:
            continue
        if key.startswith("MACD."):
            config["MACD"][key.split(".", 1)[1]] = int(value)
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
    if config.get("Decision_Scope") != "FOUNDATION_ONLY_NO_SCORE":
        raise ValueError("basic Foundation configuration must use FOUNDATION_ONLY_NO_SCORE")
    if any(value is not None for value in (overrides or {}).values()):
        config["Configuration_ID"] = (
            f"{config['Configuration_ID']}__OVERRIDE_"
            f"EMA{int(config['EMA_Period'])}_"
            f"MACD{int(config['MACD']['Fast'])}_{int(config['MACD']['Slow'])}_{int(config['MACD']['Signal'])}_"
            f"HIST{int(config['Minimum_History_Bars'])}"
        )
    return config


def normalize_price_frame(price_df):
    if not isinstance(price_df, pd.DataFrame):
        raise TypeError("price data must be a pandas DataFrame")
    if "Close" not in price_df.columns:
        raise ValueError("price data is missing required Close column")
    frame = price_df.copy()
    index = pd.to_datetime(frame.index, errors="raise")
    if getattr(index, "tz", None) is not None:
        index = index.tz_convert(None)
    frame.index = index.normalize()
    if frame.index.has_duplicates:
        raise ValueError("price data contains duplicate trading dates")
    frame = frame.sort_index()
    frame["Close"] = pd.to_numeric(frame["Close"], errors="coerce")
    if frame["Close"].isna().any():
        raise ValueError("price data contains missing or non-numeric Close values")
    if (frame["Close"] <= 0).any():
        raise ValueError("price data contains non-positive Close values")
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
    base = {
        "Engine_Version": ENGINE_VERSION,
        "Configuration_ID": config["Configuration_ID"],
        "Decision_Scope": config["Decision_Scope"],
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
        calculated = calculate_foundation_frame(frame, config)
        latest = calculated.iloc[-1]
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
        description="Minimal V8 EMA/MACD Foundation eligibility engine",
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
                    "Price_Adjustment": config["Price_Adjustment"],
                }
            )
        row = {field: clean_number(row.get(field, "")) for field in OUTPUT_FIELDS}
        rows.append(row)
        append_log(log_path, run_id, row)
        print(
            f"{ticker}: {row['Foundation_State']} | eligible={row['Foundation_Eligible']} | "
            f"reason={row['Foundation_Reason']}"
        )
    snapshot_path = write_snapshot(args.output, rows)
    print(f"Snapshot: {snapshot_path.resolve()}")
    print(f"Append-only log: {log_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
