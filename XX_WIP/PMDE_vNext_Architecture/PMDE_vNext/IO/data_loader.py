import pandas as pd
import yfinance as yf

from datetime import UTC, datetime

from CONFIG.settings import (
    DATA_INTERVALS,
    DATA_PERIODS,
    LIVE_PRICE_INTERVAL,
    LIVE_PRICE_PERIOD,
    LIVE_PRICE_PREPOST,
    USE_LIVE_PRICE_FOR_DAILY
)


class DataLoader:

    _cache = {}
    _fetch_timestamps = {}
    _live_quote_cache = {}

    @staticmethod
    def load(
        symbol: str,
        timeframe: str,
        use_live_price: bool | None = None
    ):

        apply_live_price = (
            USE_LIVE_PRICE_FOR_DAILY
            if use_live_price is None
            else use_live_price
        )

        cache_key = (
            symbol.upper(),
            timeframe,
            apply_live_price
            if timeframe == "1d"
            else None
        )

        if cache_key in DataLoader._cache:

            return DataLoader._cache[
                cache_key
            ].copy()

        interval = DATA_INTERVALS[timeframe]
        period = DATA_PERIODS[timeframe]

        df = yf.download(
            symbol,
            interval=interval,
            period=period,
            auto_adjust=True,
            prepost=LIVE_PRICE_PREPOST,
            progress=False
        )

        if df.empty:
            raise ValueError(
                f"No data for {symbol}"
            )

        df = DataLoader._normalize_columns(
            df
        )

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

        if (
            timeframe == "1d"
            and
            apply_live_price
        ):

            df = DataLoader._apply_live_daily_quote(
                symbol,
                df
            )

        DataLoader._cache[cache_key] = df.copy()
        DataLoader._fetch_timestamps[cache_key] = (
            datetime.now(UTC).isoformat()
        )

        return df

    @staticmethod
    def get_fetch_timestamp(
        symbol: str,
        timeframe: str,
        use_live_price: bool | None = None
    ) -> str | None:

        apply_live_price = (
            USE_LIVE_PRICE_FOR_DAILY
            if use_live_price is None
            else use_live_price
        )

        cache_key = (
            symbol.upper(),
            timeframe,
            apply_live_price
            if timeframe == "1d"
            else None
        )

        return DataLoader._fetch_timestamps.get(
            cache_key
        )

    @staticmethod
    def load_live_quote(
        symbol: str
    ) -> dict | None:

        cache_key = symbol.upper()

        if cache_key in DataLoader._live_quote_cache:

            return DataLoader._live_quote_cache[
                cache_key
            ].copy()

        quote = (
            DataLoader._load_intraday_quote(
                symbol
            )
            or
            DataLoader._load_fast_info_quote(
                symbol
            )
        )

        if quote:

            DataLoader._live_quote_cache[
                cache_key
            ] = quote.copy()

        return (
            quote.copy()
            if quote
            else None
        )

    @staticmethod
    def _load_intraday_quote(
        symbol: str
    ) -> dict | None:

        try:

            df = yf.download(
                symbol,
                interval=LIVE_PRICE_INTERVAL,
                period=LIVE_PRICE_PERIOD,
                auto_adjust=True,
                prepost=LIVE_PRICE_PREPOST,
                progress=False
            )

        except Exception:

            return None

        if df.empty:

            return None

        df = DataLoader._normalize_columns(
            df
        )

        close = pd.to_numeric(
            df["Close"],
            errors="coerce"
        ).dropna()

        if close.empty:

            return None

        latest_index = close.index[-1]
        valid_df = df.loc[
            close.index
        ]

        return {
            "price": float(
                close.iloc[-1]
            ),
            "open": DataLoader._safe_float(
                valid_df["Open"].iloc[0]
            ),
            "high": DataLoader._safe_float(
                pd.to_numeric(
                    valid_df["High"],
                    errors="coerce"
                ).max()
            ),
            "low": DataLoader._safe_float(
                pd.to_numeric(
                    valid_df["Low"],
                    errors="coerce"
                ).min()
            ),
            "volume": DataLoader._safe_float(
                pd.to_numeric(
                    valid_df["Volume"],
                    errors="coerce"
                ).fillna(0).sum()
            ),
            "timestamp": latest_index,
            "source": LIVE_PRICE_INTERVAL
        }

    @staticmethod
    def _load_fast_info_quote(
        symbol: str
    ) -> dict | None:

        try:

            fast_info = yf.Ticker(
                symbol
            ).fast_info

        except Exception:

            return None

        price = DataLoader._first_quote_value(
            fast_info,
            [
                "lastPrice",
                "last_price",
                "regularMarketPrice"
            ]
        )

        if price is None:

            return None

        return {
            "price": float(price),
            "open": DataLoader._first_quote_value(
                fast_info,
                [
                    "open",
                    "regularMarketOpen"
                ]
            ),
            "high": DataLoader._first_quote_value(
                fast_info,
                [
                    "dayHigh",
                    "day_high",
                    "regularMarketDayHigh"
                ]
            ),
            "low": DataLoader._first_quote_value(
                fast_info,
                [
                    "dayLow",
                    "day_low",
                    "regularMarketDayLow"
                ]
            ),
            "volume": DataLoader._first_quote_value(
                fast_info,
                [
                    "lastVolume",
                    "last_volume",
                    "regularMarketVolume"
                ]
            ),
            "timestamp": datetime.now(
                UTC
            ),
            "source": "fast_info"
        }

    @staticmethod
    def _apply_live_daily_quote(
        symbol: str,
        df: pd.DataFrame
    ) -> pd.DataFrame:

        quote = DataLoader.load_live_quote(
            symbol
        )

        if not quote:

            return df

        updated_df = df.copy()

        session_date = DataLoader._quote_session_date(
            quote["timestamp"]
        )

        row_label = DataLoader._find_or_create_daily_row(
            updated_df,
            session_date,
            quote
        )

        current_high = DataLoader._safe_float(
            updated_df.at[
                row_label,
                "High"
            ]
        )

        current_low = DataLoader._safe_float(
            updated_df.at[
                row_label,
                "Low"
            ]
        )

        current_volume = DataLoader._safe_float(
            updated_df.at[
                row_label,
                "Volume"
            ]
        )

        price = quote["price"]
        quote_high = quote.get("high") or price
        quote_low = quote.get("low") or price
        quote_volume = quote.get("volume")

        updated_df.at[
            row_label,
            "Close"
        ] = price

        updated_df.at[
            row_label,
            "Open"
        ] = (
            quote.get("open")
            or
            updated_df.at[
                row_label,
                "Open"
            ]
            or
            price
        )

        updated_df.at[
            row_label,
            "High"
        ] = max(
            value
            for value in [
                current_high,
                quote_high,
                price
            ]
            if value is not None
        )

        updated_df.at[
            row_label,
            "Low"
        ] = min(
            value
            for value in [
                current_low,
                quote_low,
                price
            ]
            if value is not None
        )

        if quote_volume is not None:

            updated_df.at[
                row_label,
                "Volume"
            ] = max(
                current_volume or 0,
                quote_volume
            )

        return updated_df.sort_index()

    @staticmethod
    def _find_or_create_daily_row(
        df: pd.DataFrame,
        session_date,
        quote: dict
    ):

        for index_value in df.index:

            if pd.Timestamp(
                index_value
            ).date() == session_date:

                return index_value

        row_label = pd.Timestamp(
            session_date
        )

        price = quote["price"]

        df.loc[
            row_label,
            [
                "Open",
                "High",
                "Low",
                "Close",
                "Volume"
            ]
        ] = [
            quote.get("open") or price,
            quote.get("high") or price,
            quote.get("low") or price,
            price,
            quote.get("volume") or 0
        ]

        return row_label

    @staticmethod
    def _quote_session_date(
        timestamp
    ):

        ts = pd.Timestamp(
            timestamp
        )

        if ts.tzinfo is not None:

            return ts.tz_convert(
                "America/New_York"
            ).date()

        return ts.date()

    @staticmethod
    def _normalize_columns(
        df: pd.DataFrame
    ) -> pd.DataFrame:

        normalized_df = df.copy()

        if isinstance(
            normalized_df.columns,
            pd.MultiIndex
        ):

            normalized_df.columns = (
                normalized_df.columns.get_level_values(0)
            )

        normalized_df.columns = [
            str(col).title().strip()
            for col in normalized_df.columns
        ]

        normalized_df.columns.name = None

        return normalized_df

    @staticmethod
    def _first_quote_value(
        quote_source,
        keys: list[str]
    ):

        for key in keys:

            try:

                value = quote_source.get(
                    key
                )

            except Exception:

                value = getattr(
                    quote_source,
                    key,
                    None
                )

            value = DataLoader._safe_float(
                value
            )

            if value is not None:

                return value

        return None

    @staticmethod
    def _safe_float(
        value
    ):

        try:

            if pd.isna(value):

                return None

            return float(value)

        except (TypeError, ValueError):

            return None
