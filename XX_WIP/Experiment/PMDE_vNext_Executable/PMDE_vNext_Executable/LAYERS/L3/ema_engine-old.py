
import pandas as pd
from CONFIG.settings import EMA_PERIOD


class EMAEngine:

    @staticmethod
    def get_ema200(df: pd.DataFrame):

        ema = (
            df["Close"]
            .ewm(span=EMA_PERIOD, adjust=False)
            .mean()
        )

        latest_price = df["Close"].iloc[-1]

        ema_value = ema.iloc[-1]

        distance_pct = (
            ((latest_price - ema_value) / ema_value) * 100
        )

        return {
            "ema200": round(ema_value, 4),
            "latest_price": round(latest_price, 4),
            "distance_pct": round(distance_pct, 4)
        }
