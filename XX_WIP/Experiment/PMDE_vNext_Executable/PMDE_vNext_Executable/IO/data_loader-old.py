
import yfinance as yf
import pandas as pd


class DataLoader:

    @staticmethod
    def load(symbol: str, timeframe: str):

        interval_map = {
            "1d": "1d",
            "4h": "1h"
        }

        period_map = {
            "1d": "1y",
            "4h": "60d"
        }

        interval = interval_map.get(timeframe, "1d")
        period = period_map.get(timeframe, "1y")

        df = yf.download(
            symbol,
            period=period,
            interval=interval,
            auto_adjust=True,
            progress=False
        )

        if df.empty:
            raise ValueError(f"No data returned for {symbol}")

        if timeframe == "4h":
            df = (
                df.resample("4H")
                .agg({
                    "Open": "first",
                    "High": "max",
                    "Low": "min",
                    "Close": "last",
                    "Volume": "sum"
                })
                .dropna()
            )

        return df
