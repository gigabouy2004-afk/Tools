from __future__ import annotations

import pandas as pd
import yfinance as yf

from .config import DataConfig


def _normalize_downloaded_frame(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    if df.empty:
        raise ValueError("No price data returned")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.rename(columns={column: str(column).capitalize() for column in df.columns})
    required = ["Open", "High", "Low", "Close", "Volume"]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(f"Price data missing required columns: {', '.join(missing)}")
    df = df[required].dropna(subset=["Close"]).copy()
    if timeframe == "4h":
        df = (
            df.resample("4h")
            .agg({
                "Open": "first",
                "High": "max",
                "Low": "min",
                "Close": "last",
                "Volume": "sum",
            })
            .dropna()
        )
    return df


def load_price_data(symbol: str, timeframe: str, config: DataConfig) -> pd.DataFrame:
    if timeframe == "1d":
        period = config.daily_period
        interval = config.daily_interval
    elif timeframe == "1h":
        period = config.intraday_period
        interval = config.one_hour_interval
    elif timeframe == "4h":
        period = config.intraday_period
        interval = config.four_hour_interval
    else:
        raise ValueError(f"Unsupported timeframe: {timeframe}")
    df = yf.download(symbol, period=period, interval=interval, auto_adjust=True, progress=False, threads=False)
    return _normalize_downloaded_frame(df, timeframe)


def empty_price_data() -> pd.DataFrame:
    return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])


def load_optional_price_data(symbol: str, timeframe: str, config: DataConfig) -> pd.DataFrame:
    try:
        return load_price_data(symbol, timeframe, config)
    except Exception:
        return empty_price_data()
