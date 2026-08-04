from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
import yfinance as yf

from config import DEFAULTS
from column_renderer import EXPORT_COLUMNS
from html_formatter import generate_html_report

logger = logging.getLogger(__name__)

OUTPUT_COLUMNS = EXPORT_COLUMNS

CANDIDATE_STATE_ORDER = [
    "PRE_BULL_CROSSOVER",
    "PRE_BEAR_CROSSOVER",
    "BULL_EXTENDED",
    "BEAR_EXTENDED",
    "SETUP_CANDIDATE",
    "BULLISH_DIVERGENCE",
    "BEARISH_DIVERGENCE",
    "STATUS_QUO",
]

BULLISH_CANDIDATE_STATES = {
    "PRE_BULL_CROSSOVER",
    "BULL_EXTENDED",
    "SETUP_CANDIDATE",
    "BULLISH_DIVERGENCE",
}

POSITIONING_BULLISH_ALIGNMENT_REQUIRED_STATES = {
    "SETUP_CANDIDATE",
}

BEARISH_CANDIDATE_STATES = {
    "PRE_BEAR_CROSSOVER",
    "BEAR_EXTENDED",
    "BEARISH_DIVERGENCE",
}

# Map yfinance exchange codes to standard names
EXCHANGE_MAP = {
    "NMS": "NASDAQ",  # NASDAQ Stock Market
    "NYQ": "NYSE",    # New York Stock Exchange
    "NYA": "NYSE",    # NYSE American (formerly AMEX)
    "BOM": "BSE",     # Bombay Stock Exchange (India)
    "NSE": "NSE",     # National Stock Exchange of India
    "NSI": "NSE",     # Yahoo Finance code for NSE India
    "NMC": "NASDAQ",  # NASDAQ OMX
    "Q": "NASDAQ",    # NASDAQ alternative
    "N": "NYSE",      # NYSE alternative
    "A": "NYSEAMERICAN",  # NASDAQ Trader listing exchange code
    "P": "NYSEARCA",      # NYSE Arca, common for ETFs
    "Z": "BATS",          # Cboe BZX
}

def normalize_exchange(exchange_code: str) -> str:
    """Map yfinance exchange code to standard name."""
    if not exchange_code:
        return None
    code = exchange_code.upper().strip()
    return EXCHANGE_MAP.get(code, code)


@dataclass
class ScreenerFilters:
    exchanges: list[str] = field(default_factory=list)
    sectors: list[str] = field(default_factory=list)
    industries: list[str] = field(default_factory=list)
    types: list[str] = field(default_factory=list)
    include_etfs: bool = True
    price_min: float | None = None
    price_max: float | None = None
    market_cap_min: float | None = None
    market_cap_max: float | None = None
    avg_volume_min: float | None = None
    avg_volume_max: float | None = None
    rsi_min: float | None = None
    rsi_max: float | None = None
    setup_rsi_max: float | None = None
    adx_min: float | None = None
    adx_max: float | None = None
    bollinger_pct_min: float | None = None
    bollinger_pct_max: float | None = None
    pre_bull_confidence_min: float | None = None
    states: list[str] = field(default_factory=list)


@dataclass
class SymbolProfile:
    symbol: str
    company_name: str | None = None
    exchange: str | None = None
    sector: str | None = None
    industry: str | None = None
    market_cap: float | None = None
    latest_price: float | None = None
    avg_daily_volume: float | None = None
    avg_monthly_volume: float | None = None
    info: dict[str, Any] = field(default_factory=dict)
    instrument_type: str | None = None


class StockScreener:
    def __init__(self, filters: ScreenerFilters):
        self.filters = filters

    @staticmethod
    def _worker_count(symbol_count: int) -> int:
        if symbol_count <= 1:
            return 1
        configured = max(1, int(DEFAULTS.max_symbol_workers))
        return min(configured, symbol_count)

    @staticmethod
    def _normalize_universe_symbol(symbol: str, exchange: str | None = None, source_is_nse: bool = False) -> str:
        normalized = str(symbol).strip().upper()
        if not normalized:
            return ""
        exchange_name = normalize_exchange(exchange) if exchange else None
        if (exchange_name == "NSE" or source_is_nse) and "." not in normalized:
            return f"{normalized}.NS"
        return normalized

    @staticmethod
    def _looks_like_nse_equity_master(columns: list[str]) -> bool:
        normalized_columns = {str(col).strip().upper() for col in columns}
        return "SYMBOL" in normalized_columns and "SERIES" in normalized_columns and "ISIN NUMBER" in normalized_columns

    @staticmethod
    def _read_universe_frame(symbols_file: str, header: int | None = 0) -> pd.DataFrame:
        with open(symbols_file, "r", encoding="utf-8-sig", errors="replace") as handle:
            first_line = handle.readline()
        delimiter = None
        if first_line.count("|") > first_line.count(",") and first_line.count("|") > 0:
            delimiter = "|"
        elif "\t" in first_line:
            delimiter = "\t"
        try:
            if delimiter:
                return pd.read_csv(symbols_file, dtype=str, header=header, sep=delimiter)
            return pd.read_csv(symbols_file, dtype=str, header=header)
        except Exception:
            return pd.read_csv(symbols_file, dtype=str, header=header)

    @staticmethod
    def _normalized_column_name(column: object) -> str:
        return " ".join(str(column).strip().upper().replace("_", " ").split())

    @staticmethod
    def _find_symbol_column(columns: list[object]) -> object | None:
        normalized = {StockScreener._normalized_column_name(column): column for column in columns}
        preferred_names = [
            "TICKER",
            "ACT SYMBOL",
            "NASDAQ SYMBOL",
            "SYMBOL",
        ]
        for name in preferred_names:
            if name in normalized:
                return normalized[name]
        return None

    @staticmethod
    def _nasdaq_flag_is_true(value: object) -> bool:
        return str(value).strip().upper() in {"Y", "YES", "TRUE", "1"}

    @staticmethod
    def _clean_universe_symbol(symbol: object) -> str:
        normalized = str(symbol).strip().upper()
        if not normalized or normalized in {"NAN", "NONE", "NULL", "SYMBOL", "TICKER", "ACT SYMBOL", "NASDAQ SYMBOL"}:
            return ""
        normalized = normalized.replace("/", "-")
        if any(ch.isspace() for ch in normalized) or "," in normalized or "|" in normalized:
            return ""
        if len(normalized) > 20:
            return ""
        allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-^=")
        if any(ch not in allowed for ch in normalized):
            return ""
        return normalized

    @staticmethod
    def _apply_universe_row_filters(df: pd.DataFrame) -> pd.DataFrame:
        filtered_df = df.copy()
        normalized_columns = {StockScreener._normalized_column_name(column): column for column in filtered_df.columns}
        test_issue_col = normalized_columns.get("TEST ISSUE")
        if test_issue_col is not None:
            filtered_df = filtered_df[~filtered_df[test_issue_col].map(StockScreener._nasdaq_flag_is_true)]
        return filtered_df

    @staticmethod
    def _filtered_universe_symbols(df: pd.DataFrame, symbol_col: object, source_is_nse: bool) -> list[str]:
        filtered_df = StockScreener._apply_universe_row_filters(df)
        symbols = [
            StockScreener._normalize_universe_symbol(cleaned, None, source_is_nse)
            for cleaned in filtered_df[symbol_col].map(StockScreener._clean_universe_symbol)
            if cleaned
        ]
        return pd.Series(symbols, dtype=str).dropna().str.strip().loc[lambda series: series != ""].unique().tolist()

    @staticmethod
    def load_universe(symbols_file: str) -> list[str]:
        # If an explicit symbols file is provided, load it. Otherwise, try
        # to discover the universe from the PMDE ACTIVE_BASELINE.csv file.
        if symbols_file:
            df = StockScreener._read_universe_frame(symbols_file)
            symbol_col = StockScreener._find_symbol_column(list(df.columns))
            if symbol_col is not None:
                source_is_nse = StockScreener._looks_like_nse_equity_master(list(df.columns))
                exchange_columns = [col for col in df.columns if str(col).strip().lower() == "exchange"]
                filtered_df = StockScreener._apply_universe_row_filters(df)
                exchange_series = df[exchange_columns[0]] if exchange_columns else pd.Series([None] * len(df), index=df.index)
                if source_is_nse or not exchange_columns:
                    symbols = StockScreener._filtered_universe_symbols(filtered_df, symbol_col, source_is_nse)
                else:
                    exchange_series = filtered_df[exchange_columns[0]]
                    symbols = [
                        StockScreener._normalize_universe_symbol(cleaned, exchange, source_is_nse)
                        for cleaned, exchange in zip(filtered_df[symbol_col].map(StockScreener._clean_universe_symbol), exchange_series)
                        if cleaned
                    ]
            else:
                # Some universe files are simple one-column ticker lists without
                # a header. Re-read without headers so A1 is kept as a symbol.
                df = StockScreener._read_universe_frame(symbols_file, header=None)
                symbols = [
                    StockScreener._normalize_universe_symbol(cleaned)
                    for cleaned in df.iloc[:, 0].map(StockScreener._clean_universe_symbol)
                    if cleaned
                ]
            series = pd.Series(symbols, dtype=str).dropna().str.strip()
            series = series[series.str.lower() != "symbol"]
            return series[series != ""].unique().tolist()

        # Default: load PMDE ACTIVE_BASELINE.csv if available
        baseline_path = r"d:\Tools\PMDE_vNext_Architecture\PMDE_vNext\STORAGE\ACTIVE_BASELINE.csv"
        try:
            df = pd.read_csv(baseline_path, dtype=str)
            if "symbol" in df.columns:
                return df["symbol"].dropna().str.strip().unique().tolist()
        except Exception:
            pass

        # Next fallback: look for user stock code lists in Tools\StockCodeMaster
        import os
        import glob

        scm_folder = r"d:\Tools\StockCodeMaster\USA"
        if os.path.isdir(scm_folder):
            symbols = []
            # CSV files
            for path in glob.glob(os.path.join(scm_folder, "00-NYSE_NASDAQ_Common_Stocks_Sector-Utilities.csv")):
                try:
                    d = pd.read_csv(path, dtype=str)
                    col = None
                    if "Symbol" in d.columns:
                        col = "Symbol"
                    elif "symbol" in d.columns:
                        col = "symbol"
                    elif "Ticker" in d.columns:
                        col = "Ticker"
                    if col:
                        symbols.extend(d[col].dropna().str.strip().tolist())
                        continue
                    # otherwise, try first column
                    first_col = d.columns[0]
                    symbols.extend(d[first_col].dropna().astype(str).str.strip().tolist())
                except Exception:
                    continue
            # TXT files (one ticker per line)
            for path in glob.glob(os.path.join(scm_folder, "*.txt")):
                try:
                    with open(path, "r", encoding="utf-8") as fh:
                        for ln in fh:
                            s = ln.strip()
                            if s:
                                symbols.append(s)
                except Exception:
                    continue

            if symbols:
                # dedupe and uppercase
                return list({s.upper() for s in symbols})

        raise ValueError("No universe provided and PMDE baseline not available.")

    @staticmethod
    def fetch_profile(symbol: str) -> SymbolProfile:
        ticker = yf.Ticker(symbol)
        fast_info = {}
        try:
            fast_info = ticker.fast_info or {}
        except Exception:
            pass
        info = {}
        try:
            info = ticker.info or {}
        except Exception:
            pass

        exchange = info.get("exchange") or info.get("exchangeTimezoneName")
        exchange = normalize_exchange(exchange)
        company_name = info.get("longName") or info.get("shortName") or info.get("displayName")
        sector = info.get("sector")
        industry = info.get("industry")
        market_cap = info.get("marketCap") or info.get("market_cap")
        latest_price = (
            fast_info.get("last_price")
            or fast_info.get("lastPrice")
            or info.get("regularMarketPrice")
            or info.get("currentPrice")
        )
        avg_daily_volume = (
            info.get("averageDailyVolume10Day")
            or info.get("averageVolume")
            or info.get("volumeAvg")
        )
        # instrument type (ETF / EQUITY / etc.) - try multiple keys
        instrument_type = (
            info.get("quoteType")
            or info.get("instrumentType")
            or fast_info.get("quoteType")
            or info.get("assetType")
        )

        return SymbolProfile(
            symbol=symbol.upper(),
            company_name=company_name,
            exchange=exchange,
            sector=sector,
            industry=industry,
            market_cap=float(market_cap) if market_cap is not None else None,
            latest_price=float(latest_price) if latest_price is not None else None,
            avg_daily_volume=float(avg_daily_volume) if avg_daily_volume is not None else None,
            info={**info, **fast_info},
            instrument_type=instrument_type,
        )

    @staticmethod
    def _load_price_data(symbol: str, timeframe: str) -> pd.DataFrame:
        if timeframe == "1d":
            interval = "1d"
            period = "2y"
        elif timeframe == "4h":
            interval = "1h"
            period = "90d"
        elif timeframe == "1h":
            interval = "30m"
            period = "30d"
        else:
            raise ValueError(f"Unsupported timeframe: {timeframe}")

        df = yf.download(
            symbol,
            interval=interval,
            period=period,
            auto_adjust=True,
            progress=False,
        )
        if df.empty:
            raise ValueError(f"No price data returned for {symbol} {timeframe}")

        # Normalize columns: handle yfinance MultiIndex columns by flattening
        new_cols = []
        for col in df.columns:
            if isinstance(col, tuple):
                # pick first non-empty part
                first = next((str(p) for p in col if p), str(col[0]))
                new_cols.append(first)
            else:
                new_cols.append(col)
        df.columns = new_cols
        df = df.rename(columns={col: str(col).capitalize() for col in df.columns})
        if timeframe == "4h":
            df = (
                df.resample("4h")
                .agg({
                    "Open": "first",
                    "High": "max",
                    "Low": "min",
                    "Close": "last",
                    "Volume": "sum",
                })
                .dropna()
            )
        return df

    @staticmethod
    def _empty_price_data() -> pd.DataFrame:
        return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])

    @staticmethod
    def _load_optional_price_data(symbol: str, timeframe: str) -> pd.DataFrame:
        try:
            return StockScreener._load_price_data(symbol, timeframe)
        except ValueError:
            return StockScreener._empty_price_data()

    @staticmethod
    def _to_series(df: pd.DataFrame, column: str) -> pd.Series:
        values = pd.to_numeric(df[column], errors="coerce").dropna()
        if len(values) < 2:
            raise ValueError(f"Not enough values to compute {column}")
        return values

    @staticmethod
    def _is_missing(value: Any) -> bool:
        return value is None or pd.isna(value)

    @staticmethod
    def calculate_macd(
        df: pd.DataFrame,
        fast_period: int | None = None,
        slow_period: int | None = None,
        signal_period: int | None = None,
    ) -> dict[str, Any]:
        fast_period = fast_period or DEFAULTS.macd_fast
        slow_period = slow_period or DEFAULTS.macd_slow
        signal_period = signal_period or DEFAULTS.macd_signal
        periods = f"{fast_period},{slow_period},{signal_period}"
        try:
            close = StockScreener._to_series(df, "Close")
        except ValueError:
            return StockScreener._insufficient_macd(periods)
        if len(close) < slow_period:
            return StockScreener._insufficient_macd(periods)
        ema_fast = close.ewm(span=fast_period, adjust=False).mean()
        ema_slow = close.ewm(span=slow_period, adjust=False).mean()
        macd = ema_fast - ema_slow
        signal = macd.ewm(span=signal_period, adjust=False).mean()
        histogram = macd - signal
        latest_macd = float(macd.iloc[-1])
        latest_signal = float(signal.iloc[-1])
        previous_macd = float(macd.iloc[-2])
        previous_signal = float(signal.iloc[-2])
        two_ago_macd = float(macd.iloc[-3]) if len(macd) >= 3 else None
        two_ago_signal = float(signal.iloc[-3]) if len(signal) >= 3 else None
        latest_histogram = float(histogram.iloc[-1])
        previous_histogram = float(histogram.iloc[-2])
        two_ago_histogram = float(histogram.iloc[-3]) if len(histogram) >= 3 else None
        hist_slope = latest_histogram - previous_histogram
        macd_slope = latest_macd - previous_macd
        spread_contracting = latest_histogram < 0 and latest_histogram > previous_histogram
        bullish_spread_contracting = latest_histogram > 0 and latest_histogram < previous_histogram
        crossover_state = "BULLISH" if latest_macd > latest_signal else "BEARISH"
        previous_state = "BULLISH" if previous_macd > previous_signal else "BEARISH"
        zero_line_state = "ABOVE_ZERO" if latest_macd >= 0 else "BELOW_ZERO"
        if latest_macd > latest_signal and latest_macd >= 0:
            regime = "BULL_CONFIRMED"
        elif latest_macd > latest_signal:
            regime = "BULL_RECOVERY"
        elif latest_macd < latest_signal and latest_macd >= 0:
            regime = "BULL_WEAKENING"
        else:
            regime = "BEAR_CONFIRMED"
        macd_signal_spread = latest_macd - latest_signal
        clear_bullish_crossover = (
            previous_macd <= previous_signal
            and latest_macd > latest_signal
            and latest_histogram > DEFAULTS.macd_clear_crossover_min_histogram
            and macd_signal_spread >= DEFAULTS.macd_clear_crossover_min_spread
        )
        clear_bearish_crossover = (
            previous_macd >= previous_signal
            and latest_macd < latest_signal
            and latest_histogram < -DEFAULTS.macd_clear_crossover_min_histogram
            and abs(macd_signal_spread) >= DEFAULTS.macd_clear_crossover_min_spread
            and previous_histogram >= latest_histogram
        )
        bullish_crosses = (macd.shift(1) <= signal.shift(1)) & (macd > signal)
        bearish_crosses = (macd.shift(1) >= signal.shift(1)) & (macd < signal)
        bullish_zero_line_crosses = (macd.shift(1) <= 0) & (macd > 0)
        bearish_zero_line_crosses = (macd.shift(1) >= 0) & (macd < 0)
        bars_since_bullish_crossover = StockScreener._bars_since_event(bullish_crosses)
        bars_since_bearish_crossover = StockScreener._bars_since_event(bearish_crosses)
        bars_since_bullish_zero_line_cross = StockScreener._bars_since_event(bullish_zero_line_crosses)
        bars_since_bearish_zero_line_cross = StockScreener._bars_since_event(bearish_zero_line_crosses)
        crossover_event = "NONE"
        if previous_macd <= previous_signal and latest_macd > latest_signal:
            crossover_event = "BULLISH_CROSSOVER"
        elif previous_macd >= previous_signal and latest_macd < latest_signal:
            crossover_event = "BEARISH_CROSSOVER"
        return {
            "macd": round(latest_macd, 4),
            "signal": round(latest_signal, 4),
            "previous_macd": round(previous_macd, 4),
            "previous_signal": round(previous_signal, 4),
            "two_ago_macd": round(two_ago_macd, 4) if two_ago_macd is not None else None,
            "two_ago_signal": round(two_ago_signal, 4) if two_ago_signal is not None else None,
            "previous_histogram": round(previous_histogram, 4),
            "two_ago_histogram": round(two_ago_histogram, 4) if two_ago_histogram is not None else None,
            "histogram": round(latest_histogram, 4),
            "histogram_slope": round(hist_slope, 4),
            "macd_slope": round(macd_slope, 4),
            "spread_contracting": spread_contracting,
            "bullish_spread_contracting": bullish_spread_contracting,
            "histogram_rising_streak": StockScreener._rising_streak(histogram),
            "histogram_falling_streak": StockScreener._falling_streak(histogram),
            "macd_signal_spread": round(macd_signal_spread, 4),
            "crossover_distance": round(abs(latest_macd - latest_signal), 4),
            "bars_since_bullish_crossover": bars_since_bullish_crossover,
            "bars_since_bearish_crossover": bars_since_bearish_crossover,
            "bars_since_bullish_zero_line_cross": bars_since_bullish_zero_line_cross,
            "bars_since_bearish_zero_line_cross": bars_since_bearish_zero_line_cross,
            "clear_bullish_crossover": clear_bullish_crossover,
            "clear_bearish_crossover": clear_bearish_crossover,
            "state": crossover_state,
            "previous_state": previous_state,
            "zero_line_state": zero_line_state,
            "regime": regime,
            "periods": periods,
            "crossover_event": crossover_event,
            "histogram_series": histogram,
            "is_sufficient": True,
        }

    @staticmethod
    def _insufficient_macd(periods: str) -> dict[str, Any]:
        return {
            "macd": None,
            "signal": None,
            "previous_macd": None,
            "previous_signal": None,
            "two_ago_macd": None,
            "two_ago_signal": None,
            "previous_histogram": None,
            "two_ago_histogram": None,
            "histogram": None,
            "histogram_slope": 0.0,
            "macd_slope": 0.0,
            "spread_contracting": False,
            "bullish_spread_contracting": False,
            "histogram_rising_streak": 0,
            "histogram_falling_streak": 0,
            "macd_signal_spread": None,
            "crossover_distance": None,
            "bars_since_bullish_crossover": None,
            "bars_since_bearish_crossover": None,
            "bars_since_bullish_zero_line_cross": None,
            "bars_since_bearish_zero_line_cross": None,
            "clear_bullish_crossover": False,
            "clear_bearish_crossover": False,
            "state": "INSUFFICIENT_HISTORY",
            "previous_state": "INSUFFICIENT_HISTORY",
            "zero_line_state": "INSUFFICIENT_HISTORY",
            "regime": "INSUFFICIENT_HISTORY",
            "periods": periods,
            "crossover_event": "NONE",
            "histogram_series": pd.Series(dtype=float),
            "is_sufficient": False,
        }

    @staticmethod
    def _rising_streak(series: pd.Series) -> int:
        values = series.dropna().tolist()
        streak = 0
        for index in range(len(values) - 1, 0, -1):
            if values[index] <= values[index - 1]:
                break
            streak += 1
        return streak

    @staticmethod
    def _bars_since_event(events: pd.Series) -> int | None:
        event_positions = np.flatnonzero(events.fillna(False).to_numpy())
        if len(event_positions) == 0:
            return None
        return int(len(events) - 1 - event_positions[-1])

    @staticmethod
    def _falling_streak(series: pd.Series) -> int:
        values = series.dropna().tolist()
        streak = 0
        for index in range(len(values) - 1, 0, -1):
            if values[index] >= values[index - 1]:
                break
            streak += 1
        return streak

    @staticmethod
    def calculate_rsi(df: pd.DataFrame) -> dict[str, Any]:
        try:
            close = StockScreener._to_series(df, "Close")
        except ValueError:
            return {"rsi": None, "slope": None, "state": "INSUFFICIENT_HISTORY"}
        if len(close) < DEFAULTS.rsi_period:
            return {"rsi": None, "slope": None, "state": "INSUFFICIENT_HISTORY"}
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(alpha=1 / DEFAULTS.rsi_period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1 / DEFAULTS.rsi_period, adjust=False).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - 100 / (1 + rs)
        latest_rsi = float(rsi.iloc[-1])
        if pd.isna(latest_rsi):
            return {"rsi": None, "slope": None, "state": "INSUFFICIENT_HISTORY"}
        state = "NEUTRAL"
        if latest_rsi >= 60:
            state = "BULLISH"
        elif latest_rsi < 40:
            state = "BEARISH"
        return {
            "rsi": round(latest_rsi, 4),
            "slope": round(float(rsi.iloc[-1] - rsi.iloc[-2]), 4),
            "state": state,
        }

    @staticmethod
    def calculate_adx(df: pd.DataFrame) -> dict[str, Any]:
        try:
            high = StockScreener._to_series(df, "High")
            low = StockScreener._to_series(df, "Low")
            close = StockScreener._to_series(df, "Close")
        except ValueError:
            return StockScreener._insufficient_adx()
        if len(close) < DEFAULTS.adx_period:
            return StockScreener._insufficient_adx()
        plus_dm_raw = high.diff()
        minus_dm_raw = -(low.diff())
        plus_dm = plus_dm_raw.where((plus_dm_raw > minus_dm_raw) & (plus_dm_raw > 0), 0)
        minus_dm = minus_dm_raw.where((minus_dm_raw > plus_dm_raw) & (minus_dm_raw > 0), 0)
        atr = StockScreener._atr(high, low, close, DEFAULTS.adx_period)
        plus_di = 100 * plus_dm.ewm(alpha=1 / DEFAULTS.adx_period, adjust=False).mean() / atr.replace(0, np.nan)
        minus_di = 100 * minus_dm.ewm(alpha=1 / DEFAULTS.adx_period, adjust=False).mean() / atr.replace(0, np.nan)
        dx = (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan) * 100
        adx = dx.ewm(alpha=1 / DEFAULTS.adx_period, adjust=False).mean()
        latest_adx = float(adx.iloc[-1])
        latest_plus_di = float(plus_di.iloc[-1])
        latest_minus_di = float(minus_di.iloc[-1])
        if pd.isna(latest_adx) or pd.isna(latest_plus_di) or pd.isna(latest_minus_di):
            return StockScreener._insufficient_adx()
        direction = "BULLISH" if latest_plus_di > latest_minus_di else "BEARISH"
        strength = "STRONG" if latest_adx >= 25 else "WEAK"
        return {
            "adx": round(latest_adx, 4),
            "plus_di": round(latest_plus_di, 4),
            "minus_di": round(latest_minus_di, 4),
            "direction": direction,
            "strength": strength,
            "state": f"{direction}_{strength}",
        }

    @staticmethod
    def _insufficient_adx() -> dict[str, Any]:
        return {
            "adx": None,
            "plus_di": None,
            "minus_di": None,
            "direction": "INSUFFICIENT_HISTORY",
            "strength": "INSUFFICIENT_HISTORY",
            "state": "INSUFFICIENT_HISTORY",
        }

    @staticmethod
    def calculate_bollinger(df: pd.DataFrame) -> dict[str, Any]:
        try:
            close = StockScreener._to_series(df, "Close")
        except ValueError:
            return StockScreener._insufficient_bollinger()
        if len(close) < DEFAULTS.bollinger_period:
            return StockScreener._insufficient_bollinger()
        sma = close.rolling(DEFAULTS.bollinger_period).mean()
        std = close.rolling(DEFAULTS.bollinger_period).std(ddof=0)
        upper = sma + DEFAULTS.bollinger_std * std
        lower = sma - DEFAULTS.bollinger_std * std
        latest_close = float(close.iloc[-1])
        latest_upper = float(upper.iloc[-1])
        latest_lower = float(lower.iloc[-1])
        if pd.isna(latest_upper) or pd.isna(latest_lower):
            return StockScreener._insufficient_bollinger()
        bandwidth = float((latest_upper - latest_lower) / latest_upper * 100) if latest_upper != 0 else 0.0
        percent_b = float((latest_close - latest_lower) / (latest_upper - latest_lower)) if latest_upper != latest_lower else 0.0
        position = "INSIDE"
        if latest_close > latest_upper:
            position = "ABOVE_UPPER"
        elif latest_close < latest_lower:
            position = "BELOW_LOWER"
        return {
            "upper": round(latest_upper, 4),
            "lower": round(latest_lower, 4),
            "bandwidth_pct": round(bandwidth, 4),
            "percent_b": round(percent_b * 100, 2),
            "position": position,
        }

    @staticmethod
    def calculate_volume_price_profile(df: pd.DataFrame) -> dict[str, Any]:
        try:
            close = StockScreener._to_series(df, "Close")
            volume = StockScreener._to_series(df, "Volume")
        except ValueError:
            return StockScreener._insufficient_volume_price_profile()
        period = DEFAULTS.relative_volume_period
        if len(close) < max(period, DEFAULTS.vpt_long_lookback + 1, DEFAULTS.bollinger_period):
            return StockScreener._insufficient_volume_price_profile()
        latest_volume = float(volume.iloc[-1])
        avg_volume = float(volume.tail(period).mean())
        relative_volume = latest_volume / avg_volume if avg_volume > 0 else None
        dollar_volume_20 = float((close * volume).tail(period).mean())

        pct_change = close.pct_change().replace([np.inf, -np.inf], np.nan).fillna(0)
        vpt = (volume * pct_change).cumsum()
        vpt_short_delta = float(vpt.iloc[-1] - vpt.iloc[-DEFAULTS.vpt_short_lookback - 1])
        vpt_long_delta = float(vpt.iloc[-1] - vpt.iloc[-DEFAULTS.vpt_long_lookback - 1])
        price_short_delta_pct = float((close.iloc[-1] - close.iloc[-DEFAULTS.vpt_short_lookback - 1]) / close.iloc[-DEFAULTS.vpt_short_lookback - 1] * 100) if close.iloc[-DEFAULTS.vpt_short_lookback - 1] else 0.0
        vpt_state = "MIXED"
        if vpt_short_delta > 0 and vpt_long_delta > 0:
            vpt_state = "ACCUMULATION"
        elif vpt_short_delta < 0 and vpt_long_delta < 0:
            vpt_state = "DISTRIBUTION"
        vpt_score = 75.0 if vpt_state == "ACCUMULATION" else 25.0 if vpt_state == "DISTRIBUTION" else 50.0
        if vpt_state == "ACCUMULATION" and price_short_delta_pct <= 2.0:
            vpt_score += 15.0
        elif vpt_state == "DISTRIBUTION" and price_short_delta_pct >= 0:
            vpt_score -= 10.0
        vpt_score = StockScreener._clamp_score(vpt_score)

        sma = close.rolling(DEFAULTS.bollinger_period).mean()
        std = close.rolling(DEFAULTS.bollinger_period).std(ddof=0)
        upper = sma + DEFAULTS.bollinger_std * std
        lower = sma - DEFAULTS.bollinger_std * std
        bandwidth = ((upper - lower) / upper.replace(0, np.nan) * 100).dropna()
        if bandwidth.empty:
            return StockScreener._insufficient_volume_price_profile()
        lookback = bandwidth.tail(DEFAULTS.compression_lookback)
        latest_bandwidth = float(bandwidth.iloc[-1])
        bandwidth_percentile = float((lookback <= latest_bandwidth).mean() * 100)
        compression_state = "NORMAL"
        if bandwidth_percentile <= 20:
            compression_state = "TIGHT_COMPRESSION"
        elif bandwidth_percentile <= 35:
            compression_state = "COMPRESSION"
        elif bandwidth_percentile >= 80:
            compression_state = "EXPANDED"
        compression_score = 100.0 - bandwidth_percentile
        if compression_state == "EXPANDED":
            compression_score *= 0.5

        return {
            "relative_volume_20": round(relative_volume, 4) if relative_volume is not None else None,
            "dollar_volume_20": round(dollar_volume_20, 2),
            "vpt_state": vpt_state,
            "vpt_short_delta": round(vpt_short_delta, 4),
            "vpt_long_delta": round(vpt_long_delta, 4),
            "vpt_score": round(vpt_score, 2),
            "price_short_delta_pct": round(price_short_delta_pct, 4),
            "compression_state": compression_state,
            "bollinger_bandwidth_percentile": round(bandwidth_percentile, 2),
            "compression_score": round(StockScreener._clamp_score(compression_score), 2),
        }

    @staticmethod
    def _insufficient_volume_price_profile() -> dict[str, Any]:
        return {
            "relative_volume_20": None,
            "dollar_volume_20": None,
            "vpt_state": "INSUFFICIENT_HISTORY",
            "vpt_short_delta": None,
            "vpt_long_delta": None,
            "vpt_score": 0.0,
            "price_short_delta_pct": None,
            "compression_state": "INSUFFICIENT_HISTORY",
            "bollinger_bandwidth_percentile": None,
            "compression_score": 0.0,
        }

    @staticmethod
    def _insufficient_bollinger() -> dict[str, Any]:
        return {
            "upper": None,
            "lower": None,
            "bandwidth_pct": None,
            "percent_b": None,
            "position": "INSUFFICIENT_HISTORY",
        }

    @staticmethod
    def calculate_ema200(df: pd.DataFrame) -> dict[str, Any]:
        try:
            close = StockScreener._to_series(df, "Close")
        except ValueError:
            close = pd.Series(dtype=float)
        if len(close) < DEFAULTS.ema200_period:
            return {
                "ema200": None,
                "zone": "INSUFFICIENT_HISTORY",
                "slope_state": "INSUFFICIENT_HISTORY",
                "distance_pct": None,
                "is_sufficient": False,
            }
        ema = close.ewm(span=DEFAULTS.ema200_period, adjust=False).mean()
        ema_value = float(ema.iloc[-1])
        prior_value = float(ema.iloc[-DEFAULTS.ema200_period])
        slope_pct = (ema_value - prior_value) / prior_value * 100 if prior_value != 0 else 0.0
        latest_price = float(close.iloc[-1])
        distance_pct = (latest_price - ema_value) / ema_value * 100 if ema_value != 0 else 0.0
        zone = "BULL_ZONE" if latest_price > ema_value else "BEAR_ZONE"
        slope_state = "RISING" if slope_pct > 0 else "FALLING" if slope_pct < 0 else "FLAT"
        return {
            "ema200": round(ema_value, 4),
            "zone": zone,
            "slope_state": slope_state,
            "distance_pct": round(distance_pct, 4),
            "is_sufficient": True,
        }

    @staticmethod
    def calculate_ceiling_profile(df: pd.DataFrame) -> dict[str, Any]:
        try:
            close = StockScreener._to_series(df, "Close")
            high = StockScreener._to_series(df, "High")
        except ValueError:
            return StockScreener._insufficient_ceiling_profile()
        if len(close) < 2 or len(high) < 2:
            return StockScreener._insufficient_ceiling_profile()

        latest_price = float(close.iloc[-1])
        previous_price = float(close.iloc[-2])
        lifetime_high = float(high.max())
        prior_highs = high.cummax().shift(1)
        lifetime_break_count = int((high > prior_highs).fillna(False).sum())

        ema20 = close.ewm(span=20, adjust=False).mean()
        ema52_high = high.ewm(span=52, adjust=False).mean()
        ema200_high = high.ewm(span=DEFAULTS.ema200_period, adjust=False).mean()

        def latest_or_none(series: pd.Series, period: int) -> float | None:
            if len(series) < period:
                return None
            return float(series.iloc[-1])

        def distance_pct(target: float | None) -> float | None:
            if target is None or target == 0:
                return None
            return round((latest_price - target) / target * 100, 4)

        def breach_count(series: pd.Series, period: int) -> int | None:
            if len(series) < period:
                return None
            crossed_up = (close > series) & (close.shift(1) <= series.shift(1))
            return int(crossed_up.fillna(False).sum())

        ema20_value = latest_or_none(ema20, 20)
        ema52_high_value = latest_or_none(ema52_high, 52)
        ema200_high_value = latest_or_none(ema200_high, DEFAULTS.ema200_period)
        ema52_distance = distance_pct(ema52_high_value)
        ema200_distance = distance_pct(ema200_high_value)

        recent_rising = latest_price > previous_price
        above_ema20 = ema20_value is not None and latest_price > ema20_value
        below_ema52_high = ema52_high_value is not None and latest_price < ema52_high_value
        above_ema200_high = ema200_high_value is not None and latest_price > ema200_high_value
        below_ema200_high = ema200_high_value is not None and latest_price < ema200_high_value

        if above_ema20 and below_ema52_high and above_ema200_high and recent_rising:
            pattern = "V_RECOVERY_BETWEEN_EMA200_AND_EMA52"
        elif above_ema20 and (below_ema52_high or below_ema200_high) and recent_rising:
            pattern = "V_RECOVERY_UNDER_HIGH_EMA"
        elif latest_price >= lifetime_high:
            pattern = "AT_LIFETIME_HIGH_CEILING"
        elif ema52_distance is not None and ema52_distance >= 0 and ema200_distance is not None and ema200_distance >= 0:
            pattern = "ABOVE_HIGH_EMA_STACK"
        else:
            pattern = "NO_V_RECOVERY"

        return {
            "lifetime_high": round(lifetime_high, 4),
            "distance_to_lifetime_high_pct": distance_pct(lifetime_high),
            "lifetime_high_break_count": lifetime_break_count,
            "ema20": round(ema20_value, 4) if ema20_value is not None else None,
            "ema52_high": round(ema52_high_value, 4) if ema52_high_value is not None else None,
            "distance_to_ema52_high_pct": ema52_distance,
            "ema52_high_breach_count": breach_count(ema52_high, 52),
            "ema200_high": round(ema200_high_value, 4) if ema200_high_value is not None else None,
            "distance_to_ema200_high_pct": ema200_distance,
            "ema200_high_breach_count": breach_count(ema200_high, DEFAULTS.ema200_period),
            "pattern": pattern,
        }

    @staticmethod
    def _insufficient_ceiling_profile() -> dict[str, Any]:
        return {
            "lifetime_high": None,
            "distance_to_lifetime_high_pct": None,
            "lifetime_high_break_count": None,
            "ema20": None,
            "ema52_high": None,
            "distance_to_ema52_high_pct": None,
            "ema52_high_breach_count": None,
            "ema200_high": None,
            "distance_to_ema200_high_pct": None,
            "ema200_high_breach_count": None,
            "pattern": "INSUFFICIENT_HISTORY",
        }

    @staticmethod
    def calculate_price_ladder(df: pd.DataFrame) -> dict[str, Any]:
        try:
            close = StockScreener._to_series(df, "Close")
        except ValueError:
            return StockScreener._insufficient_price_ladder()
        lookback_x = DEFAULTS.setup_price_lookback
        if len(close) < lookback_x + 1:
            return StockScreener._insufficient_price_ladder()
        p0 = float(close.iloc[-1])
        p1 = float(close.iloc[-2])
        px = float(close.iloc[-lookback_x - 1])
        advance_pct = (p0 - px) / px * 100 if px != 0 else 0.0
        return {
            "p0": round(p0, 4),
            "p1": round(p1, 4),
            "px": round(px, 4),
            "advance_pct": round(advance_pct, 4),
            "p0_gt_p1": p0 > p1,
            "p0_gt_px": p0 > px,
            "passed": p0 > p1 and p0 > px and advance_pct >= DEFAULTS.setup_price_min_advance_pct,
        }

    @staticmethod
    def _insufficient_price_ladder() -> dict[str, Any]:
        return {
            "p0": None,
            "p1": None,
            "px": None,
            "advance_pct": None,
            "p0_gt_p1": False,
            "p0_gt_px": False,
            "passed": False,
            "state": "INSUFFICIENT_HISTORY",
        }

    @staticmethod
    def detect_macd_divergence(
        df: pd.DataFrame,
        histogram: pd.Series,
        lookback: int | None = None,
        recent_window: int | None = None,
    ) -> str:
        lookback = lookback or DEFAULTS.macd_divergence_lookback
        recent_window = recent_window or DEFAULTS.macd_divergence_recent_window
        try:
            close = StockScreener._to_series(df, "Close")
        except ValueError:
            return "NONE"
        if recent_window <= 0 or lookback <= recent_window:
            return "NONE"
        if len(close) < lookback or len(histogram) < lookback:
            return "NONE"
        prior_close = close.iloc[-lookback:-recent_window]
        recent_close = close.iloc[-recent_window:]
        prior_hist = histogram.iloc[-lookback:-recent_window]
        recent_hist = histogram.iloc[-recent_window:]
        if recent_close.max() > prior_close.max() and recent_hist.max() < prior_hist.max():
            return "BEARISH_DIVERGENCE"
        if recent_close.min() < prior_close.min() and recent_hist.min() > prior_hist.min():
            return "BULLISH_DIVERGENCE"
        return "NONE"

    @staticmethod
    def build_bottom_up_macd_flow(
        macd_1h: dict[str, Any],
        macd_4h: dict[str, Any],
        macd_1d: dict[str, Any],
        divergence_1h: str,
        divergence_4h: str,
        divergence_1d: str,
    ) -> dict[str, str]:
        flow = {
            "state": "NONE",
            "event_type": "NONE",
            "trigger_1h": macd_1h["crossover_event"] if macd_1h["crossover_event"] != "NONE" else divergence_1h,
            "bridge_4h": divergence_4h,
            "confirmation_1d": divergence_1d,
            "reason": "No 1H MACD crossover or divergence trigger.",
        }

        if StockScreener._pre_bull_crossover_active(macd_4h):
            if StockScreener._one_hour_momentum_improving(macd_1h) and StockScreener._daily_context_not_deteriorating(macd_1d):
                flow.update({
                    "state": "PRE_BULL_CROSSOVER",
                    "event_type": "CROSSOVER",
                    "bridge_4h": macd_4h["state"],
                    "confirmation_1d": macd_1d["state"],
                    "reason": "4H-led pre-bull crossover: latest 4H MACD crossed above signal at/above the zero line, with improving 1H momentum and non-deteriorating 1D context.",
                })
            else:
                flow["reason"] = StockScreener._pre_bull_context_rejection_reason(macd_1h, macd_1d)
            return flow

        if macd_1h["clear_bearish_crossover"]:
            if StockScreener._macd_bridge_deteriorating(macd_4h) and StockScreener._macd_daily_deteriorating(macd_1d):
                flow.update({
                    "state": "PRE_BEAR_CROSSOVER",
                    "event_type": "CROSSOVER",
                    "bridge_4h": macd_4h["state"],
                    "confirmation_1d": macd_1d["state"],
                    "reason": "1H bearish MACD crossover percolated through deteriorating 4H and confirming 1D MACD.",
                })
            else:
                flow["reason"] = "1H bearish MACD crossover rejected because 4H/1D confirmation is missing."
            return flow

        if divergence_1h == "BULLISH_DIVERGENCE":
            if StockScreener._macd_bridge_constructive(macd_4h) and StockScreener._macd_daily_constructive(macd_1d):
                flow.update({
                    "state": "BULLISH_DIVERGENCE",
                    "event_type": "DIVERGENCE",
                    "reason": "1H bullish MACD divergence percolated through constructive 4H and confirming 1D MACD.",
                })
            else:
                flow["reason"] = "1H bullish MACD divergence rejected because 4H/1D confirmation is missing."
            return flow

        if divergence_1h == "BEARISH_DIVERGENCE":
            if StockScreener._macd_bridge_deteriorating(macd_4h) and StockScreener._macd_daily_deteriorating(macd_1d):
                flow.update({
                    "state": "BEARISH_DIVERGENCE",
                    "event_type": "DIVERGENCE",
                    "reason": "1H bearish MACD divergence percolated through deteriorating 4H and confirming 1D MACD.",
                })
            else:
                flow["reason"] = "1H bearish MACD divergence rejected because 4H/1D confirmation is missing."
            return flow

        return flow

    @staticmethod
    def build_pre_bull_crossover_flow(
        macd_1h: dict[str, Any],
        macd_4h: dict[str, Any],
        macd_1d: dict[str, Any],
    ) -> dict[str, str]:
        flow = {
            "state": "NONE",
            "event_type": "NONE",
            "trigger_1h": "NONE",
            "bridge_4h": macd_4h.get("state", "NONE"),
            "confirmation_1d": macd_1d.get("state", "NONE"),
            "reason": "No exact classical 4H MACD crossover trigger.",
        }
        if StockScreener._pre_bull_crossover_active(macd_4h):
            if StockScreener._one_hour_momentum_improving(macd_1h) and StockScreener._daily_context_not_deteriorating(macd_1d):
                flow.update({
                    "state": "PRE_BULL_CROSSOVER",
                    "event_type": "CROSSOVER",
                    "trigger_1h": macd_1h.get("state", "NONE"),
                    "reason": "4H-led pre-bull crossover: latest classical 12/26/9 4H MACD crossed above signal at/above the zero line, with improving 1H momentum and non-deteriorating 1D context.",
                })
            else:
                flow["reason"] = StockScreener._pre_bull_context_rejection_reason(macd_1h, macd_1d)
        return flow

    @staticmethod
    def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
        previous_close = close.shift(1)
        true_range = pd.concat([
            high - low,
            (high - previous_close).abs(),
            (low - previous_close).abs(),
        ], axis=1).max(axis=1)
        return true_range.ewm(alpha=1 / period, adjust=False).mean()

    @staticmethod
    def _support_profile(shared: dict[str, Any]) -> dict[str, Any]:
        bullish_score = 0
        bearish_score = 0
        notes: list[str] = []
        rsi = shared["rsi_1d"]
        if rsi["state"] == "BULLISH":
            bullish_score += 1
            notes.append("RSI bullish")
        elif rsi["state"] == "BEARISH":
            bearish_score += 1
            notes.append("RSI bearish")
        adx = shared["adx_1d"]
        if adx["strength"] == "STRONG":
            if adx["direction"] == "BULLISH":
                bullish_score += 1
                notes.append("ADX strong bullish")
            else:
                bearish_score += 1
                notes.append("ADX strong bearish")
        ema200 = shared["ema200"]
        if ema200.get("is_sufficient"):
            if ema200["zone"] == "BULL_ZONE" and ema200["slope_state"] in ["RISING", "FLAT"]:
                bullish_score += 1
                notes.append("EMA200 supportive")
            elif ema200["zone"] == "BEAR_ZONE" or ema200["slope_state"] == "FALLING":
                bearish_score += 1
                notes.append("EMA200 weak")
        bollinger = shared["bollinger_1d"]
        if bollinger["position"] == "ABOVE_UPPER":
            bullish_score += 1
            notes.append("Price above upper Bollinger")
        elif bollinger["position"] == "BELOW_LOWER":
            bearish_score += 1
            notes.append("Price below lower Bollinger")
        return {"bullish_score": bullish_score, "bearish_score": bearish_score, "notes": notes}

    @staticmethod
    def _classify_macd_direction(macd: dict[str, Any]) -> str:
        if not macd.get("is_sufficient"):
            return "INSUFFICIENT"
        if (
            not StockScreener._is_missing(macd.get("macd"))
            and not StockScreener._is_missing(macd.get("signal"))
            and not StockScreener._is_missing(macd.get("histogram"))
        ):
            if macd["macd"] > macd["signal"] and macd["histogram"] > 0:
                return "BULLISH"
            if macd["macd"] < macd["signal"] and macd["histogram"] < 0:
                return "BEARISH"
        return "NEUTRAL"

    @staticmethod
    def _passes_macd_zero_line_buffer(macd: dict[str, Any], threshold: float | None = None) -> bool:
        threshold = DEFAULTS.macd_bull_zero_line_min if threshold is None else threshold
        value = macd.get("macd")
        return not StockScreener._is_missing(value) and value >= threshold

    @staticmethod
    def _macd_alignment(macd_1d: dict[str, Any], macd_4h: dict[str, Any], macd_1h: dict[str, Any]) -> dict[str, Any]:
        directions = {
            "1D": StockScreener._classify_macd_direction(macd_1d),
            "4H": StockScreener._classify_macd_direction(macd_4h),
            "1H": StockScreener._classify_macd_direction(macd_1h),
        }
        if all(direction == "BULLISH" for direction in directions.values()):
            state = "BULLISH_ALIGNED"
        elif all(direction == "BEARISH" for direction in directions.values()):
            state = "BEARISH_ALIGNED"
        else:
            state = "MIXED_OR_WEAK"
        bearish_timeframes = [timeframe for timeframe, direction in directions.items() if direction == "BEARISH"]
        weak_timeframes = [timeframe for timeframe, direction in directions.items() if direction in ["NEUTRAL", "INSUFFICIENT"]]
        return {
            "state": state,
            "directions": directions,
            "bearish_timeframes": bearish_timeframes,
            "weak_timeframes": weak_timeframes,
            "reason": ", ".join(f"{timeframe}={direction}" for timeframe, direction in directions.items()),
        }

    @staticmethod
    def _l0_macd_prequalification(shared: dict[str, Any]) -> dict[str, Any]:
        alignment = StockScreener._macd_alignment(shared["macd_1d"], shared["macd_4h"], shared["macd_1h"])
        zero_line_passed = all(
            StockScreener._passes_macd_zero_line_buffer(macd)
            for macd in [shared["macd_1d"], shared["macd_4h"], shared["macd_1h"]]
        )
        bullish_passed = alignment["state"] == "BULLISH_ALIGNED" and zero_line_passed
        bearish_passed = alignment["state"] == "BEARISH_ALIGNED"
        if bullish_passed:
            reason = "L0 passed: 1D, 4H, and 1H MACD are bullish aligned and above the zero-line buffer."
        elif alignment["state"] != "BULLISH_ALIGNED":
            reason = f"L0 blocked bullish signal: strict MACD alignment failed ({alignment['reason']})."
        else:
            reason = f"L0 blocked bullish signal: one or more MACD timeframes are below {DEFAULTS.macd_bull_zero_line_min}."
        return {
            "alignment_state": alignment["state"],
            "directions": alignment["directions"],
            "bearish_timeframes": alignment["bearish_timeframes"],
            "weak_timeframes": alignment["weak_timeframes"],
            "bullish_zero_line_passed": zero_line_passed,
            "bullish_passed": bullish_passed,
            "bearish_passed": bearish_passed,
            "reason": reason,
        }

    @staticmethod
    def _setup_conditions(shared: dict[str, Any]) -> tuple[bool, int, str]:
        l0 = shared.get("l0_macd", {})
        if DEFAULTS.macd_require_all_timeframes_aligned and not l0.get("bullish_passed", False):
            return False, 0, l0.get("reason", "L0 MACD prequalification failed")
        price_ladder = shared["price_ladder"]
        macd_1d = shared["macd_1d"]
        macd_4h = shared["macd_4h"]
        macd_1h = shared["macd_1h"]
        rsi = shared["rsi_1d"]["rsi"]
        support = shared["support"]
        if not price_ladder["passed"]:
            return False, 0, "Failed price ladder gate"
        if not StockScreener._macd_components_above_bull_threshold(macd_1d):
            return False, 1, f"1D MACD, signal, and histogram are not all above {DEFAULTS.macd_bull_zero_line_min}"
        if not StockScreener._macd_components_above_bull_threshold(macd_4h):
            return False, 2, f"4H MACD, signal, and histogram are not all above {DEFAULTS.macd_bull_zero_line_min}"
        if not StockScreener._macd_components_above_bull_threshold(macd_1h):
            return False, 3, f"1H MACD, signal, and histogram are not all above {DEFAULTS.macd_bull_zero_line_min}"
        setup_rsi_max = shared.get("setup_rsi_max", DEFAULTS.setup_rsi_max)
        if not StockScreener._is_missing(rsi) and rsi > setup_rsi_max:
            return False, 4, f"RSI {rsi} is above setup headroom ceiling {setup_rsi_max}"
        if support["bearish_score"] >= 2 and support["bullish_score"] == 0:
            return False, 5, "Support profile is too bearish"
        return True, 5, f"MACD, signal, and histogram are above {DEFAULTS.macd_bull_zero_line_min} across 1D, 4H, and 1H"

    @staticmethod
    def _macd_components_above_bull_threshold(macd: dict[str, Any]) -> bool:
        threshold = DEFAULTS.macd_bull_zero_line_min
        return (
            not StockScreener._is_missing(macd.get("macd"))
            and not StockScreener._is_missing(macd.get("signal"))
            and not StockScreener._is_missing(macd.get("histogram"))
            and macd["macd"] > threshold
            and macd["signal"] > threshold
            and macd["histogram"] > threshold
        )

    @staticmethod
    def _pre_bull_crossover_active(macd: dict[str, Any]) -> bool:
        if (
            StockScreener._is_missing(macd.get("previous_macd"))
            or StockScreener._is_missing(macd.get("previous_signal"))
            or StockScreener._is_missing(macd.get("macd"))
            or StockScreener._is_missing(macd.get("signal"))
            or StockScreener._is_missing(macd.get("histogram"))
        ):
            return False
        return (
            macd["previous_macd"] <= macd["previous_signal"]
            and macd["macd"] > macd["signal"]
            and macd["histogram"] > DEFAULTS.macd_clear_crossover_min_histogram
            and macd["macd"] >= 0
        )

    @staticmethod
    def _one_hour_momentum_improving(macd: dict[str, Any]) -> bool:
        if StockScreener._is_missing(macd.get("histogram")):
            return False
        return (
            macd["histogram"] > 0
            or macd.get("histogram_slope", 0) > 0
            or macd.get("histogram_rising_streak", 0) >= 2
        )

    @staticmethod
    def _daily_context_not_deteriorating(macd: dict[str, Any]) -> bool:
        if not macd.get("is_sufficient"):
            return False
        age = macd.get("bars_since_bullish_zero_line_cross")
        if age is not None and age > DEFAULTS.pre_bull_max_daily_zero_cross_age:
            return False
        if macd.get("state") == "BULLISH":
            return True
        return macd.get("histogram_slope", 0) >= 0 or macd.get("spread_contracting", False)

    @staticmethod
    def _pre_bull_context_rejection_reason(macd_1h: dict[str, Any], macd_1d: dict[str, Any]) -> str:
        age = macd_1d.get("bars_since_bullish_zero_line_cross")
        if age is not None and age > DEFAULTS.pre_bull_max_daily_zero_cross_age:
            return (
                "4H bullish crossover rejected because 1D bull regime is mature "
                f"({age} daily bars since bullish zero-line cross; max {DEFAULTS.pre_bull_max_daily_zero_cross_age})."
            )
        if not StockScreener._one_hour_momentum_improving(macd_1h):
            return "4H bullish crossover rejected because 1H momentum is not improving."
        return "4H bullish crossover rejected because 1D context is deteriorating."

    @staticmethod
    def _macd_daily_constructive(macd: dict[str, Any]) -> bool:
        if macd["state"] == "BULLISH" and macd["histogram_slope"] >= 0:
            return True
        if macd["state"] == "BEARISH" and macd["histogram_slope"] > 0 and macd["histogram_rising_streak"] >= 1:
            return True
        return False

    @staticmethod
    def _macd_bridge_constructive(macd: dict[str, Any]) -> bool:
        if macd["state"] == "BULLISH" and macd["histogram_slope"] >= 0:
            return True
        return macd["histogram_slope"] > 0 and (macd["spread_contracting"] or macd["histogram_rising_streak"] >= 1)

    @staticmethod
    def _macd_trigger_active(macd: dict[str, Any]) -> bool:
        return macd["histogram_slope"] > 0 and macd["histogram_rising_streak"] >= DEFAULTS.setup_macd_histogram_rising_streak and (macd["state"] == "BULLISH" or macd["spread_contracting"])

    @staticmethod
    def _macd_bridge_deteriorating(macd: dict[str, Any]) -> bool:
        if macd["state"] == "BEARISH" and macd["histogram_slope"] <= 0:
            return True
        return macd["histogram_slope"] < 0 and (macd["bullish_spread_contracting"] or macd["histogram_falling_streak"] >= 1)

    @staticmethod
    def _macd_bearish_trigger_active(macd: dict[str, Any]) -> bool:
        return (
            macd["histogram_slope"] < 0
            and macd["histogram_falling_streak"] >= DEFAULTS.setup_macd_histogram_rising_streak
            and (macd["state"] == "BEARISH" or macd["bullish_spread_contracting"])
        )

    @staticmethod
    def _macd_daily_deteriorating(macd: dict[str, Any]) -> bool:
        if macd["state"] == "BEARISH" and macd["histogram_slope"] <= 0:
            return True
        if macd["state"] == "BULLISH" and macd["histogram_slope"] < 0 and macd["histogram_falling_streak"] >= 1:
            return True
        return False

    @staticmethod
    def _candidate_allowed_by_l0(candidate_state: str, l0: dict[str, Any]) -> bool:
        if not DEFAULTS.macd_require_all_timeframes_aligned:
            return True
        if candidate_state == "PRE_BULL_CROSSOVER":
            return True
        if candidate_state in POSITIONING_BULLISH_ALIGNMENT_REQUIRED_STATES:
            return bool(l0.get("bullish_passed"))
        return True

    @staticmethod
    def _l0_blocked_candidate(candidate_state: str, l0: dict[str, Any]) -> dict[str, Any]:
        return {
            "state": "NO_CANDIDATE",
            "reason": f"{l0.get('reason', 'L0 MACD prequalification failed')} Blocked {candidate_state}.",
        }

    @staticmethod
    def classify_candidate(shared: dict[str, Any]) -> dict[str, Any]:
        macd_1d = shared["macd_1d"]
        macd_4h = shared["macd_4h"]
        macd_1h = shared["macd_1h"]
        baseline_macd_1d = shared["baseline_macd_1d"]
        baseline_macd_4h = shared["baseline_macd_4h"]
        baseline_macd_1h = shared["baseline_macd_1h"]
        support = shared["support"]
        rsi = shared["rsi_1d"]
        bollinger = shared["bollinger_1d"]
        divergence = shared["divergence"]
        macd_flow = shared.get("macd_flow", {})
        l0 = shared.get("l0_macd", {})
        daily_bullish_deteriorating = macd_1d["state"] == "BULLISH" and macd_1d["histogram_slope"] < 0
        lower_bearish = sum([macd_4h["state"] == "BEARISH", macd_1h["state"] == "BEARISH"])
        support_bullish_dominant = support["bullish_score"] >= support["bearish_score"] + 2
        daily_bear_transition_risk = (
            (not StockScreener._is_missing(macd_1d["histogram"]) and macd_1d["histogram"] <= 0)
            or (
                not StockScreener._is_missing(macd_1d["crossover_distance"])
                and macd_1d["crossover_distance"] <= 0.02
            )
        )
        if macd_flow.get("state") in ["PRE_BULL_CROSSOVER", "PRE_BEAR_CROSSOVER"]:
            if StockScreener._candidate_allowed_by_l0(macd_flow["state"], l0):
                return {"state": macd_flow["state"], "reason": macd_flow["reason"]}
        if StockScreener._macd_bearish_trigger_active(macd_1h) and StockScreener._macd_bridge_deteriorating(macd_4h) and daily_bullish_deteriorating and (support["bearish_score"] >= 3 or (lower_bearish == 2 and daily_bear_transition_risk and not support_bullish_dominant)):
            return {"state": "PRE_BEAR_CROSSOVER", "reason": "1H bearish MACD trigger percolated through deteriorating 4H into weakening 1D MACD."}
        if shared["setup_passed"]:
            if StockScreener._candidate_allowed_by_l0("SETUP_CANDIDATE", l0):
                return {"state": "SETUP_CANDIDATE", "reason": shared.get("setup_reason", "MACD, signal, and histogram are positive across 1D, 4H, and 1H.")}
        if divergence in BEARISH_CANDIDATE_STATES:
            return {"state": divergence, "reason": shared.get("divergence_reason", "A bearish MACD divergence is present.")}
        rsi_value = rsi.get("rsi")
        bollinger_percent_b = bollinger.get("percent_b")
        rsi_overbought = not StockScreener._is_missing(rsi_value) and rsi_value >= 70
        rsi_oversold = not StockScreener._is_missing(rsi_value) and rsi_value <= 30
        bollinger_high_percent = not StockScreener._is_missing(bollinger_percent_b) and bollinger_percent_b >= 80
        bull_extension_signal = (
            rsi_overbought
            or bollinger["position"] == "ABOVE_UPPER"
            or (
                shared["adx_1d"]["strength"] == "STRONG"
                and shared["adx_1d"]["direction"] == "BULLISH"
                and sum([baseline_macd_4h["state"] == "BULLISH", baseline_macd_1h["state"] == "BULLISH"]) >= 1
            )
        )
        bull_lower_timeframe_rollover = (
            baseline_macd_1d["state"] == "BULLISH"
            and sum([macd_4h["state"] == "BEARISH", macd_1h["state"] == "BEARISH"]) >= 1
            and (
                rsi_overbought
                or shared["adx_1d"]["strength"] == "STRONG"
                or bollinger_high_percent
            )
        )
        baseline_daily_bullish_deteriorating = (
            baseline_macd_1d["state"] == "BULLISH"
            and baseline_macd_1d["histogram_slope"] < 0
        )
        bull_structure_intact = (
            baseline_macd_1d["state"] == "BULLISH"
            and baseline_macd_1d["zero_line_state"] == "ABOVE_ZERO"
            and not baseline_daily_bullish_deteriorating
            and sum([baseline_macd_4h["state"] == "BEARISH", baseline_macd_1h["state"] == "BEARISH"]) < 2
        )
        if bull_structure_intact and bull_extension_signal:
            if StockScreener._candidate_allowed_by_l0("BULL_EXTENDED", l0):
                return {"state": "BULL_EXTENDED", "reason": "Classical 12/26/9 MACD bull regime remains intact and extension or overbought risk is present."}
        if bull_lower_timeframe_rollover:
            if StockScreener._candidate_allowed_by_l0("BULL_EXTENDED", l0):
                return {"state": "BULL_EXTENDED", "reason": "Daily MACD bull regime is intact, but lower timeframes are rolling over after an extended move."}
        bear_extension_signal = (
            rsi_oversold
            or bollinger["position"] == "BELOW_LOWER"
            or (
                shared["adx_1d"]["strength"] == "STRONG"
                and shared["adx_1d"]["direction"] == "BEARISH"
                and sum([baseline_macd_4h["state"] == "BEARISH", baseline_macd_1h["state"] == "BEARISH"]) >= 1
            )
        )
        baseline_daily_bearish_recovering = (
            baseline_macd_1d["state"] == "BEARISH"
            and baseline_macd_1d["histogram_slope"] > 0
        )
        bear_structure_intact = (
            baseline_macd_1d["state"] == "BEARISH"
            and baseline_macd_1d["zero_line_state"] == "BELOW_ZERO"
            and not baseline_daily_bearish_recovering
            and sum([baseline_macd_4h["state"] == "BULLISH", baseline_macd_1h["state"] == "BULLISH"]) < 2
        )
        if bear_structure_intact and bear_extension_signal:
            return {"state": "BEAR_EXTENDED", "reason": "Classical 12/26/9 MACD bear regime remains intact and downside extension risk is present."}
        if divergence != "NONE":
            if divergence == "BULLISH_DIVERGENCE" and not l0.get("bullish_passed", False):
                return {
                    "state": divergence,
                    "reason": f"{shared.get('divergence_reason', 'A bullish MACD divergence is present.')} L0 bullish positioning gate failed; treat as watch-only, not a positionable bullish setup.",
                }
            if StockScreener._candidate_allowed_by_l0(divergence, l0):
                return {"state": divergence, "reason": shared.get("divergence_reason", "A MACD divergence is present.")}
        return {"state": "STATUS_QUO", "reason": f"Classical 12/26/9 MACD baseline is {baseline_macd_1d['regime']}; no selected state rule qualified."}

    @staticmethod
    def calculate_weighted_score(shared: dict[str, Any]) -> dict[str, Any]:
        candidate_state = shared.get("candidate_state", "NO_CANDIDATE")
        direction = StockScreener._candidate_direction(candidate_state)
        if candidate_state == "PRE_BULL_CROSSOVER":
            scores = StockScreener._score_pre_bull_crossover(shared)
        elif candidate_state == "BULL_EXTENDED":
            scores = StockScreener._score_bull_extended(shared)
        elif candidate_state == "BEAR_EXTENDED":
            scores = StockScreener._score_bear_extended(shared)
        elif candidate_state in ["BULLISH_DIVERGENCE", "BEARISH_DIVERGENCE"]:
            scores = StockScreener._score_divergence_candidate(shared, candidate_state)
        elif candidate_state == "STATUS_QUO":
            scores = StockScreener._score_status_quo(shared)
        else:
            scores = {
                "macd_score": StockScreener._score_macd(shared, direction),
                "rsi_score": StockScreener._score_rsi(shared["rsi_1d"]["rsi"], direction, candidate_state, shared.get("setup_rsi_max")),
                "adx_score": StockScreener._score_adx(shared["adx_1d"], direction),
                "weights": "MACD 50%, RSI 25%, ADX 25%",
            }
        weighted = scores["weighted_score"] if "weighted_score" in scores else (
            scores["macd_score"] * DEFAULTS.score_macd_weight
            + scores["rsi_score"] * DEFAULTS.score_rsi_weight
            + scores["adx_score"] * DEFAULTS.score_adx_weight
        )
        return {
            "weighted_score": round(weighted, 2),
            "macd_score": round(scores["macd_score"], 2),
            "rsi_score": round(scores["rsi_score"], 2),
            "adx_score": round(scores["adx_score"], 2),
            "weights": scores["weights"],
        }

    @staticmethod
    def _pre_bull_freshness_profile(shared: dict[str, Any]) -> dict[str, Any]:
        macd_4h = shared.get("pre_bull_trigger_macd_4h", shared["macd_4h"])
        age = macd_4h.get("bars_since_bullish_crossover")
        if age == 0 and macd_4h.get("macd", -1) >= 0:
            return {"state": "EXACT_4H_CROSSOVER", "score": 100.0, "reason": "4H bullish MACD/signal crossover occurred on the latest 4H bar with MACD at/above zero."}
        return {"state": "NOT_EXACT_4H_CROSSOVER", "score": 0.0, "reason": f"4H bullish MACD/signal crossover age is {age}; not an exact current 4H crossover."}

    @staticmethod
    def _score_relative_volume(relative_volume: float | None) -> float:
        if StockScreener._is_missing(relative_volume):
            return 0.0
        if relative_volume < 0.7:
            return 25.0
        if relative_volume < 1.0:
            return 50.0
        if relative_volume < 1.5:
            return 75.0
        return 100.0

    @staticmethod
    def _score_pre_bull_crossover(shared: dict[str, Any]) -> dict[str, Any]:
        freshness = StockScreener._pre_bull_freshness_profile(shared)
        macd_score = StockScreener._score_macd(shared, "BULLISH")
        volume_price = shared.get("volume_price_1d", {})
        relative_volume_score = StockScreener._score_relative_volume(volume_price.get("relative_volume_20"))
        vpt_score = float(volume_price.get("vpt_score") or 0.0)
        compression_score = float(volume_price.get("compression_score") or 0.0)
        participation_score = relative_volume_score * 0.60 + vpt_score * 0.40
        structure_score = compression_score
        weighted = (
            freshness["score"] * 0.35
            + macd_score * 0.30
            + relative_volume_score * 0.15
            + vpt_score * 0.10
            + compression_score * 0.10
        )
        reason = (
            f"{freshness['reason']} "
            f"RelVol20={volume_price.get('relative_volume_20')}; "
            f"VPT={volume_price.get('vpt_state')}; "
            f"Compression={volume_price.get('compression_state')}."
        )
        shared["pre_bull_quality"] = {
            "freshness": freshness["state"],
            "confidence": round(weighted, 2),
            "reason": reason,
            "relative_volume_score": round(relative_volume_score, 2),
            "participation_score": round(participation_score, 2),
            "structure_score": round(structure_score, 2),
        }
        return {
            "weighted_score": weighted,
            "macd_score": macd_score,
            "rsi_score": participation_score,
            "adx_score": structure_score,
            "weights": "Pre-Bull: freshness 35%, MACD structure 30%, relative volume 15%, VPT accumulation 10%, compression 10%",
        }

    @staticmethod
    def _candidate_direction(candidate_state: str) -> str:
        if candidate_state in BEARISH_CANDIDATE_STATES:
            return "BEARISH"
        if candidate_state in BULLISH_CANDIDATE_STATES:
            return "BULLISH"
        return "NEUTRAL"

    @staticmethod
    def _score_macd(shared: dict[str, Any], direction: str) -> float:
        macd_flow = shared.get("macd_flow", {})
        candidate_state = shared.get("candidate_state", "NO_CANDIDATE")
        l0 = shared.get("l0_macd", {})
        if (
            direction == "BULLISH"
            and candidate_state != "PRE_BULL_CROSSOVER"
            and DEFAULTS.macd_require_all_timeframes_aligned
            and not l0.get("bullish_passed", False)
        ):
            return 0.0
        if direction == "BULLISH" and l0.get("bullish_passed"):
            return 100.0
        if macd_flow.get("state") == candidate_state and candidate_state != "NONE":
            return 100.0
        if candidate_state == "BULL_EXTENDED":
            macd_1d = shared["baseline_macd_1d"]
            macd_4h = shared["baseline_macd_4h"]
            macd_1h = shared["baseline_macd_1h"]
        else:
            macd_1d = shared["macd_1d"]
            macd_4h = shared["macd_4h"]
            macd_1h = shared["macd_1h"]
        if direction == "BULLISH":
            score = 0.0
            if StockScreener._macd_trigger_active(macd_1h):
                score += 35.0
            elif macd_1h["state"] == "BULLISH":
                score += 20.0
            if StockScreener._macd_bridge_constructive(macd_4h):
                score += 30.0
            elif macd_4h["state"] == "BULLISH":
                score += 15.0
            if StockScreener._macd_daily_constructive(macd_1d):
                score += 35.0
            elif macd_1d["state"] == "BULLISH":
                score += 20.0
            return score
        if direction == "BEARISH":
            score = 0.0
            if StockScreener._macd_bearish_trigger_active(macd_1h):
                score += 35.0
            elif macd_1h["state"] == "BEARISH":
                score += 20.0
            if StockScreener._macd_bridge_deteriorating(macd_4h):
                score += 30.0
            elif macd_4h["state"] == "BEARISH":
                score += 15.0
            if StockScreener._macd_daily_deteriorating(macd_1d):
                score += 35.0
            elif macd_1d["state"] == "BEARISH":
                score += 20.0
            return score
        return 0.0

    @staticmethod
    def _clamp_score(value: float) -> float:
        return max(0.0, min(100.0, value))

    @staticmethod
    def _score_range(value: float, low: float, high: float) -> float:
        if StockScreener._is_missing(value):
            return 0.0
        if value <= low:
            return 0.0
        if value >= high:
            return 100.0
        return (value - low) / (high - low) * 100.0

    @staticmethod
    def _score_bull_extended(shared: dict[str, Any]) -> dict[str, Any]:
        rsi = shared["rsi_1d"]["rsi"]
        adx = shared["adx_1d"]["adx"]
        pct_b = shared["bollinger_1d"]["percent_b"]
        macd_1d = shared["baseline_macd_1d"]
        bearish_lower = sum([shared["macd_4h"]["state"] == "BEARISH", shared["macd_1h"]["state"] == "BEARISH"])
        daily_regime = 55.0 if macd_1d["state"] == "BULLISH" else 25.0
        daily_regime += 20.0 if macd_1d["zero_line_state"] == "ABOVE_ZERO" else 0.0
        daily_regime += 15.0 if macd_1d["histogram_slope"] >= 0 else 0.0
        daily_regime += 10.0 if bearish_lower >= 1 else 0.0
        macd_score = StockScreener._clamp_score(daily_regime)
        rsi_score = StockScreener._score_bullish_setup_rsi_headroom(rsi, shared.get("setup_rsi_max"))
        bollinger_headroom = 100.0 - StockScreener._score_range(pct_b, 80.0, 120.0)
        extension_headroom_score = StockScreener._clamp_score(min(rsi_score, bollinger_headroom))
        adx_score = StockScreener._score_adx(shared["adx_1d"], "BULLISH")
        weighted = macd_score * 0.45 + extension_headroom_score * 0.35 + adx_score * 0.20
        return {
            "weighted_score": weighted,
            "macd_score": macd_score,
            "rsi_score": extension_headroom_score,
            "adx_score": adx_score,
            "weights": "Bull Extended: MACD trend 45%, RSI/Bollinger headroom 35%, ADX 20%",
        }

    @staticmethod
    def _score_bear_extended(shared: dict[str, Any]) -> dict[str, Any]:
        rsi = shared["rsi_1d"]["rsi"]
        adx = shared["adx_1d"]["adx"]
        pct_b = shared["bollinger_1d"]["percent_b"]
        macd_1d = shared["baseline_macd_1d"]
        bullish_lower = sum([shared["macd_4h"]["state"] == "BULLISH", shared["macd_1h"]["state"] == "BULLISH"])
        daily_regime = 55.0 if macd_1d["state"] == "BEARISH" else 25.0
        daily_regime += 20.0 if macd_1d["zero_line_state"] == "BELOW_ZERO" else 0.0
        daily_regime += 15.0 if macd_1d["histogram_slope"] <= 0 else 0.0
        daily_regime += 10.0 if bullish_lower >= 1 else 0.0
        macd_score = StockScreener._clamp_score(daily_regime)
        rsi_score = StockScreener._clamp_score(max(StockScreener._score_range(45.0 - rsi, 0.0, 25.0), StockScreener._score_range(50.0 - pct_b, 0.0, 75.0)))
        adx_score = StockScreener._score_adx(shared["adx_1d"], "BEARISH")
        weighted = macd_score * 0.35 + rsi_score * 0.40 + adx_score * 0.25
        return {
            "weighted_score": weighted,
            "macd_score": macd_score,
            "rsi_score": rsi_score,
            "adx_score": adx_score,
            "weights": "Bear Extended: daily MACD 35%, downside extension RSI/Bollinger 40%, ADX 25%",
        }

    @staticmethod
    def _score_divergence_candidate(shared: dict[str, Any], candidate_state: str) -> dict[str, Any]:
        bullish = candidate_state == "BULLISH_DIVERGENCE"
        target = "BULLISH_DIVERGENCE" if bullish else "BEARISH_DIVERGENCE"
        raw_hits = sum([
            shared.get("raw_divergence_1d") == target,
            shared.get("raw_divergence_4h") == target,
            shared.get("raw_divergence_1h") == target,
            shared.get("baseline_divergence_1d") == target,
            shared.get("baseline_divergence_4h") == target,
            shared.get("baseline_divergence_1h") == target,
        ])
        macd_score = StockScreener._clamp_score(35.0 + raw_hits * 15.0)
        rsi = shared["rsi_1d"]["rsi"]
        pct_b = shared["bollinger_1d"]["percent_b"]
        if bullish:
            rsi_score = StockScreener._clamp_score(max(StockScreener._score_range(55.0 - rsi, 0.0, 30.0), StockScreener._score_range(50.0 - pct_b, 0.0, 75.0)))
            adx_score = StockScreener._score_adx(shared["adx_1d"], "BULLISH")
        else:
            rsi_score = StockScreener._clamp_score(max(StockScreener._score_range(rsi, 50.0, 80.0), StockScreener._score_range(pct_b, 60.0, 100.0)))
            adx_score = StockScreener._score_adx(shared["adx_1d"], "BEARISH")
        weighted = macd_score * 0.50 + rsi_score * 0.30 + adx_score * 0.20
        return {
            "weighted_score": weighted,
            "macd_score": macd_score,
            "rsi_score": rsi_score,
            "adx_score": adx_score,
            "weights": "Divergence: divergence evidence 50%, RSI/Bollinger location 30%, ADX 20%",
        }

    @staticmethod
    def _score_status_quo(shared: dict[str, Any]) -> dict[str, Any]:
        adx_score = StockScreener._score_adx(shared["adx_1d"], "NEUTRAL")
        rsi = shared["rsi_1d"]["rsi"]
        pct_b = shared["bollinger_1d"]["percent_b"]
        rsi_balance = 100.0 - min(100.0, abs((0.0 if StockScreener._is_missing(rsi) else rsi) - 50.0) * 3.0)
        bollinger_balance = 100.0 - min(100.0, abs((50.0 if StockScreener._is_missing(pct_b) else pct_b) - 50.0) * 2.0)
        macd_balance = 100.0 if shared.get("l0_macd", {}).get("alignment_state") == "MIXED_OR_WEAK" else 45.0
        weighted = macd_balance * 0.40 + rsi_balance * 0.30 + bollinger_balance * 0.30
        return {
            "weighted_score": weighted,
            "macd_score": macd_balance,
            "rsi_score": rsi_balance,
            "adx_score": adx_score,
            "weights": "Status Quo: mixed MACD 40%, RSI balance 30%, Bollinger balance 30%",
        }

    @staticmethod
    def _score_rsi(rsi: float, direction: str, candidate_state: str = "", setup_rsi_max: float | None = None) -> float:
        if StockScreener._is_missing(rsi):
            return 0.0
        if candidate_state in ["PRE_BULL_CROSSOVER", "SETUP_CANDIDATE"]:
            return StockScreener._score_bullish_setup_rsi_headroom(rsi, setup_rsi_max)
        if direction == "BULLISH":
            if 50 <= rsi <= 70:
                return 100.0
            if 45 <= rsi < 50:
                return 80.0
            if 70 < rsi <= 78:
                return 75.0
            if 40 <= rsi < 45:
                return 55.0
            if 78 < rsi <= 85:
                return 45.0
            return 20.0
        if direction == "BEARISH":
            if 30 <= rsi <= 50:
                return 100.0
            if 50 < rsi <= 55:
                return 80.0
            if 25 <= rsi < 30:
                return 65.0
            if 55 < rsi <= 60:
                return 50.0
            return 20.0
        return 0.0

    @staticmethod
    def _score_bullish_setup_rsi_headroom(rsi: float, setup_rsi_max: float | None = None) -> float:
        if StockScreener._is_missing(rsi):
            return 0.0
        ceiling = DEFAULTS.setup_rsi_max if setup_rsi_max is None else setup_rsi_max
        floor = DEFAULTS.setup_rsi_min
        if rsi > ceiling:
            return 0.0
        if rsi < floor:
            return StockScreener._clamp_score(35.0 + (rsi / floor * 25.0))
        headroom = ceiling - rsi
        range_width = max(1.0, ceiling - floor)
        return StockScreener._clamp_score(40.0 + (headroom / range_width * 60.0))

    @staticmethod
    def _score_adx(adx: dict[str, Any], direction: str) -> float:
        value = adx["adx"]
        if StockScreener._is_missing(value):
            return 0.0
        strength_score = 100.0 if value >= 35 else 80.0 if value >= 25 else 55.0 if value >= 20 else 30.0
        if direction in ["BULLISH", "BEARISH"] and adx["direction"] != direction:
            return strength_score * 0.5
        return strength_score

    def filter_profile(self, profile: SymbolProfile, shared: dict[str, Any]) -> tuple[bool, list[str]]:
        reasons: list[str] = []
        if self.filters.exchanges and profile.exchange:
            if profile.exchange.upper() not in [x.upper() for x in self.filters.exchanges]:
                reasons.append(f"Exchange filter failed: {profile.exchange}")
        if self.filters.sectors and profile.sector:
            if profile.sector.upper() not in [x.upper() for x in self.filters.sectors]:
                reasons.append(f"Sector filter failed: {profile.sector}")
        if self.filters.industries and profile.industry:
            if profile.industry.upper() not in [x.upper() for x in self.filters.industries]:
                reasons.append(f"Industry filter failed: {profile.industry}")
        if self.filters.price_min is not None and profile.latest_price is not None and profile.latest_price < self.filters.price_min:
            reasons.append(f"Price below min: {profile.latest_price}")
        if self.filters.price_max is not None and profile.latest_price is not None and profile.latest_price > self.filters.price_max:
            reasons.append(f"Price above max: {profile.latest_price}")
        if self.filters.market_cap_min is not None and profile.market_cap is not None and profile.market_cap < self.filters.market_cap_min:
            reasons.append(f"Market cap below min: {profile.market_cap}")
        if self.filters.market_cap_max is not None and profile.market_cap is not None and profile.market_cap > self.filters.market_cap_max:
            reasons.append(f"Market cap above max: {profile.market_cap}")
        if self.filters.avg_volume_min is not None and profile.avg_daily_volume is not None and profile.avg_daily_volume < self.filters.avg_volume_min:
            reasons.append(f"Daily volume below min: {profile.avg_daily_volume}")
        if self.filters.avg_volume_max is not None and profile.avg_daily_volume is not None and profile.avg_daily_volume > self.filters.avg_volume_max:
            reasons.append(f"Daily volume above max: {profile.avg_daily_volume}")
        etf_excluded = False
        if not self.filters.include_etfs and profile.instrument_type:
            itype = profile.instrument_type.upper()
            if "ETF" in itype:
                reasons.append(f"ETF excluded by web option: {profile.instrument_type}")
                etf_excluded = True
        if self.filters.types and profile.instrument_type and not etf_excluded:
            # Normalize and compare crude type strings
            itype = profile.instrument_type.upper()
            allowed = [t.upper() for t in self.filters.types]
            if not any(a in itype or itype in a for a in allowed):
                reasons.append(f"Instrument type filtered out: {profile.instrument_type}")
        rsi_value = shared["rsi_1d"]["rsi"]
        if self.filters.rsi_min is not None and not self._is_missing(rsi_value) and rsi_value < self.filters.rsi_min:
            reasons.append(f"RSI below min: {rsi_value}")
        if self.filters.rsi_max is not None and not self._is_missing(rsi_value) and rsi_value > self.filters.rsi_max:
            reasons.append(f"RSI above max: {rsi_value}")
        adx_value = shared["adx_1d"]["adx"]
        if self.filters.adx_min is not None and not self._is_missing(adx_value) and adx_value < self.filters.adx_min:
            reasons.append(f"ADX below min: {adx_value}")
        if self.filters.adx_max is not None and not self._is_missing(adx_value) and adx_value > self.filters.adx_max:
            reasons.append(f"ADX above max: {adx_value}")
        percent_b = shared["bollinger_1d"]["percent_b"]
        if self.filters.bollinger_pct_min is not None and not self._is_missing(percent_b) and percent_b < self.filters.bollinger_pct_min:
            reasons.append(f"Bollinger %b below min: {percent_b}")
        if self.filters.bollinger_pct_max is not None and not self._is_missing(percent_b) and percent_b > self.filters.bollinger_pct_max:
            reasons.append(f"Bollinger %b above max: {percent_b}")
        if self.filters.states and shared["candidate_state"] not in self.filters.states:
            reasons.append(f"State filtered out: {shared['candidate_state']}")
        if (
            self.filters.pre_bull_confidence_min is not None
            and shared["candidate_state"] == "PRE_BULL_CROSSOVER"
            and float(shared.get("pre_bull_quality", {}).get("confidence") or 0) < self.filters.pre_bull_confidence_min
        ):
            reasons.append(f"Pre-Bull confidence below min: {shared.get('pre_bull_quality', {}).get('confidence', 0)}")
        return len(reasons) == 0, reasons

    def _screen_symbol(self, symbol: str) -> dict[str, Any] | None:
        try:
            profile = self.fetch_profile(symbol)
            df_1d = self._load_price_data(symbol, "1d")
            df_4h = self._load_optional_price_data(symbol, "4h")
            df_1h = self._load_optional_price_data(symbol, "1h")
            if profile.avg_daily_volume is None:
                profile.avg_daily_volume = float(df_1d["Volume"].tail(21).mean())
            profile.avg_monthly_volume = float(df_1d["Volume"].tail(63).mean())
            macd_1d = self.calculate_macd(df_1d)
            macd_4h = self.calculate_macd(df_4h)
            macd_1h = self.calculate_macd(df_1h)
            baseline_macd_1d = self.calculate_macd(
                df_1d,
                DEFAULTS.baseline_macd_fast,
                DEFAULTS.baseline_macd_slow,
                DEFAULTS.baseline_macd_signal,
            )
            baseline_macd_4h = self.calculate_macd(
                df_4h,
                DEFAULTS.baseline_macd_fast,
                DEFAULTS.baseline_macd_slow,
                DEFAULTS.baseline_macd_signal,
            )
            baseline_macd_1h = self.calculate_macd(
                df_1h,
                DEFAULTS.baseline_macd_fast,
                DEFAULTS.baseline_macd_slow,
                DEFAULTS.baseline_macd_signal,
            )
            shared = {
                "macd_1d": macd_1d,
                "macd_4h": macd_4h,
                "macd_1h": macd_1h,
                "baseline_macd_1d": baseline_macd_1d,
                "baseline_macd_4h": baseline_macd_4h,
                "baseline_macd_1h": baseline_macd_1h,
                "rsi_1d": self.calculate_rsi(df_1d),
                "adx_1d": self.calculate_adx(df_1d),
                "bollinger_1d": self.calculate_bollinger(df_1d),
                "volume_price_1d": self.calculate_volume_price_profile(df_1d),
                "ema200": self.calculate_ema200(df_1d),
                "ceiling_profile": self.calculate_ceiling_profile(df_1d),
                "price_ladder": self.calculate_price_ladder(df_1d),
            }
            shared["setup_rsi_max"] = self.filters.setup_rsi_max if self.filters.setup_rsi_max is not None else DEFAULTS.setup_rsi_max
            divergence_1h = self.detect_macd_divergence(df_1h, pd.Series(macd_1h["histogram_series"]))
            divergence_4h = self.detect_macd_divergence(df_4h, pd.Series(macd_4h["histogram_series"]))
            divergence_1d = self.detect_macd_divergence(df_1d, pd.Series(macd_1d["histogram_series"]))
            baseline_divergence_1h = self.detect_macd_divergence(df_1h, pd.Series(baseline_macd_1h["histogram_series"]))
            baseline_divergence_4h = self.detect_macd_divergence(df_4h, pd.Series(baseline_macd_4h["histogram_series"]))
            baseline_divergence_1d = self.detect_macd_divergence(df_1d, pd.Series(baseline_macd_1d["histogram_series"]))
            shared["l0_macd"] = self._l0_macd_prequalification(shared)
            macd_flow = self.build_bottom_up_macd_flow(
                macd_1h,
                macd_4h,
                macd_1d,
                divergence_1h,
                divergence_4h,
                divergence_1d,
            )
            pre_bull_flow = self.build_pre_bull_crossover_flow(
                baseline_macd_1h,
                baseline_macd_4h,
                baseline_macd_1d,
            )
            if pre_bull_flow["state"] == "PRE_BULL_CROSSOVER":
                macd_flow = pre_bull_flow
            elif macd_flow["state"] in ["NONE", "PRE_BULL_CROSSOVER"]:
                macd_flow["reason"] = pre_bull_flow["reason"]
                if macd_flow["state"] == "PRE_BULL_CROSSOVER":
                    macd_flow["state"] = "NONE"
                    macd_flow["event_type"] = "NONE"
            shared["raw_divergence_1h"] = divergence_1h
            shared["raw_divergence_4h"] = divergence_4h
            shared["raw_divergence_1d"] = divergence_1d
            baseline_divergence = next(
                (
                    value
                    for value in [baseline_divergence_1d, baseline_divergence_4h, baseline_divergence_1h]
                    if value != "NONE"
                ),
                "NONE",
            )
            shared["baseline_divergence"] = baseline_divergence
            shared["baseline_divergence_1h"] = baseline_divergence_1h
            shared["baseline_divergence_4h"] = baseline_divergence_4h
            shared["baseline_divergence_1d"] = baseline_divergence_1d
            shared["macd_flow"] = macd_flow
            shared["pre_bull_trigger_macd_4h"] = baseline_macd_4h
            if macd_flow["event_type"] == "DIVERGENCE":
                shared["divergence"] = macd_flow["state"]
                shared["divergence_reason"] = macd_flow["reason"]
            else:
                shared["divergence"] = "NONE"
                shared["divergence_reason"] = (
                    f"Raw/baseline divergence observed ({baseline_divergence}) but not confirmed by bottom-up MACD flow."
                    if baseline_divergence != "NONE" or divergence_1d != "NONE" or divergence_4h != "NONE" or divergence_1h != "NONE"
                    else "No confirmed MACD divergence."
                )
            shared["support"] = self._support_profile(shared)
            shared["setup_passed"], shared["setup_score"], shared["setup_reason"] = self._setup_conditions(shared)
            candidate = self.classify_candidate(shared)
            shared["candidate_state"] = candidate["state"]
            shared["candidate_reason"] = candidate["reason"]
            weighted_score = self.calculate_weighted_score(shared)
            pre_bull_quality = shared.get("pre_bull_quality", {})
            volume_price_1d = shared["volume_price_1d"]
            passed, rejects = self.filter_profile(profile, shared)
            return {
                "Symbol": profile.symbol,
                "CompanyName": profile.company_name,
                "Exchange": profile.exchange,
                "Sector": profile.sector,
                "Industry": profile.industry,
                "LatestPrice": profile.latest_price,
                "MarketCap": profile.market_cap,
                "AvgDailyVolume": profile.avg_daily_volume,
                "AvgMonthlyVolume": profile.avg_monthly_volume,
                "MACD_1D_State": macd_1d["state"],
                "MACD_1D_Value": macd_1d["macd"],
                "MACD_1D_Histogram": macd_1d["histogram"],
                "MACD_4H_State": macd_4h["state"],
                "MACD_4H_Value": macd_4h["macd"],
                "MACD_4H_Crossover": macd_4h["crossover_event"],
                "MACD_4H_BarsSinceBullishCrossover": macd_4h["bars_since_bullish_crossover"],
                "MACD_1H_State": macd_1h["state"],
                "MACD_1H_Value": macd_1h["macd"],
                "MACD_1H_Crossover": macd_1h["crossover_event"],
                "MACD_1H_ClearBullishCrossover": macd_1h["clear_bullish_crossover"],
                "MACD_1H_ClearBearishCrossover": macd_1h["clear_bearish_crossover"],
                "MACD_1H_BarsSinceBullishCrossover": macd_1h["bars_since_bullish_crossover"],
                "MACD_1H_BarsSinceBearishCrossover": macd_1h["bars_since_bearish_crossover"],
                "MACD_1H_BarsSinceBullishZeroLineCross": macd_1h["bars_since_bullish_zero_line_cross"],
                "MACD_1H_BarsSinceBearishZeroLineCross": macd_1h["bars_since_bearish_zero_line_cross"],
                "MACD_1D_BarsSinceBullishZeroLineCross": macd_1d["bars_since_bullish_zero_line_cross"],
                "MACD_4H_BarsSinceBullishZeroLineCross": macd_4h["bars_since_bullish_zero_line_cross"],
                "PreBullFreshness": pre_bull_quality.get("freshness", ""),
                "PreBullConfidence": pre_bull_quality.get("confidence", ""),
                "PreBullQualityReason": pre_bull_quality.get("reason", ""),
                "RelativeVolume20": volume_price_1d["relative_volume_20"],
                "VPTTrend": volume_price_1d["vpt_state"],
                "VPTScore": volume_price_1d["vpt_score"],
                "CompressionState": volume_price_1d["compression_state"],
                "CompressionScore": volume_price_1d["compression_score"],
                "L0_MACD_Alignment": shared["l0_macd"]["alignment_state"],
                "L0_MACD_1D_Direction": shared["l0_macd"]["directions"]["1D"],
                "L0_MACD_4H_Direction": shared["l0_macd"]["directions"]["4H"],
                "L0_MACD_1H_Direction": shared["l0_macd"]["directions"]["1H"],
                "L0_MACD_ZeroLinePassed": shared["l0_macd"]["bullish_zero_line_passed"],
                "L0_MACD_BullishPassed": shared["l0_macd"]["bullish_passed"],
                "L0_MACD_Reason": shared["l0_macd"]["reason"],
                "MACD_Fast_1D_State": macd_1d["state"],
                "MACD_Fast_4H_State": macd_4h["state"],
                "MACD_Fast_1H_State": macd_1h["state"],
                "MACD_Baseline_1D_State": baseline_macd_1d["state"],
                "MACD_Baseline_1D_Regime": baseline_macd_1d["regime"],
                "MACD_Baseline_1D_Histogram": baseline_macd_1d["histogram"],
                "MACD_Baseline_1D_Value": baseline_macd_1d["macd"],
                "MACD_Baseline_4H_State": baseline_macd_4h["state"],
                "MACD_Baseline_4H_Value": baseline_macd_4h["macd"],
                "MACD_Baseline_4H_Crossover": baseline_macd_4h["crossover_event"],
                "MACD_Baseline_4H_BarsSinceBullishCrossover": baseline_macd_4h["bars_since_bullish_crossover"],
                "MACD_Baseline_1H_State": baseline_macd_1h["state"],
                "MACD_Baseline_1H_Value": baseline_macd_1h["macd"],
                "RawDivergence_1H": divergence_1h,
                "RawDivergence_4H": divergence_4h,
                "RawDivergence_1D": divergence_1d,
                "MACD_Flow_State": macd_flow["state"],
                "MACD_Flow_Reason": macd_flow["reason"],
                "ConfirmedDivergence": shared["divergence"],
                "BaselineDivergence": baseline_divergence,
                "RSI_1D": shared["rsi_1d"]["rsi"],
                "WeightedScore": weighted_score["weighted_score"],
                "MACDScore": weighted_score["macd_score"],
                "RSIScore": weighted_score["rsi_score"],
                "ADXScore": weighted_score["adx_score"],
                "ScoreWeights": weighted_score["weights"],
                "LifetimeHigh": shared["ceiling_profile"]["lifetime_high"],
                "DistanceToLifetimeHighPct": shared["ceiling_profile"]["distance_to_lifetime_high_pct"],
                "LifetimeHighBreakCount": shared["ceiling_profile"]["lifetime_high_break_count"],
                "EMA20": shared["ceiling_profile"]["ema20"],
                "EMA52High": shared["ceiling_profile"]["ema52_high"],
                "DistanceToEMA52HighPct": shared["ceiling_profile"]["distance_to_ema52_high_pct"],
                "EMA52HighBreachCount": shared["ceiling_profile"]["ema52_high_breach_count"],
                "EMA200High": shared["ceiling_profile"]["ema200_high"],
                "DistanceToEMA200HighPct": shared["ceiling_profile"]["distance_to_ema200_high_pct"],
                "EMA200HighBreachCount": shared["ceiling_profile"]["ema200_high_breach_count"],
                "CeilingPattern": shared["ceiling_profile"]["pattern"],
                "ADX_1D": shared["adx_1d"]["adx"],
                "ADX_State": shared["adx_1d"]["state"],
                "Bollinger_PctB": shared["bollinger_1d"]["percent_b"],
                "Bollinger_Position": shared["bollinger_1d"]["position"],
                "PriceLadder_Passed": shared["price_ladder"]["passed"],
                "SetupPassed": shared["setup_passed"],
                "SetupScore": shared["setup_score"],
                "CandidateState": shared["candidate_state"],
                "CandidateReason": shared["candidate_reason"],
                "FilterPassed": passed,
                "FilterReason": "; ".join(rejects) if rejects else "PASS",
            }
        except Exception as exc:
            logger.warning("Skipping %s: %s", symbol, exc)
            return {
                "Symbol": symbol.upper(),
                "CandidateState": "SKIPPED",
                "FilterPassed": False,
                "FilterReason": f"Skipped: {exc}",
                "_Skipped": True,
                "_SkipReason": str(exc),
            }

    def screen(self, symbols: list[str]) -> list[dict[str, Any]]:
        if not symbols:
            return []
        worker_count = self._worker_count(len(symbols))
        if worker_count == 1:
            return [row for symbol in symbols if (row := self._screen_symbol(symbol)) is not None]

        rows: list[dict[str, Any]] = []
        logger.info("Screening %d symbols with %d worker threads.", len(symbols), worker_count)
        with ThreadPoolExecutor(max_workers=worker_count, thread_name_prefix="screener") as executor:
            future_to_symbol = {executor.submit(self._screen_symbol, symbol): symbol for symbol in symbols}
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    row = future.result()
                except Exception as exc:
                    logger.warning("Skipping %s: %s", symbol, exc)
                    rows.append({
                        "Symbol": symbol.upper(),
                        "CandidateState": "SKIPPED",
                        "FilterPassed": False,
                        "FilterReason": f"Skipped: {exc}",
                        "_Skipped": True,
                        "_SkipReason": str(exc),
                    })
                    continue
                if row is not None:
                    rows.append(row)
        return rows


def parse_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def describe_filter_conditions(filters: ScreenerFilters) -> str:
    conditions = [
        ("Exchange", ", ".join(filters.exchanges) if filters.exchanges else "Any"),
        ("Sector", ", ".join(filters.sectors) if filters.sectors else "Any"),
        ("Industry", ", ".join(filters.industries) if filters.industries else "Any"),
        ("Type", ", ".join(filters.types) if filters.types else "Any"),
        ("IncludeEtf", "Yes" if filters.include_etfs else "No"),
        ("PriceMin", filters.price_min if filters.price_min is not None else "Any"),
        ("PriceMax", filters.price_max if filters.price_max is not None else "Any"),
        ("MarketCapMin", filters.market_cap_min if filters.market_cap_min is not None else "Any"),
        ("MarketCapMax", filters.market_cap_max if filters.market_cap_max is not None else "Any"),
        ("AvgVolumeMin", filters.avg_volume_min if filters.avg_volume_min is not None else "Any"),
        ("AvgVolumeMax", filters.avg_volume_max if filters.avg_volume_max is not None else "Any"),
        ("RsiMin", filters.rsi_min if filters.rsi_min is not None else "Any"),
        ("RsiMax", filters.rsi_max if filters.rsi_max is not None else "Any"),
        ("SetupRsiMax", filters.setup_rsi_max if filters.setup_rsi_max is not None else DEFAULTS.setup_rsi_max),
        ("AdxMin", filters.adx_min if filters.adx_min is not None else "Any"),
        ("AdxMax", filters.adx_max if filters.adx_max is not None else "Any"),
        ("BollingerPctMin", filters.bollinger_pct_min if filters.bollinger_pct_min is not None else "Any"),
        ("BollingerPctMax", filters.bollinger_pct_max if filters.bollinger_pct_max is not None else "Any"),
        ("PreBullConfidenceMin", filters.pre_bull_confidence_min if filters.pre_bull_confidence_min is not None else "Any"),
        ("States", ", ".join(filters.states) if filters.states else "Any candidate state"),
    ]
    return "; ".join(f"{name}: {value}" for name, value in conditions)


def build_output_rows(rows: list[dict[str, Any]], filters: ScreenerFilters) -> list[dict[str, Any]]:
    filter_summary = describe_filter_conditions(filters)
    output_rows = [
        {**row, "AppliedFilters": filter_summary}
        for row in rows
        if row.get("FilterPassed") is True and row.get("CandidateState") != "NO_CANDIDATE"
    ]
    return sort_output_rows(output_rows)


def sort_output_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    state_rank = {state: index for index, state in enumerate(CANDIDATE_STATE_ORDER)}

    def score_value(row: dict[str, Any]) -> float:
        try:
            return float(row.get("WeightedScore") or 0)
        except (TypeError, ValueError):
            return 0.0

    return sorted(
        rows,
        key=lambda row: (
            state_rank.get(str(row.get("CandidateState", "")), len(state_rank)),
            -score_value(row),
            str(row.get("Symbol", "")),
        ),
    )


def export_rows(output_rows: list[dict[str, Any]], output_file: str) -> int:
    df = pd.DataFrame(output_rows)
    for column in OUTPUT_COLUMNS:
        if column not in df.columns:
            df[column] = None
    df[OUTPUT_COLUMNS].to_csv(output_file, index=False)
    return len(output_rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MACD-based stock screener for Pre-Bull, Pre-Bear, and Bull Extended states.")
    parser.add_argument("--symbols-file", required=False, help="CSV file containing a Symbol column. If omitted, PMDE baseline or Tools/StockCodeMaster is used.")
    parser.add_argument("--output-file", default="screener_output.csv", help="CSV file to write screening results.")
    parser.add_argument("--html-output", default="screener_report.html", help="HTML report file to write filtered screening results.")
    parser.add_argument("--exchange", help="Comma-separated exchange filters.")
    parser.add_argument("--sector", help="Comma-separated sector filters.")
    parser.add_argument("--industry", help="Comma-separated industry filters.")
    parser.add_argument("--price-min", type=float)
    parser.add_argument("--price-max", type=float)
    parser.add_argument("--market-cap-min", type=float)
    parser.add_argument("--market-cap-max", type=float)
    parser.add_argument("--avg-volume-min", type=float)
    parser.add_argument("--avg-volume-max", type=float)
    parser.add_argument("--rsi-min", type=float)
    parser.add_argument("--rsi-max", type=float)
    parser.add_argument("--setup-rsi-max", type=float, default=DEFAULTS.setup_rsi_max)
    parser.add_argument("--adx-min", type=float)
    parser.add_argument("--adx-max", type=float)
    parser.add_argument("--bollinger-pct-min", type=float)
    parser.add_argument("--bollinger-pct-max", type=float)
    parser.add_argument("--pre-bull-confidence-min", type=float)
    parser.add_argument("--states", help="Comma-separated target candidate states.")
    parser.add_argument("--types", help="Comma-separated instrument types to include (e.g. ETF, EQUITY, COMMON STOCK).")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(message)s")
    filters = ScreenerFilters(
        exchanges=parse_list(args.exchange) if args.exchange else [],
        sectors=parse_list(args.sector) if args.sector else [],
        industries=parse_list(args.industry) if args.industry else [],
        types=parse_list(args.types) if args.types else [],
        price_min=args.price_min,
        price_max=args.price_max,
        market_cap_min=args.market_cap_min,
        market_cap_max=args.market_cap_max,
        avg_volume_min=args.avg_volume_min,
        avg_volume_max=args.avg_volume_max,
        rsi_min=args.rsi_min,
        rsi_max=args.rsi_max,
        setup_rsi_max=args.setup_rsi_max,
        adx_min=args.adx_min,
        adx_max=args.adx_max,
        bollinger_pct_min=args.bollinger_pct_min,
        bollinger_pct_max=args.bollinger_pct_max,
        pre_bull_confidence_min=args.pre_bull_confidence_min,
        states=parse_list(args.states) if args.states else [],
    )
    screener = StockScreener(filters)
    symbols = StockScreener.load_universe(args.symbols_file)
    rows = screener.screen(symbols)
    output_rows = build_output_rows(rows, filters)
    matched_count = export_rows(output_rows, args.output_file)
    generate_html_report(output_rows, args.html_output, describe_filter_conditions(filters))
    logger.info(
        "Screened %d symbols. Wrote %d matching rows to %s and %s",
        len(rows),
        matched_count,
        args.output_file,
        args.html_output,
    )


if __name__ == "__main__":
    main()
