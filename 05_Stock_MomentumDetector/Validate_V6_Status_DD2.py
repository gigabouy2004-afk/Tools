import argparse
import csv
import os
from pathlib import Path

import pandas as pd
import yfinance as yf

import Momentum_Detector_V6 as engine

BASE_FOLDER = "D:/Tools/Stock_MomentumDetector"
DEFAULT_OUTPUT = os.path.join(BASE_FOLDER, "V6_Status_DD2_Validation.csv")
DEFAULT_SUMMARY = os.path.join(BASE_FOLDER, "V6_Status_DD2_Validation_Summary.csv")

KNOWN_ACTION_STATUSES = {
    "Actionable Momentum Candidate",
    "Watchlist Candidate",
    "Downgraded - Wait",
    "Rejected - Distribution Risk",
    "Rejected - Extended Hours Breakdown",
    "Avoid",
}

KNOWN_FINAL_DECISIONS = {
    "MOMENTUM_ACTIVE",
    "MOMENTUM_PRESENT_WAIT_CONFIRMATION",
    "REJECT",
}

KNOWN_ENTRY_TIMING_STATUSES = {
    "Clean",
    "Wait - Daily Pullback Risk",
    "Failed - Distribution Risk",
    "Wait - Last Hour Bearish",
    "Wait - Intraday Selling",
    "Wait - Extended Hours Weakness",
    "Rejected - Extended Hours Breakdown",
    "Insufficient history",
}

KNOWN_REASON_PREFIXES = {
    "below EMA200",
    "weekly downtrend",
    "weekly flat",
    "weekly mixed",
    "weekly unknown",
    "not outperforming SPY",
    "not outperforming benchmark",
    "distribution cluster",
    "excess volatility",
    "below EMA20 with deep 20D-high pullback",
    "below EMA20 with early 20D-high pullback",
    "lower high and lower low",
    "pullback on above-average volume",
    "daily distribution",
    "daily distribution below EMA20",
    "last 3H selling",
    "2+ bearish hourly candles",
    "last 1H bearish",
    "extended-hours weakness",
    "extended-hours breakdown",
    "average dollar volume below",
    "no benchmark data - check",
}

FIELDS = [
    "Ticker",
    "D_Date",
    "D_Final_Decision",
    "D_Final_Decision_Reason",
    "D_Action_Status",
    "D_Score",
    "D_Entry_Timing_Status",
    "D_Classification_Reason",
    "D_Close",
    "D_Trend_Score",
    "D_Relative_Strength_Score",
    "D_Breakout_Score",
    "D_Accumulation_Score",
    "D_Volatility_Score",
    "D_Weekly_Trend_Score",
    "D_EMA_20",
    "D_EMA_50",
    "D_EMA_150",
    "D_EMA_200",
    "D_EMA_200_Slope_Pct_50D",
    "D_Close_Below_EMA20",
    "D_Weekly_Trend",
    "D_Weekly_Close",
    "D_Weekly_SMA_30",
    "D_Weekly_SMA_30_Slope_Pct_10W",
    "D_Benchmark_Ticker",
    "D_Benchmark_Return_126D_Pct",
    "D_Return_63D_Pct",
    "D_Return_126D_Pct",
    "D_Return_252D_Pct",
    "D_RS_126D_Excess_Pct",
    "D_RS_Ratio",
    "D_RS_SMA_50",
    "D_RS_SMA_200",
    "D_RS_Slope_Pct_50D",
    "D_Distribution_Days_50",
    "D_Accumulation_Days_50",
    "D_Net_Accumulation_50",
    "D_Latest_Distribution_Day",
    "D_ATR_Pct",
    "D_Relative_Volume_20",
    "D_Volume",
    "D_Volume_Avg_20",
    "D_Volume_Avg_50",
    "D_Avg_Dollar_Volume_50D",
    "D_Min_Avg_Dollar_Volume_50D",
    "D_Liquidity_Status",
    "D_Close_Location_Pct",
    "D_Return_5D_Pct",
    "D_Return_10D_Pct",
    "D_Distance_From_20D_High_Pct",
    "D_Distance_From_52W_High_Pct",
    "D_Lower_High_Day",
    "D_Lower_Low_Day",
    "D_Daily_Change_Pct",
    "D_Extension_Risk",
    "D_1H_Bars",
    "D_4H_Bars",
    "D_Intraday_Data_Status",
    "D1_Date",
    "D1_Open",
    "D1_Close",
    "D1_Final_Decision",
    "D1_Final_Decision_Reason",
    "D1_Action_Status",
    "D1_Score",
    "D1_1H_Bars",
    "D1_4H_Bars",
    "D1_Intraday_Data_Status",
    "D2_Date",
    "D2_Open",
    "D2_Close",
    "D2_Final_Decision",
    "D2_Final_Decision_Reason",
    "D2_Action_Status",
    "D2_Score",
    "D2_1H_Bars",
    "D2_4H_Bars",
    "D2_Intraday_Data_Status",
    "Continuation_By_D2",
    "Validation_Result",
    "Validation_Note",
    "Status_String_Check",
    "Reason_String_Check",
    "Daily_Replay_Limitation",
]

SUMMARY_FIELDS = ["Metric", "Value"]


def parse_tickers(path, limit):
    df = pd.read_csv(path)
    ticker_col = "Ticker" if "Ticker" in df.columns else "Symbol" if "Symbol" in df.columns else df.columns[0]
    tickers = [engine.normalize_ticker(t) for t in df[ticker_col].dropna().tolist()]
    tickers = sorted(dict.fromkeys(tickers))
    return tickers[:limit] if limit else tickers


def validate_reason_string(reason):
    if not reason:
        return "OK"
    unknown = []
    for part in str(reason).split(" | "):
        if not any(part == known or part.startswith(f"{known} ") for known in KNOWN_REASON_PREFIXES):
            unknown.append(part)
    return "OK" if not unknown else "UNKNOWN_REASON: " + "; ".join(unknown)


def daily_timing_from_slice(calc_df):
    return engine.evaluate_intraday_timing(calc_df, pd.DataFrame(), {})


def fetch_historical_intraday(ticker, session_date, interval):
    start = pd.Timestamp(session_date).date().isoformat()
    end = (pd.Timestamp(session_date) + pd.Timedelta(days=1)).date().isoformat()
    try:
        df = yf.Ticker(ticker).history(
            start=start,
            end=end,
            interval=interval,
            prepost=True,
            auto_adjust=False,
        )
    except Exception:
        return pd.DataFrame()
    if df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    fields = [field for field in ["Open", "High", "Low", "Close", "Volume"] if field in df.columns]
    return df[fields].dropna().copy()


def intraday_for_session(ticker, session_date, cache, enabled):
    key = (ticker, pd.Timestamp(session_date).date().isoformat())
    if key in cache:
        return cache[key]
    if not enabled:
        result = {
            "hourly": pd.DataFrame(),
            "bars_1h": 0,
            "bars_4h": 0,
            "status": "DISABLED",
        }
        cache[key] = result
        return result

    hourly = fetch_historical_intraday(ticker, session_date, "1h")
    four_hour = fetch_historical_intraday(ticker, session_date, "4h")
    status = "OK" if not hourly.empty else "INTRADAY_UNAVAILABLE"
    if not hourly.empty and four_hour.empty:
        status = "OK_1H_ONLY"
    result = {
        "hourly": hourly,
        "bars_1h": len(hourly),
        "bars_4h": len(four_hour),
        "status": status,
    }
    cache[key] = result
    return result


def replay_row(ticker, calc_df, idx, hourly_df=None):
    calc_slice = calc_df.iloc[: idx + 1]
    timing = engine.evaluate_intraday_timing(calc_slice, hourly_df if hourly_df is not None else pd.DataFrame(), {})
    latest = calc_df.iloc[idx]
    scores, weekly_trend = engine.score_v5(latest)
    scores = engine.apply_commercial_readiness_score(latest, scores, weekly_trend, timing)
    long_term_status, reason = engine.classify_signal(latest, scores, weekly_trend, timing)
    return engine.build_output_row(ticker, latest, scores, weekly_trend, timing, long_term_status, reason)


def validation_for_status(action_status, continuation):
    if action_status == "Actionable Momentum Candidate":
        return (
            "PASS" if continuation else "FLAG_REVIEW",
            "Actionable status requires D+1/D+2 continuation above D close.",
        )
    if action_status == "Watchlist Candidate":
        return (
            "OBSERVE_CONTINUED" if continuation else "PASS_WATCHLIST_NO_CONFIRMATION",
            "Watchlist is not a full action call; continuation is recorded but not required.",
        )
    if action_status == "Downgraded - Wait":
        return (
            "FLAG_REVIEW" if continuation else "PASS_WAIT",
            "Wait should usually delay action; immediate continuation flags possible over-strict timing.",
        )
    if action_status in {"Rejected - Distribution Risk", "Rejected - Extended Hours Breakdown"}:
        return (
            "FLAG_REVIEW" if continuation else "PASS_REJECTED",
            "Rejected status should not show clean immediate continuation without review.",
        )
    if action_status == "Avoid":
        return (
            "FLAG_REVIEW" if continuation else "PASS_AVOID",
            "Avoid means required conditions failed; immediate continuation flags the failed reason for review.",
        )
    return "FAIL_UNKNOWN_STATUS", "Action status is not listed in the validation contract."


def validation_for_final_decision(final_decision, continuation):
    if final_decision == "MOMENTUM_ACTIVE":
        return (
            "PASS" if continuation else "FLAG_REVIEW",
            "Active momentum requires D+1/D+2 continuation above D close.",
        )
    if final_decision == "MOMENTUM_PRESENT_WAIT_CONFIRMATION":
        return (
            "OBSERVE_CONTINUED" if continuation else "PASS_WAIT",
            "Momentum is present but not active; continuation is observed but not required.",
        )
    if final_decision == "REJECT":
        return (
            "FLAG_REVIEW" if continuation else "PASS_REJECT",
            "Rejected rows should not show clean immediate continuation without review.",
        )
    return "FAIL_UNKNOWN_FINAL_DECISION", "Final decision is not listed in the validation contract."


def build_validation_row(ticker, calc_df, d_idx, intraday_cache, use_historical_intraday):
    d_intraday = intraday_for_session(ticker, calc_df.index[d_idx], intraday_cache, use_historical_intraday)
    d1_intraday = intraday_for_session(ticker, calc_df.index[d_idx + 1], intraday_cache, use_historical_intraday)
    d2_intraday = intraday_for_session(ticker, calc_df.index[d_idx + 2], intraday_cache, use_historical_intraday)

    d = replay_row(ticker, calc_df, d_idx, d_intraday["hourly"])
    d1 = replay_row(ticker, calc_df, d_idx + 1, d1_intraday["hourly"])
    d2 = replay_row(ticker, calc_df, d_idx + 2, d2_intraday["hourly"])

    d_close = calc_df.iloc[d_idx]["Close"]
    d1_open = calc_df.iloc[d_idx + 1]["Open"]
    d2_open = calc_df.iloc[d_idx + 2]["Open"]
    d2_close = calc_df.iloc[d_idx + 2]["Close"]
    continuation = bool(d1_open > d_close or d2_open > d_close or d2_close > d_close)
    validation_result, validation_note = validation_for_final_decision(d["Final_Decision"], continuation)

    status_check = "OK"
    if d["Final_Decision"] not in KNOWN_FINAL_DECISIONS:
        status_check = f"UNKNOWN_FINAL_DECISION: {d['Final_Decision']}"
    elif d["Action_Status"] not in KNOWN_ACTION_STATUSES:
        status_check = f"UNKNOWN_ACTION_STATUS: {d['Action_Status']}"
    elif d["Entry_Timing_Status"] not in KNOWN_ENTRY_TIMING_STATUSES:
        status_check = f"UNKNOWN_ENTRY_TIMING_STATUS: {d['Entry_Timing_Status']}"

    validation_row = {
        "Ticker": ticker,
        "D_Date": calc_df.index[d_idx].date().isoformat(),
        "D_Final_Decision": d["Final_Decision"],
        "D_Final_Decision_Reason": d["Final_Decision_Reason"],
        "D_Action_Status": d["Action_Status"],
        "D_Score": d["Score"],
        "D_Entry_Timing_Status": d["Entry_Timing_Status"],
        "D_Classification_Reason": d["Classification_Reason"],
        "D_Close": d_close,
        "D_1H_Bars": d_intraday["bars_1h"],
        "D_4H_Bars": d_intraday["bars_4h"],
        "D_Intraday_Data_Status": d_intraday["status"],
        "D1_Date": calc_df.index[d_idx + 1].date().isoformat(),
        "D1_Open": d1_open,
        "D1_Close": calc_df.iloc[d_idx + 1]["Close"],
        "D1_Final_Decision": d1["Final_Decision"],
        "D1_Final_Decision_Reason": d1["Final_Decision_Reason"],
        "D1_Action_Status": d1["Action_Status"],
        "D1_Score": d1["Score"],
        "D1_1H_Bars": d1_intraday["bars_1h"],
        "D1_4H_Bars": d1_intraday["bars_4h"],
        "D1_Intraday_Data_Status": d1_intraday["status"],
        "D2_Date": calc_df.index[d_idx + 2].date().isoformat(),
        "D2_Open": d2_open,
        "D2_Close": d2_close,
        "D2_Final_Decision": d2["Final_Decision"],
        "D2_Final_Decision_Reason": d2["Final_Decision_Reason"],
        "D2_Action_Status": d2["Action_Status"],
        "D2_Score": d2["Score"],
        "D2_1H_Bars": d2_intraday["bars_1h"],
        "D2_4H_Bars": d2_intraday["bars_4h"],
        "D2_Intraday_Data_Status": d2_intraday["status"],
        "Continuation_By_D2": continuation,
        "Validation_Result": validation_result,
        "Validation_Note": validation_note,
        "Status_String_Check": status_check,
        "Reason_String_Check": validate_reason_string(d["Classification_Reason"]),
        "Daily_Replay_Limitation": "Historical extended-hours quote status is not replayable from daily bars. Historical 1H/4H candle availability is recorded per row.",
    }

    d_diagnostic_fields = {
        "D_Trend_Score": "Trend_Score",
        "D_Relative_Strength_Score": "Relative_Strength_Score",
        "D_Breakout_Score": "Breakout_Score",
        "D_Accumulation_Score": "Accumulation_Score",
        "D_Volatility_Score": "Volatility_Score",
        "D_Weekly_Trend_Score": "Weekly_Trend_Score",
        "D_EMA_20": "EMA_20",
        "D_EMA_50": "EMA_50",
        "D_EMA_150": "EMA_150",
        "D_EMA_200": "EMA_200",
        "D_EMA_200_Slope_Pct_50D": "EMA_200_Slope_Pct_50D",
        "D_Close_Below_EMA20": "Close_Below_EMA20",
        "D_Weekly_Trend": "Weekly_Trend",
        "D_Weekly_Close": "Weekly_Close",
        "D_Weekly_SMA_30": "Weekly_SMA_30",
        "D_Weekly_SMA_30_Slope_Pct_10W": "Weekly_SMA_30_Slope_Pct_10W",
        "D_Benchmark_Ticker": "Benchmark_Ticker",
        "D_Benchmark_Return_126D_Pct": "Benchmark_Return_126D_Pct",
        "D_Return_63D_Pct": "Return_63D_Pct",
        "D_Return_126D_Pct": "Return_126D_Pct",
        "D_Return_252D_Pct": "Return_252D_Pct",
        "D_RS_126D_Excess_Pct": "RS_126D_Excess_Pct",
        "D_RS_Ratio": "RS_Ratio",
        "D_RS_SMA_50": "RS_SMA_50",
        "D_RS_SMA_200": "RS_SMA_200",
        "D_RS_Slope_Pct_50D": "RS_Slope_Pct_50D",
        "D_Distribution_Days_50": "Distribution_Days_50",
        "D_Accumulation_Days_50": "Accumulation_Days_50",
        "D_Net_Accumulation_50": "Net_Accumulation_50",
        "D_Latest_Distribution_Day": "Latest_Distribution_Day",
        "D_ATR_Pct": "ATR_Pct",
        "D_Relative_Volume_20": "Relative_Volume_20",
        "D_Volume": "Volume",
        "D_Volume_Avg_20": "Volume_Avg_20",
        "D_Volume_Avg_50": "Volume_Avg_50",
        "D_Avg_Dollar_Volume_50D": "Avg_Dollar_Volume_50D",
        "D_Min_Avg_Dollar_Volume_50D": "Min_Avg_Dollar_Volume_50D",
        "D_Liquidity_Status": "Liquidity_Status",
        "D_Close_Location_Pct": "Close_Location_Pct",
        "D_Return_5D_Pct": "Return_5D_Pct",
        "D_Return_10D_Pct": "Return_10D_Pct",
        "D_Distance_From_20D_High_Pct": "Distance_From_20D_High_Pct",
        "D_Distance_From_52W_High_Pct": "Distance_From_52W_High_Pct",
        "D_Lower_High_Day": "Lower_High_Day",
        "D_Lower_Low_Day": "Lower_Low_Day",
        "D_Daily_Change_Pct": "Daily_Change_Pct",
        "D_Extension_Risk": "Extension_Risk",
    }
    for output_field, source_field in d_diagnostic_fields.items():
        validation_row[output_field] = d.get(source_field, "")

    return validation_row


def write_csv(path, fields, rows):
    with open(path, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: engine.clean_number(row.get(field, "")) for field in fields})


def summarize(rows, skipped):
    summary = [
        {"Metric": "Rows Validated", "Value": len(rows)},
        {"Metric": "Rows Skipped", "Value": skipped},
    ]
    df = pd.DataFrame(rows)
    if not df.empty:
        for status, count in df["D_Action_Status"].value_counts().sort_index().items():
            summary.append({"Metric": f"D_Action_Status={status}", "Value": int(count)})
        for status, count in df["D_Final_Decision"].value_counts().sort_index().items():
            summary.append({"Metric": f"D_Final_Decision={status}", "Value": int(count)})
        for result, count in df["Validation_Result"].value_counts().sort_index().items():
            summary.append({"Metric": f"Validation_Result={result}", "Value": int(count)})
        for check, count in df["Status_String_Check"].value_counts().sort_index().items():
            summary.append({"Metric": f"Status_String_Check={check}", "Value": int(count)})
        for check, count in df["Reason_String_Check"].value_counts().sort_index().items():
            summary.append({"Metric": f"Reason_String_Check={check}", "Value": int(count)})
    return summary


def main():
    parser = argparse.ArgumentParser(description="Validate V6 D/D+1/D+2 status behavior.")
    parser.add_argument("--ticker-csv", required=True)
    parser.add_argument("--date", default=None, help="Requested D date. Non-trading dates resolve to prior trading session.")
    parser.add_argument("--start-date", default=None, help="Start date for a trading-date validation range.")
    parser.add_argument("--end-date", default=None, help="End date for a trading-date validation range.")
    parser.add_argument("--period", default="2y")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY)
    parser.add_argument("--no-historical-intraday", action="store_true", help="Disable historical 1H/4H D-session fetches.")
    args = parser.parse_args()

    if not args.date and not (args.start_date and args.end_date):
        parser.error("Supply either --date or both --start-date and --end-date.")
    target_date = pd.Timestamp(args.date) if args.date else None
    start_date = pd.Timestamp(args.start_date) if args.start_date else None
    end_date = pd.Timestamp(args.end_date) if args.end_date else None
    tickers = parse_tickers(Path(args.ticker_csv), args.limit)
    benchmark_cache = {}
    rows = []
    skipped = 0
    intraday_cache = {}
    use_historical_intraday = not args.no_historical_intraday

    for ticker in tickers:
        print(f"Validating {ticker}...")
        try:
            df = engine.fetch_daily_data(ticker, args.period)
            if df.empty:
                skipped += 1
                continue
            benchmark_ticker = engine.benchmark_for_ticker(ticker)
            if benchmark_ticker not in benchmark_cache:
                benchmark_cache[benchmark_ticker] = engine.fetch_daily_data(benchmark_ticker, args.period)
            benchmark_df = benchmark_cache[benchmark_ticker]
            if benchmark_df.empty:
                skipped += 1
                continue
            calc_df = engine.calculate_v5_indicators(
                df,
                benchmark_df,
                benchmark_ticker=benchmark_ticker,
                exchange_profile=engine.exchange_profile_for_ticker(ticker),
            )
            if target_date is not None:
                eligible_positions = [i for i, date in enumerate(calc_df.index) if date <= target_date and i + 2 < len(calc_df)]
            else:
                eligible_positions = [
                    i
                    for i, date in enumerate(calc_df.index)
                    if start_date <= date <= end_date and i + 2 < len(calc_df)
                ]
            if not eligible_positions:
                skipped += 1
                continue
            if target_date is not None:
                eligible_positions = [eligible_positions[-1]]
            added = 0
            for d_idx in eligible_positions:
                if d_idx < engine.MIN_HISTORY_BARS:
                    continue
                rows.append(build_validation_row(ticker, calc_df, d_idx, intraday_cache, use_historical_intraday))
                added += 1
            if not added:
                skipped += 1
        except Exception as exc:
            skipped += 1
            print(f"Skipped {ticker}: {exc}")

    rows = sorted(rows, key=lambda row: (-engine.to_float(row["D_Score"]), str(row["Ticker"])))
    write_csv(args.output, FIELDS, rows)
    write_csv(args.summary_output, SUMMARY_FIELDS, summarize(rows, skipped))
    print(f"Rows validated: {len(rows)}")
    print(f"Rows skipped  : {skipped}")
    print(f"Output        : {args.output}")
    print(f"Summary       : {args.summary_output}")


if __name__ == "__main__":
    main()
