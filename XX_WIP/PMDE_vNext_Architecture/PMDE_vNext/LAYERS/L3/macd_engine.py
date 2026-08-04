import pandas as pd

from CONFIG.settings import (
    MACD_FAST,
    MACD_SLOW,
    MACD_SIGNAL
)

from MODELS.contracts import MACDResult


class MACDEngine:

    @staticmethod
    def calculate_macd(
        df: pd.DataFrame,
        timeframe: str
    ) -> MACDResult:

        close = pd.to_numeric(
            df["Close"],
            errors="coerce"
        ).dropna()

        if len(close) < 2:

            raise ValueError(
                "MACD requires at least two close values"
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

        previous_histogram = float(
            histogram.values[-2]
        )

        hist_slope = float(
            latest_histogram -
            previous_histogram
        )

        spread_contracting = (
            latest_histogram < 0
            and
            latest_histogram > previous_histogram
        )

        crossover_state = (
            "BULLISH"
            if latest_macd > latest_signal
            else "BEARISH"
        )

        return MACDResult(
            timeframe=timeframe,
            macd=round(latest_macd, 4),
            signal=round(latest_signal, 4),
            histogram=round(
                latest_histogram,
                4
            ),
            histogram_slope=round(
                hist_slope,
                4
            ),
            spread=round(
                latest_histogram,
                4
            ),
            spread_delta=round(
                hist_slope,
                4
            ),
            spread_contracting=spread_contracting,
            histogram_rising_streak=(
                MACDEngine._rising_streak(
                    histogram
                )
            ),
            crossover_distance=round(
                abs(
                    latest_macd -
                    latest_signal
                ),
                4
            ),
            state=crossover_state
        )

    @staticmethod
    def _rising_streak(
        series: pd.Series
    ) -> int:

        streak = 0

        values = series.dropna().tolist()

        for index in range(
            len(values) - 1,
            0,
            -1
        ):

            if values[index] <= values[index - 1]:

                break

            streak += 1

        return streak
