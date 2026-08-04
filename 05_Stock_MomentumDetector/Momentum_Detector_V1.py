import time
import os
import sys
import argparse
from pathlib import Path
import pandas as pd
import yfinance as yf
import ta

# ==========================================
# BASE FOLDER CONFIGURATION
# ==========================================
BASE_FOLDER = "D:/TMP"

# Ensure the base folder exists
if not os.path.exists(BASE_FOLDER):
    os.makedirs(BASE_FOLDER)

# ==========================================
# CONFIGURATION & ARGUMENT DECLARATION
# ==========================================
#TICKER_INPUT_CSV = os.path.join(BASE_FOLDER, "tickers_seed_list.csv")
TICKER_INPUT_CSV = Path("D:/Tools/StockCodeMaster/02_Stock/24-06-US_Common_Stocks_Master_Library-Sector-Technology.csv")
EXECUTION_LOG_CSV = os.path.join(BASE_FOLDER, "26-06-select_Momentum_Execution_Dump.csv")
POST_PROCESS_EXCEL = "OFF"                  # Toggle "ON" to generate formatted MS Excel file
EXCEL_OUTPUT_NAME = os.path.join(BASE_FOLDER, "26-06-US_Stock_Sector-Technology_Momentum_Analyzed_Output.xlsx")

API_DELAY_SECONDS = 1.0                     # Micro-pause to prevent throttling
LOOKBACK_WINDOW = "260d"                    # Payload size per sequential fetch

# Risk Management Configuration
DOLLAR_RISK_PER_TRADE = 100.0               # Used for dynamic ATR position sizing

# Go/No-Go Gate Thresholds
ADX_MIN_THRESHOLD = 20
RSI_MIN_THRESHOLD = 55
RSI_MAX_THRESHOLD = 75                      # Configurable upper threshold to trigger overbought penalties
MIN_MOMENTUM_SCORE = 20                     # Out of maximum 30 weighted points

def calculate_technical_indicators(df):
    """Calculates all required technical indicators using the ta library."""
    # EMA 200
    df['EMA_200'] = ta.trend.ema_indicator(df['Close'], window=200)
    
    # ADX and DMI
    adx_indicator = ta.trend.ADXIndicator(df['High'], df['Low'], df['Close'], window=14)
    df['ADX'] = adx_indicator.adx()
    df['+DI'] = adx_indicator.adx_pos()
    df['+DI_diff'] = adx_indicator.adx_pos() - adx_indicator.adx_neg()
    df['+DI_val'] = adx_indicator.adx_pos()
    df['-DI_val'] = adx_indicator.adx_neg()
    
    # MACD
    macd_indicator = ta.trend.MACD(df['Close'], window_slow=26, window_fast=12, window_sign=9)
    df['MACD_Line'] = macd_indicator.macd()
    df['Signal_Line'] = macd_indicator.macd_signal()
    
    # RSI
    df['RSI'] = ta.momentum.rsi(df['Close'], window=14)
    
    # On-Balance Volume (OBV) & EMA 20 of OBV
    df['OBV'] = ta.volume.on_balance_volume(df['Close'], df['Volume'])
    df['OBV_EMA_20'] = ta.trend.ema_indicator(df['OBV'], window=20)
    
    # ATR 14
    df['ATR'] = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'], window=14)
    
    return df

def check_phase1_gates(df_row):
    """Evaluates Strict Elimination Gates (Go/No-Go)."""
    if pd.isna(df_row['EMA_200']) or pd.isna(df_row['+DI_val']) or pd.isna(df_row['-DI_val']) or pd.isna(df_row['MACD_Line']) or pd.isna(df_row['Signal_Line']):
        return False, "Insufficient Data for Gates"
        
    macro_trend = df_row['Close'] > df_row['EMA_200']
    directional_dominance = df_row['+DI_val'] > df_row['-DI_val']
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
    
    # Goldilocks zone (56–68) = 10 points
    if 56 <= rsi_val <= 68:
        return 10, False
    # Between RSI_MIN_THRESHOLD (55) and 56
    elif RSI_MIN_THRESHOLD <= rsi_val < 56:
        # Graded scale, e.g., prorated linearly from 55 to 56 mapping to points 0-10 or just stepped
        return 5, False
    # Between 68 and RSI_MAX_THRESHOLD (75)
    elif 68 < rsi_val <= RSI_MAX_THRESHOLD:
        return 5, False
    # Exceeding maximum threshold receives active negative penalties (-10 points)
    elif rsi_val > RSI_MAX_THRESHOLD:
        return -10, False
    else:
        return 0, False

def calculate_adx_score(adx_val):
    """Scores Strength (ADX - 14 period) via weighted tiers."""
    if pd.isna(adx_val):
        return 0
    
    # Maximum points (10) sit in the 26–40 zone
    if 26 <= adx_val <= 40:
        return 10
    # Zones 20-25 or 41-60 can be assigned partial points, e.g., 5 points
    elif (ADX_MIN_THRESHOLD <= adx_val < 26) or (40 < adx_val <= 60):
        return 5
    # Climax trends above 60 are penalized (-5 points)
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
    
    # Rewards fresh volume breakouts (10 points for a cross within the last 1–3 days)
    # Checking if OBV crossed above OBV_EMA_20 recently
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
        
    # Penalizes negative divergence where price rises but volume flows out
    price_rising = last_row['Close'] > prev_row['Close']
    obv_falling = last_row['OBV'] < prev_row['OBV']
    
    if price_rising and obv_falling:
        return -5, False
        
    return 0, False

def main():
    # Setup CLI argument parser
    parser = argparse.ArgumentParser(description="Momentum Identification and Analysis Engine")
    parser.add_argument(
        "--tickers", 
        nargs="*", 
        default=[], 
        help="Space-separated list of stock codes to process directly from CLI."
    )
    args = parser.parse_args()

    # 1. Environment Initialization & Reset/Overwrite Log
    if os.path.exists(EXECUTION_LOG_CSV):
        os.remove(EXECUTION_LOG_CSV)
        
    # Initialize continuous CSV audit trail in write mode with indicator headers
    with open(EXECUTION_LOG_CSV, "w", encoding="utf-8") as f:
        f.write("Ticker,Status,Gates_Passed,Close,EMA_200,RSI,ADX,OBV,OBV_EMA_20,MACD_Line,Signal_Line,ATR,RSI_Score,ADX_Score,OBV_Score,Final_Mo_Score\n")
        
    # Determine input tickers: CLI arguments take precedence, otherwise read from TICKER_INPUT_CSV
    if args.tickers:
        raw_tickers = args.tickers
        print("Reading tickers directly from CLI arguments...")
    else:
        print(f"No CLI tickers provided. Falling back to read seed file: {TICKER_INPUT_CSV}...")
        if not os.path.exists(TICKER_INPUT_CSV):
            print(f"Error: Seed file {TICKER_INPUT_CSV} not found and no CLI tickers provided.")
            return
        tickers_df = pd.read_csv(TICKER_INPUT_CSV)
        
        # Dynamically determine the ticker column based on header rules
        if 'Ticker' in tickers_df.columns:
            ticker_col = 'Ticker'
        elif 'Symbol' in tickers_df.columns:
            ticker_col = 'Symbol'
        else:
            ticker_col = tickers_df.columns[0]
            
        raw_tickers = tickers_df[ticker_col].dropna().tolist()
        
    # Sort tickers alphabetically so they are processed and output in alphabetical order
    raw_tickers = sorted([str(t).strip() for t in raw_tickers])
    
    total_processed = 0
    total_disqualified = 0
    qualified_setups = []
    
    print("Starting sequential processing of tickers...")
    
    for ticker in raw_tickers:
        # Translate XNSE prefix to .NS suffix
        formatted_ticker = str(ticker).strip()
        if formatted_ticker.startswith("XNSE:"):
            formatted_ticker = formatted_ticker.replace("XNSE:", "") + ".NS"
            
        print(f"Processing: {formatted_ticker}...")
        
        # 2. API Rate-Limit Protection & Fetch Payload
        time.sleep(API_DELAY_SECONDS)
        
        # 3. Failsafe Resiliency
        try:
            # Fetch data payload
            df = yf.download(formatted_ticker, period=LOOKBACK_WINDOW, progress=False)
            if df.empty or len(df) < 200:
                print(f"Skipping {formatted_ticker}: Insufficient data retrieved.")
                with open(EXECUTION_LOG_CSV, "a", encoding="utf-8") as f:
                    f.write(f"{formatted_ticker},Disqualified,Insufficient Data,,,,,,,,,,,0,0,0,0\n")
                total_disqualified += 1
                total_processed += 1
                continue
                
            # Flatten multi-index columns if yfinance returns them
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [col[0] for col in df.columns]
                
            # Ensure essential columns exist
            required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
            if not all(col in df.columns for col in required_cols):
                print(f"Skipping {formatted_ticker}: Missing columns.")
                with open(EXECUTION_LOG_CSV, "a", encoding="utf-8") as f:
                    f.write(f"{formatted_ticker},Disqualified,Missing Data Columns,,,,,,,,,,,0,0,0,0\n")
                total_disqualified += 1
                total_processed += 1
                continue

            # 4. Execute Scoring & Calculations on .iloc[-1] arrays
            df = calculate_technical_indicators(df)
            
            last_row = df.iloc[-1]
            
            passed, gate_status = check_phase1_gates(last_row)
            
            if not passed:
                with open(EXECUTION_LOG_CSV, "a", encoding="utf-8") as f:
                    f.write(f"{formatted_ticker},Disqualified,{gate_status},{last_row['Close']},{last_row['EMA_200']},{last_row['RSI']},{last_row['ADX']},{last_row['OBV']},{last_row['OBV_EMA_20']},{last_row['MACD_Line']},{last_row['Signal_Line']},{last_row['ATR']},0,0,0,0\n")
                total_disqualified += 1
                total_processed += 1
                continue
                
            # Phase 2 Checks
            rsi_score, _ = calculate_rsi_score(last_row['RSI'])
            adx_score = calculate_adx_score(last_row['ADX'])
            obv_score, accumulation_flag = check_obv_conviction(df)
            
            final_score = rsi_score + adx_score + obv_score
            
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
                
            # Instantly write full audit rows with indicator values to the CSV on disk
            with open(EXECUTION_LOG_CSV, "a", encoding="utf-8") as f:
                f.write(f"{formatted_ticker},{status_label},{gate_status},{last_row['Close']},{last_row['EMA_200']},{last_row['RSI']},{last_row['ADX']},{last_row['OBV']},{last_row['OBV_EMA_20']},{last_row['MACD_Line']},{last_row['Signal_Line']},{last_row['ATR']},{rsi_score},{adx_score},{obv_score},{final_score}\n")
                
            total_processed += 1
            
        except Exception as e:
            print(f"Error processing {formatted_ticker}: {e}")
            with open(EXECUTION_LOG_CSV, "a", encoding="utf-8") as f:
                f.write(f"{formatted_ticker},Disqualified,Exception Occurred: {str(e).replace(',', ';')},,,,,,,,,,,0,0,0,0\n")
            total_disqualified += 1
            total_processed += 1
            continue
            
    # Sort the identified setups by MO Score descending (highest score first)
    qualified_setups.sort(key=lambda x: x['score'], reverse=True)

    # 5. Console Messaging Dashboard
    print("============================================================")
    print("=== RUNTIME ENGINE: MOMENTUM STOCK SCANNER COMPLETE      ===")
    print("============================================================")
    print(f"Total Tickers Processed     : {total_processed}")
    print(f"Total Disqualified          : {total_disqualified}")
    print(f"Qualified Momentum Setups   : {len(qualified_setups)}")
    print()
    print("Identified Momentum Codes (Sorted by MO Score Descending):")
    print("------------------------------------------------------------")
    for i, setup in enumerate(qualified_setups, 1):
        print(f"{i}. {setup['ticker']:<15} | Mo Score: {setup['score']}/30 | Accumulation: {setup['accumulation']}")
    print()
    print("Execution Details have been sequentially committed to:")
    print(f"-> {EXECUTION_LOG_CSV}")
    print("============================================================")
    
    # Post-Processing Excel Generation conditionally executed exclusively if global parameter matches "ON"
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