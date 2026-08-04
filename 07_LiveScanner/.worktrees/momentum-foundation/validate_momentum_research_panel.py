#!/usr/bin/env python
"""Create chronological, plain-language diagnostics for a research panel."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from momentum_research import assign_chronological_split, read_panel


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("panel")
    parser.add_argument("--training-end", required=True)
    parser.add_argument("--calibration-end", required=True)
    parser.add_argument("--horizon", type=int, default=20)
    parser.add_argument("--output-dir", default="output/Momentum_Research_Validation")
    return parser.parse_args()


def summarize_group(group: pd.DataFrame, horizon: int) -> dict:
    returns = pd.to_numeric(
        group[f"forward_{horizon}_session_return_pct"],
        errors="coerce",
    ).dropna()
    return {
        "observations": int(len(group)),
        "complete_outcomes": int(len(returns)),
        "positive_outcome_rate_pct": (
            round(float(returns.gt(0).mean() * 100.0), 2)
            if len(returns)
            else 0.0
        ),
        "average_forward_return_pct": (
            round(float(returns.mean()), 4) if len(returns) else 0.0
        ),
        "median_forward_return_pct": (
            round(float(returns.median()), 4) if len(returns) else 0.0
        ),
    }


def main() -> int:
    args = parse_args()
    panel = read_panel(args.panel)
    split = assign_chronological_split(
        panel,
        training_end=args.training_end,
        calibration_end=args.calibration_end,
        longest_horizon=args.horizon,
    )
    eligible = split.loc[split["split_eligible"].fillna(False)].copy()
    split_summary = {
        name: summarize_group(group, args.horizon)
        for name, group in eligible.groupby("research_split", sort=False)
    }
    tier_rows = []
    for (split_name, tier), group in eligible.groupby(
        ["research_split", "history_tier"],
        sort=False,
    ):
        tier_rows.append({
            "Research period": split_name,
            "Stock history group": tier,
            **summarize_group(group, args.horizon),
        })
    tier_frame = pd.DataFrame(tier_rows)

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    split_path = output_dir / "Chronological_Research_Panel.parquet"
    tier_path = output_dir / "History_Group_Outcomes.csv"
    summary_path = output_dir / "Chronological_Validation_Summary.json"
    split.to_parquet(split_path, index=False)
    tier_frame.to_csv(tier_path, index=False)
    summary = {
        "purpose": "Research-period and history-group outcome audit",
        "classifier_evaluated": False,
        "training_end": args.training_end,
        "calibration_end": args.calibration_end,
        "forward_horizon_sessions": args.horizon,
        "rows": int(len(split)),
        "eligible_rows": int(split["split_eligible"].sum()),
        "excluded_rows": int((~split["split_eligible"]).sum()),
        "period_outcomes": split_summary,
        "interpretation": (
            "These are unconditional outcome baselines. They are not evidence "
            "that a momentum classifier works."
        ),
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
