import yfinance as yf
import pandas as pd


class DataLoader:

    @staticmethod
    def load(
        symbol: str,
        timeframe: str
    ):

        interval_map = {
            "1h": "1h",
            "4h": "1h",
            "1d": "1d"
        }

        period_map = {
            "1h": "30d",
            "4h": "60d",
            "1d": "1y"
        }

        interval = interval_map[timeframe]
        period = period_map[timeframe]

        df = yf.download(
            symbol,
            interval=interval,
            period=period,
            auto_adjust=True,
            progress=False
        )

        if df.empty:
            raise ValueError(
                f"No data for {symbol}"
            )

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = (
                df.columns.get_level_values(0)
            )

        df.columns = [
            str(col).title().strip()
            for col in df.columns
        ]

        if timeframe == "4h":

            df = (
                df.resample("4h")
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