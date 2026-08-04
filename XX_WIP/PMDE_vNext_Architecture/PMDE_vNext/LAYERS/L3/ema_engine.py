import pandas as pd

from CONFIG.settings import EMA_PERIOD, EMA_SLOPE_LOOKBACK
from MODELS.contracts import EMAResult


class EMAEngine:

    @staticmethod
    def get_ema200(
        df: pd.DataFrame,
        timeframe: str = "1d"
    ) -> EMAResult:

        close = pd.to_numeric(
            df["Close"],
            errors="coerce"
        ).dropna()

        if close.empty:

            raise ValueError(
                "EMA200 requires close values"
            )

        latest_price = float(
            close.values[-1]
        )

        data_points = len(
            close
        )

        if data_points < EMA_PERIOD:

            return EMAResult(
                timeframe=timeframe,
                ema200=None,
                latest_price=round(
                    latest_price,
                    4
                ),
                distance_pct=None,
                slope_pct=None,
                slope_state="INSUFFICIENT_HISTORY",
                zone="INSUFFICIENT_HISTORY",
                data_points=data_points,
                is_sufficient=False,
                reason=(
                    f"EMA{EMA_PERIOD} requires at least "
                    f"{EMA_PERIOD} daily closes; "
                    f"{data_points} available"
                )
            )

        ema = close.ewm(
            span=EMA_PERIOD,
            adjust=False
        ).mean()

        ema_value = ema.values[-1]

        slope_index = max(
            0,
            len(ema) - EMA_SLOPE_LOOKBACK - 1
        )

        prior_ema_value = ema.values[slope_index]

        ema_slope_pct = (
            (
                ema_value -
                prior_ema_value
            ) / prior_ema_value
        ) * 100

        distance_pct = (
            (
                latest_price - ema_value
            ) / ema_value
        ) * 100

        distance_pct = round(
            float(distance_pct),
            4
        )

        zone = (
            "BULL_ZONE"
            if distance_pct > 0
            else "BEAR_ZONE"
        )

        slope_state = "RISING"

        if ema_slope_pct < 0:

            slope_state = "FALLING"

        elif abs(ema_slope_pct) < 0.25:

            slope_state = "FLAT"

        return EMAResult(
            timeframe=timeframe,
            ema200=round(float(ema_value), 4),
            latest_price=round(float(latest_price), 4),
            distance_pct=distance_pct,
            slope_pct=round(float(ema_slope_pct), 4),
            slope_state=slope_state,
            zone=zone,
            data_points=data_points,
            is_sufficient=True,
            reason=None
        )
