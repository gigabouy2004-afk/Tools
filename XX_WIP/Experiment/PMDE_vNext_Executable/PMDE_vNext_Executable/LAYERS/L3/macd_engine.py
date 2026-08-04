import pandas as pd

from CONFIG.settings import (
    MACD_FAST,
    MACD_SLOW,
    MACD_SIGNAL,
    MACD_TIMEFRAMES
)

from IO.data_loader import DataLoader


class MACDEngine:

    @staticmethod
    def calculate_macd(
        df: pd.DataFrame
    ):

        close = pd.to_numeric(
            df["Close"],
            errors="coerce"
        )

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

        latest_macd = float(
            macd.values[-1]
        )

        latest_signal = float(
            signal.values[-1]
        )

        latest_histogram = float(
            histogram.values[-1]
        )

        hist_slope = float(
            histogram.values[-1] -
            histogram.values[-2]
        )

        crossover_state = (
            "BULLISH"
            if latest_macd > latest_signal
            else "BEARISH"
        )

        return {
            "macd": round(latest_macd, 4),
            "signal": round(latest_signal, 4),
            "histogram": round(
                latest_histogram,
                4
            ),
            "histogram_slope": round(
                hist_slope,
                4
            ),
            "crossover_distance": round(
                abs(
                    latest_macd -
                    latest_signal
                ),
                4
            ),
            "state": crossover_state
        }

    @staticmethod
    def get_macd_suite(
        symbol: str
    ):

        suite = {}

        for timeframe in MACD_TIMEFRAMES:

            df = DataLoader.load(
                symbol,
                timeframe
            )

            suite[timeframe] = (
                MACDEngine.calculate_macd(df)
            )

        return suite