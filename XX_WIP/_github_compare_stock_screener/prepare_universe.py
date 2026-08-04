from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

import pandas as pd

from stock_screener import normalize_exchange


DEFAULT_INPUT = "uploads/NYSE_NASDAQ_Master_Library.csv"
DEFAULT_OUTPUT = "uploads/NYSE_NASDAQ_Clean_Common_ETF_ADR.csv"

EXCLUDE_PATTERNS = [
    r"\bwarrants?\b",
    r"\bright(s)?\b",
    r"\bunits?\b",
    r"\bpreferred\b",
    r"\bpreference\b",
    r"\bdepositary shares\b.*\bpreferred\b",
    r"\bnotes?\b",
    r"\bbonds?\b",
    r"\bdebentures?\b",
    r"\btrust certificates?\b",
    r"\bclosed end fund\b",
    r"\bclosed-end fund\b",
    r"\bbeneficial interest\b",
    r"\bconvertible\b",
    r"\bsubscription\b",
    r"\bcontingent value right\b",
]

COMMON_PATTERNS = [
    r"\bcommon stock\b",
    r"\bcommon shares?\b",
    r"\bordinary shares?\b",
    r"\bclass [a-z] ordinary shares?\b",
    r"\bclass [a-z] common stock\b",
    r"\bregistered shares?\b",
]

ADR_PATTERNS = [
    r"\badr\b",
    r"\bads\b",
    r"\bamerican depositary\b",
    r"\bglobal depositary\b",
]


def _norm_column(column: object) -> str:
    return " ".join(str(column).strip().upper().replace("_", " ").split())


def _column_map(df: pd.DataFrame) -> dict[str, object]:
    return {_norm_column(column): column for column in df.columns}


def _read_master(path: str) -> pd.DataFrame:
    with open(path, "r", encoding="utf-8-sig", errors="replace") as handle:
        first_line = handle.readline()
    if first_line.count("|") > first_line.count(",") and "|" in first_line:
        return pd.read_csv(path, dtype=str, sep="|")
    if "\t" in first_line:
        return pd.read_csv(path, dtype=str, sep="\t")
    return pd.read_csv(path, dtype=str)


def _flag_true(value: Any) -> bool:
    return str(value).strip().upper() in {"Y", "YES", "TRUE", "1"}


def _clean_symbol(value: Any) -> str:
    symbol = str(value).strip().upper().replace("/", "-")
    if not symbol or symbol in {"NAN", "NONE", "NULL", "SYMBOL", "TICKER", "ACT SYMBOL", "NASDAQ SYMBOL"}:
        return ""
    if any(ch.isspace() for ch in symbol) or "," in symbol or "|" in symbol:
        return ""
    if len(symbol) > 20:
        return ""
    if any(ch not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-^=" for ch in symbol):
        return ""
    return symbol


def _contains_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def _classify_instrument(row: pd.Series, columns: dict[str, object]) -> str:
    name = str(row.get(columns.get("SECURITY NAME", ""), "") or "")
    etf_col = columns.get("ETF")
    if etf_col is not None and _flag_true(row.get(etf_col)):
        return "ETF"
    if _contains_any(name, ADR_PATTERNS):
        return "ADR"
    if _contains_any(name, COMMON_PATTERNS):
        return "COMMON_STOCK"
    return ""


def prepare_universe(input_file: str, output_file: str) -> pd.DataFrame:
    df = _read_master(input_file)
    columns = _column_map(df)
    symbol_col = next(
        (columns[name] for name in ["TICKER", "ACT SYMBOL", "NASDAQ SYMBOL", "SYMBOL"] if name in columns),
        None,
    )
    if symbol_col is None:
        raise ValueError("Master file must contain Ticker, ACT Symbol, NASDAQ Symbol, or Symbol column.")

    security_name_col = columns.get("SECURITY NAME")
    exchange_col = columns.get("LISTING EXCHANGE") or columns.get("EXCHANGE")
    test_issue_col = columns.get("TEST ISSUE")
    market_cap_col = columns.get("MARKETCAP") or columns.get("MARKET CAP")
    sector_col = columns.get("SECTOR")
    industry_col = columns.get("INDUSTRY")

    rows: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        if test_issue_col is not None and _flag_true(row.get(test_issue_col)):
            continue
        symbol = _clean_symbol(row.get(symbol_col))
        if not symbol:
            continue
        security_name = str(row.get(security_name_col, "") or "") if security_name_col is not None else ""
        instrument_type = _classify_instrument(row, columns)
        if not instrument_type:
            continue
        if instrument_type == "COMMON_STOCK" and _contains_any(security_name, EXCLUDE_PATTERNS):
            continue
        exchange = normalize_exchange(str(row.get(exchange_col, "") or "")) if exchange_col is not None else ""
        rows.append({
            "Symbol": symbol,
            "Exchange": exchange,
            "InstrumentType": instrument_type,
            "SecurityName": security_name,
            "Sector": row.get(sector_col, "") if sector_col is not None else "",
            "Industry": row.get(industry_col, "") if industry_col is not None else "",
            "MarketCap": row.get(market_cap_col, "") if market_cap_col is not None else "",
        })

    output = pd.DataFrame(rows).drop_duplicates(subset=["Symbol"]).sort_values("Symbol").reset_index(drop=True)
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(output_path, index=False)
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare a clean NYSE/NASDAQ universe from a master library file.")
    parser.add_argument("--input", default=DEFAULT_INPUT)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output = prepare_universe(args.input, args.output)
    counts = output["InstrumentType"].value_counts().to_dict() if not output.empty else {}
    print(f"Wrote {len(output)} symbols to {args.output}")
    print(f"Instrument counts: {counts}")


if __name__ == "__main__":
    main()
