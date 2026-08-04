import pandas as pd
import ta
import yfinance as yf
from datetime import datetime, time as dt_time
from zoneinfo import ZoneInfo
import os
import argparse
import sys
import logging
import concurrent.futures
import threading


# Keep expected per-symbol Yahoo data gaps in the structured ERROR output
# instead of printing raw library errors into the scanner's terminal summary.
logging.getLogger("yfinance").setLevel(logging.CRITICAL)

# ============================================================================== 
# ENHANCED VERSION 14 - ADAPTIVE PER-TICKER BASELINE + BOUNDED CONCURRENCY
# ==============================================================================

EMA_FAST_PERIOD = 50
EMA_SLOW_PERIOD = 200
MACD_FAST_PERIOD = 12
MACD_SLOW_PERIOD = 26
MACD_SIGNAL_PERIOD = 9
ADX_PERIOD = 14
RSI_PERIOD = 14
ATR_PERIOD = 14
STOCH_K_PERIOD = 9
STOCH_D_PERIOD = 6
WEEKLY_EMA_FAST = 20
WEEKLY_EMA_SLOW = 50
VOLUME_LOOKBACK = 20
HISTORICAL_CONTEXT_LOOKBACK = 252
HISTORICAL_GUIDANCE_ONE_YEAR_SESSIONS = 252
HISTORICAL_GUIDANCE_MAX_TICKERS = 100
HISTORICAL_GUIDANCE_FIVE_YEAR_MAX_TICKERS = 1000
STOCH_RECENT_LOOKBACK = 3
STOCH_RECOVERY_BUFFER = 10.0

DEFAULT_MAX_WORKERS = 3
DEFAULT_BUY_STOCH_MAX = 80.0
DEFAULT_CURRENT_VOLUME_MIN_RATIO = 0.60
DEFAULT_US_MIN_ADV20_TURNOVER = 1_000_000.0
DEFAULT_EXTREME_EXTENSION_REVIEW_ATR = 5.0


_DAILY_HISTORY_CACHE: dict[tuple[str, str], pd.DataFrame] = {}
_DAILY_HISTORY_CACHE_LOCK = threading.Lock()


UTC_TZ = ZoneInfo("UTC")
US_MARKET_TZ = ZoneInfo("America/New_York")
INDIA_MARKET_TZ = ZoneInfo("Asia/Kolkata")
JAPAN_MARKET_TZ = ZoneInfo("Asia/Tokyo")
KOREA_MARKET_TZ = ZoneInfo("Asia/Seoul")
TAIWAN_MARKET_TZ = ZoneInfo("Asia/Taipei")
DEFAULT_MARKET_TZ = US_MARKET_TZ

DEFAULT_SESSION_PROFILE = {
    "timezone": DEFAULT_MARKET_TZ,
    "pre_start": dt_time(4, 0),
    "regular_start": dt_time(9, 30),
    "regular_end": dt_time(16, 0),
    "post_end": dt_time(20, 0),
    "extended_hours": True,
}

FALLBACK_SESSION_PROFILES = {
    "US": DEFAULT_SESSION_PROFILE,
    "NSE": {
        "timezone": INDIA_MARKET_TZ,
        "pre_start": dt_time(9, 0),
        "regular_start": dt_time(9, 15),
        "regular_end": dt_time(15, 30),
        "post_end": dt_time(16, 0),
        "extended_hours": False,
    },
    "BSE": {
        "timezone": INDIA_MARKET_TZ,
        "pre_start": dt_time(9, 0),
        "regular_start": dt_time(9, 15),
        "regular_end": dt_time(15, 30),
        "post_end": dt_time(16, 0),
        "extended_hours": False,
    },
    "JP": {
        "timezone": JAPAN_MARKET_TZ,
        "pre_start": dt_time(8, 0),
        "regular_start": dt_time(9, 0),
        "regular_end": dt_time(15, 0),
        "post_end": dt_time(15, 30),
        "extended_hours": False,
    },
    "KR": {
        "timezone": KOREA_MARKET_TZ,
        "pre_start": dt_time(8, 0),
        "regular_start": dt_time(9, 0),
        "regular_end": dt_time(15, 30),
        "post_end": dt_time(16, 0),
        "extended_hours": False,
    },
    "TW": {
        "timezone": TAIWAN_MARKET_TZ,
        "pre_start": dt_time(8, 30),
        "regular_start": dt_time(9, 0),
        "regular_end": dt_time(13, 30),
        "post_end": dt_time(14, 0),
        "extended_hours": False,
    },
}


def _safe_zoneinfo(zone_name: str | None) -> ZoneInfo | None:
    zone_name = str(zone_name or "").strip()
    if not zone_name:
        return None
    try:
        return ZoneInfo(zone_name)
    except Exception:
        return None


def _fallback_market_key(ticker_symbol: str) -> str:
    symbol = normalize_ticker_symbol(ticker_symbol)
    if symbol.endswith(".NS"):
        return "NSE"
    if symbol.endswith(".BO"):
        return "BSE"
    if symbol.endswith((".T", ".TYO")):
        return "JP"
    if symbol.endswith((".KS", ".KQ")):
        return "KR"
    if symbol.endswith((".TW", ".TWO")):
        return "TW"
    return "US"


def _exchange_label(ticker_symbol: str, metadata: dict | None = None) -> str:
    exchange_name = str((metadata or {}).get("fullExchangeName") or (metadata or {}).get("exchangeName") or "").strip()
    if exchange_name:
        return exchange_name
    market_key = _fallback_market_key(ticker_symbol)
    return {
        "US": "US",
        "NSE": "NSE",
        "BSE": "BSE",
        "JP": "Japan",
        "KR": "Korea",
        "TW": "Taiwan",
    }.get(market_key, "US")


def normalize_ticker_symbol(ticker_symbol: str) -> str:
    symbol = str(ticker_symbol or "").strip().upper()
    if symbol.startswith("XNSE:"):
        symbol = symbol.removeprefix("XNSE:") + ".NS"
    elif symbol.startswith("XNSE") and not symbol.endswith(".NS"):
        symbol = symbol[4:].lstrip(":") + ".NS"
    elif symbol.startswith(("XBOM:", "XBSE:")):
        symbol = symbol.split(":", 1)[1] + ".BO"
    elif "$" in symbol:
        base, preferred_series = symbol.split("$", 1)
        if base and preferred_series:
            symbol = f"{base}-P{preferred_series}"
    return symbol


def select_historical_guidance_scope(input_ticker_count: int) -> str:
    """
    Select advisory history depth from the full input-code count.

    This scope must never be used to size a poll or qualify a signal.
    """
    ticker_count = max(0, int(input_ticker_count or 0))
    if ticker_count <= HISTORICAL_GUIDANCE_MAX_TICKERS:
        return "MAX"
    if ticker_count <= HISTORICAL_GUIDANCE_FIVE_YEAR_MAX_TICKERS:
        return "5Y"
    return "1Y"


def fetch_daily_history_cached(
    ticker_data,
    ticker_symbol: str,
    period: str,
) -> pd.DataFrame:
    """Fetch adjusted daily history once per ticker/period during this run."""
    cache_key = (normalize_ticker_symbol(ticker_symbol), str(period).lower())
    with _DAILY_HISTORY_CACHE_LOCK:
        cached = _DAILY_HISTORY_CACHE.get(cache_key)
    if cached is not None:
        return cached.copy()

    fetched = ticker_data.history(
        period=period,
        interval="1d",
        prepost=False,
        auto_adjust=True,
    )
    if fetched is None:
        fetched = pd.DataFrame()
    if not fetched.empty:
        with _DAILY_HISTORY_CACHE_LOCK:
            _DAILY_HISTORY_CACHE[cache_key] = fetched.copy()
    return fetched.copy()


def resolve_market(ticker_symbol: str, metadata: dict | None = None) -> str:
    return _exchange_label(ticker_symbol, metadata=metadata)


def _market_profile(ticker_symbol: str, metadata: dict | None = None) -> dict:
    fallback_market = _fallback_market_key(ticker_symbol)
    profile = dict(FALLBACK_SESSION_PROFILES.get(fallback_market, DEFAULT_SESSION_PROFILE))
    market_timezone = _safe_zoneinfo((metadata or {}).get("exchangeTimezoneName"))
    if market_timezone is not None:
        profile["timezone"] = market_timezone
    return profile


def _metadata_period_datetime(period: dict | None, key: str, market_tz: ZoneInfo) -> datetime | None:
    if not period or period.get(key) is None:
        return None
    try:
        return datetime.fromtimestamp(float(period[key]), UTC_TZ).astimezone(market_tz)
    except (TypeError, ValueError, OSError):
        return None


def get_market_context(
    ticker_symbol: str,
    metadata: dict | None = None,
    now: datetime | None = None,
) -> dict:
    market = _exchange_label(ticker_symbol, metadata=metadata)
    profile = _market_profile(ticker_symbol, metadata=metadata)
    market_tz = profile["timezone"]
    now_local = now.astimezone(market_tz) if now and now.tzinfo else (
        now.replace(tzinfo=market_tz) if now else datetime.now(market_tz)
    )
    session_date = now_local.date()

    pre_start_dt = datetime.combine(session_date, profile["pre_start"], tzinfo=market_tz)
    regular_start_dt = datetime.combine(session_date, profile["regular_start"], tzinfo=market_tz)
    regular_end_dt = datetime.combine(session_date, profile["regular_end"], tzinfo=market_tz)
    post_end_dt = datetime.combine(session_date, profile["post_end"], tzinfo=market_tz)

    trading_period = (metadata or {}).get("currentTradingPeriod") or {}
    metadata_regular = trading_period.get("regular") or {}
    metadata_regular_start = _metadata_period_datetime(metadata_regular, "start", market_tz)
    metadata_regular_end = _metadata_period_datetime(metadata_regular, "end", market_tz)
    metadata_pre = trading_period.get("pre") or {}
    metadata_post = trading_period.get("post") or {}
    metadata_pre_start = _metadata_period_datetime(metadata_pre, "start", market_tz)
    metadata_post_end = _metadata_period_datetime(metadata_post, "end", market_tz)
    metadata_session_matches = bool(
        metadata_regular_start
        and metadata_regular_end
        and metadata_regular_start.date() == session_date
    )

    if metadata_session_matches:
        regular_start_dt = metadata_regular_start
        regular_end_dt = metadata_regular_end
        pre_start_dt = metadata_pre_start or pre_start_dt
        post_end_dt = metadata_post_end or post_end_dt

    calendar_closed = now_local.weekday() >= 5 or (
        bool(metadata_regular_start) and not metadata_session_matches
    )
    allow_extended_hours = bool(metadata_pre_start and metadata_post_end and profile.get("extended_hours", False))

    if calendar_closed:
        phase = "CLOSED"
        effective_mode = "completed"
        reason = f"{market} market is closed for this exchange-local session; using the latest completed regular-session candle."
    elif pre_start_dt <= now_local < regular_start_dt:
        phase = "PREMARKET"
        if allow_extended_hours:
            effective_mode = "intraday"
            reason = "US pre-market; using an extended-hours preview candle when fresh minute bars are available."
        else:
            effective_mode = "completed"
            reason = f"{market} pre-open auction; using the previous completed candle until regular-session trades begin."
    elif regular_start_dt <= now_local < regular_end_dt:
        phase = "REGULAR"
        effective_mode = "intraday"
        reason = f"{market} regular session; rebuilding the current partial daily candle from regular-session minute bars."
    elif regular_end_dt <= now_local < post_end_dt:
        phase = "POSTMARKET"
        effective_mode = "completed"
        reason = f"{market} regular session has closed; using today's completed regular-session candle."
    else:
        phase = "CLOSED"
        effective_mode = "completed"
        reason = f"{market} market is outside its active session; using the latest completed regular-session candle."

    return {
        "market": market,
        "market_key": _fallback_market_key(ticker_symbol),
        "phase": phase,
        "effective_mode": effective_mode,
        "market_time_local": now_local.isoformat(timespec="seconds"),
        "market_time_et": now_local.astimezone(US_MARKET_TZ).isoformat(timespec="seconds"),
        "session_date": session_date.isoformat(),
        "candle_state": "CURRENT_PARTIAL" if effective_mode == "intraday" else "LAST_COMPLETED",
        "reason": reason,
        "_calendar_closed": calendar_closed,
        "_timezone": market_tz,
        "_now_local": now_local,
        "_pre_start": pre_start_dt,
        "_regular_start": regular_start_dt,
        "_regular_end": regular_end_dt,
        "_post_end": post_end_dt,
        "_allow_extended_hours": allow_extended_hours,
    }


def get_us_market_phase(now: datetime | None = None) -> dict:
    return get_market_context("AAPL", now=now)


def filter_intraday_to_session(intraday_df: pd.DataFrame, market_context: dict) -> pd.DataFrame:
    if intraday_df is None or intraday_df.empty:
        return pd.DataFrame()

    intraday = intraday_df.copy()
    try:
        market_tz = market_context["_timezone"]
        index = pd.DatetimeIndex(intraday.index)
        if index.tz is None:
            index = index.tz_localize(market_tz)
        else:
            index = index.tz_convert(market_tz)
        intraday.index = index

        if market_context["phase"] == "PREMARKET":
            start_dt = market_context["_pre_start"]
            end_dt = min(market_context["_now_local"], market_context["_regular_start"])
        else:
            start_dt = market_context["_regular_start"]
            end_dt = min(market_context["_now_local"], market_context["_regular_end"])
        return intraday.loc[(intraday.index >= start_dt) & (intraday.index <= end_dt)].copy()
    except Exception:
        return pd.DataFrame()


def filter_intraday_to_today(intraday_df: pd.DataFrame, now: datetime | None = None) -> pd.DataFrame:
    return filter_intraday_to_session(intraday_df, get_us_market_phase(now))


def drop_incomplete_daily_row(df: pd.DataFrame, market_context: dict) -> pd.DataFrame:
    if df.empty:
        return df
    session_date = pd.Timestamp(market_context["session_date"]).date()
    index = pd.DatetimeIndex(df.index)
    market_tz = market_context.get("_timezone")
    if index.tz is not None and market_tz is not None:
        index = index.tz_convert(market_tz)
    keep = [pd.Timestamp(idx).date() != session_date for idx in index]
    return df.loc[keep].copy()


def has_session_daily_row(df: pd.DataFrame, market_context: dict) -> bool:
    if df is None or df.empty:
        return False
    session_date = pd.Timestamp(market_context["session_date"]).date()
    index = pd.DatetimeIndex(df.index)
    market_tz = market_context.get("_timezone")
    if index.tz is not None and market_tz is not None:
        index = index.tz_convert(market_tz)
    return any(pd.Timestamp(idx).date() == session_date for idx in index)


def has_complete_session_daily_row(df: pd.DataFrame, market_context: dict) -> bool:
    if df is None or df.empty:
        return False
    session_date = pd.Timestamp(market_context["session_date"]).date()
    index = pd.DatetimeIndex(df.index)
    market_tz = market_context.get("_timezone")
    if index.tz is not None and market_tz is not None:
        index = index.tz_convert(market_tz)
    session_rows = df.loc[[pd.Timestamp(idx).date() == session_date for idx in index]]
    if session_rows.empty:
        return False
    required_columns = [col for col in ("open", "high", "low", "close") if col in session_rows.columns]
    if len(required_columns) < 4:
        return False
    last_row = session_rows.iloc[-1]
    return bool(last_row[required_columns].notna().all())


def drop_trailing_incomplete_daily_row(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    required_columns = [col for col in ("open", "high", "low", "close") if col in df.columns]
    if len(required_columns) < 4:
        return df
    last_row = df.iloc[-1]
    if last_row[required_columns].notna().all():
        return df
    return df.iloc[:-1].copy()


def regular_session_elapsed_fraction(
    market_context: dict,
    observation_time: datetime | pd.Timestamp | None = None,
) -> float | None:
    """Return the completed fraction of the listing's regular session."""
    if market_context.get("phase") != "REGULAR":
        return None

    regular_start = market_context.get("_regular_start")
    regular_end = market_context.get("_regular_end")
    observed_at = observation_time or market_context.get("_now_local")
    if regular_start is None or regular_end is None or observed_at is None:
        return None

    try:
        observed_at = pd.Timestamp(observed_at).to_pydatetime()
        duration_seconds = (regular_end - regular_start).total_seconds()
        elapsed_seconds = (
            min(max(observed_at, regular_start), regular_end) - regular_start
        ).total_seconds()
    except (TypeError, ValueError):
        return None

    if duration_seconds <= 0 or elapsed_seconds <= 0:
        return None
    return min(1.0, elapsed_seconds / duration_seconds)


def calculate_session_paced_volume_ratios(
    current_volume: float | None,
    average_daily_volume: float | None,
    session_elapsed_fraction: float | None,
) -> tuple[float | None, float | None]:
    """Return raw and elapsed-session-adjusted daily volume ratios."""
    if (
        current_volume is None
        or average_daily_volume is None
        or average_daily_volume <= 0
    ):
        return None, None

    raw_ratio = current_volume / average_daily_volume
    if (
        session_elapsed_fraction is None
        or session_elapsed_fraction <= 0
        or session_elapsed_fraction >= 1
    ):
        return raw_ratio, raw_ratio

    return raw_ratio, raw_ratio / session_elapsed_fraction


BALANCED_CONFIG = {
    # ADX thresholds below are descriptive score bands only. They do not
    # qualify, reject, or cap a ticker.
    "adx_trend_strong": 20.0,
    "stoch_oversold": 30.0,
    "stoch_overbought": 80.0,
    "stoch_mid_low": 40.0,
    "stoch_mid_high": 65.0,
    "atr_safe_mult": 2.2,
    "atr_ext_mult": 3.0,
    "ema20_max_gap_atr": 0.50,
    "volume_mult": 1.2,
    "stoch_recent_lookback": STOCH_RECENT_LOOKBACK,
    "stoch_recovery_buffer": STOCH_RECOVERY_BUFFER,
    "continuation_volume_min_ratio": 0.80,
    "volume_history_min_percentile": 60.0,
    "current_volume_min_ratio": DEFAULT_CURRENT_VOLUME_MIN_RATIO,
    "us_min_adv20_turnover": DEFAULT_US_MIN_ADV20_TURNOVER,
    "extreme_extension_review_atr": DEFAULT_EXTREME_EXTENSION_REVIEW_ATR,
    "prior_positive_early_stoch_max": 90.0,
    "prior_positive_continuation_stoch_max": 100.0,
    "historical_context_lookback": HISTORICAL_CONTEXT_LOOKBACK,
    "hist_expansion_lookback": 3,
}

PRESETS = {
    "conservative": {
        **BALANCED_CONFIG,
        "adx_trend_strong": 25.0,
        "stoch_oversold": 20.0,
        "atr_safe_mult": 1.8,
        "atr_ext_mult": 2.5,
        "ema20_max_gap_atr": 0.35,
        "volume_mult": 1.4,
        "continuation_volume_min_ratio": 1.0,
    },
    "balanced": BALANCED_CONFIG,
    "aggressive": {
        **BALANCED_CONFIG,
        "adx_trend_strong": 18.0,
        "stoch_oversold": 35.0,
        "atr_safe_mult": 2.5,
        "atr_ext_mult": 3.5,
        "ema20_max_gap_atr": 0.75,
        "volume_mult": 1.0,
        "continuation_volume_min_ratio": 0.65,
    },
}

DEFAULT_INPUT_CSV = "D:\\Tools\\00_StockCodeMaster\\02_Stock\\22-07-US_Common_Stocks_Master_Library.csv"
DEFAULT_OUTPUT_XLSX = os.path.abspath("D:/TMP/Live_Screener/V14_Enhanced_Output.xlsx")
DEFAULT_BACKTEST_CSV = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "output",
        "V14_Enhanced_Backtest.csv",
    )
)
DEFAULT_FALLBACK_WATCHLIST = ["MU"]

STATUS_BUY_SIGNAL = "BUY"
STATUS_HOLD = "HOLD"
STATUS_IGNORE = "IGNORE"
STATUS_REJECT = "REJECT"
STATUS_ERROR = "ERROR"

SORT_ORDER_PRECEDENCE = [STATUS_BUY_SIGNAL, STATUS_HOLD, STATUS_IGNORE, STATUS_REJECT, STATUS_ERROR]

def sort_results_for_display(results: list[dict]) -> list[dict]:
    return sorted(
        results,
        key=lambda x: (
            SORT_ORDER_PRECEDENCE.index(x.get("status")) if x.get("status") in SORT_ORDER_PRECEDENCE else len(SORT_ORDER_PRECEDENCE),
            -(x.get("signal_score") or 0),
            str(x.get("ticker", "")),
        ),
    )


def normalize_date_text(date_text: str) -> str:
    parsed = pd.to_datetime(date_text, errors="coerce")
    if pd.isna(parsed):
        raise ValueError(f"Invalid date format: '{date_text}'. Use YYYY-MM-DD.")
    return parsed.strftime("%Y-%m-%d")


def build_as_of_date_list(as_of_date: str | None, as_of_dates: str | None) -> list[str | None]:
    if as_of_dates:
        normalized = []
        seen = set()
        for raw_date in as_of_dates.split(","):
            item = raw_date.strip()
            if not item:
                continue
            normalized_item = normalize_date_text(item)
            if normalized_item not in seen:
                normalized.append(normalized_item)
                seen.add(normalized_item)
        if not normalized:
            raise ValueError("--as-of-dates was provided but no valid dates were found.")
        return normalized

    if as_of_date:
        return [normalize_date_text(as_of_date)]

    return [None]


def included_session_date(df: pd.DataFrame) -> str | None:
    """Return the actual final daily session included in an evaluation frame."""
    if df.empty:
        return None
    try:
        return pd.Timestamp(df.index[-1]).date().isoformat()
    except (TypeError, ValueError):
        return None


def summarize_data_through(results: list[dict]) -> str:
    """Summarize successful rows' included session dates for run-level output."""
    session_dates = set()
    for result in results:
        if result.get("status") == STATUS_ERROR:
            continue
        raw_date = result.get("session_date")
        if raw_date in (None, ""):
            continue
        parsed_date = pd.to_datetime(raw_date, errors="coerce")
        if not pd.isna(parsed_date):
            session_dates.add(parsed_date.strftime("%Y-%m-%d"))

    ordered_dates = sorted(session_dates)
    if not ordered_dates:
        return "Unavailable"
    if len(ordered_dates) == 1:
        return ordered_dates[0]
    return (
        f"{ordered_dates[0]} to {ordered_dates[-1]} "
        f"({len(ordered_dates)} session dates)"
    )


def filter_to_as_of_date(df: pd.DataFrame, as_of_date: str) -> pd.DataFrame:
    as_of_ts = pd.Timestamp(as_of_date).normalize() + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
    if getattr(df.index, "tz", None) is not None and as_of_ts.tzinfo is None:
        as_of_ts = as_of_ts.tz_localize(df.index.tz)
    return df.loc[df.index <= as_of_ts].copy()


def summarize_backtest_results(backtest_df: pd.DataFrame) -> dict:
    if backtest_df.empty:
        return {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate_pct": 0.0,
            "average_return_pct": 0.0,
            "average_win_pct": 0.0,
            "average_loss_pct": 0.0,
            "best_trade_pct": 0.0,
            "worst_trade_pct": 0.0,
            "max_drawdown_pct": 0.0,
            "top_tickers": [],
        }

    valid_returns = backtest_df["return_pct"].dropna()
    if valid_returns.empty:
        return {
            "total_trades": int(len(backtest_df)),
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate_pct": 0.0,
            "average_return_pct": 0.0,
            "average_win_pct": 0.0,
            "average_loss_pct": 0.0,
            "best_trade_pct": 0.0,
            "worst_trade_pct": 0.0,
            "max_drawdown_pct": 0.0,
            "top_tickers": [],
        }

    win_mask = valid_returns > 0
    loss_mask = valid_returns < 0
    compounded_values = (100 * (1 + valid_returns / 100).cumprod()).tolist()
    equity_curve = pd.Series([100.0, *compounded_values], dtype=float)
    running_max = equity_curve.cummax()
    drawdown = ((equity_curve / running_max) - 1) * 100

    top_tickers = (
        backtest_df.groupby("ticker")["return_pct"].mean().dropna().sort_values(ascending=False).head(10)
    )

    return {
        "total_trades": int(len(backtest_df)),
        "winning_trades": int(win_mask.sum()),
        "losing_trades": int(loss_mask.sum()),
        "win_rate_pct": round(float((win_mask.sum() / len(valid_returns)) * 100), 2) if len(valid_returns) else 0.0,
        "average_return_pct": round(float(valid_returns.mean()), 2),
        "average_win_pct": round(float(valid_returns[win_mask].mean()), 2) if win_mask.any() else 0.0,
        "average_loss_pct": round(float(valid_returns[loss_mask].mean()), 2) if loss_mask.any() else 0.0,
        "best_trade_pct": round(float(valid_returns.max()), 2),
        "worst_trade_pct": round(float(valid_returns.min()), 2),
        "max_drawdown_pct": round(float(drawdown.min()), 2),
        "top_tickers": [
            {"ticker": ticker, "avg_return_pct": round(float(return_pct), 2)}
            for ticker, return_pct in top_tickers.items()
        ],
    }


def get_config(preset_name: str = "balanced") -> dict:
    preset_key = (preset_name or "balanced").lower()
    if preset_key not in PRESETS:
        preset_key = "balanced"
    config = PRESETS[preset_key].copy()
    config["buy_stoch_max"] = DEFAULT_BUY_STOCH_MAX
    return config


def has_supportive_volume(
    volume_ratio: float | None,
    volume_history_percentile: float | None,
    config: dict,
) -> bool:
    """Apply the mandatory current-volume floor before alternate support paths."""
    if volume_ratio is None:
        return False

    current_floor = float(
        config.get(
            "current_volume_min_ratio",
            DEFAULT_CURRENT_VOLUME_MIN_RATIO,
        )
    )
    if volume_ratio < current_floor:
        return False

    continuation_floor = float(
        config.get("continuation_volume_min_ratio", 0.80)
    )
    history_floor = float(
        config.get("volume_history_min_percentile", 60.0)
    )
    return bool(
        volume_ratio >= continuation_floor
        or (
            volume_history_percentile is not None
            and volume_history_percentile >= history_floor
        )
    )


def is_confirmed_positive_macd_crossover(
    previous_macd: float,
    previous_signal: float,
    current_macd: float,
    current_signal: float,
) -> bool:
    """Require a fresh bullish MACD signal-line crossover above zero."""
    return bool(
        previous_macd <= previous_signal
        and current_macd > current_signal
        and current_macd > 0
        and current_signal > 0
    )


def is_confirmed_positive_histogram_expansion(
    histogram_values: list[float],
) -> bool:
    """Require an expanding window whose two latest bars are both positive."""
    return bool(
        len(histogram_values) >= 2
        and histogram_values[-2] > 0
        and histogram_values[-1] > 0
        and all(
            left < right
            for left, right in zip(histogram_values, histogram_values[1:])
        )
    )


def is_sustained_positive_histogram_contraction(
    histogram_values: list[float],
) -> bool:
    """Identify cooling only while every observed histogram bar stays positive."""
    return bool(
        len(histogram_values) >= 2
        and all(value > 0 for value in histogram_values)
        and all(
            left > right
            for left, right in zip(histogram_values, histogram_values[1:])
        )
    )


def build_weekly_data(
    df: pd.DataFrame,
    include_incomplete_week: bool = False,
    current_session_incomplete: bool = False,
) -> pd.DataFrame:
    weekly = df.resample("W-FRI").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    ).dropna()

    if not include_incomplete_week and not weekly.empty:
        last_daily_date = pd.Timestamp(df.index[-1]).date()
        last_week_end = pd.Timestamp(weekly.index[-1]).date()
        weekly_period_complete = bool(df.attrs.get("weekly_period_complete", False))
        if current_session_incomplete or (
            last_daily_date < last_week_end and not weekly_period_complete
        ):
            weekly = weekly.iloc[:-1]

    weekly["weekly_ema_20"] = ta.trend.ema_indicator(weekly["close"], window=WEEKLY_EMA_FAST)
    weekly["weekly_ema_50"] = ta.trend.ema_indicator(weekly["close"], window=WEEKLY_EMA_SLOW)
    return weekly


def merge_intraday_session_candle(
    df: pd.DataFrame,
    intraday_df: pd.DataFrame,
    market_context: dict,
    current_candle_partial: bool = True,
) -> pd.DataFrame:
    if intraday_df is None or intraday_df.empty:
        return df

    intraday = intraday_df.copy()
    intraday.columns = [str(col).lower() for col in intraday.columns]
    required = {"open", "high", "low", "close"}
    if not required.issubset(intraday.columns):
        return df

    intraday = intraday.dropna(subset=["close"])
    if intraday.empty:
        return df

    candle = {
        "open": float(intraday["open"].dropna().iloc[0]),
        "high": float(intraday["high"].max()),
        "low": float(intraday["low"].min()),
        "close": float(intraday["close"].iloc[-1]),
        "volume": float(intraday["volume"].fillna(0).sum()) if "volume" in intraday.columns else 0.0,
    }

    merged = df.copy()
    session_date = pd.Timestamp(market_context["session_date"]).date()
    daily_dates = pd.Index([pd.Timestamp(idx).date() for idx in merged.index])
    matches = daily_dates == session_date

    if matches.any():
        target_idx = merged.index[matches][-1]
        for key, value in candle.items():
            if key in merged.columns:
                merged.loc[target_idx, key] = value
    else:
        new_idx = pd.Timestamp(session_date)
        if getattr(merged.index, "tz", None) is not None:
            new_idx = new_idx.tz_localize(merged.index.tz)

        # Reindex first, then populate the new candle cell-by-cell. Assigning a
        # whole mixed/all-NA row with ``merged.loc[new_idx] = row`` invokes
        # pandas' deprecated concatenation path and emits a FutureWarning.
        expanded_index = merged.index.append(pd.DatetimeIndex([new_idx]))
        merged = merged.reindex(expanded_index).sort_index()
        for key, value in candle.items():
            if key in merged.columns:
                merged.at[new_idx, key] = value
        if "adj close" in merged.columns:
            merged.at[new_idx, "adj close"] = candle["close"]
        for action_column in ("dividends", "stock splits", "capital gains"):
            if action_column in merged.columns:
                merged.at[new_idx, action_column] = 0.0

    merged.attrs["current_candle_partial"] = current_candle_partial
    merged.attrs["volume_session_fraction"] = (
        regular_session_elapsed_fraction(
            market_context,
            observation_time=intraday.index[-1],
        )
        if current_candle_partial
        else None
    )
    return merged


def adx_band(value: float, config: dict) -> tuple[str, int]:
    trend_threshold = max(15.0, float(config.get("adx_trend_strong", 20.0)))
    if value < 15:
        return "Weak", 0
    if value < trend_threshold:
        return "Emerging", 1
    if value < 35:
        return "Healthy", 2
    if value <= 50:
        return "Strong", 3
    return "Extreme", 2


def historical_series_context(
    series: pd.Series,
    current_value: float,
    lookback: int = HISTORICAL_CONTEXT_LOOKBACK,
) -> dict:
    """
    Compare the current value with the ticker's own prior completed history.

    The current observation is excluded so a new historical maximum can
    legitimately exceed 100% and no current-candle look-ahead is introduced.
    """
    clean = pd.to_numeric(series, errors="coerce").dropna()
    prior = clean.iloc[-lookback - 1:-1]
    if prior.empty:
        return {
            "count": 0,
            "min": None,
            "max": None,
            "percentile": None,
            "pct_of_max": None,
        }

    prior_min = float(prior.min())
    prior_max = float(prior.max())
    percentile = float((prior <= current_value).mean() * 100.0)
    pct_of_max = (
        float(current_value / prior_max * 100.0)
        if prior_max > 0
        else None
    )
    return {
        "count": int(len(prior)),
        "min": prior_min,
        "max": prior_max,
        "percentile": percentile,
        "pct_of_max": pct_of_max,
    }


def historical_prior_context(
    prior_series: pd.Series,
    current_value: float | None,
) -> dict:
    """Compare a current value with an explicitly supplied prior-only series."""
    clean = pd.to_numeric(prior_series, errors="coerce").dropna()
    if clean.empty or current_value is None or pd.isna(current_value):
        return {
            "count": int(len(clean)),
            "min": None,
            "max": None,
            "percentile": None,
            "pct_of_max": None,
        }

    current_number = float(current_value)
    prior_min = float(clean.min())
    prior_max = float(clean.max())
    return {
        "count": int(len(clean)),
        "min": prior_min,
        "max": prior_max,
        "percentile": float((clean <= current_number).mean() * 100.0),
        "pct_of_max": (
            float(current_number / prior_max * 100.0)
            if prior_max > 0
            else None
        ),
    }


def relative_confidence_band(percent_of_history_max: float | None) -> str:
    if percent_of_history_max is None:
        return "Unavailable"
    if percent_of_history_max < 40:
        return "Developing"
    if percent_of_history_max < 60:
        return "Moderate"
    if percent_of_history_max < 80:
        return "Strong"
    if percent_of_history_max <= 100:
        return "Near Historical Peak"
    return "New Historical Peak"


def calculate_historical_guidance(
    guidance_df: pd.DataFrame,
    current_frame: pd.DataFrame,
    current_metrics: dict,
    guidance_scope: str,
    requested_scope: str,
) -> dict:
    """
    Build advisory per-ticker limits from prior history only.

    This function is intentionally called after evaluate_frame. Its output is
    reporting context and cannot affect signal status, output_signal, or score.
    """
    output = {
        "historical_guidance_requested_scope": requested_scope,
        "historical_guidance_scope": guidance_scope,
        "historical_guidance_sessions": 0,
        "price_guidance_high": None,
        "price_guidance_low": None,
        "price_pct_guidance_high": None,
        "price_distance_guidance_high_pct": None,
        "new_guidance_high": None,
        "rsi_guidance_min": None,
        "rsi_guidance_max": None,
        "rsi_guidance_percentile": None,
        "rsi_pct_guidance_max": None,
        "adx_guidance_max": None,
        "adx_guidance_percentile": None,
        "adx_pct_guidance_max": None,
        "adx_guidance_confidence": "Unavailable",
        "stoch_k_guidance_min": None,
        "stoch_k_guidance_max": None,
        "stoch_k_guidance_percentile": None,
        "stoch_k_pct_guidance_max": None,
        "volume_guidance_max": None,
        "volume_guidance_percentile": None,
        "volume_pct_guidance_max": None,
    }
    if guidance_df is None or guidance_df.empty or current_frame.empty:
        return output

    guidance = guidance_df.copy()
    guidance.columns = [str(col).lower() for col in guidance.columns]
    required_columns = {"high", "low", "close", "volume"}
    if not required_columns.issubset(guidance.columns):
        return output

    current_index = pd.Timestamp(current_frame.index[-1])
    current_date = current_index.date()
    guidance_dates = pd.Index(
        [pd.Timestamp(index_value).date() for index_value in guidance.index]
    )

    # Drop every future row before calculating indicators. This prevents
    # historical as-of validation from seeing any later observation.
    guidance = guidance.loc[guidance_dates <= current_date].copy()
    if guidance.empty:
        return output

    guidance["rsi_guidance"] = ta.momentum.rsi(
        guidance["close"],
        window=RSI_PERIOD,
    )
    guidance["adx_guidance"] = ta.trend.adx(
        guidance["high"],
        guidance["low"],
        guidance["close"],
        window=ADX_PERIOD,
    )
    guidance["stoch_k_guidance"] = ta.momentum.stoch(
        guidance["high"],
        guidance["low"],
        guidance["close"],
        window=STOCH_K_PERIOD,
    )

    filtered_dates = pd.Index(
        [pd.Timestamp(index_value).date() for index_value in guidance.index]
    )
    prior = guidance.loc[filtered_dates < current_date].copy()
    normalized_scope = str(guidance_scope or "").upper()
    if normalized_scope.startswith("1Y"):
        prior = prior.tail(HISTORICAL_GUIDANCE_ONE_YEAR_SESSIONS)
    elif normalized_scope.startswith("5Y"):
        five_year_start = (
            pd.Timestamp(current_date) - pd.DateOffset(years=5)
        ).date()
        prior_dates = pd.Index(
            [pd.Timestamp(index_value).date() for index_value in prior.index]
        )
        prior = prior.loc[prior_dates >= five_year_start]

    if prior.empty:
        return output

    def metric_number(name: str) -> float | None:
        value = current_metrics.get(name)
        if value is None or pd.isna(value):
            return None
        return float(value)

    rsi_context = historical_prior_context(
        prior["rsi_guidance"],
        metric_number("rsi"),
    )
    adx_context = historical_prior_context(
        prior["adx_guidance"],
        metric_number("adx"),
    )
    stoch_context = historical_prior_context(
        prior["stoch_k_guidance"],
        metric_number("stoch_k"),
    )
    volume_context = historical_prior_context(
        prior["volume"],
        metric_number("volume"),
    )

    prior_high = float(prior["high"].max())
    prior_low = float(prior["low"].min())
    current_price = metric_number("price")
    current_high = float(current_frame.iloc[-1]["high"])
    price_pct_high = (
        current_price / prior_high * 100.0
        if current_price is not None and prior_high > 0
        else None
    )
    price_distance_high = (
        (current_price / prior_high - 1.0) * 100.0
        if current_price is not None and prior_high > 0
        else None
    )
    new_guidance_high = bool(current_high > prior_high)

    output.update({
        "historical_guidance_sessions": int(len(prior)),
        "price_guidance_high": round(prior_high, 2),
        "price_guidance_low": round(prior_low, 2),
        "price_pct_guidance_high": (
            round(price_pct_high, 2) if price_pct_high is not None else None
        ),
        "price_distance_guidance_high_pct": (
            round(price_distance_high, 2)
            if price_distance_high is not None
            else None
        ),
        "new_guidance_high": new_guidance_high,
        "rsi_guidance_min": (
            round(rsi_context["min"], 2)
            if rsi_context["min"] is not None
            else None
        ),
        "rsi_guidance_max": (
            round(rsi_context["max"], 2)
            if rsi_context["max"] is not None
            else None
        ),
        "rsi_guidance_percentile": (
            round(rsi_context["percentile"], 2)
            if rsi_context["percentile"] is not None
            else None
        ),
        "rsi_pct_guidance_max": (
            round(rsi_context["pct_of_max"], 2)
            if rsi_context["pct_of_max"] is not None
            else None
        ),
        "adx_guidance_max": (
            round(adx_context["max"], 2)
            if adx_context["max"] is not None
            else None
        ),
        "adx_guidance_percentile": (
            round(adx_context["percentile"], 2)
            if adx_context["percentile"] is not None
            else None
        ),
        "adx_pct_guidance_max": (
            round(adx_context["pct_of_max"], 2)
            if adx_context["pct_of_max"] is not None
            else None
        ),
        "adx_guidance_confidence": relative_confidence_band(
            adx_context["pct_of_max"]
        ),
        "stoch_k_guidance_min": (
            round(stoch_context["min"], 2)
            if stoch_context["min"] is not None
            else None
        ),
        "stoch_k_guidance_max": (
            round(stoch_context["max"], 2)
            if stoch_context["max"] is not None
            else None
        ),
        "stoch_k_guidance_percentile": (
            round(stoch_context["percentile"], 2)
            if stoch_context["percentile"] is not None
            else None
        ),
        "stoch_k_pct_guidance_max": (
            round(stoch_context["pct_of_max"], 2)
            if stoch_context["pct_of_max"] is not None
            else None
        ),
        "volume_guidance_max": (
            round(volume_context["max"], 2)
            if volume_context["max"] is not None
            else None
        ),
        "volume_guidance_percentile": (
            round(volume_context["percentile"], 2)
            if volume_context["percentile"] is not None
            else None
        ),
        "volume_pct_guidance_max": (
            round(volume_context["pct_of_max"], 2)
            if volume_context["pct_of_max"] is not None
            else None
        ),
    })

    # Preserve existing field names while making their meaning truthful: they
    # now reflect the selected adaptive guidance scope, not merely fetched data.
    output["price_history_high"] = output["price_guidance_high"]
    output["price_pct_history_high"] = output["price_pct_guidance_high"]
    output["new_history_high"] = output["new_guidance_high"]
    return output


def confidence_label(score: int, maximum: int = 10) -> str:
    pct = 0 if maximum <= 0 else max(0, min(100, round(score / maximum * 100)))
    if pct >= 85:
        level = "High"
    elif pct >= 65:
        level = "Moderate-High"
    elif pct >= 45:
        level = "Moderate"
    else:
        level = "Low"
    return f"{level} Setup ({score}/{maximum})"


def end_user_classification(status: str, output_signal: str, setup_type: str | None = None) -> str:
    if status == STATUS_BUY_SIGNAL:
        if "EXTENDED_REVIEW" in str(setup_type or ""):
            return "BUY_EXTENDED_REVIEW"
        return {
            "Buy_Pullback_Oversold_Recovery": "BUY#1",
            "Buy_EMA20_Midrange_Recovery": "BUY#2",
            "Buy_Momentum_Extension": "BUY#3",
            "Buy_Early_Momentum": "BUY#4",
        }.get(output_signal, "BUY")

    return "NO_BUY"


def end_user_reason(status: str, output_signal: str, setup_type: str | None = None) -> str:
    if status == STATUS_BUY_SIGNAL:
        if "EXTENDED_REVIEW" in str(setup_type or ""):
            return "Extreme momentum review"
        return {
            "Buy_Pullback_Oversold_Recovery": "Oversold recovery",
            "Buy_EMA20_Midrange_Recovery": "EMA20 recovery",
            "Buy_Momentum_Extension": "Momentum continuation",
            "Buy_Early_Momentum": "Positive-phase MACD crossover",
        }.get(output_signal, "Buy confirmed")

    return {
        "Ignore_Daily_Trend": "Daily trend not aligned",
        "Ignore_Weekly_Trend": "Weekly trend not aligned",
        "Hold_Buy_Stochastic_Above_Limit": "BUY stochastic limit exceeded",
        "Hold_Buy_Liquidity_Below_Minimum": "U.S. liquidity below minimum",
        "Reject_Exhaustion": "Setup exhausted",
        "Hold_Pullback_Recovery_Volume_Pending": "Pullback volume pending",
        "Hold_EMA20_Recovery_Volume_Pending": "EMA20 volume pending",
        "Hold_Pullback_Stochastic_Pending": "Stochastic pending",
        "Hold_MACD_Momentum_Not_Confirmed": "MACD momentum not confirmed",
        "Hold_MACD_Zero_Gate_Not_Met": "MACD zero gate not met",
        "Hold": "Trend intact",
        "Error_Insufficient_History": "Insufficient history",
        "Error_Insufficient_Weekly_History": "Insufficient weekly history",
        "Error_NullValuesFound": "Indicator null values",
        "Error_Weekly_NullValuesFound": "Weekly indicator null values",
        "Error_NoPriceData": "No price data",
        "Error_Missing_OHLCV_Data": "Missing OHLCV data",
        "Error_InternalError": "Internal error",
    }.get(output_signal, "No buy")


def apply_buy_quality_policies(
    result: dict,
    market_key: str,
    config: dict,
) -> dict:
    """Apply approved listing-liquidity and extreme-extension BUY policies."""
    updated = dict(result)
    is_us_listing = str(market_key or "").upper() == "US"
    minimum_turnover = float(
        config.get(
            "us_min_adv20_turnover",
            DEFAULT_US_MIN_ADV20_TURNOVER,
        )
    )
    turnover = pd.to_numeric(
        updated.get("average_daily_turnover_20"),
        errors="coerce",
    )
    turnover_value = None if pd.isna(turnover) else float(turnover)
    liquidity_floor_passed = (
        None
        if not is_us_listing or turnover_value is None
        else turnover_value >= minimum_turnover
    )

    extension_threshold = float(
        config.get(
            "extreme_extension_review_atr",
            DEFAULT_EXTREME_EXTENSION_REVIEW_ATR,
        )
    )
    distance_atr = pd.to_numeric(
        updated.get("ema50_distance_atr"),
        errors="coerce",
    )
    distance_value = None if pd.isna(distance_atr) else float(distance_atr)
    extreme_extension_review = bool(
        distance_value is not None and distance_value > extension_threshold
    )

    updated["minimum_adv20_turnover"] = (
        minimum_turnover if is_us_listing else None
    )
    updated["liquidity_floor_passed"] = liquidity_floor_passed
    updated["extreme_extension_review_atr"] = extension_threshold
    updated["extreme_extension_review"] = extreme_extension_review

    if updated.get("status") != STATUS_BUY_SIGNAL:
        return updated

    original_buy_signal = str(updated.get("output_signal") or "BUY")
    setup_type = str(updated.get("setup_type") or "BUY")
    details = str(updated.get("message_details") or "").strip()

    if is_us_listing and liquidity_floor_passed is not True:
        updated["status"] = STATUS_HOLD
        updated["output_signal"] = "Hold_Buy_Liquidity_Below_Minimum"
        updated["setup_type"] = f"{setup_type}_LIQUIDITY_FLOOR"
        updated["classification"] = "NO_BUY"
        updated["reason"] = "U.S. liquidity below minimum"
        updated["OUT_MESSAGE"] = "NO_BUY"
        updated["output_message"] = "NO_BUY"
        updated["message"] = "NO_BUY"
        updated["risk_level"] = "Liquidity Below Minimum"
        policy_detail = (
            f"WithheldSignal={original_buy_signal}; "
            f"ADV20Turnover={turnover_value if turnover_value is not None else 'Unavailable'}; "
            f"MinimumADV20Turnover={minimum_turnover:.2f}"
        )
        updated["message_details"] = " | ".join(
            part for part in (details, policy_detail) if part
        )
        return updated

    if extreme_extension_review:
        updated["setup_type"] = f"{setup_type}_EXTENDED_REVIEW"
        updated["classification"] = "BUY_EXTENDED_REVIEW"
        updated["reason"] = "Extreme momentum review"
        updated["OUT_MESSAGE"] = "BUY_EXTENDED_REVIEW"
        updated["output_message"] = "BUY_EXTENDED_REVIEW"
        updated["message"] = "BUY_EXTENDED_REVIEW"
        updated["risk_level"] = "Extreme Extension Review"
        policy_detail = (
            f"ExtendedReview=True; EMA50Distance={distance_value:.3f}ATR; "
            f"ReviewThreshold={extension_threshold:.2f}ATR"
        )
        updated["message_details"] = " | ".join(
            part for part in (details, policy_detail) if part
        )

    return updated


def evaluate_frame(df: pd.DataFrame, ticker_symbol: str, config: dict) -> dict:
    def error_result(message: str, output_signal: str) -> dict:
        out_message = f"ERROR | {message.rstrip('.')}"
        return {
            "ticker": ticker_symbol,
            "status": STATUS_ERROR,
            "output_signal": output_signal,
            "setup_type": "ERROR",
            "OUT_MESSAGE": out_message,
            "output_message": out_message,
            "message": out_message,
            "message_details": f"Error={message}",
            "confidence": "Low Setup (0/10)",
            "risk_level": "Not Applicable",
            "signal_score": 0,
        }

    if df.empty or len(df) < EMA_SLOW_PERIOD:
        return error_result(
            f"Insufficient history (Needs {EMA_SLOW_PERIOD} daily candles).",
            "Error_Insufficient_History",
        )

    frame = df.copy()
    frame.columns = [str(col).lower() for col in frame.columns]
    required_columns = {"open", "high", "low", "close", "volume"}
    if not required_columns.issubset(frame.columns):
        return error_result("Required OHLCV data is missing.", "Error_Missing_OHLCV_Data")
    if frame["close"].isna().all():
        return error_result("No price data available.", "Error_NoPriceData")

    weekly_df = build_weekly_data(
        frame,
        include_incomplete_week=False,
        current_session_incomplete=bool(frame.attrs.get("current_candle_partial", False)),
    )
    if weekly_df.empty or len(weekly_df) < WEEKLY_EMA_SLOW:
        return error_result(
            f"Insufficient weekly history (Needs {WEEKLY_EMA_SLOW} completed weekly candles).",
            "Error_Insufficient_Weekly_History",
        )

    frame["ema_20"] = ta.trend.ema_indicator(frame["close"], window=20)
    frame["ema_50"] = ta.trend.ema_indicator(frame["close"], window=EMA_FAST_PERIOD)
    frame["ema_200"] = ta.trend.ema_indicator(frame["close"], window=EMA_SLOW_PERIOD)
    macd_obj = ta.trend.MACD(
        frame["close"], window_fast=MACD_FAST_PERIOD,
        window_slow=MACD_SLOW_PERIOD, window_sign=MACD_SIGNAL_PERIOD,
    )
    frame["macd"] = macd_obj.macd()
    frame["macd_signal"] = macd_obj.macd_signal()
    frame["macd_hist"] = macd_obj.macd_diff()
    frame["adx"] = ta.trend.adx(frame["high"], frame["low"], frame["close"], window=ADX_PERIOD)
    frame["rsi"] = ta.momentum.rsi(frame["close"], window=RSI_PERIOD)
    frame["atr"] = ta.volatility.average_true_range(frame["high"], frame["low"], frame["close"], window=ATR_PERIOD)
    frame["stoch_k"] = ta.momentum.stoch(frame["high"], frame["low"], frame["close"], window=STOCH_K_PERIOD)
    frame["stoch_d"] = ta.momentum.stoch_signal(
        frame["high"], frame["low"], frame["close"],
        window=STOCH_K_PERIOD, smooth_window=STOCH_D_PERIOD,
    )

    latest = frame.iloc[-1]
    prev = frame.iloc[-2]
    prior = frame.iloc[-3]
    crucial = [
        "ema_20", "ema_50", "ema_200", "macd", "macd_signal", "macd_hist",
        "adx", "rsi", "atr", "stoch_k", "stoch_d",
    ]
    if any(pd.isna(latest[name]) for name in crucial):
        return error_result("Crucial indicators generated null values.", "Error_NullValuesFound")

    weekly_latest = weekly_df.iloc[-1]
    weekly_ema_20 = None if pd.isna(weekly_latest["weekly_ema_20"]) else float(weekly_latest["weekly_ema_20"])
    weekly_ema_50 = None if pd.isna(weekly_latest["weekly_ema_50"]) else float(weekly_latest["weekly_ema_50"])
    weekly_price = None if pd.isna(weekly_latest["close"]) else float(weekly_latest["close"])
    if weekly_ema_20 is None or weekly_ema_50 is None or weekly_price is None:
        return error_result("Weekly indicators generated null values.", "Error_Weekly_NullValuesFound")

    current_volume = volume_avg_20 = None
    if "volume" in frame.columns and len(frame) >= VOLUME_LOOKBACK + 1:
        volume_series = frame["volume"].fillna(0)
        current_volume = float(volume_series.iloc[-1])
        volume_avg_20 = float(volume_series.iloc[-VOLUME_LOOKBACK - 1:-1].mean())

    volume_session_fraction = frame.attrs.get("volume_session_fraction")
    volume_ratio_raw, volume_ratio = calculate_session_paced_volume_ratios(
        current_volume,
        volume_avg_20,
        volume_session_fraction,
    )
    if (
        volume_session_fraction is not None
        and 0 < float(volume_session_fraction) < 1
    ):
        volume_ratio_basis = "SESSION_PACED"
    elif bool(frame.attrs.get("current_candle_partial", False)):
        volume_ratio_basis = "RAW_PARTIAL"
    else:
        volume_ratio_basis = "FULL_SESSION"

    price = float(latest["close"])
    ema20 = float(latest["ema_20"])
    ema50 = float(latest["ema_50"])
    ema200 = float(latest["ema_200"])
    atr = float(latest["atr"])
    distance = price - ema50
    distance_atr = distance / atr if atr > 0 else None
    ema20_gap_atr = (price - ema20) / atr if atr > 0 else None

    macro_trend_ok = price > ema50 > ema200
    weekly_trend_ok = weekly_price > weekly_ema_20 > weekly_ema_50

    macd = float(latest["macd"])
    signal = float(latest["macd_signal"])
    hist = float(latest["macd_hist"])
    hist_prev = float(prev["macd_hist"])
    hist_lookback = max(2, int(config.get("hist_expansion_lookback", 3)))
    hist_values = frame["macd_hist"].dropna().iloc[-hist_lookback:].astype(float).tolist()
    hist3 = frame["macd_hist"].dropna().iloc[-3:].astype(float).tolist()
    hist_expanding_3 = (
        len(hist_values) == hist_lookback
        and is_confirmed_positive_histogram_expansion(hist_values)
    )
    hist_contracting_3 = (
        len(hist_values) == hist_lookback
        and is_sustained_positive_histogram_contraction(hist_values)
    )
    macd_bullish = macd > signal
    macd_above_zero = macd > 0 and signal > 0
    positive_macd_regime = bool(
        macd_bullish
        and macd_above_zero
        and hist > 0
    )
    bull_crossover = is_confirmed_positive_macd_crossover(
        float(prev["macd"]),
        float(prev["macd_signal"]),
        macd,
        signal,
    )
    adx_value = float(latest["adx"])
    adx_name, adx_points = adx_band(adx_value, config)
    rsi_value = float(latest["rsi"])
    stoch_k = float(latest["stoch_k"])
    stoch_d = float(latest["stoch_d"])

    previous_close = float(prev["close"])
    prior_close = float(prior["close"])
    current_day_return_pct = (
        (price / previous_close - 1.0) * 100.0
        if previous_close
        else None
    )
    previous_day_return_pct = (
        (previous_close / prior_close - 1.0) * 100.0
        if prior_close
        else None
    )
    current_day_positive = bool(
        current_day_return_pct is not None and current_day_return_pct > 0
    )
    previous_day_positive = bool(
        previous_day_return_pct is not None and previous_day_return_pct > 0
    )
    price_move_atr = (
        (price - previous_close) / atr
        if atr > 0
        else None
    )

    historical_lookback = max(
        20,
        int(
            config.get(
                "historical_context_lookback",
                HISTORICAL_CONTEXT_LOOKBACK,
            )
        ),
    )
    rsi_history = historical_series_context(
        frame["rsi"],
        rsi_value,
        historical_lookback,
    )
    adx_history = historical_series_context(
        frame["adx"],
        adx_value,
        historical_lookback,
    )
    stoch_history = historical_series_context(
        frame["stoch_k"],
        stoch_k,
        historical_lookback,
    )
    volume_history = historical_series_context(
        frame["volume"].fillna(0),
        current_volume or 0.0,
        historical_lookback,
    )

    prior_52w = frame.iloc[-historical_lookback - 1:-1]
    if prior_52w.empty:
        prior_52w = frame.iloc[:-1]
    price_52w_high = (
        float(prior_52w["high"].max())
        if not prior_52w.empty
        else None
    )
    price_52w_low = (
        float(prior_52w["low"].min())
        if not prior_52w.empty
        else None
    )
    available_prior = frame.iloc[:-1]
    price_history_high = (
        float(available_prior["high"].max())
        if not available_prior.empty
        else None
    )
    price_pct_52w_high = (
        price / price_52w_high * 100.0
        if price_52w_high and price_52w_high > 0
        else None
    )
    price_distance_52w_high_pct = (
        (price / price_52w_high - 1.0) * 100.0
        if price_52w_high and price_52w_high > 0
        else None
    )
    price_pct_history_high = (
        price / price_history_high * 100.0
        if price_history_high and price_history_high > 0
        else None
    )
    new_52w_high = bool(
        price_52w_high is not None
        and float(latest["high"]) > price_52w_high
    )
    new_history_high = bool(
        price_history_high is not None
        and float(latest["high"]) > price_history_high
    )

    volume_history_percentile = volume_history["percentile"]
    current_volume_minimum = float(
        config.get(
            "current_volume_min_ratio",
            DEFAULT_CURRENT_VOLUME_MIN_RATIO,
        )
    )
    volume_floor_passed = bool(
        volume_ratio is not None
        and volume_ratio >= current_volume_minimum
    )
    volume_supportive = has_supportive_volume(
        volume_ratio,
        volume_history_percentile,
        config,
    )
    volume_price_impulse = (
        volume_ratio * price_move_atr
        if volume_ratio is not None and price_move_atr is not None
        else None
    )

    adx_relative_band = relative_confidence_band(adx_history["pct_of_max"])
    adx_relative_points = (
        3
        if adx_history["pct_of_max"] is not None
        and adx_history["pct_of_max"] >= 80
        else 2
        if adx_history["pct_of_max"] is not None
        and adx_history["pct_of_max"] >= 60
        else 1
        if adx_history["pct_of_max"] is not None
        and adx_history["pct_of_max"] >= 40
        else 0
    )

    ema20_max_gap_atr = float(config.get("ema20_max_gap_atr", BALANCED_CONFIG["ema20_max_gap_atr"]))
    ema20_support = bool(
        ema20_gap_atr is not None
        and ema20 > ema50
        and 0 <= ema20_gap_atr <= ema20_max_gap_atr
    )
    stoch_mid_low = float(config.get("stoch_mid_low", BALANCED_CONFIG["stoch_mid_low"]))
    stoch_mid_high = float(config.get("stoch_mid_high", BALANCED_CONFIG["stoch_mid_high"]))
    stoch_mid_crossed_up = bool(
        prev["stoch_k"] <= prev["stoch_d"]
        and latest["stoch_k"] > latest["stoch_d"]
        and stoch_mid_low <= stoch_k <= stoch_mid_high
    )
    valid_shallow_pullback = bool(
        ema20_support
        and stoch_mid_crossed_up
    )

    lookback = max(2, int(config.get("stoch_recent_lookback", STOCH_RECENT_LOOKBACK)))
    stoch_threshold = config.get("stoch_oversold", BALANCED_CONFIG["stoch_oversold"])
    stoch_recovery_ceiling = stoch_threshold + config.get("stoch_recovery_buffer", STOCH_RECOVERY_BUFFER)
    stoch_recently_oversold = bool(frame["stoch_k"].iloc[-lookback:].min() < stoch_threshold)
    stoch_crossed_up = bool(prev["stoch_k"] <= prev["stoch_d"] and latest["stoch_k"] > latest["stoch_d"])
    stoch_recovery_trigger = bool(stoch_recently_oversold and stoch_crossed_up and stoch_k <= stoch_recovery_ceiling)

    volume_confirmed = volume_ratio is not None and volume_ratio >= config.get("volume_mult", BALANCED_CONFIG["volume_mult"])
    continuation_volume_ok = volume_supportive
    safe_atr = config.get("atr_safe_mult", BALANCED_CONFIG["atr_safe_mult"])
    ext_atr = config.get("atr_ext_mult", BALANCED_CONFIG["atr_ext_mult"])
    price_in_safe_buy_zone = distance_atr is not None and distance_atr <= safe_atr
    price_hyper_extended = distance_atr is not None and distance_atr > ext_atr

    average_daily_turnover_20 = (
        volume_avg_20 * price
        if volume_avg_20 is not None
        else None
    )

    if distance_atr is None:
        extension_state = "Unknown"
        extension_risk = 1
    elif distance_atr <= safe_atr:
        extension_state = "Controlled"
        extension_risk = 0
    elif distance_atr <= ext_atr:
        extension_state = "Moderately Extended"
        extension_risk = 1
    else:
        extension_state = "Highly Extended"
        extension_risk = 2

    momentum_continuation = bool(
        macro_trend_ok and weekly_trend_ok
        and positive_macd_regime
        and hist_expanding_3
        and current_day_positive
        and continuation_volume_ok
    )
    early_momentum = bool(
        macro_trend_ok and weekly_trend_ok
        and bull_crossover
        and hist > 0
        and stoch_k > stoch_d
        and current_day_positive
        and continuation_volume_ok
    )
    established_trend = bool(
        positive_macd_regime
    )

    metrics = {
        "ticker": ticker_symbol,
        "price": round(price, 2), "ema_20": round(ema20, 2), "ema_50": round(ema50, 2), "ema_200": round(ema200, 2),
        "current_day_return_pct": (
            round(current_day_return_pct, 3)
            if current_day_return_pct is not None
            else None
        ),
        "current_day_positive": current_day_positive,
        "previous_day_return_pct": (
            round(previous_day_return_pct, 3)
            if previous_day_return_pct is not None
            else None
        ),
        "previous_day_positive": previous_day_positive,
        "price_move_atr": (
            round(price_move_atr, 3)
            if price_move_atr is not None
            else None
        ),
        "price_52w_high": (
            round(price_52w_high, 2)
            if price_52w_high is not None
            else None
        ),
        "price_52w_low": (
            round(price_52w_low, 2)
            if price_52w_low is not None
            else None
        ),
        "price_pct_52w_high": (
            round(price_pct_52w_high, 2)
            if price_pct_52w_high is not None
            else None
        ),
        "price_distance_52w_high_pct": (
            round(price_distance_52w_high_pct, 2)
            if price_distance_52w_high_pct is not None
            else None
        ),
        "new_52w_high": new_52w_high,
        "price_history_high": (
            round(price_history_high, 2)
            if price_history_high is not None
            else None
        ),
        "price_pct_history_high": (
            round(price_pct_history_high, 2)
            if price_pct_history_high is not None
            else None
        ),
        "new_history_high": new_history_high,
        "ema20_gap_atr": round(ema20_gap_atr, 3) if ema20_gap_atr is not None else None,
        "ema50_distance_atr": round(distance_atr, 3) if distance_atr is not None else None,
        "macd_params": f"{MACD_FAST_PERIOD},{MACD_SLOW_PERIOD},{MACD_SIGNAL_PERIOD}",
        "macd": round(macd, 3), "macd_signal": round(signal, 3),
        "macd_hist": round(hist, 3), "macd_hist_prev": round(hist_prev, 3),
        "macd_hist_3bar": ",".join(f"{x:.3f}" for x in hist3),
        "macd_state": (
            "BULL_CROSS" if bull_crossover
            else "BULL_EXPANDING_3BAR" if positive_macd_regime and hist_expanding_3
            else "BULL_COOLING_3BAR" if positive_macd_regime and hist_contracting_3
            else "BULL_POSITIVE" if positive_macd_regime
            else "POSITIVE_PHASE_UNCONFIRMED" if macd > 0 and signal > 0
            else "MACD_ZERO_GATE_NOT_MET"
        ),
        "adx": round(adx_value, 2), "adx_band": adx_name,
        "adx_1y_max": (
            round(adx_history["max"], 2)
            if adx_history["max"] is not None
            else None
        ),
        "adx_1y_percentile": (
            round(adx_history["percentile"], 2)
            if adx_history["percentile"] is not None
            else None
        ),
        "adx_pct_1y_max": (
            round(adx_history["pct_of_max"], 2)
            if adx_history["pct_of_max"] is not None
            else None
        ),
        "adx_relative_confidence": adx_relative_band,
        "rsi": round(rsi_value, 2),
        "rsi_1y_min": (
            round(rsi_history["min"], 2)
            if rsi_history["min"] is not None
            else None
        ),
        "rsi_1y_max": (
            round(rsi_history["max"], 2)
            if rsi_history["max"] is not None
            else None
        ),
        "rsi_1y_percentile": (
            round(rsi_history["percentile"], 2)
            if rsi_history["percentile"] is not None
            else None
        ),
        "rsi_pct_1y_max": (
            round(rsi_history["pct_of_max"], 2)
            if rsi_history["pct_of_max"] is not None
            else None
        ),
        "atr": round(atr, 3),
        "stoch_k": round(stoch_k, 2), "stoch_d": round(stoch_d, 2),
        "stoch_k_1y_min": (
            round(stoch_history["min"], 2)
            if stoch_history["min"] is not None
            else None
        ),
        "stoch_k_1y_max": (
            round(stoch_history["max"], 2)
            if stoch_history["max"] is not None
            else None
        ),
        "stoch_k_1y_percentile": (
            round(stoch_history["percentile"], 2)
            if stoch_history["percentile"] is not None
            else None
        ),
        "stoch_k_pct_1y_max": (
            round(stoch_history["pct_of_max"], 2)
            if stoch_history["pct_of_max"] is not None
            else None
        ),
        "volume": round(current_volume, 2) if current_volume is not None else None,
        "volume_avg_20": round(volume_avg_20, 2) if volume_avg_20 is not None else None,
        "average_daily_turnover_20": (
            round(average_daily_turnover_20, 2)
            if average_daily_turnover_20 is not None
            else None
        ),
        "volume_ratio_raw": (
            round(volume_ratio_raw, 3)
            if volume_ratio_raw is not None
            else None
        ),
        "volume_session_fraction": (
            round(float(volume_session_fraction), 4)
            if volume_session_fraction is not None
            else None
        ),
        "volume_ratio_basis": volume_ratio_basis,
        "volume_ratio": round(volume_ratio, 3) if volume_ratio is not None else None,
        "minimum_volume_ratio": current_volume_minimum,
        "volume_floor_passed": volume_floor_passed,
        "volume_1y_percentile": (
            round(volume_history_percentile, 2)
            if volume_history_percentile is not None
            else None
        ),
        "volume_pct_1y_max": (
            round(volume_history["pct_of_max"], 2)
            if volume_history["pct_of_max"] is not None
            else None
        ),
        "volume_supportive": volume_supportive,
        "volume_price_impulse": (
            round(volume_price_impulse, 3)
            if volume_price_impulse is not None
            else None
        ),
        "historical_context_sessions": max(
            rsi_history["count"],
            adx_history["count"],
            stoch_history["count"],
            volume_history["count"],
        ),
        "weekly_ema_20": round(weekly_ema_20, 2) if weekly_ema_20 is not None else None,
        "weekly_ema_50": round(weekly_ema_50, 2) if weekly_ema_50 is not None else None,
        "weekly_price": round(weekly_price, 2) if weekly_price is not None else None,
        "extension_state": extension_state,
        "prior_strength_override": False,
        "effective_buy_stoch_max": None,
        "OUT_MESSAGE": None, "output_signal": None, "setup_type": "NONE",
    }

    detail_parts = [
        f"Trend={'Daily bullish' if macro_trend_ok else 'Daily trend failed'}",
        f"Weekly={'Aligned' if weekly_trend_ok else 'Not aligned'}",
        f"MACD={metrics['macd_state']} ({macd:.3f}/{signal:.3f}; Hist3={metrics['macd_hist_3bar']})",
        (
            f"ADX={adx_value:.2f} ({adx_name}; "
            f"{adx_history['pct_of_max']:.1f}% of 1Y max; {adx_relative_band})"
            if adx_history["pct_of_max"] is not None
            else f"ADX={adx_value:.2f} ({adx_name}; history unavailable)"
        ),
        (
            f"RSI={rsi_value:.2f} "
            f"(1YPercentile={rsi_history['percentile']:.1f})"
            if rsi_history["percentile"] is not None
            else f"RSI={rsi_value:.2f}"
        ),
        (
            f"Stochastic={stoch_k:.2f}/{stoch_d:.2f} "
            f"(K1YPercentile={stoch_history['percentile']:.1f}; "
            f"MidCross={stoch_mid_crossed_up})"
            if stoch_history["percentile"] is not None
            else f"Stochastic={stoch_k:.2f}/{stoch_d:.2f} "
            f"(MidCross={stoch_mid_crossed_up})"
        ),
        (
            f"PreviousDay={previous_day_return_pct:.2f}% "
            f"(Positive={previous_day_positive})"
            if previous_day_return_pct is not None
            else "PreviousDay=Unavailable"
        ),
        (
            f"CurrentResponse={current_day_return_pct:.2f}%/"
            f"{price_move_atr:.2f}ATR"
            if current_day_return_pct is not None and price_move_atr is not None
            else "CurrentResponse=Unavailable"
        ),
        f"ADV20={volume_avg_20:,.0f}" if volume_avg_20 is not None else "ADV20=Unavailable",
        f"EMA20Support={ema20_support} (Gap={ema20_gap_atr:.2f} ATR)" if ema20_gap_atr is not None else "EMA20Support=Unavailable",
        f"EMA50Distance={distance_atr:.2f} ATR ({extension_state})" if distance_atr is not None else "EMA50Distance=Unavailable",
        (
            f"VolumeRatio={volume_ratio:.2f}x "
            f"(Raw={volume_ratio_raw:.2f}x; "
            f"Basis={volume_ratio_basis}; "
            f"SessionElapsed={float(volume_session_fraction):.1%}; "
            f"1YPercentile={volume_history_percentile:.1f}; "
            f"Minimum={current_volume_minimum:.2f}x; "
            f"FloorPassed={volume_floor_passed}; Supportive={volume_supportive})"
            if (
                volume_ratio is not None
                and volume_ratio_raw is not None
                and volume_session_fraction is not None
                and volume_history_percentile is not None
            )
            else (
                f"VolumeRatio={volume_ratio:.2f}x "
                f"(Raw={volume_ratio_raw:.2f}x; Basis={volume_ratio_basis}; "
                f"SessionElapsed={float(volume_session_fraction):.1%}; "
                f"Minimum={current_volume_minimum:.2f}x; "
                f"FloorPassed={volume_floor_passed}; Supportive={volume_supportive})"
            )
            if (
                volume_ratio is not None
                and volume_ratio_raw is not None
                and volume_session_fraction is not None
            )
            else (
                f"VolumeRatio={volume_ratio:.2f}x "
                f"(1YPercentile={volume_history_percentile:.1f}; "
                f"Minimum={current_volume_minimum:.2f}x; "
                f"FloorPassed={volume_floor_passed}; Supportive={volume_supportive})"
            )
            if volume_ratio is not None and volume_history_percentile is not None
            else f"VolumeRatio={volume_ratio:.2f}x"
            if volume_ratio is not None
            else "VolumeRatio=Unavailable"
        ),
        (
            f"Price52W={price_pct_52w_high:.2f}% of prior high "
            f"(NewHigh={new_52w_high})"
            if price_pct_52w_high is not None
            else "Price52W=Unavailable"
        ),
    ]

    score = 0
    score += 2 if macro_trend_ok else 0
    score += 2 if weekly_trend_ok else 0
    if macro_trend_ok and weekly_trend_ok and positive_macd_regime:
        score += 2
        score += 2 if hist_expanding_3 else 1
        score += adx_relative_points
        score += 1 if continuation_volume_ok else 0
        score += 1 if current_day_positive and volume_supportive else 0

        if valid_shallow_pullback:
            score += 1
        
    score -= extension_risk
    score = max(0, min(10, score))

    if not macro_trend_ok:
        status, output_signal, setup_type = STATUS_IGNORE, "Ignore_Daily_Trend", "NONE"
        out_message = "Daily trend not aligned"
        risk_level = "Trend Not Qualified"
    elif not weekly_trend_ok:
        status, output_signal, setup_type = STATUS_IGNORE, "Ignore_Weekly_Trend", "NONE"
        out_message = "Weekly trend not aligned"
        risk_level = "Weekly Trend Not Qualified"
    else:
        historical_risk_context = []
        if price_hyper_extended:
            historical_risk_context.append(
                "price is extended from EMA50"
            )
        if (
            rsi_history["percentile"] is not None
            and rsi_history["percentile"] >= 90
        ):
            historical_risk_context.append(
                "RSI is in its own top historical decile"
            )
        if (
            adx_history["pct_of_max"] is not None
            and adx_history["pct_of_max"] >= 80
        ):
            historical_risk_context.append(
                "ADX is near its own historical maximum"
            )
        if historical_risk_context:
            detail_parts.append(
                "HistoricalContext=" + "; ".join(historical_risk_context)
            )

        if established_trend and price_in_safe_buy_zone and stoch_recovery_trigger:
            setup_type = "PULLBACK_OVERSOLD_RECOVERY"
            if volume_confirmed:
                status, output_signal = STATUS_BUY_SIGNAL, "Buy_Pullback_Oversold_Recovery"
                out_message = "Oversold pullback confirmed"
                risk_level = "Low-Moderate"
                score = min(10, score + 2)
            else:
                status, output_signal = STATUS_HOLD, "Hold_Pullback_Recovery_Volume_Pending"
                out_message = "Pullback recovery; volume pending"
                risk_level = "Confirmation Pending"
        elif established_trend and price_in_safe_buy_zone and valid_shallow_pullback:
            setup_type = "PULLBACK_EMA20_MIDRANGE_RECOVERY"
            if volume_confirmed:
                status, output_signal = STATUS_BUY_SIGNAL, "Buy_EMA20_Midrange_Recovery"
                out_message = "EMA20 recovery confirmed"
                risk_level = "Low-Moderate"
                score = min(10, score + 2)
            else:
                status, output_signal = STATUS_HOLD, "Hold_EMA20_Recovery_Volume_Pending"
                out_message = "EMA20 recovery; volume pending"
                risk_level = "Confirmation Pending"
        elif early_momentum:
            status, output_signal = STATUS_BUY_SIGNAL, "Buy_Early_Momentum"
            setup_type = "EARLY_MOMENTUM_POSITIVE_PHASE"
            out_message = "Volume-supported early momentum confirmed"
            risk_level = (
                "Elevated Historical Momentum"
                if (
                    rsi_history["percentile"] is not None
                    and rsi_history["percentile"] >= 90
                )
                else "Moderate"
            )
            score = min(10, score + 1)
        elif momentum_continuation:
            status, output_signal = STATUS_BUY_SIGNAL, "Buy_Momentum_Extension"
            setup_type = "MOMENTUM_CONTINUATION_EXTENDED" if extension_risk else "MOMENTUM_CONTINUATION"
            out_message = "Momentum continuation confirmed"
            risk_level = "Moderate" if (adx_name == "Emerging" or extension_risk == 1) else ("Elevated" if extension_risk == 2 else "Controlled")
            score = min(10, score + 1)
        elif established_trend and stoch_recently_oversold and not stoch_crossed_up:
            status, output_signal, setup_type = STATUS_HOLD, "Hold_Pullback_Stochastic_Pending", "PULLBACK_FORMING"
            out_message = "Stochastic reversal pending"
            risk_level = "Trigger Pending"
        elif positive_macd_regime and hist_contracting_3:
            status, output_signal, setup_type = STATUS_HOLD, "Hold", "MOMENTUM_COOLING"
            out_message = "Momentum cooling"
            risk_level = "Momentum Cooling"
        elif established_trend:
            status, output_signal, setup_type = STATUS_HOLD, "Hold", "ESTABLISHED_TREND"
            out_message = "Trend intact; no entry"
            risk_level = "No Fresh Entry"
        elif macd > 0 and signal > 0:
            status, output_signal, setup_type = (
                STATUS_HOLD,
                "Hold_MACD_Momentum_Not_Confirmed",
                "POSITIVE_TREND_MACD_UNCONFIRMED",
            )
            out_message = "Positive trend; MACD momentum not confirmed"
            risk_level = "Momentum Not Confirmed"
        else:
            status, output_signal, setup_type = (
                STATUS_HOLD,
                "Hold_MACD_Zero_Gate_Not_Met",
                "TREND_MACD_ZERO_GATE_NOT_MET",
            )
            out_message = "Positive price trend; MACD zero gate not met"
            risk_level = "MACD Regime Not Qualified"

    base_buy_stoch_max = max(
        0.0, float(config.get("buy_stoch_max", DEFAULT_BUY_STOCH_MAX))
    )
    effective_buy_stoch_max = base_buy_stoch_max
    prior_strength_override = False
    if (
        status == STATUS_BUY_SIGNAL
        and previous_day_positive
        and base_buy_stoch_max > 0
    ):
        if output_signal == "Buy_Early_Momentum":
            effective_buy_stoch_max = max(
                base_buy_stoch_max,
                float(config.get("prior_positive_early_stoch_max", 90.0)),
            )
        elif output_signal == "Buy_Momentum_Extension":
            effective_buy_stoch_max = max(
                base_buy_stoch_max,
                float(
                    config.get(
                        "prior_positive_continuation_stoch_max",
                        100.0,
                    )
                ),
            )
        prior_strength_override = effective_buy_stoch_max > base_buy_stoch_max

    metrics["prior_strength_override"] = prior_strength_override
    metrics["effective_buy_stoch_max"] = (
        round(effective_buy_stoch_max, 2)
        if effective_buy_stoch_max > 0
        else None
    )
    if prior_strength_override:
        detail_parts.append(
            "PriorStrengthOverride=True; "
            f"BaseStochLimit={base_buy_stoch_max:.2f}; "
            f"EffectiveStochLimit={effective_buy_stoch_max:.2f}"
        )

    if (
        status == STATUS_BUY_SIGNAL
        and effective_buy_stoch_max > 0
        and (
            stoch_k > effective_buy_stoch_max
            or stoch_d > effective_buy_stoch_max
        )
    ):
        original_buy_signal = output_signal
        status = STATUS_HOLD
        output_signal = "Hold_Buy_Stochastic_Above_Limit"
        setup_type = f"{setup_type}_STOCH_LIMIT"
        out_message = "BUY setup withheld; stochastic above limit"
        risk_level = "Stochastic Above BUY Limit"
        detail_parts.append(
            f"WithheldSignal={original_buy_signal}; "
            f"BuyStochLimit={effective_buy_stoch_max:.2f}"
        )

    classification = end_user_classification(status, output_signal, setup_type)
    reason = end_user_reason(status, output_signal, setup_type)
    out_message = classification

    detail_parts.append(f"Risk={risk_level}")
    detail_parts.append(f"Signal={output_signal}")
    metrics.update({
        "status": status,
        "classification": classification,
        "output_signal": output_signal,
        "setup_type": setup_type,
        "OUT_MESSAGE": out_message,
        "output_message": out_message,
        "message": out_message,
        "reason": reason,
        "message_details": " | ".join(detail_parts),
        "confidence": confidence_label(score),
        "risk_level": risk_level,
        "signal_score": score,
    })
    return metrics


def evaluate_stock_momentum(
    ticker_symbol: str,
    config: dict | None = None,
    history_years: int = 5,
    as_of_date: str | None = None,
    live_candle_mode: str = "auto",
    company_name: str | None = None,
    historical_guidance_scope: str = "MAX",
) -> dict:
    ticker_symbol = normalize_ticker_symbol(ticker_symbol)
    exchange = resolve_market(ticker_symbol)
    supplied_company_name = str(company_name or "").strip()
    config = config or get_config("balanced")
    result_template = {
        "ticker": ticker_symbol,
        "company_name": supplied_company_name or ticker_symbol,
        "currency": None,
        "status": STATUS_ERROR,
        "output_signal": "Error_InternalError",
        "classification": "",
        "reason": "Internal error",
        "OUT_MESSAGE": "ERROR | Internal scanner error",
        "message": "ERROR | Internal scanner error",
        "output_message": "ERROR | Internal scanner error",
        "message_details": "",
        "confidence": "Low Setup (0/10)",
        "risk_level": "Not Applicable",
        "summary_message": "",
        "price": None,
        "current_day_return_pct": None,
        "current_day_positive": None,
        "previous_day_return_pct": None,
        "previous_day_positive": None,
        "price_move_atr": None,
        "price_52w_high": None,
        "price_52w_low": None,
        "price_pct_52w_high": None,
        "price_distance_52w_high_pct": None,
        "new_52w_high": None,
        "price_history_high": None,
        "price_pct_history_high": None,
        "new_history_high": None,
        "ema_20": None,
        "ema_50": None,
        "ema_200": None,
        "ema20_gap_atr": None,
        "macd": None,
        "macd_signal": None,
        "macd_hist": None,
        "macd_hist_prev": None,
        "macd_hist_3bar": None,
        "macd_params": f"{MACD_FAST_PERIOD},{MACD_SLOW_PERIOD},{MACD_SIGNAL_PERIOD}",
        "macd_state": None,
        "setup_type": None,
        "extension_state": None,
        "volume_ratio_raw": None,
        "volume_session_fraction": None,
        "volume_ratio_basis": None,
        "volume_ratio": None,
        "minimum_volume_ratio": config.get(
            "current_volume_min_ratio",
            DEFAULT_CURRENT_VOLUME_MIN_RATIO,
        ),
        "volume_floor_passed": None,
        "ema50_distance_atr": None,
        "adx": None,
        "adx_band": None,
        "adx_1y_max": None,
        "adx_1y_percentile": None,
        "adx_pct_1y_max": None,
        "adx_relative_confidence": None,
        "rsi": None,
        "rsi_1y_min": None,
        "rsi_1y_max": None,
        "rsi_1y_percentile": None,
        "rsi_pct_1y_max": None,
        "atr": None,
        "stoch_k": None,
        "stoch_d": None,
        "stoch_k_1y_min": None,
        "stoch_k_1y_max": None,
        "stoch_k_1y_percentile": None,
        "stoch_k_pct_1y_max": None,
        "as_of_date": as_of_date,
        "volume": None,
        "volume_avg_20": None,
        "average_daily_turnover_20": None,
        "minimum_adv20_turnover": None,
        "liquidity_floor_passed": None,
        "extreme_extension_review_atr": config.get(
            "extreme_extension_review_atr",
            DEFAULT_EXTREME_EXTENSION_REVIEW_ATR,
        ),
        "extreme_extension_review": None,
        "volume_1y_percentile": None,
        "volume_pct_1y_max": None,
        "volume_supportive": None,
        "volume_price_impulse": None,
        "historical_context_sessions": None,
        "historical_guidance_requested_scope": historical_guidance_scope,
        "historical_guidance_scope": historical_guidance_scope,
        "historical_guidance_sessions": None,
        "price_guidance_high": None,
        "price_guidance_low": None,
        "price_pct_guidance_high": None,
        "price_distance_guidance_high_pct": None,
        "new_guidance_high": None,
        "rsi_guidance_min": None,
        "rsi_guidance_max": None,
        "rsi_guidance_percentile": None,
        "rsi_pct_guidance_max": None,
        "adx_guidance_max": None,
        "adx_guidance_percentile": None,
        "adx_pct_guidance_max": None,
        "adx_guidance_confidence": None,
        "stoch_k_guidance_min": None,
        "stoch_k_guidance_max": None,
        "stoch_k_guidance_percentile": None,
        "stoch_k_pct_guidance_max": None,
        "volume_guidance_max": None,
        "volume_guidance_percentile": None,
        "volume_pct_guidance_max": None,
        "prior_strength_override": None,
        "effective_buy_stoch_max": None,
        "weekly_ema_20": None,
        "weekly_ema_50": None,
        "weekly_price": None,
        "signal_score": 0,
        "exchange": exchange,
        "market_phase": None,
        "data_mode": None,
        "market_time_local": None,
        "market_time_et": None,
        "session_date": as_of_date,
        "candle_state": "HISTORICAL_COMPLETED" if as_of_date else None,
        "data_note": None,
    }

    def set_error(message: str, output_signal: str) -> dict:
        clean_message = str(message).strip().rstrip(".")
        out_message = f"ERROR | {clean_message}"
        result_template.update({
            "status": STATUS_ERROR,
            "classification": "",
            "reason": end_user_reason(STATUS_ERROR, output_signal),
            "output_signal": output_signal,
            "OUT_MESSAGE": out_message,
            "message": out_message,
            "output_message": out_message,
            "message_details": f"Error={clean_message}",
            "confidence": "Low Setup (0/10)",
            "risk_level": "Not Applicable",
            "signal_score": 0,
        })
        return result_template

    try:
        ticker_data = yf.Ticker(ticker_symbol)
        history_period = f"{max(1, int(history_years))}y"
        df = fetch_daily_history_cached(
            ticker_data,
            ticker_symbol,
            history_period,
        )
        requested_guidance_scope = str(
            historical_guidance_scope or "MAX"
        ).upper()
        actual_guidance_scope = requested_guidance_scope
        guidance_df = df.copy()

        guidance_period = (
            "max"
            if requested_guidance_scope == "MAX"
            else "5y"
            if requested_guidance_scope == "5Y"
            else None
        )
        if (
            guidance_period is not None
            and guidance_period.lower() != history_period.lower()
        ):
            try:
                requested_guidance_df = fetch_daily_history_cached(
                    ticker_data,
                    ticker_symbol,
                    guidance_period,
                )
                if not requested_guidance_df.empty:
                    guidance_df = requested_guidance_df
                else:
                    actual_guidance_scope = f"{history_period.upper()}_FALLBACK"
            except Exception:
                actual_guidance_scope = f"{history_period.upper()}_FALLBACK"

        metadata = {}
        try:
            metadata = ticker_data.get_history_metadata() or {}
        except Exception:
            metadata = {}
        exchange = resolve_market(ticker_symbol, metadata=metadata)
        listing_currency = str(metadata.get("currency") or "").strip().upper()
        if not supplied_company_name:
            result_template["company_name"] = (
                str(metadata.get("longName") or metadata.get("shortName") or ticker_symbol).strip()
            )
        result_template["exchange"] = exchange
        result_template["currency"] = listing_currency or None

        if df.empty or len(df) < EMA_SLOW_PERIOD:
            return set_error(
                f"Insufficient history; needs {EMA_SLOW_PERIOD} daily candles",
                "Error_Insufficient_History",
            )

        df.columns = [col.lower() for col in df.columns]
        full_daily_index = pd.DatetimeIndex(df.index)
        next_daily_after_as_of = None

        if as_of_date:
            df = filter_to_as_of_date(df, as_of_date)
            if df.empty or len(df) < EMA_SLOW_PERIOD:
                return set_error(
                    f"Insufficient history through {as_of_date}; needs {EMA_SLOW_PERIOD} daily candles",
                    "Error_Insufficient_History",
                )
            future_daily_rows = full_daily_index[full_daily_index > df.index[-1]]
            if len(future_daily_rows):
                next_daily_after_as_of = pd.Timestamp(future_daily_rows[0])

        market_context = {
            "market": exchange,
            "phase": "HISTORICAL",
            "effective_mode": "completed",
            "market_time_local": None,
            "market_time_et": None,
            "session_date": as_of_date,
            "candle_state": "HISTORICAL_COMPLETED",
            "reason": "Historical as-of-date evaluation uses completed candles.",
        }

        if as_of_date is None:
            market_context = get_market_context(ticker_symbol, metadata=metadata)
            requested_mode = (live_candle_mode or "auto").lower()
            if requested_mode not in {"auto", "completed", "intraday"}:
                requested_mode = "auto"
            effective_mode = market_context["effective_mode"] if requested_mode == "auto" else requested_mode
            if requested_mode != "auto":
                market_context["reason"] += f" Manual candle-mode override requested: {requested_mode}."
            if market_context["phase"] == "CLOSED" and effective_mode != "completed":
                effective_mode = "completed"
                market_context["reason"] += " Local exchange is closed; forcing the latest completed daily candle."

            if effective_mode == "intraday":
                df = drop_incomplete_daily_row(df, market_context)
                try:
                    minute_df = ticker_data.history(
                        period="1d",
                        interval="1m",
                        prepost=bool(market_context.get("_allow_extended_hours", False)),
                        auto_adjust=True,
                    )
                    session_minute_df = filter_intraday_to_session(minute_df, market_context)
                    if not session_minute_df.empty:
                        candle_partial = market_context["phase"] in {"PREMARKET", "REGULAR"}
                        df = merge_intraday_session_candle(
                            df,
                            session_minute_df,
                            market_context,
                            current_candle_partial=candle_partial,
                        )
                        if market_context["phase"] == "PREMARKET":
                            market_context["candle_state"] = "EXTENDED_PREVIEW"
                        elif candle_partial:
                            market_context["candle_state"] = "CURRENT_PARTIAL"
                        else:
                            market_context["candle_state"] = "CURRENT_COMPLETED"
                        last_bar = pd.Timestamp(session_minute_df.index[-1]).isoformat()
                        market_context["reason"] += f" Latest included minute bar: {last_bar}."
                    else:
                        market_context["reason"] += " No current-session minute bars were available; fell back to the latest completed daily candle."
                        effective_mode = "completed"
                        market_context["candle_state"] = "LAST_COMPLETED"
                except Exception as exc:
                    market_context["reason"] += f" Minute-data rebuild failed ({exc}); fell back to completed daily candles."
                    effective_mode = "completed"
                    market_context["candle_state"] = "LAST_COMPLETED"
            else:
                if market_context["phase"] in {"PREMARKET", "REGULAR"}:
                    df = drop_incomplete_daily_row(df, market_context)
                    market_context["candle_state"] = "LAST_COMPLETED"
                else:
                    if not has_complete_session_daily_row(df, market_context):
                        df = drop_trailing_incomplete_daily_row(df)
                    can_rebuild_closed_session = (
                        market_context["phase"] in {"POSTMARKET", "CLOSED"}
                        and not market_context.get("_calendar_closed", False)
                        and not has_session_daily_row(df, market_context)
                    )
                    if can_rebuild_closed_session:
                        try:
                            minute_df = ticker_data.history(
                                period="1d",
                                interval="1m",
                                prepost=bool(market_context.get("_allow_extended_hours", False)),
                                auto_adjust=True,
                            )
                            session_minute_df = filter_intraday_to_session(minute_df, market_context)
                            if not session_minute_df.empty:
                                df = merge_intraday_session_candle(
                                    df,
                                    session_minute_df,
                                    market_context,
                                    current_candle_partial=False,
                                )
                                market_context["candle_state"] = "CURRENT_COMPLETED"
                                market_context["reason"] += " The completed regular-session candle was reconstructed from minute bars because the daily feed had not published it yet."
                            else:
                                market_context["candle_state"] = "LAST_COMPLETED"
                                market_context["reason"] += " Today's daily candle was not yet published and minute reconstruction was unavailable; using the latest completed candle."
                        except Exception as exc:
                            market_context["candle_state"] = "LAST_COMPLETED"
                            market_context["reason"] += f" Completed-candle reconstruction failed ({exc}); using the latest completed daily candle."
                    else:
                        market_context["candle_state"] = (
                            "CURRENT_COMPLETED"
                            if has_session_daily_row(df, market_context)
                            else "LAST_COMPLETED"
                        )

            market_context["effective_mode"] = effective_mode

        session_date = pd.Timestamp(market_context["session_date"])
        if market_context["phase"] == "HISTORICAL":
            last_daily_date = pd.Timestamp(df.index[-1]).date()
            week_end_date = last_daily_date + pd.Timedelta(
                days=(4 - last_daily_date.weekday()) % 7
            )
            weekly_period_complete = bool(
                last_daily_date == week_end_date
                or (
                    next_daily_after_as_of is not None
                    and next_daily_after_as_of.date() > week_end_date
                )
                or (
                    next_daily_after_as_of is None
                    and session_date.date() >= week_end_date
                )
            )
        else:
            weekly_period_complete = bool(
                session_date.weekday() == 4
                and (
                    market_context["candle_state"] == "CURRENT_COMPLETED"
                    or market_context.get("_calendar_closed", False)
                )
            )
        df.attrs["weekly_period_complete"] = weekly_period_complete
        df.attrs["currency"] = listing_currency or None

        evaluated = evaluate_frame(df, ticker_symbol, config)
        result = {**result_template, **evaluated}

        if result.get("status") != STATUS_ERROR:
            try:
                guidance_values = calculate_historical_guidance(
                    guidance_df=guidance_df,
                    current_frame=df,
                    current_metrics=result,
                    guidance_scope=actual_guidance_scope,
                    requested_scope=requested_guidance_scope,
                )
                result.update(guidance_values)
                guidance_sessions = int(
                    result.get("historical_guidance_sessions") or 0
                )
                if guidance_sessions:
                    result["message_details"] = (
                        f"{result.get('message_details', '')} | "
                        f"HistoricalGuidance="
                        f"{result.get('historical_guidance_scope')}/"
                        f"{guidance_sessions} sessions; "
                        f"PriceHigh={result.get('price_guidance_high')}; "
                        f"RSIMax={result.get('rsi_guidance_max')}; "
                        f"ADXMax={result.get('adx_guidance_max')}; "
                        f"StochKMax={result.get('stoch_k_guidance_max')}; "
                        f"VolumePercentile="
                        f"{result.get('volume_guidance_percentile')}"
                    ).strip(" |")
            except Exception as guidance_exc:
                result["historical_guidance_scope"] = (
                    f"{actual_guidance_scope}_UNAVAILABLE"
                )
                result["historical_guidance_sessions"] = 0
                result["message_details"] = (
                    f"{result.get('message_details', '')} | "
                    f"HistoricalGuidanceUnavailable={guidance_exc}"
                ).strip(" |")

        result = apply_buy_quality_policies(
            result,
            _fallback_market_key(ticker_symbol),
            config,
        )
        result["summary_message"] = ""
        result["as_of_date"] = as_of_date
        result["exchange"] = market_context["market"]
        result["classification"] = result.get("classification") or end_user_classification(result.get("status"), result.get("output_signal"), result.get("setup_type"))
        result["reason"] = result.get("reason") or end_user_reason(result.get("status"), result.get("output_signal"), result.get("setup_type"))
        result["market_phase"] = market_context["phase"]
        result["data_mode"] = market_context["effective_mode"]
        result["market_time_local"] = market_context["market_time_local"]
        result["market_time_et"] = market_context["market_time_et"]
        result["session_date"] = (
            included_session_date(df) or market_context["session_date"]
        )
        result["candle_state"] = market_context["candle_state"]
        result["data_note"] = market_context["reason"]
        return result

    except Exception as e:
        return set_error(f"Internal scanner error: {str(e)}", "Error_InternalError")


def run_backtest(
    watchlist: list,
    config: dict,
    output_path: str,
    holding_period: int = 5,
    history_years: int = 3,
) -> tuple[pd.DataFrame, dict]:
    result_columns = [
        "ticker", "signal_date", "signal_close", "entry_date", "entry_price",
        "exit_date", "exit_price", "return_pct", "signal_score",
        "output_signal", "setup_type",
    ]
    results = []
    history_period = f"{max(1, int(history_years))}y"
    holding_period = max(1, int(holding_period))
    for raw_ticker in watchlist:
        ticker = normalize_ticker_symbol(raw_ticker)
        try:
            ticker_data = yf.Ticker(ticker)
            df = ticker_data.history(
                period=history_period,
                interval="1d",
                prepost=False,
                auto_adjust=True,
            )
            if df.empty or len(df) < EMA_SLOW_PERIOD + holding_period:
                continue
            df.columns = [col.lower() for col in df.columns]
            idx = EMA_SLOW_PERIOD
            while idx < len(df) - holding_period:
                history = df.iloc[:idx + 1].copy()
                last_daily_date = pd.Timestamp(history.index[-1]).date()
                week_end_date = last_daily_date + pd.Timedelta(
                    days=(4 - last_daily_date.weekday()) % 7
                )
                next_daily_date = pd.Timestamp(df.index[idx + 1]).date()
                history.attrs["weekly_period_complete"] = (
                    next_daily_date > week_end_date
                )
                signal = apply_buy_quality_policies(
                    evaluate_frame(history, ticker, config),
                    _fallback_market_key(ticker),
                    config,
                )
                if signal.get("status") != STATUS_BUY_SIGNAL:
                    idx += 1
                    continue

                entry_idx = idx + 1
                exit_idx = idx + holding_period
                entry_price = float(df.iloc[entry_idx]["open"])
                exit_price = float(df.iloc[exit_idx]["close"])
                return_pct = ((exit_price / entry_price) - 1) * 100 if entry_price else None
                results.append({
                    "ticker": ticker,
                    "signal_date": df.index[idx].strftime("%Y-%m-%d"),
                    "signal_close": signal.get("price"),
                    "entry_date": df.index[entry_idx].strftime("%Y-%m-%d"),
                    "entry_price": round(entry_price, 2),
                    "exit_date": df.index[exit_idx].strftime("%Y-%m-%d"),
                    "exit_price": round(exit_price, 2),
                    "return_pct": round(return_pct, 2) if return_pct is not None else None,
                    "signal_score": signal.get("signal_score"),
                    "output_signal": signal.get("output_signal"),
                    "setup_type": signal.get("setup_type"),
                })
                idx = exit_idx
        except Exception:
            continue

    if results:
        summary_df = pd.DataFrame(results, columns=result_columns)
        summary_df = summary_df.sort_values(
            by=["entry_date", "ticker"],
            ascending=[True, True],
        ).reset_index(drop=True)
    else:
        summary_df = pd.DataFrame(columns=result_columns)

    if os.path.dirname(output_path):
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
    summary_df.to_csv(output_path, index=False)
    return summary_df, summarize_backtest_results(summary_df)


def load_tickers_from_file(
    csv_path: str,
    include_company_names: bool = False,
) -> list | tuple[list, dict]:
    def fallback_result():
        fallback_tickers = DEFAULT_FALLBACK_WATCHLIST.copy()
        if include_company_names:
            return fallback_tickers, {}
        return fallback_tickers

    if not csv_path or not os.path.isfile(csv_path):
        print(f" Input file target '{csv_path}' empty or missing. Falling back to default baseline watchlist...", flush=True)
        return fallback_result()
    try:
        df_input = pd.read_csv(csv_path, keep_default_na=False)
        found_col = [col for col in df_input.columns if col.strip().lower() in ("tickers", "ticker", "symbol")]
        if not found_col:
            print(" Error: File must contain a 'Ticker', 'Tickers' or 'Symbol' header column. Reverting to system defaults.", flush=True)
            return fallback_result()
        target_column_string = found_col[0]
        company_columns = [
            col for col in df_input.columns
            if col.strip().lower() in {
                "security name", "company name", "company_name", "company", "name",
            }
        ]
        company_column = company_columns[0] if company_columns else None
        tickers = []
        company_names = {}
        seen = set()
        for row_number, raw_ticker in enumerate(df_input[target_column_string].astype(str)):
            ticker = normalize_ticker_symbol(raw_ticker)
            if ticker in {"", "NAN", "NONE", "NULL"}:
                continue
            company = (
                str(df_input.iloc[row_number][company_column]).strip()
                if company_column
                else ""
            )
            if ticker not in seen:
                tickers.append(ticker)
                seen.add(ticker)
            if company and ticker not in company_names:
                company_names[ticker] = company

        if include_company_names:
            return tickers, company_names
        return tickers
    except Exception as e:
        print(f" Error reading CSV file '{csv_path}': {str(e)}. Reverting to system defaults.", flush=True)
        return fallback_result()


def scan_watchlist_concurrently(
    watchlist: list[str],
    config: dict,
    history_years: int,
    historical_guidance_scope: str,
    as_of_date: str | None,
    live_candle_mode: str,
    company_names: dict,
    run_timestamp: str,
    as_of_label: str,
    max_count_results: int = 0,
    max_buy_results: int = 0,
    max_workers: int = DEFAULT_MAX_WORKERS,
) -> tuple[list[dict], dict]:
    """
    Run independent ticker evaluations in complete concurrent polls.

    Max-Count and Max-Buys are poll-boundary continuation triggers, not exact
    result caps and not thread-pool sizing controls. Every task submitted in
    Poll#X is allowed to finish and is retained. Limits are checked only after
    Poll#X completes; when either cumulative limit has been met, Poll#X+1 is
    not started.
    """
    counts = {
        STATUS_BUY_SIGNAL: 0,
        STATUS_HOLD: 0,
        STATUS_IGNORE: 0,
        STATUS_REJECT: 0,
        STATUS_ERROR: 0,
    }
    results = []
    total_tickers = len(watchlist)
    worker_count = max(1, min(int(max_workers or 1), total_tickers))
    max_count_results = max(0, int(max_count_results or 0))
    max_buy_results = max(0, int(max_buy_results or 0))

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=worker_count,
        thread_name_prefix="v14-enhanced",
    ) as executor:
        for poll_number, poll_start in enumerate(
            range(0, total_tickers, worker_count),
            start=1,
        ):
            poll_items = list(
                enumerate(
                    watchlist[poll_start:poll_start + worker_count],
                    start=poll_start + 1,
                )
            )
            print(
                f"Poll#{poll_number} | Submitting {len(poll_items)} ticker(s)...",
                flush=True,
            )

            poll_futures = {}
            for position, ticker in poll_items:
                print(
                    f"({position}/{total_tickers}) Queued engine for {ticker}...",
                    flush=True,
                )
                future = executor.submit(
                    evaluate_stock_momentum,
                    ticker,
                    config=config,
                    history_years=history_years,
                    historical_guidance_scope=historical_guidance_scope,
                    as_of_date=as_of_date,
                    live_candle_mode=live_candle_mode,
                    company_name=company_names.get(ticker),
                )
                poll_futures[future] = (position, ticker)

            poll_results = []
            for future in concurrent.futures.as_completed(poll_futures):
                position, ticker = poll_futures[future]
                try:
                    data_packet = future.result()
                except Exception as exc:
                    error_message = f"ERROR | Concurrent worker failed: {exc}"
                    data_packet = {
                        "ticker": ticker,
                        "company_name": company_names.get(ticker) or ticker,
                        "status": STATUS_ERROR,
                        "output_signal": "Error_InternalError",
                        "classification": "",
                        "reason": "Internal error",
                        "OUT_MESSAGE": error_message,
                        "message": error_message,
                        "output_message": error_message,
                        "message_details": f"Error={exc}",
                        "confidence": "Low Setup (0/10)",
                        "risk_level": "Not Applicable",
                        "signal_score": 0,
                    }

                data_packet["timestamp"] = run_timestamp
                data_packet["as_of_date"] = as_of_label
                poll_results.append((position, ticker, data_packet))

            # Preserve input order without making classifications or stopping
            # behavior depend on thread completion order.
            for position, ticker, data_packet in sorted(
                poll_results,
                key=lambda item: item[0],
            ):
                results.append(data_packet)
                status = data_packet.get("status", STATUS_ERROR)
                if status not in counts:
                    status = STATUS_ERROR
                counts[status] += 1
                print(
                    f"({position}/{total_tickers}) Completed {ticker}: {status}",
                    flush=True,
                )

            print(
                f"Poll#{poll_number} complete | "
                f"Processed={len(results)} | BUY={counts[STATUS_BUY_SIGNAL]}",
                flush=True,
            )

            stop_reasons = []
            if max_count_results > 0 and len(results) >= max_count_results:
                stop_reasons.append(
                    f"Max-Count reached ({len(results)} >= {max_count_results})"
                )
            if (
                max_buy_results > 0
                and counts[STATUS_BUY_SIGNAL] >= max_buy_results
            ):
                stop_reasons.append(
                    "Max-Buys reached "
                    f"({counts[STATUS_BUY_SIGNAL]} >= {max_buy_results})"
                )

            if stop_reasons:
                print(
                    " Poll boundary stop: "
                    + "; ".join(stop_reasons)
                    + f". Poll#{poll_number + 1} will not be started.",
                    flush=True,
                )
                break

    return results, counts


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Enhanced Version 14 Momentum Scanner: independent per-ticker "
            "historical context, volume-supported momentum signals, and "
            "bounded concurrent polling"
        )
    )
    parser.add_argument("-c", "--codes", type=str, nargs="+", help="Direct stock codes list")
    parser.add_argument("-i", "--input", type=str, default=DEFAULT_INPUT_CSV, help="Path to input watchlist CSV file")
    parser.add_argument("-o", "--output", type=str, default=DEFAULT_OUTPUT_XLSX, help="Path to output log XLSX file")
    parser.add_argument("--preset", type=str, default="balanced", choices=["conservative", "balanced", "aggressive"], help="Strategy preset")
    parser.add_argument("--backtest", action="store_true", help="Run a historical signal replay instead of the live scan")
    parser.add_argument("--backtest-output", type=str, default=DEFAULT_BACKTEST_CSV, help="Path to write backtest results")
    parser.add_argument("--holding-period", type=int, default=5, help="Number of bars to hold after a buy signal")
    parser.add_argument(
        "--live-history-years",
        type=int,
        default=5,
        help=(
            "Fixed core calculation history (default: 5 years). Adaptive "
            "MAX/5Y/1Y guidance is selected separately from input-code count."
        ),
    )
    parser.add_argument("--backtest-history-years", type=int, default=3, help="Years of historical daily data to use in backtest")
    parser.add_argument("--as-of-date", type=str, default=None, help="Evaluate signals as of a specific historical date (YYYY-MM-DD)")
    parser.add_argument("--as-of-dates", type=str, default=None, help="Comma-separated historical dates (YYYY-MM-DD) for multi-date engine validation")
    parser.add_argument("--live-candle-mode", choices=["auto", "completed", "intraday"], default="auto", help="Live mode options")
    parser.add_argument(
        "--countmax",
        "--countMax",
        dest="max_count",
        type=int,
        default=0,
        help=(
            "Optional processed-count continuation trigger. It is checked only "
            "after a complete concurrent poll; final-poll extras are retained."
        ),
    )
    parser.add_argument(
        "--max-buys",
        dest="max_buys",
        type=int,
        default=0,
        help=(
            "Optional BUY-count continuation trigger. It is checked only after "
            "a complete concurrent poll; final-poll extras are retained."
        ),
    )
    enhanced_group = parser.add_argument_group("Enhanced V14 controls")
    enhanced_group.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_MAX_WORKERS,
        help="Maximum concurrent ticker workers (default: 3).",
    )
    enhanced_group.add_argument(
        "--buy-stoch-max",
        type=float,
        default=DEFAULT_BUY_STOCH_MAX,
        help=(
            "Base BUY stochastic K/D guidance limit (default: 80). A positive "
            "previous session can relax it to 90 for Early Momentum or 100 "
            "for Momentum Continuation; zero disables the limit."
        ),
    )
    args = parser.parse_args()
    execution_started = datetime.now()

    config = get_config(args.preset)
    max_count_results = max(0, int(args.max_count or 0))
    max_buy_results = max(0, int(args.max_buys or 0))
    max_workers = max(1, int(args.workers or 1))

    if args.buy_stoch_max < 0:
        parser.error("--buy-stoch-max cannot be negative")
    config["buy_stoch_max"] = float(args.buy_stoch_max)

    cli_codes_str = ""
    source_message = ""
    company_names = {}
    if args.codes:
        raw_list = []
        for segment in args.codes:
            raw_list.extend(segment.split(','))
        watchlist = list(dict.fromkeys(
            normalize_ticker_symbol(t) for t in raw_list if str(t).strip()
        ))
        cli_codes_str = ",".join(watchlist)
        source_message = f"Direct Command Line Input (-c) ({len(watchlist)} Tickers Loaded)"
    else:
        watchlist, company_names = load_tickers_from_file(
            args.input,
            include_company_names=True,
        )
        if set(watchlist) == set(DEFAULT_FALLBACK_WATCHLIST) and not os.path.isfile(args.input):
            source_message = "Default System Watchlist Baseline (Fallback)"
        else:
            source_message = f"Input CSV File (-i) -> {args.input} ({len(watchlist)} Tickers Loaded)"

    if not watchlist:
        print(" Error: Watchlist resolution produced 0 items. Exiting execution loop.", flush=True)
        sys.exit(1)

    input_ticker_count = len(watchlist)
    historical_guidance_scope = select_historical_guidance_scope(
        input_ticker_count
    )

    if args.backtest:
        print("=" * 80, flush=True)
        print(" STARTING HISTORICAL SIGNAL REPLAY", flush=True)
        print("=" * 80, flush=True)
        backtest_df, backtest_summary = run_backtest(
            watchlist,
            config,
            args.backtest_output,
            holding_period=args.holding_period,
            history_years=args.backtest_history_years,
        )
        if backtest_df.empty:
            print("No qualifying non-overlapping BUY trades were found.")
        else:
            print(backtest_df.head(20).to_string(index=False))
        print(
            "Replay summary | "
            f"Trades={backtest_summary['total_trades']} | "
            f"WinRate={backtest_summary['win_rate_pct']:.2f}% | "
            f"AverageReturn={backtest_summary['average_return_pct']:.2f}% | "
            f"MaxDrawdown={backtest_summary['max_drawdown_pct']:.2f}%"
        )
        print("Note: This is signal replay, not profitability validation; it excludes costs, slippage, and stop-loss logic.")
        print("Results written to:", args.backtest_output)
        sys.exit(0)

    try:
        as_of_date_list = build_as_of_date_list(args.as_of_date, args.as_of_dates)
    except ValueError as ve:
        print(f" Error: {ve}", flush=True)
        sys.exit(1)

    all_rows_for_output = []
    date_level_summary_rows = []
    total_tickers = len(watchlist)

    for run_number, as_of_date in enumerate(as_of_date_list, start=1):
        run_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        as_of_label = as_of_date if as_of_date else datetime.now().strftime('%Y-%m-%d')
        initial_summary_message = (
            f"Summary | AsOf={as_of_label} | DataThrough=PENDING | "
            f"Input={input_ticker_count} | "
            f"Total={total_tickers} | Workers={max_workers} | "
            f"HistoryGuidance={historical_guidance_scope} | "
            f"BuyStochMax={config['buy_stoch_max'] or 'OFF'} | "
            f"Scanned=0 | MaxCount={max_count_results or 'OFF'} | "
            f"MaxBuy={max_buy_results or 'OFF'} | BUY=0 | HOLD=0 | "
            "IGNORE=0 | REJECT=0 | ERROR=0"
        )

        print("=" * 80, flush=True)
        print(
            f" STARTING ENHANCED V14 MOMENTUM SCANNER | {run_timestamp}",
            flush=True,
        )
        print("=" * 80, flush=True)
        print(initial_summary_message, flush=True)

        unordered_results, counts = scan_watchlist_concurrently(
            watchlist=watchlist,
            config=config,
            history_years=args.live_history_years,
            historical_guidance_scope=historical_guidance_scope,
            as_of_date=as_of_date,
            live_candle_mode=args.live_candle_mode,
            company_names=company_names,
            run_timestamp=run_timestamp,
            as_of_label=as_of_label,
            max_count_results=max_count_results,
            max_buy_results=max_buy_results,
            max_workers=max_workers,
        )

        processed_tickers = len(unordered_results)
        data_through = summarize_data_through(unordered_results)
        summary_message = (
            f"Summary | AsOf={as_of_label} | DataThrough={data_through} | "
            f"Input={input_ticker_count} | "
            f"Total={total_tickers} | Workers={max_workers} | "
            f"HistoryGuidance={historical_guidance_scope} | "
            f"BuyStochMax={config['buy_stoch_max'] or 'OFF'} | "
            f"Scanned={processed_tickers} | MaxCount={max_count_results or 'OFF'} | "
            f"MaxBuy={max_buy_results or 'OFF'} | BUY={counts[STATUS_BUY_SIGNAL]} | "
            f"HOLD={counts[STATUS_HOLD]} | IGNORE={counts[STATUS_IGNORE]} | REJECT={counts[STATUS_REJECT]} | ERROR={counts[STATUS_ERROR]}"
        )

        for item in unordered_results:
            item["summary_message"] = summary_message

        all_rows_for_output.extend(unordered_results)
        date_level_summary_rows.append({
            "as_of_date": as_of_label,
            "data_through": data_through,
            "input_tickers": input_ticker_count,
            "total_tickers": total_tickers,
            "historical_guidance_scope": historical_guidance_scope,
            "scanned_tickers": processed_tickers,
            "buy_count": counts[STATUS_BUY_SIGNAL],
            "hold_count": counts[STATUS_HOLD],
            "ignore_count": counts[STATUS_IGNORE],
            "reject_count": counts[STATUS_REJECT],
            "error_count": counts[STATUS_ERROR],
            "buy_rate_pct": round((counts[STATUS_BUY_SIGNAL] / processed_tickers) * 100, 2) if processed_tickers else 0.0,
        })

    df_log = pd.DataFrame(all_rows_for_output)
    columns_order = [
        "ticker", "OUT_MESSAGE", "reason", "company_name", "price", "currency",
        "output_signal", "output_message", "message_details", "status",
        "setup_type", "confidence", "risk_level", "timestamp", "as_of_date",
        "exchange", "market_phase", "data_mode", "market_time_local",
        "market_time_et", "session_date", "candle_state", "data_note",
        "current_day_return_pct", "current_day_positive",
        "previous_day_return_pct", "previous_day_positive",
        "price_move_atr", "price_52w_high", "price_52w_low",
        "price_pct_52w_high", "price_distance_52w_high_pct",
        "new_52w_high", "price_history_high", "price_pct_history_high",
        "new_history_high",
        "ema_20", "ema_50", "ema_200", "ema20_gap_atr",
        "ema50_distance_atr", "extension_state", "macd_params", "macd",
        "macd_signal", "macd_hist", "macd_hist_prev", "macd_hist_3bar",
        "macd_state", "adx", "adx_band", "adx_1y_max",
        "adx_1y_percentile", "adx_pct_1y_max",
        "adx_relative_confidence", "rsi", "rsi_1y_min", "rsi_1y_max",
        "rsi_1y_percentile", "rsi_pct_1y_max", "atr", "stoch_k",
        "stoch_d", "stoch_k_1y_min", "stoch_k_1y_max",
        "stoch_k_1y_percentile", "stoch_k_pct_1y_max", "volume",
        "volume_avg_20", "average_daily_turnover_20", "volume_ratio_raw",
        "volume_session_fraction", "volume_ratio_basis", "volume_ratio",
        "minimum_volume_ratio", "volume_floor_passed",
        "minimum_adv20_turnover", "liquidity_floor_passed",
        "volume_1y_percentile", "volume_pct_1y_max",
        "volume_supportive", "volume_price_impulse",
        "historical_context_sessions",
        "historical_guidance_requested_scope",
        "historical_guidance_scope", "historical_guidance_sessions",
        "price_guidance_high", "price_guidance_low",
        "price_pct_guidance_high", "price_distance_guidance_high_pct",
        "new_guidance_high",
        "rsi_guidance_min", "rsi_guidance_max",
        "rsi_guidance_percentile", "rsi_pct_guidance_max",
        "adx_guidance_max", "adx_guidance_percentile",
        "adx_pct_guidance_max", "adx_guidance_confidence",
        "stoch_k_guidance_min", "stoch_k_guidance_max",
        "stoch_k_guidance_percentile", "stoch_k_pct_guidance_max",
        "volume_guidance_max", "volume_guidance_percentile",
        "volume_pct_guidance_max",
        "prior_strength_override",
        "effective_buy_stoch_max",
        "weekly_ema_20", "weekly_ema_50", "weekly_price", "signal_score",
        "extreme_extension_review_atr", "extreme_extension_review",
        "summary_message", "message",
    ]

    for col in columns_order:
        if col not in df_log.columns:
            df_log[col] = None
    df_log = df_log[columns_order]

    try:
        output_dir = os.path.dirname(args.output)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        output_root, _ = os.path.splitext(args.output)
        log_path = output_root + ".log"

        execution_finished = datetime.now()
        elapsed_seconds = int((execution_finished - execution_started).total_seconds())
        elapsed_text = f"{elapsed_seconds // 60:02d}m {elapsed_seconds % 60:02d}s"
        final_summary = date_level_summary_rows[-1] if date_level_summary_rows else {}

        buy_rows = df_log[df_log["status"] == STATUS_BUY_SIGNAL]
        buy_breakup = buy_rows["output_signal"].value_counts().to_dict() if not buy_rows.empty else {}
        buy_symbols = ",".join(buy_rows["ticker"].astype(str).tolist()) if not buy_rows.empty else "None"

        final_lines = [
            "-" * 100,
            "ENHANCED V14 LIVE SCANNER - POST EXECUTION SUMMARY",
            "-" * 100,
            f"Started              : {execution_started.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Completed            : {execution_finished.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Elapsed              : {elapsed_text}",
            f"As-of label          : {final_summary.get('as_of_date', 'Unavailable')}",
            f"Data through         : {final_summary.get('data_through', 'Unavailable')}",
            f"Input file           : {args.input if not args.codes else 'Direct command-line codes'}",
            f"Codes read           : {input_ticker_count}",
            f"Codes selected       : {total_tickers}",
            f"Codes processed      : {final_summary.get('scanned_tickers', 0)}",
            f"BUY SIGNAL           : {final_summary.get('buy_count', 0)}",
            f"HOLD                 : {final_summary.get('hold_count', 0)}",
            f"IGNORE               : {final_summary.get('ignore_count', 0)}",
            f"REJECT               : {final_summary.get('reject_count', 0)}",
            f"ERROR                : {final_summary.get('error_count', 0)}",
            f"BUY symbols          : {buy_symbols}",
            f"BUY breakup          : {buy_breakup or 'None'}",
            f"Preset               : {args.preset}",
            f"Concurrent workers   : {max_workers}",
            (
                "Historical guidance  : "
                f"{historical_guidance_scope} "
                "(input-count policy: <=100 MAX, <=1000 5Y, >1000 1Y)"
            ),
            f"Max-Count trigger    : {max_count_results or 'OFF'}",
            f"Max-Buys trigger     : {max_buy_results or 'OFF'}",
            (
                "BUY stochastic limit: "
                f"{config['buy_stoch_max']:.2f}"
                if config["buy_stoch_max"] > 0
                else "BUY stochastic limit: OFF"
            ),
            f"MACD                 : {MACD_FAST_PERIOD},{MACD_SLOW_PERIOD},{MACD_SIGNAL_PERIOD}",
            f"Requested candle mode: {args.live_candle_mode}",
            f"Output file          : {os.path.abspath(args.output)}",
            f"Log file             : {os.path.abspath(log_path)}",
            "-" * 100,
        ]
        final_text = "\n".join(final_lines)
        print("\n" + final_text, flush=True)

        summary_data = []
        for line in final_lines:
            if ":" in line and not line.startswith("---"):
                parts = line.split(":", 1)
                summary_data.append({"Metric": parts[0].strip(), "Value": parts[1].strip()})
            else:
                summary_data.append({"Metric": line.strip(), "Value": ""})
        
        cli_val = cli_codes_str if cli_codes_str else "None provided"
        summary_data.insert(7, {"Metric": "Direct command-line codes", "Value": cli_val})
        
        df_summary_sheet = pd.DataFrame(summary_data)

        df_details_data = df_log.copy()

        status_sort_map = {
            status: rank for rank, status in enumerate(SORT_ORDER_PRECEDENCE)
        }
        df_details_data["_status_rank"] = (
            df_details_data["status"].map(status_sort_map).fillna(len(status_sort_map))
        )
        df_details_data["_score_sort"] = (
            pd.to_numeric(df_details_data["signal_score"], errors="coerce").fillna(0)
        )
        df_details_data = df_details_data.sort_values(
            by=["_status_rank", "as_of_date", "_score_sort", "ticker"],
            ascending=[True, False, False, True],
        )
        df_details_sheet = df_details_data.drop(columns=["_status_rank", "_score_sort"])
        df_details_sheet = df_details_sheet.rename(columns={
            "ticker": "Ticker",
            "OUT_MESSAGE": "Message",
            "reason": "Reason",
            "company_name": "Company Name",
            "price": "Price",
        })

        with pd.ExcelWriter(args.output, engine="openpyxl") as writer:
            df_summary_sheet.to_excel(writer, sheet_name="Summary", index=False)
            df_details_sheet.to_excel(writer, sheet_name="Details", index=False)

            workbook = writer.book
            
            if "Summary" in workbook.sheetnames:
                summary_ws = workbook["Summary"]
                summary_ws.column_dimensions["A"].width = 30
                summary_ws.column_dimensions["B"].width = 100

            if "Details" in workbook.sheetnames:
                details_worksheet = workbook["Details"]
                details_worksheet.freeze_panes = "E2"
                details_worksheet.column_dimensions["A"].width = 18
                details_worksheet.column_dimensions["B"].width = 14
                details_worksheet.column_dimensions["C"].width = 26
                details_worksheet.column_dimensions["D"].width = 44
                details_worksheet.column_dimensions["E"].width = 14
                for cell in details_worksheet["E"][1:]:
                    cell.number_format = "0.00"

        print(f"\nMulti-sheet XLSX written successfully: {os.path.abspath(args.output)}", flush=True)

        with open(log_path, "w", encoding="utf-8") as log_file:
            log_file.write(final_text + "\n")

    except Exception as e:
        print(f"Failed to write output files: {e}", flush=True)
