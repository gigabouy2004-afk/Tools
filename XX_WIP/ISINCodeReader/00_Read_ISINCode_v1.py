import os
import sys
import logging
import requests
import pandas as pd
import time
import random
from datetime import datetime

# =========================
# CONFIGURATION
# =========================

FILE_NAME = "Axis_Direct_Code-5_May.csv"

BASE_DIR = "D:/Tools/ISINCodeReader"

DATA_DIR = os.path.join(BASE_DIR, "INPUT")
OUTPUT_DIR = os.path.join(BASE_DIR, "OUTPUT")

INPUT_FILE = os.path.join(DATA_DIR, FILE_NAME)
OUTPUT_FILE = os.path.join(
    OUTPUT_DIR,
    f"output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
)

CACHE_FILE = os.path.join(DATA_DIR, "isin_cache.csv")

NSE_ALL_SYMBOLS_URL = "https://www.nseindia.com/api/market-data-pre-open?key=ALL"
NSE_QUOTE_URL = "https://www.nseindia.com/api/quote-equity?symbol={symbol}"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Referer": "https://www.nseindia.com/"
}

REQUEST_TIMEOUT = 5
MAX_RETRIES = 3
BASE_DELAY = 0.2

# =========================
# LOGGING
# =========================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# =========================
# FILE SYSTEM
# =========================

def ensure_directories():
    for path in [DATA_DIR, OUTPUT_DIR]:
        if not os.path.exists(path):
            os.makedirs(path)
            logging.info(f"Created directory: {path}")

# =========================
# INPUT LOADING
# =========================

def validate_isin(series):
    return series.astype(str).str.match(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")

def load_input():
    if not os.path.exists(INPUT_FILE):
        raise FileNotFoundError(f"Input file not found: {INPUT_FILE}")

    df = pd.read_csv(INPUT_FILE)

    if df.empty:
        raise ValueError("Input file is empty")

    df.columns = ["ISIN"]

    if not validate_isin(df["ISIN"]).all():
        raise ValueError("Invalid ISIN format detected")

    return df

# =========================
# CACHE
# =========================

def load_cache():
    if os.path.exists(CACHE_FILE):
        df = pd.read_csv(CACHE_FILE)
        return dict(zip(df["ISIN"], df["SYMBOL"]))
    return {}

def save_cache(isin_map):
    df = pd.DataFrame(list(isin_map.items()), columns=["ISIN", "SYMBOL"])
    df.to_csv(CACHE_FILE, index=False)

# =========================
# NETWORK LAYER
# =========================

def create_session():
    session = requests.Session()
    session.headers.update(HEADERS)

    try:
        session.get("https://www.nseindia.com", timeout=REQUEST_TIMEOUT)
    except Exception as e:
        raise ConnectionError(f"NSE handshake failed: {e}")

    return session

def safe_request(session, url):
    for attempt in range(MAX_RETRIES):
        try:
            response = session.get(url, timeout=REQUEST_TIMEOUT)

            if response.status_code == 200:
                return response

            elif response.status_code in [401, 429]:
                time.sleep(2 + random.random())

        except Exception:
            time.sleep(1)

    return None

# =========================
# FETCH SYMBOL UNIVERSE
# =========================

def fetch_nse_symbols(session):
    response = safe_request(session, NSE_ALL_SYMBOLS_URL)

    if response is None:
        raise RuntimeError("Failed to fetch NSE symbol universe")

    data = response.json()

    try:
        symbols = [
            item["metadata"]["symbol"]
            for item in data["data"]
            if "metadata" in item and "symbol" in item["metadata"]
        ]
    except Exception:
        raise RuntimeError("Unexpected NSE response format")

    if not symbols:
        raise ValueError("No symbols retrieved")

    logging.info(f"Total NSE symbols fetched: {len(symbols)}")

    return symbols

# =========================
# BUILD ISIN MAP
# =========================

def build_isin_map(session, symbols):
    isin_map = load_cache()

    logging.info(f"Loaded cache entries: {len(isin_map)}")

    for i, symbol in enumerate(symbols):
        try:
            url = NSE_QUOTE_URL.format(symbol=symbol)

            response = safe_request(session, url)
            if response is None:
                continue

            data = response.json()
            isin = data.get("info", {}).get("isin")

            if isin and isin not in isin_map:
                isin_map[isin] = symbol

        except Exception:
            continue

        if i % 50 == 0:
            logging.info(f"Processed {i}/{len(symbols)}")

        time.sleep(BASE_DELAY + random.random() * BASE_DELAY)

    if not isin_map:
        raise RuntimeError("ISIN map is empty")

    save_cache(isin_map)

    return isin_map

# =========================
# MAPPING
# =========================

def map_isin_to_symbol(df, isin_map):
    df["SYMBOL"] = df["ISIN"].map(isin_map)
    df["TICKER"] = df["SYMBOL"].apply(
        lambda x: f"{x}.NS" if pd.notna(x) else None
    )

    missing = df["SYMBOL"].isna().sum()

    logging.info(f"Mapped: {len(df) - missing}, Missing: {missing}")

    return df

# =========================
# MAIN
# =========================

def main():
    try:
        ensure_directories()

        logging.info("Loading input...")
        df = load_input()

        logging.info("Creating NSE session...")
        session = create_session()

        logging.info("Fetching NSE universe...")
        symbols = fetch_nse_symbols(session)

        logging.info("Building ISIN mapping...")
        isin_map = build_isin_map(session, symbols)

        logging.info("Mapping ISIN → ticker...")
        result = map_isin_to_symbol(df, isin_map)

        logging.info("Saving output...")
        result.to_csv(OUTPUT_FILE, index=False)

        logging.info(f"Completed successfully: {OUTPUT_FILE}")

    except Exception as e:
        logging.error(f"Fatal error: {e}")
        sys.exit(1)

# =========================
# ENTRY
# =========================

if __name__ == "__main__":
    main()