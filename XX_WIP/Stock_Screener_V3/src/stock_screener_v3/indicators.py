from __future__ import annotations

import math

import pandas as pd


def ema(series: pd.Series, span: int) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").ewm(span=span, adjust=False).mean()


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    values = pd.to_numeric(close, errors="coerce")
    delta = values.diff()
    gain = delta.clip(lower=0).rolling(period, min_periods=period).mean()
    loss = (-delta.clip(upper=0)).rolling(period, min_periods=period).mean()
    rs = gain / loss.replace(0, math.nan)
    return 100 - (100 / (1 + rs))


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    values = pd.to_numeric(close, errors="coerce")
    macd_line = ema(values, fast) - ema(values, slow)
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return pd.DataFrame(
        {
            "MACD": macd_line,
            "Signal": signal_line,
            "Histogram": histogram,
        },
        index=close.index,
    )


def adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.DataFrame:
    high_values = pd.to_numeric(high, errors="coerce")
    low_values = pd.to_numeric(low, errors="coerce")
    close_values = pd.to_numeric(close, errors="coerce")

    plus_dm = (high_values.diff()).where(lambda value: value > (-low_values.diff()), 0).clip(lower=0)
    minus_dm = (-low_values.diff()).where(lambda value: value > high_values.diff(), 0).clip(lower=0)
    tr = pd.concat(
        [
            high_values - low_values,
            (high_values - close_values.shift()).abs(),
            (low_values - close_values.shift()).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr = tr.rolling(period, min_periods=period).mean()
    plus_di = 100 * plus_dm.rolling(period, min_periods=period).mean() / atr
    minus_di = 100 * minus_dm.rolling(period, min_periods=period).mean() / atr
    dx = ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, math.nan)) * 100
    adx_line = dx.rolling(period, min_periods=period).mean()
    return pd.DataFrame({"ADX": adx_line, "PlusDI": plus_di, "MinusDI": minus_di}, index=close.index)


def bollinger(close: pd.Series, period: int = 20, deviations: float = 2.0) -> pd.DataFrame:
    values = pd.to_numeric(close, errors="coerce")
    middle = values.rolling(period, min_periods=period).mean()
    std = values.rolling(period, min_periods=period).std()
    upper = middle + deviations * std
    lower = middle - deviations * std
    bandwidth = ((upper - lower) / middle.replace(0, math.nan)) * 100
    pct_b = (values - lower) / (upper - lower).replace(0, math.nan)
    return pd.DataFrame({"BollingerPctB": pct_b, "BollingerBandwidthPct": bandwidth}, index=close.index)


def latest_number(series: pd.Series, default: float | None = None) -> float | None:
    cleaned = pd.to_numeric(series, errors="coerce").dropna()
    if cleaned.empty:
        return default
    return round(float(cleaned.iloc[-1]), 4)

