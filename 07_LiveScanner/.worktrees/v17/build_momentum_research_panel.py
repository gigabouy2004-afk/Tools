#!/usr/bin/env python
"""Build a point-in-time completed-daily momentum research panel."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from momentum_research import (
    OutcomeContract,
    PLAIN_METADATA_COLUMNS,
    build_symbol_research_panel,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build completed-daily feature and future-outcome records for all "
            "supplied NYSE/Nasdaq equities, including young and delisted names."
        )
    )
    parser.add_argument("daily_archive")
    parser.add_argument("--output-dir", default="output/Momentum_Research_Panel")
    parser.add_argument("--horizons", default="5,10,20")
    parser.add_argument("--barrier-horizon", type=int, default=10)
    parser.add_argument("--upper-atr", type=float, default=2.0)
    parser.add_argument("--lower-atr", type=float, default=1.0)
    return parser.parse_args()


def load_long_daily_archive(path: str | Path) -> pd.DataFrame:
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"Daily archive not found: {source}")
    if source.suffix.lower() in {".parquet", ".pq"}:
        frame = pd.read_parquet(source)
    else:
        frame = pd.read_csv(source, low_memory=False)
    frame.columns = [str(column).strip().lower() for column in frame.columns]
    ticker_column = next(
        (column for column in ("ticker", "symbol") if column in frame),
        None,
    )
    date_column = next(
        (column for column in ("date", "session_date", "timestamp") if column in frame),
        None,
    )
    if ticker_column is None or date_column is None:
        raise ValueError("Archive requires ticker/symbol and date/session_date.")
    frame = frame.rename(
        columns={ticker_column: "ticker", date_column: "session_date"}
    )
    frame["ticker"] = frame["ticker"].astype(str).str.strip().str.upper()
    frame["session_date"] = pd.to_datetime(
        frame["session_date"],
        errors="coerce",
    )
    frame = frame.dropna(subset=["ticker", "session_date"])

    required_identity = ("security_id", "listing_date", "delisting_date")
    missing_identity = [
        column for column in required_identity if column not in frame
    ]
    if missing_identity:
        raise ValueError(
            "Archive requires point-in-time identity fields: "
            + ", ".join(missing_identity)
        )
    security_id = frame["security_id"].fillna("").astype(str).str.strip()
    missing_security_id = security_id.str.upper().isin({"", "NAN", "NONE"})
    if missing_security_id.any():
        raise ValueError(
            "Archive contains rows without a stable security_id: "
            f"{int(missing_security_id.sum())}"
        )
    frame["security_id"] = security_id

    if "listing_exchange" not in frame:
        raise ValueError(
            "Archive requires point-in-time listing_exchange so NYSE/Nasdaq "
            "scope can be verified."
        )
    exchange = frame["listing_exchange"].astype(str).str.strip().str.upper()
    frame = frame.loc[exchange.isin({"NYSE", "NASDAQ"})].copy()
    if "is_etf" in frame:
        is_etf = frame["is_etf"].astype(str).str.strip().str.upper()
        frame = frame.loc[~is_etf.isin({"Y", "YES", "TRUE", "1"})].copy()
    elif "instrument_type" in frame:
        instrument_type = (
            frame["instrument_type"].astype(str).str.strip().str.upper()
        )
        frame = frame.loc[instrument_type.eq("EQUITY")].copy()
    else:
        raise ValueError(
            "Archive requires is_etf or instrument_type so equity scope can "
            "be verified."
        )
    return frame


def main() -> int:
    args = parse_args()
    horizons = tuple(
        sorted({
            int(value)
            for value in str(args.horizons).split(",")
            if str(value).strip()
        })
    )
    contract = OutcomeContract(
        horizons=horizons,
        barrier_horizon=args.barrier_horizon,
        upper_atr_multiple=args.upper_atr,
        lower_atr_multiple=args.lower_atr,
    )
    archive = load_long_daily_archive(args.daily_archive)
    panels = []
    coverage = []
    for security_id, group in archive.groupby("security_id", sort=True):
        group = group.sort_values("session_date").set_index("session_date")
        ticker = str(group["ticker"].iloc[-1]).strip().upper()
        keep_columns = [
            column
            for column in (
                "open", "high", "low", "close", "volume",
                *PLAIN_METADATA_COLUMNS,
            )
            if column in group
        ]
        try:
            panel = build_symbol_research_panel(
                group[keep_columns],
                ticker=ticker,
                contract=contract,
            )
            panels.append(panel.reset_index(drop=True))
            coverage.append({
                "ticker": ticker,
                "security_id": security_id,
                "status": "Processed",
                "daily_rows": int(len(group)),
                "panel_rows": int(len(panel)),
                "first_session": (
                    group.index.min().strftime("%Y-%m-%d") if len(group) else ""
                ),
                "last_session": (
                    group.index.max().strftime("%Y-%m-%d") if len(group) else ""
                ),
                "reason": "",
            })
        except Exception as exc:
            coverage.append({
                "ticker": ticker,
                "security_id": security_id,
                "status": "Error",
                "daily_rows": int(len(group)),
                "panel_rows": 0,
                "first_session": "",
                "last_session": "",
                "reason": str(exc),
            })

    panel = pd.concat(panels, ignore_index=True) if panels else pd.DataFrame()
    coverage_frame = pd.DataFrame(coverage)
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    panel_parquet = output_dir / "Momentum_Research_Panel.parquet"
    panel_csv = output_dir / "Momentum_Research_Panel.csv"
    coverage_path = output_dir / "Momentum_Research_Coverage.csv"
    summary_path = output_dir / "Momentum_Research_Summary.json"
    panel.to_parquet(panel_parquet, index=False)
    panel.to_csv(panel_csv, index=False)
    coverage_frame.to_csv(coverage_path, index=False)

    summary = {
        "purpose": "Completed-daily research panel; no production classification",
        "source": str(Path(args.daily_archive).resolve()),
        "securities": (
            int(panel["security_id"].nunique())
            if not panel.empty and "security_id" in panel
            else 0
        ),
        "rows": int(len(panel)),
        "history_tiers": (
            panel["history_tier"].value_counts().to_dict()
            if not panel.empty
            else {}
        ),
        "coverage_status": (
            coverage_frame["status"].value_counts().to_dict()
            if not coverage_frame.empty
            else {}
        ),
        "outcome_contract": (
            panel["research_outcome_contract"].iloc[0]
            if not panel.empty
            else ""
        ),
        "warnings": [
            "The panel does not classify genuine momentum.",
            "The archive must be point-in-time and include delisted securities.",
            "Sector/industry fields provide context and never replace missing stock history.",
            "The provisional ATR barriers are research labels, not approved trading thresholds.",
        ],
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
