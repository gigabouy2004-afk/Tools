#!/usr/bin/env python
"""Create reusable diagnostic slices from a V17 daily reference replay."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("trades_csv")
    parser.add_argument("--output-dir")
    parser.add_argument("--minimum-slice-trades", type=int, default=30)
    return parser.parse_args()


def performance(group: pd.DataFrame) -> dict:
    returns = pd.to_numeric(group["return_pct"], errors="coerce").dropna()
    wins = returns.loc[returns.gt(0)]
    losses = returns.loc[returns.lt(0)]
    net = returns - 0.20
    net_wins = net.loc[net.gt(0)]
    net_losses = net.loc[net.lt(0)]
    winsorized = (
        returns.clip(
            lower=returns.quantile(0.01),
            upper=returns.quantile(0.99),
        )
        if len(returns)
        else returns
    )
    return {
        "trades": int(len(returns)),
        "symbols": int(group["ticker"].nunique()),
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
        "winsorized_average_1_99_pct": (
            round(float(winsorized.mean()), 4)
            if len(winsorized)
            else 0.0
        ),
        "profit_factor": (
            round(float(wins.sum() / abs(losses.sum())), 4)
            if len(losses) and losses.sum() != 0
            else None
        ),
        "average_net_20bps_pct": (
            round(float(net.mean()), 4) if len(net) else 0.0
        ),
        "net_profit_factor_20bps": (
            round(float(net_wins.sum() / abs(net_losses.sum())), 4)
            if len(net_losses) and net_losses.sum() != 0
            else None
        ),
    }


def add_bands(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame.copy()
    output["signal_year"] = output["signal_date"].astype(str).str[:4]
    output["adx_band_research"] = pd.cut(
        pd.to_numeric(output["adx"], errors="coerce"),
        [-np.inf, 15, 20, 25, 35, 50, np.inf],
        labels=["<15", "15-20", "20-25", "25-35", "35-50", ">=50"],
        right=False,
    )
    output["rsi_band_research"] = pd.cut(
        pd.to_numeric(output["rsi"], errors="coerce"),
        [-np.inf, 50, 60, 70, 80, np.inf],
        labels=["<50", "50-60", "60-70", "70-80", ">=80"],
        right=False,
    )
    output["volume_ratio_band_research"] = pd.cut(
        pd.to_numeric(output["relative_volume_ratio"], errors="coerce"),
        [-np.inf, 0.6, 0.8, 1.0, 1.2, 1.5, np.inf],
        labels=[
            "<0.60", "0.60-0.80", "0.80-1.00", "1.00-1.20",
            "1.20-1.50", ">=1.50",
        ],
        right=False,
    )
    output["ema50_distance_band_research"] = pd.cut(
        pd.to_numeric(output["ema50_distance_atr"], errors="coerce"),
        [-np.inf, 0, 1, 2, 3, 5, np.inf],
        labels=["<0", "0-1", "1-2", "2-3", "3-5", ">=5"],
        right=False,
    )
    stochastic_max = output[["stoch_k", "stoch_d"]].apply(
        pd.to_numeric,
        errors="coerce",
    ).max(axis=1)
    output["stochastic_band_research"] = pd.cut(
        stochastic_max,
        [-np.inf, 40, 60, 70, 80, 90, np.inf],
        labels=["<40", "40-60", "60-70", "70-80", "80-90", ">=90"],
        right=False,
    )
    output["adx_direction_research"] = np.where(
        pd.to_numeric(output["adx_plus_di"], errors="coerce")
        > pd.to_numeric(output["adx_minus_di"], errors="coerce"),
        "BULLISH_DI",
        "NON_BULLISH_DI",
    )
    output["adx_slope_research"] = np.where(
        pd.to_numeric(output["adx_change_5"], errors="coerce") > 0,
        "RISING_5",
        "FLAT_OR_FALLING_5",
    )
    return output


def grouped_slices(
    frame: pd.DataFrame,
    dimensions: list[tuple[str, list[str]]],
    minimum_trades: int,
) -> pd.DataFrame:
    rows = []
    for slice_name, fields in dimensions:
        grouper = fields[0] if len(fields) == 1 else fields
        for keys, group in frame.groupby(grouper, dropna=False, observed=True):
            key_values = keys if isinstance(keys, tuple) else (keys,)
            metrics = performance(group)
            if metrics["trades"] < minimum_trades:
                continue
            row = {
                "slice": slice_name,
                **{
                    field: str(value)
                    for field, value in zip(fields, key_values)
                },
                **metrics,
            }
            rows.append(row)
    output = pd.DataFrame(rows)
    if output.empty:
        return output
    return output.sort_values(
        ["slice", "average_return_pct", "trades"],
        ascending=[True, False, False],
    )


def main() -> int:
    args = parse_args()
    source = Path(args.trades_csv).resolve()
    trades = pd.read_csv(source, low_memory=False)
    prepared = add_bands(trades)
    dimensions = [
        ("signal", ["output_signal"]),
        ("year", ["signal_year"]),
        ("daily_state", ["v17_daily_momentum_state"]),
        ("daily_quality_score", ["v17_daily_quality_score"]),
        ("signal_x_daily_state", ["output_signal", "v17_daily_momentum_state"]),
        ("signal_x_quality", ["output_signal", "v17_daily_quality_score"]),
        ("adx_band", ["adx_band_research"]),
        ("adx_direction", ["adx_direction_research"]),
        ("adx_slope", ["adx_slope_research"]),
        ("rsi_band", ["rsi_band_research"]),
        ("stochastic_band", ["stochastic_band_research"]),
        ("volume_ratio_band", ["volume_ratio_band_research"]),
        ("ema50_distance_band", ["ema50_distance_band_research"]),
        (
            "signal_x_volume",
            ["output_signal", "volume_ratio_band_research"],
        ),
        (
            "signal_x_extension",
            ["output_signal", "ema50_distance_band_research"],
        ),
    ]
    slices = grouped_slices(
        prepared,
        dimensions,
        max(1, args.minimum_slice_trades),
    )
    output_dir = (
        Path(args.output_dir).resolve()
        if args.output_dir
        else source.parent
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    slices_path = output_dir / "V17_D1_Backtest_Diagnostic_Slices.csv"
    summary_path = output_dir / "V17_D1_Backtest_Diagnostic_Summary.json"
    slices.to_csv(slices_path, index=False)

    summary = {
        "source": str(source),
        "overall": performance(prepared),
        "minimum_slice_trades": max(1, args.minimum_slice_trades),
        "slice_rows": int(len(slices)),
        "best_slices_minimum_100_trades": (
            slices.loc[slices["trades"].ge(100)]
            .sort_values(
                ["average_return_pct", "trades"],
                ascending=[False, False],
            )
            .head(25)
            .replace({np.nan: None})
            .to_dict("records")
        ),
        "worst_slices_minimum_100_trades": (
            slices.loc[slices["trades"].ge(100)]
            .sort_values(
                ["average_return_pct", "trades"],
                ascending=[True, False],
            )
            .head(25)
            .replace({np.nan: None})
            .to_dict("records")
        ),
        "warnings": [
            "Slices are descriptive and overlap; they are not independent tests.",
            "Thresholds were not selected on a separate training sample.",
            "No slice is approved as a V17 production gate.",
        ],
        "artifacts": {
            "slices_csv": str(slices_path),
        },
    }
    summary_path.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
