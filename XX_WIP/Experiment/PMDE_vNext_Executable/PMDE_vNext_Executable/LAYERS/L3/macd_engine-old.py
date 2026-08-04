
import pandas as pd
from MODELS.contracts import MACDResult
from CONFIG.settings import (
    MACD_FAST,
    MACD_SLOW,
    MACD_SIGNAL
)


class MACDEngine:

    @staticmethod
    def get_macd(df: pd.DataFrame, timeframe: str):

        close = df["Close"]

        ema_fast = close.ewm(
            span=MACD_FAST,
            adjust=False
        ).mean()

        ema_slow = close.ewm(
            span=MACD_SLOW,
            adjust=False
        ).mean()

        macd = ema_fast - ema_slow

        signal = macd.ewm(
            span=MACD_SIGNAL,
            adjust=False
        ).mean()

        histogram = macd - signal

        hist_slope = histogram.iloc[-1] - histogram.iloc[-2]

        return MACDResult(
            timeframe=timeframe,
            macd=round(macd.iloc[-1], 4),
            signal=round(signal.iloc[-1], 4),
            histogram=round(histogram.iloc[-1], 4),
            histogram_slope=round(hist_slope, 4),
            crossover_distance=round(
                abs(macd.iloc[-1] - signal.iloc[-1]),
                4
            )
        )
