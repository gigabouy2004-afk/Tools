from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .config import BaselineMacdConfig, IndicatorConfig, MacdConfig


def _to_series(df: pd.DataFrame, column: str) -> pd.Series:
    values = pd.to_numeric(df[column], errors="coerce").dropna()
    if len(values) < 2:
        raise ValueError(f"Not enough values to compute {column}")
    return values


def _is_missing(value: Any) -> bool:
    return value is None or pd.isna(value)


def _bars_since_event(events: pd.Series) -> int | None:
    event_positions = np.flatnonzero(events.fillna(False).to_numpy())
    if len(event_positions) == 0:
        return None
    return int(len(events) - 1 - event_positions[-1])


def _rising_streak(series: pd.Series) -> int:
    values = series.dropna().tolist()
    streak = 0
    for index in range(len(values) - 1, 0, -1):
        if values[index] <= values[index - 1]:
            break
        streak += 1
    return streak


def _falling_streak(series: pd.Series) -> int:
    values = series.dropna().tolist()
    streak = 0
    for index in range(len(values) - 1, 0, -1):
        if values[index] >= values[index - 1]:
            break
        streak += 1
    return streak


def _insufficient_macd(periods: str) -> dict[str, Any]:
    return {
        "macd": None,
        "signal": None,
        "previous_macd": None,
        "previous_signal": None,
        "two_ago_macd": None,
        "two_ago_signal": None,
        "previous_histogram": None,
        "two_ago_histogram": None,
        "histogram": None,
        "histogram_slope": 0.0,
        "macd_slope": 0.0,
        "spread_contracting": False,
        "bullish_spread_contracting": False,
        "histogram_rising_streak": 0,
        "histogram_falling_streak": 0,
        "macd_signal_spread": None,
        "crossover_distance": None,
        "bars_since_bullish_crossover": None,
        "bars_since_bearish_crossover": None,
        "bars_since_bullish_zero_line_cross": None,
        "bars_since_bearish_zero_line_cross": None,
        "clear_bullish_crossover": False,
        "clear_bearish_crossover": False,
        "state": "INSUFFICIENT_HISTORY",
        "previous_state": "INSUFFICIENT_HISTORY",
        "zero_line_state": "INSUFFICIENT_HISTORY",
        "regime": "INSUFFICIENT_HISTORY",
        "periods": periods,
        "crossover_event": "NONE",
        "histogram_series": pd.Series(dtype=float),
        "is_sufficient": False,
    }


def calculate_macd(
    df: pd.DataFrame,
    config: MacdConfig | BaselineMacdConfig,
    clear_min_histogram: float = 0.0,
    clear_min_spread: float = 0.0,
) -> dict[str, Any]:
    periods = f"{config.fast},{config.slow},{config.signal}"
    try:
        close = _to_series(df, "Close")
    except (KeyError, ValueError):
        return _insufficient_macd(periods)
    if len(close) < config.slow:
        return _insufficient_macd(periods)

    ema_fast = close.ewm(span=config.fast, adjust=False).mean()
    ema_slow = close.ewm(span=config.slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    signal = macd.ewm(span=config.signal, adjust=False).mean()
    histogram = macd - signal

    latest_macd = float(macd.iloc[-1])
    latest_signal = float(signal.iloc[-1])
    previous_macd = float(macd.iloc[-2])
    previous_signal = float(signal.iloc[-2])
    two_ago_macd = float(macd.iloc[-3]) if len(macd) >= 3 else None
    two_ago_signal = float(signal.iloc[-3]) if len(signal) >= 3 else None
    latest_histogram = float(histogram.iloc[-1])
    previous_histogram = float(histogram.iloc[-2])
    two_ago_histogram = float(histogram.iloc[-3]) if len(histogram) >= 3 else None
    hist_slope = latest_histogram - previous_histogram
    macd_slope = latest_macd - previous_macd
    spread_contracting = latest_histogram < 0 and latest_histogram > previous_histogram
    bullish_spread_contracting = latest_histogram > 0 and latest_histogram < previous_histogram
    crossover_state = "BULLISH" if latest_macd > latest_signal else "BEARISH"
    previous_state = "BULLISH" if previous_macd > previous_signal else "BEARISH"
    zero_line_state = "ABOVE_ZERO" if latest_macd >= 0 else "BELOW_ZERO"
    if latest_macd > latest_signal and latest_macd >= 0:
        regime = "BULL_CONFIRMED"
    elif latest_macd > latest_signal:
        regime = "BULL_RECOVERY"
    elif latest_macd < latest_signal and latest_macd >= 0:
        regime = "BULL_WEAKENING"
    else:
        regime = "BEAR_CONFIRMED"

    macd_signal_spread = latest_macd - latest_signal
    clear_bullish_crossover = (
        previous_macd <= previous_signal
        and latest_macd > latest_signal
        and latest_histogram > clear_min_histogram
        and macd_signal_spread >= clear_min_spread
    )
    clear_bearish_crossover = (
        previous_macd >= previous_signal
        and latest_macd < latest_signal
        and latest_histogram < -clear_min_histogram
        and abs(macd_signal_spread) >= clear_min_spread
        and previous_histogram >= latest_histogram
    )
    bullish_crosses = (macd.shift(1) <= signal.shift(1)) & (macd > signal)
    bearish_crosses = (macd.shift(1) >= signal.shift(1)) & (macd < signal)
    bullish_zero_line_crosses = (macd.shift(1) <= 0) & (macd > 0)
    bearish_zero_line_crosses = (macd.shift(1) >= 0) & (macd < 0)
    crossover_event = "NONE"
    if previous_macd <= previous_signal and latest_macd > latest_signal:
        crossover_event = "BULLISH_CROSSOVER"
    elif previous_macd >= previous_signal and latest_macd < latest_signal:
        crossover_event = "BEARISH_CROSSOVER"

    return {
        "macd": round(latest_macd, 4),
        "signal": round(latest_signal, 4),
        "previous_macd": round(previous_macd, 4),
        "previous_signal": round(previous_signal, 4),
        "two_ago_macd": round(two_ago_macd, 4) if two_ago_macd is not None else None,
        "two_ago_signal": round(two_ago_signal, 4) if two_ago_signal is not None else None,
        "previous_histogram": round(previous_histogram, 4),
        "two_ago_histogram": round(two_ago_histogram, 4) if two_ago_histogram is not None else None,
        "histogram": round(latest_histogram, 4),
        "histogram_slope": round(hist_slope, 4),
        "macd_slope": round(macd_slope, 4),
        "spread_contracting": spread_contracting,
        "bullish_spread_contracting": bullish_spread_contracting,
        "histogram_rising_streak": _rising_streak(histogram),
        "histogram_falling_streak": _falling_streak(histogram),
        "macd_signal_spread": round(macd_signal_spread, 4),
        "crossover_distance": round(abs(latest_macd - latest_signal), 4),
        "bars_since_bullish_crossover": _bars_since_event(bullish_crosses),
        "bars_since_bearish_crossover": _bars_since_event(bearish_crosses),
        "bars_since_bullish_zero_line_cross": _bars_since_event(bullish_zero_line_crosses),
        "bars_since_bearish_zero_line_cross": _bars_since_event(bearish_zero_line_crosses),
        "clear_bullish_crossover": clear_bullish_crossover,
        "clear_bearish_crossover": clear_bearish_crossover,
        "state": crossover_state,
        "previous_state": previous_state,
        "zero_line_state": zero_line_state,
        "regime": regime,
        "periods": periods,
        "crossover_event": crossover_event,
        "histogram_series": histogram,
        "is_sufficient": True,
    }


def calculate_rsi(df: pd.DataFrame, period: int) -> dict[str, Any]:
    try:
        close = _to_series(df, "Close")
    except (KeyError, ValueError):
        return {"rsi": None, "slope": None, "state": "INSUFFICIENT_HISTORY"}
    if len(close) < period:
        return {"rsi": None, "slope": None, "state": "INSUFFICIENT_HISTORY"}
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - 100 / (1 + rs)
    latest_rsi = float(rsi.iloc[-1])
    if pd.isna(latest_rsi):
        return {"rsi": None, "slope": None, "state": "INSUFFICIENT_HISTORY"}
    state = "NEUTRAL"
    if latest_rsi >= 60:
        state = "BULLISH"
    elif latest_rsi < 40:
        state = "BEARISH"
    return {
        "rsi": round(latest_rsi, 4),
        "slope": round(float(rsi.iloc[-1] - rsi.iloc[-2]), 4),
        "state": state,
    }


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
    previous_close = close.shift(1)
    true_range = pd.concat([
        high - low,
        (high - previous_close).abs(),
        (low - previous_close).abs(),
    ], axis=1).max(axis=1)
    return true_range.ewm(alpha=1 / period, adjust=False).mean()


def _insufficient_adx() -> dict[str, Any]:
    return {
        "adx": None,
        "plus_di": None,
        "minus_di": None,
        "direction": "INSUFFICIENT_HISTORY",
        "strength": "INSUFFICIENT_HISTORY",
        "state": "INSUFFICIENT_HISTORY",
    }


def calculate_adx(df: pd.DataFrame, period: int) -> dict[str, Any]:
    try:
        high = _to_series(df, "High")
        low = _to_series(df, "Low")
        close = _to_series(df, "Close")
    except (KeyError, ValueError):
        return _insufficient_adx()
    if len(close) < period:
        return _insufficient_adx()
    plus_dm_raw = high.diff()
    minus_dm_raw = -(low.diff())
    plus_dm = plus_dm_raw.where((plus_dm_raw > minus_dm_raw) & (plus_dm_raw > 0), 0)
    minus_dm = minus_dm_raw.where((minus_dm_raw > plus_dm_raw) & (minus_dm_raw > 0), 0)
    atr = _atr(high, low, close, period)
    plus_di = 100 * plus_dm.ewm(alpha=1 / period, adjust=False).mean() / atr.replace(0, np.nan)
    minus_di = 100 * minus_dm.ewm(alpha=1 / period, adjust=False).mean() / atr.replace(0, np.nan)
    dx = (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan) * 100
    adx = dx.ewm(alpha=1 / period, adjust=False).mean()
    latest_adx = float(adx.iloc[-1])
    latest_plus_di = float(plus_di.iloc[-1])
    latest_minus_di = float(minus_di.iloc[-1])
    if pd.isna(latest_adx) or pd.isna(latest_plus_di) or pd.isna(latest_minus_di):
        return _insufficient_adx()
    direction = "BULLISH" if latest_plus_di > latest_minus_di else "BEARISH"
    strength = "STRONG" if latest_adx >= 25 else "WEAK"
    return {
        "adx": round(latest_adx, 4),
        "plus_di": round(latest_plus_di, 4),
        "minus_di": round(latest_minus_di, 4),
        "direction": direction,
        "strength": strength,
        "state": f"{direction}_{strength}",
    }


def _insufficient_bollinger() -> dict[str, Any]:
    return {
        "upper": None,
        "lower": None,
        "bandwidth_pct": None,
        "percent_b": None,
        "position": "INSUFFICIENT_HISTORY",
    }


def calculate_bollinger(df: pd.DataFrame, period: int, std_count: int) -> dict[str, Any]:
    try:
        close = _to_series(df, "Close")
    except (KeyError, ValueError):
        return _insufficient_bollinger()
    if len(close) < period:
        return _insufficient_bollinger()
    sma = close.rolling(period).mean()
    std = close.rolling(period).std(ddof=0)
    upper = sma + std_count * std
    lower = sma - std_count * std
    latest_close = float(close.iloc[-1])
    latest_upper = float(upper.iloc[-1])
    latest_lower = float(lower.iloc[-1])
    if pd.isna(latest_upper) or pd.isna(latest_lower):
        return _insufficient_bollinger()
    bandwidth = float((latest_upper - latest_lower) / latest_upper * 100) if latest_upper != 0 else 0.0
    percent_b = float((latest_close - latest_lower) / (latest_upper - latest_lower)) if latest_upper != latest_lower else 0.0
    position = "INSIDE"
    if latest_close > latest_upper:
        position = "ABOVE_UPPER"
    elif latest_close < latest_lower:
        position = "BELOW_LOWER"
    return {
        "upper": round(latest_upper, 4),
        "lower": round(latest_lower, 4),
        "bandwidth_pct": round(bandwidth, 4),
        "percent_b": round(percent_b * 100, 2),
        "position": position,
    }


def compute_daily_indicators(df_1d: pd.DataFrame, config: IndicatorConfig) -> dict[str, Any]:
    return {
        "macd_1d": calculate_macd(df_1d, config.macd),
        "baseline_macd_1d": calculate_macd(df_1d, config.baseline_macd),
        "rsi_1d": calculate_rsi(df_1d, config.rsi_period),
        "adx_1d": calculate_adx(df_1d, config.adx_period),
        "bollinger_1d": calculate_bollinger(df_1d, config.bollinger_period, config.bollinger_std),
    }
