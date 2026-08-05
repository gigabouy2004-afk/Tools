#!/usr/bin/env python3
"""Scalable CSV backtest matrix for the V19 D-1 qualification engine.

The runner downloads each symbol once, evaluates the Cartesian product of
symbols and execution dates without using the D candle for qualification, and
adds the adjusted D opening gap as a post-signal backtest outcome.
"""

from __future__ import annotations

import argparse
import csv
import math
import os
import random
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable, Iterable, Sequence

import numpy as np
import pandas as pd

import Live_Scanner_v19 as v19


SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_VERSION = "19.1.0"
DATE_HEADER_WORDS = {"DATE", "DATES", "EXECUTION DATE", "EXECUTION_DATE", "BACKTEST DATE", "BACKTEST_DATE", "D"}
DATE_INPUT_SUFFIXES = {".csv", ".txt", ".xlsx"}


CSV_PREFIX_COLUMNS = [
    "Pair_Index",
    "Symbol_Input_Index",
    "Date_Input_Index",
    "Symbol",
    "Execution_Date_D",
    "D1_Date",
    "D2_Date",
    "D1_Close",
    "D_Open",
    "D_Open_Gap_Return",
    "D_Open_Positive",
    "Outcome_Status",
    "Price_Basis",
]

_PREFIX_DUPLICATES = {"Symbol", "Execution_Date_D", "D1_Date", "D2_Date", "D1_Close"}
CSV_COLUMNS = (
    CSV_PREFIX_COLUMNS
    + [column for column in v19.TECHNICAL_COLUMNS if column not in _PREFIX_DUPLICATES]
    + [
        "Download_Attempts",
        "Provider_Failure",
        "Error_Code",
        "Error_Message",
    ]
)


HistoryFetcher = Callable[[str, date, date, float], pd.DataFrame]


@dataclass(frozen=True)
class MatrixConfig:
    input_source: str
    date_source: str
    raw_code_count: int
    duplicate_code_count: int
    raw_date_count: int
    duplicate_date_count: int
    output_path: Path
    overwrite: bool
    workers: int
    max_attempts: int
    request_timeout: float
    request_interval: float
    retry_base_seconds: float
    history_lookback_days: int
    progress_every: int
    stoch_zone_low: float
    stoch_zone_high: float
    calendar_symbol: str
    date_range_start: date | None = None
    date_range_end: date | None = None


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="V19 code/date matrix backtester with D-opening CSV outcomes.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    code_group = parser.add_mutually_exclusive_group(required=True)
    code_group.add_argument("-c", "--codes", nargs="+", help="Codes separated by spaces and/or commas.")
    code_group.add_argument("-i", "--input-file", help="CSV, TXT or XLSX whose first column contains codes.")

    date_group = parser.add_mutually_exclusive_group(required=True)
    date_group.add_argument("-d", "--dates", nargs="+", help="Execution dates D in YYYY-MM-DD form.")
    date_group.add_argument("--dates-file", help="CSV, TXT or XLSX whose first column contains dates.")
    date_group.add_argument(
        "--date-range",
        nargs=2,
        metavar=("START", "END"),
        help="Inclusive range resolved to trading dates with --calendar-symbol.",
    )

    parser.add_argument("-o", "--output", required=True, help="Output CSV path.")
    parser.add_argument("--overwrite", action="store_true", help="Allow replacement of an existing output CSV.")
    parser.add_argument("--calendar-symbol", default="SPY", help="Trading calendar proxy for --date-range.")
    parser.add_argument("--workers", type=int, default=v19.DEFAULT_WORKERS)
    parser.add_argument("--max-attempts", type=int, default=v19.DEFAULT_MAX_ATTEMPTS)
    parser.add_argument("--request-timeout", type=float, default=v19.DEFAULT_REQUEST_TIMEOUT)
    parser.add_argument("--request-interval", type=float, default=v19.DEFAULT_REQUEST_INTERVAL)
    parser.add_argument("--retry-base-seconds", type=float, default=v19.DEFAULT_RETRY_BASE_SECONDS)
    parser.add_argument("--history-lookback-days", type=int, default=v19.DEFAULT_HISTORY_LOOKBACK_DAYS)
    parser.add_argument("--progress-every", type=int, default=v19.DEFAULT_PROGRESS_EVERY)
    parser.add_argument("--stoch-zone-low", type=float, default=v19.DEFAULT_STOCH_ZONE_LOW)
    parser.add_argument("--stoch-zone-high", type=float, default=v19.DEFAULT_STOCH_ZONE_HIGH)
    return parser


def _split_values(values: Iterable[object]) -> list[str]:
    items: list[str] = []
    for value in values:
        text = str(value).strip()
        if not text:
            continue
        normalized = text.replace(";", ",").replace("\t", ",")
        for comma_part in normalized.split(","):
            items.extend(part for part in comma_part.split() if part)
    return items


def _parse_date_value(value: object) -> date:
    if isinstance(value, datetime):
        parsed = value.date()
    elif isinstance(value, date):
        parsed = value
    else:
        text = str(value).strip()
        try:
            parsed = datetime.strptime(text, "%Y-%m-%d").date()
        except ValueError as exc:
            raise v19.PreflightError(f"Invalid date '{text}'; expected YYYY-MM-DD.") from exc
    if parsed > date.today():
        raise v19.PreflightError(f"Backtest date cannot be in the future: {parsed}")
    return parsed


def read_dates_from_file(input_path: Path) -> list[object]:
    if not input_path.exists() or not input_path.is_file():
        raise v19.PreflightError(f"Dates file does not exist or is not a file: {input_path}")
    suffix = input_path.suffix.lower()
    if suffix not in DATE_INPUT_SUFFIXES:
        raise v19.PreflightError(f"Unsupported dates file type '{suffix}'. Use CSV, TXT or XLSX.")
    try:
        if suffix == ".xlsx":
            frame = pd.read_excel(input_path, sheet_name=0, header=None)
            values = frame.iloc[:, 0].tolist() if not frame.empty else []
        elif suffix == ".csv":
            frame = pd.read_csv(input_path, header=None)
            values = frame.iloc[:, 0].tolist() if not frame.empty else []
        else:
            values = input_path.read_text(encoding="utf-8-sig").splitlines()
    except Exception as exc:
        raise v19.PreflightError(f"Unable to read dates file '{input_path}': {exc}") from exc
    if values and str(values[0]).strip().upper() in DATE_HEADER_WORDS:
        values = values[1:]
    return values


def normalize_dates(raw_values: Sequence[object]) -> tuple[list[date], int]:
    parsed: list[date] = []
    seen: set[date] = set()
    duplicates = 0
    for value in raw_values:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            continue
        parsed_date = _parse_date_value(value)
        if parsed_date in seen:
            duplicates += 1
            continue
        seen.add(parsed_date)
        parsed.append(parsed_date)
    if not parsed:
        raise v19.PreflightError("No valid backtest dates were supplied.")
    return parsed, duplicates


def _validate_output_path(output_path: Path, inputs: Sequence[Path], overwrite: bool) -> None:
    if output_path.suffix.lower() != ".csv":
        raise v19.PreflightError(f"Output file must use the .csv extension: {output_path}")
    if output_path in inputs:
        raise v19.PreflightError("Input and output files must be different paths.")
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        raise v19.PreflightError(f"Unable to create output directory '{output_path.parent}': {exc}") from exc
    if output_path.exists():
        if not output_path.is_file():
            raise v19.PreflightError(f"Output path is not a file: {output_path}")
        if not overwrite:
            raise v19.PreflightError(f"Output already exists. Use --overwrite to replace it: {output_path}")
        try:
            with output_path.open("r+b"):
                pass
        except OSError as exc:
            raise v19.PreflightError(f"Existing output is not writable: {output_path}: {exc}") from exc
    try:
        handle, probe_name = tempfile.mkstemp(prefix=".v19_matrix_probe_", dir=output_path.parent)
        os.close(handle)
        Path(probe_name).unlink()
    except Exception as exc:
        raise v19.PreflightError(f"Output directory is not writable: {output_path.parent}: {exc}") from exc


def preflight(argv: Sequence[str] | None = None) -> tuple[MatrixConfig, list[str], list[date]]:
    args = build_argument_parser().parse_args(argv)
    input_paths: list[Path] = []

    if args.input_file:
        code_path = Path(args.input_file).expanduser().resolve()
        input_paths.append(code_path)
        raw_codes = v19.read_symbols_from_file(code_path)
        input_source = str(code_path)
    else:
        raw_codes = _split_values(args.codes or [])
        input_source = "CLI codes"
    symbols, duplicate_code_count = v19.normalize_and_deduplicate_symbols(raw_codes)

    dates: list[date] = []
    raw_date_count = 0
    duplicate_date_count = 0
    range_start: date | None = None
    range_end: date | None = None
    if args.dates_file:
        date_path = Path(args.dates_file).expanduser().resolve()
        input_paths.append(date_path)
        raw_dates = read_dates_from_file(date_path)
        raw_date_count = len(raw_dates)
        dates, duplicate_date_count = normalize_dates(raw_dates)
        date_source = str(date_path)
    elif args.dates:
        raw_dates = _split_values(args.dates)
        raw_date_count = len(raw_dates)
        dates, duplicate_date_count = normalize_dates(raw_dates)
        date_source = "CLI dates"
    else:
        assert args.date_range is not None
        range_start = _parse_date_value(args.date_range[0])
        range_end = _parse_date_value(args.date_range[1])
        if range_start > range_end:
            raise v19.PreflightError("--date-range START must not be after END.")
        date_source = f"Trading-date range {range_start} to {range_end} via {args.calendar_symbol.upper()}"

    if not 1 <= args.workers <= 32:
        raise v19.PreflightError("--workers must be between 1 and 32.")
    if not 1 <= args.max_attempts <= 10:
        raise v19.PreflightError("--max-attempts must be between 1 and 10.")
    if not 1.0 <= args.request_timeout <= 120.0:
        raise v19.PreflightError("--request-timeout must be between 1 and 120 seconds.")
    if not 0.0 <= args.request_interval <= 60.0:
        raise v19.PreflightError("--request-interval must be between 0 and 60 seconds.")
    if not 0.0 <= args.retry_base_seconds <= 120.0:
        raise v19.PreflightError("--retry-base-seconds must be between 0 and 120 seconds.")
    if args.history_lookback_days < 500:
        raise v19.PreflightError("--history-lookback-days must be at least 500.")
    if args.progress_every < 1:
        raise v19.PreflightError("--progress-every must be at least 1.")
    if not 0.0 <= args.stoch_zone_low < args.stoch_zone_high <= 100.0:
        raise v19.PreflightError("Stochastic zone must satisfy 0 <= low < high <= 100.")

    calendar_symbol = args.calendar_symbol.strip().upper()
    v19.normalize_and_deduplicate_symbols([calendar_symbol])
    output_path = Path(args.output).expanduser().resolve()
    _validate_output_path(output_path, input_paths, args.overwrite)

    config = MatrixConfig(
        input_source=input_source,
        date_source=date_source,
        raw_code_count=len(raw_codes),
        duplicate_code_count=duplicate_code_count,
        raw_date_count=raw_date_count,
        duplicate_date_count=duplicate_date_count,
        output_path=output_path,
        overwrite=args.overwrite,
        workers=args.workers,
        max_attempts=args.max_attempts,
        request_timeout=args.request_timeout,
        request_interval=args.request_interval,
        retry_base_seconds=args.retry_base_seconds,
        history_lookback_days=args.history_lookback_days,
        progress_every=args.progress_every,
        stoch_zone_low=args.stoch_zone_low,
        stoch_zone_high=args.stoch_zone_high,
        calendar_symbol=calendar_symbol,
        date_range_start=range_start,
        date_range_end=range_end,
    )
    return config, symbols, dates


def normalize_full_history(frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None or frame.empty:
        raise v19.DataExtractionError("NO_PRICE_DATA", "No daily history was returned.")
    data = frame.copy()
    if isinstance(data.columns, pd.MultiIndex):
        flattened: list[str] = []
        for column in data.columns:
            parts = [str(part) for part in column if part not in (None, "")]
            required_part = next((part for part in parts if part in {"Open", "High", "Low", "Close", "Volume"}), None)
            flattened.append(required_part or parts[-1])
        data.columns = flattened
    required = ["Open", "High", "Low", "Close"]
    missing = [column for column in required if column not in data.columns]
    if missing:
        raise v19.DataExtractionError("MISSING_REQUIRED_COLUMN", f"Missing daily columns: {', '.join(missing)}")
    try:
        index = pd.DatetimeIndex(pd.to_datetime(data.index))
    except Exception as exc:
        raise v19.DataExtractionError("INVALID_DATE_INDEX", f"Unable to parse daily dates: {exc}") from exc
    if index.tz is not None:
        index = index.tz_localize(None)
    data.index = index.normalize()
    data = data[~data.index.duplicated(keep="last")].sort_index()
    for column in required + (["Volume"] if "Volume" in data.columns else []):
        data[column] = pd.to_numeric(data[column], errors="coerce")
    data = data.dropna(subset=["High", "Low", "Close"])
    if data.empty:
        raise v19.DataExtractionError("NO_PRICE_DATA", "Daily history contained no valid OHLC rows.")
    return data


def _download_with_retries(
    symbol: str,
    start_date: date,
    end_date: date,
    config: MatrixConfig,
    fetcher: HistoryFetcher,
    guard: v19.ProviderGuard,
    stats: v19.RetryStatistics,
    *,
    sleep_fn: Callable[[float], None] = time.sleep,
    jitter_fn: Callable[[float, float], float] = random.uniform,
) -> tuple[pd.DataFrame, int]:
    last_error: v19.DataExtractionError | None = None
    for attempt in range(1, config.max_attempts + 1):
        guard.wait_for_request_slot()
        stats.record_attempt()
        try:
            frame = fetcher(symbol, start_date, end_date, config.request_timeout)
            return normalize_full_history(frame), attempt
        except v19.DataExtractionError as exc:
            current = exc
        except Exception as exc:
            current = v19.classify_provider_exception(exc)
        last_error = current
        if current.code == "YF_RATE_LIMIT":
            stats.record_rate_limit()
            guard.pause_after_rate_limit(min(60.0, config.retry_base_seconds * (2**attempt)))
        if not current.retriable or attempt >= config.max_attempts:
            break
        stats.record_retry()
        delay = config.retry_base_seconds * (2 ** (attempt - 1)) + jitter_fn(0.0, max(0.1, config.retry_base_seconds))
        sleep_fn(delay)
    assert last_error is not None
    raise last_error


def resolve_range_dates(
    config: MatrixConfig,
    fetcher: HistoryFetcher,
    guard: v19.ProviderGuard,
    stats: v19.RetryStatistics,
) -> list[date]:
    assert config.date_range_start is not None and config.date_range_end is not None
    calendar, _ = _download_with_retries(
        config.calendar_symbol,
        config.date_range_start,
        config.date_range_end + timedelta(days=1),
        config,
        fetcher,
        guard,
        stats,
    )
    dates = [
        timestamp.date()
        for timestamp in calendar.index
        if config.date_range_start <= timestamp.date() <= config.date_range_end
    ]
    if not dates:
        raise v19.PreflightError(
            f"No trading dates were found in {config.date_range_start} to {config.date_range_end} "
            f"using {config.calendar_symbol}."
        )
    return dates


def _runtime_config(execution_date: date, config: MatrixConfig) -> v19.RuntimeConfig:
    return v19.RuntimeConfig(
        execution_date=execution_date,
        explicit_execution_date=True,
        input_source=config.input_source,
        raw_input_count=config.raw_code_count,
        duplicate_count=config.duplicate_code_count,
        output_path=config.output_path,
        overwrite=config.overwrite,
        workers=config.workers,
        max_attempts=config.max_attempts,
        request_timeout=config.request_timeout,
        request_interval=config.request_interval,
        retry_base_seconds=config.retry_base_seconds,
        history_lookback_days=config.history_lookback_days,
        progress_every=config.progress_every,
        stoch_zone_low=config.stoch_zone_low,
        stoch_zone_high=config.stoch_zone_high,
    )


def _outcome_values(full_history: pd.DataFrame, execution_date: date, d1_close: float | None) -> dict:
    timestamp = pd.Timestamp(execution_date)
    if timestamp not in full_history.index:
        return {
            "D_Open": None,
            "D_Open_Gap_Return": None,
            "D_Open_Positive": None,
            "Outcome_Status": "D_CANDLE_UNAVAILABLE",
        }
    d_open = float(full_history.loc[timestamp, "Open"])
    if not math.isfinite(d_open) or d_open <= 0:
        return {
            "D_Open": None,
            "D_Open_Gap_Return": None,
            "D_Open_Positive": None,
            "Outcome_Status": "D_OPEN_INVALID",
        }
    if d1_close is None or not math.isfinite(d1_close) or d1_close <= 0:
        prior = full_history[full_history.index < timestamp]
        if prior.empty:
            return {
                "D_Open": d_open,
                "D_Open_Gap_Return": None,
                "D_Open_Positive": None,
                "Outcome_Status": "D1_CLOSE_UNAVAILABLE",
            }
        d1_close = float(prior["Close"].iloc[-1])
        if not math.isfinite(d1_close) or d1_close <= 0:
            return {
                "D_Open": d_open,
                "D_Open_Gap_Return": None,
                "D_Open_Positive": None,
                "Outcome_Status": "D1_CLOSE_UNAVAILABLE",
            }
    gap = (d_open / d1_close) - 1.0
    return {
        "D_Open": d_open,
        "D_Open_Gap_Return": gap,
        "D_Open_Positive": bool(gap > 0.0),
        "Outcome_Status": "VALID",
    }


def _invalid_row(
    symbol_index: int,
    date_index: int,
    symbol: str,
    execution_date: date,
    attempts: int,
    error: v19.DataExtractionError,
    full_history: pd.DataFrame | None = None,
    pair_index: int | None = None,
) -> dict:
    if pair_index is None:
        pair_index = symbol_index * 1_000_000 + date_index
    row = {column: None for column in CSV_COLUMNS}
    row.update(
        {
            "Pair_Index": pair_index,
            "Symbol_Input_Index": symbol_index,
            "Date_Input_Index": date_index,
            "Symbol": symbol,
            "Execution_Date_D": execution_date,
            "Qualification_Status": v19.STATUS_INVALID,
            "Qualification_Tier": "NOT_AVAILABLE",
            "Momentum_Return_Band": "NOT_AVAILABLE",
            "Stochastic_Calculated": False,
            "Stochastic_Status": "NOT_EVALUATED",
            "Data_Integrity_Flag": "INVALID",
            "Price_Basis": "AUTO_ADJUSTED",
            "Download_Attempts": attempts,
            "Provider_Failure": error.provider_failure,
            "Error_Code": error.code,
            "Error_Message": str(error),
        }
    )
    if full_history is not None:
        prior = full_history[full_history.index < pd.Timestamp(execution_date)]
        if not prior.empty:
            row["D1_Date"] = prior.index[-1].date()
            row["D1_Close"] = float(prior["Close"].iloc[-1])
        row.update(_outcome_values(full_history, execution_date, None))
    else:
        row["Outcome_Status"] = "HISTORY_UNAVAILABLE"
    return row


def evaluate_dates_from_history(
    symbol_index: int,
    symbol: str,
    dates: Sequence[date],
    full_history: pd.DataFrame,
    config: MatrixConfig,
    attempts: int,
) -> list[dict]:
    rows: list[dict] = []
    for date_index, execution_date in enumerate(dates):
        pair_index = symbol_index * len(dates) + date_index
        start_date = execution_date - timedelta(days=config.history_lookback_days)
        window = full_history[
            (full_history.index.date >= start_date) & (full_history.index.date < execution_date)
        ]
        try:
            completed = v19.normalize_completed_history(window, execution_date)
            result = v19.calculate_symbol_result(
                pair_index,
                symbol,
                completed,
                _runtime_config(execution_date, config),
                attempts,
            )
            assert result.technical is not None
            technical = result.technical
            row = {column: None for column in CSV_COLUMNS}
            row.update(technical)
            row.update(
                {
                    "Pair_Index": pair_index,
                    "Symbol_Input_Index": symbol_index,
                    "Date_Input_Index": date_index,
                    "Symbol": symbol,
                    "Execution_Date_D": execution_date,
                    "D1_Date": technical["D1_Date"],
                    "D2_Date": technical["D2_Date"],
                    "D1_Close": technical["D1_Close"],
                    "Price_Basis": "AUTO_ADJUSTED",
                    "Download_Attempts": attempts,
                    "Provider_Failure": False,
                    "Error_Code": None,
                    "Error_Message": None,
                }
            )
            row.update(_outcome_values(full_history, execution_date, float(technical["D1_Close"])))
            rows.append(row)
        except v19.DataExtractionError as exc:
            rows.append(
                _invalid_row(
                    symbol_index,
                    date_index,
                    symbol,
                    execution_date,
                    attempts,
                    exc,
                    full_history,
                    pair_index,
                )
            )
    return rows


def _download_and_evaluate_symbol(
    item: tuple[int, str],
    dates: Sequence[date],
    config: MatrixConfig,
    fetcher: HistoryFetcher,
    guard: v19.ProviderGuard,
    stats: v19.RetryStatistics,
) -> tuple[int, str, list[dict]]:
    symbol_index, symbol = item
    start_date = min(dates) - timedelta(days=config.history_lookback_days)
    end_date = max(dates) + timedelta(days=1)
    attempts = 0
    try:
        history, attempts = _download_with_retries(symbol, start_date, end_date, config, fetcher, guard, stats)
        rows = evaluate_dates_from_history(symbol_index, symbol, dates, history, config, attempts)
    except v19.DataExtractionError as exc:
        attempts = attempts or config.max_attempts if exc.retriable else attempts or 1
        rows = [
            _invalid_row(
                symbol_index,
                date_index,
                symbol,
                execution_date,
                attempts,
                exc,
                pair_index=symbol_index * len(dates) + date_index,
            )
            for date_index, execution_date in enumerate(dates)
        ]
    except Exception as exc:
        error = v19.DataExtractionError("INTERNAL_WORKER_ERROR", f"Unexpected worker failure: {exc}")
        rows = [
            _invalid_row(
                symbol_index,
                date_index,
                symbol,
                execution_date,
                attempts or 1,
                error,
                pair_index=symbol_index * len(dates) + date_index,
            )
            for date_index, execution_date in enumerate(dates)
        ]
    return symbol_index, symbol, rows


def _blank_summary(symbol_count: int, date_count: int) -> dict:
    return {
        "symbols": symbol_count,
        "dates": date_count,
        "pairs": symbol_count * date_count,
        "rows_written": 0,
        "tier_1": 0,
        "tier_2": 0,
        "rejected": 0,
        "invalid": 0,
        "valid_outcomes": 0,
        "positive_all": 0,
        "qualified_with_outcome": 0,
        "positive_qualified": 0,
        "provider_failures": 0,
    }


def _record_summary(summary: dict, row: dict) -> None:
    summary["rows_written"] += 1
    status = row.get("Qualification_Status")
    if status == v19.STATUS_TIER_1:
        summary["tier_1"] += 1
    elif status == v19.STATUS_TIER_2:
        summary["tier_2"] += 1
    elif status == v19.STATUS_REJECT:
        summary["rejected"] += 1
    else:
        summary["invalid"] += 1
    if bool(row.get("Provider_Failure")):
        summary["provider_failures"] += 1
    if row.get("Outcome_Status") == "VALID":
        summary["valid_outcomes"] += 1
        if row.get("D_Open_Positive") is True:
            summary["positive_all"] += 1
        if status in {v19.STATUS_TIER_1, v19.STATUS_TIER_2}:
            summary["qualified_with_outcome"] += 1
            if row.get("D_Open_Positive") is True:
                summary["positive_qualified"] += 1


def run_matrix(
    symbols: Sequence[str],
    dates: Sequence[date],
    config: MatrixConfig,
    *,
    fetcher: HistoryFetcher = v19.yahoo_history_fetcher,
    guard: v19.ProviderGuard | None = None,
    stats: v19.RetryStatistics | None = None,
) -> tuple[dict, v19.RetryStatistics]:
    shared_guard = guard or v19.ProviderGuard(config.request_interval)
    shared_stats = stats or v19.RetryStatistics()
    summary = _blank_summary(len(symbols), len(dates))
    temp_handle, temp_name = tempfile.mkstemp(prefix=".v19_matrix_", suffix=".csv", dir=config.output_path.parent)
    os.close(temp_handle)
    temp_path = Path(temp_name)
    started = time.monotonic()
    try:
        with temp_path.open("w", newline="", encoding="utf-8-sig") as output_handle:
            writer = csv.DictWriter(output_handle, fieldnames=CSV_COLUMNS, extrasaction="ignore")
            writer.writeheader()
            with ThreadPoolExecutor(max_workers=config.workers, thread_name_prefix="v19-matrix") as executor:
                iterator = executor.map(
                    lambda item: _download_and_evaluate_symbol(
                        item, dates, config, fetcher, shared_guard, shared_stats
                    ),
                    enumerate(symbols),
                )
                for completed, (_, symbol, rows) in enumerate(iterator, start=1):
                    for row in rows:
                        writer.writerow(row)
                        _record_summary(summary, row)
                    if completed == 1 or completed % config.progress_every == 0 or completed == len(symbols):
                        print(
                            f"[PROGRESS] symbols={completed}/{len(symbols)} rows={summary['rows_written']}/{summary['pairs']} "
                            f"tier1={summary['tier_1']} tier2={summary['tier_2']} rejected={summary['rejected']} "
                            f"invalid={summary['invalid']} latest={symbol} elapsed={time.monotonic()-started:.1f}s",
                            flush=True,
                        )
        os.replace(temp_path, config.output_path)
    except Exception:
        try:
            temp_path.unlink(missing_ok=True)
        except Exception:
            pass
        raise
    return summary, shared_stats


def _rate(numerator: int, denominator: int) -> str:
    return "N/A" if denominator == 0 else f"{numerator / denominator:.2%}"


def print_initial(config: MatrixConfig, symbols: Sequence[str], dates: Sequence[date]) -> None:
    print("=" * 92)
    print(f"V19 CSV Backtest Matrix ({SCRIPT_VERSION})")
    print("=" * 92)
    print(f"Script                      : {SCRIPT_PATH.name}")
    print(f"Codes / Dates / Combinations: {len(symbols)} / {len(dates)} / {len(symbols) * len(dates):,}")
    print(f"Code Source                 : {config.input_source}")
    print(f"Date Source                 : {config.date_source}")
    print(f"Date Range                  : {min(dates)} to {max(dates)}")
    print(f"Qualification Data          : completed candles strictly before each D")
    print(f"Backtest Outcome            : adjusted D Open versus adjusted D-1 Close")
    print(f"Yahoo Downloads             : once per symbol across the full date span")
    print(f"Workers / Request Interval  : {config.workers} / {config.request_interval:.2f}s")
    print(f"Output CSV                  : {config.output_path}")
    print("-" * 92, flush=True)


def print_final(config: MatrixConfig, summary: dict, stats: v19.RetryStatistics, elapsed: float) -> None:
    print("-" * 92)
    print("V19 CSV MATRIX SUMMARY")
    print("-" * 92)
    print(f"Rows Written                : {summary['rows_written']:,}")
    print(f"Tier 1 / Tier 2             : {summary['tier_1']:,} / {summary['tier_2']:,}")
    print(f"Rejected / Invalid          : {summary['rejected']:,} / {summary['invalid']:,}")
    print(f"All Positive D Opens        : {summary['positive_all']:,}/{summary['valid_outcomes']:,} ({_rate(summary['positive_all'], summary['valid_outcomes'])})")
    print(f"Qualified Positive D Opens  : {summary['positive_qualified']:,}/{summary['qualified_with_outcome']:,} ({_rate(summary['positive_qualified'], summary['qualified_with_outcome'])})")
    print(f"Provider Failures           : {summary['provider_failures']:,}")
    print(f"Requests / Retries / 429s   : {stats.request_attempts} / {stats.retries} / {stats.rate_limit_events}")
    print(f"Elapsed                     : {elapsed:.1f}s")
    print(f"Output CSV                  : {config.output_path}")
    print("=" * 92, flush=True)


def main(argv: Sequence[str] | None = None) -> int:
    try:
        config, symbols, dates = preflight(argv)
    except v19.PreflightError as exc:
        print(f"[PRE-FLIGHT ERROR] {exc}", file=sys.stderr)
        return 2

    guard = v19.ProviderGuard(config.request_interval)
    stats = v19.RetryStatistics()
    cache_directory = v19.temporary_yfinance_cache()
    started = time.monotonic()
    try:
        if config.date_range_start is not None:
            dates = resolve_range_dates(config, v19.yahoo_history_fetcher, guard, stats)
        print_initial(config, symbols, dates)
        summary, stats = run_matrix(symbols, dates, config, guard=guard, stats=stats)
        print_final(config, summary, stats, time.monotonic() - started)
        return 0 if summary["provider_failures"] == 0 else 1
    except (v19.PreflightError, v19.DataExtractionError) as exc:
        print(f"[BACKTEST ERROR] {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"[FATAL ERROR] {type(exc).__name__}: {exc}", file=sys.stderr)
        return 3
    finally:
        v19.cleanup_yfinance_cache(cache_directory)


if __name__ == "__main__":
    raise SystemExit(main())
