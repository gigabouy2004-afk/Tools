import pandas as pd
import ta
import yfinance as yf
from datetime import datetime, time as dt_time
from zoneinfo import ZoneInfo
import os
import argparse
import sys
import time

# ============================================================================== 
# VERSION 8 - MOMENTUM SCANNER WITH AUTOMATIC SESSION DETECTION + COHERENT OHLCV
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
STOCH_RECENT_LOOKBACK = 3
STOCH_RECOVERY_BUFFER = 10.0


US_MARKET_TZ = ZoneInfo("America/New_York")
PREMARKET_START = dt_time(4, 0)
REGULAR_START = dt_time(9, 30)
REGULAR_END = dt_time(16, 0)
POSTMARKET_END = dt_time(20, 0)


def get_us_market_phase(now: datetime | None = None) -> dict:
    """Return the expected US session phase without external calendar packages.

    Weekends are treated as COMPLETED. On weekdays, clock time determines the
    expected phase. Yahoo minute-bar availability is validated separately; this
    automatically handles holidays, outages and missing extended-hours data by
    falling back to completed daily candles.
    """
    now_et = now.astimezone(US_MARKET_TZ) if now else datetime.now(US_MARKET_TZ)
    current_time = now_et.time().replace(tzinfo=None)

    if now_et.weekday() >= 5:
        phase = "COMPLETED"
        effective_mode = "completed"
        reason = "Weekend; use the last completed daily candle."
    elif PREMARKET_START <= current_time < REGULAR_START:
        phase = "PREMARKET"
        effective_mode = "intraday"
        reason = "Pre-market window; rebuild today's OHLCV candle from Yahoo extended-hours minute bars."
    elif REGULAR_START <= current_time < REGULAR_END:
        phase = "REGULAR"
        effective_mode = "intraday"
        reason = "Regular US market window; rebuild today's OHLCV candle from Yahoo minute bars."
    elif REGULAR_END <= current_time < POSTMARKET_END:
        phase = "POSTMARKET"
        effective_mode = "intraday"
        reason = "Post-market window; rebuild today's OHLCV candle from regular plus extended-hours minute bars."
    else:
        phase = "COMPLETED"
        effective_mode = "completed"
        reason = "Extended-hours session is inactive; use completed daily candles."

    return {
        "phase": phase,
        "effective_mode": effective_mode,
        "market_time_et": now_et.isoformat(timespec="seconds"),
        "reason": reason,
    }


def filter_intraday_to_today(intraday_df: pd.DataFrame, now: datetime | None = None) -> pd.DataFrame:
    """Keep only bars belonging to today's US Eastern calendar date."""
    if intraday_df is None or intraday_df.empty:
        return pd.DataFrame()

    now_et = now.astimezone(US_MARKET_TZ) if now else datetime.now(US_MARKET_TZ)
    intraday = intraday_df.copy()

    try:
        index = pd.DatetimeIndex(intraday.index)
        if index.tz is None:
            index = index.tz_localize(US_MARKET_TZ)
        else:
            index = index.tz_convert(US_MARKET_TZ)
        intraday.index = index
        return intraday.loc[intraday.index.date == now_et.date()].copy()
    except Exception:
        return pd.DataFrame()


def drop_incomplete_daily_row(df: pd.DataFrame, phase: str, now: datetime | None = None) -> pd.DataFrame:
    """Remove today's Yahoo daily row while pre/regular/post-market is active."""
    if phase not in {"PREMARKET", "REGULAR", "POSTMARKET"} or df.empty:
        return df
    now_et = now.astimezone(US_MARKET_TZ) if now else datetime.now(US_MARKET_TZ)
    today = now_et.date()
    keep = [pd.Timestamp(idx).date() != today for idx in df.index]
    return df.loc[keep].copy()

BALANCED_CONFIG = {
    "adx_trend_strong": 20.0,
    "adx_extreme": 50.0,
    "rsi_overbought": 78.0,
    "stoch_oversold": 30.0,
    "stoch_overbought": 80.0,
    "atr_safe_mult": 2.2,
    "atr_ext_mult": 3.0,
    "volume_mult": 1.2,
    "stoch_recent_lookback": STOCH_RECENT_LOOKBACK,
    "stoch_recovery_buffer": STOCH_RECOVERY_BUFFER,
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
DEFAULT_OUTPUT_CSV = os.path.abspath(os.path.join(os.path.dirname(__file__), "output", "Live_Scanner_v8_Execution_log.csv"))
DEFAULT_BACKTEST_CSV = os.path.abspath(os.path.join(os.path.dirname(__file__), "output", "Live_Scanner_v8_backtest.csv"))
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
MSG_BUY_TRIGGER = "Trend aligned; recent stochastic oversold pullback has crossed upward with volume confirmation."
MSG_HOLD_TREND = "Healthy upward trend, but no fresh entry trigger."
MSG_LOW_VOLUME = "Volume is not confirming the move."


def sort_results_for_display(results: list[dict]) -> list[dict]:
    return sorted(
        results,
        key=lambda x: (
            SORT_ORDER_PRECEDENCE.index(x.get("status")) if x.get("status") in SORT_ORDER_PRECEDENCE else len(SORT_ORDER_PRECEDENCE),
            -(x.get("signal_score") or 0),
            str(x.get("ticker", "")),
        ),
    )


def normalize_date_text(date_text: str) -> str:
    parsed = pd.to_datetime(date_text, errors="coerce")
    if pd.isna(parsed):
        raise ValueError(f"Invalid date format: '{date_text}'. Use YYYY-MM-DD.")
    return parsed.strftime("%Y-%m-%d")


def build_as_of_date_list(as_of_date: str | None, as_of_dates: str | None) -> list[str | None]:
    if as_of_dates:
        normalized = []
        seen = set()
        for raw_date in as_of_dates.split(","):
            item = raw_date.strip()
            if not item:
                continue
            normalized_item = normalize_date_text(item)
            if normalized_item not in seen:
                normalized.append(normalized_item)
                seen.add(normalized_item)
        if not normalized:
            raise ValueError("--as-of-dates was provided but no valid dates were found.")
        return normalized

    if as_of_date:
        return [normalize_date_text(as_of_date)]

    return [None]


def filter_to_as_of_date(df: pd.DataFrame, as_of_date: str) -> pd.DataFrame:
    as_of_ts = pd.Timestamp(as_of_date).normalize() + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
    if getattr(df.index, "tz", None) is not None and as_of_ts.tzinfo is None:
        as_of_ts = as_of_ts.tz_localize(df.index.tz)
    return df.loc[df.index <= as_of_ts].copy()


def summarize_backtest_results(backtest_df: pd.DataFrame) -> dict:
    if backtest_df.empty:
        return {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate_pct": 0.0,
            "average_return_pct": 0.0,
            "average_win_pct": 0.0,
            "average_loss_pct": 0.0,
            "best_trade_pct": 0.0,
            "worst_trade_pct": 0.0,
            "max_drawdown_pct": 0.0,
            "top_tickers": [],
        }

    valid_returns = backtest_df["return_pct"].dropna()
    if valid_returns.empty:
        return {
            "total_trades": int(len(backtest_df)),
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate_pct": 0.0,
            "average_return_pct": 0.0,
            "average_win_pct": 0.0,
            "average_loss_pct": 0.0,
            "best_trade_pct": 0.0,
            "worst_trade_pct": 0.0,
            "max_drawdown_pct": 0.0,
            "top_tickers": [],
        }

    win_mask = valid_returns > 0
    loss_mask = valid_returns < 0
    equity_curve = 100 * (1 + valid_returns / 100).cumprod()
    running_max = equity_curve.cummax()
    drawdown = ((equity_curve / running_max) - 1) * 100

    top_tickers = (
        backtest_df.groupby("ticker")["return_pct"].mean().dropna().sort_values(ascending=False).head(10)
    )

    return {
        "total_trades": int(len(backtest_df)),
        "winning_trades": int(win_mask.sum()),
        "losing_trades": int(loss_mask.sum()),
        "win_rate_pct": round((win_mask.sum() / len(valid_returns)) * 100, 2) if len(valid_returns) else 0.0,
        "average_return_pct": round(float(valid_returns.mean()), 2),
        "average_win_pct": round(float(valid_returns[win_mask].mean()), 2) if win_mask.any() else 0.0,
        "average_loss_pct": round(float(valid_returns[loss_mask].mean()), 2) if loss_mask.any() else 0.0,
        "best_trade_pct": round(float(valid_returns.max()), 2),
        "worst_trade_pct": round(float(valid_returns.min()), 2),
        "max_drawdown_pct": round(float(drawdown.min()), 2),
        "top_tickers": [
            {"ticker": ticker, "avg_return_pct": round(float(return_pct), 2)}
            for ticker, return_pct in top_tickers.items()
        ],
    }


def get_config(preset_name: str = "balanced") -> dict:
    preset_key = (preset_name or "balanced").lower()
    if preset_key not in PRESETS:
        preset_key = "balanced"
    return PRESETS[preset_key].copy()


def build_weekly_data(df: pd.DataFrame, include_incomplete_week: bool = False) -> pd.DataFrame:
    weekly = df.resample("W-FRI").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    ).dropna()

    # During a live weekday scan, the final resampled row is an incomplete week.
    # Default to completed weeks so the weekly gate does not move intraday.
    if not include_incomplete_week and not weekly.empty:
        last_daily_date = pd.Timestamp(df.index[-1]).date()
        last_week_end = pd.Timestamp(weekly.index[-1]).date()
        if last_daily_date < last_week_end:
            weekly = weekly.iloc[:-1]

    weekly["weekly_ema_20"] = ta.trend.ema_indicator(weekly["close"], window=WEEKLY_EMA_FAST)
    weekly["weekly_ema_50"] = ta.trend.ema_indicator(weekly["close"], window=WEEKLY_EMA_SLOW)
    return weekly


def merge_intraday_session_candle(df: pd.DataFrame, intraday_df: pd.DataFrame) -> pd.DataFrame:
    """Replace/append today's daily candle using complete intraday OHLCV data."""
    if intraday_df is None or intraday_df.empty:
        return df

    intraday = intraday_df.copy()
    intraday.columns = [str(col).lower() for col in intraday.columns]
    required = {"open", "high", "low", "close"}
    if not required.issubset(intraday.columns):
        return df

    intraday = intraday.dropna(subset=["close"])
    if intraday.empty:
        return df

    candle = {
        "open": float(intraday["open"].dropna().iloc[0]),
        "high": float(intraday["high"].max()),
        "low": float(intraday["low"].min()),
        "close": float(intraday["close"].iloc[-1]),
        "volume": float(intraday["volume"].fillna(0).sum()) if "volume" in intraday.columns else 0.0,
    }

    merged = df.copy()
    session_date = pd.Timestamp(intraday.index[-1]).date()
    daily_dates = pd.Index([pd.Timestamp(idx).date() for idx in merged.index])
    matches = daily_dates == session_date

    if matches.any():
        target_idx = merged.index[matches][-1]
        for key, value in candle.items():
            if key in merged.columns:
                merged.loc[target_idx, key] = value
    else:
        new_idx = pd.Timestamp(session_date)
        if getattr(merged.index, "tz", None) is not None:
            new_idx = new_idx.tz_localize(merged.index.tz)
        row = {col: None for col in merged.columns}
        row.update({key: value for key, value in candle.items() if key in row})
        merged.loc[new_idx] = row
        merged = merged.sort_index()

    return merged


def evaluate_frame(df: pd.DataFrame, ticker_symbol: str, config: dict) -> dict:
    if df.empty or len(df) < EMA_SLOW_PERIOD:
        return {"ticker": ticker_symbol, "status": STATUS_ERROR, "message": f"Insufficient history (Needs {EMA_SLOW_PERIOD} daily candles)."}

    frame = df.copy()
    frame.columns = [str(col).lower() for col in frame.columns]

    required_columns = {"close", "high", "low"}
    if not required_columns.issubset(frame.columns):
        return {"ticker": ticker_symbol, "status": STATUS_ERROR, "message": "Missing OHLC data."}
    if frame["close"].isna().all():
        return {"ticker": ticker_symbol, "status": STATUS_ERROR, "message": "No price data available."}

    weekly_df = build_weekly_data(frame, include_incomplete_week=False)
    if weekly_df.empty or len(weekly_df) < WEEKLY_EMA_SLOW:
        weekly_df = None

    frame["ema_50"] = ta.trend.ema_indicator(frame["close"], window=EMA_FAST_PERIOD)
    frame["ema_200"] = ta.trend.ema_indicator(frame["close"], window=EMA_SLOW_PERIOD)
    macd_obj = ta.trend.MACD(frame["close"])
    frame["macd"] = macd_obj.macd()
    frame["macd_signal"] = macd_obj.macd_signal()
    frame["macd_hist"] = macd_obj.macd_diff()
    frame["adx"] = ta.trend.adx(frame["high"], frame["low"], frame["close"], window=ADX_PERIOD)
    frame["rsi"] = ta.momentum.rsi(frame["close"], window=RSI_PERIOD)
    frame["atr"] = ta.volatility.average_true_range(frame["high"], frame["low"], frame["close"], window=ATR_PERIOD)
    frame["stoch_k"] = ta.momentum.stoch(frame["high"], frame["low"], frame["close"], window=STOCH_K_PERIOD)
    frame["stoch_d"] = ta.momentum.stoch_signal(
        frame["high"], frame["low"], frame["close"], window=STOCH_K_PERIOD, smooth_window=STOCH_D_PERIOD
    )

    latest = frame.iloc[-1]
    prev = frame.iloc[-2]
    crucial = ["ema_50", "ema_200", "macd", "macd_signal", "macd_hist", "adx", "rsi", "atr", "stoch_k", "stoch_d"]
    if any(pd.isna(latest[name]) for name in crucial):
        return {"ticker": ticker_symbol, "status": STATUS_ERROR, "message": "Crucial indicators generated null values."}

    weekly_ema_20 = weekly_ema_50 = weekly_price = None
    if weekly_df is not None:
        weekly_latest = weekly_df.iloc[-1]
        weekly_ema_20 = None if pd.isna(weekly_latest["weekly_ema_20"]) else float(weekly_latest["weekly_ema_20"])
        weekly_ema_50 = None if pd.isna(weekly_latest["weekly_ema_50"]) else float(weekly_latest["weekly_ema_50"])
        weekly_price = None if pd.isna(weekly_latest["close"]) else float(weekly_latest["close"])

    current_volume = volume_avg_20 = None
    if "volume" in frame.columns and len(frame) >= VOLUME_LOOKBACK + 1:
        volume_series = frame["volume"].fillna(0)
        current_volume = float(volume_series.iloc[-1])
        # Exclude the current candle from its own comparison baseline.
        volume_avg_20 = float(volume_series.iloc[-VOLUME_LOOKBACK - 1:-1].mean())

    metrics = {
        "ticker": ticker_symbol,
        "price": round(float(latest["close"]), 2),
        "ema_50": round(float(latest["ema_50"]), 2),
        "ema_200": round(float(latest["ema_200"]), 2),
        "macd": round(float(latest["macd"]), 3),
        "macd_signal": round(float(latest["macd_signal"]), 3),
        "macd_hist": round(float(latest["macd_hist"]), 3),
        "adx": round(float(latest["adx"]), 2),
        "rsi": round(float(latest["rsi"]), 2),
        "atr": round(float(latest["atr"]), 3),
        "stoch_k": round(float(latest["stoch_k"]), 2),
        "stoch_d": round(float(latest["stoch_d"]), 2),
        "volume": round(current_volume, 2) if current_volume is not None else None,
        "volume_avg_20": round(volume_avg_20, 2) if volume_avg_20 is not None else None,
        "weekly_ema_20": round(weekly_ema_20, 2) if weekly_ema_20 is not None else None,
        "weekly_ema_50": round(weekly_ema_50, 2) if weekly_ema_50 is not None else None,
        "weekly_price": round(weekly_price, 2) if weekly_price is not None else None,
    }

    price_distance_from_ema50 = float(latest["close"] - latest["ema_50"])
    macro_trend_ok = bool(latest["close"] > latest["ema_50"] > latest["ema_200"])
    weekly_trend_ok = False
    if weekly_ema_20 is not None and weekly_ema_50 is not None and weekly_price is not None:
        weekly_trend_ok = bool(weekly_price > weekly_ema_20 > weekly_ema_50)

    macd_bullish = bool(latest["macd"] > latest["macd_signal"])
    macd_above_zero = bool(latest["macd"] > 0)
    macd_improving = bool(latest["macd_hist"] > prev["macd_hist"])
    trend_strength_ok = bool(latest["adx"] >= config.get("adx_trend_strong", BALANCED_CONFIG["adx_trend_strong"]))
    established_momentum = macd_bullish and macd_above_zero and trend_strength_ok
    recovering_momentum = macd_bullish and macd_improving and trend_strength_ok

    volume_confirmed = True
    if current_volume is not None and volume_avg_20 is not None and volume_avg_20 > 0:
        volume_confirmed = current_volume >= volume_avg_20 * config.get("volume_mult", BALANCED_CONFIG["volume_mult"])

    atr_value = float(latest["atr"])
    price_in_safe_buy_zone = price_distance_from_ema50 <= config.get("atr_safe_mult", BALANCED_CONFIG["atr_safe_mult"]) * atr_value
    price_hyper_extended = price_distance_from_ema50 > config.get("atr_ext_mult", BALANCED_CONFIG["atr_ext_mult"]) * atr_value
    rsi_exhausted = latest["rsi"] > config.get("rsi_overbought", BALANCED_CONFIG["rsi_overbought"])
    adx_extreme = latest["adx"] > config.get("adx_extreme", BALANCED_CONFIG["adx_extreme"])

    lookback = max(2, int(config.get("stoch_recent_lookback", STOCH_RECENT_LOOKBACK)))
    stoch_threshold = config.get("stoch_oversold", BALANCED_CONFIG["stoch_oversold"])
    stoch_recovery_ceiling = stoch_threshold + config.get("stoch_recovery_buffer", STOCH_RECOVERY_BUFFER)
    stoch_recently_oversold = bool(frame["stoch_k"].iloc[-lookback:].min() < stoch_threshold)
    stoch_crossed_up = bool(prev["stoch_k"] <= prev["stoch_d"] and latest["stoch_k"] > latest["stoch_d"])
    stoch_recovery_trigger = stoch_recently_oversold and stoch_crossed_up and latest["stoch_k"] <= stoch_recovery_ceiling

    signal_score = 0
    signal_score += 2 if macro_trend_ok else 0
    signal_score += 2 if weekly_trend_ok else 0
    signal_score += 2 if established_momentum else (1 if recovering_momentum else 0)
    signal_score += 1 if volume_confirmed else 0
    signal_score += 2 if stoch_recovery_trigger else 0
    signal_score += 1 if price_in_safe_buy_zone else 0

    if not macro_trend_ok:
        metrics.update({"status": STATUS_IGNORE, "message": MSG_NO_TREND, "signal_score": signal_score})
        return metrics

    if weekly_df is not None and not weekly_trend_ok:
        metrics.update({"status": STATUS_IGNORE, "message": MSG_NO_WEEKLY_TREND, "signal_score": signal_score})
        return metrics

    # Exhaustion requires confluence. ADX alone is not a top signal.
    exhaustion_reasons = []
    if price_hyper_extended:
        exhaustion_reasons.append("price is hyper-extended from EMA50")
    if rsi_exhausted:
        exhaustion_reasons.append("RSI is exhausted")
    if adx_extreme and not macd_improving:
        exhaustion_reasons.append("ADX is extreme while MACD histogram is weakening")

    if len(exhaustion_reasons) >= 2:
        signal_score -= 3
        metrics.update({
            "status": STATUS_DO_NOT_BUY,
            "message": f"{MSG_EXTREME_TOP} Reasons: " + " | ".join(exhaustion_reasons),
            "signal_score": signal_score,
        })
        return metrics

    if established_momentum and price_in_safe_buy_zone and stoch_recovery_trigger:
        if volume_confirmed:
            signal_score += 2
            status, message = STATUS_BUY_SIGNAL, MSG_BUY_TRIGGER
        else:
            status, message = STATUS_WATCHLIST, "Valid pullback recovery; waiting for volume confirmation."
    elif established_momentum and stoch_recently_oversold and not stoch_crossed_up:
        status, message = STATUS_WATCHLIST, "Strong trend with an oversold pullback; waiting for stochastic reversal."
    elif established_momentum and not price_in_safe_buy_zone:
        status = STATUS_WATCHLIST
        message = f"{MSG_WAIT_PULLBACK} (Dist from EMA50: {price_distance_from_ema50:.2f})"
    elif recovering_momentum and price_in_safe_buy_zone:
        status, message = STATUS_WATCHLIST, "Momentum is recovering near EMA50; trend confirmation is not yet fully established."
    elif established_momentum:
        status, message = STATUS_HOLD, MSG_HOLD_TREND
    else:
        status, message = STATUS_HOLD, "Macro trend is intact, but MACD/ADX momentum is not aligned for a fresh entry."

    metrics.update({"status": status, "message": message, "signal_score": signal_score})
    return metrics


def evaluate_stock_momentum(
    ticker_symbol: str,
    config: dict | None = None,
    history_years: int = 5,
    as_of_date: str | None = None,
    live_candle_mode: str = "auto",
) -> dict:
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
        "macd_hist": None,
        "adx": None,
        "rsi": None,
        "atr": None,
        "stoch_k": None,
        "stoch_d": None,
        "as_of_date": as_of_date,
        "volume": None,
        "volume_avg_20": None,
        "weekly_ema_20": None,
        "weekly_ema_50": None,
        "weekly_price": None,
        "signal_score": None,
        "market_phase": None,
        "data_mode": None,
        "market_time_et": None,
        "data_note": None,
    }

    try:
        ticker_data = yf.Ticker(ticker_symbol)
        history_period = f"{max(1, int(history_years))}y"
        df = ticker_data.history(period=history_period, interval="1d", prepost=True)
        if df.empty or len(df) < EMA_SLOW_PERIOD:
            result_template["message"] = f"Insufficient history (Needs {EMA_SLOW_PERIOD} daily candles)."
            return result_template

        df.columns = [col.lower() for col in df.columns]

        if as_of_date:
            df = filter_to_as_of_date(df, as_of_date)
            if df.empty or len(df) < EMA_SLOW_PERIOD:
                result_template["message"] = f"Insufficient history up to {as_of_date} (Needs {EMA_SLOW_PERIOD} daily candles)."
                return result_template

        market_context = {
            "phase": "HISTORICAL",
            "effective_mode": "completed",
            "market_time_et": None,
            "reason": "Historical as-of-date evaluation uses completed candles.",
        }

        if as_of_date is None:
            market_context = get_us_market_phase()
            requested_mode = (live_candle_mode or "auto").lower()
            effective_mode = market_context["effective_mode"] if requested_mode == "auto" else requested_mode

            # Avoid mixing Yahoo's partially formed daily row with a separately rebuilt
            # extended-hours candle. Remove today's daily row first, then append one
            # internally consistent OHLCV candle from minute data.
            if effective_mode == "intraday":
                df = drop_incomplete_daily_row(df, market_context["phase"])
                try:
                    minute_df = ticker_data.history(period="1d", interval="1m", prepost=True)
                    today_minute_df = filter_intraday_to_today(minute_df)
                    if not today_minute_df.empty:
                        df = merge_intraday_session_candle(df, today_minute_df)
                    else:
                        market_context["reason"] += " No minute bars for today's US session; fell back to the latest completed daily candle."
                        effective_mode = "completed"
                except Exception as exc:
                    market_context["reason"] += f" Minute-data rebuild failed ({exc}); fell back to completed daily candles."
                    effective_mode = "completed"
            else:
                df = drop_incomplete_daily_row(df, market_context["phase"])

            market_context["effective_mode"] = effective_mode

        result = evaluate_frame(df, ticker_symbol, config)
        result["summary_message"] = ""
        result["as_of_date"] = as_of_date
        result["market_phase"] = market_context["phase"]
        result["data_mode"] = market_context["effective_mode"]
        result["market_time_et"] = market_context["market_time_et"]
        result["data_note"] = market_context["reason"]
        return result

    except Exception as e:
        result_template["message"] = f"Skipped (Internal Error: {str(e)})"
        return result_template


def run_backtest(
    watchlist: list,
    config: dict,
    output_path: str,
    holding_period: int = 5,
    history_years: int = 3,
) -> tuple[pd.DataFrame, dict]:
    results = []
    history_period = f"{max(1, int(history_years))}y"
    for ticker in watchlist:
        try:
            ticker_data = yf.Ticker(ticker)
            df = ticker_data.history(period=history_period, interval="1d", prepost=True)
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
        summary_df = summary_df.sort_values(by=["return_pct"], ascending=False).reset_index(drop=True)
        if os.path.dirname(output_path):
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
        summary_df.to_csv(output_path, index=False)
        return summary_df, summarize_backtest_results(summary_df)
    return pd.DataFrame(results), summarize_backtest_results(pd.DataFrame(results))


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
    parser = argparse.ArgumentParser(description="Multi-Day Momentum Live Scanner Engine v8")
    parser.add_argument("-c", "--codes", type=str, nargs="+", help="Direct stock codes list")
    parser.add_argument("-i", "--input", type=str, default=DEFAULT_INPUT_CSV, help="Path to input watchlist CSV file")
    parser.add_argument("-o", "--output", type=str, default=DEFAULT_OUTPUT_CSV, help="Path to output log CSV file")
    parser.add_argument("--preset", type=str, default="balanced", choices=["conservative", "balanced", "aggressive"], help="Strategy preset")
    parser.add_argument("--backtest", action="store_true", help="Run a simple historical backtest instead of the live scan")
    parser.add_argument("--backtest-output", type=str, default=DEFAULT_BACKTEST_CSV, help="Path to write backtest results")
    parser.add_argument("--holding-period", type=int, default=5, help="Number of bars to hold after a buy signal")
    parser.add_argument("--live-history-years", type=int, default=5, help="Years of historical daily data to use for live scan context")
    parser.add_argument("--backtest-history-years", type=int, default=3, help="Years of historical daily data to use in backtest")
    parser.add_argument("--as-of-date", type=str, default=None, help="Evaluate signals as of a specific historical date (YYYY-MM-DD)")
    parser.add_argument("--as-of-dates", type=str, default=None, help="Comma-separated historical dates (YYYY-MM-DD) for multi-date engine validation")
    parser.add_argument("--live-candle-mode", choices=["auto", "completed", "intraday"], default="auto", help="auto=detect PREMARKET/REGULAR/POSTMARKET and validate today's Yahoo minute bars; completed=force completed daily candles; intraday=force today's extended-hours minute OHLCV with safe fallback")
    parser.add_argument("--countmax", "--countMax", dest="max_tickers", type=int, default=0, help="Maximum number of tickers to scan. Use 0 to scan the full input file.")
    parser.add_argument("--max-buys", dest="max_buys", type=int, default=0, help="Optional early-stop limit for BUY signals. Use 0 to disable early stopping.")
    args = parser.parse_args()

    config = get_config(args.preset)
    max_tickers = max(0, int(args.max_tickers or 0))
    max_buy_results = max(0, int(args.max_buys or 0))

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

    input_ticker_count = len(watchlist)
    if max_tickers > 0:
        watchlist = watchlist[:max_tickers]

    if args.backtest:
        print("=" * 80, flush=True)
        print(" STARTING V8 BACKTEST", flush=True)
        print("=" * 80, flush=True)
        backtest_df, backtest_summary = run_backtest(
            watchlist,
            config,
            args.backtest_output,
            holding_period=args.holding_period,
            history_years=args.backtest_history_years,
        )
        print(backtest_df.head(20).to_string(index=False))
        print("\nBacktest complete. Results written to:", args.backtest_output)
        print("\nBacktest Summary")
        print(f"Total trades        : {backtest_summary['total_trades']}")
        print(f"Winning trades      : {backtest_summary['winning_trades']}")
        print(f"Losing trades       : {backtest_summary['losing_trades']}")
        print(f"Win rate            : {backtest_summary['win_rate_pct']}%")
        print(f"Average return      : {backtest_summary['average_return_pct']}%")
        print(f"Average win         : {backtest_summary['average_win_pct']}%")
        print(f"Average loss        : {backtest_summary['average_loss_pct']}%")
        print(f"Best trade          : {backtest_summary['best_trade_pct']}%")
        print(f"Worst trade         : {backtest_summary['worst_trade_pct']}%")
        print(f"Max drawdown        : {backtest_summary['max_drawdown_pct']}%")
        if backtest_summary['top_tickers']:
            print("Top performers      :", ", ".join([f"{item['ticker']} ({item['avg_return_pct']}%)" for item in backtest_summary['top_tickers']]))
        sys.exit(0)

    try:
        as_of_date_list = build_as_of_date_list(args.as_of_date, args.as_of_dates)
    except ValueError as ve:
        print(f" Error: {ve}", flush=True)
        sys.exit(1)

    all_rows_for_output = []
    date_level_summary_rows = []
    total_tickers = len(watchlist)

    for run_number, as_of_date in enumerate(as_of_date_list, start=1):
        run_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        as_of_label = as_of_date if as_of_date else datetime.now().strftime('%Y-%m-%d')
        initial_summary_message = (
            f"Summary | AsOf={as_of_label} | Input={input_ticker_count} | Total={total_tickers} | Scanned=0 | MaxTickers={max_tickers or 'ALL'} | MaxBuy={max_buy_results or 'OFF'} | BUY=0 | WATCHLIST=0 | HOLD=0 | DO NOT BUY=0 | IGNORE=0 | ERROR/SKIPPED=0"
        )

        print("=" * 80, flush=True)
        print(f" STARTING LIVE MOMENTUM SCANNER V8 | {run_timestamp}", flush=True)
        print(f" Run : {run_number}/{len(as_of_date_list)}", flush=True)
        print(f" As-Of Date : {as_of_label}", flush=True)
        print(f" Watchlist Source : {source_message}", flush=True)
        print(f" Historical Log Target: {args.output}", flush=True)
        print(f" Preset : {args.preset}", flush=True)
        if as_of_date is None:
            startup_market_context = get_us_market_phase()
            print(f" Market Phase : {startup_market_context['phase']} | Requested Mode: {args.live_candle_mode} | Effective Auto Mode: {startup_market_context['effective_mode']}", flush=True)
            print(f" Market Time ET : {startup_market_context['market_time_et']}", flush=True)
        print("=" * 80, flush=True)
        print(initial_summary_message, flush=True)

        unordered_results = []
        counts = {STATUS_BUY_SIGNAL: 0, STATUS_WATCHLIST: 0, STATUS_HOLD: 0, STATUS_DO_NOT_BUY: 0, STATUS_IGNORE: 0, STATUS_ERROR: 0}

        for idx, ticker in enumerate(watchlist, start=1):
            print(f"({idx}/{total_tickers}) Running engine for {ticker}...", flush=True)
            data_packet = evaluate_stock_momentum(
                ticker,
                config=config,
                history_years=args.live_history_years,
                as_of_date=as_of_date,
                live_candle_mode=args.live_candle_mode,
            )
            data_packet["timestamp"] = run_timestamp
            data_packet["as_of_date"] = as_of_label
            unordered_results.append(data_packet)
            counts[data_packet["status"]] += 1

            if max_buy_results > 0 and data_packet["status"] == STATUS_BUY_SIGNAL and counts[STATUS_BUY_SIGNAL] >= max_buy_results:
                print(f" BUY limit reached ({max_buy_results}). Stopping further scan.", flush=True)
                break

            time.sleep(1)

        processed_tickers = len(unordered_results)
        summary_message = (
            f"Summary | AsOf={as_of_label} | Input={input_ticker_count} | Total={total_tickers} | Scanned={processed_tickers} | MaxTickers={max_tickers or 'ALL'} | MaxBuy={max_buy_results or 'OFF'} | BUY={counts[STATUS_BUY_SIGNAL]} | WATCHLIST={counts[STATUS_WATCHLIST]} | "
            f"HOLD={counts[STATUS_HOLD]} | DO NOT BUY={counts[STATUS_DO_NOT_BUY]} | IGNORE={counts[STATUS_IGNORE]} | ERROR/SKIPPED={counts[STATUS_ERROR]}"
        )

        for item in unordered_results:
            item["summary_message"] = summary_message

        summary_row = {
            "ticker": "SUMMARY",
            "timestamp": run_timestamp,
            "as_of_date": as_of_label,
            "status": "SUMMARY",
            "message": summary_message,
            "summary_message": summary_message,
            "price": None,
            "ema_50": None,
            "ema_200": None,
            "macd": None,
            "macd_signal": None,
            "macd_hist": None,
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
            "market_phase": None,
            "data_mode": None,
            "market_time_et": None,
            "data_note": None,
        }

        rows_for_output = [summary_row] + unordered_results
        all_rows_for_output.extend(rows_for_output)
        date_level_summary_rows.append({
            "as_of_date": as_of_label,
            "input_tickers": input_ticker_count,
            "total_tickers": total_tickers,
            "scanned_tickers": processed_tickers,
            "buy_count": counts[STATUS_BUY_SIGNAL],
            "watchlist_count": counts[STATUS_WATCHLIST],
            "hold_count": counts[STATUS_HOLD],
            "do_not_buy_count": counts[STATUS_DO_NOT_BUY],
            "ignore_count": counts[STATUS_IGNORE],
            "error_count": counts[STATUS_ERROR],
            "buy_rate_pct": round((counts[STATUS_BUY_SIGNAL] / processed_tickers) * 100, 2) if processed_tickers else 0.0,
        })

        print("\n" + "=" * 80, flush=True)
        print(f" SUMMARY EXECUTION REPORT V8 | {run_timestamp}", flush=True)
        print("=" * 80, flush=True)
        print(f" As-Of Date           : {as_of_label}", flush=True)
        print(f" Total Tickers Analyzed : {total_tickers}", flush=True)
        print(f" Tickers Scanned        : {processed_tickers}", flush=True)
        print(f" BUY SIGNAL Count       : {counts[STATUS_BUY_SIGNAL]}", flush=True)
        print(f" WATCHLIST Count        : {counts[STATUS_WATCHLIST]}", flush=True)
        print(f" HOLD Count             : {counts[STATUS_HOLD]}", flush=True)
        print(f" DO NOT BUY Count       : {counts[STATUS_DO_NOT_BUY]}", flush=True)
        print(f" IGNORE Count           : {counts[STATUS_IGNORE]}", flush=True)
        print(f" ERROR/SKIPPED Count    : {counts[STATUS_ERROR]}", flush=True)
        print("-" * 80, flush=True)
        print(f"{'CODE':<8} | {'STATUS':<12} | {'SCORE':<5} | {'EXECUTION MESSAGE'}", flush=True)
        print("-" * 80, flush=True)

        for item in sort_results_for_display(unordered_results):
            score_value = item.get("signal_score")
            score_text = str(score_value) if score_value is not None else "-"
            print(f"{item['ticker']:<8} | {item['status']:<12} | {score_text:<5} | {item['message']}", flush=True)
        print("=" * 80, flush=True)

    df_log = pd.DataFrame(all_rows_for_output)
    columns_order = ["ticker", "timestamp", "as_of_date", "market_phase", "data_mode", "market_time_et", "data_note", "status", "message", "summary_message", "price", "ema_50", "ema_200", "macd", "macd_signal", "macd_hist", "adx", "rsi", "atr", "stoch_k", "stoch_d", "volume", "volume_avg_20", "weekly_ema_20", "weekly_ema_50", "weekly_price", "signal_score"]

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

        if len(date_level_summary_rows) > 1:
            summary_path = os.path.splitext(args.output)[0] + "_date_summary.csv"
            pd.DataFrame(date_level_summary_rows).to_csv(summary_path, index=False)
            print(f" Date-level summary report written at:\n 📊 👉 {summary_path}\n", flush=True)
    except Exception as e:
        print(f" Failed to write log data to disk: {e}", flush=True)