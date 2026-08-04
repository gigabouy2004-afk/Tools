
"""Blind computational MACD engine."""

from MODELS.contracts import MACDResult


class MACDEngine:

    @staticmethod
    def get_macd(
        symbol: str,
        timeframe: str,
        macd: float,
        signal: float,
        histogram: float,
        histogram_slope: float
    ) -> MACDResult:

        crossover_distance = abs(macd - signal)

        return MACDResult(
            symbol=symbol,
            timeframe=timeframe,
            macd=macd,
            signal=signal,
            histogram=histogram,
            histogram_slope=histogram_slope,
            crossover_distance=crossover_distance
        )
