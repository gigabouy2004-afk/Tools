import argparse
import csv
import math
import os
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import ta
import yfinance as yf

# ==========================================
# MOMENTUM DETECTOR V4 - LONG-TERM ENGINE
# ==========================================
BASE_FOLDER = "D:/Tools/Stock_MomentumDetector"

if not os.path.exists(BASE_FOLDER):
    os.makedirs(BASE_FOLDER)

TICKER_INPUT_CSV = Path("D:/Tools/StockCodeMaster/02_Stock/24-06-US_Common_Stocks_Master_Library-Industry_Semiconductor.csv")
EXECUTION_LOG_CSV = os.path.join(BASE_FOLDER, "V4_LongTerm_Momentum_Execution_Dump.csv")
POST_PROCESS_EXCEL = "OFF"
EXCEL_OUTPUT_NAME = os.path.join(BASE_FOLDER, "V4_LongTerm_Momentum_Analyzed_Output.xlsx")

API_DELAY_SECONDS = 1.0
LOOKBACK_WINDOW = "3y"
MIN_HISTORY_BARS = 260

DOLLAR_RISK_PER_TRADE = 100.0
MIN_MOMENTUM_SCORE = 65

ADX_MIN_THRESHOLD = 18
MAX_ACCEPTABLE_ATR_PERCENT = 15.0
INTRADAY_DISTRIBUTION_CHECK = "ON"
INTRADAY_DISTRIBUTION_VETO = "ON"
DAILY_DROP_RISK_PCT = -3.0
LAST_3H_DROP_RISK_PCT = -1.0
INTRADAY_RISK_PENALTY = 25

CSV_FIELDS = [
    "Ticker",
    "Status",
    "Gate_Status",
    "Close",
    "EMA_50",
    "EMA_150",
    "EMA_200",
    "EMA_200_Slope_Pct_50D",
    "Return_63D_Pct",
    "Return_126D_Pct",
    "Return_252D_Pct",
    "High_252D",
    "Distance_From_52W_High_Pct",
    "Low_50D",
    "Volume",
    "Volume_Avg_20",
    "Volume_Avg_50",
    "Volume_Ratio_20_50",
    "ADX",
    "ATR",
    "ATR_Pct",
    "OBV",
    "OBV_EMA_50",
    "Trend_Score",
    "Relative_Strength_Score",
    "High_Proximity_Score",
    "Volume_Score",
    "ADX_Score",
    "Risk_Quality_Score",
    "Raw_Mo_Score",
    "Intraday_Risk_Flag",
    "Intraday_Risk_Reason",
    "Daily_Change_Pct",
    "Last_3H_Return_Pct",
    "Bearish_1H_Candles_Last3",
    "Last_1H_Bearish",
    "Intraday_Risk_Penalty",
    "Final_Mo_Score",
    "Stop_ATR_3x",
    "Stop_50D_Low",
    "Stop_EMA50_Buffer",
    "Recommended_Stop",
    "Stop_Distance_Pct",
    "Risk_Per_Share",
    "Position_Size",
]


def clean_number(value):
    if value is None or pd.isna(value):
        return ""
    if isinstance(value, (int, float)) and not math.isfinite(value):
        return ""
    return value


def fetch_historical_daily_data(formatted_ticker):
    """Fetch enough daily history for long-term trend and 52-week calculations."""
    try:
        hist_df = yf.download(formatted_ticker, period=LOOKBACK_WINDOW, progress=False, auto_adjust=False)

        if hist_df.empty or len(hist_df) < MIN_HISTORY_BARS:
            return pd.DataFrame()

        if isinstance(hist_df.columns, pd.MultiIndex):
            hist_df.columns = hist_df.columns.get_level_values(0)

        return hist_df[["Open", "High", "Low", "Close", "Volume"]].copy()

    except Exception as e:
        raise RuntimeError(f"API_Daily_Fetch_Error: {str(e)}")


def fetch_live_intraday_override(formatted_ticker):
    """Fetch latest quote data available from yfinance."""
    try:
        ticker_obj = yf.Ticker(formatted_ticker)
        return ticker_obj.history(period="1d", auto_adjust=False)
    except Exception as e:
        raise RuntimeError(f"API_Intraday_Fetch_Error: {str(e)}")


def fetch_hourly_intraday_data(formatted_ticker):
    """Fetch recent 1-hour candles for distribution-risk validation."""
    if INTRADAY_DISTRIBUTION_CHECK != "ON":
        return pd.DataFrame()

    try:
        hourly_df = yf.Ticker(formatted_ticker).history(period="5d", interval="1h", auto_adjust=False)
        if hourly_df.empty:
            return pd.DataFrame()
        if isinstance(hourly_df.columns, pd.MultiIndex):
            hourly_df.columns = hourly_df.columns.get_level_values(0)
        return hourly_df[["Open", "High", "Low", "Close", "Volume"]].dropna().copy()
    except Exception:
        return pd.DataFrame()


def apply_live_price_override(df, live_df):
    """Apply the latest available OHLCV values to the most recent daily row."""
    if live_df.empty:
        return df

    last_idx = df.index[-1]
    live_row = live_df.iloc[-1]

    df.loc[last_idx, "Close"] = live_row["Close"]
    df.loc[last_idx, "High"] = max(df.loc[last_idx, "High"], live_row["High"])
    df.loc[last_idx, "Low"] = min(df.loc[last_idx, "Low"], live_row["Low"])
    df.loc[last_idx, "Volume"] = live_row["Volume"]

    return df


def percent_change(current, previous):
    if pd.isna(current) or pd.isna(previous) or previous == 0:
        return float("nan")
    return ((current / previous) - 1) * 100


def calculate_technical_indicators(df):
    """Calculate long-term momentum, trend, volume, and risk fields."""
    close = pd.to_numeric(df["Close"], errors="coerce")
    high = pd.to_numeric(df["High"], errors="coerce")
    low = pd.to_numeric(df["Low"], errors="coerce")
    volume = pd.to_numeric(df["Volume"], errors="coerce")

    df["EMA_50"] = ta.trend.ema_indicator(close, window=50)
    df["EMA_150"] = ta.trend.ema_indicator(close, window=150)
    df["EMA_200"] = ta.trend.ema_indicator(close, window=200)
    df["EMA_200_Slope_Pct_50D"] = df["EMA_200"].pct_change(50) * 100

    df["Return_63D_Pct"] = close.pct_change(63) * 100
    df["Return_126D_Pct"] = close.pct_change(126) * 100
    df["Return_252D_Pct"] = close.pct_change(252) * 100

    df["High_252D"] = high.rolling(window=252).max()
    df["Low_50D"] = low.rolling(window=50).min()
    df["Distance_From_52W_High_Pct"] = ((df["High_252D"] - close) / df["High_252D"]) * 100

    df["Volume_Avg_20"] = volume.rolling(window=20).mean()
    df["Volume_Avg_50"] = volume.rolling(window=50).mean()
    df["Volume_Ratio_20_50"] = df["Volume_Avg_20"] / df["Volume_Avg_50"]

    adx_indicator = ta.trend.ADXIndicator(high=high, low=low, close=close, window=14)
    df["ADX"] = adx_indicator.adx()
    df["+DI"] = adx_indicator.adx_pos()
    df["-DI"] = adx_indicator.adx_neg()

    df["OBV"] = ta.volume.on_balance_volume(close, volume)
    df["OBV_EMA_50"] = ta.trend.ema_indicator(df["OBV"], window=50)

    df["ATR"] = ta.volatility.average_true_range(high=high, low=low, close=close, window=14)
    df["ATR_Pct"] = (df["ATR"] / close) * 100

    return df


def check_long_term_gates(row):
    required_fields = ["Close", "EMA_50", "EMA_200", "EMA_200_Slope_Pct_50D", "Return_126D_Pct", "ATR_Pct"]
    if any(pd.isna(row[field]) for field in required_fields):
        return False, "Insufficient data for long-term gates"

    checks = {
        "Close <= EMA_200": row["Close"] <= row["EMA_200"],
        "EMA_50 <= EMA_200": row["EMA_50"] <= row["EMA_200"],
        "EMA_200 slope <= 0": row["EMA_200_Slope_Pct_50D"] <= 0,
        "126D return <= 0": row["Return_126D_Pct"] <= 0,
        f"ATR% > {MAX_ACCEPTABLE_ATR_PERCENT}": row["ATR_Pct"] > MAX_ACCEPTABLE_ATR_PERCENT,
    }

    failed = [reason for reason, did_fail in checks.items() if did_fail]
    if failed:
        return False, " | ".join(failed)

    return True, "Passed"


def score_trend_structure(row):
    score = 0
    if row["Close"] > row["EMA_50"]:
        score += 10
    if row["EMA_50"] > row["EMA_150"] > row["EMA_200"]:
        score += 10
    elif row["EMA_50"] > row["EMA_200"]:
        score += 7
    if row["EMA_200_Slope_Pct_50D"] > 2:
        score += 10
    elif row["EMA_200_Slope_Pct_50D"] > 0:
        score += 6
    return score


def score_relative_strength(row):
    score = 0

    if row["Return_126D_Pct"] >= 20:
        score += 10
    elif row["Return_126D_Pct"] >= 8:
        score += 6
    elif row["Return_126D_Pct"] > 0:
        score += 3

    if row["Return_252D_Pct"] >= 35:
        score += 10
    elif row["Return_252D_Pct"] >= 12:
        score += 6
    elif row["Return_252D_Pct"] > 0:
        score += 3

    if row["Return_63D_Pct"] > 0:
        score += 5

    return score


def score_high_proximity(row):
    distance = row["Distance_From_52W_High_Pct"]
    if pd.isna(distance):
        return 0
    if distance <= 10:
        return 15
    if distance <= 20:
        return 10
    if distance <= 30:
        return 5
    return 0


def score_volume_confirmation(row):
    score = 0
    if pd.notna(row["Volume_Ratio_20_50"]) and row["Volume_Ratio_20_50"] > 1:
        score += 5
    if pd.notna(row["OBV"]) and pd.notna(row["OBV_EMA_50"]) and row["OBV"] > row["OBV_EMA_50"]:
        score += 5
    return score


def score_adx(row):
    adx = row["ADX"]
    if pd.isna(adx):
        return 0
    if 20 <= adx <= 40:
        return 10
    if ADX_MIN_THRESHOLD <= adx < 20 or 40 < adx <= 60:
        return 5
    if adx > 60:
        return 2
    return 0


def score_risk_quality(row):
    atr_pct = row["ATR_Pct"]
    if pd.isna(atr_pct):
        return 0
    if atr_pct <= 4:
        return 10
    if atr_pct <= 7:
        return 7
    if atr_pct <= 10:
        return 4
    if atr_pct <= MAX_ACCEPTABLE_ATR_PERCENT:
        return 1
    return -5


def calculate_stop_loss(row):
    close = row["Close"]
    atr_stop = close - (3 * row["ATR"]) if pd.notna(row["ATR"]) else float("nan")
    low_50_stop = row["Low_50D"]
    ema50_stop = row["EMA_50"] * 0.98 if pd.notna(row["EMA_50"]) else float("nan")

    stop_candidates = [atr_stop, low_50_stop, ema50_stop]
    valid_stops = [stop for stop in stop_candidates if pd.notna(stop) and 0 < stop < close]

    if not valid_stops:
        return atr_stop, low_50_stop, ema50_stop, float("nan"), float("nan"), float("nan"), 0

    recommended_stop = max(valid_stops)
    risk_per_share = close - recommended_stop
    stop_distance_pct = (risk_per_share / close) * 100 if close else float("nan")
    position_size = math.floor(DOLLAR_RISK_PER_TRADE / risk_per_share) if risk_per_share > 0 else 0

    return atr_stop, low_50_stop, ema50_stop, recommended_stop, stop_distance_pct, risk_per_share, position_size


def evaluate_intraday_distribution_risk(daily_df, hourly_df):
    risk = {
        "flag": False,
        "reason": "",
        "daily_change_pct": float("nan"),
        "last_3h_return_pct": float("nan"),
        "bearish_1h_candles_last3": 0,
        "last_1h_bearish": False,
        "penalty": 0,
    }

    if INTRADAY_DISTRIBUTION_CHECK != "ON" or len(daily_df) < 2 or hourly_df.empty or len(hourly_df) < 3:
        return risk

    previous_close = daily_df["Close"].iloc[-2]
    current_close = daily_df["Close"].iloc[-1]
    if pd.notna(previous_close) and previous_close != 0:
        risk["daily_change_pct"] = ((current_close / previous_close) - 1) * 100

    last_3h = hourly_df.tail(3)
    first_open = last_3h["Open"].iloc[0]
    last_close = last_3h["Close"].iloc[-1]
    if pd.notna(first_open) and first_open != 0:
        risk["last_3h_return_pct"] = ((last_close / first_open) - 1) * 100

    bearish_candles = (last_3h["Close"] < last_3h["Open"]).sum()
    risk["bearish_1h_candles_last3"] = int(bearish_candles)
    risk["last_1h_bearish"] = bool(last_3h["Close"].iloc[-1] < last_3h["Open"].iloc[-1])

    reasons = []
    if risk["daily_change_pct"] <= DAILY_DROP_RISK_PCT:
        reasons.append(f"Daily change <= {DAILY_DROP_RISK_PCT}%")
    if risk["last_3h_return_pct"] <= LAST_3H_DROP_RISK_PCT:
        reasons.append(f"Last 3H return <= {LAST_3H_DROP_RISK_PCT}%")
    if risk["bearish_1h_candles_last3"] >= 2:
        reasons.append("2+ bearish candles in last 3H")
    if risk["last_1h_bearish"]:
        reasons.append("Last 1H candle bearish")

    severe = (
        risk["daily_change_pct"] <= DAILY_DROP_RISK_PCT
        and risk["bearish_1h_candles_last3"] >= 2
        and risk["last_1h_bearish"]
    )

    if severe or (risk["last_3h_return_pct"] <= LAST_3H_DROP_RISK_PCT and risk["bearish_1h_candles_last3"] >= 2):
        risk["flag"] = True
        risk["reason"] = " | ".join(reasons)
        risk["penalty"] = INTRADAY_RISK_PENALTY

    return risk


def build_result_row(ticker, status, gate_status, row, scores, intraday_risk):
    atr_stop, low_50_stop, ema50_stop, recommended_stop, stop_distance_pct, risk_per_share, position_size = calculate_stop_loss(row)

    output = {
        "Ticker": ticker,
        "Status": status,
        "Gate_Status": gate_status,
        "Trend_Score": scores.get("trend", 0),
        "Relative_Strength_Score": scores.get("relative_strength", 0),
        "High_Proximity_Score": scores.get("high_proximity", 0),
        "Volume_Score": scores.get("volume", 0),
        "ADX_Score": scores.get("adx", 0),
        "Risk_Quality_Score": scores.get("risk_quality", 0),
        "Raw_Mo_Score": scores.get("raw", scores.get("final", 0)),
        "Intraday_Risk_Flag": intraday_risk.get("flag", False),
        "Intraday_Risk_Reason": intraday_risk.get("reason", ""),
        "Daily_Change_Pct": intraday_risk.get("daily_change_pct", ""),
        "Last_3H_Return_Pct": intraday_risk.get("last_3h_return_pct", ""),
        "Bearish_1H_Candles_Last3": intraday_risk.get("bearish_1h_candles_last3", 0),
        "Last_1H_Bearish": intraday_risk.get("last_1h_bearish", False),
        "Intraday_Risk_Penalty": intraday_risk.get("penalty", 0),
        "Final_Mo_Score": scores.get("final", 0),
        "Stop_ATR_3x": atr_stop,
        "Stop_50D_Low": low_50_stop,
        "Stop_EMA50_Buffer": ema50_stop,
        "Recommended_Stop": recommended_stop,
        "Stop_Distance_Pct": stop_distance_pct,
        "Risk_Per_Share": risk_per_share,
        "Position_Size": position_size,
    }

    for field in CSV_FIELDS:
        if field not in output and field in row:
            output[field] = row[field]

    return {field: clean_number(output.get(field, "")) for field in CSV_FIELDS}


def open_log_writer():
    global EXECUTION_LOG_CSV

    if os.path.exists(EXECUTION_LOG_CSV):
        try:
            os.remove(EXECUTION_LOG_CSV)
        except PermissionError:
            locked_log = EXECUTION_LOG_CSV
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_path = Path(EXECUTION_LOG_CSV)
            EXECUTION_LOG_CSV = str(base_path.with_name(f"{base_path.stem}_{timestamp}{base_path.suffix}"))
            print(f"Warning: Log file {locked_log} is in use. Writing this run to: {EXECUTION_LOG_CSV}")

    log_file = open(EXECUTION_LOG_CSV, "w", encoding="utf-8", newline="")
    writer = csv.DictWriter(log_file, fieldnames=CSV_FIELDS)
    writer.writeheader()
    return log_file, writer


def load_tickers_from_csv():
    if not os.path.exists(TICKER_INPUT_CSV):
        print(f"Error: Seed file {TICKER_INPUT_CSV} not found.")
        return []

    tickers_df = pd.read_csv(TICKER_INPUT_CSV)
    if "Ticker" in tickers_df.columns:
        ticker_col = "Ticker"
    elif "Symbol" in tickers_df.columns:
        ticker_col = "Symbol"
    else:
        ticker_col = tickers_df.columns[0]

    return tickers_df[ticker_col].dropna().tolist()


def normalize_ticker(ticker):
    formatted_ticker = str(ticker).strip()
    if "XNSE" in formatted_ticker:
        formatted_ticker = formatted_ticker.replace("XNSE", "").replace(":", "").strip() + ".NS"
    return formatted_ticker


def main():
    parser = argparse.ArgumentParser(description="Momentum Detector V4 - Long-Term Momentum Engine")
    parser.add_argument("--tickers", nargs="*", default=[], help="Space-separated list of stock codes.")
    args = parser.parse_args()

    log_file, writer = open_log_writer()

    try:
        if args.tickers:
            raw_tickers = args.tickers
            print("Reading tickers directly from CLI arguments...")
        else:
            print(f"Reading seed file: {TICKER_INPUT_CSV}...")
            raw_tickers = load_tickers_from_csv()
            if not raw_tickers:
                return

        raw_tickers = sorted([str(t).strip() for t in raw_tickers if str(t).strip()])

        total_processed = 0
        total_disqualified = 0
        qualified_setups = []

        print("Starting Momentum Detector V4 long-term scan...")

        for ticker in raw_tickers:
            formatted_ticker = normalize_ticker(ticker)
            print(f"Processing long-term asset series for: {formatted_ticker}...")
            time.sleep(API_DELAY_SECONDS)

            try:
                df = fetch_historical_daily_data(formatted_ticker)

                if df.empty:
                    print(f"Skipping {formatted_ticker}: insufficient history (<{MIN_HISTORY_BARS} bars).")
                    writer.writerow({"Ticker": formatted_ticker, "Status": "Disqualified", "Gate_Status": "Insufficient history"})
                    total_disqualified += 1
                    total_processed += 1
                    continue

                live_data = fetch_live_intraday_override(formatted_ticker)
                df = apply_live_price_override(df, live_data)
                hourly_data = fetch_hourly_intraday_data(formatted_ticker)
                calc_df = calculate_technical_indicators(df.copy())
                last_row = calc_df.iloc[-1]

                gates_passed, gate_status = check_long_term_gates(last_row)
                intraday_risk = evaluate_intraday_distribution_risk(calc_df, hourly_data)

                scores = {
                    "trend": score_trend_structure(last_row),
                    "relative_strength": score_relative_strength(last_row),
                    "high_proximity": score_high_proximity(last_row),
                    "volume": score_volume_confirmation(last_row),
                    "adx": score_adx(last_row),
                    "risk_quality": score_risk_quality(last_row),
                }
                scores["raw"] = sum(scores.values())
                scores["final"] = max(0, scores["raw"] - intraday_risk["penalty"])
                intraday_vetoed = intraday_risk["flag"] and INTRADAY_DISTRIBUTION_VETO == "ON"

                if gates_passed and scores["final"] >= MIN_MOMENTUM_SCORE and not intraday_vetoed:
                    status_label = "Passed"
                    qualified_setups.append(
                        {
                            "ticker": formatted_ticker,
                            "score": scores["final"],
                            "raw_score": scores["raw"],
                            "close": last_row["Close"],
                            "stop": calculate_stop_loss(last_row)[3],
                            "position_size": calculate_stop_loss(last_row)[6],
                        }
                    )
                else:
                    status_label = "Disqualified"
                    if intraday_vetoed:
                        gate_status = f"{gate_status} | Intraday distribution risk: {intraday_risk['reason']}"
                    total_disqualified += 1

                writer.writerow(build_result_row(formatted_ticker, status_label, gate_status, last_row, scores, intraday_risk))
                total_processed += 1

            except RuntimeError as re:
                print(f"API Error processing {formatted_ticker}: {re}")
                writer.writerow({"Ticker": formatted_ticker, "Status": "Disqualified", "Gate_Status": "API Connection/Rate Limit Failure"})
                total_disqualified += 1
                total_processed += 1
            except Exception as e:
                print(f"System Exception processing {formatted_ticker}: {e}")
                writer.writerow({"Ticker": formatted_ticker, "Status": "Disqualified", "Gate_Status": f"System Exception: {str(e).replace(',', ';')}"})
                total_disqualified += 1
                total_processed += 1

        qualified_setups.sort(key=lambda x: x["score"], reverse=True)

        print("============================================================")
        print("=== MOMENTUM DETECTOR V4: LONG-TERM SCANNER COMPLETE ===")
        print("============================================================")
        print(f"Total Tickers Processed     : {total_processed}")
        print(f"Total Disqualified          : {total_disqualified}")
        print(f"Qualified Momentum Setups   : {len(qualified_setups)}")
        print()
        print("Identified Long-Term Momentum Codes:")
        print("------------------------------------------------------------")
        for i, setup in enumerate(qualified_setups, 1):
            print(
                f"{i}. {setup['ticker']:<10} | Score: {setup['score']}/100 | "
                f"Close: {setup['close']:.2f} | Stop: {setup['stop']:.2f} | Shares: {setup['position_size']}"
            )
        print()
        print(f"-> Logs committed to: {EXECUTION_LOG_CSV}")
        print("============================================================")

        if POST_PROCESS_EXCEL == "ON":
            print("Generating MS Excel Workbook via openpyxl post-processing...")
            try:
                df_log = pd.read_csv(EXECUTION_LOG_CSV)
                with pd.ExcelWriter(EXCEL_OUTPUT_NAME, engine="openpyxl") as writer_excel:
                    df_log.to_excel(writer_excel, sheet_name="Long_Term_Momentum", index=False)
                print(f"Workbook successfully created: {EXCEL_OUTPUT_NAME}")
            except Exception as e:
                print(f"Failed to generate Excel workbook: {e}")
    finally:
        log_file.close()


if __name__ == "__main__":
    main()
