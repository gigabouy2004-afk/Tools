import pandas as pd
import ta
import yfinance as yf
from datetime import datetime
import os
import argparse
import sys

# ==============================================================================
# 1. CONFIGURABLE STRATEGY CONSTANTS & PARAMETERS
# ==============================================================================
EMA_FAST_PERIOD = 50
EMA_SLOW_PERIOD = 200
ADX_PERIOD      = 14
RSI_PERIOD      = 14
ATR_PERIOD      = 14
STOCH_K_PERIOD  = 9
STOCH_D_PERIOD  = 6

# Strategy Thresholds (Configurable)
CFG_ADX_TREND_STRONG = 25.0       
CFG_ADX_EXTREME      = 50.0       
CFG_RSI_OVERBOUGHT   = 70.0       
CFG_STOCH_OVERSOLD   = 20.0       
CFG_STOCH_OVERBOUGHT  = 80.0       

# ATR Multipliers for Distance from EMA50 (Configurable)
CFG_ATR_SAFE_MULT    = 1.5        
CFG_ATR_EXT_MULT     = 2.5        

# DEFAULT SYSTEM PATHS (Used if no CLI file overrides are provided)
DEFAULT_INPUT_CSV  = "d:/Tools/07_LiveScanner/watchlist.csv"
DEFAULT_OUTPUT_CSV = "d:/Tools/07_LiveScanner/scanner_historical_log.csv"
DEFAULT_FALLBACK_WATCHLIST = ["AAPL", "NVDA", "TSLA", "MSFT", "AMD", "AMZN", "PARR"]

# ==============================================================================
# 2. CONFIGURABLE OUTPUT STATUS CODES & MESSAGES
# ==============================================================================
STATUS_IGNORE       = "IGNORE"
STATUS_DO_NOT_BUY   = "DO NOT BUY"
STATUS_WATCHLIST    = "WATCHLIST"
STATUS_BUY_SIGNAL   = "BUY SIGNAL"
STATUS_HOLD         = "HOLD"
STATUS_ERROR        = "ERROR/SKIPPED"

MSG_NO_TREND       = "No macro uptrend. Price below EMA50 or EMA50 below EMA200."
MSG_EXTREME_TOP    = "Hyper-extended top! Too far from EMA50 or Oscillators maxed out."
MSG_WAIT_PULLBACK  = "Strong trend, but slightly extended. Wait for a pullback to EMA50."
MSG_BUY_TRIGGER    = "Macro trend aligned, pullback completed, Stochastic crossed up!"
MSG_HOLD_TREND     = "In a healthy upward phase. No new entries, but no exit triggers yet."

# ==============================================================================
# 3. CORE STRATEGY PIPELINE FUNCTION
# ==============================================================================
def evaluate_stock_momentum(ticker_symbol: str) -> dict:
    result_template = {
        "ticker": ticker_symbol, "status": STATUS_ERROR, "message": "",
        "price": None, "ema_50": None, "ema_200": None, "macd": None,
        "macd_signal": None, "adx": None, "rsi": None, "atr": None,
        "stoch_k": None, "stoch_d": None
    }
    
    try:
        ticker_data = yf.Ticker(ticker_symbol)
        df = ticker_data.history(period="1y", interval="1d", prepost=True)
        
        if df.empty or len(df) < EMA_SLOW_PERIOD:
            result_template["message"] = f"Insufficient data history (Requires {EMA_SLOW_PERIOD} days)."
            return result_template

        df.columns = [col.lower() for col in df.columns]

        # Indicators
        df['ema_50'] = ta.trend.ema_indicator(df['close'], window=EMA_FAST_PERIOD)
        df['ema_200'] = ta.trend.ema_indicator(df['close'], window=EMA_SLOW_PERIOD)
        
        macd_obj = ta.trend.MACD(df['close'])
        df['macd'] = macd_obj.macd()
        df['macd_signal'] = macd_obj.macd_signal()
        
        df['adx'] = ta.trend.adx(df['high'], df['low'], df['close'], window=ADX_PERIOD)
        df['rsi'] = ta.momentum.rsi(df['close'], window=RSI_PERIOD)
        df['atr'] = ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=ATR_PERIOD)
        
        df['stoch_k'] = ta.momentum.stoch(df['high'], df['low'], df['close'], window=STOCH_K_PERIOD)
        df['stoch_d'] = ta.momentum.stoch_signal(df['high'], df['low'], df['close'], window=STOCH_K_PERIOD, smooth_window=STOCH_D_PERIOD)

        latest = df.iloc[-1]
        prev   = df.iloc[-2] 
        
        metrics = {
            "ticker": ticker_symbol, "price": round(latest['close'], 2),
            "ema_50": round(latest['ema_50'], 2), "ema_200": round(latest['ema_200'], 2),
            "macd": round(latest['macd'], 3), "macd_signal": round(latest['macd_signal'], 3),
            "adx": round(latest['adx'], 2), "rsi": round(latest['rsi'], 2),
            "atr": round(latest['atr'], 3), "stoch_k": round(latest['stoch_k'], 2),
            "stoch_d": round(latest['stoch_d'], 2)
        }

        price_distance_from_ema50 = metrics["price"] - metrics["ema_50"]

        # PHASE 1: Macro Trend Filter
        if not (metrics["price"] > metrics["ema_50"] > metrics["ema_200"]):
            metrics.update({"status": STATUS_IGNORE, "message": MSG_NO_TREND})
            return metrics

        # PHASE 2: Momentum Verification
        is_momentum_strong = (latest['macd'] > latest['macd_signal']) and (latest['macd'] > 0) and (latest['adx'] > CFG_ADX_TREND_STRONG)

        # PHASE 3: Extension Check
        is_price_hyper_extended = price_distance_from_ema50 > (CFG_ATR_EXT_MULT * metrics["atr"])
        is_oscillator_exhausted = (latest['rsi'] > CFG_RSI_OVERBOUGHT) or (latest['adx'] > CFG_ADX_EXTREME)
        
        if is_price_hyper_extended or is_oscillator_exhausted:
            metrics.update({"status": STATUS_DO_NOT_BUY, "message": f"{MSG_EXTREME_TOP} (RSI: {metrics['rsi']})"})
            return metrics

        # PHASE 4: Timing / Triggers
        stoch_crossed_up = (prev['stoch_k'] <= prev['stoch_d']) and (latest['stoch_k'] > latest['stoch_d'])
        stoch_is_oversold = latest['stoch_k'] < CFG_STOCH_OVERSOLD
        price_in_safe_buy_zone = price_distance_from_ema50 <= (CFG_ATR_SAFE_MULT * metrics["atr"])

        if is_momentum_strong and price_in_safe_buy_zone and stoch_is_oversold and stoch_crossed_up:
            metrics.update({"status": STATUS_BUY_SIGNAL, "message": MSG_BUY_TRIGGER})
        elif is_momentum_strong and not price_in_safe_buy_zone:
            metrics.update({"status": STATUS_WATCHLIST, "message": f"{MSG_WAIT_PULLBACK} (Dist: {price_distance_from_ema50:.2f})"})
        else:
            metrics.update({"status": STATUS_HOLD, "message": MSG_HOLD_TREND})
            
        return metrics

    except Exception as e:
        result_template["message"] = f"Execution Error: {str(e)}"
        return result_template

# ==============================================================================
# 4. TICKER LOADER ENGINE (CSV FILE / PARSER)
# ==============================================================================
def load_tickers_from_file(csv_path: str) -> list:
    """Reads tickers from file using standard headers. Falls back if file is missing."""
    if not csv_path or not os.path.isfile(csv_path):
        print(f"ℹ[] Input file target '{csv_path}' empty or missing. Falling back to default baseline watchlist...")
        return DEFAULT_FALLBACK_WATCHLIST
        
    try:
        df_input = pd.read_csv(csv_path)
        found_col = [col for col in df_input.columns if col.strip().lower() in ["tickers", "symbol"]]
        
        if not found_col:
            print(f"⚠️ Error: File must contain a 'Tickers' or 'Symbol' header. Using fallback watchlist.")
            return DEFAULT_FALLBACK_WATCHLIST
            
        tickers = df_input[found_col].dropna().astype(str).str.strip().upper().unique().tolist()
        return [t for t in tickers if t]
    except Exception as e:
        print(f"❌ Failed to parse input file: {e}. Using fallback watchlist.")
        return DEFAULT_FALLBACK_WATCHLIST

# ==============================================================================
# 5. CLI RUNNER PIPELINE
# ==============================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-Day Momentum Live Scanner Engine v1.2")
    
    # The 3 Explicit CLI parameters requested
    parser.add_argument("-c", "--codes", type=str, nargs="+", help="CLI 1: Direct space-separated stock tickers (e.g. -c AAPL NVDA TSLA)")
    parser.add_argument("-i", "--input", type=str, default=DEFAULT_INPUT_CSV, help="CLI 2: Path to input watchlist CSV file")
    parser.add_argument("-o", "--output", type=str, default=DEFAULT_OUTPUT_CSV, help="CLI 3: Path to historical output results log CSV file")
    
    args = parser.parse_args()

    # Determine Watchlist source logic
    source_message = ""
    if args.codes:
        watchlist = [t.strip().upper() for t in args.codes if t.strip()]
        source_message = "Direct Command Line Ticker Input (-c)"
    else:
        watchlist = load_tickers_from_file(args.input)
        if set(watchlist) == set(DEFAULT_FALLBACK_WATCHLIST) and not os.path.isfile(args.input):
            source_message = "Default System Watchlist Baseline (Fallback)"
        else:
            source_message = f"Input CSV File (-i) -> {args.input}"

    if not watchlist:
        print("❌ Error: Watchlist resolution produced 0 items. Exiting execution loop.")
        sys.exit(1)

    run_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print("=" * 80)
    print(f"🚀 STARTING LIVE MOMENTUM SCANNER | {run_timestamp}")
    print(f"📥 Watchlist Source  : {source_message}")
    print(f"💾 Historical Log Target: {args.output}")
    print("=" * 80)

    results_list = []
    counts = {STATUS_HOLD: 0, STATUS_DO_NOT_BUY: 0, STATUS_IGNORE: 0, STATUS_BUY_SIGNAL: 0, STATUS_WATCHLIST: 0, STATUS_ERROR: 0}

    # Execute calculations loop
    for ticker in watchlist:
        print(f"Running engine for {ticker}...")
        data_packet = evaluate_stock_momentum(ticker)
        data_packet["timestamp"] = run_timestamp
        results_list.append(data_packet)
        counts[data_packet["status"]] += 1

    # --- TERMINAL SUMMARY OUTPUT ---
    print("\n" + "=" * 80)
    print(f"📊 SUMMARY EXECUTION REPORT | {run_timestamp}")
    print("=" * 80)
    print(f"▶ Total Tickers Analyzed : {len(watchlist)}")
    print(f"▶ BUY SIGNAL Count       : {counts[STATUS_BUY_SIGNAL]}")
    print(f"▶ WATCHLIST Count        : {counts[STATUS_WATCHLIST]}")
    print(f"▶ HOLD Count             : {counts[STATUS_HOLD]}")
    print(f"▶ DO NOT BUY Count       : {counts[STATUS_DO_NOT_BUY]}")
    print(f"▶ IGNORE Count           : {counts[STATUS_IGNORE]}")
    print(f"▶ ERROR/SKIPPED Count    : {counts[STATUS_ERROR]}")
    print("-" * 80)
    print(f"{'CODE':<8} | {'STATUS':<12} | {'EXECUTION MESSAGE'}")
    print("-" * 80)
    for item in results_list:
        print(f"{item['ticker']:<8} | {item['status']:<12} | {item['message']}")
    print("=" * 80)
    # --- CSV FILE GENERATION ---
    df_log = pd.DataFrame(results_list)
    columns_order = ["timestamp", "ticker", "status", "message", "price", "ema_50", "ema_200", "macd", "macd_signal", "adx", "rsi", "atr", "stoch_k", "stoch_d"]
    df_log = df_log[columns_order]
    try:
        if os.path.dirname(args.output):
            os.makedirs(os.path.dirname(args.output), exist_ok=True)
        file_exists = os.path.isfile(args.output)
        df_log.to_csv(args.output, mode='a', index=False, header=not file_exists)
        print(f"💾 Historical analysis report updated successfully at:\n👉 {args.output}\n")
    except Exception as e:
        print(f"❌ Failed to write log data to disk: {e}")