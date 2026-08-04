import argparse
import csv
import os
import time

import pandas as pd

import Momentum_Detector_V5 as engine

BASE_FOLDER = "D:/Tools/Stock_MomentumDetector"
SIGNALS_CSV = os.path.join(BASE_FOLDER, "V5_Backtest_Signal_Audit.csv")
SUMMARY_CSV = os.path.join(BASE_FOLDER, "V5_Backtest_Summary.csv")
DEFAULT_PERIOD = "8y"
DEFAULT_SIGNAL_STEP_DAYS = 21

SIGNAL_FIELDS = [
    "Ticker", "Signal_Date", "Long_Term_Status", "Score", "Weekly_Trend",
    "Signal_Close", "Next_Open", "D_Minus_1_Close", "D_Plus_1_Close", "D_Plus_2_Close",
    "D_Minus_1_Lt_D", "D_Lt_D_Plus_1", "D_Lt_D_Plus_2", "D1_D2_Confirmation",
    "Trend_Score", "Relative_Strength_Score", "Breakout_Score", "Accumulation_Score",
    "Volatility_Score", "Weekly_Trend_Score", "RS_126D_Excess_Pct", "RS_Slope_Pct_50D",
    "Distance_From_52W_High_Pct", "Net_Accumulation_50", "Distribution_Days_50",
    "ATR_Pct", "Forward_21D_Return_Pct", "Forward_63D_Return_Pct",
    "Forward_126D_Return_Pct", "Forward_252D_Return_Pct",
]

SUMMARY_FIELDS = [
    "Ticker", "Signals", "Momentum_Candidates", "Watchlist_Candidates", "Avg_Score",
    "D1_D2_Confirm_Rate_Pct", "Avg_Fwd_21D_Return_Pct", "Avg_Fwd_63D_Return_Pct",
    "Avg_Fwd_126D_Return_Pct", "Avg_Fwd_252D_Return_Pct",
]


def clean_number(value):
    if value is None or pd.isna(value):
        return ""
    return value


def forward_return(df, signal_idx, holding_days):
    entry_idx = signal_idx + 1
    exit_idx = signal_idx + holding_days
    if entry_idx >= len(df) or exit_idx >= len(df):
        return float("nan")
    entry = df.iloc[entry_idx]["Open"]
    exit_price = df.iloc[exit_idx]["Close"]
    return ((exit_price / entry) - 1) * 100 if entry else float("nan")


def build_signal_row(ticker, df, signal_idx, scores, weekly_trend, status):
    row = df.iloc[signal_idx]
    d_minus_1 = df.iloc[signal_idx - 1]["Close"] if signal_idx > 0 else float("nan")
    d_plus_1 = df.iloc[signal_idx + 1]["Close"] if signal_idx + 1 < len(df) else float("nan")
    d_plus_2 = df.iloc[signal_idx + 2]["Close"] if signal_idx + 2 < len(df) else float("nan")
    d_minus_1_lt_d = bool(pd.notna(d_minus_1) and d_minus_1 < row["Close"])
    d_lt_d_plus_1 = bool(pd.notna(d_plus_1) and row["Close"] < d_plus_1)
    d_lt_d_plus_2 = bool(pd.notna(d_plus_2) and row["Close"] < d_plus_2)

    return {
        "Ticker": ticker,
        "Signal_Date": df.index[signal_idx].date(),
        "Long_Term_Status": status,
        "Score": scores["final"],
        "Weekly_Trend": weekly_trend,
        "Signal_Close": row["Close"],
        "Next_Open": df.iloc[signal_idx + 1]["Open"] if signal_idx + 1 < len(df) else float("nan"),
        "D_Minus_1_Close": d_minus_1,
        "D_Plus_1_Close": d_plus_1,
        "D_Plus_2_Close": d_plus_2,
        "D_Minus_1_Lt_D": d_minus_1_lt_d,
        "D_Lt_D_Plus_1": d_lt_d_plus_1,
        "D_Lt_D_Plus_2": d_lt_d_plus_2,
        "D1_D2_Confirmation": d_minus_1_lt_d and d_lt_d_plus_1 and d_lt_d_plus_2,
        "Trend_Score": scores["trend"],
        "Relative_Strength_Score": scores["relative_strength"],
        "Breakout_Score": scores["breakout"],
        "Accumulation_Score": scores["accumulation"],
        "Volatility_Score": scores["volatility"],
        "Weekly_Trend_Score": scores["weekly_trend"],
        "RS_126D_Excess_Pct": row["RS_126D_Excess_Pct"],
        "RS_Slope_Pct_50D": row["RS_Slope_Pct_50D"],
        "Distance_From_52W_High_Pct": row["Distance_From_52W_High_Pct"],
        "Net_Accumulation_50": row["Net_Accumulation_50"],
        "Distribution_Days_50": row["Distribution_Days_50"],
        "ATR_Pct": row["ATR_Pct"],
        "Forward_21D_Return_Pct": forward_return(df, signal_idx, 21),
        "Forward_63D_Return_Pct": forward_return(df, signal_idx, 63),
        "Forward_126D_Return_Pct": forward_return(df, signal_idx, 126),
        "Forward_252D_Return_Pct": forward_return(df, signal_idx, 252),
    }


def audit_ticker(ticker, period, signal_step_days, benchmark_df):
    df = engine.fetch_daily_data(ticker, period)
    if df.empty or len(df) < engine.MIN_HISTORY_BARS:
        return []
    calc_df = engine.calculate_v5_indicators(df, benchmark_df)
    signals = []
    i = engine.MIN_HISTORY_BARS
    while i < len(calc_df) - 2:
        row = calc_df.iloc[i]
        timing = {"status": "Clean", "reason": "", "last_3h_return_pct": float("nan"), "bearish_1h_candles_last3": 0, "last_1h_bearish": False}
        scores, weekly_trend = engine.score_v5(row)
        scores = engine.apply_commercial_readiness_score(row, scores, weekly_trend, timing)
        status, _ = engine.classify_signal(row, scores, weekly_trend, timing)
        if status in ["Momentum Candidate", "Watchlist Candidate"]:
            signals.append(build_signal_row(ticker, calc_df, i, scores, weekly_trend, status))
            i += signal_step_days
        else:
            i += 1
    return signals


def summarize(ticker, rows):
    df = pd.DataFrame(rows)
    if df.empty:
        return {"Ticker": ticker, "Signals": 0}
    return {
        "Ticker": ticker,
        "Signals": len(df),
        "Momentum_Candidates": int((df["Long_Term_Status"] == "Momentum Candidate").sum()),
        "Watchlist_Candidates": int((df["Long_Term_Status"] == "Watchlist Candidate").sum()),
        "Avg_Score": df["Score"].mean(),
        "D1_D2_Confirm_Rate_Pct": df["D1_D2_Confirmation"].mean() * 100,
        "Avg_Fwd_21D_Return_Pct": df["Forward_21D_Return_Pct"].dropna().mean(),
        "Avg_Fwd_63D_Return_Pct": df["Forward_63D_Return_Pct"].dropna().mean(),
        "Avg_Fwd_126D_Return_Pct": df["Forward_126D_Return_Pct"].dropna().mean(),
        "Avg_Fwd_252D_Return_Pct": df["Forward_252D_Return_Pct"].dropna().mean(),
    }


def write_csv(path, fields, rows):
    with open(path, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: clean_number(row.get(field, "")) for field in fields})


def main():
    parser = argparse.ArgumentParser(description="Backtest Momentum Detector V5 signal quality.")
    parser.add_argument("--tickers", nargs="+", required=True)
    parser.add_argument("--period", default=DEFAULT_PERIOD)
    parser.add_argument("--signal-step-days", type=int, default=DEFAULT_SIGNAL_STEP_DAYS)
    args = parser.parse_args()

    benchmark_df = engine.fetch_daily_data(engine.BENCHMARK_TICKER, args.period)
    all_rows = []
    summaries = []

    for raw_ticker in args.tickers:
        ticker = engine.normalize_ticker(raw_ticker)
        print(f"Auditing {ticker}...")
        time.sleep(engine.API_DELAY_SECONDS)
        rows = audit_ticker(ticker, args.period, args.signal_step_days, benchmark_df)
        all_rows.extend(rows)
        summaries.append(summarize(ticker, rows))

    write_csv(SIGNALS_CSV, SIGNAL_FIELDS, all_rows)
    write_csv(SUMMARY_CSV, SUMMARY_FIELDS, summaries)

    print("============================================================")
    print("=== MOMENTUM DETECTOR V5 BACKTEST COMPLETE ===")
    print("============================================================")
    for row in summaries:
        if not row.get("Signals"):
            print(f"{row['Ticker']:<8} | Signals: 0")
            continue
        print(
            f"{row['Ticker']:<8} | Signals: {row['Signals']:<3} | Avg Score: {row['Avg_Score']:.1f} | "
            f"Confirm: {row['D1_D2_Confirm_Rate_Pct']:.1f}% | "
            f"Fwd63: {row['Avg_Fwd_63D_Return_Pct']:.2f}% | "
            f"Fwd126: {row['Avg_Fwd_126D_Return_Pct']:.2f}% | "
            f"Fwd252: {row['Avg_Fwd_252D_Return_Pct']:.2f}%"
        )
    print(f"Signals CSV : {SIGNALS_CSV}")
    print(f"Summary CSV : {SUMMARY_CSV}")


if __name__ == "__main__":
    main()
