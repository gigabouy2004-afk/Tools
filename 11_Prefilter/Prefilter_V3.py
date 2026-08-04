import yfinance as yf
import pandas as pd
import ta
import os
import sys
import argparse
import concurrent.futures
import time
import random
from datetime import datetime, timezone

# ==========================================
# CONFIGURATION VARIABLES (Defaults)
# ==========================================
DEFAULT_INPUT_CSV_PATH = "D:/Tools/11_Prefilter/SampleCodes.csv"
TICKER_COLUMN_NAME = "Ticker"
DEFAULT_OUTPUT_CSV_PATH = "D:/Tools/11_Prefilter/filtered_results.csv"

# Multithreading configuration (Reduced to prevent Rate Limiting)
MAX_WORKERS = 3

YF_PERIOD = "1y"
YF_INTERVAL = "1d"
MIN_HISTORY_DAYS = 200

ADV_WINDOW = 20
ADV_MIN_LIMIT = 500000

EMA_FAST_WINDOW = 50
EMA_SLOW_WINDOW = 200

MACD_FAST_WINDOW = 12
MACD_SLOW_WINDOW = 26
MACD_SIGNAL_WINDOW = 9
MACD_MIN_LIMIT = 0

ADX_WINDOW = 14
ADX_MIN_LIMIT = 20

RSI_WINDOW = 14
RSI_MIN_LIMIT = 40
RSI_MAX_LIMIT = 65

STOCH_WINDOW = 14
STOCH_SMOOTH_WINDOW = 3
STOCH_MIN_LIMIT = 50
STOCH_MAX_LIMIT = 80
# ==========================================

def get_ticker_list_from_file(csv_path, column_name=TICKER_COLUMN_NAME):
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Missing {csv_path}. You must provide a valid input file.")
        
    try:
        df = pd.read_csv(csv_path, encoding='utf-8-sig')
    except UnicodeDecodeError:
        try:
            df = pd.read_csv(csv_path, encoding='latin-1')
        except Exception:
            df = pd.read_csv(csv_path, encoding='utf-16')

    if column_name not in df.columns:
        raise ValueError(f"Column '{column_name}' not found in {csv_path}. Available columns: {list(df.columns)}")
        
    return df[column_name].dropna().astype(str).tolist()

def get_days_to_earnings(ticker_obj):
    try:
        calendar = ticker_obj.calendar
        earnings_date = None
        
        if isinstance(calendar, dict):
            for key in ["Earnings Date", "earningsDate", "Earnings Date 1"]:
                if key in calendar:
                    val = calendar[key]
                    if isinstance(val, list) and len(val) > 0:
                        earnings_date = val[0]
                    else:
                        earnings_date = val
                    break
                    
        if earnings_date is None:
            try:
                earnings_df = ticker_obj.get_earnings_dates(limit=12)
                if earnings_df is not None and not earnings_df.empty:
                    today_ts = pd.Timestamp.today(tz='UTC')
                    future_earnings = earnings_df[earnings_df.index >= today_ts]
                    if not future_earnings.empty:
                        earnings_date = future_earnings.index.min()
            except Exception:
                pass
                    
        if earnings_date is not None:
            if isinstance(earnings_date, str):
                parsed_date = pd.to_datetime(earnings_date).date()
            elif isinstance(earnings_date, (datetime, pd.Timestamp)):
                parsed_date = earnings_date.date()
            else:
                parsed_date = None

            if parsed_date:
                today = datetime.now(timezone.utc).date()
                delta_days = (parsed_date - today).days
                if delta_days >= 0:
                    return delta_days
    except Exception:
        pass
        
    return None

def process_single_ticker(ticker):
    # Jitter to stagger initial thread execution and prevent immediate rate limit wall
    time.sleep(random.uniform(0.1, 1.5))
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            ticker_obj = yf.Ticker(ticker)
            
            days_to_earnings = get_days_to_earnings(ticker_obj)
            earnings_flag = f"{days_to_earnings} Days" if days_to_earnings is not None else "N/A"

            df = ticker_obj.history(period=YF_PERIOD, interval=YF_INTERVAL)
            
            if df.empty or len(df) < MIN_HISTORY_DAYS:
                return None
                
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            df = df.dropna(subset=['Close', 'High', 'Low', 'Volume'])
            if len(df) < MIN_HISTORY_DAYS:
                return None

            close = df['Close']
            high = df['High']
            low = df['Low']
            volume = df['Volume']
            
            if volume.iloc[-1] == 0 or volume.iloc[-5:].mean() == 0:
                return None
            
            # 1. Liquidity Check
            adv = volume.rolling(window=ADV_WINDOW).mean().iloc[-1]
            if adv < ADV_MIN_LIMIT:
                return None

            current_price = close.iloc[-1]

            # 2. Trend Direction
            ema_fast = ta.trend.ema_indicator(close, window=EMA_FAST_WINDOW, fillna=False).iloc[-1]
            ema_slow = ta.trend.ema_indicator(close, window=EMA_SLOW_WINDOW, fillna=False).iloc[-1]
            
            macd_line = ta.trend.macd(close, window_slow=MACD_SLOW_WINDOW, window_fast=MACD_FAST_WINDOW, fillna=False)
            macd_signal = ta.trend.macd_signal(close, window_slow=MACD_SLOW_WINDOW, window_fast=MACD_FAST_WINDOW, window_sign=MACD_SIGNAL_WINDOW, fillna=False)
            
            current_macd = macd_line.iloc[-1]
            current_macd_signal = macd_signal.iloc[-1]
            
            # 3. Trend Strength (ADX)
            adx = ta.trend.adx(high, low, close, window=ADX_WINDOW, fillna=False).iloc[-1]
            
            # 4. Pullback / Consolidation (RSI)
            rsi = ta.momentum.rsi(close, window=RSI_WINDOW, fillna=False).iloc[-1]
            
            # 5. Momentum Trigger (Slow Stochastic Oscillator 14, 3, 3)
            stoch = ta.momentum.StochasticOscillator(high=high, low=low, close=close, window=STOCH_WINDOW, fillna=False)
            fast_k = stoch.stoch()
            
            slow_k = fast_k.rolling(window=STOCH_SMOOTH_WINDOW).mean()
            slow_d = slow_k.rolling(window=STOCH_SMOOTH_WINDOW).mean()
            
            current_k = slow_k.iloc[-1]
            current_d = slow_d.iloc[-1]

            # Logic Evaluation
            cond_trend = (current_price > ema_fast) and (current_price > ema_slow)
            cond_macd = (current_macd > MACD_MIN_LIMIT) and (current_macd > current_macd_signal)
            cond_adx = (adx > ADX_MIN_LIMIT)
            cond_rsi = (RSI_MIN_LIMIT <= rsi <= RSI_MAX_LIMIT)
            cond_stoch = (current_k > current_d) and (STOCH_MIN_LIMIT < current_k <= STOCH_MAX_LIMIT) and (current_d > STOCH_MIN_LIMIT)

            if cond_trend and cond_macd and cond_adx and cond_rsi and cond_stoch:
                return {
                    TICKER_COLUMN_NAME: ticker,
                    "Earnings_Due_In": earnings_flag
                }
                
            return None # Processed successfully but didn't meet criteria
            
        except Exception as e:
            err_msg = str(e).lower()
            if "rate limited" in err_msg or "429" in err_msg or "401" in err_msg or "unauthorized" in err_msg:
                time.sleep((2 ** attempt) + random.uniform(0.5, 2.0)) # Exponential backoff
                continue
            else:
                print(f"Error processing {ticker}: {str(e)}")
                return None
                
    print(f"Failed to process {ticker} after {max_retries} attempts due to rate limits.")
    return None

def filter_stocks(tickers):
    matching_tickers = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_single_ticker, ticker): ticker for ticker in tickers}
        
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result is not None:
                matching_tickers.append(result)
                
    return matching_tickers

def save_results(results_list, output_path):
    if not results_list:
        return
    df = pd.DataFrame(results_list)
    df.to_csv(output_path, index=False)
    print(f"\nResults successfully saved to: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Technical Analysis Pre-filter Engine for Stocks using Trend, RSI, MACD, ADX, Slow Stochastics, and Corporate Event Tagging."
    )
    parser.add_argument(
        "-input-file", 
        type=str, 
        default=DEFAULT_INPUT_CSV_PATH, 
        help="Path to the input CSV file containing stock tickers."
    )
    parser.add_argument(
        "-ticker", 
        type=str, 
        default="", 
        help="Comma-separated stock codes to scan directly via CLI (overrides input-file if provided)."
    )
    parser.add_argument(
        "-output", 
        type=str, 
        default=DEFAULT_OUTPUT_CSV_PATH, 
        help="Path to the output CSV file where results will be saved."
    )

    args = parser.parse_args()

    ticker_list = []

    if args.ticker and args.ticker.strip():
        ticker_list = [t.strip() for t in args.ticker.split(",") if t.strip()]
        print(f"Using {len(ticker_list)} tickers provided via CLI argument.")
    else:
        print(f"Reading tickers from input file: {args.input_file}...")
        ticker_list = get_ticker_list_from_file(args.input_file)

    print(f"Starting scan for {len(ticker_list)} tickers using {MAX_WORKERS} concurrent threads...")
    results = filter_stocks(ticker_list)
    
    print("\n--- Scan Complete ---")
    print(f"Tickers meeting all technical requirements ({len(results)} found):")
    for item in results:
        print(f"{item[TICKER_COLUMN_NAME]} | Earnings Due In: {item['Earnings_Due_In']}")
        
    if results:
        save_results(results, args.output)
    else:
        print("\nNo tickers matched the criteria. No output file generated.")