import pandas as pd
import ta
import yfinance as yf
from datetime import datetime

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

# ==============================================================================
# 2. CONFIGURABLE OUTPUT STATUS MESSAGES
# ==============================================================================
MSG_NO_TREND       = "❌ [IGNORE] No macro uptrend. Price below EMA50 or EMA50 below EMA200."
MSG_EXTREME_TOP    = "🚨 [DO NOT BUY] Hyper-extended top! Too far from EMA50 or Oscillators maxed out."
MSG_WAIT_PULLBACK  = "⏳ [WATCHLIST] Strong trend, but slightly extended. Wait for a pullback to EMA50."
MSG_BUY_TRIGGER    = "🔥 [BUY SIGNAL] Macro trend aligned, pullback completed, Stochastic crossed up!"
MSG_HOLD_TREND     = "📈 [HOLD] In a healthy upward phase. No new entries, but no exit triggers yet."

# ==============================================================================
# 3. CORE STRATEGY PIPELINE FUNCTION
# ==============================================================================
def evaluate_stock_momentum(ticker_symbol: str) -> str:
    """
    Downloads live data (including pre/post market) and runs the precedence pipeline.
    """
    try:
        # Fetching daily data ('1d' interval). 'prepost=True' ensures that if the market 
        # is currently closed, the last candle includes pre/post market pricing data.
        ticker_data = yf.Ticker(ticker_symbol)
        df = ticker_data.history(period="1y", interval="1d", prepost=True)
        
        if df.empty or len(df) < EMA_SLOW_PERIOD:
            return f"⚠️ [SKIPPED] Insufficient data history for {ticker_symbol}."

        # Make column names lowercase to maintain alignment with 'ta' library expectations
        df.columns = [col.lower() for col in df.columns]

        # Indicator Calculations
        df['ema_50'] = ta.trend.ema_indicator(df['close'], window=EMA_FAST_PERIOD)
        df['ema_200'] = ta.trend.ema_indicator(df['close'], window=EMA_SLOW_PERIOD)
        
        macd_obj = ta.trend.MACD(df['close'])
        df['macd'] = macd_obj.macd()
        df['macd_signal'] = macd_obj.macd_signal()
        
        df['adx'] = ta.trend.adx(df['high'], df['low'], df['close'], window=ADX_PERIOD)
        df['rsi'] = ta.momentum.rsi(df['close'], window=RSI_PERIOD)
        df['atr'] = ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=ATR_PERIOD)
        
        # --- FIXED STOCHASTIC FUNCTIONS HERE ---
        # stoch() gives %K, stoch_signal() gives the moving average %D line
        df['stoch_k'] = ta.momentum.stoch(df['high'], df['low'], df['close'], window=STOCH_K_PERIOD)
        df['stoch_d'] = ta.momentum.stoch_signal(df['high'], df['low'], df['close'], window=STOCH_K_PERIOD, smooth_window=STOCH_D_PERIOD)

        # Isolate final rows
        latest = df.iloc[-1]
        prev   = df.iloc[-2] 
        
        current_price = latest['close']
        ema50 = latest['ema_50']
        ema200 = latest['ema_200']
        atr = latest['atr']
        
        price_distance_from_ema50 = current_price - ema50

        # PHASE 1: Macro Trend Filter
        is_macro_bullish = (current_price > ema50) and (ema50 > ema200)
        if not is_macro_bullish:
            return MSG_NO_TREND

        # PHASE 2: Momentum Verification
        is_momentum_strong = (latest['macd'] > 0) and (latest['macd'] > latest['macd_signal']) and (latest['adx'] > CFG_ADX_TREND_STRONG)

        # PHASE 3: Extension Check (The Rubber Band Filter)
        is_price_hyper_extended = price_distance_from_ema50 > (CFG_ATR_EXT_MULT * atr)
        is_oscillator_exhausted = (latest['rsi'] > CFG_RSI_OVERBOUGHT) or (latest['adx'] > CFG_ADX_EXTREME)
        
        if is_price_hyper_extended or is_oscillator_exhausted:
            return f"{MSG_EXTREME_TOP} (Price: {current_price:.2f}, EMA50: {ema50:.2f}, RSI: {latest['rsi']:.1f}, ADX: {latest['adx']:.1f})"

        # PHASE 4: Timing & Pullback Trigger Logic
        stoch_crossed_up = (prev['stoch_k'] <= prev['stoch_d']) and (latest['stoch_k'] > latest['stoch_d'])
        stoch_is_oversold = latest['stoch_k'] < CFG_STOCH_OVERSOLD
        price_in_safe_buy_zone = price_distance_from_ema50 <= (CFG_ATR_SAFE_MULT * atr)

        if is_momentum_strong and price_in_safe_buy_zone and stoch_is_oversold and stoch_crossed_up:
            return MSG_BUY_TRIGGER
        elif is_momentum_strong and not price_in_safe_buy_zone:
            return f"{MSG_WAIT_PULLBACK} (Current Distance: {price_distance_from_ema50:.2f} vs Safe Limit: {CFG_ATR_SAFE_MULT * atr:.2f})"
        else:
            return MSG_HOLD_TREND

    except Exception as e:
        return f"❌ [ERROR] Could not process {ticker_symbol}: {str(e)}"

# ==============================================================================
# 4. MULTI-STOCK LIVE SCANNER RUNNER
# ==============================================================================
if __name__ == "__main__":
    WATCHLIST = ["AAPL", "NVDA", "TSLA", "MSFT", "AMD", "AMZN", "PARR"]
    
    print("=" * 70)
    print(f"🚀 STARTING LIVE MOMENTUM SCANNER (Executed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
    print("⚠️ Includes Automatic Extended Hours Tracking (Pre/Post Market data)")
    print("=" * 70)
    
    for ticker in WATCHLIST:
        print(f"Scanning {ticker}...")
        scan_result = evaluate_stock_momentum(ticker)
        print(f" -> {scan_result}\n")
        
    print("=" * 70)
    print("✨ Scanner Loop Complete.")
    print("=" * 70)
