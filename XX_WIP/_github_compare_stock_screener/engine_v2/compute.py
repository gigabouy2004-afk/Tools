from __future__ import annotations

from typing import Any

from .config import DEFAULT_ENGINE_CONFIG, EngineConfig
from .data_provider import load_optional_price_data, load_price_data
from .indicators import calculate_macd, compute_daily_indicators


def compute_symbol_indicators(symbol: str, config: EngineConfig = DEFAULT_ENGINE_CONFIG) -> dict[str, Any]:
    df_1d = load_price_data(symbol, "1d", config.data)
    df_4h = load_optional_price_data(symbol, "4h", config.data)
    df_1h = load_optional_price_data(symbol, "1h", config.data)
    values = compute_daily_indicators(df_1d, config.indicators)
    values.update({
        "macd_4h": calculate_macd(df_4h, config.indicators.macd),
        "macd_1h": calculate_macd(df_1h, config.indicators.macd),
        "baseline_macd_4h": calculate_macd(df_4h, config.indicators.baseline_macd),
        "baseline_macd_1h": calculate_macd(df_1h, config.indicators.baseline_macd),
        "latest_price": round(float(df_1d["Close"].iloc[-1]), 4),
        "price_rows_1d": len(df_1d),
        "price_rows_4h": len(df_4h),
        "price_rows_1h": len(df_1h),
    })
    return values
