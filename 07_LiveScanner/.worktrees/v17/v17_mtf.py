"""V17 U.S. completed-candle multi-timeframe diagnostics.

The daily V16 result is intentionally authoritative.  This module evaluates
only completed NYSE regular-session 30-minute source bars, aggregates them into
session-anchored 1-hour and 4-hour views, and reports whether those views are
supporting or contradicting the completed-daily thesis.

Nothing in this module changes an operational status or creates an executable
BUY.  The classifications are shadow diagnostics intended for replay and
calibration.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd
import ta

try:
    import exchange_calendars as xcals
except ImportError:  # pragma: no cover - exercised only in degraded installs.
    xcals = None


US_MARKET_TZ = ZoneInfo("America/New_York")
UTC_TZ = ZoneInfo("UTC")
SOURCE_INTERVAL_MINUTES = 30
SOURCE_PERIOD = "60d"
TIMEFRAME_MINUTES = {"1h": 60, "4h": 240}
MIN_INDICATOR_BARS = 40
VOLUME_SLOT_LOOKBACK = 20
VOLUME_SLOT_MIN_PERIODS = 5


def _as_timestamp(value: Any) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize(US_MARKET_TZ)
    else:
        timestamp = timestamp.tz_convert(US_MARKET_TZ)
    return timestamp


def _as_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if pd.notna(number) else None


def _rounded(value: Any, digits: int = 4) -> float | None:
    number = _as_float(value)
    return round(number, digits) if number is not None else None


@lru_cache(maxsize=1)
def get_us_calendar():
    """Return the declared NYSE calendar used for NYSE/Nasdaq session timing."""
    if xcals is None:
        return None
    return xcals.get_calendar("XNYS")


@lru_cache(maxsize=1024)
def us_session_bounds(session_date: date) -> tuple[pd.Timestamp, pd.Timestamp] | None:
    """Return the official regular-session open/close in New York time."""
    calendar = get_us_calendar()
    label = pd.Timestamp(session_date)
    if calendar is None:
        if label.weekday() >= 5:
            return None
        open_at = label.tz_localize(US_MARKET_TZ) + pd.Timedelta(hours=9, minutes=30)
        close_at = label.tz_localize(US_MARKET_TZ) + pd.Timedelta(hours=16)
        return open_at, close_at
    if not calendar.is_session(label):
        return None
    open_at = calendar.session_open(label).tz_convert(US_MARKET_TZ)
    close_at = calendar.session_close(label).tz_convert(US_MARKET_TZ)
    return open_at, close_at


def is_completed_us_trading_week(session_date: date | str | pd.Timestamp) -> bool:
    """Return whether the supplied completed session ends its trading week."""
    label = pd.Timestamp(session_date).normalize().tz_localize(None)
    calendar = get_us_calendar()
    if calendar is None:
        return label.weekday() == 4
    if not calendar.is_session(label):
        return False
    next_label = pd.Timestamp(calendar.next_session(label))
    return (
        next_label.isocalendar().year,
        next_label.isocalendar().week,
    ) != (
        label.isocalendar().year,
        label.isocalendar().week,
    )


def us_market_context(as_at: datetime | pd.Timestamp | None = None) -> dict:
    """Resolve the current U.S. phase and latest fully completed session."""
    timestamp = _as_timestamp(as_at or datetime.now(US_MARKET_TZ))
    bounds = us_session_bounds(timestamp.date())
    calendar = get_us_calendar()
    calendar_source = "XNYS_EXCHANGE_CALENDAR" if calendar is not None else "WEEKDAY_FALLBACK"

    if bounds is None:
        phase = "WEEKEND" if timestamp.weekday() >= 5 else "HOLIDAY"
        current_open = current_close = None
    else:
        current_open, current_close = bounds
        if timestamp < current_open:
            phase = "PREMARKET"
        elif timestamp < current_close:
            phase = "REGULAR"
        else:
            phase = "POSTMARKET"

    if bounds is not None and timestamp >= bounds[1]:
        completed_label = pd.Timestamp(timestamp.date())
    elif calendar is not None:
        candidate = calendar.date_to_session(
            pd.Timestamp(timestamp.date()),
            direction="previous",
        )
        if bounds is not None and candidate == pd.Timestamp(timestamp.date()):
            candidate = calendar.previous_session(candidate)
        completed_label = pd.Timestamp(candidate)
    else:
        candidate = pd.Timestamp(timestamp.date()) - pd.Timedelta(days=1)
        while candidate.weekday() >= 5:
            candidate -= pd.Timedelta(days=1)
        completed_label = candidate

    completed_bounds = us_session_bounds(completed_label.date())
    if calendar is not None:
        if bounds is not None:
            previous_label = pd.Timestamp(
                calendar.previous_session(pd.Timestamp(timestamp.date()))
            )
        else:
            previous_label = pd.Timestamp(
                calendar.date_to_session(
                    pd.Timestamp(timestamp.date()),
                    direction="previous",
                )
            )
    else:
        previous_label = pd.Timestamp(timestamp.date()) - pd.Timedelta(days=1)
        while previous_label.weekday() >= 5:
            previous_label -= pd.Timedelta(days=1)
    return {
        "market": "US",
        "timezone": str(US_MARKET_TZ),
        "phase": phase,
        "as_at": timestamp.isoformat(),
        "session_open": current_open.isoformat() if bounds is not None else None,
        "session_close": current_close.isoformat() if bounds is not None else None,
        "execution_session_date": (
            timestamp.date().isoformat() if bounds is not None else None
        ),
        "latest_completed_session_date": completed_label.date().isoformat(),
        "previous_traded_session_date": previous_label.date().isoformat(),
        "latest_completed_session_close": (
            completed_bounds[1].isoformat() if completed_bounds is not None else None
        ),
        "calendar_source": calendar_source,
    }


def validate_us_listing(
    ticker_symbol: str,
    metadata: dict | None = None,
) -> dict:
    """Classify whether a Yahoo code is in the NYSE/Nasdaq V17 scope."""
    symbol = str(ticker_symbol or "").strip().upper()
    metadata = metadata or {}
    rejected_suffixes = (
        ".NS", ".BO", ".L", ".T", ".TO", ".V", ".AX", ".HK", ".SS", ".SZ",
        ".PA", ".DE", ".F", ".MI", ".SW", ".AS", ".BR", ".CO", ".ST",
    )
    if not symbol or symbol.startswith("^") or symbol.endswith(rejected_suffixes):
        return {
            "in_scope": False,
            "scope": "UNSUPPORTED",
            "basis": "SYMBOL_SUFFIX",
            "exchange_code": None,
        }

    instrument_type = str(
        metadata.get("instrumentType")
        or metadata.get("quoteType")
        or ""
    ).strip().upper()
    if instrument_type and instrument_type != "EQUITY":
        return {
            "in_scope": False,
            "scope": "UNSUPPORTED",
            "basis": "PROVIDER_INSTRUMENT_TYPE",
            "exchange_code": instrument_type,
        }

    exchange_values = [
        metadata.get("exchangeName"),
        metadata.get("exchange"),
        metadata.get("fullExchangeName"),
    ]
    normalized_exchanges = [
        str(value).strip().upper()
        for value in exchange_values
        if value is not None and str(value).strip()
    ]
    exchange_text = " | ".join(normalized_exchanges)
    accepted_codes = {"NYQ", "NMS", "NGM", "NCM", "NAS"}
    rejected_tokens = (
        "NYSE AMERICAN",
        "NYSEAMERICAN",
        "NYSE ARCA",
        "NYSEARCA",
        "AMEX",
        "ARCA",
        "OTC",
    )
    known_non_us_tokens = (
        "NSE", "BSE", "LSE", "JPX", "TSX", "ASX", "EURONEXT", "XETRA",
    )
    if normalized_exchanges:
        if (
            any(value in {"ASE", "PCX"} for value in normalized_exchanges)
            or any(
                token in value
                for value in normalized_exchanges
                for token in rejected_tokens
            )
        ):
            return {
                "in_scope": False,
                "scope": "UNSUPPORTED",
                "basis": "PROVIDER_METADATA",
                "exchange_code": exchange_text,
            }
        if (
            any(value in accepted_codes for value in normalized_exchanges)
            or any(value == "NYSE" for value in normalized_exchanges)
            or any("NASDAQ" in value for value in normalized_exchanges)
        ):
            return {
                "in_scope": True,
                "scope": "NYSE_NASDAQ",
                "basis": "PROVIDER_METADATA",
                "exchange_code": exchange_text,
            }
        if any(token in exchange_text for token in known_non_us_tokens):
            return {
                "in_scope": False,
                "scope": "UNSUPPORTED",
                "basis": "PROVIDER_METADATA",
                "exchange_code": exchange_text,
            }

    return {
        "in_scope": False,
        "scope": "UNVERIFIED",
        "basis": "INSUFFICIENT_PROVIDER_METADATA",
        "exchange_code": exchange_text or None,
    }


def filter_completed_regular_bars(
    source_df: pd.DataFrame,
    *,
    cutoff: datetime | pd.Timestamp | None = None,
    source_interval_minutes: int = SOURCE_INTERVAL_MINUTES,
) -> pd.DataFrame:
    """Keep only fully completed bars inside official U.S. regular sessions."""
    if source_df is None or source_df.empty:
        return pd.DataFrame()

    frame = source_df.copy()
    frame.columns = [str(column).strip().lower() for column in frame.columns]
    required = {"open", "high", "low", "close", "volume"}
    if not required.issubset(frame.columns):
        return pd.DataFrame()
    frame = frame[list(sorted(required))].apply(pd.to_numeric, errors="coerce")
    frame = frame.dropna(subset=["open", "high", "low", "close"])
    frame["volume"] = frame["volume"].fillna(0.0)

    index = pd.DatetimeIndex(frame.index)
    if index.tz is None:
        index = index.tz_localize(US_MARKET_TZ)
    else:
        index = index.tz_convert(US_MARKET_TZ)
    frame.index = index
    frame = frame[~frame.index.duplicated(keep="last")].sort_index()

    cutoff_at = _as_timestamp(cutoff or datetime.now(US_MARKET_TZ))
    keep: list[bool] = []
    session_dates: list[str | None] = []
    bar_ends: list[pd.Timestamp | pd.NaT] = []
    for bar_start in frame.index:
        bounds = us_session_bounds(bar_start.date())
        if bounds is None:
            keep.append(False)
            session_dates.append(None)
            bar_ends.append(pd.NaT)
            continue
        open_at, close_at = bounds
        bar_end = min(
            bar_start + pd.Timedelta(minutes=source_interval_minutes),
            close_at,
        )
        included = bool(
            open_at <= bar_start < close_at
            and bar_end <= cutoff_at
        )
        keep.append(included)
        session_dates.append(bar_start.date().isoformat() if included else None)
        bar_ends.append(bar_end if included else pd.NaT)

    frame["_session_date"] = session_dates
    frame["_source_bar_end"] = bar_ends
    frame = frame.loc[keep].copy()
    frame.attrs["cutoff"] = cutoff_at.isoformat()
    frame.attrs["source_interval_minutes"] = int(source_interval_minutes)
    frame.attrs["calendar_source"] = (
        "XNYS_EXCHANGE_CALENDAR"
        if get_us_calendar() is not None
        else "WEEKDAY_FALLBACK"
    )
    return frame


def aggregate_session_bars(
    completed_source_df: pd.DataFrame,
    *,
    timeframe_minutes: int,
    source_interval_minutes: int = SOURCE_INTERVAL_MINUTES,
) -> pd.DataFrame:
    """Aggregate completed source bars without crossing a session boundary."""
    if completed_source_df is None or completed_source_df.empty:
        return pd.DataFrame()
    if timeframe_minutes <= 0 or source_interval_minutes <= 0:
        raise ValueError("Timeframe and source interval must be positive.")
    if timeframe_minutes % source_interval_minutes:
        raise ValueError("Timeframe must be divisible by the source interval.")

    source = completed_source_df.copy()
    records: list[dict] = []
    excluded_short_tail_count = 0
    excluded_incomplete_bucket_count = 0
    for session_text, session_rows in source.groupby("_session_date", sort=True):
        if not session_text:
            continue
        session_day = pd.Timestamp(session_text).date()
        bounds = us_session_bounds(session_day)
        if bounds is None:
            continue
        open_at, close_at = bounds
        session_minutes = int((close_at - open_at).total_seconds() // 60)
        rows = session_rows.sort_index().copy()
        offsets = (
            (pd.DatetimeIndex(rows.index) - open_at).total_seconds() // 60
        ).astype(int)
        rows["_bucket"] = offsets // timeframe_minutes

        for bucket, bucket_rows in rows.groupby("_bucket", sort=True):
            bucket = int(bucket)
            bucket_start = open_at + pd.Timedelta(
                minutes=bucket * timeframe_minutes
            )
            bucket_end = min(
                bucket_start + pd.Timedelta(minutes=timeframe_minutes),
                close_at,
            )
            duration_minutes = int((bucket_end - bucket_start).total_seconds() // 60)
            if duration_minutes < timeframe_minutes:
                excluded_short_tail_count += 1
                continue
            expected_source_bars = (
                duration_minutes + source_interval_minutes - 1
            ) // source_interval_minutes
            if len(bucket_rows) != expected_source_bars:
                excluded_incomplete_bucket_count += 1
                continue

            actual_end = pd.Timestamp(bucket_rows["_source_bar_end"].iloc[-1])
            if actual_end < bucket_end:
                excluded_incomplete_bucket_count += 1
                continue
            records.append({
                "bar_start": bucket_start,
                "bar_end": bucket_end,
                "session_date": session_day.isoformat(),
                "session_bucket": bucket,
                "duration_minutes": duration_minutes,
                "nominal_duration_minutes": int(timeframe_minutes),
                "is_short_bar": False,
                "source_bar_count": int(len(bucket_rows)),
                "expected_source_bar_count": int(expected_source_bars),
                "open": float(bucket_rows["open"].iloc[0]),
                "high": float(bucket_rows["high"].max()),
                "low": float(bucket_rows["low"].min()),
                "close": float(bucket_rows["close"].iloc[-1]),
                "volume": float(bucket_rows["volume"].sum()),
                "session_minutes": session_minutes,
            })

    if records:
        output = pd.DataFrame.from_records(records)
        output = output.set_index("bar_end", drop=False).sort_index()
    else:
        output = pd.DataFrame()
    output.attrs.update(completed_source_df.attrs)
    output.attrs["timeframe_minutes"] = int(timeframe_minutes)
    output.attrs["excluded_short_tail_count"] = excluded_short_tail_count
    output.attrs["excluded_incomplete_bucket_count"] = (
        excluded_incomplete_bucket_count
    )
    return output


def calculate_timeframe_indicator_frame(bars: pd.DataFrame) -> pd.DataFrame:
    """Calculate the complete V17 diagnostic series for one timeframe."""
    if bars is None:
        return pd.DataFrame()
    if bars.empty:
        output = pd.DataFrame()
        output.attrs.update(bars.attrs)
        return output
    frame = bars.copy().sort_index()
    required = {"open", "high", "low", "close", "volume", "duration_minutes", "session_bucket"}
    if not required.issubset(frame.columns):
        return pd.DataFrame()

    frame["ema_20"] = ta.trend.ema_indicator(frame["close"], window=20)
    frame["ema_50"] = ta.trend.ema_indicator(frame["close"], window=50)
    frame["ema_200"] = ta.trend.ema_indicator(frame["close"], window=200)
    macd = ta.trend.MACD(
        frame["close"],
        window_fast=12,
        window_slow=26,
        window_sign=9,
    )
    frame["macd"] = macd.macd()
    frame["macd_signal"] = macd.macd_signal()
    frame["macd_hist"] = macd.macd_diff()
    frame["adx"] = ta.trend.adx(
        frame["high"], frame["low"], frame["close"], window=14
    )
    frame["adx_plus_di"] = ta.trend.adx_pos(
        frame["high"], frame["low"], frame["close"], window=14
    )
    frame["adx_minus_di"] = ta.trend.adx_neg(
        frame["high"], frame["low"], frame["close"], window=14
    )
    frame["rsi"] = ta.momentum.rsi(frame["close"], window=14)
    frame["atr"] = ta.volatility.average_true_range(
        frame["high"], frame["low"], frame["close"], window=14
    )
    frame["stoch_k"] = ta.momentum.stoch(
        frame["high"], frame["low"], frame["close"], window=9
    )
    frame["stoch_d"] = ta.momentum.stoch_signal(
        frame["high"],
        frame["low"],
        frame["close"],
        window=9,
        smooth_window=6,
    )

    session_groups = frame.groupby("session_date", group_keys=False)
    frame["bar_return_pct"] = session_groups["close"].pct_change() * 100.0
    frame["bar_open_to_close_pct"] = (
        frame["close"].div(frame["open"].where(frame["open"].ne(0))) - 1.0
    ) * 100.0
    frame["session_return_pct"] = (
        frame["close"].div(
            session_groups["open"].transform("first").where(
                session_groups["open"].transform("first").ne(0)
            )
        ) - 1.0
    ) * 100.0
    frame["macd_hist_change_1"] = session_groups["macd_hist"].diff()
    frame["adx_change_1"] = session_groups["adx"].diff()
    frame["rsi_change_1"] = session_groups["rsi"].diff()
    frame["stoch_spread"] = frame["stoch_k"] - frame["stoch_d"]
    frame["stoch_spread_change_1"] = session_groups["stoch_spread"].diff()
    frame["volume_per_minute"] = (
        frame["volume"] / frame["duration_minutes"].replace(0, pd.NA)
    )
    frame["volume_rate_avg_20_same_slot"] = frame.groupby(
        "session_bucket",
        group_keys=False,
    )["volume_per_minute"].transform(
        lambda values: values.shift(1).rolling(
            VOLUME_SLOT_LOOKBACK,
            min_periods=VOLUME_SLOT_MIN_PERIODS,
        ).mean()
    )
    frame["volume_slot_ratio"] = (
        frame["volume_per_minute"] / frame["volume_rate_avg_20_same_slot"]
    )
    frame["volume_slot_ratio_change_1"] = session_groups[
        "volume_slot_ratio"
    ].diff()

    frame["trend_check_available"] = frame[
        ["close", "ema_20", "ema_50"]
    ].notna().all(axis=1)
    frame["macd_check_available"] = frame[
        ["macd", "macd_signal", "macd_hist"]
    ].notna().all(axis=1)
    frame["adx_check_available"] = frame[
        ["adx", "adx_plus_di", "adx_minus_di"]
    ].notna().all(axis=1)
    frame["stoch_check_available"] = frame[
        ["stoch_k", "stoch_d"]
    ].notna().all(axis=1)
    frame["rsi_check_available"] = frame["rsi"].notna()
    frame["volume_check_available"] = frame["volume_slot_ratio"].notna()

    frame["trend_supportive"] = (
        (frame["close"] > frame["ema_20"])
        & (frame["ema_20"] > frame["ema_50"])
    ).astype("boolean").where(frame["trend_check_available"])
    frame["macd_supportive"] = (
        (frame["macd"] > frame["macd_signal"])
        & (frame["macd_hist"] > 0)
    ).astype("boolean").where(frame["macd_check_available"])
    frame["adx_supportive"] = (
        (frame["adx_plus_di"] > frame["adx_minus_di"])
        & (frame["adx"] >= 20)
    ).astype("boolean").where(frame["adx_check_available"])
    frame["stoch_supportive"] = (
        (frame["stoch_k"] > frame["stoch_d"])
        .astype("boolean")
        .where(frame["stoch_check_available"])
    )
    frame["rsi_supportive"] = (
        (frame["rsi"] >= 50)
        .astype("boolean")
        .where(frame["rsi_check_available"])
    )
    frame["volume_supportive"] = (
        (frame["volume_slot_ratio"] >= 1.0)
        .astype("boolean")
        .where(frame["volume_check_available"])
    )
    return frame


def summarize_timeframe_diagnostics(
    indicator_frame: pd.DataFrame,
    *,
    timeframe_name: str,
    execution_session_date: str | None = None,
) -> dict:
    """Summarize the latest and prior completed bars without hiding raw inputs."""
    base = {
        "available": False,
        "timeframe": timeframe_name,
        "bars": 0,
        "latest_session_date": None,
        "fresh_for_execution_session": False,
        "diagnostic_bias": "UNAVAILABLE",
        "progression_state": "UNAVAILABLE",
        "relation_to_daily": "UNAVAILABLE",
        "improved_components": "",
        "regressed_components": "",
        "support_count": 0,
        "support_max": 0,
        "historical_warmup_bars": 0,
        "excluded_short_tail_count": int(
            (indicator_frame.attrs if indicator_frame is not None else {}).get(
                "excluded_short_tail_count",
                0,
            )
        ),
        "excluded_incomplete_bucket_count": int(
            (indicator_frame.attrs if indicator_frame is not None else {}).get(
                "excluded_incomplete_bucket_count",
                0,
            )
        ),
    }
    if indicator_frame is None or indicator_frame.empty:
        return base

    frame = indicator_frame.copy()
    base["historical_warmup_bars"] = int(len(frame))
    if len(frame) < MIN_INDICATOR_BARS:
        base["diagnostic_bias"] = "INSUFFICIENT_HISTORY"
        base["progression_state"] = "INSUFFICIENT_HISTORY"
        return base

    current_frame = frame.loc[
        frame["session_date"].astype(str).eq(
            str(execution_session_date or "")
        )
    ].copy()
    base["historical_warmup_bars"] = int(len(frame) - len(current_frame))
    base["bars"] = int(len(current_frame))
    if current_frame.empty:
        base["diagnostic_bias"] = "NO_COMPLETED_CURRENT_SESSION_BAR"
        base["progression_state"] = "NO_COMPLETED_CURRENT_SESSION_BAR"
        return base

    latest = current_frame.iloc[-1]
    previous = current_frame.iloc[-2] if len(current_frame) >= 2 else None
    required = (
        "macd", "macd_signal", "macd_hist", "adx", "adx_plus_di",
        "adx_minus_di", "rsi", "atr", "stoch_k", "stoch_d",
    )
    if any(pd.isna(latest.get(name)) for name in required):
        base["diagnostic_bias"] = "INDICATORS_INCOMPLETE"
        base["progression_state"] = "INDICATORS_INCOMPLETE"
        return base

    support_checks = (
        ("trend_supportive", "trend_check_available"),
        ("macd_supportive", "macd_check_available"),
        ("adx_supportive", "adx_check_available"),
        ("stoch_supportive", "stoch_check_available"),
        ("rsi_supportive", "rsi_check_available"),
        ("volume_supportive", "volume_check_available"),
    )
    observed_support = [
        bool(latest.get(support_name))
        for support_name, available_name in support_checks
        if bool(latest.get(available_name, False))
        and pd.notna(latest.get(support_name))
    ]
    support_count = sum(observed_support)
    support_max = len(observed_support)
    support_ratio = support_count / support_max if support_max else 0.0
    if support_max < 4:
        diagnostic_bias = "INDICATORS_INCOMPLETE"
    elif support_ratio >= (5 / 6):
        diagnostic_bias = "BULLISH"
    elif support_ratio >= (4 / 6):
        diagnostic_bias = "SUPPORTIVE"
    elif support_ratio >= (2 / 6):
        diagnostic_bias = "MIXED"
    else:
        diagnostic_bias = "BEARISH"

    improved: list[str] = []
    regressed: list[str] = []

    def compare(name: str, current_value: Any, previous_value: Any) -> None:
        current_number = _as_float(current_value)
        previous_number = _as_float(previous_value)
        if current_number is None or previous_number is None:
            return
        tolerance = max(1e-9, abs(previous_number) * 1e-6)
        if current_number > previous_number + tolerance:
            improved.append(name)
        elif current_number < previous_number - tolerance:
            regressed.append(name)

    if previous is None:
        progression_state = "CURRENT_SESSION_START"
    else:
        compare("price", latest["close"], previous["close"])
        compare("macd_histogram", latest["macd_hist"], previous["macd_hist"])
        if latest["adx_plus_di"] > latest["adx_minus_di"]:
            compare("bullish_adx", latest["adx"], previous["adx"])
        elif latest["adx_minus_di"] >= latest["adx_plus_di"]:
            regressed.append("directional_movement")
        compare(
            "stochastic_spread",
            latest["stoch_spread"],
            previous["stoch_spread"],
        )
        compare("rsi", latest["rsi"], previous["rsi"])
        compare(
            "volume_change",
            latest["volume_per_minute"],
            previous["volume_per_minute"],
        )

        if len(improved) >= 4 and len(improved) >= len(regressed) + 2:
            progression_state = "PROGRESSED"
        elif len(regressed) >= 4 and len(regressed) >= len(improved) + 2:
            progression_state = "REGRESSED"
        elif not improved and not regressed:
            progression_state = "STABLE"
        else:
            progression_state = "MIXED"

    bullish_cross = (
        bool(
            previous["stoch_k"] <= previous["stoch_d"]
            and latest["stoch_k"] > latest["stoch_d"]
        )
        if previous is not None
        else None
    )
    bearish_cross = (
        bool(
            previous["stoch_k"] >= previous["stoch_d"]
            and latest["stoch_k"] < latest["stoch_d"]
        )
        if previous is not None
        else None
    )
    latest_session = str(latest.get("session_date") or "")
    result = {
        **base,
        "available": True,
        "bars": int(len(current_frame)),
        "latest_session_date": latest_session or None,
        "fresh_for_execution_session": bool(
            execution_session_date
            and latest_session == execution_session_date
        ),
        "bar_start": pd.Timestamp(latest["bar_start"]).isoformat(),
        "bar_end": pd.Timestamp(latest["bar_end"]).isoformat(),
        "bar_duration_minutes": int(latest["duration_minutes"]),
        "bar_is_short": bool(latest["is_short_bar"]),
        "bar_source_count": int(latest["source_bar_count"]),
        "open": _rounded(latest["open"]),
        "high": _rounded(latest["high"]),
        "low": _rounded(latest["low"]),
        "close": _rounded(latest["close"]),
        "bar_return_pct": _rounded(latest["bar_return_pct"]),
        "bar_open_to_close_pct": _rounded(latest["bar_open_to_close_pct"]),
        "session_return_pct": _rounded(latest["session_return_pct"]),
        "ema_20": _rounded(latest["ema_20"]),
        "ema_50": _rounded(latest["ema_50"]),
        "ema_200": _rounded(latest["ema_200"]),
        "macd": _rounded(latest["macd"]),
        "macd_signal": _rounded(latest["macd_signal"]),
        "macd_hist": _rounded(latest["macd_hist"]),
        "macd_hist_change_1": _rounded(latest["macd_hist_change_1"]),
        "adx": _rounded(latest["adx"]),
        "adx_plus_di": _rounded(latest["adx_plus_di"]),
        "adx_minus_di": _rounded(latest["adx_minus_di"]),
        "adx_change_1": _rounded(latest["adx_change_1"]),
        "rsi": _rounded(latest["rsi"]),
        "rsi_change_1": _rounded(latest["rsi_change_1"]),
        "atr": _rounded(latest["atr"]),
        "stoch_k": _rounded(latest["stoch_k"]),
        "stoch_d": _rounded(latest["stoch_d"]),
        "stoch_spread": _rounded(latest["stoch_spread"]),
        "stoch_spread_change_1": _rounded(
            latest["stoch_spread_change_1"]
        ),
        "stoch_bullish_cross": bullish_cross,
        "stoch_bearish_cross": bearish_cross,
        "volume": _rounded(latest["volume"], 2),
        "volume_per_minute": _rounded(latest["volume_per_minute"], 2),
        "volume_rate_avg_20_same_slot": _rounded(
            latest["volume_rate_avg_20_same_slot"],
            2,
        ),
        "volume_slot_ratio": _rounded(latest["volume_slot_ratio"]),
        "volume_slot_ratio_change_1": _rounded(
            latest["volume_slot_ratio_change_1"]
        ),
        "trend_check_available": bool(latest["trend_check_available"]),
        "macd_check_available": bool(latest["macd_check_available"]),
        "adx_check_available": bool(latest["adx_check_available"]),
        "stoch_check_available": bool(latest["stoch_check_available"]),
        "rsi_check_available": bool(latest["rsi_check_available"]),
        "volume_check_available": bool(latest["volume_check_available"]),
        "trend_supportive": (
            bool(latest["trend_supportive"])
            if pd.notna(latest["trend_supportive"])
            else None
        ),
        "macd_supportive": (
            bool(latest["macd_supportive"])
            if pd.notna(latest["macd_supportive"])
            else None
        ),
        "adx_supportive": (
            bool(latest["adx_supportive"])
            if pd.notna(latest["adx_supportive"])
            else None
        ),
        "stoch_supportive": (
            bool(latest["stoch_supportive"])
            if pd.notna(latest["stoch_supportive"])
            else None
        ),
        "rsi_supportive": (
            bool(latest["rsi_supportive"])
            if pd.notna(latest["rsi_supportive"])
            else None
        ),
        "volume_supportive": (
            bool(latest["volume_supportive"])
            if pd.notna(latest["volume_supportive"])
            else None
        ),
        "support_count": support_count,
        "support_max": support_max,
        "diagnostic_bias": diagnostic_bias,
        "progression_state": progression_state,
        "improved_components": ",".join(improved),
        "regressed_components": ",".join(regressed),
    }
    if diagnostic_bias in {"BULLISH", "SUPPORTIVE"} and progression_state != "REGRESSED":
        result["relation_to_daily"] = "SUPPORTIVE"
    elif diagnostic_bias == "BEARISH" or progression_state == "REGRESSED":
        result["relation_to_daily"] = "REGRESSING"
    else:
        result["relation_to_daily"] = "MIXED"
    return result


def flatten_diagnostics(prefix: str, diagnostics: dict) -> dict:
    return {f"{prefix}_{key}": value for key, value in diagnostics.items()}


def combine_daily_and_intraday(
    daily_result: dict,
    four_hour: dict,
    one_hour: dict,
) -> dict:
    """Build a non-binding interpretation while preserving the daily result."""
    daily_primary = bool(daily_result.get("v16_primary_regime_passed"))
    daily_momentum_state = str(daily_result.get("momentum_state") or "NONE")
    timeframe_values = (four_hour, one_hour)
    relations = [
        value.get("relation_to_daily", "UNAVAILABLE")
        for value in timeframe_values
    ]
    available_relations = [value for value in relations if value != "UNAVAILABLE"]
    fresh_relations = [
        value.get("relation_to_daily", "UNAVAILABLE")
        for value in timeframe_values
        if bool(value.get("fresh_for_execution_session"))
        and value.get("relation_to_daily", "UNAVAILABLE") != "UNAVAILABLE"
    ]
    supportive_count = available_relations.count("SUPPORTIVE")
    regressing_count = available_relations.count("REGRESSING")
    fresh_supportive_count = fresh_relations.count("SUPPORTIVE")
    fresh_regressing_count = fresh_relations.count("REGRESSING")

    if not daily_primary:
        if fresh_supportive_count == 2:
            combined_state = "INTRADAY_IGNITION_DAILY_UNQUALIFIED"
        else:
            combined_state = "DAILY_UNQUALIFIED"
    elif not fresh_relations:
        combined_state = "DAILY_MOMENTUM_INTRADAY_UNAVAILABLE"
    elif fresh_regressing_count:
        combined_state = "DAILY_MOMENTUM_REGRESSING"
    elif fresh_supportive_count == 2:
        combined_state = "TRUE_MOMENTUM_CANDIDATE"
    elif fresh_supportive_count == 1:
        combined_state = "DAILY_MOMENTUM_PARTIALLY_SUPPORTED"
    else:
        combined_state = "DAILY_MOMENTUM_MIXED"

    return {
        "v17_shadow_mode": True,
        "v17_classification_active": False,
        "v17_operational_status_unchanged": True,
        "v17_daily_baseline_status": daily_result.get("status"),
        "v17_daily_baseline_signal": daily_result.get("output_signal"),
        "v17_daily_baseline_momentum_state": daily_momentum_state,
        "v17_daily_primary_regime_passed": daily_primary,
        "v17_current_development_state": combined_state,
        "v17_true_momentum_candidate": (
            combined_state == "TRUE_MOMENTUM_CANDIDATE"
        ),
        "v17_true_momentum_confirmed": False,
        "v17_mtf_supportive_count": supportive_count,
        "v17_mtf_regressing_count": regressing_count,
        "v17_mtf_available_count": len(available_relations),
        "v17_mtf_fresh_count": len(fresh_relations),
        "v17_mtf_fresh_supportive_count": fresh_supportive_count,
        "v17_mtf_fresh_regressing_count": fresh_regressing_count,
    }


def evaluate_mtf_source(
    source_df: pd.DataFrame,
    *,
    daily_result: dict,
    cutoff: datetime | pd.Timestamp | None = None,
) -> tuple[dict, dict[str, pd.DataFrame]]:
    """Evaluate completed 1H/4H bars and return flattened audit diagnostics."""
    context = us_market_context(cutoff)
    completed_source = filter_completed_regular_bars(source_df, cutoff=cutoff)
    frames: dict[str, pd.DataFrame] = {
        "source_completed_30m": completed_source,
    }
    summaries: dict[str, dict] = {}
    for name, minutes in TIMEFRAME_MINUTES.items():
        bars = aggregate_session_bars(
            completed_source,
            timeframe_minutes=minutes,
        )
        indicators = calculate_timeframe_indicator_frame(bars)
        summary = summarize_timeframe_diagnostics(
            indicators,
            timeframe_name=name,
            execution_session_date=context.get("execution_session_date"),
        )
        frames[f"{name}_bars"] = bars
        frames[f"{name}_indicators"] = indicators
        summaries[name] = summary

    combined = combine_daily_and_intraday(
        daily_result,
        summaries["4h"],
        summaries["1h"],
    )
    output = {
        "engine_version": "V17_D1_MTF_SHADOW",
        "v17_market_scope": "NYSE_NASDAQ",
        "v17_intraday_source_interval": "30m",
        "v17_intraday_source_rows": int(len(completed_source)),
        "v17_execution_phase": context["phase"],
        "v17_execution_timestamp": context["as_at"],
        "v17_execution_session_date": context["execution_session_date"],
        "v17_latest_completed_session_date": (
            context["latest_completed_session_date"]
        ),
        "v17_calendar_source": context["calendar_source"],
        **flatten_diagnostics("mtf_4h", summaries["4h"]),
        **flatten_diagnostics("mtf_1h", summaries["1h"]),
        **combined,
    }
    return output, frames


def load_intraday_source(path: str | Path) -> pd.DataFrame:
    """Load a replayable 30-minute source file from CSV or Parquet."""
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"Intraday source not found: {source}")
    if source.suffix.lower() in {".parquet", ".pq"}:
        frame = pd.read_parquet(source)
    else:
        frame = pd.read_csv(source)
    if not isinstance(frame.index, pd.DatetimeIndex):
        timestamp_column = next(
            (
                column
                for column in ("timestamp", "datetime", "date", "Datetime", "Date")
                if column in frame.columns
            ),
            None,
        )
        if timestamp_column is None:
            raise ValueError("Intraday source needs a timestamp/date column.")
        frame.index = pd.to_datetime(frame.pop(timestamp_column), errors="raise")
    return frame
