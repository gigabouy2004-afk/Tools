import time
import os
import sys
import argparse
from pathlib import Path
import pandas as pd
import yfinance as yf
import ta
from datetime import datetime, timedelta

# ==========================================
# BASE FOLDER CONFIGURATION
# ==========================================
BASE_FOLDER = "D:/Tools/Stock_MomentumDetector"  # Change this to your desired base folder path

# Ensure the base folder exists
if not os.path.exists(BASE_FOLDER):
    os.makedirs(BASE_FOLDER)

# ==========================================
# CONFIGURATION & ARGUMENT DECLARATION
# ==========================================
TICKER_INPUT_CSV = Path("D:/Tools/StockCodeMaster/02_Stock/21-6-All_Energy_DataCenter_Listed_StockCodes.csv")  # Input seed file with stock codes
EXECUTION_LOG_CSV = os.path.join(BASE_FOLDER, "29-06-USA_AllStocks_Momentum_Execution_Dump.csv")
POST_PROCESS_EXCEL = "OFF"                  # Toggle "ON" to generate formatted MS Excel file
EXCEL_OUTPUT_NAME = os.path.join(BASE_FOLDER, "29-06-US_Stock_Momentum_Analyzed_Output.xlsx")

API_DELAY_SECONDS = 1.0                     # Micro-pause to prevent throttling
LOOKBACK_WINDOW = "260d"                    # Payload size per sequential fetch

# Risk Management Configuration
DOLLAR_RISK_PER_TRADE = 100.0               # Used for dynamic ATR position sizing

# Go/No-Go Gate Thresholds
ADX_MIN_THRESHOLD = 20
RSI_MIN_THRESHOLD = 55
RSI_MAX_THRESHOLD = 75                      # Configurable upper threshold to trigger overbought penalties
MIN_MOMENTUM_SCORE = 25                     # Out of maximum 45 weighted points (30 base + 5 structural + 10 Aroon)

def fetch_historical_daily_data(formatted_ticker):
    """Fetches purely daily historical candles to build unbiased technical indicator arrays."""
    try:
        hist_df = yf.download(formatted_ticker, period=LOOKBACK_WINDOW, progress=False)
        
        if hist_df.empty or len(hist_df) < 250: # Enforce 250 bars to safely compute indicators
            return pd.DataFrame()
            
        if isinstance(hist_df.columns, pd.MultiIndex):
            hist_df.columns = hist_df.columns.get_level_values(0)
            
        return hist_df[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
        
    except Exception as e:
        raise RuntimeError(f"API_Daily_Fetch_Error: {str(e)}")

def fetch_live_intraday_override(formatted_ticker):
    """Fetches the current real-time/intraday quote to override the last array bar."""
    try:
        ticker_obj = yf.Ticker(formatted_ticker)
        todays_data = ticker_obj.history(period="1d")
        return todays_data
    except Exception as e:
        raise RuntimeError(f"API_Intraday_Fetch_Error: {str(e)}")

def calculate_technical_indicators(df):
    """Calculates technical indicators using completed daily historical bars."""
    close = pd.to_numeric(df['Close'], errors='coerce')
    high = pd.to_numeric(df['High'], errors='coerce')
    low = pd.to_numeric(df['Low'], errors='coerce')
    volume = pd.to_numeric(df['Volume'], errors='coerce')

    df['EMA_200'] = ta.trend.ema_indicator(close, window=200)
    
    adx_indicator = ta.trend.ADXIndicator(high=high, low=low, close=close, window=14)
    df['ADX'] = adx_indicator.adx()
    df['+DI'] = adx_indicator.adx_pos()
    df['-DI'] = adx_indicator.adx_neg()
    
    macd_indicator = ta.trend.MACD(close=close, window_slow=26, window_fast=12, window_sign=9)
    df['MACD_Line'] = macd_indicator.macd()
    df['Signal_Line'] = macd_indicator.macd_signal()
    
    df['RSI'] = ta.momentum.rsi(close, window=14)
    
    df['OBV'] = ta.volume.on_balance_volume(close, volume)
    df['OBV_EMA_20'] = ta.trend.ema_indicator(df['OBV'], window=20)
    
    df['ATR'] = ta.volatility.average_true_range(high=high, low=low, close=close, window=14)

    aroon_indicator = ta.trend.AroonIndicator(high=high, low=low, window=14)
    df['Aroon_Up'] = aroon_indicator.aroon_up()
    df['Aroon_Down'] = aroon_indicator.aroon_down()
    
    return df

def apply_live_price_override(df, live_df):
    """Applies live intraday prices to the most recent bar for gate evaluation."""
    if live_df.empty:
        return df
        
    real_time_close = live_df['Close'].iloc[-1]
    real_time_high = live_df['High'].iloc[-1]
    real_time_low = live_df['Low'].iloc[-1]
    real_time_volume = live_df['Volume'].iloc[-1]
    
    last_idx = df.index[-1]
    df.loc[last_idx, 'Close'] = real_time_close
    df.loc[last_idx, 'High'] = max(df.loc[last_idx, 'High'], real_time_high)
    df.loc[last_idx, 'Low'] = min(df.loc[last_idx, 'Low'], real_time_low)
    df.loc[last_idx, 'Volume'] = real_time_volume
    
    return df

def check_phase1_gates(df_row):
    """Evaluates Strict Elimination Gates (Go/No-Go)."""
    if pd.isna(df_row['EMA_200']) or pd.isna(df_row['+DI']) or pd.isna(df_row['-DI']) or pd.isna(df_row['MACD_Line']) or pd.isna(df_row['Signal_Line']):
        return False, "Insufficient Data for Gates"
        
    macro_trend = df_row['Close'] > df_row['EMA_200']
    directional_dominance = df_row['+DI'] > df_row['-DI']
    trajectory = (df_row['MACD_Line'] > df_row['Signal_Line']) and (df_row['MACD_Line'] > 0)
    
    gates_passed = macro_trend and directional_dominance and trajectory
    
    gate_reasons = []
    if not macro_trend: gate_reasons.append("Price <= EMA_200")
    if not directional_dominance: gate_reasons.append("+DI <= -DI")
    if not trajectory: gate_reasons.append("MACD fails conditions")
    
    return gates_passed, "Passed" if gates_passed else " | ".join(gate_reasons)

def calculate_rsi_score(rsi_val):
    """Scores Velocity (RSI - 14 period) based on tiered scale."""
    if pd.isna(rsi_val):
        return 0, False
    
    if 56 <= rsi_val <= 68:
        return 10, False
    elif RSI_MIN_THRESHOLD <= rsi_val < 56:
        return 5, False
    elif 68 < rsi_val <= RSI_MAX_THRESHOLD:
        return 5, False
    elif rsi_val > RSI_MAX_THRESHOLD:
        return -10, False
    else:
        return 0, False

def calculate_adx_score(adx_val):
    """Scores Strength (ADX - 14 period) via weighted tiers."""
    if pd.isna(adx_val):
        return 0
    
    if 26 <= adx_val <= 40:
        return 10
    elif (ADX_MIN_THRESHOLD <= adx_val < 26) or (40 < adx_val <= 60):
        return 5
    elif adx_val > 60:
        return -5
    else:
        return 0

def check_obv_conviction(df):
    """Evaluates Conviction (On-Balance Volume vs. 20-EMA)."""
    if len(df) < 2:
        return 0, False
        
    last_row = df.iloc[-1]
    prev_row = df.iloc[-2]
    
    cross_fresh = False
    for i in range(1, 4):
        if len(df) > i:
            r = df.iloc[-i]
            r_prev = df.iloc[-(i+1)]
            if r['OBV'] >= r['OBV_EMA_20'] and r_prev['OBV'] < r_prev['OBV_EMA_20']:
                cross_fresh = True
                break
                
    if cross_fresh:
        return 10, True
        
    price_rising = last_row['Close'] > prev_row['Close']
    obv_falling = last_row['OBV'] < prev_row['OBV']
    
    if price_rising and obv_falling:
        return -5, False
        
    return 0, False

def check_structural_security(df):
    """Checks if Day D Opening Price > Day D-1 Opening Price for structural gap continuation."""
    if len(df) < 2:
        return 0
    open_d = df['Open'].iloc[-1]
    open_d_minus_1 = df['Open'].iloc[-2]
    
    if pd.notna(open_d) and pd.notna(open_d_minus_1) and open_d > open_d_minus_1:
        return 5
    return 0

def calculate_aroon_score(aroon_up, aroon_down):
    """Scores Trend Synchronicity using the Aroon Indicator (14 period)."""
    if pd.isna(aroon_up) or pd.isna(aroon_down):
        return 0
        
    if aroon_up > 70 and aroon_down < 30:
        return 10
    elif aroon_up > 50 and aroon_down < 50:
        return 5
    elif aroon_up < 30 and aroon_down > 70:
        return -5
    else:
        return 0

def main():
    global EXECUTION_LOG_CSV

    parser = argparse.ArgumentParser(description="Momentum Identification Engine")
    parser.add_argument("--tickers", nargs="*", default=[], help="Space-separated list of stock codes.")
    args = parser.parse_args()

    # Safely clear or reset log. If the configured CSV is locked, write this run to a new file.
    if os.path.exists(EXECUTION_LOG_CSV):
        try:
            os.remove(EXECUTION_LOG_CSV)
        except PermissionError:
            locked_log = EXECUTION_LOG_CSV
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_path = Path(EXECUTION_LOG_CSV)
            EXECUTION_LOG_CSV = str(base_path.with_name(f"{base_path.stem}_{timestamp}{base_path.suffix}"))
            print(f"Warning: Log file {locked_log} is in use. Writing this run to: {EXECUTION_LOG_CSV}")
        
    with open(EXECUTION_LOG_CSV, "w", encoding="utf-8") as f:
        f.write("Ticker,Status,Gates_Passed,Close,EMA_200,RSI,ADX,OBV,OBV_EMA_20,MACD_Line,Signal_Line,ATR,Aroon_Up,Aroon_Down,RSI_Score,ADX_Score,OBV_Score,Structural_Score,Aroon_Score,Final_Mo_Score\n")
        
    if args.tickers:
        raw_tickers = args.tickers
        print("Reading tickers directly from CLI arguments...")
    else:
        print(f"Reading seed file: {TICKER_INPUT_CSV}...")
        if not os.path.exists(TICKER_INPUT_CSV):
            print(f"Error: Seed file {TICKER_INPUT_CSV} not found.")
            return
        tickers_df = pd.read_csv(TICKER_INPUT_CSV)
        
        if 'Ticker' in tickers_df.columns:
            ticker_col = 'Ticker'
        elif 'Symbol' in tickers_df.columns:
            ticker_col = 'Symbol'
        else:
            ticker_col = tickers_df.columns[0]
            
        raw_tickers = tickers_df[ticker_col].dropna().tolist()
        
    raw_tickers = sorted([str(t).strip() for t in raw_tickers])
    
    total_processed = 0
    total_disqualified = 0
    qualified_setups = []
    
    print("Starting processing with decoupled technical arrays and real-time overlays...")
    
    for ticker in raw_tickers:
        formatted_ticker = str(ticker).strip()
        if "XNSE" in formatted_ticker:
            formatted_ticker = formatted_ticker.replace("XNSE", "").replace(":", "").strip() + ".NS"
            
        print(f"Processing structural asset series for: {formatted_ticker}...")
        time.sleep(API_DELAY_SECONDS)
        
        try:
            # 1. Base Technical Array (Completed Historical Closes Only)
            df = fetch_historical_daily_data(formatted_ticker)
            
            if df.empty:
                print(f"Skipping {formatted_ticker}: Insufficient historical depth (<250 bars). Cannot compute 200-day EMA.")
                with open(EXECUTION_LOG_CSV, "a", encoding="utf-8") as f:
                    f.write(f"{formatted_ticker},Disqualified,Insufficient History (<250 bars),,,,,,,,,,,,,,,,0\n")
                total_disqualified += 1
                total_processed += 1
                continue

            # 2. Live Intraday Data Fetch & Splicing before indicator calculation
            live_data = fetch_live_intraday_override(formatted_ticker)
            df = apply_live_price_override(df, live_data)

            # 3. Extract Data Completeness Check: Ensure 200-day EMA is available on spliced array
            calc_df = calculate_technical_indicators(df.copy())
            if pd.isna(calc_df['EMA_200'].iloc[-1]):
                print(f"Skipping {formatted_ticker}: 200-day EMA resolves to NaN (Insufficient asset history).")
                with open(EXECUTION_LOG_CSV, "a", encoding="utf-8") as f:
                    f.write(f"{formatted_ticker},Disqualified,200-day EMA history unavailable (NaN),,,,,,,,,,,,,,,,0\n")
                total_disqualified += 1
                total_processed += 1
                continue
            
            last_row = calc_df.iloc[-1]
            
            # 4. Strict Elimination Gates Evaluation using spliced array
            passed, gate_status = check_phase1_gates(last_row)
            
            if not passed:
                with open(EXECUTION_LOG_CSV, "a", encoding="utf-8") as f:
                    f.write(f"{formatted_ticker},Disqualified,{gate_status},{last_row['Close']},{last_row['EMA_200']},{last_row['RSI']},{last_row['ADX']},{last_row['OBV']},{last_row['OBV_EMA_20']},{last_row['MACD_Line']},{last_row['Signal_Line']},{last_row['ATR']},{last_row['Aroon_Up']},{last_row['Aroon_Down']},0,0,0,0,0,0\n")
                total_disqualified += 1
                total_processed += 1
                continue
                
            # 5. Phase 2 Multi-Tiered Scoring
            rsi_score, _ = calculate_rsi_score(last_row['RSI'])
            adx_score = calculate_adx_score(last_row['ADX'])
            obv_score, accumulation_flag = check_obv_conviction(calc_df)
            struct_score = check_structural_security(calc_df)
            aroon_score = calculate_aroon_score(last_row['Aroon_Up'], last_row['Aroon_Down'])
            
            final_score = rsi_score + adx_score + obv_score + struct_score + aroon_score
            
            if final_score >= MIN_MOMENTUM_SCORE:
                qualified_setups.append({
                    'ticker': formatted_ticker,
                    'score': final_score,
                    'accumulation': accumulation_flag
                })
                status_label = "Passed"
            else:
                status_label = "Disqualified"
                total_disqualified += 1
                
            with open(EXECUTION_LOG_CSV, "a", encoding="utf-8") as f:
                f.write(f"{formatted_ticker},{status_label},{gate_status},{last_row['Close']},{last_row['EMA_200']},{last_row['RSI']},{last_row['ADX']},{last_row['OBV']},{last_row['OBV_EMA_20']},{last_row['MACD_Line']},{last_row['Signal_Line']},{last_row['ATR']},{last_row['Aroon_Up']},{last_row['Aroon_Down']},{rsi_score},{adx_score},{obv_score},{struct_score},{aroon_score},{final_score}\n")
                
            total_processed += 1
            
        except RuntimeError as re:
            print(f"API Error processing {formatted_ticker}: {re}")
            with open(EXECUTION_LOG_CSV, "a", encoding="utf-8") as f:
                f.write(f"{formatted_ticker},Disqualified,API Connection/Rate Limit Failure,,,,,,,,,,,,,,,0\n")
            total_disqualified += 1
            total_processed += 1
            continue
        except Exception as e:
            print(f"System Exception processing {formatted_ticker}: {e}")
            with open(EXECUTION_LOG_CSV, "a", encoding="utf-8") as f:
                f.write(f"{formatted_ticker},Disqualified,System Exception: {str(e).replace(',', ';')},,,,,,,,,,,,,,,,0\n")
            total_disqualified += 1
            total_processed += 1
            continue
            
    qualified_setups.sort(key=lambda x: x['score'], reverse=True)

    print("============================================================")
    print("=== RUNTIME ENGINE: REAL-TIME OVERRIDE SCANNER COMPLETE ===")
    print("============================================================")
    print(f"Total Tickers Processed     : {total_processed}")
    print(f"Total Disqualified          : {total_disqualified}")
    print(f"Qualified Momentum Setups   : {len(qualified_setups)}")
    print()
    print("Identified Momentum Codes (Sorted by MO Score Descending):")
    print("------------------------------------------------------------")
    for i, setup in enumerate(qualified_setups, 1):
        print(f"{i}. {setup['ticker']:<15} | Mo Score: {setup['score']}/45 | Accumulation: {setup['accumulation']}")
    print()
    print(f"-> Logs committed to: {EXECUTION_LOG_CSV}")
    print("============================================================")
    
    if POST_PROCESS_EXCEL == "ON":
        print("Generating MS Excel Workbook via openpyxl post-processing...")
        try:
            df_log = pd.read_csv(EXECUTION_LOG_CSV)
            with pd.ExcelWriter(EXCEL_OUTPUT_NAME, engine='openpyxl') as writer:
                df_log.to_excel(writer, sheet_name="Momentum_Scan_Results", index=False)
            print(f"Workbook successfully created: {EXCEL_OUTPUT_NAME}")
        except Exception as e:
            print(f"Failed to generate Excel workbook: {e}")

if __name__ == "__main__":
    main()
