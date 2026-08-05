#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ETF Portfolio Mapping and Analysis Engine V8

Input modes:
1. Direct ETF codes:
    python ETF_Portfolio_Mapping_V8.py -t CHPS,PSI,AIVC,SMH

2. ETF code file:
    python ETF_Portfolio_Mapping_V8.py -f ETF_List.txt

3. Theme/classifier mode:
    python ETF_Portfolio_Mapping_V8.py --theme "Europe,Defence" --classifier-file ETF_Master_Classification.csv

The script generates a pure, completely agnostic extraction layer:
- ETF x Company weighted matrix (Sorted by ETF coverage frequency and aggregate portfolio weight)
- ETF summary and performance comparison (LTP, AUM, Volume, Alpha, Beta, multi-window returns)
- Stock summary (Global visibility counts and weight statistics across the universe)
- Raw holdings data dump
"""

import os
import sys
import argparse
import csv
import json
import re
import importlib.util
import urllib.request
from io import StringIO
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import yfinance as yf
import openpyxl
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import PatternFill

INTL_SUFFIX_CANDIDATES = [
    ".T", ".HK", ".KS", ".KQ", ".AX", ".ST", ".SW", ".PA", ".DE", ".L",
    ".TO", ".V", ".SI", ".MI", ".AS", ".SS", ".SZ", ".NS", ".BO",
]

FOTO_PUBLIC_API = "https://jdkfnvgkfwotjlyovbrk.supabase.co/functions/v1/fund-public-api"
TEMA_HOLDINGS_CSV = "https://temaetfs.com/hubfs/Website/Holdings/{ticker}-holdings.csv"
TEMA_FUND_URL = "https://temaetfs.com/{ticker}"

# Yahoo can retain the former security type when a ticker is reassigned.  LAZR
# was reassigned to Tema's Photonics & Optical ETF in 2026, but Yahoo currently
# reports the new fund name alongside quoteType=EQUITY.  Issuer-confirmed
# identities take precedence over that field.
ISSUER_CONFIRMED_ETFS = {"FOTO", "EUV", "LAZR"}
ETF_INCEPTION_DATES = {
    "LAZR": "2026-06-30",
}

BLOOMBERG_TO_YAHOO_SUFFIX = {
    "US": "",
    "UW": "",
    "UN": "",
    "UQ": "",
    "GR": ".DE",
    "JP": ".T",
    "HK": ".HK",
    "LN": ".L",
    "FP": ".PA",
    "SS": ".ST",
    "TT": ".TWO",
    "C1": ".SS",
    "C2": ".SZ",
    "SZ": ".SZ",
}

CURRENCY_SYMBOLS = {
    "USD": "$",
    "KRW": "₩",
    "TWD": "NT$",
    "EUR": "€",
    "JPY": "¥",
    "GBP": "£",
    "INR": "₹",
    "CHF": "CHF ",
    "CAD": "C$",
    "AUD": "A$",
    "HKD": "HK$",
    "CNY": "¥",
}

def get_currency_symbol(currency_code):
    if not currency_code:
        return ""
    return CURRENCY_SYMBOLS.get(str(currency_code).upper(), f"{currency_code} ")

def parse_arguments():
    # Handle custom -? help flag before argparse processes it
    if "-?" in sys.argv or "/?" in sys.argv:
        sys.argv = [sys.argv[0], "-h"]

    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="ETF Portfolio Mapping Engine V8 - ETF Mapping + Focus Pipeline"
    )
    parser.add_argument("-t", "--tickers", type=str, help="Comma-separated ETF tickers")
    parser.add_argument("-f", "--file", type=str, default=None, help="Path to a file containing ETF tickers")
    parser.add_argument("--theme", type=str, help="Comma-separated theme terms")
    parser.add_argument("--classifier-file", type=str, default="D:\\Tools\\StockCodeMaster\\03_ETF\\01-07-US_ETF_Classification_Mapping.csv", help="CSV file containing ETF classification data")
    parser.add_argument(
        "-o",
        "--output",
        "--output-file",
        "--output-dir",
        dest="output",
        type=str,
        default=None,
        help="Output filename (or path). If not provided, file is created in current working directory.",
    )
    
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)
    return parser.parse_args()

def extract_tickers_from_file(file_path):
    if not os.path.exists(file_path):
        print(f"\n[ERROR] Ticker source file not found at: '{file_path}'")
        print("Please check your file path string or provide an alternative workspace directory.")
        raise FileNotFoundError(f"Input file does not exist: {file_path}")
    print(f"[INFO] Reading ETF ticker source file: {file_path}")
    extracted_tickers = []
    header_keywords = {
        "symbol", "ticker", "etf", "code", "equitycode", "equity code",
        "stock ticker", "stock code", "company code", "company ticker"
    }
    is_first_line = True

    with open(file_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row or not any(cell.strip() for cell in row):
                continue

            first_value = row[0].strip()
            if not first_value:
                continue

            if is_first_line:
                is_first_line = False
                normalized_header = re.sub(r"[^a-z0-9]+", " ", first_value.lower()).strip()
                if first_value.lower() in header_keywords or normalized_header in header_keywords:
                    continue

            symbol = first_value.upper()
            if is_valid_ticker_symbol(symbol):
                extracted_tickers.append(symbol)

    print(f"[SUCCESS] Extracted {len(extracted_tickers)} ETF rows from file.")
    return extracted_tickers

def extract_tickers_from_theme(classifier_file, theme_string):
    if not classifier_file:
        print("\n[ERROR] Theme execution missing structural path registry.")
        print("Command execution requires `--classifier-file` argument when defining a target `--theme`.")
        raise ValueError("--classifier-file is required when using --theme mode")
    if not os.path.exists(classifier_file):
        print(f"\n[ERROR] Theme classifier reference file not found at: '{classifier_file}'")
        print("Verify your local registry directory coordinates before repeating theme lookups.")
        raise FileNotFoundError(f"Classifier metadata registry does not exist: {classifier_file}")
    
    print(f"[INFO] Scanning classifier mapping registry: {classifier_file} for theme keys: '{theme_string}'")
    df = pd.read_csv(classifier_file, encoding="utf-8-sig")
    if "ETF_Code" not in df.columns:
        raise ValueError("Classifier file missing mandatory column header: 'ETF_Code'")
        
    searchable_columns = [col for col in df.columns if col.lower() not in {"etf_code", "include"}]
    if "Include" in df.columns:
        df = df[df["Include"].astype(str).str.upper().str.strip().isin(["Y", "YES", "TRUE", "1"])]
        
    df["_SEARCH_TEXT"] = df[searchable_columns].fillna("").astype(str).agg(" ".join, axis=1).str.lower()
    theme_terms = [term.strip().lower() for term in theme_string.split(",") if term.strip()]
    
    filtered = df.copy()
    for term in theme_terms:
        filtered = filtered[filtered["_SEARCH_TEXT"].str.contains(re.escape(term), na=False)]
        
    selected = filtered["ETF_Code"].astype(str).str.upper().str.strip().replace("", pd.NA).dropna().drop_duplicates().tolist()
    if not selected:
        print(f"\n[WARNING] Theme scan completed successfully but returned 0 results for input keys: '{theme_string}'.")
        print("Check if your CSV classification strings contain alternate naming matches.")
    else:
        print(f"[SUCCESS] Theme matching filter selected {len(selected)} operational ETFs: {selected}")
    return selected, filtered.drop(columns=["_SEARCH_TEXT"], errors="ignore")

def format_market_cap(value, currency_sym):
    if value is None or pd.isna(value) or value == "N/A":
        return "N/A"
    try:
        val = float(value)
        if val >= 1e12: return f"{currency_sym}{val / 1e12:.2f}T"
        if val >= 1e9: return f"{currency_sym}{val / 1e9:.2f}B"
        if val >= 1e6: return f"{currency_sym}{val / 1e6:.2f}M"
        return f"{currency_sym}{val:,.0f}"
    except Exception:
        return "N/A"

def fetch_company_metadata(ticker, company_name=None):
    try:
        resolved_ticker = resolve_international_ticker(ticker)
        t = yf.Ticker(resolved_ticker)
        info = t.info
        market_cap = info.get("marketCap", "N/A")
        price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose") or "N/A"
        currency_code = info.get("currency", "")
        country = info.get("country", "Unknown")
        exchange = info.get("exchange", "Unknown")
        location = f"{country} ({exchange})" if country != "Unknown" else exchange
        symbol = get_currency_symbol(currency_code)
        formatted_market_cap = format_market_cap(market_cap, symbol)
        formatted_price = f"{symbol}{float(price):.2f}" if price != "N/A" else "N/A"
        resolution_status = "Exact" if str(resolved_ticker).upper() == str(ticker).upper() else "Resolved"
        instrument_type, classification_basis = classify_instrument(ticker, info, company_name)
        return (
            ticker,
            resolved_ticker,
            formatted_market_cap,
            formatted_price,
            location,
            resolution_status,
            instrument_type,
            classification_basis,
        )
    except Exception:
        instrument_type, classification_basis = classify_instrument(ticker, {}, company_name)
        return (
            ticker,
            ticker,
            "N/A",
            "N/A",
            "Unknown",
            "Unresolved",
            instrument_type,
            classification_basis,
        )


def classify_instrument(ticker, yahoo_info=None, company_name=None):
    """Classify a holding without treating Yahoo quoteType as authoritative.

    Ticker reuse can leave Yahoo's security type stale.  Curated issuer evidence
    and an explicit fund name therefore outrank quoteType.
    """
    cleaned_ticker = str(ticker or "").strip().upper()
    info = yahoo_info if isinstance(yahoo_info, dict) else {}

    if cleaned_ticker in ISSUER_CONFIRMED_ETFS:
        return "ETF", "Issuer-confirmed ETF ticker"

    names = " ".join(
        str(value or "")
        for value in [
            company_name,
            info.get("longName"),
            info.get("shortName"),
            info.get("displayName"),
        ]
    ).upper()
    if re.search(r"\bETF\b", names) or "EXCHANGE TRADED FUND" in names or "EXCHANGE-TRADED FUND" in names:
        return "ETF", "Fund name"

    quote_type = str(info.get("quoteType") or "").strip().upper()
    if quote_type == "ETF":
        return "ETF", "Yahoo quoteType"
    if quote_type in {"MUTUALFUND", "MONEYMARKET"}:
        return "Fund", "Yahoo quoteType"
    if quote_type == "EQUITY":
        return "Stock", "Yahoo quoteType"
    return "Unknown", "Insufficient metadata"


def partition_holding_views(raw_holdings):
    """Separate company, listed-stock, and nested-fund reporting views."""
    instrument_types = raw_holdings["Instrument Type"].fillna("Unknown")
    nested_fund_mask = instrument_types.isin(["ETF", "Fund"])
    private_or_other_mask = instrument_types.isin(["Private Company", "Cash"])
    return (
        raw_holdings.loc[~nested_fund_mask].copy(),
        raw_holdings.loc[~nested_fund_mask & ~private_or_other_mask].copy(),
        raw_holdings.loc[nested_fund_mask].copy(),
    )


def _ticker_has_price_history(ticker):
    try:
        hist = yf.Ticker(ticker).history(period="1mo", auto_adjust=False, actions=False)
        return hist is not None and not hist.empty and "Close" in hist.columns
    except Exception:
        return False


def resolve_international_ticker(ticker):
    base = str(ticker).strip().upper()
    if not base:
        return base

    # Already exchange-qualified or prefixed.
    if any(sep in base for sep in [".", ":", "="]):
        return base

    # Keep valid live symbols as-is.
    if _ticker_has_price_history(base):
        return base

    # Numeric / local codes often require exchange suffixes (e.g., 6301.T).
    for suffix in INTL_SUFFIX_CANDIDATES:
        candidate = f"{base}{suffix}"
        if _ticker_has_price_history(candidate):
            return candidate

    return base


def _normalize_weight(raw_weight):
    try:
        if raw_weight is None or pd.isna(raw_weight):
            return 0.0
        if isinstance(raw_weight, str):
            raw_weight = raw_weight.replace("%", "").replace(",", "").strip()
        weight = float(raw_weight)
        if weight > 1.0:
            weight = weight / 100.0
        if weight < 0:
            return 0.0
        return weight
    except Exception:
        return 0.0


def _percentage_points_to_weight(raw_weight):
    """Convert an issuer field expressed in percentage points to a fraction."""
    try:
        if raw_weight is None or pd.isna(raw_weight):
            return 0.0
        if isinstance(raw_weight, str):
            raw_weight = raw_weight.replace("%", "").replace(",", "").strip()
        return max(0.0, float(raw_weight) / 100.0)
    except Exception:
        return 0.0


def _upsert_holding(
    holdings_dict,
    ticker,
    name,
    weight,
    source_ticker=None,
    instrument_type=None,
    classification_basis=None,
):
    t_key = str(ticker).strip().upper()
    if not t_key or t_key == "NAN":
        return
    if not is_valid_ticker_symbol(t_key):
        return

    w = _normalize_weight(weight)
    if t_key not in holdings_dict or w > holdings_dict[t_key]["Weight"]:
        holdings_dict[t_key] = {
            "Company Ticker": t_key,
            "Company Name": str(name).strip() if name else t_key,
            "Weight": w,
            "Source Ticker": str(source_ticker or ticker).strip().upper(),
            "Instrument Type": instrument_type,
            "Classification Basis": classification_basis,
        }


def _read_html_tables_with_timeout(url, timeout_seconds=8):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        return pd.read_html(StringIO(html))
    except Exception:
        return []


def _read_url_text(url, timeout_seconds=12, accept="text/html,application/json"):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": accept,
        },
    )
    with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def _normalize_issuer_ticker(raw_ticker):
    value = str(raw_ticker or "").strip().upper()
    if not value or value in {"N/A", "NONE", "NAN", "CASH&OTHER"}:
        return ""

    # Normalize exchange-prefixed and Bloomberg-style labels while preserving
    # ordinary Yahoo-compatible tickers such as BRK.B and RDS-A.
    if ":" in value:
        value = value.split(":", 1)[1].strip()
    parts = value.split()
    if len(parts) == 2 and parts[1] in BLOOMBERG_TO_YAHOO_SUFFIX:
        value = parts[0] + BLOOMBERG_TO_YAHOO_SUFFIX[parts[1]]
    return value if is_valid_ticker_symbol(value) else ""


def _select_canonical_company_name(names, fallback_ticker=""):
    candidates = []
    for raw_name in names:
        if raw_name is None or pd.isna(raw_name):
            continue
        name = str(raw_name).strip()
        if name and name.upper() not in {"NAN", "NONE"}:
            candidates.append(name)

    if not candidates:
        return str(fallback_ticker).strip().upper()

    # Prefer readable issuer names over all-caps security descriptions and
    # generic instrument suffixes such as "COMMON STOCK".
    return min(
        candidates,
        key=lambda name: (
            name == name.upper(),
            "COMMON STOCK" in name.upper(),
            len(name),
            name.upper(),
        ),
    )


def fetch_holdings_from_foto_issuer(etf_ticker):
    """Return FOTO's issuer-reported underlying company exposures.

    FOTO holds equities directly and through receive/payable total-return-swap
    legs.  The receive leg represents the underlying equity exposure; the
    payable leg and cash/T-bill collateral are financing instruments and must
    not be counted as separate portfolio companies.
    """
    if str(etf_ticker).strip().upper() != "FOTO":
        return []

    try:
        url = f"{FOTO_PUBLIC_API}?ticker=FOTO&view=all"
        payload = json.loads(_read_url_text(url, accept="application/json"))
        raw_holdings = payload.get("holdings") or []
    except Exception:
        return []

    aggregated = {}
    for item in raw_holdings:
        if not isinstance(item, dict):
            continue

        name = str(item.get("security_name") or "").strip()
        upper_name = name.upper()
        if upper_name.startswith("PAYB "):
            continue

        raw_ticker = item.get("security_ticker")
        receive_match = re.match(
            r"^RECV\s+FOTO\s+TRS\s+([A-Z0-9.\-]+)\s+EQ$",
            upper_name,
        )
        if receive_match:
            raw_ticker = receive_match.group(1)

        ticker = _normalize_issuer_ticker(raw_ticker)
        if not ticker or ticker == "TLDR" or "CASH" in upper_name:
            continue

        weight = _percentage_points_to_weight(item.get("weight"))
        if weight <= 0:
            continue

        if ticker not in aggregated:
            aggregated[ticker] = {
                "Company Ticker": ticker,
                "Company Name": ticker if receive_match else (name or ticker),
                "Weight": 0.0,
            }
        aggregated[ticker]["Weight"] += weight
        if not receive_match and name:
            aggregated[ticker]["Company Name"] = name

    return list(aggregated.values())


def fetch_holdings_from_corgi_issuer(etf_ticker):
    """Read the complete holdings snapshot embedded in a Corgi fund page."""
    cleaned_ticker = str(etf_ticker).strip().upper()
    if cleaned_ticker != "EUV":
        return []

    try:
        html = _read_url_text(f"https://corgifunds.com/{cleaned_ticker.lower()}")
    except Exception:
        return []

    holdings_dict = {}
    object_pattern = re.compile(r'\{[^{}]*"security_ticker"[^{}]*"weight_pct"[^{}]*\}')
    for match in object_pattern.finditer(html):
        try:
            item = json.loads(match.group(0))
        except (TypeError, ValueError, json.JSONDecodeError):
            continue

        ticker = _normalize_issuer_ticker(item.get("security_ticker"))
        if not ticker:
            continue
        _upsert_holding(
            holdings_dict,
            ticker,
            item.get("security_name") or ticker,
            _percentage_points_to_weight(item.get("weight_pct")),
        )

    return list(holdings_dict.values())


def fetch_holdings_from_tema_issuer(etf_ticker):
    """Read Tema's complete daily holdings file for issuer-confirmed ETFs."""
    cleaned_ticker = str(etf_ticker).strip().upper()
    if cleaned_ticker != "LAZR":
        return []

    try:
        csv_text = _read_url_text(
            TEMA_HOLDINGS_CSV.format(ticker=cleaned_ticker),
            accept="text/csv",
        )
        frame = pd.read_csv(StringIO(csv_text))
    except Exception:
        return []

    holdings_dict = {}
    for _, row in frame.iterrows():
        is_cash = str(row.get("is_cash") or "").strip().lower() in {"1", "true", "yes", "y"}
        if is_cash:
            continue

        source_ticker = str(row.get("ticker") or "").strip().upper()
        name = str(row.get("proper_name") or source_ticker).strip()
        instrument_type = "Stock"
        classification_basis = "Tema issuer holdings"

        if "SPV" in source_ticker or "SPV" in name.upper():
            # Preserve private-company exposure in the raw/company views while
            # avoiding a doomed Yahoo lookup for a non-exchange symbol.
            ticker = re.sub(r"[^A-Z0-9]+", "-", source_ticker).strip("-")[:20]
            instrument_type = "Private Company"
        else:
            ticker = _normalize_issuer_ticker(source_ticker)

        if not ticker:
            continue

        _upsert_holding(
            holdings_dict,
            ticker,
            name or ticker,
            row.get("percent_of_nav"),
            source_ticker=source_ticker,
            instrument_type=instrument_type,
            classification_basis=classification_basis,
        )

    return list(holdings_dict.values())


def fetch_tema_fund_metrics(etf_ticker):
    """Return current issuer metrics that Yahoo may corrupt after ticker reuse."""
    cleaned_ticker = str(etf_ticker).strip().upper()
    if cleaned_ticker != "LAZR":
        return {}

    try:
        html = _read_url_text(TEMA_FUND_URL.format(ticker=cleaned_ticker.lower()))
    except Exception:
        return {}

    def numeric_match(pattern):
        match = re.search(pattern, html, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            return None
        try:
            return float(match.group(1).replace(",", ""))
        except (TypeError, ValueError):
            return None

    aum = numeric_match(
        r"<span>\s*AUM\s*</span>.*?<div[^>]*class=[\"']col-details[\"'][^>]*>\s*\$([\d,.]+)"
    )
    nav = numeric_match(r"<span>\s*NAV\s*</span>\s*<span>\s*\$([\d,.]+)")
    market_price = numeric_match(r"<span>\s*Market Price\s*</span>\s*<span>\s*\$([\d,.]+)")
    as_of_match = re.search(
        r"LAZR NAV / Market Price.*?As of\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )

    return {
        "Name": "Tema Photonics & Optical ETF",
        "AUM (USD M)": round(aum / 1_000_000.0, 2) if aum is not None else None,
        "NAV": nav,
        "Market Price": market_price,
        "As Of": as_of_match.group(1) if as_of_match else None,
    }


def fetch_holdings_from_issuer(etf_ticker):
    cleaned_ticker = str(etf_ticker).strip().upper()
    if cleaned_ticker == "FOTO":
        return fetch_holdings_from_foto_issuer(cleaned_ticker)
    if cleaned_ticker == "EUV":
        return fetch_holdings_from_corgi_issuer(cleaned_ticker)
    if cleaned_ticker == "LAZR":
        return fetch_holdings_from_tema_issuer(cleaned_ticker)
    return []


def fetch_holdings_from_fmp(etf_ticker):
    # Free/demo endpoint; if unavailable the function safely returns []
    url = f"https://financialmodelingprep.com/api/v3/etf-holder/{etf_ticker}?apikey=demo"
    holdings = []
    try:
        df = pd.read_json(url)
        if df is None or df.empty:
            return holdings

        df_cols = {c.lower(): c for c in df.columns}
        ticker_col = next((df_cols[k] for k in ["asset", "symbol", "ticker"] if k in df_cols), None)
        name_col = next((df_cols[k] for k in ["name", "companyname", "company_name"] if k in df_cols), None)
        weight_col = next((df_cols[k] for k in ["weightpercentage", "weight", "holdingpercent"] if k in df_cols), None)

        if not ticker_col:
            return holdings

        for _, row in df.iterrows():
            symbol = row.get(ticker_col)
            if symbol is None or pd.isna(symbol):
                continue
            holdings.append(
                {
                    "Company Ticker": str(symbol).strip().upper(),
                    "Company Name": str(row.get(name_col)).strip() if name_col and row.get(name_col) is not None else str(symbol).strip().upper(),
                    "Weight": _normalize_weight(row.get(weight_col) if weight_col else 0.0),
                }
            )
    except Exception:
        return []

    return holdings


def fetch_holdings_from_stockanalysis(etf_ticker):
    # Free HTML table source (no API key). Useful when APIs return only top holdings.
    url = f"https://stockanalysis.com/etf/{str(etf_ticker).lower()}/holdings/"
    holdings = []
    try:
        tables = _read_html_tables_with_timeout(url)
        if not tables:
            return holdings

        best_df = None
        for table in tables:
            cols = [str(c).strip().lower() for c in table.columns]
            if any(c in cols for c in ["symbol", "ticker"]) and any("weight" in c for c in cols):
                best_df = table
                break

        if best_df is None or best_df.empty:
            return holdings

        table_cols = {str(c).strip().lower(): c for c in best_df.columns}
        ticker_col = next((table_cols[k] for k in ["symbol", "ticker"] if k in table_cols), None)
        name_col = next((table_cols[k] for k in ["name", "company", "holding"] if k in table_cols), None)
        weight_col = next((orig for low, orig in table_cols.items() if "weight" in low), None)

        if not ticker_col:
            return holdings

        for _, row in best_df.iterrows():
            symbol = row.get(ticker_col)
            if symbol is None or pd.isna(symbol):
                continue
            holdings.append(
                {
                    "Company Ticker": str(symbol).strip().upper(),
                    "Company Name": str(row.get(name_col)).strip() if name_col and row.get(name_col) is not None else str(symbol).strip().upper(),
                    "Weight": _normalize_weight(row.get(weight_col) if weight_col else 0.0),
                }
            )
    except Exception:
        return []

    return holdings


def _extract_holdings_from_html_table(df):
    holdings = []
    if df is None or df.empty:
        return holdings

    table_cols = {str(c).strip().lower(): c for c in df.columns}
    ticker_col = next((table_cols[k] for k in ["symbol", "ticker"] if k in table_cols), None)
    name_col = next((table_cols[k] for k in ["holding", "name", "company"] if k in table_cols), None)
    weight_col = next((orig for low, orig in table_cols.items() if "% assets" in low or "weight" in low or "percent" in low), None)

    if not ticker_col:
        return holdings

    for _, row in df.iterrows():
        symbol = row.get(ticker_col)
        if symbol is None or pd.isna(symbol):
            continue
        holdings.append(
            {
                "Company Ticker": str(symbol).strip().upper(),
                "Company Name": str(row.get(name_col)).strip() if name_col and row.get(name_col) is not None else str(symbol).strip().upper(),
                "Weight": _normalize_weight(row.get(weight_col) if weight_col else 0.0),
            }
        )

    return holdings


def fetch_holdings_from_etfdb(etf_ticker):
    # Free holdings table scrape (best-effort)
    url = f"https://etfdb.com/etf/{str(etf_ticker).upper()}/#holdings"
    holdings = []
    try:
        tables = _read_html_tables_with_timeout(url)
        if not tables:
            return holdings

        for table in tables:
            rows = _extract_holdings_from_html_table(table)
            if rows:
                holdings.extend(rows)
                break
    except Exception:
        return []

    return holdings


def fetch_holdings_from_etftrends(etf_ticker):
    # Free ETF Trends table scrape (best-effort)
    # Site paths can vary; this fallback is intentionally tolerant.
    candidate_urls = [
        f"https://www.etftrends.com/etf/{str(etf_ticker).lower()}/",
        f"https://www.etftrends.com/{str(etf_ticker).lower()}/",
    ]
    for url in candidate_urls:
        try:
            tables = _read_html_tables_with_timeout(url)
            if not tables:
                continue
            for table in tables:
                rows = _extract_holdings_from_html_table(table)
                if rows:
                    return rows
        except Exception:
            continue
    return []

def fetch_etf_market_and_holdings(etf_ticker):
    cleaned_ticker = etf_ticker.strip().upper()
    if cleaned_ticker.startswith("XNSE:"):
        cleaned_ticker = cleaned_ticker.replace("XNSE:", "") + ".NS"
    try:
        ticker_obj = yf.Ticker(cleaned_ticker)
        info = ticker_obj.info
        instrument_type, classification_basis = classify_instrument(cleaned_ticker, info)
        print(
            f"  [IDENTITY] {cleaned_ticker} -> {instrument_type} "
            f"({classification_basis}; Yahoo quoteType={info.get('quoteType') or 'N/A'})"
        )
        current_price = info.get("currentPrice") or info.get("navPrice") or info.get("regularMarketPrice") or info.get("previousClose") or "N/A"
        if isinstance(current_price, (int, float)):
            current_price = round(current_price, 2)
        etf_currency = info.get("currency", "")
        symbol = get_currency_symbol(etf_currency)
        formatted_etf_price = f"{symbol}{float(current_price):.2f}" if current_price != "N/A" else "Error"
        
        holdings_dict = {}
        source_counts = {
            "YF_funds_data": 0,
            "YF_get_holdings": 0,
            "YF_holdings": 0,
            "Issuer": 0,
            "FMP": 0,
            "StockAnalysis": 0,
            "ETFDB": 0,
            "ETFTrends": 0,
        }

        # Prefer a complete, same-day issuer snapshot when one is available.
        # This prevents a top-10 Yahoo response from becoming the final universe
        # and avoids blending stale rows from several different snapshots.
        issuer_holdings = fetch_holdings_from_issuer(cleaned_ticker)
        for holding in issuer_holdings:
            _upsert_holding(
                holdings_dict,
                holding.get("Company Ticker"),
                holding.get("Company Name"),
                holding.get("Weight", 0.0),
                source_ticker=holding.get("Source Ticker"),
                instrument_type=holding.get("Instrument Type"),
                classification_basis=holding.get("Classification Basis"),
            )
        source_counts["Issuer"] = len(holdings_dict)
        
        # Discovery Method A: Standard fund_data endpoint sweep
        before_count = len(holdings_dict)
        if not issuer_holdings and hasattr(ticker_obj, "funds_data") and ticker_obj.funds_data is not None:
            for source_attr in ["top_holdings", "equity_holdings"]:
                if hasattr(ticker_obj.funds_data, source_attr):
                    holdings_df = getattr(ticker_obj.funds_data, source_attr)
                    if holdings_df is not None and not holdings_df.empty:
                        for comp_ticker, row in holdings_df.iterrows():
                            comp_name = str(row.get("Name", "")).strip()
                            weight = row.get("Holding Percent", 0)
                            if weight > 1.0: weight = weight / 100.0
                            if comp_ticker and str(comp_ticker).lower() != "nan" and str(comp_ticker).strip() != "":
                                _upsert_holding(holdings_dict, comp_ticker, comp_name if comp_name else comp_ticker, weight)
        source_counts["YF_funds_data"] = max(0, len(holdings_dict) - before_count)

        # Discovery Method B: Comprehensive fallback method execution
        before_count = len(holdings_dict)
        if not holdings_dict and hasattr(ticker_obj, "get_holdings"):
            try:
                fallback_df = ticker_obj.get_holdings()
                if fallback_df is not None and not fallback_df.empty:
                    tick_col = next((c for c in fallback_df.columns if "symbol" in c.lower() or "ticker" in c.lower()), None)
                    name_col = next((c for c in fallback_df.columns if "name" in c.lower() or "company" in c.lower()), None)
                    pct_col = next((c for c in fallback_df.columns if "percent" in c.lower() or "weight" in c.lower() or "holding" in c.lower()), None)
                    
                    if tick_col:
                        for _, row in fallback_df.iterrows():
                            c_tick = str(row[tick_col]).strip().upper()
                            if c_tick and c_tick != "NAN" and c_tick != "":
                                c_name = str(row[name_col]).strip() if name_col else c_tick
                                c_weight = float(row[pct_col]) if pct_col else 0.0
                                if c_weight > 1.0: c_weight = c_weight / 100.0
                                _upsert_holding(holdings_dict, c_tick, c_name, c_weight)
            except Exception:
                pass
        source_counts["YF_get_holdings"] = max(0, len(holdings_dict) - before_count)

        # Discovery Method C: Clean raw property dictionary parsing
        before_count = len(holdings_dict)
        if not holdings_dict and hasattr(ticker_obj, "holdings") and ticker_obj.holdings is not None:
            try:
                raw_dict_holdings = ticker_obj.holdings
                if isinstance(raw_dict_holdings, list):
                    for h_item in raw_dict_holdings:
                        if isinstance(h_item, dict):
                            c_tick = str(h_item.get("symbol", h_item.get("ticker", ""))).strip().upper()
                            if c_tick and c_tick != "NAN" and c_tick != "":
                                c_name = str(h_item.get("name", h_item.get("holdingName", c_tick))).strip()
                                c_weight = float(h_item.get("holdingPercent", h_item.get("weight", 0.0)))
                                if c_weight > 1.0: c_weight = c_weight / 100.0
                                _upsert_holding(holdings_dict, c_tick, c_name, c_weight)
            except Exception:
                pass
        source_counts["YF_holdings"] = max(0, len(holdings_dict) - before_count)

        # Discovery Method D: Free FMP endpoint (best-effort, no hard dependency)
        if not issuer_holdings:
            before_count = len(holdings_dict)
            fmp_holdings = fetch_holdings_from_fmp(cleaned_ticker)
            for holding in fmp_holdings:
                _upsert_holding(
                    holdings_dict,
                    holding.get("Company Ticker"),
                    holding.get("Company Name"),
                    holding.get("Weight", 0.0),
                )
            source_counts["FMP"] = max(0, len(holdings_dict) - before_count)

        # Discovery Method E: StockAnalysis holdings table scrape (best-effort fallback)
        if not issuer_holdings:
            before_count = len(holdings_dict)
            sa_holdings = fetch_holdings_from_stockanalysis(cleaned_ticker)
            for holding in sa_holdings:
                _upsert_holding(
                    holdings_dict,
                    holding.get("Company Ticker"),
                    holding.get("Company Name"),
                    holding.get("Weight", 0.0),
                )
            source_counts["StockAnalysis"] = max(0, len(holdings_dict) - before_count)

        # Discovery Method F/G: Additional free table sources for deeper constituent coverage.
        # Only trigger when current count is still shallow to control latency.
        if not issuer_holdings and len(holdings_dict) < 15:
            before_count = len(holdings_dict)
            etfdb_holdings = fetch_holdings_from_etfdb(cleaned_ticker)
            for holding in etfdb_holdings:
                _upsert_holding(
                    holdings_dict,
                    holding.get("Company Ticker"),
                    holding.get("Company Name"),
                    holding.get("Weight", 0.0),
                )
            source_counts["ETFDB"] = max(0, len(holdings_dict) - before_count)

        if not issuer_holdings and len(holdings_dict) < 15:
            before_count = len(holdings_dict)
            etftrends_holdings = fetch_holdings_from_etftrends(cleaned_ticker)
            for holding in etftrends_holdings:
                _upsert_holding(
                    holdings_dict,
                    holding.get("Company Ticker"),
                    holding.get("Company Name"),
                    holding.get("Weight", 0.0),
                )
            source_counts["ETFTrends"] = max(0, len(holdings_dict) - before_count)
                                    
        holdings_list = list(holdings_dict.values())
        print(f"  [PARSED] ETF: {etf_ticker} | Harvested Constituents: {len(holdings_list)}")
        print(
            "  [SOURCES] "
            f"YF_funds={source_counts['YF_funds_data']}, "
            f"YF_get={source_counts['YF_get_holdings']}, "
            f"YF_raw={source_counts['YF_holdings']}, "
            f"Issuer={source_counts['Issuer']}, "
            f"FMP={source_counts['FMP']}, "
            f"StockAnalysis={source_counts['StockAnalysis']}, "
            f"ETFDB={source_counts['ETFDB']}, "
            f"ETFTrends={source_counts['ETFTrends']}, "
            f"TotalUnique={len(holdings_list)}"
        )
        return formatted_etf_price, holdings_list, None
    except Exception as e:
        print(f"  [WARNING] Data API extraction failed for target '{etf_ticker}': {e}")
        return "Error", [], str(e)

def safe_theme_name(theme_string):
    name = theme_string.strip().replace(",", "_").replace(" ", "").replace("&", "And").replace("/", "_")
    return re.sub(r"[^A-Za-z0-9_\-]", "", name) or "Theme"

def build_output_filename(args):
    date_tag = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
    if args.theme:
        return f"{safe_theme_name(args.theme)}_Portfolio-{date_tag}.xlsx"
    return f"ETFCode_PortfolioMapping-{date_tag}.xlsx"


def resolve_output_path(cli_output, default_filename):
    if cli_output is None:
        return os.path.abspath(os.path.join(os.getcwd(), default_filename))

    value = str(cli_output).strip()
    if not value:
        raise ValueError("Output filename cannot be empty.")

    # If user passes only a filename, write to current working directory.
    candidate = value if os.path.isabs(value) else os.path.join(os.getcwd(), value)
    output_path = os.path.abspath(candidate)

    if os.path.isdir(output_path):
        raise ValueError(f"Output must be a file name/path, not a directory: {output_path}")

    base_name = os.path.basename(output_path)
    root_name, ext = os.path.splitext(base_name)
    if not root_name:
        raise ValueError("Output filename is invalid.")

    if not ext:
        output_path = output_path + ".xlsx"
    elif ext.lower() != ".xlsx":
        raise ValueError("Output file extension must be .xlsx")

    parent_dir = os.path.dirname(output_path) or os.getcwd()
    if not os.path.exists(parent_dir):
        raise ValueError(f"Output directory does not exist: {parent_dir}")

    return output_path

def print_no_etf_message():
    print("\n" + "=" * 80 + "\n [CRITICAL CONFIGURATION FAULT] ETF UNIVERSE BLANK\n" + "=" * 80)
    print("\nNo tracking ETF data sources or matching inputs were supplied.")
    print("Please use one of the following clear command execution paths:")
    print("  1. Direct Ticker Entry  : -t SMH,SOXX,QQQ")
    print("  2. Local File Read Path : -f ETF_List.txt")
    print("  3. Thematic Filter Mode : --theme \"Europe,Chips\" --classifier-file ETF_Master_Classification.csv\n")

def is_valid_ticker_symbol(ticker_str):
    """
    Prevents Yahoo benchmark metrics (e.g. 'PRICE/BOOK', 'MEDIAN MARKET CAP') 
    from hitting the background threading execution pool.
    """
    if not ticker_str or pd.isna(ticker_str):
        return False
    t_clean = str(ticker_str).strip().upper()
    if re.fullmatch(r"\d+(\.\d+)?", t_clean):
        return False
    if any(metric in t_clean for metric in ["MARKET CAP", "GROWTH", "PRICE/", "VALUATION", "YIELD", "TURNOVER"]):
        return False
    if not re.fullmatch(r"[A-Z0-9][A-Z0-9.\-:=]{0,19}", t_clean):
        return False
    # Drop strings that contain more than 2 blank spaces (identifies pure word titles)
    if len(t_clean.split(" ")) > 2:
        return False
    return True


def normalize_yahoo_symbol(ticker):
    value = str(ticker).strip().upper()
    if value.startswith("XNSE:"):
        return value.split(":", 1)[1] + ".NS"
    if value.startswith("XNSE") and ":" not in value:
        return value.replace("XNSE", "", 1) + ".NS"
    return value


def ensure_runtime_dependencies():
    # yfinance repair pipeline can require scipy for historical-price cleanup.
    if importlib.util.find_spec("scipy") is None:
        print("\n[CRITICAL DEPENDENCY MISSING] scipy is required for price history repair and benchmark calculations.", file=sys.stderr)
        print("Install it in your active environment and re-run:", file=sys.stderr)
        print(f"  \"{sys.executable}\" -m pip install scipy", file=sys.stderr)
        sys.exit(1)


def fetch_price_history_series(ticker):
    yf_symbol = normalize_yahoo_symbol(ticker)
    ticker_obj = yf.Ticker(yf_symbol)
    history_kwargs = {
        "period": "max",
        "auto_adjust": True,
        "actions": True,
        "repair": True,
    }

    try:
        history = ticker_obj.history(**history_kwargs)
    except ModuleNotFoundError as error:
        if getattr(error, "name", "") != "scipy":
            raise
        print(f"  [WARN] scipy not installed; retrying price history for {yf_symbol} with repair=False")
        history_kwargs["repair"] = False
        try:
            history = ticker_obj.history(**history_kwargs)
        except Exception as retry_error:
            print(f"  [WARN] Price history unavailable for {yf_symbol}: {retry_error}")
            return ticker_obj, None, None
    except Exception as error:
        print(f"  [WARN] Price history unavailable for {yf_symbol}: {error}")
        return ticker_obj, None, None

    if history is None or history.empty or "Close" not in history.columns:
        return ticker_obj, None, history

    history.index = pd.to_datetime(history.index).tz_localize(None)
    prices = pd.to_numeric(history["Close"], errors="coerce").dropna().sort_index()
    inception_date = ETF_INCEPTION_DATES.get(str(ticker).strip().upper())
    if inception_date:
        inception_timestamp = pd.Timestamp(inception_date)
        history = history.loc[history.index >= inception_timestamp].copy()
        prices = prices.loc[prices.index >= inception_timestamp]
    if prices.empty:
        return ticker_obj, None, history

    return ticker_obj, prices, history


def calculate_price_performance(prices):
    if prices is None or len(prices) < 2:
        return {}

    prices = prices.dropna().sort_index()
    last_date = pd.Timestamp(prices.index[-1])

    def index_on_or_before(date_value):
        position = prices.index.searchsorted(pd.Timestamp(date_value), side="right") - 1
        return position if position >= 0 else None

    def index_before(date_value):
        position = prices.index.searchsorted(pd.Timestamp(date_value), side="left") - 1
        return position if position >= 0 else None

    def return_between(start_date, end_date=None, use_previous_close=False):
        end_date = last_date if end_date is None else pd.Timestamp(end_date)

        if use_previous_close:
            start_index = index_before(start_date)
        else:
            start_index = index_on_or_before(start_date)

        end_index = index_on_or_before(end_date)
        if start_index is None or end_index is None or end_index <= start_index:
            return None

        start_price = float(prices.iloc[start_index])
        end_price = float(prices.iloc[end_index])
        if start_price <= 0:
            return None

        return round(((end_price / start_price) - 1.0) * 100.0, 2)

    week_start = last_date.normalize() - pd.Timedelta(days=last_date.weekday())
    month_start = pd.Timestamp(last_date.year, last_date.month, 1)
    year_start = pd.Timestamp(last_date.year, 1, 1)

    previous_month_end = month_start - pd.Timedelta(days=1)
    previous_month_start = pd.Timestamp(previous_month_end.year, previous_month_end.month, 1)

    two_months_ago_end = previous_month_start - pd.Timedelta(days=1)
    two_months_ago_start = pd.Timestamp(two_months_ago_end.year, two_months_ago_end.month, 1)

    return {
        "LTP": round(float(prices.iloc[-1]), 2),
        "Since Yesterday (%)": round(
            ((float(prices.iloc[-1]) / float(prices.iloc[-2])) - 1.0) * 100.0, 2
        ),
        "This Week (%)": return_between(week_start, use_previous_close=True),
        "MTD (%)": return_between(month_start, use_previous_close=True),
        previous_month_start.strftime("%b-%y (%%)"): return_between(
            previous_month_start, previous_month_end, use_previous_close=True
        ),
        two_months_ago_start.strftime("%b-%y (%%)"): return_between(
            two_months_ago_start, two_months_ago_end, use_previous_close=True
        ),
        "3 Month (%)": return_between(last_date - pd.DateOffset(months=3)),
        "YTD (%)": return_between(year_start, use_previous_close=True),
        "6 Month (%)": return_between(last_date - pd.DateOffset(months=6)),
        "9 Month (%)": return_between(last_date - pd.DateOffset(months=9)),
        "1 Year (%)": return_between(last_date - pd.DateOffset(years=1)),
    }


def compute_etf_risk_metrics(prices, benchmark_prices, risk_free_rate=0.04):
    result = {"Beta": None, "Alpha (Ann. %)": None}
    if prices is None or benchmark_prices is None:
        return result

    aligned = pd.concat(
        [prices.rename("Instrument"), benchmark_prices.rename("Benchmark")],
        axis=1,
        join="inner",
    ).dropna()

    if len(aligned) < 30:
        return result

    aligned = aligned.iloc[-756:]
    returns = aligned.pct_change().dropna()
    if len(returns) < 20:
        return result

    instrument_returns = returns["Instrument"]
    benchmark_returns = returns["Benchmark"]
    benchmark_variance = benchmark_returns.var(ddof=1)
    if pd.isna(benchmark_variance) or benchmark_variance == 0:
        return result

    beta = instrument_returns.cov(benchmark_returns) / benchmark_variance
    result["Beta"] = round(float(beta), 2)

    daily_rf = risk_free_rate / 252.0
    alpha_daily = (instrument_returns - daily_rf).mean() - beta * (benchmark_returns - daily_rf).mean()
    result["Alpha (Ann. %)"] = round(float(alpha_daily * 252.0 * 100.0), 2)
    return result


def get_etf_aum_usd_m(ticker_obj, info):
    value = info.get("totalAssets")
    if value is None:
        try:
            value = ticker_obj.fast_info.get("marketCap")
        except Exception:
            value = None
    try:
        return round(float(value) / 1_000_000.0, 2) if value is not None else None
    except (TypeError, ValueError):
        return None


def get_latest_trading_volume(history):
    if history is None or history.empty or "Volume" not in history.columns:
        return None
    volume = pd.to_numeric(history["Volume"], errors="coerce").dropna()
    if volume.empty:
        return None
    return int(volume.iloc[-1])


def build_etf_performance_row(etf_ticker, benchmark_prices):
    ticker_obj, prices, history = fetch_price_history_series(etf_ticker)

    info = {}
    try:
        info = ticker_obj.info or {}
    except Exception:
        info = {}

    performance = calculate_price_performance(prices)
    risk_metrics = compute_etf_risk_metrics(prices, benchmark_prices)
    cleaned_ticker = str(etf_ticker).strip().upper()
    issuer_metrics = fetch_tema_fund_metrics(cleaned_ticker)

    return {
        "Ticker": cleaned_ticker,
        "Name": issuer_metrics.get("Name") or str(info.get("longName") or info.get("shortName") or "").strip(),
        "AUM (USD M)": issuer_metrics.get("AUM (USD M)")
        if issuer_metrics.get("AUM (USD M)") is not None
        else get_etf_aum_usd_m(ticker_obj, info),
        "Last Trading Volume": get_latest_trading_volume(history),
        "LTP": performance.pop("LTP", None),
        **risk_metrics,
        **performance,
    }


def _autosize_worksheet_columns(worksheet, min_width=10, max_width=45):
    for column_cells in worksheet.columns:
        max_length = max(
            len(str(cell.value)) if cell.value is not None else 0
            for cell in column_cells
        )
        worksheet.column_dimensions[column_cells[0].column_letter].width = min(max(max_length + 2, min_width), max_width)


def _apply_dynamic_rank_rules(worksheet, column_number, first_data_row=2):
    if worksheet.max_row < first_data_row:
        return

    red_fill = PatternFill(fill_type="solid", fgColor="FFFF0000")
    yellow_fill = PatternFill(fill_type="solid", fgColor="FFFFFF00")
    green_fill = PatternFill(fill_type="solid", fgColor="FF92D050")

    letter = openpyxl.utils.get_column_letter(column_number)
    data_range = f"{letter}{first_data_row}:{letter}{worksheet.max_row}"

    worksheet.conditional_formatting.add(
        data_range,
        FormulaRule(
            formula=[f"AND(COUNT({letter}:{letter})>=1,ISNUMBER({letter}{first_data_row}),{letter}{first_data_row}=MAX({letter}:{letter}))"],
            fill=red_fill,
        ),
    )
    worksheet.conditional_formatting.add(
        data_range,
        FormulaRule(
            formula=[f"AND(COUNT({letter}:{letter})>=2,ISNUMBER({letter}{first_data_row}),{letter}{first_data_row}=LARGE({letter}:{letter},2),{letter}{first_data_row}<>MAX({letter}:{letter}))"],
            fill=yellow_fill,
        ),
    )
    worksheet.conditional_formatting.add(
        data_range,
        FormulaRule(
            formula=[f"AND(COUNT({letter}:{letter})>=1,ISNUMBER({letter}{first_data_row}),{letter}{first_data_row}=MIN({letter}:{letter}))"],
            fill=green_fill,
        ),
    )


def apply_etf_performance_formatting(file_path):
    workbook = openpyxl.load_workbook(file_path)
    if "ETF Performance" not in workbook.sheetnames:
        workbook.save(file_path)
        return

    worksheet = workbook["ETF Performance"]
    if worksheet.max_row < 2:
        workbook.save(file_path)
        return

    worksheet.conditional_formatting._cf_rules.clear()

    headers = [worksheet.cell(row=1, column=i).value for i in range(1, worksheet.max_column + 1)]
    column_numbers = {
        str(name).strip(): index + 1
        for index, name in enumerate(headers)
        if name is not None
    }

    percentage_columns = [name for name in column_numbers if str(name).endswith("(%)")]
    for column_name in percentage_columns:
        _apply_dynamic_rank_rules(worksheet, column_numbers[column_name], first_data_row=2)

    for row in range(2, worksheet.max_row + 1):
        for name in percentage_columns:
            worksheet.cell(row=row, column=column_numbers[name]).number_format = "0.00"

        for name in ["LTP", "Beta", "Alpha (Ann. %)"]:
            if name in column_numbers:
                worksheet.cell(row=row, column=column_numbers[name]).number_format = "0.00"

        for name in ["AUM (USD M)", "Last Trading Volume"]:
            if name in column_numbers:
                worksheet.cell(row=row, column=column_numbers[name]).number_format = "#,##0"

    worksheet.freeze_panes = "A2"
    worksheet.auto_filter.ref = f"A1:{openpyxl.utils.get_column_letter(worksheet.max_column)}{worksheet.max_row}"
    _autosize_worksheet_columns(worksheet)
    workbook.save(file_path)


def apply_etf_summary_formatting(file_path):
    workbook = openpyxl.load_workbook(file_path)
    if "ETF_Summary" in workbook.sheetnames:
        worksheet = workbook["ETF_Summary"]
    elif "ETF Summary" in workbook.sheetnames:
        worksheet = workbook["ETF Summary"]
    else:
        workbook.save(file_path)
        return

    if worksheet.max_row < 2:
        workbook.save(file_path)
        return

    worksheet.conditional_formatting._cf_rules.clear()

    headers = [worksheet.cell(row=1, column=i).value for i in range(1, worksheet.max_column + 1)]
    column_numbers = {
        str(name).strip(): index + 1
        for index, name in enumerate(headers)
        if name is not None
    }

    rank_columns = [
        "Holding_Count",
        "Total_Holding_Weight",
        "Avg_Holding_Weight",
        "Max_Holding_Weight",
    ]
    for name in rank_columns:
        if name in column_numbers:
            _apply_dynamic_rank_rules(worksheet, column_numbers[name], first_data_row=2)

    for row in range(2, worksheet.max_row + 1):
        if "Holding_Count" in column_numbers:
            worksheet.cell(row=row, column=column_numbers["Holding_Count"]).number_format = "#,##0"
        for name in [
            "Total_Holding_Weight",
            "Avg_Holding_Weight",
            "Max_Holding_Weight",
            "LTP",
            "Beta",
            "Alpha (Ann. %)",
        ]:
            if name in column_numbers:
                worksheet.cell(row=row, column=column_numbers[name]).number_format = "0.00"
        for name in [name for name in column_numbers if str(name).endswith("(%)")]:
            worksheet.cell(row=row, column=column_numbers[name]).number_format = "0.00"
        if "AUM (USD M)" in column_numbers:
            worksheet.cell(row=row, column=column_numbers["AUM (USD M)"]).number_format = "#,##0.00"
        if "Last Trading Volume" in column_numbers:
            worksheet.cell(row=row, column=column_numbers["Last Trading Volume"]).number_format = "#,##0"

    worksheet.freeze_panes = "A2"
    worksheet.auto_filter.ref = f"A1:{openpyxl.utils.get_column_letter(worksheet.max_column)}{worksheet.max_row}"
    _autosize_worksheet_columns(worksheet)
    workbook.save(file_path)


def apply_stock_summary_formatting(file_path):
    workbook = openpyxl.load_workbook(file_path)
    if "Stock_Summary" not in workbook.sheetnames:
        workbook.save(file_path)
        return

    worksheet = workbook["Stock_Summary"]
    headers = [worksheet.cell(row=1, column=i).value for i in range(1, worksheet.max_column + 1)]
    column_numbers = {
        str(name).strip(): index + 1
        for index, name in enumerate(headers)
        if name is not None
    }

    for row in range(2, worksheet.max_row + 1):
        if "ETF_Count" in column_numbers:
            worksheet.cell(row=row, column=column_numbers["ETF_Count"]).number_format = "#,##0"
        for name in ["Total_Weight_Across_ETFs", "Avg_Weight_When_Present", "Max_Weight_In_One_ETF"]:
            if name in column_numbers:
                worksheet.cell(row=row, column=column_numbers[name]).number_format = "0.00"

    worksheet.freeze_panes = "A2"
    worksheet.auto_filter.ref = f"A1:{openpyxl.utils.get_column_letter(worksheet.max_column)}{worksheet.max_row}"
    _autosize_worksheet_columns(worksheet)
    workbook.save(file_path)


def apply_raw_holdings_formatting(file_path, sheet_name="RAW_Holdings"):
    workbook = openpyxl.load_workbook(file_path)
    if sheet_name not in workbook.sheetnames:
        workbook.save(file_path)
        return

    worksheet = workbook[sheet_name]
    headers = [worksheet.cell(row=1, column=i).value for i in range(1, worksheet.max_column + 1)]
    column_numbers = {
        str(name).strip(): index + 1
        for index, name in enumerate(headers)
        if name is not None
    }

    if "Weight" in column_numbers:
        for row in range(2, worksheet.max_row + 1):
            worksheet.cell(row=row, column=column_numbers["Weight"]).number_format = "0.00%"

    worksheet.freeze_panes = "A2"
    worksheet.auto_filter.ref = f"A1:{openpyxl.utils.get_column_letter(worksheet.max_column)}{worksheet.max_row}"
    _autosize_worksheet_columns(worksheet)
    workbook.save(file_path)


def apply_matrix_formatting(file_path):
    workbook = openpyxl.load_workbook(file_path)
    if "Matrix" not in workbook.sheetnames:
        workbook.save(file_path)
        return

    worksheet = workbook["Matrix"]
    if worksheet.max_row < 2:
        workbook.save(file_path)
        return

    worksheet.conditional_formatting._cf_rules.clear()

    headers = [worksheet.cell(row=1, column=i).value for i in range(1, worksheet.max_column + 1)]
    column_numbers = {
        str(name).strip(): index + 1
        for index, name in enumerate(headers)
        if name is not None
    }

    rank_columns = ["ETF_Count", "Total_Weight_Across_ETFs"]
    for name in rank_columns:
        if name in column_numbers:
            _apply_dynamic_rank_rules(worksheet, column_numbers[name], first_data_row=2)

    for row in range(2, worksheet.max_row + 1):
        if "ETF_Count" in column_numbers:
            worksheet.cell(row=row, column=column_numbers["ETF_Count"]).number_format = "#,##0"
        if "Total_Weight_Across_ETFs" in column_numbers:
            worksheet.cell(row=row, column=column_numbers["Total_Weight_Across_ETFs"]).number_format = "0.00"

    worksheet.freeze_panes = "A2"
    worksheet.auto_filter.ref = f"A1:{openpyxl.utils.get_column_letter(worksheet.max_column)}{worksheet.max_row}"
    _autosize_worksheet_columns(worksheet)
    workbook.save(file_path)


def sort_etf_summary_by_mtd(etf_summary_df):
    result = etf_summary_df.copy()
    if "MTD (%)" not in result.columns:
        return result

    result["MTD (%)"] = pd.to_numeric(result["MTD (%)"], errors="coerce")
    tie_breakers = ["MTD (%)"]
    ascending = [False]
    if "ETF_Code" in result.columns:
        tie_breakers.append("ETF_Code")
        ascending.append(True)
    return result.sort_values(
        by=tie_breakers,
        ascending=ascending,
        na_position="last",
    ).reset_index(drop=True)


def main():
    args = parse_arguments()
    ensure_runtime_dependencies()

    output_filename = build_output_filename(args)
    try:
        output_path = resolve_output_path(args.output, output_filename)
    except Exception as e:
        print(f"[CRITICAL ERR] Output file configuration error: {e}", file=sys.stderr)
        sys.exit(1)

    combined_tickers = []
    theme_selection_df = None

    if args.tickers:
        combined_tickers.extend([t.strip().upper() for t in args.tickers.replace("\ufeff", "").split(",") if t.strip()])
    if args.file:
        try: combined_tickers.extend(extract_tickers_from_file(args.file))
        except Exception as e: print(f"[CRITICAL ERR] Input configuration file path failed to read: {e}", file=sys.stderr); sys.exit(1)
    if args.theme:
        print("This input flag is still WIP")
        sys.exit(0)

    unique_etfs = sorted(set(combined_tickers))
    if not unique_etfs:
        print_no_etf_message()
        sys.exit(0)

    print("\n================================================================================")
    print(f"INITIALIZING WORKLOAD: HARVESTING PORTFOLIOS FOR {len(unique_etfs)} TARGET ETFS")
    print("================================================================================")
    
    master_holdings_records = []
    etf_prices_summary = {}
    failed_etfs = {}

    for etf in unique_etfs:
        price, holdings, err_msg = fetch_etf_market_and_holdings(etf)
        if err_msg or price == "Error":
            failed_etfs[etf] = err_msg if err_msg else "Price Lookup Failed"
            etf_prices_summary[etf] = "Error"
            continue
        etf_prices_summary[etf] = price

        for holding in holdings:
            master_holdings_records.append({
                "ETF_Code": etf,
                "Company Ticker": holding["Company Ticker"],
                "Company Name": holding["Company Name"],
                "Weight": holding["Weight"],
                "Source Ticker": holding.get("Source Ticker", holding["Company Ticker"]),
                "Instrument Type": holding.get("Instrument Type"),
                "Classification Basis": holding.get("Classification Basis"),
            })

    if not master_holdings_records:
        print("\n[CRITICAL FAILURE] Pipeline halted: No constituent stock rows could be harvested from the specified universe.")
        if failed_etfs:
            print(f"Current Exception Manifest: {failed_etfs}")
        sys.exit(1)

    raw_df = pd.DataFrame(master_holdings_records)
    raw_df["Company Ticker"] = raw_df["Company Ticker"].astype(str).str.upper().str.strip()
    raw_df["Company Name"] = raw_df["Company Name"].fillna(raw_df["Company Ticker"]).astype(str).str.strip()
    canonical_company_names = {
        ticker: _select_canonical_company_name(group["Company Name"], ticker)
        for ticker, group in raw_df.groupby("Company Ticker", sort=False)
    }
    raw_df["Company Name"] = raw_df["Company Ticker"].map(canonical_company_names)
    
    # Private/SPV rows remain visible but are not sent through Yahoo's public-
    # security resolver.
    metadata_rows = raw_df.loc[~raw_df["Instrument Type"].isin(["Private Company", "Cash"])]
    unique_company_tickers = sorted([
        t
        for t in metadata_rows["Company Ticker"].unique().tolist()
        if t and t != "NAN" and is_valid_ticker_symbol(t)
    ])
    print(f"\nParallel background threading online. Pulling fundamental layers for {len(unique_company_tickers)} stocks...")
    resolved_ticker_map = {}
    resolution_status_map = {}
    instrument_type_map = {}
    classification_basis_map = {}
    company_metadata = {}
    with ThreadPoolExecutor(max_workers=15) as executor:
        future_to_ticker = {
            executor.submit(fetch_company_metadata, ticker, canonical_company_names.get(ticker)): ticker
            for ticker in unique_company_tickers
        }
        for i, future in enumerate(as_completed(future_to_ticker), 1):
            (
                ticker,
                resolved_ticker,
                market_cap,
                price,
                location,
                resolution_status,
                instrument_type,
                classification_basis,
            ) = future.result()
            resolved_ticker_map[ticker] = resolved_ticker
            resolution_status_map[ticker] = resolution_status
            instrument_type_map[ticker] = instrument_type
            classification_basis_map[ticker] = classification_basis
            company_metadata[resolved_ticker] = {"Market Cap": market_cap, "LTP": price, "Location": location}
            if i % 10 == 0 or i == len(unique_company_tickers):
                print(f"  Progress: Aligned context metadata for {i}/{len(unique_company_tickers)} assets.")

    # Preserve the exact ETF-published symbol in Company Ticker.
    # Use Resolved Ticker only for metadata/price enrichment.
    raw_df["Resolved Ticker"] = raw_df["Company Ticker"].map(lambda t: resolved_ticker_map.get(t, t))
    raw_df["Resolution Status"] = raw_df["Company Ticker"].map(lambda t: resolution_status_map.get(t, "Unresolved"))

    raw_df["Listed Exchange"] = raw_df["Resolved Ticker"].map(lambda t: company_metadata.get(t, {}).get("Location", "Unknown"))
    raw_df["Company Market Cap"] = raw_df["Resolved Ticker"].map(lambda t: company_metadata.get(t, {}).get("Market Cap", "N/A"))
    raw_df["Company LTP"] = raw_df["Resolved Ticker"].map(lambda t: company_metadata.get(t, {}).get("LTP", "N/A"))

    declared_types = raw_df["Instrument Type"].fillna("").astype(str).str.strip()
    declared_bases = raw_df["Classification Basis"].fillna("").astype(str).str.strip()
    raw_df["Instrument Type"] = declared_types.where(
        declared_types.ne(""),
        raw_df["Company Ticker"].map(lambda t: instrument_type_map.get(t, "Unknown")),
    )
    raw_df["Classification Basis"] = declared_bases.where(
        declared_bases.ne(""),
        raw_df["Company Ticker"].map(lambda t: classification_basis_map.get(t, "Insufficient metadata")),
    )

    # A fund held by another fund is retained in RAW_Holdings and
    # Nested_Funds, but must not be presented as a company in Matrix or
    # Stock_Summary.  Look-through expansion is intentionally not automatic.
    company_holdings_df, stock_holdings_df, nested_funds_df = partition_holding_views(raw_df)

    print("\nEngineering and pivoting baseline allocation tracking cross-tabulation matrix...")
    matrix_df = company_holdings_df.pivot_table(
        index=["Company Name", "Company Ticker", "Listed Exchange", "Company Market Cap", "Company LTP"],
        columns="ETF_Code",
        values="Weight",
        aggfunc="first",
        fill_value=0.0,
    )
    matrix_df = matrix_df.reindex(columns=unique_etfs, fill_value=0.0)
    matrix_df["ETF_Count"] = (matrix_df[unique_etfs] > 0).sum(axis=1)
    matrix_df["Total_Weight_Across_ETFs"] = round( matrix_df[unique_etfs].sum(axis=1) * 100,2)
    matrix_df = matrix_df[(matrix_df["ETF_Count"] > 0) & (matrix_df["Total_Weight_Across_ETFs"] > 0)]
    matrix_df = matrix_df.sort_values(by=["ETF_Count", "Total_Weight_Across_ETFs"], ascending=[False, False])
    
    final_matrix_df = matrix_df.reset_index()
    for etf in unique_etfs:
        final_matrix_df[etf] = final_matrix_df[etf].apply(lambda x: f"{x * 100:.2f}%" if x > 0 else "")

    etf_summary_df = raw_df.groupby("ETF_Code").agg(
        Holding_Count=("Company Ticker", "nunique"),
        Total_Holding_Weight=("Weight", "sum"),
        Avg_Holding_Weight=("Weight", "mean"),
        Max_Holding_Weight=("Weight", "max"),
    ).reset_index()
    etf_summary_df["Total_Holding_Weight"] *= 100
    etf_summary_df["Avg_Holding_Weight"] *= 100
    etf_summary_df["Max_Holding_Weight"] *= 100
    etf_summary_df["ETF_Price"] = etf_summary_df["ETF_Code"].map(etf_prices_summary)

    stock_summary_df = stock_holdings_df.groupby(["Company Ticker", "Company Name", "Listed Exchange"]).agg(
        ETF_Count=("ETF_Code", "nunique"),
        Total_Weight_Across_ETFs=("Weight", "sum"),
        Avg_Weight_When_Present=("Weight", "mean"),
        Max_Weight_In_One_ETF=("Weight", "max"),
    ).reset_index()
    stock_summary_df["Total_Weight_Across_ETFs"] *= 100
    stock_summary_df["Avg_Weight_When_Present"] *= 100
    stock_summary_df["Max_Weight_In_One_ETF"] *= 100
    stock_summary_df = stock_summary_df[
        (stock_summary_df["Total_Weight_Across_ETFs"] > 0)
        & (stock_summary_df["Max_Weight_In_One_ETF"] > 0)
    ]
    stock_summary_df = stock_summary_df.rename(columns={"Company Ticker": "Stock Ticker", "Listed Exchange": "Exchange"})
    stock_summary_df = stock_summary_df[
        ["Stock Ticker", "Company Name", "Exchange", "ETF_Count", "Total_Weight_Across_ETFs", "Avg_Weight_When_Present", "Max_Weight_In_One_ETF"]
    ]
    stock_summary_df = stock_summary_df.sort_values(by=["ETF_Count", "Total_Weight_Across_ETFs"], ascending=[False, False])

    print("\nBuilding ETF performance benchmark sheet (period returns, AUM, Volume, Alpha, Beta, LTP)...")
    _, benchmark_prices, _ = fetch_price_history_series("SPY")
    etf_performance_rows = []
    for etf in unique_etfs:
        try:
            etf_performance_rows.append(build_etf_performance_row(etf, benchmark_prices))
        except Exception:
            etf_performance_rows.append({
                "Ticker": etf,
                "Name": "",
                "AUM (USD M)": None,
                "Last Trading Volume": None,
                "LTP": None,
                "Beta": None,
                "Alpha (Ann. %)": None,
            })

    etf_performance_df = pd.DataFrame(etf_performance_rows)
    performance_front = [
        "Ticker", "Name", "AUM (USD M)", "Last Trading Volume", "LTP",
        "Beta", "Alpha (Ann. %)", "Since Yesterday (%)", "This Week (%)", "MTD (%)",
    ]
    performance_back = ["3 Month (%)", "YTD (%)", "6 Month (%)", "9 Month (%)", "1 Year (%)"]
    performance_middle = [c for c in etf_performance_df.columns if c not in performance_front + performance_back]
    etf_performance_df = etf_performance_df.reindex(columns=performance_front + performance_middle + performance_back)
    if "MTD (%)" in etf_performance_df.columns:
        etf_performance_df["MTD (%)"] = pd.to_numeric(etf_performance_df["MTD (%)"], errors="coerce")
        etf_performance_df = etf_performance_df.sort_values(by=["MTD (%)", "Ticker"], ascending=[False, True], na_position="last").reset_index(drop=True)

    etf_summary_enhanced_df = etf_summary_df.merge(
        etf_performance_df,
        left_on="ETF_Code",
        right_on="Ticker",
        how="left",
    ).drop(columns=["Ticker"], errors="ignore")
    etf_summary_enhanced_df = sort_etf_summary_by_mtd(etf_summary_enhanced_df)

    try:
        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            matrix_export_df = final_matrix_df.rename(columns={
                "Company Ticker": "Ticker",
                "Listed Exchange": "Exchange",
                "Company Market Cap": "Market Cap",
                "Company LTP": "Price",
            })

            matrix_front_columns = [
                "Ticker",
                "Company Name",
                "Exchange",
                "Market Cap",
                "Price",
                "ETF_Count",
                "Total_Weight_Across_ETFs",
            ]
            matrix_etf_columns = [etf for etf in unique_etfs if etf in matrix_export_df.columns]
            matrix_export_df = matrix_export_df.reindex(columns=matrix_front_columns + matrix_etf_columns)

            price_row_df = pd.DataFrame(
                [["", "", "", "", "", "", ""] + [str(etf_prices_summary.get(etf, "N/A")) for etf in matrix_etf_columns]],
                columns=matrix_front_columns + matrix_etf_columns,
            )
            combined_matrix_export = pd.concat([price_row_df, matrix_export_df], ignore_index=True)

            raw_holdings_export_df = raw_df.rename(columns={
                "Company Ticker": "Stock Ticker",
                "Listed Exchange": "Exchange",
                "Company Market Cap": "Market Cap",
                "Company LTP": "Price",
            })
            raw_holdings_columns = [
                "ETF_Code",
                "Stock Ticker",
                "Company Name",
                "Exchange",
                "Market Cap",
                "Price",
                "Weight",
                "Source Ticker",
                "Resolved Ticker",
                "Resolution Status",
                "Instrument Type",
                "Classification Basis",
            ]
            raw_holdings_export_df = raw_holdings_export_df.reindex(columns=[
                col for col in raw_holdings_columns if col in raw_holdings_export_df.columns
            ])
            nested_funds_export_df = nested_funds_df.rename(columns={
                "Company Ticker": "Stock Ticker",
                "Listed Exchange": "Exchange",
                "Company Market Cap": "Market Cap",
                "Company LTP": "Price",
            }).reindex(columns=raw_holdings_export_df.columns)

            print("  [LAYOUT] Matrix columns -> " + " | ".join(combined_matrix_export.columns.tolist()))
            print("  [LAYOUT] RAW_Holdings columns -> " + " | ".join(raw_holdings_export_df.columns.tolist()))

            combined_matrix_export.to_excel(writer, sheet_name="Matrix", index=False)
            etf_summary_enhanced_df.to_excel(writer, sheet_name="ETF_Summary", index=False)
            stock_summary_df.to_excel(writer, sheet_name="Stock_Summary", index=False)
            raw_holdings_export_df.to_excel(writer, sheet_name="RAW_Holdings", index=False)
            nested_funds_export_df.to_excel(writer, sheet_name="Nested_Funds", index=False)
            if theme_selection_df is not None:
                theme_selection_df.to_excel(writer, sheet_name="Theme Selection", index=False)
            pd.DataFrame(
                [{"ETF_Code": k, "Error": v} for k, v in failed_etfs.items()],
                columns=["ETF_Code", "Error"],
            ).to_excel(writer, sheet_name="FaILED_ETF", index=False)

        apply_etf_summary_formatting(output_path)
        apply_stock_summary_formatting(output_path)
        apply_raw_holdings_formatting(output_path)
        apply_raw_holdings_formatting(output_path, sheet_name="Nested_Funds")
        apply_matrix_formatting(output_path)
        
        print("\n================================================================================")
        print("ARTIFACT EXPORT MATRIX COMPLETED SUCCESSFULLY")
        print("================================================================================")
        print(f"  File Target Path : {output_path}")
        print(f"  Unique ETFs      : {len(unique_etfs)} parsed ({len(failed_etfs)} errors noted)")
        print(f"  List of Unique ETFs : {list(unique_etfs)} ")
        print(f"  Public Securities: {len(unique_company_tickers)} entities cross-mapped safely.")
        print("================================================================================")
        
    except Exception as e:
        print(f"\n[FATAL ERROR] System I/O block when compiling spreadsheet file: {e}", file=sys.stderr); sys.exit(1)

if __name__ == "__main__":
    main()
