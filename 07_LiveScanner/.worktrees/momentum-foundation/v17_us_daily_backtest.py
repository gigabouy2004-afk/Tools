#!/usr/bin/env python
"""
Vectorized, auditable multi-year U.S. daily-baseline replay for V17.

The production scanner evaluates one historical prefix at a time. That is useful
for a small convenience backtest, but recalculates every indicator hundreds of
times per symbol and is not practical for the full NYSE/Nasdaq universe.
This harness calculates the carried-forward V16 daily predicates once per symbol,
preserves the production five-session non-overlap rule, and writes batch
checkpoints so a long universe run can be resumed safely.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import Live_Scanner_v17 as engine


DEFAULT_US_MASTER = (
    r"D:\Tools\00_StockCodeMaster\02_Stock"
    r"\22-07-US_Common_Stocks_Master_Library.csv"
)
DEFAULT_OUTPUT_DIR = Path("output") / "V17_D1_Backtest_5Y"
TRADE_COLUMNS = [
    "ticker",
    "market",
    "security_name",
    "sector",
    "signal_date",
    "signal_close",
    "entry_date",
    "entry_price",
    "exit_date",
    "exit_price",
    "holding_sessions",
    "return_pct",
    "output_signal",
    "setup_type",
    "v17_daily_primary_regime_passed",
    "v17_daily_momentum_state",
    "v17_daily_quality_score",
    "ema20",
    "ema50",
    "ema200",
    "weekly_close",
    "weekly_ema_20",
    "weekly_ema_50",
    "macd",
    "macd_signal",
    "macd_hist",
    "macd_hist_change_1",
    "adx",
    "adx_plus_di",
    "adx_minus_di",
    "adx_change_5",
    "rsi",
    "atr",
    "stoch_k",
    "stoch_d",
    "volume",
    "volume_avg_20",
    "effective_buy_stoch_max",
    "relative_volume_ratio",
    "volume_history_percentile",
    "average_daily_turnover_20",
    "ema50_distance_atr",
    "ema50_slope_20_pct",
    "ema200_slope_60_pct",
    "return_20d_pct",
    "return_60d_pct",
    "return_120d_pct",
    "price_pct_prior_52w_high",
    "extreme_extension_review",
]
COVERAGE_COLUMNS = [
    "ticker",
    "market",
    "security_name",
    "sector",
    "status",
    "reason",
    "history_rows",
    "first_history_date",
    "last_history_date",
    "measured_sessions",
    "buy_trades",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run a vectorized multi-year V17 completed-D1 reference replay "
            "over NYSE/Nasdaq common stocks."
        )
    )
    parser.add_argument("--us-master", default=DEFAULT_US_MASTER)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--years", type=int, default=5)
    parser.add_argument(
        "--history-period",
        default="8y",
        help="Yahoo history fetched; must include indicator warm-up before measured years.",
    )
    parser.add_argument(
        "--evaluation-windows",
        default="1,2,3,5",
        help=(
            "Comma-separated trailing-year windows summarized from the same "
            "replay (default: 1,2,3,5)."
        ),
    )
    parser.add_argument("--holding-period", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--batch-pause", type=float, default=0.35)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--preset", choices=sorted(engine.PRESETS), default="balanced")
    parser.add_argument("--max-symbols", type=int, default=0)
    parser.add_argument("--symbols", nargs="*", default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--no-retry",
        action="store_true",
        help="Do not retry symbols missing from their first batch download.",
    )
    return parser.parse_args()


def clean_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def optional_round(value: object, digits: int = 4):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return round(number, digits) if math.isfinite(number) else None


def load_master(path: str) -> pd.DataFrame:
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"Master file not found: {source}")
    frame = pd.read_csv(source, dtype=str, low_memory=False)
    if "Ticker" not in frame.columns:
        raise ValueError(f"Ticker column is missing from {source}")

    output = pd.DataFrame()
    output["ticker"] = (
        frame["Ticker"].map(engine.normalize_ticker_symbol).astype(str)
    )
    output["market"] = "US"
    output["security_name"] = frame.get(
        "Security Name", pd.Series("", index=frame.index)
    ).map(clean_text)
    output["sector"] = frame.get(
        "Sector", pd.Series("", index=frame.index)
    ).map(clean_text)
    output["listing_exchange"] = frame.get(
        "Listing Exchange", pd.Series("", index=frame.index)
    ).map(clean_text)
    output["source_file"] = str(source.resolve())
    output["is_etf"] = frame.get(
        "ETF", pd.Series("N", index=frame.index)
    ).map(clean_text)
    output = output.loc[output["ticker"].ne("")].copy()
    output = output.loc[
        output["listing_exchange"].str.upper().isin({"NYSE", "NASDAQ"})
        & ~output["is_etf"].str.upper().eq("Y")
        & ~output["ticker"].str.endswith((".NS", ".BO"), na=False)
    ].copy()
    return output


def load_universe(args: argparse.Namespace) -> pd.DataFrame:
    universe = load_master(args.us_master)
    universe = universe.drop_duplicates(subset=["ticker"], keep="first")
    if args.symbols:
        requested = {
            engine.normalize_ticker_symbol(symbol)
            for symbol in args.symbols
            if clean_text(symbol)
            and engine.normalize_ticker_symbol(symbol)
            and not engine.normalize_ticker_symbol(symbol).endswith(
                (".NS", ".BO")
            )
        }
        universe = universe.loc[universe["ticker"].isin(requested)].copy()
        absent = sorted(requested.difference(set(universe["ticker"])))
        if absent:
            raise ValueError(
                "Requested symbols are not verified as NYSE/Nasdaq non-ETF "
                "equities in the supplied master: "
                + ", ".join(absent)
            )
    if args.max_symbols > 0:
        universe = universe.iloc[: args.max_symbols].copy()
    return universe.reset_index(drop=True)


def download_batch(
    symbols: list[str],
    period: str,
    timeout: float,
) -> pd.DataFrame:
    if not symbols:
        return pd.DataFrame()
    return engine.yf.download(
        tickers=symbols,
        period=period,
        interval="1d",
        group_by="ticker",
        auto_adjust=True,
        actions=False,
        prepost=False,
        threads=True,
        progress=False,
        timeout=timeout,
        multi_level_index=True,
    )


def extract_symbol_frame(downloaded: pd.DataFrame, symbol: str) -> pd.DataFrame:
    if downloaded is None or downloaded.empty:
        return pd.DataFrame()

    frame: pd.DataFrame | pd.Series
    if isinstance(downloaded.columns, pd.MultiIndex):
        level_zero = downloaded.columns.get_level_values(0)
        level_one = downloaded.columns.get_level_values(1)
        if symbol in level_zero:
            frame = downloaded[symbol]
        elif symbol in level_one:
            frame = downloaded.xs(symbol, axis=1, level=1)
        else:
            return pd.DataFrame()
    else:
        frame = downloaded.copy()

    if isinstance(frame, pd.Series):
        frame = frame.to_frame()
    frame = frame.copy()
    frame.columns = [str(column).strip().lower() for column in frame.columns]
    required = ["open", "high", "low", "close", "volume"]
    if not set(required).issubset(frame.columns):
        return pd.DataFrame()
    frame = frame[required].apply(pd.to_numeric, errors="coerce")
    frame = frame.dropna(subset=["open", "high", "low", "close"])
    frame["volume"] = frame["volume"].fillna(0.0)
    if frame.empty:
        return frame
    index = pd.DatetimeIndex(frame.index)
    if index.tz is not None:
        index = index.tz_localize(None)
    frame.index = index.normalize()
    frame = frame.loc[~frame.index.duplicated(keep="last")].sort_index()
    return frame


def combine_downloads(
    primary: pd.DataFrame,
    retry: pd.DataFrame,
    symbols: list[str],
) -> dict[str, pd.DataFrame]:
    frames: dict[str, pd.DataFrame] = {}
    for symbol in symbols:
        frame = extract_symbol_frame(primary, symbol)
        if frame.empty:
            frame = extract_symbol_frame(retry, symbol)
        frames[symbol] = frame
    return frames


def prior_percentiles(
    values: pd.Series,
    needed: pd.Series,
    lookback: int,
) -> pd.Series:
    result = pd.Series(np.nan, index=values.index, dtype=float)
    array = pd.to_numeric(values, errors="coerce").to_numpy(dtype=float)
    positions = np.flatnonzero(needed.fillna(False).to_numpy(dtype=bool))
    for position in positions:
        start = max(0, position - lookback)
        prior = array[start:position]
        prior = prior[np.isfinite(prior)]
        if prior.size:
            result.iat[position] = float(
                np.count_nonzero(prior <= array[position]) / prior.size * 100.0
            )
    return result


def completed_weekly_values(frame: pd.DataFrame) -> pd.DataFrame:
    weekly = (
        frame.resample("W-FRI")
        .agg(
            {
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum",
            }
        )
        .dropna(subset=["close"])
    )
    weekly["weekly_ema_20"] = engine.ta.trend.ema_indicator(
        weekly["close"], window=engine.WEEKLY_EMA_FAST
    )
    weekly["weekly_ema_50"] = engine.ta.trend.ema_indicator(
        weekly["close"], window=engine.WEEKLY_EMA_SLOW
    )

    dates = pd.Series(frame.index, index=frame.index)
    weekday = dates.dt.weekday
    week_end = dates + pd.to_timedelta((4 - weekday) % 7, unit="D")
    next_date = dates.shift(-1)
    week_complete = next_date.gt(week_end)
    usable_week = week_end.where(week_complete, week_end - pd.Timedelta(days=7))

    lookup = weekly[["close", "weekly_ema_20", "weekly_ema_50"]].rename(
        columns={"close": "weekly_close"}
    )
    aligned = lookup.reindex(pd.DatetimeIndex(usable_week))
    aligned.index = frame.index
    return aligned


def replay_symbol(
    frame: pd.DataFrame,
    metadata: dict,
    config: dict,
    analysis_start: pd.Timestamp,
    holding_period: int,
) -> tuple[list[dict], dict]:
    ticker = metadata["ticker"]
    market = metadata["market"]
    coverage = {
        "ticker": ticker,
        "market": market,
        "security_name": metadata.get("security_name", ""),
        "sector": metadata.get("sector", ""),
        "status": "PROCESSED",
        "reason": "",
        "history_rows": int(len(frame)),
        "first_history_date": (
            frame.index.min().strftime("%Y-%m-%d") if not frame.empty else ""
        ),
        "last_history_date": (
            frame.index.max().strftime("%Y-%m-%d") if not frame.empty else ""
        ),
        "measured_sessions": 0,
        "buy_trades": 0,
    }
    if frame.empty:
        coverage.update(status="NO_DATA", reason="No Yahoo OHLCV rows returned")
        return [], coverage
    if len(frame) < engine.EMA_SLOW_PERIOD + holding_period + 1:
        coverage.update(
            status="INSUFFICIENT_HISTORY",
            reason=(
                f"Needs at least {engine.EMA_SLOW_PERIOD + holding_period + 1} "
                "daily rows"
            ),
        )
        return [], coverage

    measured = frame.index >= analysis_start
    coverage["measured_sessions"] = int(measured.sum())
    if not measured.any():
        coverage.update(
            status="NO_MEASURED_PERIOD",
            reason=f"No rows on or after {analysis_start:%Y-%m-%d}",
        )
        return [], coverage

    calc = frame.copy()
    calc["ema20"] = engine.ta.trend.ema_indicator(calc["close"], window=20)
    calc["ema50"] = engine.ta.trend.ema_indicator(
        calc["close"], window=engine.EMA_FAST_PERIOD
    )
    calc["ema200"] = engine.ta.trend.ema_indicator(
        calc["close"], window=engine.EMA_SLOW_PERIOD
    )
    macd = engine.ta.trend.MACD(
        calc["close"],
        window_fast=engine.MACD_FAST_PERIOD,
        window_slow=engine.MACD_SLOW_PERIOD,
        window_sign=engine.MACD_SIGNAL_PERIOD,
    )
    calc["macd"] = macd.macd()
    calc["macd_signal"] = macd.macd_signal()
    calc["macd_hist"] = macd.macd_diff()
    calc["macd_hist_change_1"] = calc["macd_hist"].diff()
    calc["atr"] = engine.ta.volatility.average_true_range(
        calc["high"],
        calc["low"],
        calc["close"],
        window=engine.ATR_PERIOD,
    )
    calc["adx"] = engine.ta.trend.adx(
        calc["high"],
        calc["low"],
        calc["close"],
        window=engine.ADX_PERIOD,
    )
    calc["adx_plus_di"] = engine.ta.trend.adx_pos(
        calc["high"],
        calc["low"],
        calc["close"],
        window=engine.ADX_PERIOD,
    )
    calc["adx_minus_di"] = engine.ta.trend.adx_neg(
        calc["high"],
        calc["low"],
        calc["close"],
        window=engine.ADX_PERIOD,
    )
    calc["rsi"] = engine.ta.momentum.rsi(
        calc["close"],
        window=engine.RSI_PERIOD,
    )
    calc["stoch_k"] = engine.ta.momentum.stoch(
        calc["high"],
        calc["low"],
        calc["close"],
        window=engine.STOCH_K_PERIOD,
    )
    calc["stoch_d"] = engine.ta.momentum.stoch_signal(
        calc["high"],
        calc["low"],
        calc["close"],
        window=engine.STOCH_K_PERIOD,
        smooth_window=engine.STOCH_D_PERIOD,
    )
    calc = calc.join(completed_weekly_values(calc))

    volume_average = (
        calc["volume"]
        .shift(1)
        .rolling(engine.VOLUME_LOOKBACK, min_periods=engine.VOLUME_LOOKBACK)
        .mean()
    )
    volume_ratio = calc["volume"].div(volume_average.where(volume_average.gt(0)))
    history_needed = volume_ratio.ge(
        float(config.get("current_volume_min_ratio", 0.60))
    ) & volume_ratio.lt(
        float(config.get("continuation_volume_min_ratio", 0.80))
    )
    volume_percentile = prior_percentiles(
        calc["volume"],
        history_needed,
        int(config.get("historical_context_lookback", 252)),
    )
    volume_supportive = volume_ratio.ge(
        float(config.get("continuation_volume_min_ratio", 0.80))
    ) | (
        volume_ratio.ge(float(config.get("current_volume_min_ratio", 0.60)))
        & volume_percentile.ge(
            float(config.get("volume_history_min_percentile", 60.0))
        )
    )
    volume_confirmed = volume_ratio.ge(
        float(config.get("volume_mult", 1.20))
    )

    price = calc["close"]
    atr = calc["atr"]
    distance_atr = (price - calc["ema50"]).div(atr.where(atr.gt(0)))
    ema20_gap_atr = (price - calc["ema20"]).div(atr.where(atr.gt(0)))
    macro = price.gt(calc["ema50"]) & calc["ema50"].gt(calc["ema200"])
    weekly = calc["weekly_close"].gt(calc["weekly_ema_20"]) & calc[
        "weekly_ema_20"
    ].gt(calc["weekly_ema_50"])

    positive_macd = (
        calc["macd"].gt(calc["macd_signal"])
        & calc["macd"].gt(0)
        & calc["macd_signal"].gt(0)
        & calc["macd_hist"].gt(0)
    )
    ema50_slope_20 = calc["ema50"].pct_change(20) * 100.0
    ema200_slope_60 = calc["ema200"].pct_change(60) * 100.0
    return_20d = price.pct_change(20) * 100.0
    return_60d = price.pct_change(60) * 100.0
    return_120d = price.pct_change(120) * 100.0
    prior_52w_high = (
        calc["high"].shift(1).rolling(252, min_periods=1).max()
    )
    price_pct_prior_52w_high = price.div(
        prior_52w_high.where(prior_52w_high.gt(0))
    ) * 100.0
    adx_change_5 = calc["adx"] - calc["adx"].shift(5)
    daily_primary_regime = macro & weekly & positive_macd
    daily_quality_score = (
        ema50_slope_20.gt(0).astype(int)
        + ema200_slope_60.ge(0).astype(int)
        + return_20d.gt(0).astype(int)
        + return_60d.gt(0).astype(int)
        + return_120d.gt(0).astype(int)
        + calc["adx_plus_di"].gt(calc["adx_minus_di"]).astype(int)
        + calc["adx"].ge(engine.V16_ADX_CONFIRMATION_MIN).astype(int)
        + price_pct_prior_52w_high.ge(
            engine.V16_NEAR_52W_HIGH_MIN_PCT
        ).astype(int)
        + volume_ratio.ge(
            engine.V16_BUY_VOLUME_CONFIRMATION_RATIO
        ).astype(int)
        + distance_atr.le(engine.V16_SAFE_ENTRY_MAX_ATR).astype(int)
    )
    daily_momentum_state = pd.Series("NONE", index=calc.index, dtype=object)
    daily_momentum_state.loc[
        daily_primary_regime & daily_quality_score.lt(
            engine.V16_DEVELOPING_MIN_SCORE
        )
    ] = "WEAK"
    daily_momentum_state.loc[
        daily_primary_regime
        & daily_quality_score.ge(engine.V16_DEVELOPING_MIN_SCORE)
    ] = "DEVELOPING"
    daily_momentum_state.loc[
        daily_primary_regime
        & daily_quality_score.ge(engine.V16_LEADER_MIN_SCORE)
    ] = "LEADER"
    bull_crossover = (
        calc["macd"].shift(1).le(calc["macd_signal"].shift(1))
        & calc["macd"].gt(calc["macd_signal"])
        & calc["macd"].gt(0)
        & calc["macd_signal"].gt(0)
    )
    hist_expanding = (
        calc["macd_hist"].shift(2).lt(calc["macd_hist"].shift(1))
        & calc["macd_hist"].shift(1).lt(calc["macd_hist"])
        & calc["macd_hist"].shift(1).gt(0)
        & calc["macd_hist"].gt(0)
    )
    current_positive = price.pct_change().gt(0)
    previous_positive = price.pct_change().shift(1).gt(0)

    stoch_cross = (
        calc["stoch_k"].shift(1).le(calc["stoch_d"].shift(1))
        & calc["stoch_k"].gt(calc["stoch_d"])
    )
    stoch_oversold = float(config.get("stoch_oversold", 30.0))
    stoch_recovery = (
        calc["stoch_k"]
        .rolling(
            max(2, int(config.get("stoch_recent_lookback", 3))),
            min_periods=max(2, int(config.get("stoch_recent_lookback", 3))),
        )
        .min()
        .lt(stoch_oversold)
        & stoch_cross
        & calc["stoch_k"].le(
            stoch_oversold + float(config.get("stoch_recovery_buffer", 10.0))
        )
    )
    ema20_support = (
        calc["ema20"].gt(calc["ema50"])
        & ema20_gap_atr.ge(0)
        & ema20_gap_atr.le(float(config.get("ema20_max_gap_atr", 0.50)))
    )
    stoch_mid_cross = (
        stoch_cross
        & calc["stoch_k"].ge(float(config.get("stoch_mid_low", 40.0)))
        & calc["stoch_k"].le(float(config.get("stoch_mid_high", 65.0)))
    )
    shallow_pullback = ema20_support & stoch_mid_cross
    safe_price = distance_atr.le(float(config.get("atr_safe_mult", 2.20)))
    gate = macro & weekly

    branch_one = gate & positive_macd & safe_price & stoch_recovery
    branch_two = (
        gate
        & ~branch_one
        & positive_macd
        & safe_price
        & shallow_pullback
    )
    early = (
        gate
        & bull_crossover
        & calc["macd_hist"].gt(0)
        & calc["stoch_k"].gt(calc["stoch_d"])
        & current_positive
        & volume_supportive
    )
    continuation = (
        gate
        & positive_macd
        & hist_expanding
        & current_positive
        & volume_supportive
    )
    branch_three = ~branch_one & ~branch_two & early
    branch_four = ~branch_one & ~branch_two & ~branch_three & continuation

    buy_one = branch_one & volume_confirmed
    buy_two = branch_two & volume_confirmed
    candidate = buy_one | buy_two | branch_three | branch_four
    output_signal = pd.Series("", index=calc.index, dtype=object)
    setup_type = pd.Series("", index=calc.index, dtype=object)
    output_signal.loc[buy_one] = "Buy_Pullback_Oversold_Recovery"
    setup_type.loc[buy_one] = "PULLBACK_OVERSOLD_RECOVERY"
    output_signal.loc[buy_two] = "Buy_EMA20_Midrange_Recovery"
    setup_type.loc[buy_two] = "PULLBACK_EMA20_MIDRANGE_RECOVERY"
    output_signal.loc[branch_three] = "Buy_Early_Momentum"
    setup_type.loc[branch_three] = "EARLY_MOMENTUM_POSITIVE_PHASE"
    output_signal.loc[branch_four] = "Buy_Momentum_Extension"
    setup_type.loc[branch_four] = np.where(
        distance_atr.loc[branch_four].gt(float(config.get("atr_ext_mult", 3.0))),
        "MOMENTUM_CONTINUATION_EXTENDED",
        "MOMENTUM_CONTINUATION",
    )

    base_stoch_limit = max(0.0, float(config.get("buy_stoch_max", 80.0)))
    effective_stoch_limit = pd.Series(
        base_stoch_limit, index=calc.index, dtype=float
    )
    effective_stoch_limit.loc[
        candidate
        & previous_positive
        & output_signal.eq("Buy_Early_Momentum")
    ] = max(
        base_stoch_limit,
        float(config.get("prior_positive_early_stoch_max", 90.0)),
    )
    effective_stoch_limit.loc[
        candidate
        & previous_positive
        & output_signal.eq("Buy_Momentum_Extension")
    ] = max(
        base_stoch_limit,
        float(config.get("prior_positive_continuation_stoch_max", 100.0)),
    )
    if base_stoch_limit > 0:
        candidate &= calc["stoch_k"].le(effective_stoch_limit) & calc[
            "stoch_d"
        ].le(effective_stoch_limit)

    average_turnover = volume_average * price
    if market == "US":
        candidate &= average_turnover.ge(
            float(config.get("us_min_adv20_turnover", 1_000_000.0))
        )

    valid_core = calc[
        [
            "ema20",
            "ema50",
            "ema200",
            "macd",
            "macd_signal",
            "macd_hist",
            "atr",
            "stoch_k",
            "stoch_d",
            "weekly_close",
            "weekly_ema_20",
            "weekly_ema_50",
        ]
    ].notna().all(axis=1)
    positions = np.flatnonzero(
        (
            candidate
            & valid_core
            & calc.index.to_series().ge(analysis_start)
        ).to_numpy(dtype=bool)
    )

    trades: list[dict] = []
    next_eligible_position = engine.EMA_SLOW_PERIOD
    for signal_position in positions:
        if signal_position < next_eligible_position:
            continue
        entry_position = signal_position + 1
        exit_position = signal_position + holding_period
        if exit_position >= len(calc):
            break
        entry_price = float(calc["open"].iat[entry_position])
        exit_price = float(calc["close"].iat[exit_position])
        if not (
            math.isfinite(entry_price)
            and math.isfinite(exit_price)
            and entry_price > 0
        ):
            continue
        extreme_review = bool(
            distance_atr.iat[signal_position]
            > float(config.get("extreme_extension_review_atr", 5.0))
        )
        selected_setup = clean_text(setup_type.iat[signal_position])
        if extreme_review:
            selected_setup = f"{selected_setup}_EXTENDED_REVIEW"
        trades.append(
            {
                "ticker": ticker,
                "market": market,
                "security_name": metadata.get("security_name", ""),
                "sector": metadata.get("sector", ""),
                "signal_date": calc.index[signal_position].strftime("%Y-%m-%d"),
                "signal_close": round(float(price.iat[signal_position]), 4),
                "entry_date": calc.index[entry_position].strftime("%Y-%m-%d"),
                "entry_price": round(entry_price, 4),
                "exit_date": calc.index[exit_position].strftime("%Y-%m-%d"),
                "exit_price": round(exit_price, 4),
                "holding_sessions": holding_period,
                "return_pct": round((exit_price / entry_price - 1.0) * 100.0, 4),
                "output_signal": clean_text(output_signal.iat[signal_position]),
                "setup_type": selected_setup,
                "v17_daily_primary_regime_passed": bool(
                    daily_primary_regime.iat[signal_position]
                ),
                "v17_daily_momentum_state": clean_text(
                    daily_momentum_state.iat[signal_position]
                ),
                "v17_daily_quality_score": int(
                    daily_quality_score.iat[signal_position]
                ),
                "ema20": optional_round(
                    calc["ema20"].iat[signal_position]
                ),
                "ema50": optional_round(
                    calc["ema50"].iat[signal_position]
                ),
                "ema200": optional_round(
                    calc["ema200"].iat[signal_position]
                ),
                "weekly_close": optional_round(
                    calc["weekly_close"].iat[signal_position]
                ),
                "weekly_ema_20": optional_round(
                    calc["weekly_ema_20"].iat[signal_position]
                ),
                "weekly_ema_50": optional_round(
                    calc["weekly_ema_50"].iat[signal_position]
                ),
                "macd": optional_round(calc["macd"].iat[signal_position]),
                "macd_signal": optional_round(
                    calc["macd_signal"].iat[signal_position]
                ),
                "macd_hist": optional_round(
                    calc["macd_hist"].iat[signal_position]
                ),
                "macd_hist_change_1": optional_round(
                    calc["macd_hist_change_1"].iat[signal_position]
                ),
                "adx": optional_round(calc["adx"].iat[signal_position]),
                "adx_plus_di": optional_round(
                    calc["adx_plus_di"].iat[signal_position]
                ),
                "adx_minus_di": optional_round(
                    calc["adx_minus_di"].iat[signal_position]
                ),
                "adx_change_5": optional_round(
                    adx_change_5.iat[signal_position]
                ),
                "rsi": optional_round(calc["rsi"].iat[signal_position]),
                "atr": optional_round(calc["atr"].iat[signal_position]),
                "stoch_k": round(float(calc["stoch_k"].iat[signal_position]), 4),
                "stoch_d": round(float(calc["stoch_d"].iat[signal_position]), 4),
                "volume": optional_round(
                    calc["volume"].iat[signal_position],
                    2,
                ),
                "volume_avg_20": optional_round(
                    volume_average.iat[signal_position],
                    2,
                ),
                "effective_buy_stoch_max": round(
                    float(effective_stoch_limit.iat[signal_position]), 4
                ),
                "relative_volume_ratio": round(
                    float(volume_ratio.iat[signal_position]), 4
                ),
                "volume_history_percentile": (
                    round(float(volume_percentile.iat[signal_position]), 4)
                    if pd.notna(volume_percentile.iat[signal_position])
                    else None
                ),
                "average_daily_turnover_20": round(
                    float(average_turnover.iat[signal_position]), 2
                ),
                "ema50_distance_atr": round(
                    float(distance_atr.iat[signal_position]), 4
                ),
                "ema50_slope_20_pct": optional_round(
                    ema50_slope_20.iat[signal_position]
                ),
                "ema200_slope_60_pct": optional_round(
                    ema200_slope_60.iat[signal_position]
                ),
                "return_20d_pct": optional_round(
                    return_20d.iat[signal_position]
                ),
                "return_60d_pct": optional_round(
                    return_60d.iat[signal_position]
                ),
                "return_120d_pct": optional_round(
                    return_120d.iat[signal_position]
                ),
                "price_pct_prior_52w_high": optional_round(
                    price_pct_prior_52w_high.iat[signal_position]
                ),
                "extreme_extension_review": extreme_review,
            }
        )
        # Production sets idx=exit_idx, allowing a new signal on the old exit day.
        next_eligible_position = exit_position

    coverage["buy_trades"] = len(trades)
    return trades, coverage


def atomic_csv(frame: pd.DataFrame, path: Path, columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    frame.reindex(columns=columns).to_csv(temporary, index=False)
    os.replace(temporary, path)


def read_parts(parts_dir: Path, prefix: str, columns: list[str]) -> pd.DataFrame:
    frames = []
    for path in sorted(parts_dir.glob(f"{prefix}_*.csv")):
        try:
            frames.append(pd.read_csv(path, low_memory=False))
        except pd.errors.EmptyDataError:
            continue
    if not frames:
        return pd.DataFrame(columns=columns)
    return pd.concat(frames, ignore_index=True).reindex(columns=columns)


def finite_or_zero(value: float | int | None) -> float:
    if value is None or not math.isfinite(float(value)):
        return 0.0
    return float(value)


def performance_slice(frame: pd.DataFrame) -> dict:
    returns = pd.to_numeric(frame.get("return_pct"), errors="coerce").dropna()
    wins = returns.loc[returns.gt(0)]
    losses = returns.loc[returns.lt(0)]
    return {
        "trades": int(len(returns)),
        "winning_trades": int(len(wins)),
        "losing_trades": int(len(losses)),
        "flat_trades": int(returns.eq(0).sum()),
        "win_rate_pct": (
            round(float(returns.gt(0).mean() * 100.0), 2)
            if len(returns)
            else 0.0
        ),
        "average_return_pct": (
            round(float(returns.mean()), 4) if len(returns) else 0.0
        ),
        "median_return_pct": (
            round(float(returns.median()), 4) if len(returns) else 0.0
        ),
        "profit_factor": (
            round(float(wins.sum() / abs(losses.sum())), 4)
            if len(losses) and losses.sum() != 0
            else None
        ),
    }


def grouped_performance(frame: pd.DataFrame, field: str) -> dict:
    if frame.empty or field not in frame:
        return {}
    return {
        str(key): performance_slice(group)
        for key, group in frame.groupby(field, dropna=False)
    }


def trailing_window_performance(
    trades: pd.DataFrame,
    windows: str,
) -> dict:
    """Summarize several trailing periods from one identical replay."""
    parsed_windows = sorted({
        int(value.strip())
        for value in str(windows or "").split(",")
        if value.strip() and int(value.strip()) > 0
    })
    if trades.empty:
        return {f"{years}y": {"trades": 0} for years in parsed_windows}

    signal_dates = pd.to_datetime(trades["signal_date"], errors="coerce")
    today = pd.Timestamp.now().normalize()
    output = {}
    for years in parsed_windows:
        subset = trades.loc[
            signal_dates >= today - pd.DateOffset(years=years)
        ].copy()
        metrics = performance_slice(subset)
        metrics["symbols"] = (
            int(subset["ticker"].nunique()) if not subset.empty else 0
        )
        metrics["by_signal"] = grouped_performance(
            subset,
            "output_signal",
        )
        output[f"{years}y"] = metrics
    return output


def audit_backtest_outputs(
    trades: pd.DataFrame,
    coverage: pd.DataFrame,
    universe: pd.DataFrame,
    analysis_start: pd.Timestamp,
    holding_period: int,
) -> dict:
    required_trade_fields = [
        "ticker",
        "signal_date",
        "entry_date",
        "entry_price",
        "exit_date",
        "exit_price",
        "return_pct",
        "output_signal",
    ]
    missing_values = (
        int(trades[required_trade_fields].isna().any(axis=1).sum())
        if not trades.empty
        else 0
    )
    duplicate_signals = (
        int(trades.duplicated(["ticker", "signal_date"]).sum())
        if not trades.empty
        else 0
    )

    if trades.empty:
        return_error = 0.0
        overlap_count = 0
        invalid_date_order = 0
        outside_window = 0
        holding_mismatches = 0
    else:
        entry_price = pd.to_numeric(trades["entry_price"], errors="coerce")
        exit_price = pd.to_numeric(trades["exit_price"], errors="coerce")
        stated_return = pd.to_numeric(trades["return_pct"], errors="coerce")
        recalculated = (exit_price / entry_price - 1.0) * 100.0
        return_error = float((recalculated - stated_return).abs().max())

        dates = trades[["ticker", "signal_date", "entry_date", "exit_date"]].copy()
        for field in ("signal_date", "entry_date", "exit_date"):
            dates[field] = pd.to_datetime(dates[field], errors="coerce")
        invalid_date_order = int(
            (
                dates["signal_date"].ge(dates["entry_date"])
                | dates["entry_date"].gt(dates["exit_date"])
            ).sum()
        )
        outside_window = int(dates["signal_date"].lt(analysis_start).sum())
        ordered = dates.sort_values(["ticker", "signal_date"], kind="stable")
        previous_exit = ordered.groupby("ticker")["exit_date"].shift(1)
        overlap_count = int(ordered["signal_date"].lt(previous_exit).sum())
        holding_mismatches = int(
            pd.to_numeric(
                trades["holding_sessions"], errors="coerce"
            ).ne(holding_period).sum()
        )

    coverage_trade_total = int(
        pd.to_numeric(coverage.get("buy_trades"), errors="coerce").fillna(0).sum()
    )
    checks = {
        "universe_rows_match": int(len(coverage)) == int(len(universe)),
        "coverage_trade_total_matches": coverage_trade_total == int(len(trades)),
        "no_duplicate_ticker_signal_dates": duplicate_signals == 0,
        "no_same_ticker_trade_overlap": overlap_count == 0,
        "valid_signal_entry_exit_order": invalid_date_order == 0,
        "all_signals_within_measured_window": outside_window == 0,
        "holding_period_matches": holding_mismatches == 0,
        "required_trade_fields_complete": missing_values == 0,
        "return_recalculation_within_0_01_pct": return_error <= 0.01,
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "universe_rows": int(len(universe)),
        "coverage_rows": int(len(coverage)),
        "coverage_trade_total": coverage_trade_total,
        "trade_rows": int(len(trades)),
        "duplicate_ticker_signal_dates": duplicate_signals,
        "same_ticker_trade_overlaps": overlap_count,
        "invalid_signal_entry_exit_order": invalid_date_order,
        "signals_outside_measured_window": outside_window,
        "holding_period_mismatches": holding_mismatches,
        "rows_missing_required_trade_fields": missing_values,
        "maximum_return_recalculation_error_pct": round(return_error, 6),
    }


def calculate_summary(
    trades: pd.DataFrame,
    coverage: pd.DataFrame,
    universe: pd.DataFrame,
    args: argparse.Namespace,
    started_at: datetime,
) -> dict:
    returns = pd.to_numeric(trades.get("return_pct"), errors="coerce").dropna()
    wins = returns.loc[returns.gt(0)]
    losses = returns.loc[returns.lt(0)]

    if trades.empty:
        cohort_drawdown = 0.0
    else:
        cohort_returns = (
            trades.assign(
                return_pct=pd.to_numeric(trades["return_pct"], errors="coerce")
            )
            .groupby("entry_date", dropna=True)["return_pct"]
            .mean()
            .dropna()
            .sort_index()
        )
        cohort_equity = (1.0 + cohort_returns / 100.0).cumprod()
        cohort_drawdown = finite_or_zero(
            ((cohort_equity / cohort_equity.cummax()) - 1.0).min() * 100.0
        )

    ticker_stats = []
    if not trades.empty:
        grouped = trades.groupby("ticker")["return_pct"].agg(
            trades="count", average_return_pct="mean", win_rate=lambda x: (x > 0).mean()
        )
        grouped = grouped.loc[grouped["trades"].ge(3)].sort_values(
            ["average_return_pct", "trades"], ascending=[False, False]
        )
        ticker_stats = [
            {
                "ticker": ticker,
                "trades": int(row["trades"]),
                "average_return_pct": round(float(row["average_return_pct"]), 4),
                "win_rate_pct": round(float(row["win_rate"]) * 100.0, 2),
            }
            for ticker, row in grouped.head(20).iterrows()
        ]

    completed_at = datetime.now(timezone.utc)
    coverage_counts = Counter(coverage.get("status", pd.Series(dtype=str)).fillna(""))
    requested_analysis_start = (
        pd.Timestamp.now().normalize() - pd.DateOffset(years=args.years)
    )
    by_market = grouped_performance(trades, "market")
    by_signal = grouped_performance(trades, "output_signal")
    net_cost_scenarios = {}
    if len(returns):
        for cost_bps in (10, 20, 50):
            cost_pct = cost_bps / 100.0
            net = returns - cost_pct
            net_wins = net.loc[net.gt(0)]
            net_losses = net.loc[net.lt(0)]
            net_cost_scenarios[f"{cost_bps}_bps_round_trip"] = {
                "average_net_return_pct": round(float(net.mean()), 4),
                "net_win_rate_pct": round(float(net.gt(0).mean() * 100.0), 2),
                "net_profit_factor": (
                    round(float(net_wins.sum() / abs(net_losses.sum())), 4)
                    if len(net_losses) and net_losses.sum() != 0
                    else None
                ),
            }
    winsorized_mean = 0.0
    if len(returns):
        winsorized_mean = float(
            returns.clip(
                lower=returns.quantile(0.01),
                upper=returns.quantile(0.99),
            ).mean()
        )

    return {
        "engine": "V17_D1_REFERENCE",
        "classification": (
            "V16 completed-daily BUY rules carried into V17; daily-only "
            "reference replay, not an MTF validation"
        ),
        "preset": args.preset,
        "requested_history_period": args.history_period,
        "measured_years": args.years,
        "holding_period_sessions": args.holding_period,
        "analysis_start": requested_analysis_start.strftime("%Y-%m-%d"),
        "first_signal_date": (
            trades["signal_date"].min() if not trades.empty else None
        ),
        "analysis_end": (
            trades["exit_date"].max() if not trades.empty else None
        ),
        "started_utc": started_at.isoformat(),
        "completed_utc": completed_at.isoformat(),
        "elapsed_seconds": round((completed_at - started_at).total_seconds(), 2),
        "universe": {
            "requested_symbols": int(len(universe)),
            "us_symbols": int(universe["market"].eq("US").sum()),
            "india_symbols": 0,
            "processed_symbols": int(coverage["status"].eq("PROCESSED").sum())
            if not coverage.empty
            else 0,
            "symbols_with_buy_trades": int(trades["ticker"].nunique())
            if not trades.empty
            else 0,
            "coverage_status": {
                key: int(value)
                for key, value in sorted(coverage_counts.items())
                if key
            },
        },
        "performance": {
            "total_trades": int(len(returns)),
            "winning_trades": int(len(wins)),
            "losing_trades": int(len(losses)),
            "flat_trades": int(returns.eq(0).sum()),
            "win_rate_pct": round(
                float(returns.gt(0).mean() * 100.0), 2
            )
            if len(returns)
            else 0.0,
            "average_return_pct": round(float(returns.mean()), 4)
            if len(returns)
            else 0.0,
            "median_return_pct": round(float(returns.median()), 4)
            if len(returns)
            else 0.0,
            "average_win_pct": round(float(wins.mean()), 4)
            if len(wins)
            else 0.0,
            "average_loss_pct": round(float(losses.mean()), 4)
            if len(losses)
            else 0.0,
            "profit_factor": round(
                float(wins.sum() / abs(losses.sum())), 4
            )
            if len(losses) and losses.sum() != 0
            else None,
            "best_trade_pct": round(float(returns.max()), 4)
            if len(returns)
            else 0.0,
            "worst_trade_pct": round(float(returns.min()), 4)
            if len(returns)
            else 0.0,
            "p10_return_pct": round(float(returns.quantile(0.10)), 4)
            if len(returns)
            else 0.0,
            "p25_return_pct": round(float(returns.quantile(0.25)), 4)
            if len(returns)
            else 0.0,
            "p75_return_pct": round(float(returns.quantile(0.75)), 4)
            if len(returns)
            else 0.0,
            "p90_return_pct": round(float(returns.quantile(0.90)), 4)
            if len(returns)
            else 0.0,
            "entry_cohort_max_drawdown_pct": round(cohort_drawdown, 4),
            "winsorized_average_return_1_99_pct": round(
                winsorized_mean, 4
            ),
            "drawdown_note": (
                "Equal-weight mean returns are compounded by entry date. "
                "This is a cohort diagnostic, not a capital-constrained "
                "portfolio backtest, because trades can overlap across symbols."
            ),
        },
        "signals_by_type": (
            {
                key: int(value)
                for key, value in trades["output_signal"].value_counts().items()
            }
            if not trades.empty
            else {}
        ),
        "trades_by_market": (
            {
                key: int(value)
                for key, value in trades["market"].value_counts().items()
            }
            if not trades.empty
            else {}
        ),
        "performance_by_market": by_market,
        "performance_by_signal": by_signal,
        "performance_by_trailing_window": trailing_window_performance(
            trades,
            args.evaluation_windows,
        ),
        "illustrative_cost_scenarios": net_cost_scenarios,
        "top_tickers_minimum_3_trades": ticker_stats,
        "audit": audit_backtest_outputs(
            trades,
            coverage,
            universe,
            requested_analysis_start,
            args.holding_period,
        ),
        "method_notes": [
            f"{args.history_period} of daily OHLCV is requested so EMA200 and 50 completed weekly candles are warm before the measured window.",
            "Signals use only data available on each signal date; entry is the next session open and exit is the close after the configured holding period.",
            "After a BUY, the same ticker cannot enter another trade before the prior trade's exit date, matching the carried-forward V16 production behavior.",
            "Yahoo adjusted OHLCV is the external data source; coverage.csv records missing and insufficient-history symbols.",
            "This daily-only reference cannot validate the incremental 1H/4H V17 hypothesis.",
        ],
    }


def build_breakdowns(trades: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "market",
        "signal_year",
        "output_signal",
        "trades",
        "winning_trades",
        "win_rate_pct",
        "average_return_pct",
        "median_return_pct",
        "best_trade_pct",
        "worst_trade_pct",
    ]
    if trades.empty:
        return pd.DataFrame(columns=columns)
    working = trades.copy()
    working["signal_year"] = working["signal_date"].astype(str).str[:4]
    breakdown = (
        working.groupby(["market", "signal_year", "output_signal"])["return_pct"]
        .agg(
            trades="count",
            winning_trades=lambda values: int((values > 0).sum()),
            average_return_pct="mean",
            median_return_pct="median",
            best_trade_pct="max",
            worst_trade_pct="min",
        )
        .reset_index()
    )
    breakdown["win_rate_pct"] = (
        breakdown["winning_trades"] / breakdown["trades"] * 100.0
    )
    numeric = [
        "win_rate_pct",
        "average_return_pct",
        "median_return_pct",
        "best_trade_pct",
        "worst_trade_pct",
    ]
    breakdown[numeric] = breakdown[numeric].round(4)
    return breakdown.reindex(columns=columns)


def main() -> int:
    args = parse_args()
    if args.years < 1 or args.holding_period < 1 or args.batch_size < 1:
        raise ValueError("years, holding-period, and batch-size must be positive")

    logging.getLogger("yfinance").setLevel(logging.CRITICAL)
    output_dir = Path(args.output_dir).resolve()
    parts_dir = output_dir / "parts"
    parts_dir.mkdir(parents=True, exist_ok=True)
    universe = load_universe(args)
    if universe.empty:
        raise ValueError("No symbols remain after loading the requested universe")

    config = engine.get_config(args.preset)
    analysis_start = (
        pd.Timestamp.now().normalize() - pd.DateOffset(years=args.years)
    )
    started_at = datetime.now(timezone.utc)
    total_batches = math.ceil(len(universe) / args.batch_size)
    print(
        f"V17 completed-D1 {args.years}-year reference replay: "
        f"{len(universe):,} NYSE/Nasdaq symbols, "
        f"{total_batches:,} batches, analysis from {analysis_start:%Y-%m-%d}",
        flush=True,
    )

    for batch_number, start in enumerate(
        range(0, len(universe), args.batch_size), start=1
    ):
        batch = universe.iloc[start : start + args.batch_size].copy()
        trade_part = parts_dir / f"trades_{batch_number:04d}.csv"
        coverage_part = parts_dir / f"coverage_{batch_number:04d}.csv"
        if args.resume and trade_part.exists() and coverage_part.exists():
            print(
                f"[{batch_number}/{total_batches}] checkpoint exists; skipped",
                flush=True,
            )
            continue

        symbols = batch["ticker"].tolist()
        primary = pd.DataFrame()
        retry = pd.DataFrame()
        fetch_error = ""
        try:
            primary = download_batch(symbols, args.history_period, args.timeout)
        except Exception as exc:
            fetch_error = f"{type(exc).__name__}: {exc}"

        missing = [
            symbol
            for symbol in symbols
            if extract_symbol_frame(primary, symbol).empty
        ]
        if missing and not args.no_retry:
            try:
                if args.batch_pause > 0:
                    time.sleep(args.batch_pause)
                retry = download_batch(missing, args.history_period, args.timeout)
            except Exception as exc:
                retry_message = f"{type(exc).__name__}: {exc}"
                fetch_error = " | ".join(
                    value for value in (fetch_error, retry_message) if value
                )

        frames = combine_downloads(primary, retry, symbols)
        batch_trades: list[dict] = []
        batch_coverage: list[dict] = []
        for record in batch.to_dict(orient="records"):
            symbol = record["ticker"]
            frame = frames[symbol]
            try:
                trades, coverage = replay_symbol(
                    frame,
                    record,
                    config,
                    analysis_start,
                    args.holding_period,
                )
            except Exception as exc:
                trades = []
                coverage = {
                    "ticker": symbol,
                    "market": record["market"],
                    "security_name": record.get("security_name", ""),
                    "sector": record.get("sector", ""),
                    "status": "PROCESSING_ERROR",
                    "reason": f"{type(exc).__name__}: {exc}",
                    "history_rows": int(len(frame)),
                    "first_history_date": (
                        frame.index.min().strftime("%Y-%m-%d")
                        if not frame.empty
                        else ""
                    ),
                    "last_history_date": (
                        frame.index.max().strftime("%Y-%m-%d")
                        if not frame.empty
                        else ""
                    ),
                    "measured_sessions": 0,
                    "buy_trades": 0,
                }
            if frame.empty and fetch_error and coverage["status"] == "NO_DATA":
                coverage["reason"] = (
                    f"{coverage['reason']}; batch fetch error: {fetch_error}"
                )
            batch_trades.extend(trades)
            batch_coverage.append(coverage)

        atomic_csv(
            pd.DataFrame(batch_trades),
            trade_part,
            TRADE_COLUMNS,
        )
        atomic_csv(
            pd.DataFrame(batch_coverage),
            coverage_part,
            COVERAGE_COLUMNS,
        )
        print(
            f"[{batch_number}/{total_batches}] symbols={len(batch):,}; "
            f"downloaded={sum(not value.empty for value in frames.values()):,}; "
            f"trades={len(batch_trades):,}",
            flush=True,
        )
        if args.batch_pause > 0 and batch_number < total_batches:
            time.sleep(args.batch_pause)

    trades = read_parts(parts_dir, "trades", TRADE_COLUMNS)
    coverage = read_parts(parts_dir, "coverage", COVERAGE_COLUMNS)
    if not trades.empty:
        trades["return_pct"] = pd.to_numeric(trades["return_pct"], errors="coerce")
        trades = trades.sort_values(
            ["entry_date", "ticker"], kind="stable"
        ).reset_index(drop=True)
    coverage = coverage.sort_values(["market", "ticker"], kind="stable").reset_index(
        drop=True
    )
    breakdown = build_breakdowns(trades)
    summary = calculate_summary(
        trades,
        coverage,
        universe,
        args,
        started_at,
    )

    trades_path = output_dir / "V17_D1_Backtest_Trades.csv"
    coverage_path = output_dir / "V17_D1_Backtest_Coverage.csv"
    breakdown_path = output_dir / "V17_D1_Backtest_Breakdown.csv"
    summary_path = output_dir / "V17_D1_Backtest_Summary.json"
    atomic_csv(trades, trades_path, TRADE_COLUMNS)
    atomic_csv(coverage, coverage_path, COVERAGE_COLUMNS)
    atomic_csv(breakdown, breakdown_path, list(breakdown.columns))
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(json.dumps(summary, indent=2, ensure_ascii=False), flush=True)
    print(f"Trades: {trades_path}", flush=True)
    print(f"Coverage: {coverage_path}", flush=True)
    print(f"Breakdown: {breakdown_path}", flush=True)
    print(f"Summary: {summary_path}", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("Interrupted; completed batch checkpoints are preserved.", file=sys.stderr)
        raise SystemExit(130)
