#!/usr/bin/env python3
"""
Generate USA-listed stock ticker codes from company names.

Input:
    CSV/TXT: one company name per line, with or without a header
    XLSX:     company names in the first column (or a named column)

Primary output columns:
    A: Stock Code
    B: Company Name

The matcher is intentionally grep-like:
  1. Normalise company names and remove legal suffixes.
  2. Exact normalised-name match.
  3. Token-prefix / substring candidate filtering.
  4. Fuzzy scoring across the reduced candidate set.
  5. Yahoo Finance search fallback for unresolved names.
  6. Ambiguous/low-confidence matches are not silently accepted.

Examples:
    python generate_usa_stock_codes.py Energy_Stock_Companies_Names.csv
    python generate_usa_stock_codes.py input.xlsx --column "Company Name"
    python generate_usa_stock_codes.py input.csv --min-score 82 --accept-score 90

Dependencies:
    pip install pandas openpyxl requests rapidfuzz
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import sys
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd
import requests
from rapidfuzz import fuzz

SEC_URL = "https://www.sec.gov/files/company_tickers_exchange.json"
YAHOO_SEARCH_URL = "https://query2.finance.yahoo.com/v1/finance/search"

US_EXCHANGES = {
    "Nasdaq",
    "NYSE",
    "NYSE Arca",
    "NYSE American",
    "Cboe BZX",
    "Cboe BYX",
    "Cboe EDGX",
    "Cboe EDGA",
}

LEGAL_SUFFIXES = {
    "inc", "incorporated", "corp", "corporation", "company", "co", "companies",
    "limited", "ltd", "plc", "lp", "llp", "llc", "sa", "se", "nv", "ag",
    "spa", "srl", "asa", "ab", "oyj", "pte", "pty", "holdings", "holding",
    "group", "partners", "partnership", "trust", "the", "class", "ordinary",
    "shares", "share", "common", "stock", "depositary", "adr", "ads",
}

# Tokens that are meaningful in company names and should not be stripped even if short.
KEEP_TOKENS = {"bp", "hp", "ge", "3m", "at", "t"}

SESSION = requests.Session()
SESSION.headers.update(
    {
        # SEC asks automated clients to identify themselves. Replace the email if desired.
        "User-Agent": "USA Stock Code Mapper contact@example.com",
        "Accept-Language": "en-US,en;q=0.9",
    }
)


@dataclass
class Candidate:
    ticker: str
    name: str
    exchange: str
    source: str
    quote_type: str = "EQUITY"


@dataclass
class MatchResult:
    ticker: str
    company_name: str
    matched_name: str = ""
    exchange: str = ""
    score: float = 0.0
    status: str = "NOT FOUND"
    source: str = ""
    alternatives: str = ""


def ascii_fold(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in value if not unicodedata.combining(ch))


def normalise_name(value: str, strip_suffixes: bool = True) -> str:
    text = ascii_fold(str(value)).lower()
    text = text.replace("&", " and ")
    text = re.sub(r"\b(petrobras)\b", "petrobras", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    tokens = [t for t in text.split() if t]

    if strip_suffixes:
        # Repeatedly remove legal suffixes from the tail, then remove low-value suffix
        # tokens elsewhere. This handles names such as "The Williams Companies, Inc.".
        while tokens and tokens[-1] in LEGAL_SUFFIXES:
            tokens.pop()
        tokens = [t for t in tokens if t not in LEGAL_SUFFIXES or t in KEEP_TOKENS]

    return " ".join(tokens)


def compact_name(value: str) -> str:
    return normalise_name(value).replace(" ", "")


def meaningful_tokens(value: str) -> list[str]:
    return [t for t in normalise_name(value).split() if len(t) >= 2 or t in KEEP_TOKENS]


def score_names(query: str, candidate: str) -> float:
    q = normalise_name(query)
    c = normalise_name(candidate)
    if not q or not c:
        return 0.0
    if q == c:
        return 100.0

    q_compact = q.replace(" ", "")
    c_compact = c.replace(" ", "")
    if q_compact == c_compact:
        return 99.5

    q_tokens = set(q.split())
    c_tokens = set(c.split())
    overlap = len(q_tokens & c_tokens) / max(1, len(q_tokens | c_tokens))

    scores = [
        fuzz.ratio(q, c),
        fuzz.token_sort_ratio(q, c),
        fuzz.token_set_ratio(q, c),
        fuzz.WRatio(q, c),
        overlap * 100,
    ]

    # Strong grep-style containment bonus, but only for sufficiently descriptive names.
    if min(len(q_compact), len(c_compact)) >= 5 and (
        q_compact in c_compact or c_compact in q_compact
    ):
        scores.append(94.0)

    # First meaningful token usually carries substantial identity.
    qt = meaningful_tokens(query)
    ct = meaningful_tokens(candidate)
    if qt and ct and qt[0] == ct[0]:
        scores.append(min(96.0, fuzz.WRatio(q, c) + 4.0))

    return round(max(scores), 2)


def read_company_names(path: Path, column: Optional[str]) -> list[str]:
    suffix = path.suffix.lower()

    if suffix in {".xlsx", ".xlsm", ".xls"}:
        df = pd.read_excel(path)
        series = df[column] if column else df.iloc[:, 0]
        return clean_company_list(series.tolist())

    # The supplied input is a headerless, one-name-per-line UTF-8 file. We first
    # attempt that safe format because commas may legitimately occur inside names.
    raw_lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    nonempty = [line.strip() for line in raw_lines if line.strip()]

    if column:
        df = pd.read_csv(path, dtype=str, keep_default_na=False)
        if column not in df.columns:
            raise KeyError(f"Column {column!r} not found. Available: {list(df.columns)}")
        return clean_company_list(df[column].tolist())

    # Detect a conventional CSV header only when the first row clearly looks like one.
    first = nonempty[0].strip().lower() if nonempty else ""
    if first in {"company", "company name", "company_name", "name"}:
        return clean_company_list(nonempty[1:])

    return clean_company_list(nonempty)


def clean_company_list(values: Iterable[object]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        name = str(value).strip()
        if not name or name.lower() in {"nan", "none"}:
            continue
        key = normalise_name(name, strip_suffixes=False)
        if key not in seen:
            seen.add(key)
            output.append(name)
    return output


def load_sec_candidates(cache_path: Path, refresh: bool = False) -> list[Candidate]:
    payload: dict
    if cache_path.exists() and not refresh:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
    else:
        response = SESSION.get(SEC_URL, timeout=30)
        response.raise_for_status()
        payload = response.json()
        cache_path.write_text(json.dumps(payload), encoding="utf-8")

    fields = payload.get("fields", [])
    data = payload.get("data", [])
    index = {name: i for i, name in enumerate(fields)}

    required = {"name", "ticker", "exchange"}
    if not required.issubset(index):
        raise ValueError(f"Unexpected SEC schema. Fields: {fields}")

    candidates: list[Candidate] = []
    for row in data:
        ticker = str(row[index["ticker"]]).strip()
        name = str(row[index["name"]]).strip()
        exchange = str(row[index["exchange"]]).strip()
        if not ticker or not name:
            continue
        # The SEC file can include OTC/blank exchange entries. The request is for
        # USA exchange-listed codes, so keep recognised US exchanges by default.
        if exchange and exchange not in US_EXCHANGES:
            continue
        candidates.append(Candidate(ticker, name, exchange, "SEC"))
    return candidates


def grep_candidates(query: str, universe: list[Candidate], limit: int = 80) -> list[Candidate]:
    q_norm = normalise_name(query)
    q_compact = q_norm.replace(" ", "")
    q_tokens = meaningful_tokens(query)
    if not q_norm:
        return []

    exact: list[Candidate] = []
    contained: list[Candidate] = []
    token_hits: list[tuple[int, Candidate]] = []

    for cand in universe:
        c_norm = normalise_name(cand.name)
        c_compact = c_norm.replace(" ", "")
        if c_norm == q_norm or c_compact == q_compact:
            exact.append(cand)
            continue
        if min(len(q_compact), len(c_compact)) >= 5 and (
            q_compact in c_compact or c_compact in q_compact
        ):
            contained.append(cand)
            continue
        c_tokens = set(meaningful_tokens(cand.name))
        hit_count = sum(1 for token in q_tokens if token in c_tokens)
        prefix_count = sum(
            1 for qt in q_tokens for ct in c_tokens
            if len(qt) >= 4 and (qt.startswith(ct) or ct.startswith(qt))
        )
        rank = hit_count * 10 + prefix_count
        if rank > 0:
            token_hits.append((rank, cand))

    if exact:
        return exact[:limit]
    token_hits.sort(key=lambda item: item[0], reverse=True)
    merged = contained + [cand for _, cand in token_hits]

    deduped: list[Candidate] = []
    seen: set[tuple[str, str]] = set()
    for cand in merged:
        key = (cand.ticker, cand.name)
        if key not in seen:
            seen.add(key)
            deduped.append(cand)
        if len(deduped) >= limit:
            break
    return deduped


def yahoo_candidates(query: str, retries: int = 3) -> list[Candidate]:
    params = {
        "q": query,
        "quotesCount": 20,
        "newsCount": 0,
        "enableFuzzyQuery": "true",
        "quotesQueryId": "tss_match_phrase_query",
    }

    for attempt in range(retries):
        try:
            response = SESSION.get(YAHOO_SEARCH_URL, params=params, timeout=20)
            response.raise_for_status()
            quotes = response.json().get("quotes", [])
            output: list[Candidate] = []
            for item in quotes:
                quote_type = str(item.get("quoteType", "")).upper()
                if quote_type not in {"EQUITY"}:
                    continue
                exchange = str(item.get("exchDisp") or item.get("exchange") or "")
                symbol = str(item.get("symbol") or "").strip()
                name = str(item.get("longname") or item.get("shortname") or "").strip()
                if not symbol or not name:
                    continue
                # Exclude common non-US suffixes. US tickers generally have no suffix;
                # class shares such as BRK-B remain valid.
                if re.search(r"\.[A-Z]{1,3}$", symbol):
                    continue
                output.append(Candidate(symbol, name, exchange, "YAHOO", quote_type))
            return output
        except (requests.RequestException, ValueError) as exc:
            if attempt == retries - 1:
                logging.warning("Yahoo search failed for %s: %s", query, exc)
                return []
            time.sleep(1.5 * (attempt + 1))
    return []


def rank_candidates(query: str, candidates: list[Candidate]) -> list[tuple[float, Candidate]]:
    ranked = [(score_names(query, cand.name), cand) for cand in candidates]
    ranked.sort(key=lambda item: item[0], reverse=True)
    return ranked


def choose_match(
    company_name: str,
    sec_universe: list[Candidate],
    min_score: float,
    accept_score: float,
    ambiguity_gap: float,
    use_yahoo: bool,
) -> MatchResult:
    local = grep_candidates(company_name, sec_universe)
    ranked = rank_candidates(company_name, local)

    # Search externally when SEC candidates are absent or weak.
    if use_yahoo and (not ranked or ranked[0][0] < accept_score):
        combined = local + yahoo_candidates(company_name)
        unique: dict[tuple[str, str], Candidate] = {}
        for cand in combined:
            unique[(cand.ticker, cand.name)] = cand
        ranked = rank_candidates(company_name, list(unique.values()))

    alternatives = "; ".join(
        f"{cand.ticker}|{cand.name}|{score:.1f}"
        for score, cand in ranked[:5]
    )

    if not ranked or ranked[0][0] < min_score:
        return MatchResult(
            ticker="NOT FOUND",
            company_name=company_name,
            score=ranked[0][0] if ranked else 0.0,
            status="NOT FOUND",
            alternatives=alternatives,
        )

    best_score, best = ranked[0]
    second_score = ranked[1][0] if len(ranked) > 1 else 0.0

    if best_score < accept_score or best_score - second_score < ambiguity_gap:
        return MatchResult(
            ticker="REVIEW",
            company_name=company_name,
            matched_name=best.name,
            exchange=best.exchange,
            score=best_score,
            status="REVIEW",
            source=best.source,
            alternatives=alternatives,
        )

    return MatchResult(
        ticker=best.ticker,
        company_name=company_name,
        matched_name=best.name,
        exchange=best.exchange,
        score=best_score,
        status="MATCHED",
        source=best.source,
        alternatives=alternatives,
    )


def write_outputs(results: list[MatchResult], output_base: Path) -> tuple[Path, Path, Path]:
    primary = pd.DataFrame(
        {
            "Stock Code": [r.ticker for r in results],
            "Company Name": [r.company_name for r in results],
        }
    )
    audit = pd.DataFrame(
        {
            "Stock Code": [r.ticker for r in results],
            "Company Name": [r.company_name for r in results],
            "Matched Name": [r.matched_name for r in results],
            "Exchange": [r.exchange for r in results],
            "Match Score": [r.score for r in results],
            "Status": [r.status for r in results],
            "Source": [r.source for r in results],
            "Top Alternatives": [r.alternatives for r in results],
        }
    )

    csv_path = output_base.with_suffix(".csv")
    xlsx_path = output_base.with_suffix(".xlsx")
    review_path = output_base.with_name(output_base.name + "_review.csv")

    primary.to_csv(csv_path, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        primary.to_excel(writer, sheet_name="Stock Codes", index=False)
        audit.to_excel(writer, sheet_name="Match Audit", index=False)
        ws = writer.book["Stock Codes"]
        ws.column_dimensions["A"].width = 16
        ws.column_dimensions["B"].width = 48
        audit_ws = writer.book["Match Audit"]
        for col, width in {"A": 16, "B": 42, "C": 42, "D": 18, "E": 14, "F": 14, "G": 12, "H": 90}.items():
            audit_ws.column_dimensions[col].width = width
        ws.freeze_panes = "A2"
        audit_ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
        audit_ws.auto_filter.ref = audit_ws.dimensions

    audit[audit["Status"] != "MATCHED"].to_csv(
        review_path, index=False, encoding="utf-8-sig"
    )
    return csv_path, xlsx_path, review_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Map company names to USA stock ticker codes.")
    parser.add_argument("input_file", type=Path, help="Input CSV, TXT, or XLSX file")
    parser.add_argument("--column", help="Company-name column; defaults to first column/one line per name")
    parser.add_argument("--output", type=Path, help="Output base path without extension")
    parser.add_argument("--min-score", type=float, default=78.0, help="Below this score => NOT FOUND")
    parser.add_argument("--accept-score", type=float, default=88.0, help="At/above this score can auto-match")
    parser.add_argument("--ambiguity-gap", type=float, default=4.0, help="Required lead over second candidate")
    parser.add_argument("--no-yahoo", action="store_true", help="Disable Yahoo fallback; SEC universe only")
    parser.add_argument("--refresh-sec", action="store_true", help="Refresh the cached SEC ticker universe")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path: Path = args.input_file.resolve()
    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}", file=sys.stderr)
        return 2

    output_base = (
        args.output.resolve()
        if args.output
        else input_path.with_name(input_path.stem + "_USA_Stock_Codes")
    )
    output_base.parent.mkdir(parents=True, exist_ok=True)

    log_path = output_base.with_suffix(".log")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[logging.FileHandler(log_path, encoding="utf-8"), logging.StreamHandler()],
    )

    try:
        companies = read_company_names(input_path, args.column)
        logging.info("Company names read: %d", len(companies))
        cache_path = output_base.parent / "sec_company_tickers_cache.json"
        sec_universe = load_sec_candidates(cache_path, refresh=args.refresh_sec)
        logging.info("SEC USA-listed ticker candidates loaded: %d", len(sec_universe))

        results: list[MatchResult] = []
        total = len(companies)
        for index, company in enumerate(companies, start=1):
            result = choose_match(
                company,
                sec_universe,
                min_score=args.min_score,
                accept_score=args.accept_score,
                ambiguity_gap=args.ambiguity_gap,
                use_yahoo=not args.no_yahoo,
            )
            results.append(result)
            logging.info(
                "[%d/%d] %-45s -> %-10s score=%5.1f status=%s",
                index, total, company[:45], result.ticker, result.score, result.status,
            )
            # Be polite to external search when it is used.
            if result.source == "YAHOO" or result.status != "MATCHED":
                time.sleep(0.12)

        csv_path, xlsx_path, review_path = write_outputs(results, output_base)
        matched = sum(r.status == "MATCHED" for r in results)
        review = sum(r.status == "REVIEW" for r in results)
        not_found = sum(r.status == "NOT FOUND" for r in results)

        print("\n" + "=" * 78)
        print("USA STOCK CODE MAPPING SUMMARY")
        print("=" * 78)
        print(f"Input companies : {total}")
        print(f"Matched         : {matched}")
        print(f"Review required : {review}")
        print(f"Not found       : {not_found}")
        print(f"CSV output      : {csv_path}")
        print(f"Excel output    : {xlsx_path}")
        print(f"Review file     : {review_path}")
        print(f"Log file        : {log_path}")
        return 0

    except Exception as exc:
        logging.exception("Fatal error: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())