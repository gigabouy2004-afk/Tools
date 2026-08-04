import argparse
import contextlib
import csv
import io
import math
import os
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import yfinance as yf

from Beta_Context_V8 import apply_beta_postprocessor

DEFAULT_COUNT_X = 5       # Default max rows in the final summary
DEFAULT_SCORE_Y = 75.0    # Default minimum score included in the final summary

BASE_FOLDER = "D:/Tools/Stock_MomentumDetector"
SUMMARY_OUTPUT_CSV = os.path.join(BASE_FOLDER, "Processed_Data", "V8_Momentum_Execution_Dump.csv")
EXECUTION_LOG_CSV = os.path.join(BASE_FOLDER, "Processed_Data", "V8_Momentum_Execution_Log.csv")
TICKER_INPUT_CSV = Path("D:/Tools/StockCodeMaster/02_Stock/01-07-US_Common_Stocks_Master_Library.csv")

LOOKBACK_WINDOW = "5y"
BENCHMARK_TICKER = "SPY"
US_DEFAULT_BENCHMARK = "SPY"
US_GROWTH_BENCHMARK = "QQQ"
NSE_BENCHMARK = "^NSEI"
API_DELAY_SECONDS = 1.0
MIN_HISTORY_BARS = 300
MIN_MOMENTUM_SCORE = 70
MIN_AVG_DOLLAR_VOLUME_50D_US = 5_000_000
MIN_AVG_DOLLAR_VOLUME_50D_NSE = 100_000_000
EXTENDED_HOURS_WAIT_DROP_PCT = -2.0
EXTENDED_HOURS_REJECT_DROP_PCT = -5.0
LIVE_PRICE_SCORE_STATES = {"PRE", "REGULAR", "POST", "POSTPOST"}
DAILY_PULLBACK_DEEP_20D_HIGH_PCT = -8.0
DAILY_PULLBACK_EARLY_20D_HIGH_PCT = -5.0
DAILY_PULLBACK_5D_RETURN_PCT = -3.0
DAILY_DISTRIBUTION_DROP_PCT = -3.0
HIGH_VOLUME_PULLBACK_MAX_GAIN_PCT = 0.5
INTRADAY_SELLING_3H_RETURN_PCT = -1.0
BEARISH_HOURLY_CANDLES_CONFIRMATION = 2
CONFIRMED_ENTRY_MIN_SCORE = 85
CONFIRMED_ENTRY_MIN_RS_EXCESS_PCT = 5.0
CONFIRMED_ENTRY_MAX_ATR_PCT = 10.0
CONFIRMED_ENTRY_MAX_5D_RETURN_PCT = 18.0
CONFIRMED_ENTRY_MAX_10D_RETURN_PCT = 30.0
CONFIRMED_ENTRY_MIN_REL_VOLUME_20 = 0.75
CONFIRMED_ENTRY_MIN_CLOSE_LOCATION_PCT = 50.0
REJECT_SCORE_CAP = 49

STATUS_SORT_RANK = {
    "Momentum Candidate": 0,
    "Watchlist Candidate": 1,
    "Extended / Exhaustion Risk": 2,
    "Avoid": 3,
}

ENTRY_TIMING_SORT_RANK = {
    "Clean": 0,
    "Wait - Last Hour Bearish": 1,
    "Wait - Intraday Selling": 2,
    "Wait - Extended Hours Weakness": 3,
    "Wait - Daily Pullback Risk": 4,
    "Failed - Distribution Risk": 5,
    "Rejected - Extended Hours Breakdown": 6,
    "Insufficient history": 7,
}

ACTION_STATUS_RANK = {
    "Actionable Momentum Candidate": 1,
    "Watchlist Candidate": 2,
    "Downgraded - Wait": 3,
    "Rejected - Distribution Risk": 4,
    "Rejected - Extended Hours Breakdown": 4,
    "Avoid": 5,
}

FINAL_DECISION_RANK = {
    "MOMENTUM_ACTIVE": 1,
    "MOMENTUM_PRESENT_WAIT_CONFIRMATION": 2,
    "REJECT": 3,
}

FINAL_DECISION_SCORE_CAP = {
    "MOMENTUM_ACTIVE": 100,
    "MOMENTUM_PRESENT_WAIT_CONFIRMATION": CONFIRMED_ENTRY_MIN_SCORE - 1,
    "REJECT": REJECT_SCORE_CAP,
}

CSV_FIELDS = [
    "Ticker", "Final_Decision", "Final_Decision_Rank", "Final_Decision_Reason",
    "External_Message", "Analyst_Message", "EPS_Message", "Event_Message",
    "Action_Status", "Score", "Score_Message", "Action_Rank", "Long_Term_Status", "Entry_Timing_Status", "Classification_Reason",
    "Market_State", "Live_Price", "Regular_Market_Price", "PreMarket_Price", "PostMarket_Price",
    "Regular_Session_Close", "Score_Price_Source", "Score_Price_Change_Pct",
    "Extended_Hours_Change_Pct", "Close", "Trend_Score", "Relative_Strength_Score", "Breakout_Score", "Freshness_Score",
    "Accumulation_Score", "Volatility_Score", "Weekly_Trend_Score",
    "Weekly_Trend", "Weekly_Close", "Weekly_SMA_30", "Weekly_SMA_30_Slope_Pct_10W",
    "EMA_20", "EMA_50", "EMA_150", "EMA_200", "EMA_200_Slope_Pct_50D",
    "Exchange_Profile", "Benchmark_Ticker", "Return_63D_Pct", "Return_126D_Pct", "Return_252D_Pct", "Benchmark_Return_126D_Pct",
    "RS_126D_Excess_Pct", "RS_Ratio", "RS_SMA_50", "RS_SMA_200", "RS_Slope_Pct_50D",
    "Return_5D_Pct", "Return_10D_Pct", "High_20D", "High_55D", "High_100D", "High_252D",
    "Distance_From_20D_High_Pct", "Distance_From_52W_High_Pct", "Lower_High_Day",
    "Lower_Low_Day", "Close_Below_EMA20",
    "ATR_14", "ATR_Pct", "Volume", "Volume_Avg_20", "Volume_Avg_50", "Relative_Volume_20",
    "Avg_Dollar_Volume_50D", "Min_Avg_Dollar_Volume_50D", "Liquidity_Status",
    "Close_Location_Pct", "Extension_Risk", "Accumulation_Days_50",
    "Distribution_Days_50", "Net_Accumulation_50", "Latest_Distribution_Day",
    "Daily_Change_Pct", "Last_3H_Return_Pct", "Bearish_1H_Candles_Last3", "Last_1H_Bearish",
]

EXECUTION_LOG_FIELDS = ["Run_ID", "Processed_At", *CSV_FIELDS]


def clean_number(value):
    if value is None or pd.isna(value):
        return ""
    if isinstance(value, (int, float)) and not math.isfinite(value):
        return ""
    return value


def to_float(value):
    try:
        if value == "":
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def format_optional_number(value, width=8, decimals=2):
    if value in ["", None]:
        return " " * max(width - 3, 0) + "N/A"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return " " * max(width - 3, 0) + "N/A"
    if not math.isfinite(number):
        return " " * max(width - 3, 0) + "N/A"
    return f"{number:>{width}.{decimals}f}"


def sort_output_rows(rows):
    return sorted(
        rows,
        key=lambda row: (
            int(to_float(row.get("Final_Decision_Rank")) or 99),
            -to_float(row.get("Score")),
            -to_float(row.get("Trend_Score")),
            -to_float(row.get("Relative_Strength_Score")),
            -to_float(row.get("Breakout_Score")),
            -to_float(row.get("Accumulation_Score")),
            int(to_float(row.get("Action_Rank")) or 99),
            STATUS_SORT_RANK.get(row.get("Long_Term_Status"), 99),
            ENTRY_TIMING_SORT_RANK.get(row.get("Entry_Timing_Status"), 99),
            str(row.get("Ticker", "")),
        ),
    )


def timestamped_output_path(path):
    base, ext = os.path.splitext(path)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{base}_{timestamp}{ext}"


def write_summary_output(rows, output_path=SUMMARY_OUTPUT_CSV, force_unique=False):
    sorted_rows = sort_output_rows(rows)
    if force_unique:
        output_path = timestamped_output_path(output_path)
    output_path = os.path.abspath(output_path)
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    try:
        file = open(output_path, "w", encoding="utf-8", newline="")
    except OSError:
        output_path = timestamped_output_path(output_path)
        file = open(output_path, "w", encoding="utf-8", newline="")

    with file:
        writer = csv.DictWriter(file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in sorted_rows:
            writer.writerow({field: clean_number(row.get(field, "")) for field in CSV_FIELDS})

    return output_path, sorted_rows


def initialize_execution_log(output_path=EXECUTION_LOG_CSV):
    output_path = os.path.abspath(output_path)
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    has_content = os.path.exists(output_path) and os.path.getsize(output_path) > 0
    if has_content:
        with open(output_path, "r", encoding="utf-8", newline="") as file:
            existing_header = next(csv.reader(file), [])
        if existing_header != EXECUTION_LOG_FIELDS:
            raise ValueError(
                f"Execution log header does not match the current V8 schema: {output_path}"
            )
        return output_path

    with open(output_path, "a", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=EXECUTION_LOG_FIELDS)
        writer.writeheader()
        file.flush()
        os.fsync(file.fileno())
    return output_path


def append_execution_log_row(row, run_id, output_path=EXECUTION_LOG_CSV):
    output_path = os.path.abspath(output_path)
    log_row = {
        "Run_ID": run_id,
        "Processed_At": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    log_row.update({field: clean_number(row.get(field, "")) for field in CSV_FIELDS})

    with open(output_path, "a", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=EXECUTION_LOG_FIELDS)
        writer.writerow(log_row)
        file.flush()
        os.fsync(file.fileno())
    return output_path


def format_summary_row(row):
    reason = simplify_user_reason(row.get("Final_Decision_Reason", ""))
    summary = (
        f"{row.get('Ticker', ''):<8} | "
        f"{row.get('Final_Decision', ''):<34} | "
        f"Score {format_optional_number(row.get('Score'), width=5, decimals=1)} | "
        f"Close {format_optional_number(row.get('Close'))} | "
        f"Reason: {reason}"
    )
    external_message = str(row.get("External_Message", "") or "").strip()
    if external_message:
        summary += f" | External: {external_message}"
    return summary


def simplify_user_reason(reason):
    reason = str(reason or "")
    replacements = {
        "distribution cluster": "selling pressure too high",
        "below EMA200": "price below long-term trend",
        "weekly downtrend": "weekly trend down",
        "weekly mixed": "weekly trend not clear",
        "weekly flat": "weekly trend flat",
        "not outperforming SPY": "not beating market",
        "not outperforming benchmark": "not beating benchmark",
        "excess volatility": "too volatile",
        "average dollar volume below": "liquidity below threshold",
        "below EMA20 with deep 20D-high pullback": "deep short-term pullback",
        "below EMA20 with early 20D-high pullback": "early short-term pullback",
        "lower high and lower low": "daily price structure weakening",
        "pullback on above-average volume": "heavy-volume pullback",
        "daily distribution below EMA20": "heavy selling below short-term trend",
        "daily distribution": "heavy selling day",
        "last 3H selling": "late-session selling",
        "2+ bearish hourly candles": "multiple weak hourly candles",
        "last 1H bearish": "final hour weak",
        "relative volume below 1.0x": "not enough volume confirmation",
        "RS excess below 5.0%": "market outperformance too weak",
        "ATR above 10.0%": "too volatile for active momentum",
        "5D extension above 12.0%": "too stretched over 5 days",
        "10D extension above 20.0%": "too stretched over 10 days",
        "close location below 50.0%": "closed weak within daily range",
        "score below 85": "score too low",
        "not qualified": "momentum not valid",
        "no market data - check symbol": "no market data - check symbol",
        "insufficient price history": "insufficient price history",
        "all confirmation gates passed": "momentum active",
    }
    for old, new in replacements.items():
        reason = reason.replace(old, new)
    return reason


def print_cli_summary(rows, output_path, execution_log_path, total_processed):
    decisions = ["MOMENTUM_ACTIVE", "MOMENTUM_PRESENT_WAIT_CONFIRMATION", "REJECT"]
    counts = {decision: 0 for decision in decisions}
    for row in rows:
        decision = row.get("Final_Decision", "REJECT")
        counts[decision] = counts.get(decision, 0) + 1

    print("============================================================")
    print("=== MOMENTUM DETECTOR V8 COMPLETE ===")
    print("============================================================")
    print(f"Total Processed : {total_processed}")
    print(f"Summary Rows    : {len(rows)}")
    print(f"MOMENTUM_ACTIVE : {counts.get('MOMENTUM_ACTIVE', 0)}")
    print(f"WAIT_CONFIRM    : {counts.get('MOMENTUM_PRESENT_WAIT_CONFIRMATION', 0)}")
    print(f"REJECT          : {counts.get('REJECT', 0)}")

    print("\nTicker Decisions")
    for row in rows:
        print(format_summary_row(row))

    print(f"\nExecution Log CSV: {execution_log_path}")
    print(f"Summary Output CSV: {output_path}")


def parse_ticker_values(values):
    tickers = []
    for value in values or []:
        tickers.extend(part.strip() for part in str(value).split(","))
    return [ticker for ticker in tickers if ticker]


def resolve_action_status(long_term_status, entry_timing_status):
    if entry_timing_status == "Rejected - Extended Hours Breakdown":
        action_status = "Rejected - Extended Hours Breakdown"
    elif entry_timing_status == "Failed - Distribution Risk":
        action_status = "Rejected - Distribution Risk"
    elif long_term_status == "Momentum Candidate" and entry_timing_status == "Clean":
        action_status = "Actionable Momentum Candidate"
    elif long_term_status == "Momentum Candidate":
        action_status = "Downgraded - Wait"
    elif long_term_status == "Watchlist Candidate" and entry_timing_status == "Clean":
        action_status = "Watchlist Candidate"
    elif long_term_status == "Watchlist Candidate":
        action_status = "Downgraded - Wait"
    else:
        action_status = "Avoid"
    return ACTION_STATUS_RANK[action_status], action_status


def build_status_row(ticker, long_term_status, entry_timing_status, reason=""):
    action_rank, action_status = resolve_action_status(long_term_status, entry_timing_status)
    final_decision, final_rank, final_reason = resolve_final_decision({}, {}, "", {"status": entry_timing_status}, long_term_status, reason)
    return {
        "Ticker": ticker,
        "Final_Decision": final_decision,
        "Final_Decision_Rank": final_rank,
        "Final_Decision_Reason": final_reason,
        "Score": 0,
        "Action_Rank": action_rank,
        "Action_Status": action_status,
        "Long_Term_Status": long_term_status,
        "Entry_Timing_Status": entry_timing_status,
        "Classification_Reason": reason,
    }


def normalize_index(df):
    df = df.copy()
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    return df


def normalize_ticker(ticker, market="auto"):
    formatted = str(ticker).strip()
    if "XNSE" in formatted:
        formatted = formatted.replace("XNSE", "").replace(":", "").strip() + ".NS"
    if market == "nse" and "." not in formatted and ":" not in formatted:
        formatted = formatted + ".NS"
    return formatted


def exchange_profile_for_ticker(ticker, market="auto"):
    ticker_text = str(ticker).strip().upper()
    if market == "nse" or ticker_text.endswith(".NS"):
        return "NSE"
    return "US"


def benchmark_for_ticker(ticker, market="auto", us_benchmark=US_DEFAULT_BENCHMARK):
    profile = exchange_profile_for_ticker(ticker, market)
    if profile == "NSE":
        return NSE_BENCHMARK
    return us_benchmark or US_DEFAULT_BENCHMARK


def min_avg_dollar_volume_for_profile(profile):
    if profile == "NSE":
        return MIN_AVG_DOLLAR_VOLUME_50D_NSE
    return MIN_AVG_DOLLAR_VOLUME_50D_US


def fetch_daily_data(ticker, period=LOOKBACK_WINDOW):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        df = yf.download(ticker, period=period, progress=False, auto_adjust=False)
    if df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return normalize_index(df[["Open", "High", "Low", "Close", "Volume"]].dropna())


def fetch_hourly_data(ticker):
    try:
        df = yf.Ticker(ticker).history(period="5d", interval="1h", prepost=True, auto_adjust=False)
        if df.empty:
            return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df[["Open", "High", "Low", "Close", "Volume"]].dropna().copy()
    except Exception:
        return pd.DataFrame()


def fetch_live_quote(ticker):
    quote = {
        "market_state": "",
        "live_price": float("nan"),
        "regular_market_price": float("nan"),
        "pre_market_price": float("nan"),
        "post_market_price": float("nan"),
    }
    try:
        info = yf.Ticker(ticker).info
    except Exception:
        return quote

    quote["market_state"] = info.get("marketState") or ""
    quote["regular_market_price"] = info.get("regularMarketPrice") or info.get("currentPrice") or float("nan")
    quote["pre_market_price"] = info.get("preMarketPrice") or float("nan")
    quote["post_market_price"] = info.get("postMarketPrice") or float("nan")

    if quote["market_state"] == "PRE" and pd.notna(quote["pre_market_price"]):
        quote["live_price"] = quote["pre_market_price"]
    elif quote["market_state"] in ["POST", "POSTPOST"] and pd.notna(quote["post_market_price"]):
        quote["live_price"] = quote["post_market_price"]
    elif pd.notna(quote["regular_market_price"]):
        quote["live_price"] = quote["regular_market_price"]

    return quote


def safe_number(value):
    try:
        if value in ["", None] or pd.isna(value):
            return None
        number = float(value)
        if not math.isfinite(number):
            return None
        return number
    except (TypeError, ValueError):
        return None


def live_price_for_scoring(quote):
    market_state = str((quote or {}).get("market_state", "") or "").upper()
    if market_state not in LIVE_PRICE_SCORE_STATES:
        return None
    live_price = safe_number((quote or {}).get("live_price"))
    if live_price is None or live_price <= 0:
        return None
    return live_price


def apply_live_price_to_daily_data(df, quote):
    if df.empty:
        return df

    adjusted = df.copy()
    if "Regular_Session_Close" not in adjusted.columns:
        adjusted["Regular_Session_Close"] = adjusted["Close"]
    adjusted["Score_Price_Source"] = "REGULAR_CLOSE"
    adjusted["Score_Price_Change_Pct"] = 0.0

    live_price = live_price_for_scoring(quote)
    if live_price is None:
        return adjusted

    latest_idx = adjusted.index[-1]
    regular_close = safe_number(adjusted.at[latest_idx, "Regular_Session_Close"])
    if regular_close is None or regular_close <= 0:
        return adjusted

    adjusted.at[latest_idx, "Close"] = live_price
    adjusted.at[latest_idx, "High"] = max(float(adjusted.at[latest_idx, "High"]), live_price)
    adjusted.at[latest_idx, "Low"] = min(float(adjusted.at[latest_idx, "Low"]), live_price)
    adjusted.at[latest_idx, "Score_Price_Source"] = str((quote or {}).get("market_state") or "LIVE")
    adjusted.at[latest_idx, "Score_Price_Change_Pct"] = ((live_price / regular_close) - 1) * 100
    return adjusted


def format_pct(value):
    number = safe_number(value)
    if number is None:
        return "N/A"
    return f"{number:+.1f}%"


def extract_recommendation_counts(recommendations_summary):
    if recommendations_summary is None or getattr(recommendations_summary, "empty", True):
        return None

    try:
        row = recommendations_summary.iloc[0]
        return {
            "strong_buy": int(safe_number(row.get("strongBuy")) or 0),
            "buy": int(safe_number(row.get("buy")) or 0),
            "hold": int(safe_number(row.get("hold")) or 0),
            "sell": int(safe_number(row.get("sell")) or 0),
            "strong_sell": int(safe_number(row.get("strongSell")) or 0),
        }
    except Exception:
        return None


def extract_price_target_message(analyst_price_targets, close_price):
    if not analyst_price_targets:
        return "Target: N/A"

    try:
        mean_target = safe_number(
            analyst_price_targets.get("mean")
            or analyst_price_targets.get("meanTargetPrice")
        )
        current_price = (
            safe_number(analyst_price_targets.get("current"))
            or safe_number(analyst_price_targets.get("currentPrice"))
            or safe_number(close_price)
        )
        if mean_target is None or current_price is None or current_price == 0:
            return "Target: N/A"
        upside_pct = ((mean_target / current_price) - 1) * 100
        return f"Mean target {mean_target:.2f} ({format_pct(upside_pct)} vs current)"
    except Exception:
        return "Target: N/A"


def extract_upgrade_downgrade_message(upgrades_downgrades):
    if upgrades_downgrades is None or getattr(upgrades_downgrades, "empty", True):
        return "Recent changes: N/A"

    try:
        df = upgrades_downgrades.copy()
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index, errors="coerce")
        cutoff = pd.Timestamp.now(tz=df.index.tz) - pd.Timedelta(days=90)
        recent = df[df.index >= cutoff]
        if recent.empty:
            return "Recent changes: 0 upgrades, 0 downgrades"

        action_text = recent.astype(str).agg(" ".join, axis=1).str.lower()
        upgrades = int(action_text.str.contains("up", na=False).sum())
        downgrades = int(action_text.str.contains("down", na=False).sum())
        return f"Recent changes: {upgrades} upgrades, {downgrades} downgrades"
    except Exception:
        return "Recent changes: N/A"


def extract_eps_message(eps_revisions):
    if eps_revisions is None or getattr(eps_revisions, "empty", True):
        return "EPS revisions: N/A"

    try:
        df = eps_revisions.copy()
        text_parts = []
        numeric_columns = []
        for column in df.columns:
            numeric = pd.to_numeric(df[column], errors="coerce")
            if numeric.notna().any():
                numeric_columns.append((str(column), numeric))

        up_total = 0
        down_total = 0
        for column, numeric in numeric_columns:
            lower_name = column.lower()
            value = numeric.sum(skipna=True)
            if "up" in lower_name:
                up_total += int(value)
            elif "down" in lower_name:
                down_total += int(value)

        if up_total or down_total:
            text_parts.append(f"up {up_total}, down {down_total}")

        if not text_parts:
            flattened = " ".join(df.fillna("").astype(str).agg(" ".join, axis=1).tolist()).strip()
            if flattened:
                text_parts.append(flattened[:160])

        return "EPS revisions: " + ("; ".join(text_parts) if text_parts else "N/A")
    except Exception:
        return "EPS revisions: N/A"


def extract_event_message(earnings_dates):
    if earnings_dates is None or getattr(earnings_dates, "empty", True):
        return "Earnings/event: N/A"

    try:
        df = earnings_dates.copy()
        if isinstance(df.index, pd.DatetimeIndex):
            event_dates = pd.Series(df.index)
        elif "Earnings Date" in df.columns:
            event_dates = pd.to_datetime(df["Earnings Date"], errors="coerce")
        else:
            event_dates = pd.to_datetime(df.iloc[:, 0], errors="coerce")

        event_dates = pd.to_datetime(event_dates, errors="coerce").dropna()
        if event_dates.empty:
            return "Earnings/event: N/A"

        now = pd.Timestamp.now(tz=event_dates.dt.tz) if event_dates.dt.tz is not None else pd.Timestamp.now()
        future_dates = event_dates[event_dates >= now]
        if future_dates.empty:
            return "Earnings/event: no upcoming date from Yahoo"

        next_event = future_dates.min()
        days = int((next_event.normalize() - now.normalize()).days)
        return f"Earnings/event: next {next_event.date().isoformat()} ({days} days)"
    except Exception:
        return "Earnings/event: N/A"


def fetch_analyst_message(ticker, close_price=None):
    try:
        ticker_obj = yf.Ticker(ticker)
        recommendations_summary = getattr(ticker_obj, "recommendations_summary", None)
        analyst_price_targets = getattr(ticker_obj, "analyst_price_targets", None)
        upgrades_downgrades = getattr(ticker_obj, "upgrades_downgrades", None)

        counts = extract_recommendation_counts(recommendations_summary)
        if counts:
            ratings_message = (
                "Ratings: "
                f"StrongBuy {counts['strong_buy']}, "
                f"Buy {counts['buy']}, "
                f"Hold {counts['hold']}, "
                f"Sell {counts['sell']}, "
                f"StrongSell {counts['strong_sell']}"
            )
        else:
            ratings_message = "Ratings: N/A"

        target_message = extract_price_target_message(analyst_price_targets, close_price)
        changes_message = extract_upgrade_downgrade_message(upgrades_downgrades)
        return f"{ratings_message}; {target_message}; {changes_message}"
    except Exception as exc:
        return f"Analyst data unavailable: {exc}"


def fetch_eps_message(ticker):
    try:
        eps_revisions = getattr(yf.Ticker(ticker), "eps_revisions", None)
        return extract_eps_message(eps_revisions)
    except Exception as exc:
        return f"EPS revisions unavailable: {exc}"


def fetch_event_message(ticker):
    try:
        earnings_dates = getattr(yf.Ticker(ticker), "earnings_dates", None)
        return extract_event_message(earnings_dates)
    except Exception as exc:
        return f"Earnings/event unavailable: {exc}"


def fetch_external_messages(ticker, close_price=None):
    analyst_message = fetch_analyst_message(ticker, close_price)
    eps_message = fetch_eps_message(ticker)
    event_message = fetch_event_message(ticker)
    external_message = f"{analyst_message}; {eps_message}; {event_message}"
    return {
        "Analyst_Message": analyst_message,
        "EPS_Message": eps_message,
        "Event_Message": event_message,
        "External_Message": external_message,
    }


def ema(series, span):
    return series.ewm(span=span, adjust=False, min_periods=span).mean()


def true_range(df):
    prev_close = df["Close"].shift(1)
    return pd.concat(
        [
            df["High"] - df["Low"],
            (df["High"] - prev_close).abs(),
            (df["Low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)


def calculate_v5_indicators(
    df,
    benchmark_df,
    benchmark_ticker=BENCHMARK_TICKER,
    exchange_profile="US",
):
    df = df.copy()
    close = df["Close"]
    volume = df["Volume"]
    min_avg_dollar_volume = min_avg_dollar_volume_for_profile(exchange_profile)

    df["EMA_20"] = ema(close, 20)
    df["EMA_50"] = ema(close, 50)
    df["EMA_150"] = ema(close, 150)
    df["EMA_200"] = ema(close, 200)
    df["EMA_200_Slope_Pct_50D"] = df["EMA_200"].pct_change(50, fill_method=None) * 100

    df["Return_5D_Pct"] = close.pct_change(5, fill_method=None) * 100
    df["Return_10D_Pct"] = close.pct_change(10, fill_method=None) * 100
    df["Return_63D_Pct"] = close.pct_change(63, fill_method=None) * 100
    df["Return_126D_Pct"] = close.pct_change(126, fill_method=None) * 100
    df["Return_252D_Pct"] = close.pct_change(252, fill_method=None) * 100
    df["Extension_Risk"] = (df["Return_5D_Pct"] > CONFIRMED_ENTRY_MAX_5D_RETURN_PCT) | (df["Return_10D_Pct"] > CONFIRMED_ENTRY_MAX_10D_RETURN_PCT)

    df["High_20D"] = df["High"].rolling(20).max()
    df["High_55D"] = df["High"].rolling(55).max()
    df["High_100D"] = df["High"].rolling(100).max()
    df["High_252D"] = df["High"].rolling(252).max()
    df["Distance_From_20D_High_Pct"] = ((close / df["High_20D"]) - 1) * 100
    df["Distance_From_52W_High_Pct"] = ((df["High_252D"] - close) / df["High_252D"]) * 100
    df["Lower_High_Day"] = df["High"] < df["High"].shift(1)
    df["Lower_Low_Day"] = df["Low"] < df["Low"].shift(1)
    df["Close_Below_EMA20"] = close < df["EMA_20"]

    df["ATR_14"] = true_range(df).rolling(14).mean()
    df["ATR_Pct"] = (df["ATR_14"] / close) * 100
    df["Volume_Avg_20"] = volume.rolling(20).mean()
    df["Volume_Avg_50"] = volume.rolling(50).mean()
    df["Relative_Volume_20"] = volume / df["Volume_Avg_20"]
    df["Avg_Dollar_Volume_50D"] = (close * volume).rolling(50).mean()
    df["Min_Avg_Dollar_Volume_50D"] = min_avg_dollar_volume
    df["Liquidity_Status"] = "OK"
    df.loc[df["Avg_Dollar_Volume_50D"] < min_avg_dollar_volume, "Liquidity_Status"] = "LOW"
    daily_range = df["High"] - df["Low"]
    df["Close_Location_Pct"] = ((close - df["Low"]) / daily_range) * 100
    df.loc[daily_range == 0, "Close_Location_Pct"] = 50.0

    daily_change = close.pct_change(fill_method=None) * 100
    df["Daily_Change_Pct"] = daily_change
    df["Accumulation_Day"] = (daily_change >= 1.0) & (volume > df["Volume_Avg_50"])
    df["Distribution_Day"] = (daily_change <= -1.0) & (volume > df["Volume_Avg_50"])
    df["Accumulation_Days_50"] = df["Accumulation_Day"].rolling(50).sum()
    df["Distribution_Days_50"] = df["Distribution_Day"].rolling(50).sum()
    df["Net_Accumulation_50"] = df["Accumulation_Days_50"] - df["Distribution_Days_50"]
    df["Latest_Distribution_Day"] = df["Distribution_Day"]

    benchmark_close = benchmark_df["Close"].reindex(df.index).ffill()
    df["Exchange_Profile"] = exchange_profile
    df["Benchmark_Ticker"] = benchmark_ticker
    df["Benchmark_Return_126D_Pct"] = benchmark_close.pct_change(126, fill_method=None) * 100
    df["RS_126D_Excess_Pct"] = df["Return_126D_Pct"] - df["Benchmark_Return_126D_Pct"]
    df["RS_Ratio"] = close / benchmark_close
    df["RS_SMA_50"] = df["RS_Ratio"].rolling(50).mean()
    df["RS_SMA_200"] = df["RS_Ratio"].rolling(200).mean()
    df["RS_Slope_Pct_50D"] = df["RS_Ratio"].pct_change(50, fill_method=None) * 100

    weekly = df.resample("W-FRI").agg({"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}).dropna()
    weekly["Weekly_SMA_30"] = weekly["Close"].rolling(30).mean()
    weekly["Weekly_SMA_30_Slope_Pct_10W"] = weekly["Weekly_SMA_30"].pct_change(10, fill_method=None) * 100
    weekly_fields = weekly[["Close", "Weekly_SMA_30", "Weekly_SMA_30_Slope_Pct_10W"]].rename(columns={"Close": "Weekly_Close"})
    df = df.join(weekly_fields.reindex(df.index, method="ffill"))

    return df


def decision_blockers(row, scores, weekly_trend, timing):
    blockers = []
    score = scores.get("final", 0)

    if score < CONFIRMED_ENTRY_MIN_SCORE:
        blockers.append(f"score below {CONFIRMED_ENTRY_MIN_SCORE}")
    if weekly_trend != "Uptrend":
        blockers.append(f"weekly {str(weekly_trend).lower()}")
    if timing.get("status") != "Clean":
        blockers.append(f"timing {timing.get('status', '')}")
    if row.get("RS_126D_Excess_Pct", float("nan")) < CONFIRMED_ENTRY_MIN_RS_EXCESS_PCT:
        blockers.append(f"RS excess below {CONFIRMED_ENTRY_MIN_RS_EXCESS_PCT}%")
    if row.get("ATR_Pct", float("nan")) > CONFIRMED_ENTRY_MAX_ATR_PCT:
        blockers.append(f"ATR above {CONFIRMED_ENTRY_MAX_ATR_PCT}%")
    if row.get("Return_5D_Pct", float("nan")) > CONFIRMED_ENTRY_MAX_5D_RETURN_PCT:
        blockers.append(f"5D extension above {CONFIRMED_ENTRY_MAX_5D_RETURN_PCT}%")
    if row.get("Return_10D_Pct", float("nan")) > CONFIRMED_ENTRY_MAX_10D_RETURN_PCT:
        blockers.append(f"10D extension above {CONFIRMED_ENTRY_MAX_10D_RETURN_PCT}%")
    if row.get("Relative_Volume_20", float("nan")) < CONFIRMED_ENTRY_MIN_REL_VOLUME_20:
        blockers.append(f"relative volume below {CONFIRMED_ENTRY_MIN_REL_VOLUME_20}x")
    if row.get("Close_Location_Pct", float("nan")) < CONFIRMED_ENTRY_MIN_CLOSE_LOCATION_PCT:
        blockers.append(f"close location below {CONFIRMED_ENTRY_MIN_CLOSE_LOCATION_PCT}%")
    min_avg_dollar_volume = row.get("Min_Avg_Dollar_Volume_50D", float("nan"))
    avg_dollar_volume = row.get("Avg_Dollar_Volume_50D", float("nan"))
    if pd.notna(min_avg_dollar_volume) and pd.notna(avg_dollar_volume) and avg_dollar_volume < min_avg_dollar_volume:
        blockers.append(f"average dollar volume below {min_avg_dollar_volume:.0f}")

    return blockers


def resolve_final_decision(row, scores, weekly_trend, timing, long_term_status, reason):
    timing_status = timing.get("status", "")
    if timing_status in ["Rejected - Extended Hours Breakdown", "Failed - Distribution Risk"]:
        return "REJECT", FINAL_DECISION_RANK["REJECT"], reason or timing_status
    if long_term_status == "Avoid":
        return "REJECT", FINAL_DECISION_RANK["REJECT"], reason or "not qualified"
    if long_term_status in ["Extended / Exhaustion Risk"]:
        return "REJECT", FINAL_DECISION_RANK["REJECT"], reason or "extension risk"

    blockers = decision_blockers(row, scores, weekly_trend, timing)
    if long_term_status == "Momentum Candidate":
        if not blockers:
            return (
                "MOMENTUM_ACTIVE",
                FINAL_DECISION_RANK["MOMENTUM_ACTIVE"],
                "all confirmation gates passed",
            )
        return (
            "MOMENTUM_PRESENT_WAIT_CONFIRMATION",
            FINAL_DECISION_RANK["MOMENTUM_PRESENT_WAIT_CONFIRMATION"],
            " | ".join(blockers),
        )

    if long_term_status == "Watchlist Candidate":
        return (
            "MOMENTUM_PRESENT_WAIT_CONFIRMATION",
            FINAL_DECISION_RANK["MOMENTUM_PRESENT_WAIT_CONFIRMATION"],
            reason or "below confirmed entry threshold",
        )

    return "REJECT", FINAL_DECISION_RANK["REJECT"], reason or "not qualified"


def score_for_final_decision(score, final_decision):
    score = min(100.0, max(0.0, to_float(score)))
    cap = min(100.0, max(0.0, to_float(FINAL_DECISION_SCORE_CAP.get(final_decision, 0))))
    return min(score, cap)


def append_reason(reasons, reason):
    if reason and reason not in reasons:
        reasons.append(reason)


def evaluate_intraday_timing(daily_df, hourly_df, quote=None):
    result = {
        "status": "Clean",
        "market_state": "",
        "live_price": float("nan"),
        "regular_market_price": float("nan"),
        "pre_market_price": float("nan"),
        "post_market_price": float("nan"),
        "extended_hours_change_pct": float("nan"),
        "last_3h_return_pct": float("nan"),
        "bearish_1h_candles_last3": 0,
        "last_1h_bearish": False,
        "reason": "",
    }

    latest = daily_df.iloc[-1]
    reasons = []
    quote = quote or {}
    result["market_state"] = quote.get("market_state", "")
    result["live_price"] = quote.get("live_price", float("nan"))
    result["regular_market_price"] = quote.get("regular_market_price", float("nan"))
    result["pre_market_price"] = quote.get("pre_market_price", float("nan"))
    result["post_market_price"] = quote.get("post_market_price", float("nan"))

    regular_session_close = latest.get("Regular_Session_Close", latest["Close"])
    if result["market_state"] in ["PRE", "POST", "POSTPOST"] and pd.notna(result["live_price"]) and regular_session_close:
        result["extended_hours_change_pct"] = ((result["live_price"] / regular_session_close) - 1) * 100
        if result["extended_hours_change_pct"] <= EXTENDED_HOURS_REJECT_DROP_PCT:
            result["status"] = "Rejected - Extended Hours Breakdown"
            append_reason(reasons, f"extended-hours breakdown {result['extended_hours_change_pct']:.2f}%")
        elif result["extended_hours_change_pct"] <= EXTENDED_HOURS_WAIT_DROP_PCT:
            result["status"] = "Wait - Extended Hours Weakness"
            append_reason(reasons, f"extended-hours weakness {result['extended_hours_change_pct']:.2f}%")

    daily_pullback = (
        latest["Close_Below_EMA20"]
        and latest["Distance_From_20D_High_Pct"] <= DAILY_PULLBACK_DEEP_20D_HIGH_PCT
        and latest["Return_5D_Pct"] <= DAILY_PULLBACK_5D_RETURN_PCT
    )
    lower_high_low = bool(latest["Lower_High_Day"] and latest["Lower_Low_Day"])
    high_volume_pullback = bool(latest["Volume"] > latest["Volume_Avg_50"] and latest["Daily_Change_Pct"] <= HIGH_VOLUME_PULLBACK_MAX_GAIN_PCT)
    daily_drop = latest["Daily_Change_Pct"]
    daily_distribution = bool(pd.notna(daily_drop) and daily_drop <= DAILY_DISTRIBUTION_DROP_PCT)
    early_pullback = (
        latest["Close_Below_EMA20"]
        and latest["Distance_From_20D_High_Pct"] <= DAILY_PULLBACK_EARLY_20D_HIGH_PCT
        and latest["Return_5D_Pct"] <= DAILY_PULLBACK_5D_RETURN_PCT
    )
    daily_trend_break = latest["Close_Below_EMA20"] and daily_distribution and (lower_high_low or high_volume_pullback)

    if daily_pullback:
        append_reason(reasons, "below EMA20 with deep 20D-high pullback")
    if early_pullback and not daily_pullback:
        append_reason(reasons, "below EMA20 with early 20D-high pullback")
    if lower_high_low:
        append_reason(reasons, "lower high and lower low")
    if high_volume_pullback:
        append_reason(reasons, "pullback on above-average volume")
    if daily_distribution:
        append_reason(reasons, "daily distribution")
    if daily_trend_break:
        append_reason(reasons, "daily distribution below EMA20")

    if result["status"] == "Clean" and ((daily_pullback and (lower_high_low or high_volume_pullback)) or daily_trend_break):
        result["status"] = "Wait - Daily Pullback Risk"

    if hourly_df.empty or len(hourly_df) < 3:
        result["reason"] = " | ".join(reasons)
        return result

    last_3h = hourly_df.tail(3)
    first_open = last_3h["Open"].iloc[0]
    last_close = last_3h["Close"].iloc[-1]
    result["last_3h_return_pct"] = ((last_close / first_open) - 1) * 100 if first_open else float("nan")
    result["bearish_1h_candles_last3"] = int((last_3h["Close"] < last_3h["Open"]).sum())
    result["last_1h_bearish"] = bool(last_3h["Close"].iloc[-1] < last_3h["Open"].iloc[-1])

    if result["last_3h_return_pct"] <= INTRADAY_SELLING_3H_RETURN_PCT:
        append_reason(reasons, "last 3H selling")
    if result["bearish_1h_candles_last3"] >= BEARISH_HOURLY_CANDLES_CONFIRMATION:
        append_reason(reasons, "2+ bearish hourly candles")
    if result["last_1h_bearish"]:
        append_reason(reasons, "last 1H bearish")

    if result["status"] != "Rejected - Extended Hours Breakdown" and daily_distribution and result["bearish_1h_candles_last3"] >= BEARISH_HOURLY_CANDLES_CONFIRMATION:
        result["status"] = "Failed - Distribution Risk"
    elif result["status"] == "Clean" and result["last_3h_return_pct"] <= INTRADAY_SELLING_3H_RETURN_PCT and result["bearish_1h_candles_last3"] >= BEARISH_HOURLY_CANDLES_CONFIRMATION:
        result["status"] = "Wait - Intraday Selling"
    elif result["status"] == "Clean" and result["last_1h_bearish"]:
        result["status"] = "Wait - Last Hour Bearish"
    result["reason"] = " | ".join(reasons)
    return result


def classify_weekly_trend(row):
    if pd.isna(row["Weekly_SMA_30"]) or pd.isna(row["Weekly_SMA_30_Slope_Pct_10W"]):
        return "Unknown"
    if row["Weekly_Close"] > row["Weekly_SMA_30"] and row["Weekly_SMA_30_Slope_Pct_10W"] > 0:
        return "Uptrend"
    if row["Weekly_Close"] < row["Weekly_SMA_30"] and row["Weekly_SMA_30_Slope_Pct_10W"] < 0:
        return "Downtrend"
    if abs(row["Weekly_SMA_30_Slope_Pct_10W"]) <= 1:
        return "Flat"
    return "Mixed"


def score_v5(row):
    scores = {"trend": 0, "relative_strength": 0, "breakout": 0, "accumulation": 0, "volatility": 0, "weekly_trend": 0}

    if row["Close"] > row["EMA_50"] > row["EMA_150"] > row["EMA_200"]:
        scores["trend"] += 20
    elif row["Close"] > row["EMA_200"] and row["EMA_50"] > row["EMA_200"]:
        scores["trend"] += 12
    if row["EMA_200_Slope_Pct_50D"] > 2:
        scores["trend"] += 10
    elif row["EMA_200_Slope_Pct_50D"] > 0:
        scores["trend"] += 5

    if row["RS_126D_Excess_Pct"] > 20:
        scores["relative_strength"] += 12
    elif row["RS_126D_Excess_Pct"] > 5:
        scores["relative_strength"] += 8
    elif row["RS_126D_Excess_Pct"] > 0:
        scores["relative_strength"] += 4
    if row["RS_Ratio"] > row["RS_SMA_50"] > row["RS_SMA_200"] and row["RS_Slope_Pct_50D"] > 0:
        scores["relative_strength"] += 13

    if row["Close"] >= row["High_55D"] * 0.98:
        scores["breakout"] += 6
    if row["Close"] >= row["High_100D"] * 0.97:
        scores["breakout"] += 6
    if row["Distance_From_52W_High_Pct"] <= 10:
        scores["breakout"] += 8
    elif row["Distance_From_52W_High_Pct"] <= 20:
        scores["breakout"] += 4

    freshness = 0
    if pd.notna(row.get("Distance_From_20D_High_Pct", None)):
        if row["Distance_From_20D_High_Pct"] <= 2:
            freshness += 12
        elif row["Distance_From_20D_High_Pct"] <= 5:
            freshness += 8
        elif row["Distance_From_20D_High_Pct"] <= 10:
            freshness += 5
        elif row["Distance_From_20D_High_Pct"] <= 20:
            freshness += 2

        if pd.notna(row.get("Return_5D_Pct", None)) and row["Return_5D_Pct"] > 15 and row["Distance_From_20D_High_Pct"] > 10:
            freshness -= 4
        if pd.notna(row.get("Return_10D_Pct", None)) and row["Return_10D_Pct"] > 20 and row["Distance_From_20D_High_Pct"] > 15:
            freshness -= 5

    scores["freshness"] = max(-10, min(15, freshness))

    if row["Net_Accumulation_50"] >= 3:
        scores["accumulation"] += 10
    elif row["Net_Accumulation_50"] > 0:
        scores["accumulation"] += 6
    if row["Distribution_Days_50"] <= 5:
        scores["accumulation"] += 5
    elif row["Distribution_Days_50"] >= 10:
        scores["accumulation"] -= 5
    if row["Latest_Distribution_Day"]:
        scores["accumulation"] -= 8

    if row["ATR_Pct"] <= 4:
        scores["volatility"] += 10
    elif row["ATR_Pct"] <= 7:
        scores["volatility"] += 7
    elif row["ATR_Pct"] <= 10:
        scores["volatility"] += 3
    elif row["ATR_Pct"] > 15:
        scores["volatility"] -= 5

    weekly_trend = classify_weekly_trend(row)
    if weekly_trend == "Uptrend":
        scores["weekly_trend"] += 15
    elif weekly_trend == "Mixed":
        scores["weekly_trend"] += 5
    elif weekly_trend == "Downtrend":
        scores["weekly_trend"] -= 10

    scores["raw"] = min(100, max(0, sum(scores.values())))
    scores["final"] = scores["raw"]
    return scores, weekly_trend


def apply_commercial_readiness_score(row, scores, weekly_trend, timing):
    final_score = scores["final"]

    if row["Close"] <= row["EMA_200"]:
        final_score = min(final_score, 20)
    if weekly_trend == "Downtrend":
        final_score = min(final_score, 25)
    elif weekly_trend != "Uptrend":
        final_score = min(final_score, 45)
    if row["RS_126D_Excess_Pct"] <= 0:
        final_score = min(final_score, 35)
    if row["Distribution_Days_50"] >= 8:
        final_score = min(final_score, 40)
    if row["ATR_Pct"] > 15:
        final_score = min(final_score, 30)

    if timing["status"] == "Rejected - Extended Hours Breakdown":
        final_score = 0
    elif timing["status"] == "Failed - Distribution Risk":
        final_score = min(final_score, 25)
    elif timing["status"] != "Clean":
        final_score = min(final_score, 69)

    scores["final"] = min(100, max(0, final_score))
    return scores


def classify_signal(row, scores, weekly_trend, timing):
    reasons = []
    if row["Close"] <= row["EMA_200"]:
        reasons.append("below EMA200")
    if weekly_trend != "Uptrend":
        reasons.append(f"weekly {weekly_trend.lower()}")
    if row["RS_126D_Excess_Pct"] <= 0:
        reasons.append(f"not outperforming benchmark {row.get('Benchmark_Ticker', BENCHMARK_TICKER)}")
    if row["Distribution_Days_50"] >= 8:
        reasons.append("distribution cluster")
    if row["ATR_Pct"] > 15:
        reasons.append("excess volatility")

    raw_score = scores.get("raw", scores["final"])

    if reasons:
        long_term_status = "Avoid"
    elif raw_score >= 85 and timing["status"] == "Clean":
        long_term_status = "Momentum Candidate"
    elif raw_score >= MIN_MOMENTUM_SCORE:
        long_term_status = "Watchlist Candidate"
    elif row["Distance_From_52W_High_Pct"] <= 5 and row["ATR_Pct"] > 10:
        long_term_status = "Extended / Exhaustion Risk"
    else:
        long_term_status = "Avoid"

    return long_term_status, " | ".join(reasons) if reasons else timing["reason"]


def build_output_row(ticker, row, scores, weekly_trend, timing, long_term_status, reason):
    action_rank, action_status = resolve_action_status(long_term_status, timing["status"])
    final_decision, final_decision_rank, final_decision_reason = resolve_final_decision(
        row,
        scores,
        weekly_trend,
        timing,
        long_term_status,
        reason,
    )
    output = {
        "Ticker": ticker,
        "Final_Decision": final_decision,
        "Final_Decision_Rank": final_decision_rank,
        "Final_Decision_Reason": final_decision_reason,
        "Action_Rank": action_rank,
        "Action_Status": action_status,
        "Long_Term_Status": long_term_status,
        "Entry_Timing_Status": timing["status"],
        "Classification_Reason": reason,
        "Market_State": timing["market_state"],
        "Live_Price": timing["live_price"],
        "Regular_Market_Price": timing["regular_market_price"],
        "PreMarket_Price": timing["pre_market_price"],
        "PostMarket_Price": timing["post_market_price"],
        "Extended_Hours_Change_Pct": timing["extended_hours_change_pct"],
        "Score": score_for_final_decision(scores["final"], final_decision),
        "Trend_Score": scores["trend"],
        "Relative_Strength_Score": scores["relative_strength"],
        "Breakout_Score": scores["breakout"],
        "Freshness_Score": scores.get("freshness", 0),
        "Accumulation_Score": scores["accumulation"],
        "Volatility_Score": scores["volatility"],
        "Weekly_Trend_Score": scores["weekly_trend"],
        "Weekly_Trend": weekly_trend,
        "Last_3H_Return_Pct": timing["last_3h_return_pct"],
        "Bearish_1H_Candles_Last3": timing["bearish_1h_candles_last3"],
        "Last_1H_Bearish": timing["last_1h_bearish"],
    }
    for field in CSV_FIELDS:
        if field not in output and field in row:
            output[field] = row[field]
    return {field: clean_number(output.get(field, "")) for field in CSV_FIELDS}


def load_tickers(ticker_csv=TICKER_INPUT_CSV):
    if not os.path.exists(ticker_csv):
        return []
    tickers_df = pd.read_csv(ticker_csv)
    ticker_col = "Ticker" if "Ticker" in tickers_df.columns else "Symbol" if "Symbol" in tickers_df.columns else tickers_df.columns[0]
    return tickers_df[ticker_col].dropna().tolist()


def resolve_tickers(cli_tickers, ticker_csv, positional_tickers=None):
    tickers = parse_ticker_values([*(cli_tickers or []), *(positional_tickers or [])])
    if tickers:
        return tickers, "CLI ticker list"
    input_csv = Path(ticker_csv) if ticker_csv else TICKER_INPUT_CSV
    return load_tickers(input_csv), str(input_csv)


def run_scan(args, tickers, force_unique_output=False):
    benchmark_cache = {}
    quote_cache = {}
    rows = []
    total_processed = 0
    run_id = datetime.now().strftime("V8_%Y%m%d_%H%M%S_%f")
    execution_log_path = initialize_execution_log(getattr(args, "log_output", EXECUTION_LOG_CSV))

    print(f"Starting Scan (V8) | Filter: Top {args.count_x} rows with Score >= {args.score_y}...")
    print(f"Append-only execution log: {execution_log_path}")

    for ticker in tickers:
        print(f"Processing {ticker}...")
        time.sleep(API_DELAY_SECONDS)
        output = None
        try:
            df = fetch_daily_data(ticker, LOOKBACK_WINDOW)
            if df.empty:
                output = build_status_row(ticker, "Avoid", "No market data", "no market data - check symbol")
            elif len(df) < MIN_HISTORY_BARS:
                output = build_status_row(
                    ticker,
                    "Avoid",
                    "Insufficient history",
                    f"insufficient price history ({len(df)} bars; {MIN_HISTORY_BARS} required)",
                )
            else:
                quote = fetch_live_quote(ticker)
                df = apply_live_price_to_daily_data(df, quote)
                exchange_profile = exchange_profile_for_ticker(ticker, args.market)
                benchmark_ticker = benchmark_for_ticker(ticker, args.market, args.us_benchmark)
                if benchmark_ticker not in benchmark_cache:
                    benchmark_cache[benchmark_ticker] = fetch_daily_data(benchmark_ticker, LOOKBACK_WINDOW)
                if benchmark_ticker not in quote_cache:
                    quote_cache[benchmark_ticker] = fetch_live_quote(benchmark_ticker)
                benchmark_df = benchmark_cache[benchmark_ticker]
                if benchmark_df.empty:
                    output = build_status_row(
                        ticker,
                        "Avoid",
                        "No benchmark data",
                        f"no benchmark data - check {benchmark_ticker}",
                    )
                else:
                    benchmark_df = apply_live_price_to_daily_data(benchmark_df, quote_cache[benchmark_ticker])
                    calc_df = calculate_v5_indicators(
                        df,
                        benchmark_df,
                        benchmark_ticker=benchmark_ticker,
                        exchange_profile=exchange_profile,
                    )
                    timing = evaluate_intraday_timing(calc_df, fetch_hourly_data(ticker), quote)
                    row = calc_df.iloc[-1]
                    scores, weekly_trend = score_v5(row)
                    scores = apply_commercial_readiness_score(row, scores, weekly_trend, timing)
                    long_term_status, reason = classify_signal(row, scores, weekly_trend, timing)

                    output = build_output_row(ticker, row, scores, weekly_trend, timing, long_term_status, reason)

                    apply_beta_postprocessor(
                        output,
                        df,
                        benchmark_df,
                        benchmark_ticker,
                        active_threshold=CONFIRMED_ENTRY_MIN_SCORE,
                    )

                    if output["Final_Decision"] == "MOMENTUM_ACTIVE":
                        output.update(fetch_external_messages(ticker, output.get("Close")))

        except Exception as exc:
            output = build_status_row(ticker, "Avoid", f"Error: {exc}", str(exc))

        append_execution_log_row(output, run_id, execution_log_path)
        total_processed += 1

        if float(output.get("Score", 0)) >= args.score_y:
            rows.append(output)

    sorted_rows = sort_output_rows(rows)[:args.count_x]
    output_path, sorted_rows = write_summary_output(sorted_rows, args.output, force_unique=force_unique_output)
    print_cli_summary(sorted_rows, output_path, execution_log_path, total_processed)
    return output_path, sorted_rows


def run_live_feed(args, tickers):
    iteration = 0
    while True:
        iteration += 1
        print("\n" + "=" * 60)
        print(f"Live Feed Refresh {iteration} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        run_scan(args, tickers, force_unique_output=args.unique_output)

        if args.live_iterations and iteration >= args.live_iterations:
            break

        print(f"\nNext refresh in {args.refresh_seconds} seconds. Press Ctrl+C to stop.")
        time.sleep(args.refresh_seconds)


def main():
    parser = argparse.ArgumentParser(
        description="Momentum Detector V8",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    # Original Arguments
    parser.add_argument("positional_tickers", nargs="*", help="List of tickers to process.")
    parser.add_argument("--tickers", nargs="*", default=[], help="Alternative list of tickers.")
    parser.add_argument("--ticker-csv", default=TICKER_INPUT_CSV, help="CSV file for ticker list.")
    parser.add_argument("--market", choices=["auto", "us", "nse"], default="auto", help="Market exchange.")
    parser.add_argument("--us-benchmark", default=US_DEFAULT_BENCHMARK, help="Benchmark ticker.")
    parser.add_argument("--output", default=SUMMARY_OUTPUT_CSV, help="Final top-X summary CSV path.")
    parser.add_argument(
        "--log-output",
        default=EXECUTION_LOG_CSV,
        help="Append-only per-ticker execution log CSV path.",
    )

    # V8 CLI Enhancements
    parser.add_argument("--count-x", type=int, default=DEFAULT_COUNT_X,
                        help="Max number of top-scoring rows to return.")
    parser.add_argument("--score-y", type=float, default=DEFAULT_SCORE_Y,
                        help="Minimum 'Score' value required to be included.")
    parser.add_argument("--live", action="store_true",
                        help="Continuously refresh the scan as a live data feed.")
    parser.add_argument("--refresh-seconds", type=int, default=300,
                        help="Seconds between live feed refreshes.")
    parser.add_argument("--live-iterations", type=int, default=0,
                        help="Stop live mode after this many refreshes. Use 0 to run until Ctrl+C.")
    parser.add_argument("--unique-output", action="store_true",
                        help="Write timestamped output files instead of overwriting the selected output path.")

    args = parser.parse_args()
    if not 0 <= args.score_y <= 100:
        parser.error("--score-y must be between 0 and 100.")
    if args.count_x < 1:
        parser.error("--count-x must be at least 1.")
    explicit_output = args.output != parser.get_default("output")

    tickers, ticker_source = resolve_tickers(args.tickers, args.ticker_csv, args.positional_tickers)
    tickers = sorted([normalize_ticker(t, args.market) for t in tickers if str(t).strip()])

    if not tickers:
        print("No tickers supplied.")
        return

    if args.live:
        try:
            run_live_feed(args, tickers)
        except KeyboardInterrupt:
            print("\nLive feed stopped.")
        return

    run_scan(args, tickers, force_unique_output=args.unique_output or not explicit_output)

if __name__ == "__main__":
    main()
