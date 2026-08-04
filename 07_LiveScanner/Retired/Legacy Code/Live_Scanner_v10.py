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
# VERSION 10 - OFFLINE MOMENTUM SCANNER + CONSOLIDATED OUTPUT
# ==============================================================================

EMA_FAST_PERIOD = 50
EMA_SLOW_PERIOD = 200
MACD_FAST_PERIOD = 8
MACD_SLOW_PERIOD = 21
MACD_SIGNAL_PERIOD = 5
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
    "continuation_rsi_min": 50.0,
    "continuation_rsi_max": 75.0,
    "continuation_atr_mult": 2.2,
    "continuation_volume_min_ratio": 0.80,
    "hist_expansion_lookback": 3,
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
        "continuation_rsi_max": 72.0,
        "continuation_atr_mult": 1.8,
        "continuation_volume_min_ratio": 1.0,
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
        "continuation_rsi_max": 80.0,
        "continuation_atr_mult": 2.5,
        "continuation_volume_min_ratio": 0.65,
    },
}

DEFAULT_INPUT_CSV = "D:\\Tools\\00_StockCodeMaster\\02_Stock\\01-07-US_Common_Stocks_Master_Library.csv"
DEFAULT_OUTPUT_CSV = os.path.abspath(os.path.join(os.path.dirname(__file__), "output", "Live_Scanner_v10_Output.csv"))
DEFAULT_BACKTEST_CSV = os.path.abspath(os.path.join(os.path.dirname(__file__), "output", "Live_Scanner_v10_backtest.csv"))
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
MSG_BUY_CONTINUATION = "Active bullish momentum continuation: MACD is above Signal and zero with an expanding positive histogram; ADX confirms trend strength."
MSG_BUY_CONTINUATION_EXTENDED = "Active bullish momentum continuation remains intact, but price extension above EMA50 increases entry risk."
MSG_HOLD_TREND = "Healthy upward trend, but no fresh entry trigger."


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


def adx_band(value: float, config: dict) -> tuple[str, int]:
    """Return a readable ADX band and confidence points.

    ADX is a confidence modifier in V10, not a universal hard veto.
    """
    if value < 15:
        return "Weak", 0
    if value < 20:
        return "Emerging", 1
    if value < 35:
        return "Healthy", 2
    if value <= 50:
        return "Strong", 3
    return "Extreme", 2


def confidence_label(score: int, maximum: int = 10) -> str:
    pct = 0 if maximum <= 0 else max(0, min(100, round(score / maximum * 100)))
    if pct >= 85:
        level = "High"
    elif pct >= 65:
        level = "Moderate-High"
    elif pct >= 45:
        level = "Moderate"
    else:
        level = "Low"
    return f"{level} ({pct}%)"


def evaluate_frame(df: pd.DataFrame, ticker_symbol: str, config: dict) -> dict:
    def error_result(message: str, output_signal: str) -> dict:
        return {
            "ticker": ticker_symbol,
            "status": STATUS_ERROR,
            "output_signal": output_signal,
            "setup_type": "ERROR",
            "output_message": message,
            "message": message,
            "message_details": f"Error={message}",
            "confidence": "Low (0%)",
            "risk_level": "Not Applicable",
        }

    if df.empty or len(df) < EMA_SLOW_PERIOD:
        return error_result(
            f"Insufficient history (Needs {EMA_SLOW_PERIOD} daily candles).",
            "Error_Insufficient_History",
        )

    frame = df.copy()
    frame.columns = [str(col).lower() for col in frame.columns]
    required_columns = {"open", "high", "low", "close"}
    if not required_columns.issubset(frame.columns):
        return error_result("Missing OHLC data.", "Error_Missing_OHLC_Data")
    if frame["close"].isna().all():
        return error_result("No price data available.", "Error_NoPriceData")

    weekly_df = build_weekly_data(frame, include_incomplete_week=False)
    if weekly_df.empty or len(weekly_df) < WEEKLY_EMA_SLOW:
        weekly_df = None

    frame["ema_50"] = ta.trend.ema_indicator(frame["close"], window=EMA_FAST_PERIOD)
    frame["ema_200"] = ta.trend.ema_indicator(frame["close"], window=EMA_SLOW_PERIOD)
    macd_obj = ta.trend.MACD(
        frame["close"], window_fast=MACD_FAST_PERIOD,
        window_slow=MACD_SLOW_PERIOD, window_sign=MACD_SIGNAL_PERIOD,
    )
    frame["macd"] = macd_obj.macd()
    frame["macd_signal"] = macd_obj.macd_signal()
    frame["macd_hist"] = macd_obj.macd_diff()
    frame["adx"] = ta.trend.adx(frame["high"], frame["low"], frame["close"], window=ADX_PERIOD)
    frame["rsi"] = ta.momentum.rsi(frame["close"], window=RSI_PERIOD)
    frame["atr"] = ta.volatility.average_true_range(frame["high"], frame["low"], frame["close"], window=ATR_PERIOD)
    frame["stoch_k"] = ta.momentum.stoch(frame["high"], frame["low"], frame["close"], window=STOCH_K_PERIOD)
    frame["stoch_d"] = ta.momentum.stoch_signal(
        frame["high"], frame["low"], frame["close"],
        window=STOCH_K_PERIOD, smooth_window=STOCH_D_PERIOD,
    )

    latest = frame.iloc[-1]
    prev = frame.iloc[-2]
    crucial = ["ema_50", "ema_200", "macd", "macd_signal", "macd_hist", "adx", "rsi", "atr", "stoch_k", "stoch_d"]
    if any(pd.isna(latest[name]) for name in crucial):
        return error_result("Crucial indicators generated null values.", "Error_NullValuesFound")

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
        volume_avg_20 = float(volume_series.iloc[-VOLUME_LOOKBACK - 1:-1].mean())

    volume_ratio = None
    if current_volume is not None and volume_avg_20 and volume_avg_20 > 0:
        volume_ratio = current_volume / volume_avg_20

    price = float(latest["close"])
    ema50 = float(latest["ema_50"])
    ema200 = float(latest["ema_200"])
    atr = float(latest["atr"])
    distance = price - ema50
    distance_atr = distance / atr if atr > 0 else None

    macro_trend_ok = price > ema50 > ema200
    weekly_trend_ok = False
    if weekly_ema_20 is not None and weekly_ema_50 is not None and weekly_price is not None:
        weekly_trend_ok = weekly_price > weekly_ema_20 > weekly_ema_50

    macd = float(latest["macd"])
    signal = float(latest["macd_signal"])
    hist = float(latest["macd_hist"])
    hist_prev = float(prev["macd_hist"])
    hist3 = frame["macd_hist"].dropna().iloc[-3:].astype(float).tolist()
    hist_expanding_3 = len(hist3) == 3 and hist3[0] <= hist3[1] <= hist3[2] and hist3[2] > 0
    hist_contracting_3 = len(hist3) == 3 and hist3[0] >= hist3[1] >= hist3[2] and hist3[2] > 0
    hist_improving = hist > hist_prev
    macd_bullish = macd > signal
    macd_above_zero = macd > 0 and signal > 0
    pre_bull_crossover = macd < signal and hist < 0 and hist_improving

    adx_value = float(latest["adx"])
    adx_name, adx_points = adx_band(adx_value, config)
    rsi_value = float(latest["rsi"])
    stoch_k = float(latest["stoch_k"])
    stoch_d = float(latest["stoch_d"])

    lookback = max(2, int(config.get("stoch_recent_lookback", STOCH_RECENT_LOOKBACK)))
    stoch_threshold = config.get("stoch_oversold", BALANCED_CONFIG["stoch_oversold"])
    stoch_recovery_ceiling = stoch_threshold + config.get("stoch_recovery_buffer", STOCH_RECOVERY_BUFFER)
    stoch_recently_oversold = bool(frame["stoch_k"].iloc[-lookback:].min() < stoch_threshold)
    stoch_crossed_up = bool(prev["stoch_k"] <= prev["stoch_d"] and latest["stoch_k"] > latest["stoch_d"])
    stoch_recovery_trigger = bool(stoch_recently_oversold and stoch_crossed_up and stoch_k <= stoch_recovery_ceiling)

    continuation_rsi_ok = config.get("continuation_rsi_min", 50.0) <= rsi_value <= config.get("continuation_rsi_max", 75.0)
    rsi_exhausted = rsi_value > config.get("rsi_overbought", BALANCED_CONFIG["rsi_overbought"])
    volume_confirmed = volume_ratio is None or volume_ratio >= config.get("volume_mult", BALANCED_CONFIG["volume_mult"])
    continuation_volume_ok = volume_ratio is None or volume_ratio >= config.get("continuation_volume_min_ratio", 0.80)
    safe_atr = config.get("atr_safe_mult", BALANCED_CONFIG["atr_safe_mult"])
    ext_atr = config.get("atr_ext_mult", BALANCED_CONFIG["atr_ext_mult"])
    price_in_safe_buy_zone = distance_atr is not None and distance_atr <= safe_atr
    price_hyper_extended = distance_atr is not None and distance_atr > ext_atr

    if distance_atr is None:
        extension_state = "Unknown"
        extension_risk = 1
    elif distance_atr <= safe_atr:
        extension_state = "Controlled"
        extension_risk = 0
    elif distance_atr <= ext_atr:
        extension_state = "Moderately Extended"
        extension_risk = 1
    else:
        extension_state = "Highly Extended"
        extension_risk = 2

    momentum_continuation = bool(
        macro_trend_ok and (weekly_df is None or weekly_trend_ok)
        and macd_bullish and macd_above_zero
        and hist > 0 and (hist_expanding_3 or hist_improving)
        and continuation_rsi_ok and continuation_volume_ok
        and adx_value >= 15
    )
    established_trend = bool(macd_bullish and macd_above_zero and adx_value >= 15)
    recovering_momentum = bool(macd_bullish and hist_improving and adx_value >= 15)

    metrics = {
        "ticker": ticker_symbol,
        "price": round(price, 2), "ema_50": round(ema50, 2), "ema_200": round(ema200, 2),
        "ema50_distance_atr": round(distance_atr, 3) if distance_atr is not None else None,
        "macd_params": f"{MACD_FAST_PERIOD},{MACD_SLOW_PERIOD},{MACD_SIGNAL_PERIOD}",
        "macd": round(macd, 3), "macd_signal": round(signal, 3),
        "macd_hist": round(hist, 3), "macd_hist_prev": round(hist_prev, 3),
        "macd_hist_3bar": ",".join(f"{x:.3f}" for x in hist3),
        "macd_state": (
            "BULL_EXPANDING_3BAR" if macd_bullish and hist_expanding_3
            else "BULL_IMPROVING" if macd_bullish and hist_improving
            else "BULL_COOLING_3BAR" if macd_bullish and hist_contracting_3
            else "PRE_BULL_CROSS" if pre_bull_crossover
            else "BULL_BELOW_ZERO" if macd_bullish and not macd_above_zero
            else "BEARISH"
        ),
        "adx": round(adx_value, 2), "adx_band": adx_name,
        "rsi": round(rsi_value, 2), "atr": round(atr, 3),
        "stoch_k": round(stoch_k, 2), "stoch_d": round(stoch_d, 2),
        "volume": round(current_volume, 2) if current_volume is not None else None,
        "volume_avg_20": round(volume_avg_20, 2) if volume_avg_20 is not None else None,
        "volume_ratio": round(volume_ratio, 3) if volume_ratio is not None else None,
        "weekly_ema_20": round(weekly_ema_20, 2) if weekly_ema_20 is not None else None,
        "weekly_ema_50": round(weekly_ema_50, 2) if weekly_ema_50 is not None else None,
        "weekly_price": round(weekly_price, 2) if weekly_price is not None else None,
        "extension_state": extension_state,
        "output_signal": None, "setup_type": "NONE",
    }

    detail_parts = [
        f"Trend={'Daily bullish' if macro_trend_ok else 'Daily trend failed'}",
        f"Weekly={'Aligned' if weekly_trend_ok else ('Unavailable' if weekly_df is None else 'Not aligned')}",
        f"MACD={metrics['macd_state']} ({macd:.3f}/{signal:.3f}; Hist3={metrics['macd_hist_3bar']})",
        f"ADX={adx_value:.2f} ({adx_name})",
        f"RSI={rsi_value:.2f}",
        f"Stochastic={stoch_k:.2f}/{stoch_d:.2f}",
        f"EMA50Distance={distance_atr:.2f} ATR ({extension_state})" if distance_atr is not None else "EMA50Distance=Unavailable",
        f"VolumeRatio={volume_ratio:.2f}x" if volume_ratio is not None else "VolumeRatio=Unavailable",
    ]

    score = 0
    score += 2 if macro_trend_ok else 0
    score += 2 if weekly_trend_ok else 0
    score += 2 if macd_bullish and macd_above_zero else (1 if macd_bullish else 0)
    score += 2 if hist_expanding_3 else (1 if hist_improving else 0)
    score += adx_points
    score += 1 if continuation_volume_ok else 0
    score -= extension_risk
    score = max(0, min(10, score))

    if not macro_trend_ok:
        status, output_signal, setup_type = STATUS_IGNORE, "Ignore_Daily_Trend", "NONE"
        output_message = "Ignore: the daily bullish structure is not aligned because price is below EMA50 or EMA50 is below EMA200."
        risk_level = "Trend Not Qualified"
    elif weekly_df is not None and not weekly_trend_ok:
        status, output_signal, setup_type = STATUS_IGNORE, "Ignore_Weekly_Trend", "NONE"
        output_message = "Ignore: the daily structure is positive, but the completed weekly trend is not aligned."
        risk_level = "Weekly Trend Not Qualified"
    else:
        exhaustion_reasons = []
        if price_hyper_extended:
            exhaustion_reasons.append("price is highly extended from EMA50")
        if rsi_exhausted:
            exhaustion_reasons.append("RSI is exhausted")
        if adx_value > config.get("adx_extreme", 50.0) and not hist_improving:
            exhaustion_reasons.append("ADX is extreme while MACD momentum is weakening")

        if len(exhaustion_reasons) >= 2:
            status, output_signal, setup_type = STATUS_DO_NOT_BUY, "Do_Not_Buy", "EXHAUSTION"
            output_message = "Do not buy: multiple extension and exhaustion conditions are active despite the broader trend."
            risk_level = "High"
            detail_parts.append("Exhaustion=" + "; ".join(exhaustion_reasons))
            score = max(0, score - 3)
        elif established_trend and price_in_safe_buy_zone and stoch_recovery_trigger:
            setup_type = "PULLBACK_RECOVERY"
            if volume_confirmed:
                status, output_signal = STATUS_BUY_SIGNAL, "Buy_Pullback_Recovery"
                output_message = "Buy pullback recovery: the bullish trend is intact, Stochastic has reversed upward from oversold, and volume confirms the recovery."
                risk_level = "Low-Moderate"
                score = min(10, score + 2)
            else:
                status, output_signal = STATUS_WATCHLIST, "Watchlist_Pullback_Recovery_But_Volume_Confirmation_Pending"
                output_message = "Watchlist: the pullback recovery has triggered, but volume confirmation is still pending."
                risk_level = "Confirmation Pending"
        elif momentum_continuation:
            status, output_signal = STATUS_BUY_SIGNAL, "Buy_Momentum_Extension"
            setup_type = "MOMENTUM_CONTINUATION_EXTENDED" if extension_risk else "MOMENTUM_CONTINUATION"
            if adx_name == "Emerging":
                output_message = "Buy momentum continuation: MACD(8,21,5) is bullish with improving acceleration; ADX is emerging, so confirmation is moderate."
            elif extension_risk:
                output_message = "Buy momentum continuation: MACD(8,21,5) is bullish with improving acceleration; price is extended, increasing entry risk but not invalidating the move."
            else:
                output_message = "Buy momentum continuation: MACD(8,21,5) is bullish with improving acceleration, trend strength is confirmed, and price extension is controlled."
            risk_level = "Moderate" if (adx_name == "Emerging" or extension_risk == 1) else ("Elevated" if extension_risk == 2 else "Controlled")
            score = min(10, score + 1)
        elif established_trend and stoch_recently_oversold and not stoch_crossed_up:
            status, output_signal, setup_type = STATUS_WATCHLIST, "Watchlist_Pullback_Forming_But_Stochastic_Reversal_Pending", "PULLBACK_FORMING"
            output_message = "Watchlist: the bullish trend remains intact and the pullback is oversold, but the Stochastic bullish reversal is still pending."
            risk_level = "Trigger Pending"
        elif macd_bullish and hist_contracting_3:
            status, output_signal, setup_type = STATUS_HOLD, "Hold", "MOMENTUM_COOLING"
            output_message = "Hold: the broader bullish structure remains intact, but the positive MACD histogram has contracted across three bars and momentum is cooling."
            risk_level = "Momentum Cooling"
        elif pre_bull_crossover and price_in_safe_buy_zone:
            status, output_signal, setup_type = STATUS_WATCHLIST, "Watchlist_Bull_Crossover_Formation", "PRE_BULL_CROSSOVER"
            output_message = "Watchlist: the negative MACD histogram is improving and a bullish 8/21/5 crossover is forming, but it has not triggered yet."
            risk_level = "Crossover Pending"
        elif recovering_momentum and price_in_safe_buy_zone:
            status, output_signal, setup_type = STATUS_WATCHLIST, "Watchlist_Momentum_Building", "MOMENTUM_RECOVERY"
            output_message = "Watchlist: bullish momentum is rebuilding near EMA50, but the full continuation conditions are not yet confirmed."
            risk_level = "Confirmation Pending"
        elif established_trend:
            status, output_signal, setup_type = STATUS_HOLD, "Hold", "ESTABLISHED_TREND"
            output_message = "Hold: the upward trend remains healthy, but there is no fresh pullback-recovery or momentum-continuation entry trigger."
            risk_level = "No Fresh Entry"
        else:
            status, output_signal, setup_type = STATUS_HOLD, "Hold", "TREND_NO_ENTRY"
            output_message = "Hold: the macro trend remains intact, but MACD acceleration or ADX strength is insufficient for a fresh entry."
            risk_level = "Momentum Not Confirmed"

    detail_parts.append(f"Risk={risk_level}")
    detail_parts.append(f"Signal={output_signal}")
    metrics.update({
        "status": status,
        "output_signal": output_signal,
        "setup_type": setup_type,
        "output_message": output_message,
        "message": output_message,
        "message_details": " | ".join(detail_parts),
        "confidence": confidence_label(score),
        "risk_level": risk_level,
        "signal_score": score,
    })
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
        "output_signal": "Error_InternalError",
        "message": "",
        "output_message": "",
        "message_details": "",
        "confidence": None,
        "risk_level": None,
        "summary_message": "",
        "price": None,
        "ema_50": None,
        "ema_200": None,
        "macd": None,
        "macd_signal": None,
        "macd_hist": None,
        "macd_hist_prev": None,
        "macd_params": f"{MACD_FAST_PERIOD},{MACD_SLOW_PERIOD},{MACD_SIGNAL_PERIOD}",
        "macd_state": None,
        "setup_type": None,
        "volume_ratio": None,
        "ema50_distance_atr": None,
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
            result_template["output_signal"] = "Error_Insufficient_History"
            result_template["message"] = f"Insufficient history (Needs {EMA_SLOW_PERIOD} daily candles)."
            result_template["output_message"] = result_template["message"]
            result_template["message_details"] = "Error=" + result_template["message"]
            result_template["confidence"] = "Low (0%)"
            result_template["risk_level"] = "Not Applicable"
            return result_template

        df.columns = [col.lower() for col in df.columns]

        if as_of_date:
            df = filter_to_as_of_date(df, as_of_date)
            if df.empty or len(df) < EMA_SLOW_PERIOD:
                result_template["output_signal"] = "Error_Insufficient_History"
                result_template["message"] = f"Insufficient history up to {as_of_date} (Needs {EMA_SLOW_PERIOD} daily candles)."
                result_template["output_message"] = result_template["message"]
                result_template["message_details"] = "Error=" + result_template["message"]
                result_template["confidence"] = "Low (0%)"
                result_template["risk_level"] = "Not Applicable"
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
        result_template["output_signal"] = "Error_InternalError"
        result_template["message"] = f"Skipped (Internal Error: {str(e)})"
        result_template["output_message"] = result_template["message"]
        result_template["message_details"] = "Error=" + result_template["message"]
        result_template["confidence"] = "Low (0%)"
        result_template["risk_level"] = "Not Applicable"
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
                    "signal_score": signal.get("signal_score"),
                    "output_signal": signal.get("output_signal"),
                    "setup_type": signal.get("setup_type")
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
    parser = argparse.ArgumentParser(description="Version 10 Momentum Scanner: Consolidated Signal + Message Output")
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
    execution_started = datetime.now()

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
        print(" STARTING V10 BACKTEST", flush=True)
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
        print(f" STARTING LIVE MOMENTUM SCANNER V10 | {run_timestamp}", flush=True)
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
            "output_signal": "SUMMARY",
            "output_message": summary_message,
            "message": summary_message,
            "message_details": f"Version=V10 | Preset={args.preset} | MACD={MACD_FAST_PERIOD},{MACD_SLOW_PERIOD},{MACD_SIGNAL_PERIOD} | Input={input_ticker_count} | Scanned={processed_tickers} | BUY={counts[STATUS_BUY_SIGNAL]} | WATCHLIST={counts[STATUS_WATCHLIST]} | HOLD={counts[STATUS_HOLD]} | DO_NOT_BUY={counts[STATUS_DO_NOT_BUY]} | IGNORE={counts[STATUS_IGNORE]} | ERROR={counts[STATUS_ERROR]}",
            "confidence": None,
            "risk_level": None,
            "summary_message": summary_message,
            "price": None,
            "ema_50": None,
            "ema_200": None,
            "macd": None,
            "macd_signal": None,
            "macd_hist": None,
            "macd_hist_prev": None,
            "macd_params": f"{MACD_FAST_PERIOD},{MACD_SLOW_PERIOD},{MACD_SIGNAL_PERIOD}",
            "macd_state": None,
            "setup_type": None,
            "volume_ratio": None,
            "ema50_distance_atr": None,
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
        print(f" SUMMARY EXECUTION REPORT V10 | {run_timestamp}", flush=True)
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
        print(f"{'CODE':<8} | {'OUTPUT SIGNAL':<62} | {'MESSAGE'}", flush=True)
        print("-" * 80, flush=True)

        for item in sort_results_for_display(unordered_results):
            print(f"{item['ticker']:<8} | {str(item.get('output_signal', '')):<62} | {item.get('output_message') or item.get('message', '')}", flush=True)
        print("=" * 80, flush=True)

    df_log = pd.DataFrame(all_rows_for_output)
    columns_order = ["ticker", "output_signal", "output_message", "message_details", "status", "setup_type", "confidence", "risk_level", "timestamp", "as_of_date", "market_phase", "data_mode", "market_time_et", "data_note", "price", "ema_50", "ema_200", "ema50_distance_atr", "extension_state", "macd_params", "macd", "macd_signal", "macd_hist", "macd_hist_prev", "macd_hist_3bar", "macd_state", "adx", "adx_band", "rsi", "atr", "stoch_k", "stoch_d", "volume", "volume_avg_20", "volume_ratio", "weekly_ema_20", "weekly_ema_50", "weekly_price", "signal_score", "summary_message", "message"]

    for col in columns_order:
        if col not in df_log.columns:
            df_log[col] = None
    df_log = df_log[columns_order]

    try:
        output_dir = os.path.dirname(args.output)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        output_root, _ = os.path.splitext(args.output)
        error_path = output_root + "_errors.csv"
        log_path = output_root + ".log"

        # V10 writes a clean current-run file. The first row is the SUMMARY row;
        # the user-facing signal/message columns appear immediately after ticker.
        df_log.to_csv(args.output, mode="w", index=False, header=True)

        error_df = df_log[df_log["status"] == STATUS_ERROR].copy()
        if not error_df.empty:
            error_df.to_csv(error_path, index=False)
        elif os.path.isfile(error_path):
            os.remove(error_path)

        execution_finished = datetime.now()
        elapsed_seconds = int((execution_finished - execution_started).total_seconds())
        elapsed_text = f"{elapsed_seconds // 60:02d}m {elapsed_seconds % 60:02d}s"
        final_summary = date_level_summary_rows[-1] if date_level_summary_rows else {}

        buy_rows = df_log[df_log["status"] == STATUS_BUY_SIGNAL]
        buy_breakup = buy_rows["output_signal"].value_counts().to_dict() if not buy_rows.empty else {}
        buy_symbols = ", ".join(buy_rows["ticker"].astype(str).tolist()) if not buy_rows.empty else "None"

        final_lines = [
            "=" * 100,
            "LIVE SCANNER V10 - POST EXECUTION SUMMARY",
            "=" * 100,
            f"Started              : {execution_started.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Completed            : {execution_finished.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Elapsed              : {elapsed_text}",
            f"Input file           : {args.input if not args.codes else 'Direct command-line codes'}",
            f"Codes read           : {input_ticker_count}",
            f"Codes selected       : {total_tickers}",
            f"Codes processed      : {final_summary.get('scanned_tickers', 0)}",
            f"BUY SIGNAL           : {final_summary.get('buy_count', 0)}",
            f"WATCHLIST            : {final_summary.get('watchlist_count', 0)}",
            f"HOLD                 : {final_summary.get('hold_count', 0)}",
            f"DO NOT BUY           : {final_summary.get('do_not_buy_count', 0)}",
            f"IGNORE               : {final_summary.get('ignore_count', 0)}",
            f"ERROR/SKIPPED        : {final_summary.get('error_count', 0)}",
            f"BUY symbols          : {buy_symbols}",
            f"BUY breakup          : {buy_breakup or 'None'}",
            f"Preset               : {args.preset}",
            f"MACD                 : {MACD_FAST_PERIOD},{MACD_SLOW_PERIOD},{MACD_SIGNAL_PERIOD}",
            f"Requested candle mode: {args.live_candle_mode}",
            f"Output file          : {os.path.abspath(args.output)}",
            f"Error file           : {os.path.abspath(error_path) if not error_df.empty else 'Not created (no errors)'}",
            f"Log file             : {os.path.abspath(log_path)}",
            "=" * 100,
        ]
        final_text = "\n".join(final_lines)
        print("\n" + final_text, flush=True)

        with open(log_path, "w", encoding="utf-8") as log_file:
            log_file.write(final_text + "\n")
            log_file.write("\nOUTPUT SIGNAL BREAKUP\n")
            for signal_name, signal_count in df_log.loc[df_log["ticker"] != "SUMMARY", "output_signal"].value_counts().items():
                log_file.write(f"{signal_name}: {signal_count}\n")

        if len(date_level_summary_rows) > 1:
            summary_path = output_root + "_date_summary.csv"
            pd.DataFrame(date_level_summary_rows).to_csv(summary_path, index=False)
            print(f"Date-level summary file: {summary_path}", flush=True)
    except Exception as e:
        print(f"Failed to write V10 output/report files: {e}", flush=True)
