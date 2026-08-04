import argparse
import datetime
import io
import json
import re
import time
from decimal import Decimal, InvalidOperation
from ftplib import FTP
from pathlib import Path
from urllib.request import Request, urlopen
import pandas as pd

# --- DIRECTORY MANAGEMENT & DYNAMIC DATE PREFIXING ---
SCRIPT_DIR = Path(__file__).resolve().parent
DATE_PREFIX = datetime.datetime.now().strftime("%d-%m-")

BASE_OUTPUT_FILE = SCRIPT_DIR / f"{DATE_PREFIX}Master_Ticker_List_Base.csv"
FINAL_OUTPUT_FILE = SCRIPT_DIR / f"{DATE_PREFIX}NYSE_NASDAQ_NSE_Master_Library.csv"
COMMON_STOCK_OUTPUT_FILE = SCRIPT_DIR / f"{DATE_PREFIX}Common_Stocks_Master_Library.csv"
ETF_OUTPUT_FILE = SCRIPT_DIR / f"{DATE_PREFIX}ETF_Master_Library.csv"
CLASSIFICATION_OUTPUT_FILE = SCRIPT_DIR / f"{DATE_PREFIX}ETF_Classification_Mapping.csv"

# --- CORE SETTINGS ---
EXCHANGE_CODE_SET = {"NASDAQ", "NYSE", "NSE"}
ALLOW_MULTI_CLASS_STOCKS = True

# --- STEP 2: ELIMINATION RULES (STRICT FILTERS) ---
COMMON_EQUITY_INCLUDE_PATTERNS = [
    re.compile(pattern, re.IGNORECASE) for pattern in [
        r"\bCommon Stock\b", r"\bCommon Shares?\b", r"\bOrdinary Shares?\b",
        r"\bCapital Stock\b", r"\bAmerican Depositary Shares?\b",
        r"\bAmerican Depositary Receipts?\b", r"\bGlobal Depositary Shares?\b",
        r"\bNew York Registry Shares?\b", r"\bNY Registry Shares?\b",
        r"\bRegistered Shares?\b", r"\bVoting Shares?\b", r"\bADR\b", r"\bADS\b"
    ]
]

COMMON_EQUITY_EXCLUDE_PATTERNS = [
    re.compile(pattern, re.IGNORECASE) for pattern in [
        r"\bWarrants?\b", r"\bRights?\b", r"\bUnits?\b", r"\bPreferred\b",
        r"\bPreference\b", r"\bNotes?\b", r"\bBonds?\b", r"\bDebentures?\b",
        r"\bETF\b", r"\bETN\b", r"\bFund\b", r"\bClosed[- ]End\b", r"\bPurchase Contracts?\b"
    ]
]

EXOTIC_ETF_NOT_BLOCK = re.compile(
    r"\bleverag(?:e|ed|es)\b|\b[234]\s*x\b|\b[234]x\b|\bultra(?:pro)?\b|\bdaily target\b|"
    r"\bshort\b|\binverse\b|\bbear\b|\bbull\b|\bbitcoin\b|\bbtc\b|\bethereum\b|\bether\b|"
    r"\bsui\b|\bsolana\b|\bdogecoin\b|\bcrypto\b|\bhyperliquid\b|\bpolkadot\b|\betn\b",
    re.IGNORECASE
)

# --- STEP 3: ETF MULTI-DIMENSIONAL CLASSIFICATION RULES ---
ASSET_CLASS_RULES = [
    ("Crypto", [r"\bbitcoin\b", r"\bbtc\b", r"\bether\b", r"\bethereum\b", r"\bcrypto\b", r"\bsui\b", r"\bsolana\b", r"\bblockchain\b"]),
    ("Commodity", [r"\bgold\b", r"\bsilver\b", r"\bcopper\b", r"\bcommodity\b", r"\bcommodities\b", r"\boil\b", r"\bnatural gas\b", r"\buranium\b"]),
    ("Fixed Income", [r"\bbond\b", r"\bbonds\b", r"\btreasury\b", r"\bmunicipal\b", r"\bmuni\b", r"\bhigh yield\b", r"\bt-bill\b"]),
    ("Real Estate", ["reit", "real estate"]),
    ("Currency", [r"\bcurrency\b", r"\bdollar\b", r"\busd\b", r"\byen\b"]),
    ("Multi Asset", ["multi-asset", "multi asset", "allocation"]),
    ("Equity", ["equity", "stock", "shares", "s&p", "nasdaq", "russell", "dow jones", "msci"]),
]

STRATEGY_RULES = [
    ("Covered Call", ["covered call", "buywrite", "option income", "premium income"]),
    ("Dividend/Income", ["dividend", "income", "yield", "distribution"]),
    ("Municipal Bond", [r"\bmunicipal\b", r"\bmuni\b"]),
    ("Active", ["active", "actively managed"]),
    ("ESG/Sustainable", ["esg", "sustainable", "responsible", "climate"]),
    ("Factor", ["value", "growth", "quality", "momentum", "low volatility", "equal weight"]),
    ("Target Maturity", ["defined maturity", "target maturity", "bulletshares", "ibonds"]),
]

THEME_RULES = [
    # --- Advanced Tech & Deep Innovation ---
    ("Semiconductor", ["semiconductor", "semiconductors", "phlx sox", r"\bchips\b", "foundry", "wafer", "lithography"]),
    ("AI & Machine Learning", ["artificial intelligence", r"\bai\b", "machine learning", "generative ai", "neural network", "deep learning", "llm", "natural language processing", "computer vision", "cognitive", "openai"]),
    ("Quantum Computing", ["quantum", "quantum computing", "qubit", "quantum mechanics", "quantum information"]),
    ("Memory & Storage", ["memory", "storage", "nand", "dram", "flash memory", "solid state", "ssd", "semiconductor memory"]),
    ("Datacenter & Hyperscaler", ["data center", "datacenter", "data centres", "hyperscale", "hyperscaler", "cloud infrastructure", "colocation", "server farm", "digital infrastructure"]),
    ("Cybersecurity", ["cybersecurity", "cyber security", "network security", "zero trust", "threat intelligence"]),
    ("Cloud Computing", ["cloud computing", "cloud", "saas", "software as a service", "paas", "iaas"]),
    ("Fintech & Payments", ["fintech", "financial technology", "digital payments", "mobile payments", "blockchain", r"\bpaypal\b", r"\bsquare\b"]),
    ("Internet & E-Commerce", ["internet", "e-commerce", "ecommerce", "online retail", "digital economy"]),
    ("Gaming & Esports", ["gaming", "video games", "esports", "electronic entertainment"]),
    ("Space & Aerospace", ["space exploration", "satellite", "rocket", "aerospace", "defense & aerospace", "orbital", "astronomy", "constellation", "lunar", "mars"]),
    ("Digital Infrastructure", ["data center", "5g", "telecom", "telecommunications", "cell tower", "fiber optic"]),
    
    # --- Energy, Sustainability & Climate ---
    ("Traditional Energy", ["energy", "oil", "gas", "exploration", "production", "petroleum", "fossil", "crude"]),
    ("Clean Energy", ["clean energy", "solar", "wind", "renewable", "hydrogen", "clean tech", "green energy", "hydroelectric"]),
    ("Electric Vehicles & Batteries", ["electric vehicle", r"\bev\b", "battery", "lithium", "autonomous driving", "tesla"]),
    ("Uranium & Nuclear", ["uranium", "nuclear", "atomic energy"]),
    ("Water & Environment", ["water", "clean water", "water utilities", "waste management", "recycling"]),
    ("Carbon & Climate", ["carbon credit", "climate change", "net zero", "decarbonization"]),

    # --- Healthcare & Life Sciences ---
    ("Healthcare Broad", ["healthcare", "health care", "medical devices", "health insurance", "hospitals", "medical providers"]),
    ("Biotech & Genomics", ["biotech", "biotechnology", "genomics", "gene editing", "crispr", "life sciences", "mrna"]),
    ("Pharmaceuticals", ["pharmaceutical", "pharmaceuticals", "pharma", "drugs"]),

    # --- Financials & Real Estate ---
    ("Banking", ["bank", "banking", "regional banks", "commercial banks", "nifty bank"]),
    ("Insurance", ["insurance", "reinsurance", "life insurance", "property & casualty"]),
    ("Financial Services", ["financial services", "asset management", "brokerage", "capital markets", "exchanges"]),
    ("Real Estate & REITs", ["real estate", "reit", "reits", "homebuilders", "property"]),

    # --- Industrials, Materials & Infrastructure ---
    ("Industrials & Manufacturing", ["industrial", "industrials", "manufacturing", "machinery", "capital goods"]),
    ("Defense & Military", ["defense", "military", "weapons", "national security", "aerospace and defense"]),
    ("Infrastructure", ["infrastructure", "toll roads", "airports", "construction"]),
    ("Materials & Chemicals", ["materials", "basic materials", "chemical", "chemicals", "forest products", "paper"]),
    ("Precious Metals", [r"\bgold\b", r"\bsilver\b", "platinum", "palladium", "miners", "gold miners", "bullion"]),
    ("Base Metals & Commodities", ["copper", "steel", "aluminum", "commodity", "commodities", "agriculture", "timber"]),

    # --- Consumer, Lifestyle & Media ---
    ("Consumer Staples", ["consumer staples", "food", "beverage", "tobacco", "household products", "supermarkets"]),
    ("Consumer Discretionary", ["consumer discretionary", "luxury", "apparel", "automotive", "retailers"]),
    ("Retail", ["retail", "e-retail", "wholesale", "department stores"]),
    ("Travel & Hospitality", ["travel", "airline", "airlines", "cruise", "hotel", "hotels", "hospitality", "leisure", "casino"]),
    ("Media & Entertainment", ["media", "entertainment", "streaming", "broadcasting", "movies", "television"]),

    # --- Utilities & Broad Core Market ---
    ("Utilities", ["utilities", "utility", "electric utility", "gas utility", "power generation"]),
    ("Broad Market & Core Indices", ["s&p 500", "nasdaq", "nifty", "russell", "dow jones", "msci", "total market", "broad market", "large cap", "mid cap", "small cap"]),
    
    # --- Yield, Factor & Investment Strategies ---
    ("Dividend & Income", ["dividend", "dividends", "dividend aristocrats", "high yield", "covered call", "income focus"]),
    ("Growth & Momentum", ["growth", "momentum", "secular growth"]),
    ("Value & Quality", ["value", "deep value", "quality factor", "low volatility", "minimum volatility"]),
]

GEOGRAPHY_RULES = [
    ("Emerging Markets", ["emerging markets", "emerging market"]),
    ("Developed ex-US", ["developed markets", "international developed", "eafe", "ex-us", "ex-u.s."]),
    ("Global", ["global", "world", "all country"]),
    ("Europe", ["europe", "eurozone"]),
    ("Asia Pacific", ["asia pacific", "asia"]),
    ("China", ["china", "chinese"]),
    ("India", ["india", "nifty"]),
    ("Japan", ["japan"]),
    ("South Korea", ["korea"]),
    ("Taiwan", ["taiwan"]),
    ("Brazil", ["brazil"]),
    ("United Kingdom", ["united kingdom", " uk ", "u.k."]),
    ("United States", ["u.s.", "us ", "usa", "united states", "s&p 500", "russell", "nasdaq"]),
]

STANDARD_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
NASDAQ_HEADERS = {**STANDARD_HEADERS, "Accept": "application/json,text/plain,*/*", "Origin": "https://www.nasdaq.com", "Referer": "https://www.nasdaq.com/"}


def extract_raw_us_data():
    try:
        ftp = FTP("ftp.nasdaqtrader.com")
        ftp.login()
        ftp.cwd("SymbolDirectory")
        r = io.BytesIO()
        ftp.retrbinary("RETR nasdaqtraded.txt", r.write)
        ftp.quit()
        r.seek(0)
        df = pd.read_csv(r, sep="|").iloc[:-1].copy()
        
        exchange_map = {"N": "NYSE", "Q": "NASDAQ", "A": "NYSE", "P": "NYSE"}
        df["Listing Exchange"] = df["Listing Exchange"].map(exchange_map)
        
        raw_us = pd.DataFrame()
        raw_us["Ticker"] = df["Symbol"].astype(str).str.replace(".", "-", regex=False)
        raw_us["Symbol"] = df["Symbol"]
        raw_us["Security Name"] = df["Security Name"]
        raw_us["Listing Exchange"] = df["Listing Exchange"]
        raw_us["Market Category"] = df["Market Category"]
        raw_us["ETF"] = df["ETF"]
        raw_us["Test Issue"] = df["Test Issue"]
        return raw_us
    except Exception:
        return pd.DataFrame()


def extract_raw_nse_data():
    equity_url = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
    etf_url = "https://nsearchives.nseindia.com/content/equities/eq_etfseclist.csv"
    
    master_nse_segments = []

    # 1. Fetch Indian Board Common Equity Master Registers
    try:
        req_eq = Request(equity_url, headers=STANDARD_HEADERS)
        with urlopen(req_eq, timeout=30) as response:
            df_eq = pd.read_csv(io.BytesIO(response.read()))
        df_eq.columns = df_eq.columns.str.strip().str.upper()
        df_eq = df_eq.dropna(subset=["SYMBOL"])
        
        raw_eq = pd.DataFrame()
        raw_eq["Ticker"] = df_eq["SYMBOL"].astype(str).str.strip() + ".NS"
        raw_eq["Symbol"] = "XNSE:" + df_eq["SYMBOL"].astype(str).str.strip()
        raw_eq["Security Name"] = df_eq["NAME OF COMPANY"]
        raw_eq["Listing Exchange"] = "NSE"
        raw_eq["Market Category"] = df_eq["SERIES"].astype(str).str.strip().str.upper()
        
        # Dual validation: text-matching backup to catch mislabeled equity records
        raw_eq["ETF"] = df_eq.apply(
            lambda row: "Y" if (
                str(row["SERIES"]).upper() in {"MF", "ETF"} or 
                "BEES" in str(row["SYMBOL"]).upper() or 
                "ETF" in str(row["SYMBOL"]).upper() or 
                "ETF" in str(row["NAME OF COMPANY"]).upper() or 
                "EXCHANGE TRADED" in str(row["NAME OF COMPANY"]).upper()
            ) else "N", axis=1
        )
        raw_eq["Test Issue"] = "N"
        master_nse_segments.append(raw_eq)
    except Exception as e:
        print(f"  [ERROR] NSE India Equity Sheet Extraction Failure: {e}")

    # 2. Fetch Isolated Dedicated Exchange Traded Funds Master Lists
    try:
        req_etf = Request(etf_url, headers=STANDARD_HEADERS)
        with urlopen(req_etf, timeout=30) as response:
            content = response.read().decode("utf-8", errors="ignore")
            
        lines = content.splitlines()
        start_idx = 0
        for i, line in enumerate(lines):
            if "SYMBOL" in line.upper():
                start_idx = i
                break
                
        clean_content = "\n".join(lines[start_idx:])
        df_etf = pd.read_csv(io.StringIO(clean_content))
        df_etf.columns = df_etf.columns.str.strip().str.upper()
        
        symbol_col = next((c for c in df_etf.columns if "SYMBOL" in c or "TICKER" in c), None)
        name_col = next((c for c in df_etf.columns if "NAME" in c or "SECURITY" in c or "SCHEME" in c or "COMPANY" in c), None)
        
        if symbol_col and name_col:
            df_etf = df_etf.dropna(subset=[symbol_col])
            raw_etf = pd.DataFrame()
            raw_etf["Ticker"] = df_etf[symbol_col].astype(str).str.strip() + ".NS"
            raw_etf["Symbol"] = "XNSE:" + df_etf[symbol_col].astype(str).str.strip()
            raw_etf["Security Name"] = df_etf[name_col]
            raw_etf["Listing Exchange"] = "NSE"
            raw_etf["Market Category"] = "ETF"
            raw_etf["ETF"] = "Y"
            raw_etf["Test Issue"] = "N"
            master_nse_segments.append(raw_etf)
    except Exception as e:
        print(f"  [ERROR] NSE India ETF Sheet Extraction Failure: {e}")

    if master_nse_segments:
        combined = pd.concat(master_nse_segments, ignore_index=True)
        return combined.drop_duplicates(subset=["Ticker"], keep="last")
    return pd.DataFrame()


def download_json(url):
    request = Request(url, headers=NASDAQ_HEADERS)
    with urlopen(request, timeout=45) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_enrichment_data():
    try:
        stock_rows = download_json("https://api.nasdaq.com/api/screener/stocks?tableonly=true&limit=25000&offset=0&download=true").get("data", {}).get("rows", [])
        etf_rows = download_json("https://api.nasdaq.com/api/screener/etf?download=true").get("data", {}).get("rows", [])
    except Exception:
        return pd.DataFrame()

    enrichment = {}
    for row in stock_rows:
        ticker = row.get("symbol")
        if ticker:
            enrichment[str(ticker).strip().upper()] = {
                "Ticker": str(ticker).strip().upper(),
                "MarketCap": parse_number(row.get("marketCap")),
                "Sector": clean_field(row.get("sector")),
                "Industry": clean_field(row.get("industry")),
            }
    for row in etf_rows:
        ticker = row.get("symbol")
        if ticker:
            key = str(ticker).strip().upper()
            enrichment.setdefault(key, {"Ticker": key, "MarketCap": None, "Sector": None, "Industry": "ETF"})
            enrichment[key]["Industry"] = "ETF"
            
    return pd.DataFrame(enrichment.values())


def parse_number(value):
    if value is None:
        return None
    text = str(value).strip().replace("$", "").replace(",", "").replace("%", "")
    if not text or text.upper() in {"N/A", "NA", "NONE", "--"}:
        return None
    try:
        number = Decimal(text)
        return int(number) if number == number.to_integral_value() else float(number)
    except InvalidOperation:
        return None


def clean_field(value):
    if value is None:
        return None
    text = str(value).strip()
    return None if not text or text.upper() in {"N/A", "NA", "NONE", "--"} else text


def is_valid_common_stock(name, exchange, category, is_etf_flag):
    if is_etf_flag == "Y":
        return False
    if exchange == "NSE" and category not in {"EQ", "BE"}:
        return False
    text = clean_field(name)
    if not text:
        return False
    if any(p.search(text) for p in COMMON_EQUITY_EXCLUDE_PATTERNS):
        return False
    if exchange == "NSE":
        return True
    return any(p.search(text) for p in COMMON_EQUITY_INCLUDE_PATTERNS)


def contains_any(text, keywords):
    text = str(text).lower()
    return any(re.search(keyword.lower(), text) for keyword in keywords)


def all_matching_labels(text, rules, default_value=None):
    matches = [label for label, keywords in rules if contains_any(text, keywords)]
    if not matches and default_value:
        return [default_value]
    return matches


def classify_etf_multidim(name, ticker, default_geography):
    combined_str = f" {name} {ticker} "
    asset_classes = all_matching_labels(combined_str, ASSET_CLASS_RULES, default_value="Equity")
    strategies = all_matching_labels(combined_str, STRATEGY_RULES, default_value="Plain")
    themes = all_matching_labels(combined_str, THEME_RULES, default_value="Broad Market")
    geo_default = "India" if str(ticker).endswith(".NS") or "XNSE" in str(ticker) else default_geography
    geographies = all_matching_labels(combined_str, GEOGRAPHY_RULES, default_value=geo_default)
    flags = sorted(set(asset_classes + strategies + themes + geographies))
    
    return {
        "Asset Class": "; ".join(asset_classes),
        "Strategy": "; ".join(strategies),
        "Theme": "; ".join(themes),
        "Geography": "; ".join(geographies),
        "Category Flags": "; ".join(flags),
    }


def execute_elimination_and_classification(master_df, default_geography):
    if "MarketCap" in master_df.columns:
        master_df["MarketCap"] = pd.to_numeric(master_df["MarketCap"], errors="coerce").astype("Int64")

    # --- STEP 2: ELIMINATION SUB-ENGINE ROUTING ---
    initial_stock_pool = master_df[master_df["ETF"] == "N"]
    us_stock_pool_len = len(initial_stock_pool[initial_stock_pool["Listing Exchange"] != "NSE"])
    nse_stock_pool_len = len(initial_stock_pool[initial_stock_pool["Listing Exchange"] == "NSE"])

    stocks_df = master_df[
        (master_df["ETF"] == "N") & 
        (master_df["Test Issue"] == "N") &
        (master_df["Listing Exchange"].isin(EXCHANGE_CODE_SET)) &
        master_df.apply(lambda r: is_valid_common_stock(r["Security Name"], r["Listing Exchange"], r["Market Category"], r["ETF"]), axis=1)
    ].copy()
    
    stocks_df = stocks_df.sort_values(by="MarketCap", ascending=False, na_position="last") if "MarketCap" in stocks_df.columns else stocks_df.sort_values(by="Ticker")
    stocks_df.to_csv(COMMON_STOCK_OUTPUT_FILE, index=False)

    us_stocks_retained = len(stocks_df[stocks_df["Listing Exchange"] != "NSE"])
    nse_stocks_retained = len(stocks_df[stocks_df["Listing Exchange"] == "NSE"])

    initial_etf_pool = master_df[master_df["ETF"] == "Y"]
    us_etf_pool_len = len(initial_etf_pool[initial_etf_pool["Listing Exchange"] != "NSE"])
    nse_etf_pool_len = len(initial_etf_pool[initial_etf_pool["Listing Exchange"] == "NSE"])

    etf_df = master_df[
        (master_df["ETF"] == "Y") & 
        (master_df["Listing Exchange"].isin(EXCHANGE_CODE_SET))
    ].copy()
    
    etf_df = etf_df[
        ~etf_df["Security Name"].astype(str).apply(lambda x: bool(EXOTIC_ETF_NOT_BLOCK.search(x))) &
        ~etf_df["Symbol"].astype(str).apply(lambda x: bool(EXOTIC_ETF_NOT_BLOCK.search(x)))
    ].copy()

    us_etfs_retained = len(etf_df[etf_df["Listing Exchange"] != "NSE"])
    nse_etfs_retained = len(etf_df[etf_df["Listing Exchange"] == "NSE"])

    # --- STEP 3: ETF MULTI-DIMENSIONAL CLASSIFICATION ATTACHMENT ---
    classifications = [classify_etf_multidim(row["Security Name"], row["Ticker"], default_geography) for _, row in etf_df.iterrows()]
    if classifications:
        class_df = pd.DataFrame(classifications, index=etf_df.index)
        etf_df = pd.concat([etf_df, class_df], axis=1)
    else:
        for col in ["Asset Class", "Strategy", "Theme", "Geography", "Category Flags"]:
            etf_df[col] = ""

    etf_df = etf_df.sort_values(by=["Asset Class", "Theme", "Ticker"])
    etf_df.to_csv(ETF_OUTPUT_FILE, index=False)

    mapping_columns = ["Ticker", "Security Name", "Asset Class", "Strategy", "Theme", "Geography", "Category Flags"]
    if all(col in etf_df.columns for col in mapping_columns):
        etf_df[mapping_columns].to_csv(CLASSIFICATION_OUTPUT_FILE, index=False)

    return {
        "stocks_ingested": len(initial_stock_pool),
        "us_stocks_pool": us_stock_pool_len,
        "nse_stocks_pool": nse_stock_pool_len,
        "stocks_retained": len(stocks_df),
        "us_stocks_retained": us_stocks_retained,
        "nse_stocks_retained": nse_stocks_retained,
        "stocks_eliminated": len(initial_stock_pool) - len(stocks_df),
        "us_stocks_eliminated": us_stock_pool_len - us_stocks_retained,
        "nse_stocks_eliminated": nse_stock_pool_len - nse_stocks_retained,
        
        "etfs_ingested": len(initial_etf_pool),
        "us_etfs_pool": us_etf_pool_len,
        "nse_etfs_pool": nse_etf_pool_len,
        "etfs_retained": len(etf_df),
        "us_etfs_retained": us_etfs_retained,
        "nse_etfs_retained": nse_etfs_retained,
        "etfs_eliminated": len(initial_etf_pool) - len(etf_df),
        "us_etfs_eliminated": us_etf_pool_len - us_etfs_retained,
        "nse_etfs_eliminated": nse_etf_pool_len - nse_etfs_retained
    }


def main():
    parser = argparse.ArgumentParser(description="Unified Market Data Downloader, Multi-Step Elimination, and ETF Classifier Engine.")
    parser.add_argument("--default-geography", default="United States")
    args = parser.parse_args()

    print("\n================================================================================")
    print("🚀 RUNNING MARKET DATA EXTRACTION, ELIMINATION & CLASSIFICATION ENGINE")
    print("================================================================================")

    # --- STEP 1: EXTRACTION AND COMPILATION OF RAW MASTER LIST ---
    print("[STEP 1/3] Fetching raw security listing metrics from global archives...")
    us_df = extract_raw_us_data()
    print(f"  ├── US Exchanges (NYSE/NASDAQ FTP) pulled: {len(us_df)} rows")
    in_df = extract_raw_nse_data()
    print(f"  ├── Indian Exchange (NSE Archives) pulled: {len(in_df)} rows")
    
    master_list = pd.concat([us_df, in_df], ignore_index=True).dropna(subset=["Ticker"])
    if master_list.empty:
        print("[CRITICAL] Ingested raw master compilation table is empty. Aborting execution.")
        return
    master_list.to_csv(BASE_OUTPUT_FILE, index=False)

    print("[INFO] Fetching fundamental screener market cap layers from NASDAQ endpoints...")
    enrich_df = fetch_enrichment_data()
    if not enrich_df.empty:
        master_list = master_list.merge(enrich_df, on="Ticker", how="left")
        master_list.loc[master_list["ETF"] == "Y", "Industry"] = master_list.loc[master_list["ETF"] == "Y", "Industry"].fillna("ETF")
        master_list.to_csv(FINAL_OUTPUT_FILE, index=False)
        print(f"  └── Financial enrichment matrices aligned successfully for {len(enrich_df)} symbols.")

    # --- STEPS 2 & 3: PROCESS ELIMINATIONS AND COMPULSORY CLASSIFICATIONS ---
    print("[STEP 2/3] Processing segregation logic and active elimination blocks...")
    print("[STEP 3/3] Engineering multi-dimensional target category mapping matrices...")
    metrics = execute_elimination_and_classification(master_list, args.default_geography)

    # --- COMPREHENSIVE OUTPUT SUMMARY & FILE LOCATION MANIFEST ---
    print("\n================================================================================")
    print("📊 ENGINE EXECUTION ARCHIVE SUMMARY (MARKET DISTINCTION)")
    print("================================================================================")
    print(f"  Total Raw Ingested Instruments Pool : {len(master_list)}")
    print(f"  ├── US Ingested Components          : {len(us_df)}")
    print(f"  └── Indian Ingested Components      : {len(in_df)}")
    print("\n  [EQUITY SECURITY ROUTE]")
    print(f"  ├── Total Stocks Analyzed           : {metrics['stocks_ingested']}")
    print(f"  │   ├── US Stocks Pool              : {metrics['us_stocks_pool']}")
    print(f"  │   └── Indian Stocks Pool          : {metrics['nse_stocks_pool']}")
    print(f"  ├── Retained Valid Common Equities  : {metrics['stocks_retained']}")
    print(f"  │   ├── US Common Stocks Retained   : {metrics['us_stocks_retained']}")
    print(f"  │   └── Indian Common Stocks Retained: {metrics['nse_stocks_retained']}")
    print(f"  └── Eliminated Non-Common Structures: {metrics['stocks_eliminated']}")
    print(f"      ├── US Elements Eliminated      : {metrics['us_stocks_eliminated']}")
    print(f"      └── Indian Elements Eliminated  : {metrics['nse_stocks_eliminated']}")
    print("\n  [EXCHANGE TRADED FUND ROUTE]")
    print(f"  ├── Total ETFs Analyzed             : {metrics['etfs_ingested']}")
    print(f"  │   ├── US ETFs Pool                : {metrics['us_etfs_pool']}")
    print(f"  │   └── Indian ETFs Pool            : {metrics['nse_etfs_pool']}")
    print(f"  ├── Retained Structural Clean ETFs  : {metrics['etfs_retained']}")
    print(f"  │   ├── US Clean ETFs Retained      : {metrics['us_etfs_retained']}")
    print(f"  │   └── Indian Clean ETFs Retained  : {metrics['nse_etfs_retained']}")
    print(f"  └── Scratched Exotic Asset Targets  : {metrics['etfs_eliminated']}")
    print(f"      ├── US Exotic ETFs Scratched    : {metrics['us_etfs_eliminated']}")
    print(f"      └── Indian Exotic ETFs Scratched: {metrics['nse_etfs_eliminated']}")

    print("\n================================================================================")
    print("💾 OUTPUT ARTIFACT LOCATION MANIFEST")
    print("================================================================================")
    print(f"  1. Raw Extracted Ground-Base File  :\n     📍 {BASE_OUTPUT_FILE.resolve()}")
    print(f"  2. Merged Enriched Master Library  :\n     📍 {FINAL_OUTPUT_FILE.resolve()}")
    print(f"  3. Scrubbed Common Stock Registry  :\n     📍 {COMMON_STOCK_OUTPUT_FILE.resolve()}")
    print(f"  4. Scrubbed Categorized ETF Master  :\n     📍 {ETF_OUTPUT_FILE.resolve()}")
    print(f"  5. Comparator Target Input Dataset  :\n     📍 {CLASSIFICATION_OUTPUT_FILE.resolve()}")
    print("================================================================================\n")


if __name__ == "__main__":
    main()