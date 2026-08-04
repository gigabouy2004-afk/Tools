from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class HistoricalSlice:
    as_of: pd.Timestamp
    frame: pd.DataFrame


def normalize_cutoff(index: pd.Index, cutoff: pd.Timestamp) -> pd.Timestamp:
    normalized = cutoff
    if index.tz is None and normalized.tzinfo is not None:
        normalized = normalized.tz_localize(None)
    if index.tz is not None and normalized.tzinfo is None:
        normalized = normalized.tz_localize(index.tz)
    return normalized


def slice_as_of(frame: pd.DataFrame, cutoff: pd.Timestamp) -> HistoricalSlice:
    if frame.empty:
        raise ValueError("Cannot slice an empty price frame.")
    cutoff_cmp = normalize_cutoff(frame.index, cutoff)
    sliced = frame.loc[frame.index <= cutoff_cmp].copy()
    if sliced.empty:
        raise ValueError(f"No rows available on or before cutoff {cutoff}.")
    return HistoricalSlice(as_of=pd.Timestamp(sliced.index[-1]), frame=sliced)


def forward_return(frame: pd.DataFrame, cutoff: pd.Timestamp, bars: int) -> float | None:
    if frame.empty or "Close" not in frame.columns:
        return None
    cutoff_cmp = normalize_cutoff(frame.index, cutoff)
    eligible_positions = [idx for idx, timestamp in enumerate(frame.index) if timestamp <= cutoff_cmp]
    if not eligible_positions:
        return None
    start_position = eligible_positions[-1]
    end_position = start_position + bars
    if end_position >= len(frame):
        return None
    start_close = float(frame["Close"].iloc[start_position])
    end_close = float(frame["Close"].iloc[end_position])
    if start_close == 0:
        return None
    return round(((end_close - start_close) / start_close) * 100.0, 4)


def forward_worst_low_return(frame: pd.DataFrame, cutoff: pd.Timestamp, bars: int) -> float | None:
    return _forward_extreme_return(frame, cutoff, bars, "Low", min)


def forward_best_high_return(frame: pd.DataFrame, cutoff: pd.Timestamp, bars: int) -> float | None:
    return _forward_extreme_return(frame, cutoff, bars, "High", max)


def _forward_extreme_return(frame: pd.DataFrame, cutoff: pd.Timestamp, bars: int, column: str, reducer) -> float | None:
    if frame.empty or "Close" not in frame.columns or column not in frame.columns:
        return None
    cutoff_cmp = normalize_cutoff(frame.index, cutoff)
    eligible_positions = [idx for idx, timestamp in enumerate(frame.index) if timestamp <= cutoff_cmp]
    if not eligible_positions:
        return None
    start_position = eligible_positions[-1]
    end_position = start_position + bars
    if end_position >= len(frame):
        return None
    start_close = float(frame["Close"].iloc[start_position])
    if start_close == 0:
        return None
    future_values = [float(value) for value in frame[column].iloc[start_position + 1 : end_position + 1]]
    if not future_values:
        return None
    extreme_value = reducer(future_values)
    return round(((extreme_value - start_close) / start_close) * 100.0, 4)
