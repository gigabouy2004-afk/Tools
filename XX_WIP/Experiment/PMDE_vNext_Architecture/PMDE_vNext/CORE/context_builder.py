
"""Builds MarketContext objects from raw market data."""

from MODELS.contracts import MarketContext
from datetime import datetime


def build_market_context(
    symbol: str,
    timeframe: str,
    latest_price: float,
    ema200: float,
    macd: float,
    macd_signal: float,
    macd_histogram: float,
    macd_histogram_slope: float
) -> MarketContext:

    ema_distance_pct = (
        ((latest_price - ema200) / ema200) * 100
        if ema200 else 0
    )

    return MarketContext(
        symbol=symbol,
        timestamp=datetime.utcnow(),
        timeframe=timeframe,
        latest_price=latest_price,
        ema200=ema200,
        ema_distance_pct=ema_distance_pct,
        macd=macd,
        macd_signal=macd_signal,
        macd_histogram=macd_histogram,
        macd_histogram_slope=macd_histogram_slope
    )
