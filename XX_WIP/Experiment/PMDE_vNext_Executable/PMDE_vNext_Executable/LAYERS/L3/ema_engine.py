import pandas as pd

from CONFIG.settings import EMA_PERIOD


class EMAEngine:

    @staticmethod
    def get_ema200(
        df: pd.DataFrame
    ):

        close = pd.to_numeric(
            df["Close"],
            errors="coerce"
        )

        ema = close.ewm(
            span=EMA_PERIOD,
            adjust=False
        ).mean()

        latest_price = close.values[-1]

        ema_value = ema.values[-1]

        distance_pct = (
            (
                latest_price - ema_value
            ) / ema_value
        ) * 100

        return {
            "ema200": round(float(ema_value), 4),
            "latest_price": round(float(latest_price), 4),
            "distance_pct": round(
                float(distance_pct),
                4
            )
        }