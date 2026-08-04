import yfinance as yf
import pandas as pd
import ta
import time
import os
import sys
import argparse

# ==========================================
# CONFIGURATION VARIABLES (Defaults)
# ==========================================
DEFAULT_INPUT_CSV_PATH = "D:/Tools/11_Prefilter/SampleCodes.csv"
TICKER_COLUMN_NAME = "Ticker" # Column containing fully qualified stock codes
DEFAULT_OUTPUT_CSV_PATH = "D:/Tools/11_Prefilter/filtered_results.csv"

YF_PERIOD = "1y"
YF_INTERVAL = "1d"
MIN_HISTORY_DAYS = 200
API_SLEEP_TIME = 0.5

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

def filter_stocks(tickers):
    matching_tickers = []
    
    for ticker in tickers:
        try:
            df = yf.download(ticker, period=YF_PERIOD, interval=YF_INTERVAL, progress=False)
            
            if df.empty or len(df) < MIN_HISTORY_DAYS:
                continue
                
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            close = df['Close']
            high = df['High']
            low = df['Low']
            volume = df['Volume']
            
            # 1. Liquidity Check
            adv = volume.rolling(window=ADV_WINDOW).mean().iloc[-1]
            if adv < ADV_MIN_LIMIT:
                continue

            current_price = close.iloc[-1]

            # 2. Trend Direction
            ema_fast = ta.trend.ema_indicator(close, window=EMA_FAST_WINDOW, fillna=False).iloc[-1]
            ema_slow = ta.trend.ema_indicator(close, window=EMA_SLOW_WINDOW, fillna=False).iloc[-1]
            
            # MACD & Signal Line Calculation
            macd_line = ta.trend.macd(close, window_slow=MACD_SLOW_WINDOW, window_fast=MACD_FAST_WINDOW, fillna=False)
            macd_signal = ta.trend.macd_signal(close, window_slow=MACD_SLOW_WINDOW, window_fast=MACD_FAST_WINDOW, window_sign=MACD_SIGNAL_WINDOW, fillna=False)
            
            current_macd = macd_line.iloc[-1]
            current_macd_signal = macd_signal.iloc[-1]
            
            # 3. Trend Strength (ADX)
            adx = ta.trend.adx(high, low, close, window=ADX_WINDOW, fillna=False).iloc[-1]
            
            # 4. Pullback / Consolidation (RSI)
            rsi = ta.momentum.rsi(close, window=RSI_WINDOW, fillna=False).iloc[-1]
            
            # 5. Momentum Trigger (Stochastic Oscillator)
            stoch = ta.momentum.StochasticOscillator(high=high, low=low, close=close, window=STOCH_WINDOW, smooth_window=STOCH_SMOOTH_WINDOW, fillna=False)
            current_k = stoch.stoch().iloc[-1]
            current_d = stoch.stoch_signal().iloc[-1]

            # Logic Evaluation (Including MACD Line > Signal Line and MACD Line > Zero)
            cond_trend = (current_price > ema_fast) and (current_price > ema_slow)
            cond_macd = (current_macd > MACD_MIN_LIMIT) and (current_macd > current_macd_signal)
            cond_adx = (adx > ADX_MIN_LIMIT)
            cond_rsi = (RSI_MIN_LIMIT <= rsi <= RSI_MAX_LIMIT)
            cond_stoch = (current_k > current_d) and (current_k > STOCH_MIN_LIMIT) and (current_d > STOCH_MIN_LIMIT)

            if cond_trend and cond_macd and cond_adx and cond_rsi and cond_stoch:
                matching_tickers.append(ticker)
                
            time.sleep(API_SLEEP_TIME)
            
        except Exception as e:
            print(f"Error processing {ticker}: {str(e)}")
            continue
            
    return matching_tickers

def save_results(tickers, output_path):
    df = pd.DataFrame(tickers, columns=[TICKER_COLUMN_NAME])
    df.to_csv(output_path, index=False)
    print(f"\nResults successfully saved to: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Technical Analysis Pre-filter Engine for Stocks using Trend, RSI, MACD, ADX, and Stochastics."
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

    # Priority 1: If CLI provided explicit comma-separated tickers, use them
    if args.ticker and args.ticker.strip():
        ticker_list = [t.strip() for t in args.ticker.split(",") if t.strip()]
        print(f"Using {len(ticker_list)} tickers provided via CLI argument.")
    else:
        # Priority 2: Read from the input file path
        print(f"Reading tickers from input file: {args.input_file}...")
        ticker_list = get_ticker_list_from_file(args.input_file)

    print(f"Starting scan for {len(ticker_list)} tickers...")
    results = filter_stocks(ticker_list)
    
    print("\n--- Scan Complete ---")
    print(f"Tickers meeting all technical requirements ({len(results)} found):")
    for t in results:
        print(t)
        
    if results:
        save_results(results, args.output)
    else:
        print("\nNo tickers matched the criteria. No output file generated.")