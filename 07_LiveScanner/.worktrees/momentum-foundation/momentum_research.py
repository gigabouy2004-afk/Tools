"""Daily momentum research foundation.

This module does not classify a security as genuine momentum.  It builds a
point-in-time feature record from one completed daily session and joins future
outcomes only after that record is frozen.  The resulting panel is intended for
chronological calibration and holdout research.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import ta

from v17_mtf import is_completed_us_trading_week


REQUIRED_OHLCV = ("open", "high", "low", "close", "volume")
DEFAULT_HORIZONS = (5, 10, 20)
PLAIN_METADATA_COLUMNS = (
    "ticker",
    "security_id",
    "security_name",
    "sector",
    "industry",
    "listing_exchange",
    "instrument_type",
    "is_etf",
    "listing_date",
    "delisting_date",
)


@dataclass(frozen=True)
class OutcomeContract:
    """Research outcome settings; these are not production thresholds."""

    horizons: tuple[int, ...] = DEFAULT_HORIZONS
    barrier_horizon: int = 10
    upper_atr_multiple: float = 2.0
    lower_atr_multiple: float = 1.0

    def __post_init__(self) -> None:
        if not self.horizons or any(value <= 0 for value in self.horizons):
            raise ValueError("Forward horizons must be positive.")
        if self.barrier_horizon <= 0:
            raise ValueError("Barrier horizon must be positive.")
        if self.barrier_horizon not in self.horizons:
            raise ValueError("Barrier horizon must be included in horizons.")
        if self.upper_atr_multiple <= 0 or self.lower_atr_multiple <= 0:
            raise ValueError("ATR barrier multiples must be positive.")


def history_tier(completed_sessions: int) -> tuple[str, str]:
    """Return a plain history tier and the eligible research track."""
    sessions = max(0, int(completed_sessions))
    if sessions < 20:
        return "Observation only", "Not enough stock history"
    if sessions < 120:
        return "Young listing", "Young-listing research"
    if sessions < 252:
        return "Developing history", "Reduced-history research"
    return "Established history", "Standard-history research"


def normalize_daily_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize one security's daily frame without filling missing history."""
    if frame is None or frame.empty:
        return pd.DataFrame(columns=REQUIRED_OHLCV)
    output = frame.copy()
    output.columns = [str(column).strip().lower() for column in output.columns]
    missing = [column for column in REQUIRED_OHLCV if column not in output]
    if missing:
        raise ValueError("Daily data is missing: " + ", ".join(missing))

    index = pd.DatetimeIndex(output.index)
    if index.tz is not None:
        index = index.tz_convert("America/New_York").tz_localize(None)
    output.index = index.normalize()
    output = output.loc[~output.index.duplicated(keep="last")].sort_index()
    for column in REQUIRED_OHLCV:
        output[column] = pd.to_numeric(output[column], errors="coerce")
    output = output.dropna(subset=["open", "high", "low", "close"])
    output["volume"] = output["volume"].fillna(0.0).clip(lower=0.0)
    valid_prices = output[list(REQUIRED_OHLCV[:-1])].gt(0).all(axis=1)
    return output.loc[valid_prices].copy()


def _completed_weekly_context(frame: pd.DataFrame) -> pd.DataFrame:
    weekly = (
        frame[list(REQUIRED_OHLCV)]
        .resample("W-FRI")
        .agg({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        })
        .dropna(subset=["close"])
    )
    weekly["weekly_ema_20"] = ta.trend.ema_indicator(
        weekly["close"],
        window=20,
    )
    weekly["weekly_ema_50"] = ta.trend.ema_indicator(
        weekly["close"],
        window=50,
    )
    weekly_lookup = weekly[
        ["close", "weekly_ema_20", "weekly_ema_50"]
    ].rename(columns={"close": "weekly_close"})

    effective_labels = []
    for session in frame.index:
        friday = session + pd.Timedelta(days=(4 - session.weekday()) % 7)
        if not is_completed_us_trading_week(session):
            friday -= pd.Timedelta(days=7)
        effective_labels.append(friday.normalize())
    aligned = weekly_lookup.reindex(pd.DatetimeIndex(effective_labels))
    aligned.index = frame.index
    return aligned


def calculate_daily_features(
    frame: pd.DataFrame,
    *,
    ticker: str,
) -> pd.DataFrame:
    """Build point-in-time features from completed daily observations."""
    source = normalize_daily_frame(frame)
    if source.empty:
        return pd.DataFrame()

    calc = source[list(REQUIRED_OHLCV)].copy()
    calc["ticker"] = (
        source["ticker"].astype(str).str.strip().str.upper()
        if "ticker" in source
        else str(ticker).strip().upper()
    )
    calc["previous_completed_session"] = calc.index.strftime("%Y-%m-%d")
    calc["available_completed_sessions"] = np.arange(1, len(calc) + 1)

    tiers = calc["available_completed_sessions"].map(history_tier)
    calc["history_tier"] = tiers.map(lambda value: value[0])
    calc["eligible_research_track"] = tiers.map(lambda value: value[1])

    calc["ema_20"] = ta.trend.ema_indicator(calc["close"], window=20)
    calc["ema_50"] = ta.trend.ema_indicator(calc["close"], window=50)
    calc["ema_200"] = ta.trend.ema_indicator(calc["close"], window=200)
    macd = ta.trend.MACD(
        calc["close"],
        window_fast=12,
        window_slow=26,
        window_sign=9,
    )
    calc["macd"] = macd.macd()
    calc["macd_signal"] = macd.macd_signal()
    calc["macd_histogram"] = macd.macd_diff()
    calc["macd_histogram_change"] = calc["macd_histogram"].diff()
    calc["atr_14"] = ta.volatility.average_true_range(
        calc["high"],
        calc["low"],
        calc["close"],
        window=14,
    )
    calc["adx_14"] = ta.trend.adx(
        calc["high"],
        calc["low"],
        calc["close"],
        window=14,
    )
    calc["plus_di_14"] = ta.trend.adx_pos(
        calc["high"],
        calc["low"],
        calc["close"],
        window=14,
    )
    calc["minus_di_14"] = ta.trend.adx_neg(
        calc["high"],
        calc["low"],
        calc["close"],
        window=14,
    )
    calc["adx_change_5_sessions"] = calc["adx_14"].diff(5)
    calc["rsi_14"] = ta.momentum.rsi(calc["close"], window=14)
    calc["stochastic_k_9"] = ta.momentum.stoch(
        calc["high"],
        calc["low"],
        calc["close"],
        window=9,
    )
    calc["stochastic_d_6"] = ta.momentum.stoch_signal(
        calc["high"],
        calc["low"],
        calc["close"],
        window=9,
        smooth_window=6,
    )
    # The indicator library emits placeholder zeroes before Wilder's ADX has
    # enough observations. Missing evidence must remain missing, especially
    # for young listings.
    calc.loc[
        calc["available_completed_sessions"].lt(28),
        ["adx_14", "plus_di_14", "minus_di_14"],
    ] = np.nan
    calc.loc[
        calc["available_completed_sessions"].lt(14),
        ["atr_14"],
    ] = np.nan

    for horizon in (5, 10, 20, 60, 120):
        calc[f"return_{horizon}_sessions_pct"] = (
            calc["close"].pct_change(horizon, fill_method=None) * 100.0
        )
    calc["ema_20_slope_10_sessions_pct"] = (
        calc["ema_20"].pct_change(10, fill_method=None) * 100.0
    )
    calc["ema_50_slope_20_sessions_pct"] = (
        calc["ema_50"].pct_change(20, fill_method=None) * 100.0
    )
    calc["ema_200_slope_60_sessions_pct"] = (
        calc["ema_200"].pct_change(60, fill_method=None) * 100.0
    )

    calc["prior_20_session_average_volume"] = (
        calc["volume"].shift(1).rolling(20, min_periods=20).mean()
    )
    calc["daily_volume_ratio"] = calc["volume"].div(
        calc["prior_20_session_average_volume"].where(
            calc["prior_20_session_average_volume"].gt(0)
        )
    )
    calc["prior_20_session_average_turnover"] = (
        (calc["volume"] * calc["close"])
        .shift(1)
        .rolling(20, min_periods=20)
        .mean()
    )
    calc["prior_52_week_high"] = (
        calc["high"].shift(1).rolling(252, min_periods=1).max()
    )
    calc["price_as_pct_of_prior_52_week_high"] = (
        calc["close"].div(calc["prior_52_week_high"].where(
            calc["prior_52_week_high"].gt(0)
        )) * 100.0
    )
    calc["post_listing_high"] = calc["high"].cummax()
    calc["post_listing_low"] = calc["low"].cummin()
    calc["price_as_pct_of_post_listing_high"] = (
        calc["close"].div(calc["post_listing_high"]) * 100.0
    )
    calc["return_since_listing_pct"] = (
        calc["close"].div(float(calc["close"].iloc[0])) - 1.0
    ) * 100.0
    calc["distance_from_ema_20_atr"] = (
        (calc["close"] - calc["ema_20"])
        .div(calc["atr_14"].where(calc["atr_14"].gt(0)))
    )
    calc["distance_from_ema_50_atr"] = (
        (calc["close"] - calc["ema_50"])
        .div(calc["atr_14"].where(calc["atr_14"].gt(0)))
    )

    calc = calc.join(_completed_weekly_context(source))
    for column in PLAIN_METADATA_COLUMNS:
        if column == "ticker":
            continue
        if column in source.columns:
            calc[column] = source[column]
        else:
            calc[column] = None

    calc["ema_20_available"] = calc["ema_20"].notna()
    calc["ema_50_available"] = calc["ema_50"].notna()
    calc["ema_200_available"] = calc["ema_200"].notna()
    calc["macd_available"] = calc[
        ["macd", "macd_signal", "macd_histogram"]
    ].notna().all(axis=1)
    calc["adx_available"] = calc[
        ["adx_14", "plus_di_14", "minus_di_14"]
    ].notna().all(axis=1)
    calc["rsi_available"] = calc["rsi_14"].notna()
    calc["stochastic_available"] = calc[
        ["stochastic_k_9", "stochastic_d_6"]
    ].notna().all(axis=1)
    calc["atr_available"] = (
        calc["atr_14"].notna() & calc["atr_14"].gt(0)
    )
    calc["weekly_ema_20_available"] = calc["weekly_ema_20"].notna()
    calc["weekly_ema_50_available"] = calc["weekly_ema_50"].notna()
    calc["volume_comparison_available"] = calc["daily_volume_ratio"].notna()
    calc["standard_history_features_available"] = calc[
        [
            "ema_20",
            "ema_50",
            "ema_200",
            "weekly_ema_20",
            "weekly_ema_50",
            "daily_volume_ratio",
        ]
    ].notna().all(axis=1)
    calc["standard_history_features_available"] &= calc[
        [
            "macd_available",
            "adx_available",
            "rsi_available",
            "stochastic_available",
            "atr_available",
        ]
    ].all(axis=1)

    calc["daily_structure_description"] = "Insufficient stock history"
    young_ready = calc["ema_20"].notna()
    calc.loc[young_ready, "daily_structure_description"] = np.where(
        calc.loc[young_ready, "close"].gt(calc.loc[young_ready, "ema_20"]),
        "Price is above its available short-term trend",
        "Price is below its available short-term trend",
    )
    established = calc[["ema_50", "ema_200"]].notna().all(axis=1)
    strong = (
        established
        & calc["close"].gt(calc["ema_20"])
        & calc["ema_20"].gt(calc["ema_50"])
        & calc["ema_50"].gt(calc["ema_200"])
    )
    positive = (
        established
        & ~strong
        & calc["close"].gt(calc["ema_50"])
        & calc["ema_50"].gt(calc["ema_200"])
    )
    calc.loc[established, "daily_structure_description"] = (
        "Long-term upward structure is absent"
    )
    calc.loc[positive, "daily_structure_description"] = (
        "Long-term structure is positive but not fully aligned"
    )
    calc.loc[strong, "daily_structure_description"] = (
        "Short-, medium- and long-term structure is aligned upward"
    )

    calc["participation_description"] = "Volume comparison unavailable"
    volume_ready = calc["daily_volume_ratio"].notna()
    calc.loc[volume_ready, "participation_description"] = "Volume is below its prior average"
    calc.loc[
        volume_ready & calc["daily_volume_ratio"].ge(1.0),
        "participation_description",
    ] = "Volume is at or above its prior average"
    calc.loc[
        volume_ready & calc["daily_volume_ratio"].ge(1.5),
        "participation_description",
    ] = "Volume is materially above its prior average"

    calc["extension_description"] = "Extension cannot yet be measured"
    extension_ready = calc["distance_from_ema_50_atr"].notna()
    calc.loc[extension_ready, "extension_description"] = "Price extension is controlled"
    calc.loc[
        extension_ready & calc["distance_from_ema_50_atr"].gt(3.0),
        "extension_description",
    ] = "Price is extended above its medium-term trend"
    calc.loc[
        extension_ready & calc["distance_from_ema_50_atr"].gt(5.0),
        "extension_description",
    ] = "Price is extremely extended; exhaustion risk is elevated"

    calc.attrs["feature_contract"] = (
        "Every feature uses completed data through previous_completed_session."
    )
    return calc


def _barrier_outcome(
    *,
    highs: np.ndarray,
    lows: np.ndarray,
    upper: float,
    lower: float,
) -> str:
    for high_value, low_value in zip(highs, lows):
        upper_hit = bool(high_value >= upper)
        lower_hit = bool(low_value <= lower)
        if upper_hit and lower_hit:
            return "Both targets touched in the same session; order unknown"
        if upper_hit:
            return "Upward target reached first"
        if lower_hit:
            return "Downside threshold reached first"
    return "Neither target reached within the review window"


def attach_forward_outcomes(
    features: pd.DataFrame,
    *,
    contract: OutcomeContract | None = None,
) -> pd.DataFrame:
    """Join hypothetical entry and forward outcomes without changing features."""
    if features is None or features.empty:
        return pd.DataFrame()
    settings = contract or OutcomeContract()
    output = features.copy()
    count = len(output)
    opens = output["open"].to_numpy(dtype=float)
    highs = output["high"].to_numpy(dtype=float)
    lows = output["low"].to_numpy(dtype=float)
    closes = output["close"].to_numpy(dtype=float)
    atr = output["atr_14"].to_numpy(dtype=float)
    dates = pd.DatetimeIndex(output.index)

    output["hypothetical_entry_session"] = None
    output["hypothetical_entry_open"] = np.nan
    for horizon in settings.horizons:
        output[f"outcome_{horizon}_sessions_complete"] = False
        output[f"outcome_{horizon}_end_date"] = None
        output[f"forward_{horizon}_session_return_pct"] = np.nan
        output[f"forward_{horizon}_session_mfe_pct"] = np.nan
        output[f"forward_{horizon}_session_mae_pct"] = np.nan
    output[f"barrier_outcome_{settings.barrier_horizon}_sessions"] = (
        "Future window incomplete"
    )

    entry_date_column = output.columns.get_loc("hypothetical_entry_session")
    entry_open_column = output.columns.get_loc("hypothetical_entry_open")
    barrier_column = output.columns.get_loc(
        f"barrier_outcome_{settings.barrier_horizon}_sessions"
    )

    for position in range(count):
        entry_position = position + 1
        if entry_position >= count or not np.isfinite(opens[entry_position]):
            continue
        entry_price = float(opens[entry_position])
        if entry_price <= 0:
            continue
        output.iat[entry_position - 1, entry_date_column] = (
            dates[entry_position].strftime("%Y-%m-%d")
        )
        output.iat[entry_position - 1, entry_open_column] = entry_price

        for horizon in settings.horizons:
            end_position = position + horizon
            if end_position >= count:
                continue
            future_slice = slice(entry_position, end_position + 1)
            future_highs = highs[future_slice]
            future_lows = lows[future_slice]
            if (
                len(future_highs) != horizon
                or not np.isfinite(future_highs).all()
                or not np.isfinite(future_lows).all()
                or not np.isfinite(closes[end_position])
            ):
                continue

            output.at[
                output.index[position],
                f"outcome_{horizon}_sessions_complete",
            ] = True
            output.at[
                output.index[position],
                f"outcome_{horizon}_end_date",
            ] = dates[end_position].strftime("%Y-%m-%d")
            output.at[
                output.index[position],
                f"forward_{horizon}_session_return_pct",
            ] = (closes[end_position] / entry_price - 1.0) * 100.0
            output.at[
                output.index[position],
                f"forward_{horizon}_session_mfe_pct",
            ] = (float(np.max(future_highs)) / entry_price - 1.0) * 100.0
            output.at[
                output.index[position],
                f"forward_{horizon}_session_mae_pct",
            ] = (float(np.min(future_lows)) / entry_price - 1.0) * 100.0

            if horizon == settings.barrier_horizon:
                output.iat[position, barrier_column] = (
                    "ATR unavailable for the foundation"
                )
                if np.isfinite(atr[position]) and atr[position] > 0:
                    output.iat[position, barrier_column] = _barrier_outcome(
                        highs=future_highs,
                        lows=future_lows,
                        upper=(
                            entry_price
                            + settings.upper_atr_multiple * atr[position]
                        ),
                        lower=(
                            entry_price
                            - settings.lower_atr_multiple * atr[position]
                        ),
                    )

    output["research_outcome_contract"] = (
        "Entry=session immediately after the daily foundation, at its open; "
        f"barrier window={settings.barrier_horizon} "
        f"sessions; upper={settings.upper_atr_multiple:g} ATR; "
        f"lower={settings.lower_atr_multiple:g} ATR"
    )
    output.attrs.update(features.attrs)
    output.attrs["outcome_contract"] = output[
        "research_outcome_contract"
    ].iloc[0]
    return output


def build_symbol_research_panel(
    frame: pd.DataFrame,
    *,
    ticker: str,
    contract: OutcomeContract | None = None,
) -> pd.DataFrame:
    features = calculate_daily_features(frame, ticker=ticker)
    return attach_forward_outcomes(features, contract=contract)


def assign_chronological_split(
    panel: pd.DataFrame,
    *,
    training_end: str | pd.Timestamp,
    calibration_end: str | pd.Timestamp,
    longest_horizon: int = 20,
) -> pd.DataFrame:
    """Assign chronological splits and purge labels crossing a boundary."""
    if panel is None or panel.empty:
        return pd.DataFrame()
    output = panel.copy()
    dates = pd.to_datetime(output["previous_completed_session"], errors="coerce")
    outcome_end = pd.to_datetime(
        output[f"outcome_{longest_horizon}_end_date"],
        errors="coerce",
    )
    train_boundary = pd.Timestamp(training_end)
    calibration_boundary = pd.Timestamp(calibration_end)
    if calibration_boundary <= train_boundary:
        raise ValueError("Calibration end must be after training end.")

    output["research_split"] = "Holdout"
    training_mask = dates.le(train_boundary)
    calibration_mask = dates.gt(train_boundary) & dates.le(calibration_boundary)
    output.loc[training_mask, "research_split"] = "Training"
    output.loc[calibration_mask, "research_split"] = "Calibration"

    output["split_eligible"] = True
    output["split_exclusion_reason"] = ""
    train_leak = training_mask & (
        outcome_end.isna() | outcome_end.gt(train_boundary)
    )
    calibration_leak = calibration_mask & (
        outcome_end.isna() | outcome_end.gt(calibration_boundary)
    )
    incomplete_holdout = dates.gt(calibration_boundary) & outcome_end.isna()
    output.loc[train_leak, "split_eligible"] = False
    output.loc[train_leak, "split_exclusion_reason"] = (
        "Forward outcome crosses the training boundary"
    )
    output.loc[calibration_leak, "split_eligible"] = False
    output.loc[calibration_leak, "split_exclusion_reason"] = (
        "Forward outcome crosses the calibration boundary"
    )
    output.loc[incomplete_holdout, "split_eligible"] = False
    output.loc[incomplete_holdout, "split_exclusion_reason"] = (
        "Forward outcome is not yet complete"
    )
    return output


def read_panel(path: str | Path) -> pd.DataFrame:
    source = Path(path)
    if source.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(source)
    return pd.read_csv(source, low_memory=False)
