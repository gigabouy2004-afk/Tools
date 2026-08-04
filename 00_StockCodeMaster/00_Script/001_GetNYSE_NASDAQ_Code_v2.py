import pandas as pd
from ftplib import FTP
import io
import json
import re
import time
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.request import Request, urlopen

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_OUTPUT_FILE = SCRIPT_DIR / "14-06-Master_Ticker_List_Base.csv"
FINAL_OUTPUT_FILE = SCRIPT_DIR / "14-06-NYSE_NASDAQ_Master_Library.csv"
COMMON_STOCK_OUTPUT_FILE = SCRIPT_DIR / "14-06-NYSE_NASDAQ_Common_Stocks_Master_Library.csv"
ETF_OUTPUT_FILE = SCRIPT_DIR / "14-06-NYSE_NASDAQ_ETF_Master_Library.csv"

RUN_ENRICHMENT = True

COMMON_EQUITY_INCLUDE_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"\bCommon Stock\b",
        r"\bCommon Shares?\b",
        r"\bOrdinary Shares?\b",
        r"\bCapital Stock\b",
        r"\bAmerican Depositary Shares?\b",
        r"\bAmerican Depositary Receipts?\b",
        r"\bGlobal Depositary Shares?\b",
        r"\bNew York Registry Shares?\b",
        r"\bNY Registry Shares?\b",
        r"\bRegistered Shares?\b",
        r"\bVoting Shares?\b",
        r"\bADR\b",
        r"\bADS\b",
    ]
]

COMMON_EQUITY_EXCLUDE_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"\bWarrants?\b",
        r"\bRights?\b",
        r"\bUnits?\b",
        r"\bPreferred\b",
        r"\bPreference\b",
        r"\bNotes?\b",
        r"\bBonds?\b",
        r"\bDebentures?\b",
        r"\bETF\b",
        r"\bETN\b",
        r"\bFund\b",
        r"\bClosed[- ]End\b",
        r"\bPurchase Contracts?\b",

    ]
]

ETF_CATEGORY_PATTERNS = [
    (
        "Target US Treasury",
        re.compile(
            r"(?=.*\btarget\b)(?=.*\b(?:u\.?s\.?|united states)\s+treasur(?:y|ies)\b)",
            re.IGNORECASE,
        ),
    ),
    (
        "Leveraged",
        re.compile(
            r"\bleverag(?:e|ed|es)\b|\b[234]\s*x\b|\b[234]x\b|\bultra(?:pro)?\b|\bdaily target\b",
            re.IGNORECASE,
        ),
    ),
    ("Short", re.compile(r"\bshort\b|\binverse\b", re.IGNORECASE)),
    ("Bull", re.compile(r"\bbull\b", re.IGNORECASE)),
    ("Long", re.compile(r"\blong\b", re.IGNORECASE)),
    ("Bear", re.compile(r"\bbear\b", re.IGNORECASE)),
    (
        "Bond",
        re.compile(
            r"\bbonds?\b|\bfixed income\b|\btreasur(?:y|ies)\b|\bmunicipal\b|\bmuni\b|\bCLO\b|\bdebt\b|\bloans?\b|\bmortgage\b|\bhigh yield\b",
            re.IGNORECASE,
        ),
    ),
    ("Income", re.compile(r"\bincome\b|\byield\b", re.IGNORECASE)),
]

NASDAQ_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/json,text/plain,*/*",
    "Origin": "https://www.nasdaq.com",
    "Referer": "https://www.nasdaq.com/",
}

NASDAQ_STOCKS_URL = (
    "https://api.nasdaq.com/api/screener/stocks"
    "?tableonly=true&limit=25000&offset=0&download=true"
)
NASDAQ_ETF_URL = "https://api.nasdaq.com/api/screener/etf?download=true"

def download_exchange_list():
    """Downloads the master traded list from NASDAQ FTP."""
    print("Connecting to NASDAQ FTP...")
    try:
        ftp = FTP('ftp.nasdaqtrader.com')
        ftp.login()
        ftp.cwd('SymbolDirectory')
        
        r = io.BytesIO()
        ftp.retrbinary('RETR nasdaqtraded.txt', r.write)
        ftp.quit()
        
        r.seek(0)
        df = pd.read_csv(r, sep='|')
        return df.iloc[:-1] # Remove metadata footer
    except Exception as e:
        print(f"FTP Error: {e}")
        return None

def filter_and_clean(df):
    """
    Filters for primary exchanges and enforces strict alphanumeric symbols.
    Excludes rows with missing symbols to prevent ValueError.
    """
    # N=NYSE, P=NYSE Arca, A=NYSE American, Q=NASDAQ
    valid_exchanges = ['N', 'P', 'A', 'Q'] 
    
    # 1. Basic Exchange and Test Issue Filter
    df_filtered = df[
        (df['Test Issue'] == 'N') & 
        (df['Listing Exchange'].isin(valid_exchanges))
    ].copy()

    # 2. Fix for "Cannot mask with non-boolean array": Drop NaN symbols
    df_filtered = df_filtered.dropna(subset=['Symbol'])

    # 3. Filter for strictly alphanumeric symbols (No hyphens, dots, or suffixes)
    mask = df_filtered['Symbol'].str.isalnum()
    df_clean = df_filtered[mask].copy()
    
    df_clean['Ticker'] = df_clean['Symbol']
    
    return df_clean[
        ['Ticker', 'Symbol', 'Security Name', 'Listing Exchange', 'Market Category', 'ETF']
    ]

def download_json(url, retries=3):
    """Download NASDAQ JSON with short retry handling for transient edge errors."""
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            request = Request(url, headers=NASDAQ_HEADERS)
            with urlopen(request, timeout=45) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as e:
            last_error = e
            if attempt < retries:
                wait_seconds = attempt * 2
                print(f"NASDAQ request failed ({e}). Retrying in {wait_seconds}s...")
                time.sleep(wait_seconds)

    raise RuntimeError(f"NASDAQ request failed after {retries} attempts: {last_error}")


def extract_rows(payload):
    """Handle both NASDAQ screener JSON layouts."""
    data = payload.get("data", {})
    if isinstance(data, dict) and isinstance(data.get("rows"), list):
        return data["rows"]

    nested_data = data.get("data") if isinstance(data, dict) else None
    if isinstance(nested_data, dict) and isinstance(nested_data.get("rows"), list):
        return nested_data["rows"]

    return []


def parse_number(value):
    """Convert NASDAQ formatted numeric strings into ints/floats for sorting."""
    if value is None:
        return None

    text = str(value).strip()
    if not text or text.upper() in {"N/A", "NA", "NONE", "--"}:
        return None

    text = text.replace("$", "").replace(",", "").replace("%", "")
    try:
        number = Decimal(text)
    except InvalidOperation:
        return None

    if number == number.to_integral_value():
        return int(number)
    return float(number)


def clean_text(value):
    if value is None:
        return None

    text = str(value).strip()
    if not text or text.upper() in {"N/A", "NA", "NONE", "--"}:
        return None

    return text


def matches_any_pattern(text, patterns):
    return any(pattern.search(text) for pattern in patterns)


def is_common_equity_security(security_name):
    """Return True for common-share style listings, including ADR/ADS listings."""
    text = clean_text(security_name)
    if not text:
        return False

    if matches_any_pattern(text, COMMON_EQUITY_EXCLUDE_PATTERNS):
        return False

    return matches_any_pattern(text, COMMON_EQUITY_INCLUDE_PATTERNS)


def classify_etf_categories(security_name):
    """Classify ETFs by security name only; unmatched ETFs are plain ETFs."""
    text = clean_text(security_name)
    if not text:
        return "Plain ETF"

    categories = [
        category
        for category, pattern in ETF_CATEGORY_PATTERNS
        if pattern.search(text)
    ]

    if not categories:
        return "Plain ETF"

    return "; ".join(categories)


def add_etf_classification(etf_df):
    etf_df = etf_df.copy()
    etf_df["ETF_Category"] = etf_df["Security Name"].apply(classify_etf_categories)
    etf_df["ETF_Type"] = etf_df["ETF_Category"].where(
        etf_df["ETF_Category"].eq("Plain ETF"),
        "Special ETF",
    )

    columns = list(etf_df.columns)
    for column in ["ETF_Type", "ETF_Category"]:
        columns.remove(column)

    etf_column_index = columns.index("ETF") + 1 if "ETF" in columns else len(columns)
    columns[etf_column_index:etf_column_index] = ["ETF_Type", "ETF_Category"]
    return etf_df[columns]


def sort_stock_output(stocks_df):
    if "MarketCap" in stocks_df.columns:
        return stocks_df.sort_values(
            by="MarketCap",
            ascending=False,
            na_position="last",
        )

    return stocks_df.sort_values(by="Ticker")


def sort_etf_output(etf_df):
    etf_df = etf_df.copy()
    etf_df["_ETF_TYPE_ORDER"] = etf_df["ETF_Type"].map(
        {"Plain ETF": 0, "Special ETF": 1}
    ).fillna(2)

    sort_columns = ["_ETF_TYPE_ORDER", "ETF_Category", "Ticker"]
    return etf_df.sort_values(by=sort_columns).drop(columns=["_ETF_TYPE_ORDER"])


def normalize_market_cap(master_df):
    master_df = master_df.copy()
    if "MarketCap" in master_df.columns:
        master_df["MarketCap"] = pd.to_numeric(
            master_df["MarketCap"],
            errors="coerce",
        ).astype("Int64")

    return master_df


def write_split_outputs(master_df):
    master_df = normalize_market_cap(master_df)
    stocks_df = master_df[
        (master_df["ETF"] == "N")
        & master_df["Security Name"].apply(is_common_equity_security)
    ].copy()
    etf_df = master_df[master_df["ETF"] == "Y"].copy()

    stocks_df = sort_stock_output(stocks_df)
    etf_df = sort_etf_output(add_etf_classification(etf_df))

    stocks_df.to_csv(COMMON_STOCK_OUTPUT_FILE, index=False)
    etf_df.to_csv(ETF_OUTPUT_FILE, index=False)

    return stocks_df, etf_df


def fetch_bulk_enrichment():
    """
    Fetch enrichment data in two bulk NASDAQ calls.

    yfinance's Ticker.info endpoint is intentionally avoided here. It performs
    one Yahoo request per symbol and quickly triggers 429/401 crumb failures for
    full-market runs.
    """
    print("Downloading NASDAQ stock screener data...")
    stock_rows = extract_rows(download_json(NASDAQ_STOCKS_URL))
    print(f"NASDAQ stock screener rows received: {len(stock_rows)}")

    print("Downloading NASDAQ ETF screener data...")
    etf_rows = extract_rows(download_json(NASDAQ_ETF_URL))
    print(f"NASDAQ ETF screener rows received: {len(etf_rows)}")

    enrichment = {}

    for row in stock_rows:
        ticker = clean_text(row.get("symbol"))
        if not ticker:
            continue

        enrichment[ticker.upper()] = {
            "Ticker": ticker.upper(),
            "MarketCap": parse_number(row.get("marketCap")),
            "TrailingPE": None,
            "ForwardPE": None,
            "Sector": clean_text(row.get("sector")),
            "Industry": clean_text(row.get("industry")),
        }

    for row in etf_rows:
        ticker = clean_text(row.get("symbol"))
        if not ticker:
            continue

        key = ticker.upper()
        enrichment.setdefault(
            key,
            {
                "Ticker": key,
                "MarketCap": None,
                "TrailingPE": None,
                "ForwardPE": None,
                "Sector": None,
                "Industry": "ETF",
            },
        )
        enrichment[key]["Industry"] = "ETF"

    return pd.DataFrame(enrichment.values())

def main():
    raw_df = download_exchange_list()
    if raw_df is None: return
    
    master_list = filter_and_clean(raw_df)
    print(f"Filter applied. {len(master_list)} primary tickers remaining.")
    
    # Save the base codes immediately.
    master_list.to_csv(BASE_OUTPUT_FILE, index=False)
    print(f"Base ticker file saved as: {BASE_OUTPUT_FILE}")
    
    if RUN_ENRICHMENT:
        print("Starting enrichment from NASDAQ bulk screener data...")

        try:
            enrich_df = fetch_bulk_enrichment()
        except KeyboardInterrupt:
            print("\nProcess interrupted by user. Saving partial results...")
            return

        if not enrich_df.empty:
            final_df = master_list.merge(enrich_df, on="Ticker", how="left")
            final_df.loc[final_df["ETF"] == "Y", "Industry"] = (
                final_df.loc[final_df["ETF"] == "Y", "Industry"].fillna("ETF")
            )
            final_df["MarketCap"] = pd.to_numeric(
                final_df["MarketCap"], errors="coerce"
            ).astype("Int64")
            final_df = final_df.sort_values(by="MarketCap", ascending=False, na_position="last")

            matched = final_df["Sector"].notna() | final_df["Industry"].notna()
            final_df.to_csv(FINAL_OUTPUT_FILE, index=False)
            stocks_df, etf_df = write_split_outputs(final_df)
            etf_type_counts = etf_df["ETF_Type"].value_counts().to_dict()
            print(
                f"\nProcessing Complete. Enriched {matched.sum()} of {len(final_df)} tickers. "
                f"File saved as: {FINAL_OUTPUT_FILE}"
            )
            print(
                f"Common stock file saved as: {COMMON_STOCK_OUTPUT_FILE} "
                f"({len(stocks_df)} tickers)"
            )
            print(
                f"ETF file saved as: {ETF_OUTPUT_FILE} ({len(etf_df)} tickers; "
                f"{etf_type_counts})"
            )
        else:
            stocks_df, etf_df = write_split_outputs(master_list)
            print("No data enriched. Split files saved from the base ticker list.")
            print(
                f"Common stock file saved as: {COMMON_STOCK_OUTPUT_FILE} "
                f"({len(stocks_df)} tickers)"
            )
            print(f"ETF file saved as: {ETF_OUTPUT_FILE} ({len(etf_df)} tickers)")
    else:
        stocks_df, etf_df = write_split_outputs(master_list)
        print("Enrichment skipped. Split files saved from the base ticker list.")
        print(
            f"Common stock file saved as: {COMMON_STOCK_OUTPUT_FILE} "
            f"({len(stocks_df)} tickers)"
        )
        print(f"ETF file saved as: {ETF_OUTPUT_FILE} ({len(etf_df)} tickers)")

if __name__ == "__main__":
    main()
