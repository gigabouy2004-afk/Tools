import pandas as pd
import ta
import yfinance as yf
from datetime import datetime
import os
import argparse
import sys
import time

# ============================================================================== 
# V7 - MOMENTUM SCANNER WITH VOLUME + WEEKLY TREND FILTERS + PRESETS + BACKTEST
# ==============================================================================

EMA_FAST_PERIOD = 50
EMA_SLOW_PERIOD = 200
ADX_PERIOD = 14
RSI_PERIOD = 14
ATR_PERIOD = 14
STOCH_K_PERIOD = 9
STOCH_D_PERIOD = 6
WEEKLY_EMA_FAST = 20
WEEKLY_EMA_SLOW = 50
VOLUME_LOOKBACK = 20

BALANCED_CONFIG = {
    "adx_trend_strong": 20.0,
    "adx_extreme": 50.0,
    "rsi_overbought": 78.0,
    "stoch_oversold": 30.0,
    "stoch_overbought": 80.0,
    "atr_safe_mult": 2.2,
    "atr_ext_mult": 3.0,
    "volume_mult": 1.2,
}

PRESETS = {
    "conservative": {
        **BALANCED_CONFIG,
        "adx_trend_strong": 25.0,
        "rsi_overbought": 75.0,
        "stoch_oversold": 20.0,
        "atr_safe_mult": 1.8,
        "atr_ext_mult": 2.5,
        "volume_mult": 1.4,
    },
    "balanced": BALANCED_CONFIG,
    "aggressive": {
        **BALANCED_CONFIG,
        "adx_trend_strong": 18.0,
        "rsi_overbought": 80.0,
        "stoch_oversold": 35.0,
        "atr_safe_mult": 2.5,
        "atr_ext_mult": 3.5,
        "volume_mult": 1.0,
    },
}

DEFAULT_INPUT_CSV = "D:\\Tools\\00_StockCodeMaster\\02_Stock\\01-07-US_Common_Stocks_Master_Library.csv"
DEFAULT_OUTPUT_CSV = os.path.abspath(os.path.join(os.path.dirname(__file__), "output", "Live_Scanner_v7_Execution_log.csv"))
DEFAULT_BACKTEST_CSV = os.path.abspath(os.path.join(os.path.dirname(__file__), "output", "Live_Scanner_v7_backtest.csv"))
DEFAULT_FALLBACK_WATCHLIST = ["MU"]

STATUS_BUY_SIGNAL = "BUY SIGNAL"
STATUS_WATCHLIST = "WATCHLIST"
STATUS_HOLD = "HOLD"
STATUS_DO_NOT_BUY = "DO NOT BUY"
STATUS_IGNORE = "IGNORE"
STATUS_ERROR = "ERROR/SKIPPED"

SORT_ORDER_PRECEDENCE = [STATUS_BUY_SIGNAL, STATUS_WATCHLIST, STATUS_HOLD, STATUS_DO_NOT_BUY, STATUS_IGNORE, STATUS_ERROR]

MSG_NO_TREND = "No macro uptrend. Price below EMA50 or EMA50 below EMA200."
MSG_NO_WEEKLY_TREND = "Weekly trend not aligned."
MSG_EXTREME_TOP = "Hyper-extended top!"
MSG_WAIT_PULLBACK = "Strong trend, but slightly extended. Wait for a pullback to EMA50."
MSG_BUY_TRIGGER = "Macro trend aligned, pullback completed, stochastic crossed up, and volume confirmed."
MSG_HOLD_TREND = "In a healthy upward phase. No new entries, but no exit triggers yet."
MSG_LOW_VOLUME = "Volume is not confirming the move."


def get_config(preset_name: str = "balanced") -> dict:
    preset_key = (preset_name or "balanced").lower()
    if preset_key not in PRESETS:
        preset_key = "balanced"
    return PRESETS[preset_key].copy()


def build_weekly_data(df: pd.DataFrame) -> pd.DataFrame:
    weekly = df.resample("W").agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()
    weekly["weekly_ema_20"] = ta.trend.ema_indicator(weekly["close"], window=WEEKLY_EMA_FAST)
    weekly["weekly_ema_50"] = ta.trend.ema_indicator(weekly["close"], window=WEEKLY_EMA_SLOW)
    return weekly


def evaluate_frame(df: pd.DataFrame, ticker_symbol: str, config: dict) -> dict:
    if df.empty or len(df) < EMA_SLOW_PERIOD:
        return {"ticker": ticker_symbol, "status": STATUS_ERROR, "message": f"Insufficient history (Needs {EMA_SLOW_PERIOD} daily candles)."}

    frame = df.copy()
    frame.columns = [col.lower() for col in frame.columns]

    if "close" not in frame.columns or "high" not in frame.columns or "low" not in frame.columns:
        return {"ticker": ticker_symbol, "status": STATUS_ERROR, "message": "Missing OHLC data."}

    if frame['close'].isna().all():
        return {"ticker": ticker_symbol, "status": STATUS_ERROR, "message": "No price data available."}

    weekly_df = build_weekly_data(frame)
    if weekly_df.empty or len(weekly_df) < WEEKLY_EMA_SLOW:
        weekly_df = None

    frame['ema_50'] = ta.trend.ema_indicator(frame['close'], window=EMA_FAST_PERIOD)
    frame['ema_200'] = ta.trend.ema_indicator(frame['close'], window=EMA_SLOW_PERIOD)

    if frame['ema_200'].isna().all():
        return {"ticker": ticker_symbol, "status": STATUS_ERROR, "message": "EMA200 calculation generated insufficient historical data."}

    macd_obj = ta.trend.MACD(frame['close'])
    frame['macd'] = macd_obj.macd()
    frame['macd_signal'] = macd_obj.macd_signal()

    frame['adx'] = ta.trend.adx(frame['high'], frame['low'], frame['close'], window=ADX_PERIOD)
    frame['rsi'] = ta.momentum.rsi(frame['close'], window=RSI_PERIOD)
    frame['atr'] = ta.volatility.average_true_range(frame['high'], frame['low'], frame['close'], window=ATR_PERIOD)
    frame['stoch_k'] = ta.momentum.stoch(frame['high'], frame['low'], frame['close'], window=STOCH_K_PERIOD)
    frame['stoch_d'] = ta.momentum.stoch_signal(frame['high'], frame['low'], frame['close'], window=STOCH_K_PERIOD, smooth_window=STOCH_D_PERIOD)

    latest = frame.iloc[-1]
    prev = frame.iloc[-2]

    weekly_latest = None
    weekly_ema_20 = None
    weekly_ema_50 = None
    weekly_price = None
    if weekly_df is not None:
        weekly_latest = weekly_df.iloc[-1]
        weekly_ema_20 = float(weekly_latest['weekly_ema_20']) if not pd.isna(weekly_latest['weekly_ema_20']) else None
        weekly_ema_50 = float(weekly_latest['weekly_ema_50']) if not pd.isna(weekly_latest['weekly_ema_50']) else None
        weekly_price = float(weekly_latest['close']) if not pd.isna(weekly_latest['close']) else None

    if 'volume' in frame.columns and len(frame) >= VOLUME_LOOKBACK:
        volume_series = frame['volume'].fillna(0)
        volume_avg_20 = float(volume_series.iloc[-VOLUME_LOOKBACK:].mean())
        current_volume = float(volume_series.iloc[-1])
    else:
        volume_avg_20 = None
        current_volume = None

    metrics = {
        "ticker": ticker_symbol,
        "price": round(float(latest['close']), 2),
        "ema_50": round(float(latest['ema_50']), 2) if not pd.isna(latest['ema_50']) else None,
        "ema_200": round(float(latest['ema_200']), 2) if not pd.isna(latest['ema_200']) else None,
        "macd": round(float(latest['macd']), 3) if not pd.isna(latest['macd']) else None,
        "macd_signal": round(float(latest['macd_signal']), 3) if not pd.isna(latest['macd_signal']) else None,
        "adx": round(float(latest['adx']), 2) if not pd.isna(latest['adx']) else None,
        "rsi": round(float(latest['rsi']), 2) if not pd.isna(latest['rsi']) else None,
        "atr": round(float(latest['atr']), 3) if not pd.isna(latest['atr']) else None,
        "stoch_k": round(float(latest['stoch_k']), 2) if not pd.isna(latest['stoch_k']) else None,
        "stoch_d": round(float(latest['stoch_d']), 2) if not pd.isna(latest['stoch_d']) else None,
        "volume": round(current_volume, 2) if current_volume is not None else None,
        "volume_avg_20": round(volume_avg_20, 2) if volume_avg_20 is not None else None,
        "weekly_ema_20": round(weekly_ema_20, 2) if weekly_ema_20 is not None else None,
        "weekly_ema_50": round(weekly_ema_50, 2) if weekly_ema_50 is not None else None,
        "weekly_price": round(weekly_price, 2) if weekly_price is not None else None,
    }

    if metrics["ema_50"] is None or metrics["ema_200"] is None:
        return {**metrics, **{"status": STATUS_ERROR, "message": "Crucial baseline indicators generated null values."}}

    price_distance_from_ema50 = metrics["price"] - metrics["ema_50"]
    macro_trend_ok = metrics["price"] > metrics["ema_50"] > metrics["ema_200"]
    weekly_trend_ok = False
    if weekly_ema_20 is not None and weekly_ema_50 is not None and weekly_price is not None:
        weekly_trend_ok = weekly_price > weekly_ema_20 > weekly_ema_50

    volume_confirmed = True
    if current_volume is not None and volume_avg_20 is not None:
        volume_confirmed = current_volume >= (volume_avg_20 * config.get("volume_mult", BALANCED_CONFIG["volume_mult"]))

    is_momentum_strong = (latest['macd'] > latest['macd_signal']) and (latest['macd'] > 0) and (latest['adx'] > config.get("adx_trend_strong", BALANCED_CONFIG["adx_trend_strong"]))

    reasons_for_top = []
    if price_distance_from_ema50 > (config.get("atr_ext_mult", BALANCED_CONFIG["atr_ext_mult"]) * metrics["atr"]):
        reasons_for_top.append(f"Price too far from EMA50 (Dist: {price_distance_from_ema50:.2f} > Max: {config.get('atr_ext_mult', BALANCED_CONFIG['atr_ext_mult']) * metrics['atr']:.2f})")
    if latest['rsi'] > config.get("rsi_overbought", BALANCED_CONFIG["rsi_overbought"]):
        reasons_for_top.append(f"RSI Exhausted ({metrics['rsi']:.2f} > {config.get('rsi_overbought', BALANCED_CONFIG['rsi_overbought'])})")
    if latest['adx'] > config.get("adx_extreme", BALANCED_CONFIG["adx_extreme"]):
        reasons_for_top.append(f"ADX Trend Hyper-Extended ({metrics['adx']:.2f} > {config.get('adx_extreme', BALANCED_CONFIG['adx_extreme'])})")

    signal_score = 0
    if macro_trend_ok:
        signal_score += 2
    if weekly_trend_ok:
        signal_score += 2
    if volume_confirmed:
        signal_score += 2
    if is_momentum_strong:
        signal_score += 2

    if not macro_trend_ok:
        metrics.update({"status": STATUS_IGNORE, "message": MSG_NO_TREND, "signal_score": signal_score})
        return metrics

    if weekly_df is not None and not weekly_trend_ok:
        metrics.update({"status": STATUS_IGNORE, "message": MSG_NO_WEEKLY_TREND, "signal_score": signal_score})
        return metrics

    if reasons_for_top:
        signal_score -= 3
        combined_reason_msg = f"{MSG_EXTREME_TOP} Reasons: " + " | ".join(reasons_for_top)
        metrics.update({"status": STATUS_DO_NOT_BUY, "message": combined_reason_msg, "signal_score": signal_score})
        return metrics

    if not volume_confirmed:
        signal_score -= 1
        metrics.update({"status": STATUS_WATCHLIST, "message": MSG_LOW_VOLUME, "signal_score": signal_score})
        return metrics

    stoch_crossed_up = (prev['stoch_k'] <= prev['stoch_d']) and (latest['stoch_k'] > latest['stoch_d'])
    stoch_is_oversold = latest['stoch_k'] < config.get("stoch_oversold", BALANCED_CONFIG["stoch_oversold"])
    price_in_safe_buy_zone = price_distance_from_ema50 <= (config.get("atr_safe_mult", BALANCED_CONFIG["atr_safe_mult"]) * metrics["atr"])

    if is_momentum_strong and price_in_safe_buy_zone and stoch_is_oversold and stoch_crossed_up:
        signal_score += 3
        metrics.update({"status": STATUS_BUY_SIGNAL, "message": MSG_BUY_TRIGGER, "signal_score": signal_score})
    elif is_momentum_strong and not price_in_safe_buy_zone:
        signal_score += 1
        metrics.update({"status": STATUS_WATCHLIST, "message": f"{MSG_WAIT_PULLBACK} (Dist from EMA50: {price_distance_from_ema50:.2f})", "signal_score": signal_score})
    else:
        metrics.update({"status": STATUS_HOLD, "message": MSG_HOLD_TREND, "signal_score": signal_score})

    return metrics


def evaluate_stock_momentum(ticker_symbol: str, config: dict | None = None) -> dict:
    if ticker_symbol.startswith("XNSE"):
        ticker_symbol = ticker_symbol[4:] + ".NS"

    config = config or BALANCED_CONFIG
    result_template = {
        "ticker": ticker_symbol,
        "status": STATUS_ERROR,
        "message": "",
        "summary_message": "",
        "price": None,
        "ema_50": None,
        "ema_200": None,
        "macd": None,
        "macd_signal": None,
        "adx": None,
        "rsi": None,
        "atr": None,
        "stoch_k": None,
        "stoch_d": None,
        "volume": None,
        "volume_avg_20": None,
        "weekly_ema_20": None,
        "weekly_ema_50": None,
        "weekly_price": None,
        "signal_score": None,
    }

    try:
        ticker_data = yf.Ticker(ticker_symbol)
        df = ticker_data.history(period="5y", interval="1d", prepost=True)
        if df.empty or len(df) < EMA_SLOW_PERIOD:
            result_template["message"] = f"Insufficient history (Needs {EMA_SLOW_PERIOD} daily candles)."
            return result_template

        df.columns = [col.lower() for col in df.columns]

        live_price = None
        try:
            info = ticker_data.info
            post_market = info.get('postMarketPrice')
            pre_market = info.get('preMarketPrice')
            if post_market and post_market > 0:
                live_price = post_market
            elif pre_market and pre_market > 0:
                live_price = pre_market

            if not live_price:
                minute_df = ticker_data.history(period="1d", interval="1m", prepost=True)
                if not minute_df.empty:
                    live_price = minute_df['close'].iloc[-1]
        except Exception:
            live_price = None

        if live_price and not pd.isna(live_price):
            df.loc[df.index[-1], 'close'] = live_price

        result = evaluate_frame(df, ticker_symbol, config)
        result["summary_message"] = ""
        return result

    except Exception as e:
        result_template["message"] = f"Skipped (Internal Error: {str(e)})"
        return result_template


def run_backtest(watchlist: list, config: dict, output_path: str, holding_period: int = 5) -> pd.DataFrame:
    results = []
    for ticker in watchlist:
        try:
            ticker_data = yf.Ticker(ticker)
            df = ticker_data.history(period="3y", interval="1d", prepost=True)
            if df.empty or len(df) < EMA_SLOW_PERIOD + holding_period:
                continue
            df.columns = [col.lower() for col in df.columns]
            for idx in range(EMA_SLOW_PERIOD, len(df) - holding_period):
                history = df.iloc[:idx + 1].copy()
                signal = evaluate_frame(history, ticker, config)
                if signal.get("status") != STATUS_BUY_SIGNAL:
                    continue
                entry_price = signal.get("price")
                exit_price = float(df.iloc[idx + holding_period]['close'])
                return_pct = ((exit_price / entry_price) - 1) * 100 if entry_price else None
                results.append({
                    "ticker": ticker,
                    "entry_date": df.index[idx].strftime('%Y-%m-%d'),
                    "entry_price": entry_price,
                    "exit_date": df.index[idx + holding_period].strftime('%Y-%m-%d'),
                    "exit_price": round(exit_price, 2),
                    "return_pct": round(return_pct, 2) if return_pct is not None else None,
                    "signal_score": signal.get("signal_score")
                })
        except Exception:
            continue

    if results:
        summary_df = pd.DataFrame(results)
        summary_df = summary_df.sort_values(by=["return_pct"], ascending=False)
        summary_df.to_csv(output_path, index=False)
        return summary_df
    return pd.DataFrame(results)


def load_tickers_from_file(csv_path: str) -> list:
    if not csv_path or not os.path.isfile(csv_path):
        print(f" Input file target '{csv_path}' empty or missing. Falling back to default baseline watchlist...", flush=True)
        return DEFAULT_FALLBACK_WATCHLIST
    try:
        df_input = pd.read_csv(csv_path)
        found_col = [col for col in df_input.columns if col.strip().lower() in ("tickers", "ticker", "symbol")]
        if not found_col:
            print(" Error: File must contain a 'Ticker', 'Tickers' or 'Symbol' header column. Reverting to system defaults.", flush=True)
            return DEFAULT_FALLBACK_WATCHLIST
        target_column_string = found_col[0]
        tickers = df_input[target_column_string].dropna().astype(str).str.strip().str.upper().unique().tolist()
        return [t for t in tickers if t]
    except Exception as e:
        print(f" Error reading CSV file '{csv_path}': {str(e)}. Reverting to system defaults.", flush=True)
        return DEFAULT_FALLBACK_WATCHLIST


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-Day Momentum Live Scanner Engine v7")
    parser.add_argument("-c", "--codes", type=str, nargs="+", help="Direct stock codes list")
    parser.add_argument("-i", "--input", type=str, default=DEFAULT_INPUT_CSV, help="Path to input watchlist CSV file")
    parser.add_argument("-o", "--output", type=str, default=DEFAULT_OUTPUT_CSV, help="Path to output log CSV file")
    parser.add_argument("--preset", type=str, default="balanced", choices=["conservative", "balanced", "aggressive"], help="Strategy preset")
    parser.add_argument("--backtest", action="store_true", help="Run a simple historical backtest instead of the live scan")
    parser.add_argument("--backtest-output", type=str, default=DEFAULT_BACKTEST_CSV, help="Path to write backtest results")
    parser.add_argument("--holding-period", type=int, default=5, help="Number of bars to hold after a buy signal")
    parser.add_argument("--countmax", "--countMax", "--max-buys", dest="max_buys", type=int, default=5, help="Maximum number of BUY signals to collect before stopping the scan")
    args = parser.parse_args()

    config = get_config(args.preset)
    max_buy_results = max(1, args.max_buys)

    source_message = ""
    if args.codes:
        raw_list = []
        for segment in args.codes:
            raw_list.extend(segment.split(','))
        watchlist = [t.strip().upper() for t in raw_list if t.strip()]
        source_message = f"Direct Command Line Input (-c) ({len(watchlist)} Tickers Loaded)"
    else:
        watchlist = load_tickers_from_file(args.input)
        if set(watchlist) == set(DEFAULT_FALLBACK_WATCHLIST) and not os.path.isfile(args.input):
            source_message = "Default System Watchlist Baseline (Fallback)"
        else:
            source_message = f"Input CSV File (-i) -> {args.input} ({len(watchlist)} Tickers Loaded)"

    if not watchlist:
        print(" Error: Watchlist resolution produced 0 items. Exiting execution loop.", flush=True)
        sys.exit(1)

    if args.backtest:
        print("=" * 80, flush=True)
        print(" STARTING V7 BACKTEST", flush=True)
        print("=" * 80, flush=True)
        backtest_df = run_backtest(watchlist, config, args.backtest_output, holding_period=args.holding_period)
        print(backtest_df.head(20).to_string(index=False))
        print("\nBacktest complete. Results written to:", args.backtest_output)
        sys.exit(0)

    run_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    total_tickers = len(watchlist)
    initial_summary_message = (
        f"Summary | Total={total_tickers} | Scanned=0 | MaxBuy={max_buy_results} | BUY=0 | WATCHLIST=0 | HOLD=0 | DO NOT BUY=0 | IGNORE=0 | ERROR/SKIPPED=0"
    )

    print("=" * 80, flush=True)
    print(f" STARTING LIVE MOMENTUM SCANNER V7 | {run_timestamp}", flush=True)
    print(f" Watchlist Source : {source_message}", flush=True)
    print(f" Historical Log Target: {args.output}", flush=True)
    print(f" Preset : {args.preset}", flush=True)
    print("=" * 80, flush=True)
    print(initial_summary_message, flush=True)

    unordered_results = []
    counts = {STATUS_BUY_SIGNAL: 0, STATUS_WATCHLIST: 0, STATUS_HOLD: 0, STATUS_DO_NOT_BUY: 0, STATUS_IGNORE: 0, STATUS_ERROR: 0}

    for idx, ticker in enumerate(watchlist, start=1):
        print(f"({idx}/{total_tickers}) Running engine for {ticker}...", flush=True)
        data_packet = evaluate_stock_momentum(ticker, config=config)
        data_packet["timestamp"] = run_timestamp
        unordered_results.append(data_packet)
        counts[data_packet["status"]] += 1

        if data_packet["status"] == STATUS_BUY_SIGNAL and counts[STATUS_BUY_SIGNAL] >= max_buy_results:
            print(f" BUY limit reached ({max_buy_results}). Stopping further scan.", flush=True)
            break

        time.sleep(1)

    processed_tickers = len(unordered_results)
    summary_message = (
        f"Summary | Total={total_tickers} | Scanned={processed_tickers} | MaxBuy={max_buy_results} | BUY={counts[STATUS_BUY_SIGNAL]} | WATCHLIST={counts[STATUS_WATCHLIST]} | "
        f"HOLD={counts[STATUS_HOLD]} | DO NOT BUY={counts[STATUS_DO_NOT_BUY]} | IGNORE={counts[STATUS_IGNORE]} | ERROR/SKIPPED={counts[STATUS_ERROR]}"
    )

    for item in unordered_results:
        item["summary_message"] = summary_message

    summary_row = {
        "ticker": "SUMMARY",
        "timestamp": run_timestamp,
        "status": "SUMMARY",
        "message": summary_message,
        "summary_message": summary_message,
        "price": None,
        "ema_50": None,
        "ema_200": None,
        "macd": None,
        "macd_signal": None,
        "adx": None,
        "rsi": None,
        "atr": None,
        "stoch_k": None,
        "stoch_d": None,
        "volume": None,
        "volume_avg_20": None,
        "weekly_ema_20": None,
        "weekly_ema_50": None,
        "weekly_price": None,
        "signal_score": None,
    }

    rows_for_output = [summary_row] + unordered_results

    print("\n" + "=" * 80, flush=True)
    print(f" SUMMARY EXECUTION REPORT V7 | {run_timestamp}", flush=True)
    print("=" * 80, flush=True)
    print(f" Total Tickers Analyzed : {total_tickers}", flush=True)
    print(f" Tickers Scanned        : {processed_tickers}", flush=True)
    print(f" BUY SIGNAL Count       : {counts[STATUS_BUY_SIGNAL]}", flush=True)
    print(f" WATCHLIST Count        : {counts[STATUS_WATCHLIST]}", flush=True)
    print(f" HOLD Count             : {counts[STATUS_HOLD]}", flush=True)
    print(f" DO NOT BUY Count       : {counts[STATUS_DO_NOT_BUY]}", flush=True)
    print(f" IGNORE Count           : {counts[STATUS_IGNORE]}", flush=True)
    print(f" ERROR/SKIPPED Count    : {counts[STATUS_ERROR]}", flush=True)
    print("-" * 80, flush=True)
    print(f"{'CODE':<8} | {'STATUS':<12} | {'EXECUTION MESSAGE'}", flush=True)
    print("-" * 80, flush=True)

    for item in sorted(unordered_results, key=lambda x: SORT_ORDER_PRECEDENCE.index(x["status"]) if x["status"] in SORT_ORDER_PRECEDENCE else len(SORT_ORDER_PRECEDENCE)):
        print(f"{item['ticker']:<8} | {item['status']:<12} | {item['message']}", flush=True)
    print("=" * 80, flush=True)

    df_log = pd.DataFrame(rows_for_output)
    columns_order = ["ticker", "timestamp", "status", "message", "summary_message", "price", "ema_50", "ema_200", "macd", "macd_signal", "adx", "rsi", "atr", "stoch_k", "stoch_d", "volume", "volume_avg_20", "weekly_ema_20", "weekly_ema_50", "weekly_price", "signal_score"]

    for col in columns_order:
        if col not in df_log.columns:
            df_log[col] = None
    df_log = df_log[columns_order]

    try:
        if os.path.dirname(args.output):
            os.makedirs(os.path.dirname(args.output), exist_ok=True)
        file_exists = os.path.isfile(args.output)
        df_log.to_csv(args.output, mode='a', index=False, header=not file_exists)
        print(f" Historical analysis report updated successfully at:\n 💾 👉 {args.output}\n", flush=True)
    except Exception as e:
        print(f" Failed to write log data to disk: {e}", flush=True)
