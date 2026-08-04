from pathlib import Path
import re

import pandas as pd


class SymbolLoader:

    SYMBOL_COLUMN_CANDIDATES = [
        "symbol",
        "ticker",
        "code",
        "stock_code",
        "stock code",
        "scrip",
        "security code",
        "tradingsymbol",
        "trading_symbol"
    ]

    EXCHANGE_SUFFIX = {
        "NSE": ".NS",
        "BSE": ".BO"
    }

    @staticmethod
    def normalize_list(
        values,
        default_exchange=None,
        sort_unique=True
    ) -> list[str]:

        return SymbolLoader._normalize_symbols(
            values or [],
            default_exchange=default_exchange,
            sort_unique=sort_unique
        )

    @staticmethod
    def merge_sources(
        symbol_sources,
        sort_unique=True
    ) -> list[str]:

        symbols = []

        for source_symbols in symbol_sources:

            symbols.extend(
                source_symbols or []
            )

        return SymbolLoader._dedupe(
            symbols,
            sort_unique=sort_unique
        )

    @staticmethod
    def load(
        input_file,
        symbol_column=None,
        exchange_column=None,
        default_exchange=None,
        fallback_symbols=None,
        sort_unique=True
    ) -> list[str]:

        fallback_symbols = fallback_symbols or []

        if input_file is None:

            return SymbolLoader._normalize_symbols(
                fallback_symbols,
                default_exchange=default_exchange,
                sort_unique=sort_unique
            )

        input_path = Path(input_file)

        if not input_path.exists():
            raise FileNotFoundError(
                f"Input symbol file not found: {input_path}"
            )

        if not input_path.is_file():

            raise ValueError(
                f"Input symbol path is not a file: {input_path}"
            )

        try:

            df = SymbolLoader._read_table(
                input_path
            )

        except Exception as error:
            raise RuntimeError(
                f"Failed to read input symbol file "
                f"{input_path}: {error}"
            ) from error

        if df.empty:
            raise ValueError(
                f"Input symbol file is empty: {input_path}"
            )

        selected_symbol_column = (
            SymbolLoader._select_symbol_column(
                df,
                symbol_column
            )
        )

        selected_exchange_column = (
            SymbolLoader._select_optional_column(
                df,
                exchange_column
            )
        )

        symbols = []

        for _, row in df.iterrows():

            raw_symbol = row[
                selected_symbol_column
            ]

            raw_exchange = (
                row[selected_exchange_column]
                if selected_exchange_column is not None
                else default_exchange
            )

            symbol = SymbolLoader._normalize_symbol(
                raw_symbol,
                exchange=raw_exchange
            )

            if symbol:

                symbols.append(symbol)

        if not symbols:

            raise ValueError(
                f"No usable symbols found in {input_path}"
            )

        return SymbolLoader._dedupe(
            symbols,
            sort_unique=sort_unique
        )

    @staticmethod
    def _read_table(
        input_path: Path
    ) -> pd.DataFrame:

        extension = input_path.suffix.lower()

        if extension in [".xlsx", ".xls"]:

            df = pd.read_excel(
                input_path,
                dtype=str
            )

        else:

            df = pd.read_csv(
                input_path,
                dtype=str,
                keep_default_na=False,
                header=None
            )

            if SymbolLoader._first_row_looks_like_header(
                df
            ):

                df.columns = [
                    str(value).strip()
                    for value in df.iloc[0].tolist()
                ]

                df = df.iloc[1:].reset_index(
                    drop=True
                )

        df = df.dropna(
            how="all"
        )

        df.columns = [
            str(column).strip()
            for column in df.columns
        ]

        return df

    @staticmethod
    def _first_row_looks_like_header(
        df: pd.DataFrame
    ) -> bool:

        if df.empty:

            return False

        first_row_values = [
            str(value).strip().lower()
            for value in df.iloc[0].tolist()
        ]

        return any(
            value in SymbolLoader.SYMBOL_COLUMN_CANDIDATES
            for value in first_row_values
        )

    @staticmethod
    def _select_symbol_column(
        df: pd.DataFrame,
        configured_column
    ):

        if configured_column is not None:

            return SymbolLoader._require_column(
                df,
                configured_column,
                "symbol"
            )

        normalized_columns = {
            str(column).strip().lower(): column
            for column in df.columns
        }

        for candidate in SymbolLoader.SYMBOL_COLUMN_CANDIDATES:

            if candidate in normalized_columns:

                return normalized_columns[candidate]

        if len(df.columns) == 1:

            return df.columns[0]

        first_column = df.columns[0]

        if SymbolLoader._column_looks_like_symbols(
            df[first_column]
        ):

            return first_column

        raise ValueError(
            "Multiple input columns found but no symbol "
            "column was configured. Set INPUT_SYMBOL_COLUMN "
            "in CONFIG/settings.py."
        )

    @staticmethod
    def _select_optional_column(
        df: pd.DataFrame,
        configured_column
    ):

        if configured_column is None:

            return None

        return SymbolLoader._require_column(
            df,
            configured_column,
            "exchange"
        )

    @staticmethod
    def _require_column(
        df: pd.DataFrame,
        configured_column,
        label
    ):

        for column in df.columns:

            if (
                str(column).strip().lower()
                == str(configured_column).strip().lower()
            ):

                return column

        raise ValueError(
            f"Configured {label} column "
            f"'{configured_column}' was not found. "
            f"Available columns: {list(df.columns)}"
        )

    @staticmethod
    def _column_looks_like_symbols(
        series: pd.Series
    ) -> bool:

        values = [
            str(value).strip()
            for value in series.dropna().head(20)
            if str(value).strip()
        ]

        if not values:

            return False

        matches = [
            SymbolLoader._is_symbol_like(value)
            for value in values
        ]

        return (
            sum(matches) /
            len(matches)
        ) >= 0.70

    @staticmethod
    def _normalize_symbols(
        values,
        default_exchange=None,
        sort_unique=True
    ) -> list[str]:

        values = SymbolLoader._expand_symbol_values(
            values
        )

        symbols = [
            SymbolLoader._normalize_symbol(
                value,
                exchange=default_exchange
            )
            for value in values
        ]

        symbols = [
            symbol
            for symbol in symbols
            if symbol
        ]

        return SymbolLoader._dedupe(
            symbols,
            sort_unique=sort_unique
        )

    @staticmethod
    def _expand_symbol_values(
        values
    ) -> list:

        if isinstance(values, str):

            values = [values]

        expanded = []

        for value in values or []:

            if isinstance(value, str):

                expanded.extend(
                    part.strip()
                    for part in re.split(
                        r"[,;|]+",
                        value
                    )
                    if part.strip()
                )

            else:

                expanded.append(value)

        return expanded

    @staticmethod
    def _normalize_symbol(
        value,
        exchange=None
    ):

        if value is None:

            return None

        symbol = str(value).strip().upper()

        if not symbol:

            return None

        if symbol in [
            "SYMBOL",
            "TICKER",
            "CODE",
            "NAN",
            "NONE"
        ]:

            return None

        symbol = re.sub(
            r"\s+",
            "",
            symbol
        )

        if not SymbolLoader._is_symbol_like(symbol):

            return None

        if "." in symbol:

            return symbol

        exchange_code = (
            str(exchange).strip().upper()
            if exchange is not None
            else ""
        )

        suffix = SymbolLoader.EXCHANGE_SUFFIX.get(
            exchange_code
        )

        if suffix:

            return f"{symbol}{suffix}"

        return symbol

    @staticmethod
    def _is_symbol_like(
        value
    ) -> bool:

        value = str(value).strip().upper()

        return bool(
            re.fullmatch(
                r"[A-Z0-9][A-Z0-9.\-^=]{0,19}",
                value
            )
        )

    @staticmethod
    def _dedupe(
        symbols: list[str],
        sort_unique=True
    ) -> list[str]:

        unique_symbols = list(
            dict.fromkeys(symbols)
        )

        if sort_unique:

            return sorted(unique_symbols)

        return unique_symbols
