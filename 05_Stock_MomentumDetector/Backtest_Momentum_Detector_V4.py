import argparse
import csv
import math
import os
import time

import pandas as pd
import yfinance as yf

import Momentum_Detector_V4 as engine

BASE_FOLDER = "D:/Tools/Stock_MomentumDetector"
TRADES_CSV = os.path.join(BASE_FOLDER, "V4_Backtest_Trades.csv")
SUMMARY_CSV = os.path.join(BASE_FOLDER, "V4_Backtest_Summary.csv")
SIGNALS_CSV = os.path.join(BASE_FOLDER, "V4_Backtest_Signal_Audit.csv")

DEFAULT_PERIOD = "8y"
DEFAULT_MAX_HOLDING_DAYS = 252
DEFAULT_COOLDOWN_DAYS = 20
API_DELAY_SECONDS = 1.0

TRADE_FIELDS = [
    "Ticker",
    "Signal_Date",
    "Entry_Date",
    "Exit_Date",
    "Exit_Reason",
    "Entry_Price",
    "Exit_Price",
    "Initial_Stop",
    "Final_Stop",
    "Shares",
    "Trade_Return_Pct",
    "Dollar_PnL",
    "Holding_Days",
    "Signal_Score",
    "Trend_Score",
    "Relative_Strength_Score",
    "High_Proximity_Score",
    "Volume_Score",
    "ADX_Score",
    "Risk_Quality_Score",
    "Signal_Close",
    "Signal_EMA_50",
    "Signal_EMA_200",
    "Signal_EMA_200_Slope_Pct_50D",
    "Signal_Return_126D_Pct",
    "Signal_Return_252D_Pct",
    "Signal_Distance_From_52W_High_Pct",
    "Signal_ATR_Pct",
]

SUMMARY_FIELDS = [
    "Ticker",
    "Trades",
    "Wins",
    "Losses",
    "Win_Rate_Pct",
    "Average_Return_Pct",
    "Median_Return_Pct",
    "Best_Return_Pct",
    "Worst_Return_Pct",
    "Total_Dollar_PnL",
    "Profit_Factor",
    "Average_Holding_Days",
    "Buy_Hold_Return_Pct",
]

SIGNAL_FIELDS = [
    "Ticker",
    "Signal_Date",
    "D_Minus_1_Close",
    "Signal_Close",
    "D_Plus_1_Close",
    "D_Plus_2_Close",
    "D_Minus_1_Lt_D",
    "D_Lt_D_Plus_1",
    "D_Lt_D_Plus_2",
    "D1_D2_Confirmation",
    "Next_Open",
    "Gate_Status",
    "Signal_Score",
    "Trend_Score",
    "Relative_Strength_Score",
    "High_Proximity_Score",
    "Volume_Score",
    "ADX_Score",
    "Risk_Quality_Score",
    "EMA_50",
    "EMA_150",
    "EMA_200",
    "EMA_200_Slope_Pct_50D",
    "Return_63D_Pct",
    "Return_126D_Pct",
    "Return_252D_Pct",
    "High_252D",
    "Distance_From_52W_High_Pct",
    "Volume_Avg_20",
    "Volume_Avg_50",
    "Volume_Ratio_20_50",
    "ADX",
    "ATR_Pct",
    "OBV",
    "OBV_EMA_50",
    "Forward_21D_Return_Pct",
    "Forward_63D_Return_Pct",
    "Forward_126D_Return_Pct",
    "Forward_252D_Return_Pct",
]


def clean_number(value):
    if value is None or pd.isna(value):
        return ""
    if isinstance(value, (int, float)) and not math.isfinite(value):
        return ""
    return value


def normalize_downloaded_data(df):
    if df.empty:
        return df
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df[["Open", "High", "Low", "Close", "Volume"]].dropna().copy()


def fetch_backtest_data(ticker, period):
    try:
        df = yf.download(ticker, period=period, progress=False, auto_adjust=False)
        return normalize_downloaded_data(df)
    except Exception as exc:
        raise RuntimeError(f"Backtest download failed for {ticker}: {exc}")


def calculate_signal_scores(row):
    scores = {
        "trend": engine.score_trend_structure(row),
        "relative_strength": engine.score_relative_strength(row),
        "high_proximity": engine.score_high_proximity(row),
        "volume": engine.score_volume_confirmation(row),
        "adx": engine.score_adx(row),
        "risk_quality": engine.score_risk_quality(row),
    }
    scores["final"] = sum(scores.values())
    return scores


def is_entry_signal(row):
    gates_passed, gate_status = engine.check_long_term_gates(row)
    scores = calculate_signal_scores(row)
    return gates_passed and scores["final"] >= engine.MIN_MOMENTUM_SCORE, gate_status, scores


def get_recommended_stop(row):
    return engine.calculate_stop_loss(row)[3]


def forward_return_from_next_open(df, signal_idx, holding_days):
    entry_idx = signal_idx + 1
    exit_idx = signal_idx + holding_days

    if entry_idx >= len(df) or exit_idx >= len(df):
        return float("nan")

    entry_price = df.iloc[entry_idx]["Open"]
    exit_price = df.iloc[exit_idx]["Close"]
    if pd.isna(entry_price) or pd.isna(exit_price) or entry_price == 0:
        return float("nan")

    return ((exit_price / entry_price) - 1) * 100


def build_signal_audit_row(ticker, signal_idx, df, gate_status, scores):
    row = df.iloc[signal_idx]
    next_open = df.iloc[signal_idx + 1]["Open"] if signal_idx + 1 < len(df) else float("nan")
    d_minus_1_close = df.iloc[signal_idx - 1]["Close"] if signal_idx - 1 >= 0 else float("nan")
    d_plus_1_close = df.iloc[signal_idx + 1]["Close"] if signal_idx + 1 < len(df) else float("nan")
    d_plus_2_close = df.iloc[signal_idx + 2]["Close"] if signal_idx + 2 < len(df) else float("nan")

    d_minus_1_lt_d = bool(pd.notna(d_minus_1_close) and d_minus_1_close < row["Close"])
    d_lt_d_plus_1 = bool(pd.notna(d_plus_1_close) and row["Close"] < d_plus_1_close)
    d_lt_d_plus_2 = bool(pd.notna(d_plus_2_close) and row["Close"] < d_plus_2_close)
    d1_d2_confirmation = d_minus_1_lt_d and d_lt_d_plus_1 and d_lt_d_plus_2

    return {
        "Ticker": ticker,
        "Signal_Date": df.index[signal_idx].date(),
        "D_Minus_1_Close": d_minus_1_close,
        "Signal_Close": row["Close"],
        "D_Plus_1_Close": d_plus_1_close,
        "D_Plus_2_Close": d_plus_2_close,
        "D_Minus_1_Lt_D": d_minus_1_lt_d,
        "D_Lt_D_Plus_1": d_lt_d_plus_1,
        "D_Lt_D_Plus_2": d_lt_d_plus_2,
        "D1_D2_Confirmation": d1_d2_confirmation,
        "Next_Open": next_open,
        "Gate_Status": gate_status,
        "Signal_Score": scores["final"],
        "Trend_Score": scores["trend"],
        "Relative_Strength_Score": scores["relative_strength"],
        "High_Proximity_Score": scores["high_proximity"],
        "Volume_Score": scores["volume"],
        "ADX_Score": scores["adx"],
        "Risk_Quality_Score": scores["risk_quality"],
        "EMA_50": row["EMA_50"],
        "EMA_150": row["EMA_150"],
        "EMA_200": row["EMA_200"],
        "EMA_200_Slope_Pct_50D": row["EMA_200_Slope_Pct_50D"],
        "Return_63D_Pct": row["Return_63D_Pct"],
        "Return_126D_Pct": row["Return_126D_Pct"],
        "Return_252D_Pct": row["Return_252D_Pct"],
        "High_252D": row["High_252D"],
        "Distance_From_52W_High_Pct": row["Distance_From_52W_High_Pct"],
        "Volume_Avg_20": row["Volume_Avg_20"],
        "Volume_Avg_50": row["Volume_Avg_50"],
        "Volume_Ratio_20_50": row["Volume_Ratio_20_50"],
        "ADX": row["ADX"],
        "ATR_Pct": row["ATR_Pct"],
        "OBV": row["OBV"],
        "OBV_EMA_50": row["OBV_EMA_50"],
        "Forward_21D_Return_Pct": forward_return_from_next_open(df, signal_idx, 21),
        "Forward_63D_Return_Pct": forward_return_from_next_open(df, signal_idx, 63),
        "Forward_126D_Return_Pct": forward_return_from_next_open(df, signal_idx, 126),
        "Forward_252D_Return_Pct": forward_return_from_next_open(df, signal_idx, 252),
    }


def collect_signal_audit_rows(ticker, df, signal_step_days):
    signal_rows = []
    i = engine.MIN_HISTORY_BARS

    while i < len(df) - 1:
        signal_passed, gate_status, scores = is_entry_signal(df.iloc[i])
        if signal_passed:
            signal_rows.append(build_signal_audit_row(ticker, i, df, gate_status, scores))
            i += signal_step_days
        else:
            i += 1

    return signal_rows


def build_trade(ticker, signal_idx, entry_idx, exit_idx, exit_reason, exit_price, df, scores, initial_stop, final_stop):
    signal_row = df.iloc[signal_idx]
    entry_row = df.iloc[entry_idx]

    entry_price = entry_row["Open"]
    risk_per_share = entry_price - initial_stop
    shares = math.floor(engine.DOLLAR_RISK_PER_TRADE / risk_per_share) if risk_per_share > 0 else 0
    trade_return_pct = ((exit_price / entry_price) - 1) * 100 if entry_price else float("nan")
    dollar_pnl = (exit_price - entry_price) * shares

    return {
        "Ticker": ticker,
        "Signal_Date": df.index[signal_idx].date(),
        "Entry_Date": df.index[entry_idx].date(),
        "Exit_Date": df.index[exit_idx].date(),
        "Exit_Reason": exit_reason,
        "Entry_Price": entry_price,
        "Exit_Price": exit_price,
        "Initial_Stop": initial_stop,
        "Final_Stop": final_stop,
        "Shares": shares,
        "Trade_Return_Pct": trade_return_pct,
        "Dollar_PnL": dollar_pnl,
        "Holding_Days": exit_idx - entry_idx + 1,
        "Signal_Score": scores["final"],
        "Trend_Score": scores["trend"],
        "Relative_Strength_Score": scores["relative_strength"],
        "High_Proximity_Score": scores["high_proximity"],
        "Volume_Score": scores["volume"],
        "ADX_Score": scores["adx"],
        "Risk_Quality_Score": scores["risk_quality"],
        "Signal_Close": signal_row["Close"],
        "Signal_EMA_50": signal_row["EMA_50"],
        "Signal_EMA_200": signal_row["EMA_200"],
        "Signal_EMA_200_Slope_Pct_50D": signal_row["EMA_200_Slope_Pct_50D"],
        "Signal_Return_126D_Pct": signal_row["Return_126D_Pct"],
        "Signal_Return_252D_Pct": signal_row["Return_252D_Pct"],
        "Signal_Distance_From_52W_High_Pct": signal_row["Distance_From_52W_High_Pct"],
        "Signal_ATR_Pct": signal_row["ATR_Pct"],
    }


def backtest_ticker(ticker, period, max_holding_days, cooldown_days, trailing_stop):
    raw_df = fetch_backtest_data(ticker, period)
    if raw_df.empty or len(raw_df) < engine.MIN_HISTORY_BARS + 2:
        return [], raw_df

    df = engine.calculate_technical_indicators(raw_df)
    trades = []
    i = engine.MIN_HISTORY_BARS

    while i < len(df) - 1:
        signal_row = df.iloc[i]
        signal_passed, _, scores = is_entry_signal(signal_row)

        if not signal_passed:
            i += 1
            continue

        initial_stop = get_recommended_stop(signal_row)
        entry_idx = i + 1
        entry_price = df.iloc[entry_idx]["Open"]

        if pd.isna(initial_stop) or initial_stop <= 0 or initial_stop >= entry_price:
            i += 1
            continue

        active_stop = initial_stop
        exit_idx = None
        exit_reason = None
        exit_price = None
        last_possible_exit = min(len(df) - 1, entry_idx + max_holding_days - 1)

        for j in range(entry_idx, last_possible_exit + 1):
            day = df.iloc[j]

            if day["Open"] <= active_stop:
                exit_idx = j
                exit_reason = "Gap Stop"
                exit_price = day["Open"]
                break

            if day["Low"] <= active_stop:
                exit_idx = j
                exit_reason = "Trailing Stop" if active_stop > initial_stop else "Initial Stop"
                exit_price = active_stop
                break

            if day["Close"] < day["EMA_200"] or day["EMA_50"] < day["EMA_200"]:
                exit_idx = j
                exit_reason = "Trend Break"
                exit_price = day["Close"]
                break

            if trailing_stop:
                new_stop = get_recommended_stop(day)
                if pd.notna(new_stop) and 0 < new_stop < day["Close"]:
                    active_stop = max(active_stop, new_stop)

        if exit_idx is None:
            exit_idx = last_possible_exit
            exit_reason = "Max Hold" if last_possible_exit < len(df) - 1 else "Open At End"
            exit_price = df.iloc[exit_idx]["Close"]

        trades.append(build_trade(ticker, i, entry_idx, exit_idx, exit_reason, exit_price, df, scores, initial_stop, active_stop))
        i = exit_idx + cooldown_days

    return trades, df


def summarize_ticker(ticker, trades, df):
    returns = [trade["Trade_Return_Pct"] for trade in trades if pd.notna(trade["Trade_Return_Pct"])]
    wins = [ret for ret in returns if ret > 0]
    losses = [ret for ret in returns if ret <= 0]
    total_pnl = sum(trade["Dollar_PnL"] for trade in trades if pd.notna(trade["Dollar_PnL"]))
    gross_profit = sum(trade["Dollar_PnL"] for trade in trades if trade["Dollar_PnL"] > 0)
    gross_loss = abs(sum(trade["Dollar_PnL"] for trade in trades if trade["Dollar_PnL"] < 0))
    buy_hold_return = ""

    if not df.empty and len(df) > engine.MIN_HISTORY_BARS:
        start_price = df["Close"].iloc[engine.MIN_HISTORY_BARS]
        end_price = df["Close"].iloc[-1]
        buy_hold_return = ((end_price / start_price) - 1) * 100 if start_price else ""

    return {
        "Ticker": ticker,
        "Trades": len(trades),
        "Wins": len(wins),
        "Losses": len(losses),
        "Win_Rate_Pct": (len(wins) / len(returns)) * 100 if returns else "",
        "Average_Return_Pct": sum(returns) / len(returns) if returns else "",
        "Median_Return_Pct": pd.Series(returns).median() if returns else "",
        "Best_Return_Pct": max(returns) if returns else "",
        "Worst_Return_Pct": min(returns) if returns else "",
        "Total_Dollar_PnL": total_pnl,
        "Profit_Factor": gross_profit / gross_loss if gross_loss > 0 else "",
        "Average_Holding_Days": sum(trade["Holding_Days"] for trade in trades) / len(trades) if trades else "",
        "Buy_Hold_Return_Pct": buy_hold_return,
    }


def write_csv(path, fieldnames, rows):
    with open(path, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: clean_number(row.get(field, "")) for field in fieldnames})


def print_summary(summary_rows, signal_only=False):
    print("============================================================")
    print("=== MOMENTUM DETECTOR V4 BACKTEST COMPLETE ===")
    print("============================================================")
    for row in summary_rows:
        if signal_only:
            print(f"{row['Ticker']:<8} | Trade simulation skipped; signal audit only")
            continue

        win_rate = row["Win_Rate_Pct"]
        avg_ret = row["Average_Return_Pct"]
        buy_hold = row["Buy_Hold_Return_Pct"]
        print(
            f"{row['Ticker']:<8} | Trades: {row['Trades']:<3} | "
            f"Win Rate: {win_rate:.1f}% | Avg Trade: {avg_ret:.2f}% | "
            f"PnL: {row['Total_Dollar_PnL']:.2f} | Buy/Hold: {buy_hold:.2f}%"
            if row["Trades"]
            else f"{row['Ticker']:<8} | Trades: 0 | No qualifying historical entries"
        )
    print("------------------------------------------------------------")
    print(f"Trades CSV  : {TRADES_CSV}")
    print(f"Summary CSV : {SUMMARY_CSV}")
    print(f"Signal CSV  : {SIGNALS_CSV}")
    print("============================================================")


def print_signal_audit_summary(signal_rows):
    if not signal_rows:
        print("No qualifying V4 signals were found for the audit window.")
        return

    df = pd.DataFrame(signal_rows)
    print("Signal Audit Summary:")
    for ticker, group in df.groupby("Ticker"):
        avg_score = group["Signal_Score"].mean()
        avg_63d = group["Forward_63D_Return_Pct"].dropna().mean()
        avg_126d = group["Forward_126D_Return_Pct"].dropna().mean()
        avg_252d = group["Forward_252D_Return_Pct"].dropna().mean()
        confirmation_rate = group["D1_D2_Confirmation"].mean() * 100
        print(
            f"{ticker:<8} | Signals: {len(group):<3} | Avg Score: {avg_score:.1f} | "
            f"D-1/D+1/D+2 Confirm: {confirmation_rate:.1f}% | "
            f"Avg Fwd 63D: {avg_63d:.2f}% | Avg Fwd 126D: {avg_126d:.2f}% | Avg Fwd 252D: {avg_252d:.2f}%"
        )


def main():
    parser = argparse.ArgumentParser(description="Backtest Momentum Detector V4 long-term signals.")
    parser.add_argument("--tickers", nargs="+", required=True, help="Space-separated ticker symbols.")
    parser.add_argument("--period", default=DEFAULT_PERIOD, help="Yahoo Finance period, e.g. 5y, 8y, 10y.")
    parser.add_argument("--max-holding-days", type=int, default=DEFAULT_MAX_HOLDING_DAYS)
    parser.add_argument("--cooldown-days", type=int, default=DEFAULT_COOLDOWN_DAYS)
    parser.add_argument("--signal-step-days", type=int, default=21, help="Minimum spacing between audited signals per ticker.")
    parser.add_argument("--signal-only", action="store_true", help="Only write the signal audit CSV; skip trade simulation.")
    parser.add_argument("--no-trailing-stop", action="store_true", help="Use only the initial signal stop.")
    args = parser.parse_args()

    all_trades = []
    all_signals = []
    summary_rows = []
    trailing_stop = not args.no_trailing_stop

    for raw_ticker in args.tickers:
        ticker = engine.normalize_ticker(raw_ticker)
        print(f"Backtesting {ticker} over {args.period}...")
        time.sleep(API_DELAY_SECONDS)

        try:
            if args.signal_only:
                raw_df = fetch_backtest_data(ticker, args.period)
                df = engine.calculate_technical_indicators(raw_df) if not raw_df.empty else raw_df
                trades = []
            else:
                trades, df = backtest_ticker(ticker, args.period, args.max_holding_days, args.cooldown_days, trailing_stop)
                all_trades.extend(trades)

            all_signals.extend(collect_signal_audit_rows(ticker, df, args.signal_step_days) if not df.empty else [])
            summary_rows.append(summarize_ticker(ticker, trades, df))
        except Exception as exc:
            print(f"Backtest failed for {ticker}: {exc}")
            summary_rows.append({"Ticker": ticker, "Trades": 0})

    write_csv(TRADES_CSV, TRADE_FIELDS, all_trades)
    write_csv(SUMMARY_CSV, SUMMARY_FIELDS, summary_rows)
    write_csv(SIGNALS_CSV, SIGNAL_FIELDS, all_signals)
    print_summary(summary_rows, signal_only=args.signal_only)
    print(f"Audited qualifying signals: {len(all_signals)}")
    print_signal_audit_summary(all_signals)


if __name__ == "__main__":
    main()
