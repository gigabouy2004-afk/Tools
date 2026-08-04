import argparse
import contextlib
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

try:
    import requests
except ImportError:
    requests = None

try:
    import yfinance as yf
except ImportError:
    yf = None

# --- DIRECTORY MANAGEMENT & DYNAMIC DATE PREFIXING ---
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
DATE_PREFIX = datetime.datetime.now().strftime("%d-%m-")

US_STOCK_DIR = ROOT_DIR / "02_Stock"
NSE_STOCK_DIR = ROOT_DIR / "02_Stock"
US_ETF_DIR = ROOT_DIR / "03_ETF"
NSE_ETF_DIR = ROOT_DIR / "03_ETF"

BASE_OUTPUT_FILE = ROOT_DIR / "01_MASTER" / f"{DATE_PREFIX}Master_Ticker_List_Base.csv"
FINAL_OUTPUT_FILE = ROOT_DIR / "01_MASTER" / f"{DATE_PREFIX}NYSE_NASDAQ_NSE_Master_Library.csv"

# Composite Eliminated Master Registries
ELIMINATED_STOCKS_OUTPUT_FILE = ROOT_DIR / "01_MASTER" / f"{DATE_PREFIX}Eliminated_Non_Common_Stocks.csv"
ELIMINATED_ETFS_OUTPUT_FILE = ROOT_DIR / "01_MASTER" / f"{DATE_PREFIX}Excluded_ETFs.csv"

# USA Specific Output Registries
US_COMMON_STOCK_OUTPUT_FILE = US_STOCK_DIR / f"{DATE_PREFIX}US_Common_Stocks_Master_Library.csv"
US_ETF_OUTPUT_FILE = US_ETF_DIR / f"{DATE_PREFIX}US_ETF_Master_Library.csv"
US_CLASSIFICATION_OUTPUT_FILE = US_ETF_DIR / f"{DATE_PREFIX}US_ETF_Classification_Mapping.csv"
ETF_HOLDINGS_DETAIL_OUTPUT_FILE = US_ETF_DIR / f"{DATE_PREFIX}ETF_Holdings_Detail.csv"

# Cross-Reference Matrices Output Registries
ETF_STOCK_MATRIX_FILE = US_ETF_DIR / f"{DATE_PREFIX}ETF_vs_Stock_Matrix.csv"
STOCK_ETF_LOOKUP_FILE = US_ETF_DIR / f"{DATE_PREFIX}Stock_vs_ETF_Lookup.csv"

# India (NSE) Specific Output Registries
NSE_COMMON_STOCK_OUTPUT_FILE = NSE_STOCK_DIR / f"{DATE_PREFIX}NSE_Common_Stocks_Master_Library.csv"
NSE_ETF_OUTPUT_FILE = NSE_ETF_DIR / f"{DATE_PREFIX}NSE_ETF_Master_Library.csv"
NSE_CLASSIFICATION_OUTPUT_FILE = NSE_ETF_DIR / f"{DATE_PREFIX}NSE_ETF_Classification_Mapping.csv"

# --- CORE SETTINGS ---
EXCHANGE_CODE_SET = {
    "NASDAQ", "NYSE", "NYSE MKT", "NYSE ARCA", "BATS", "IEX", 
    "NYSE National", "DirectEdge A", "DirectEdge X", "NASDAQ PSX", "BATS Y", "NSE"
}
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

ETF_EXCLUDE_PATTERN = re.compile(
    r"""
    # Leveraged, inverse, single-stock daily products, and ETNs
    \bleveraged?\b|\bleverage\s+shares\b|\bultra(?:short)?\b|\binverse\b|
    \bshort\b|\bbear\b|\bbull\b|\b[2345]x\b|\b-?[123]x\b|
    \bdaily\s+(?:long|short|bull|bear|target)\b|
    \b(?:long|short|bull|bear).*\bdaily\b|
    \bsingle[-\s]?stock\b|\bETNs?\b|\bexchange[-\s]?traded\s+notes?\b|
    \bmedium[-\s]?term\s+notes?\b|\bsenior\s+notes?\b|\bmicrosectors\b|

    # Option-income, covered-call, yield-boost, buffer, and defined-outcome products
    \bcovered\s+call\b|\bbuy[-\s]?write\b|\byield\s*boost\b|\byieldmax\b|
    \boption\s+income\b|\bmonthly\s+option\s+income\b|
    \bbuffer(?:ed)?\b|\bdefined\s+(?:outcome|protection)\b|
    \bautocallable\b|\bbarrier\b|\bfloor\b|\bcapped\b|

    # Fixed-income, treasury, target-maturity, and term bond products
    \bfixed\s+income\b|\bbonds?\b|\btreasur(?:y|ies)\b|\bt[-\s]?bills?\b|
    \bmunicipal\b|\bmuni\b|\bmortgage\b|\bsecuriti[sz]ed\b|\bCLO\b|
    \btarget\s+maturity\b|\bdefined\s+maturity\b|\bterm\s+corporate\b|
    \bterm\s+tips\b|\bibonds\b|\bbulletshares\b|\b\d+\s*(?:month|year|yr)\b|

    # Themes the downstream comparator should not include
    \bcannabis\b|\bmarijuana\b|\bhemp\b|\bpsychedelic\b|\bpshyedelic\b|\bpsilocybin\b|

    # Crypto and digital-asset products
    \bbitcoin\b|\bbtc\b|\bether\b|\bethereum\b|\beth\b|\bcrypto\b|
    \b21shares\b|\bcoin\b|\bblockchain\b|\bsui\b|\bsolana\b|\bdefi\b|
    \bmetaverse\b|\bnft\b|

    # High-frequency distribution products
    \bweekly\b
    """,
    re.IGNORECASE | re.VERBOSE
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
    ("Traditional Energy", ["energy", "oil", "gas", "exploration", "production", "petroleum", "fossil", "crude"]),
    ("Clean Energy", ["clean energy", "solar", "wind", "renewable", "hydrogen", "clean tech", "green energy", "hydroelectric"]),
    ("Electric Vehicles & Batteries", ["electric vehicle", r"\bev\b", "battery", "lithium", "autonomous driving", "tesla"]),
    ("Uranium & Nuclear", ["uranium", "nuclear", "atomic energy"]),
    ("Water & Environment", ["water", "clean water", "water utilities", "waste management", "recycling"]),
    ("Carbon & Climate", ["carbon credit", "climate change", "net zero", "decarbonization"]),
    ("Healthcare Broad", ["healthcare", "health care", "medical devices", "health insurance", "hospitals", "medical providers"]),
    ("Biotech & Genomics", ["biotech", "biotechnology", "genomics", "gene editing", "crispr", "life sciences", "mrna"]),
    ("Pharmaceuticals", ["pharmaceutical", "pharmaceuticals", "pharma", "drugs"]),
    ("Banking", ["bank", "banking", "regional banks", "commercial banks", "nifty bank"]),
    ("Insurance", ["insurance", "reinsurance", "life insurance", "property & casualty"]),
    ("Financial Services", ["financial services", "asset management", "brokerage", "capital markets", "exchanges"]),
    ("Real Estate & REITs", ["real estate", "reit", "reits", "homebuilders", "property"]),
    ("Industrials & Manufacturing", ["industrial", "industrials", "manufacturing", "machinery", "capital goods"]),
    ("Defense & Military", ["defense", "military", "weapons", "national security", "aerospace and defense"]),
    ("Infrastructure", ["infrastructure", "toll roads", "airports", "construction"]),
    ("Materials & Chemicals", ["materials", "basic materials", "chemical", "chemicals", "forest products", "paper"]),
    ("Precious Metals", [r"\bgold\b", r"\bsilver\b", "platinum", "palladium", "miners", "gold miners", "bullion"]),
    ("Base Metals & Commodities", ["copper", "steel", "aluminum", "commodity", "commodities", "agriculture", "timber"]),
    ("Consumer Staples", ["consumer staples", "food", "beverage", "tobacco", "household products", "supermarkets"]),
    ("Consumer Discretionary", ["consumer discretionary", "luxury", "apparel", "automotive", "retailers"]),
    ("Retail", ["retail", "e-retail", "wholesale", "department stores"]),
    ("Travel & Hospitality", ["travel", "airline", "airlines", "cruise", "hotel", "hotels", "hospitality", "leisure", "casino"]),
    ("Media & Entertainment", ["media", "entertainment", "streaming", "broadcasting", "movies", "television"]),
    ("Utilities", ["utilities", "utility", "electric utility", "gas utility", "power generation"]),
    ("Broad Market & Core Indices", ["s&p 500", "nasdaq", "nifty", "russell", "dow jones", "msci", "total market", "broad market", "large cap", "mid cap", "small cap"]),
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
    ("Latin America", ["latam", "latin america", "chile", "colombia", "columbia", "peru", "brazil", "braxil", "mexico", "argentina"]),
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
        ftp = FTP("ftp.nasdaqtrader.com", timeout=30)
        ftp.login()
        ftp.cwd("SymbolDirectory")
        r = io.BytesIO()
        ftp.retrbinary("RETR nasdaqtraded.txt", r.write)
        ftp.quit()
        r.seek(0)
        df = pd.read_csv(r, sep="|").iloc[:-1].copy()
        
        df["Listing Exchange"] = df["Listing Exchange"].astype(str).str.strip()
        df["Listing Exchange"] = df["Listing Exchange"].replace(["", "nan", "None"], "N")

        exchange_map = {
            "N": "NYSE", 
            "Q": "NASDAQ", 
            "A": "NYSE MKT", 
            "P": "NYSE ARCA",
            "Z": "BATS", 
            "V": "IEX", 
            "C": "NYSE National", 
            "J": "DirectEdge A", 
            "K": "DirectEdge X", 
            "X": "NASDAQ PSX", 
            "Y": "BATS Y"
        }
        df["Listing Exchange"] = df["Listing Exchange"].map(exchange_map).fillna(df["Listing Exchange"])
        
        raw_us = pd.DataFrame()
        raw_us["Ticker"] = df["Symbol"].astype(str).str.replace(".", "-", regex=False)
        raw_us["Symbol"] = df["Symbol"]
        raw_us["Security Name"] = df["Security Name"]
        raw_us["Listing Exchange"] = df["Listing Exchange"]
        raw_us["Market Category"] = df["Market Category"]
        raw_us["ETF"] = df["ETF"]
        raw_us["Test Issue"] = df["Test Issue"]
        return raw_us
    except Exception as e:
        print(f"  [ERROR] US FTP Extraction Failure: {e}")
        return pd.DataFrame()


def extract_raw_nse_data():
    equity_url = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
    etf_url = "https://nsearchives.nseindia.com/content/equities/eq_etfseclist.csv"
    
    master_nse_segments = []

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
    except Exception as e:
        print(f"  [WARN] NASDAQ enrichment fetch failed: {e}")
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
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    return None if not text or text.upper() in {"N/A", "NA", "NAN", "NONE", "--"} else text


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


def clean_ticker_for_lookup(ticker):
    if not isinstance(ticker, str):
        return ""
    ticker = ticker.strip().upper()
    if ticker.startswith("XNSE:"):
        return ticker.replace("XNSE:", "") + ".NS"
    return ticker


def parse_weight_value(raw_value):
    if pd.isna(raw_value):
        return 0.0
    text = str(raw_value).replace("%", "").strip()
    try:
        weight = float(text)
    except (TypeError, ValueError):
        return 0.0
    return weight * 100.0 if 0.0 < weight < 1.0 else weight


def fetch_etf_top_holdings(etf_ticker):
    holdings = {}
    etf_ticker = clean_ticker_for_lookup(etf_ticker)
    if not etf_ticker:
        return holdings

    if requests is not None:
        try:
            response = requests.get(
                f"https://query2.finance.yahoo.com/v1/finance/etfProfile?symbol={etf_ticker}",
                headers={"User-Agent": STANDARD_HEADERS["User-Agent"]},
                timeout=15,
            )
            if response.status_code == 200:
                data = response.json()
                results = data.get("finance", {}).get("result", [])
                if results and results[0].get("holdings"):
                    for holding in results[0]["holdings"]:
                        symbol = clean_ticker_for_lookup(holding.get("symbol", ""))
                        if symbol:
                            holdings[symbol] = parse_weight_value(holding.get("holdingPercent", 0))
                    return holdings
        except Exception:
            pass

    if yf is not None:
        try:
            ticker_instance = yf.Ticker(etf_ticker)
            try:
                fund_holdings = ticker_instance.funds_data.holdings
                if fund_holdings is not None and not fund_holdings.empty:
                    for idx, row in fund_holdings.iterrows():
                        symbol = clean_ticker_for_lookup(str(idx))
                        weight_cols = [c for c in row.index if "weight" in str(c).lower() or "percent" in str(c).lower()]
                        if symbol and weight_cols:
                            holdings[symbol] = parse_weight_value(row[weight_cols[0]])
                    if holdings:
                        return holdings
            except Exception:
                pass

            top_holdings = ticker_instance.funds_data.top_holdings
            if top_holdings is not None and not top_holdings.empty:
                top_holdings.columns = [str(c).lower().strip() for c in top_holdings.columns]
                if "symbol" in top_holdings.columns:
                    top_holdings = top_holdings.set_index("symbol")
                weight_cols = [
                    c for c in top_holdings.columns
                    if any(term in c for term in ["percent", "holding", "weight", "allocation"])
                ]
                if weight_cols:
                    for idx, row in top_holdings.iterrows():
                        symbol = clean_ticker_for_lookup(str(idx))
                        if symbol:
                            holdings[symbol] = parse_weight_value(row[weight_cols[0]])
        except Exception:
            pass

    return holdings


def build_stock_metadata(master_df):
    metadata = {}
    stock_rows = master_df[master_df["ETF"] == "N"].copy()
    for _, row in stock_rows.iterrows():
        ticker = clean_ticker_for_lookup(str(row.get("Ticker", "")))
        symbol = clean_ticker_for_lookup(str(row.get("Symbol", "")))
        record = {
            "Holding Name": clean_field(row.get("Security Name")) or "",
            "Holding Sector": clean_field(row.get("Sector")) or "",
            "Holding Industry": clean_field(row.get("Industry")) or "",
            "Holding Market Region": "India (NSE)" if row.get("Listing Exchange") == "NSE" else "USA",
            "Holding MarketCap": row.get("MarketCap"),
            "Holding Metadata Source": "Stock Master",
        }
        for key in {ticker, symbol}:
            if key:
                metadata[key] = record
    return metadata


def lookup_external_holding_metadata(ticker, external_metadata_cache):
    ticker = clean_ticker_for_lookup(ticker)
    if not ticker:
        return {}
    if ticker in external_metadata_cache:
        return external_metadata_cache[ticker]

    record = {
        "Holding Name": "",
        "Holding Sector": "External / Unmapped",
        "Holding Industry": "External / Unmapped",
        "Holding Market Region": "External",
        "Holding MarketCap": None,
        "Holding Metadata Source": "External / Unmapped",
    }

    candidates = [ticker]
    if re.fullmatch(r"\d{4,5}", ticker):
        if ticker.startswith("0"):
            candidates.append(f"{ticker}.HK")
        elif ticker.startswith("5"):
            candidates.append(f"{ticker}.BO")

    if yf is not None:
        for candidate in candidates:
            try:
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    info = yf.Ticker(candidate).get_info()
                sector = clean_field(info.get("sector"))
                industry = clean_field(info.get("industry"))
                if sector or industry:
                    record.update({
                        "Holding Name": clean_field(info.get("longName")) or clean_field(info.get("shortName")) or "",
                        "Holding Sector": sector or "External / Unmapped",
                        "Holding Industry": industry or "External / Unmapped",
                        "Holding MarketCap": parse_number(info.get("marketCap")),
                        "Holding Metadata Source": "Yahoo Finance",
                    })
                    break
            except Exception:
                pass

    external_metadata_cache[ticker] = record
    return record


def complete_holding_metadata(holding_ticker, stock_metadata, external_metadata_cache):
    holding_meta = dict(stock_metadata.get(holding_ticker) or {})
    needs_external_lookup = (
        not holding_meta or
        not holding_meta.get("Holding Sector") or
        not holding_meta.get("Holding Industry")
    )
    if needs_external_lookup:
        external_meta = lookup_external_holding_metadata(holding_ticker, external_metadata_cache)
        if not holding_meta:
            return external_meta
            
        for key in ["Holding Name", "Holding Sector", "Holding Industry", "Holding MarketCap"]:
            hm_val = holding_meta.get(key)
            em_val = external_meta.get(key)
            
            # Safe truthy check avoiding "boolean value of NA is ambiguous" errors
            hm_is_empty = True if pd.isna(hm_val) else not bool(hm_val)
            em_is_valid = False if pd.isna(em_val) else bool(em_val)
            
            if hm_is_empty and em_is_valid:
                holding_meta[key] = em_val
                
        if (
            external_meta.get("Holding Metadata Source") == "Yahoo Finance" and
            (holding_meta.get("Holding Sector") or holding_meta.get("Holding Industry"))
        ):
            holding_meta["Holding Metadata Source"] = "Stock Master + Yahoo Finance"
    return holding_meta


def format_weighted_mix(weight_by_label, max_items=5):
    items = [
        (label, weight)
        for label, weight in weight_by_label.items()
        if label and label not in {"External / Unmapped", "nan"}
    ]
    items.sort(key=lambda item: item[1], reverse=True)
    return "; ".join(f"{label} {weight:.2f}%" for label, weight in items[:max_items])


def enrich_etfs_with_holdings(etf_df, master_df, holdings_limit=0):
    if etf_df.empty:
        return etf_df, pd.DataFrame()

    stock_metadata = build_stock_metadata(master_df)
    external_metadata_cache = {}
    detail_records = []
    summary_by_etf = {}
    total_etfs = len(etf_df) if not holdings_limit else min(len(etf_df), holdings_limit)

    for processed_count, (_, etf_row) in enumerate(etf_df.iterrows(), start=1):
        if holdings_limit and processed_count > holdings_limit:
            break

        etf_ticker = clean_ticker_for_lookup(str(etf_row.get("Ticker", "")))
        etf_name = clean_field(etf_row.get("Security Name")) or ""
        print(f"  - Holdings enrichment {processed_count}/{total_etfs}: {etf_ticker}")
        holdings = fetch_etf_top_holdings(etf_ticker)

        sector_weights = {}
        industry_weights = {}
        top_holding_parts = []
        known_weight = 0.0

        for holding_ticker, holding_weight in sorted(holdings.items(), key=lambda item: item[1], reverse=True):
            holding_meta = complete_holding_metadata(holding_ticker, stock_metadata, external_metadata_cache)

            sector = holding_meta.get("Holding Sector") or "External / Unmapped"
            industry = holding_meta.get("Holding Industry") or "External / Unmapped"
            if sector != "External / Unmapped":
                sector_weights[sector] = sector_weights.get(sector, 0.0) + holding_weight
            if industry != "External / Unmapped":
                industry_weights[industry] = industry_weights.get(industry, 0.0) + holding_weight
            if holding_meta.get("Holding Metadata Source") != "External / Unmapped":
                known_weight += holding_weight

            top_holding_parts.append(f"{holding_ticker} {holding_weight:.2f}%")
            detail_records.append({
                "ETF Ticker": etf_ticker,
                "ETF Name": etf_name,
                "Holding Ticker": holding_ticker,
                "Holding Name": holding_meta.get("Holding Name", ""),
                "Holding Weight %": round(holding_weight, 4),
                "Holding Sector": sector,
                "Holding Industry": industry,
                "Holding Market Region": holding_meta.get("Holding Market Region", "External"),
                "Holding MarketCap": holding_meta.get("Holding MarketCap"),
                "Holding Metadata Source": holding_meta.get("Holding Metadata Source", "External / Unmapped"),
                "Holdings Source": "Yahoo ETF Top Holdings",
            })

        sector_mix = format_weighted_mix(sector_weights)
        industry_mix = format_weighted_mix(industry_weights)
        summary_by_etf[etf_ticker] = {
            "Holding Count": len(holdings),
            "Known Holding Weight %": round(known_weight, 4),
            "Top Holdings": "; ".join(top_holding_parts[:10]),
            "Weighted Sector Mix": sector_mix,
            "Weighted Industry Mix": industry_mix,
            "Holdings Classification Text": " | ".join(part for part in [sector_mix, industry_mix] if part),
            "Holdings Classification Source": "Yahoo ETF Top Holdings",
        }

    summary_df = pd.DataFrame.from_dict(summary_by_etf, orient="index")
    if not summary_df.empty:
        summary_df.index.name = "Ticker"
        etf_df = etf_df.merge(summary_df.reset_index(), on="Ticker", how="left")

    detail_df = pd.DataFrame(detail_records)
    return etf_df, detail_df


def execute_elimination_and_classification(master_df, default_geography, enrich_holdings=True, holdings_limit=0):
    if "MarketCap" in master_df.columns:
        master_df["MarketCap"] = pd.to_numeric(master_df["MarketCap"], errors="coerce").astype("Int64")

    initial_stock_pool = master_df[master_df["ETF"] == "N"]
    us_stock_pool_len = len(initial_stock_pool[initial_stock_pool["Listing Exchange"] != "NSE"])
    initial_stock_pool_nse = initial_stock_pool[initial_stock_pool["Listing Exchange"] == "NSE"]
    nse_stock_pool_len = len(initial_stock_pool_nse)

    stocks_df = master_df[
        (master_df["ETF"] == "N") & 
        (master_df["Test Issue"] == "N") &
        (master_df["Listing Exchange"].isin(EXCHANGE_CODE_SET)) &
        master_df.apply(lambda r: is_valid_common_stock(r["Security Name"], r["Listing Exchange"], r["Market Category"], r["ETF"]), axis=1)
    ].copy()
    
    # Process Eliminated Stocks
    eliminated_stocks_df = initial_stock_pool.drop(stocks_df.index).copy()
    eliminated_stocks_df["Market Region"] = eliminated_stocks_df["Listing Exchange"].apply(lambda x: "India (NSE)" if x == "NSE" else "USA")
    
    ELIMINATED_STOCKS_OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    eliminated_stocks_df.to_csv(ELIMINATED_STOCKS_OUTPUT_FILE, index=False)
    
    stocks_df = stocks_df.sort_values(by="MarketCap", ascending=False, na_position="last") if "MarketCap" in stocks_df.columns else stocks_df.sort_values(by="Ticker")
    
    us_stocks = stocks_df[stocks_df["Listing Exchange"] != "NSE"]
    nse_stocks = stocks_df[stocks_df["Listing Exchange"] == "NSE"]
    
    US_COMMON_STOCK_OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    us_stocks.to_csv(US_COMMON_STOCK_OUTPUT_FILE, index=False)
    
    NSE_COMMON_STOCK_OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    nse_stocks.to_csv(NSE_COMMON_STOCK_OUTPUT_FILE, index=False)

    us_stocks_retained = len(us_stocks)
    nse_stocks_retained = len(nse_stocks)

    initial_etf_pool = master_df[master_df["ETF"] == "Y"]
    us_etf_pool_len = len(initial_etf_pool[initial_etf_pool["Listing Exchange"] != "NSE"])
    nse_etf_pool_len = len(initial_etf_pool[initial_etf_pool["Listing Exchange"] == "NSE"])

    etf_df = master_df[
        (master_df["ETF"] == "Y") & 
        (master_df["Listing Exchange"].isin(EXCHANGE_CODE_SET))
    ].copy()
    
    etf_df = etf_df[
        ~etf_df["Security Name"].astype(str).apply(lambda x: bool(ETF_EXCLUDE_PATTERN.search(x))) &
        ~etf_df["Symbol"].astype(str).apply(lambda x: bool(ETF_EXCLUDE_PATTERN.search(x)))
    ].copy()
    
    # Process Eliminated ETFs
    eliminated_etfs_df = initial_etf_pool.drop(etf_df.index).copy()
    eliminated_etfs_df["Market Region"] = eliminated_etfs_df["Listing Exchange"].apply(lambda x: "India (NSE)" if x == "NSE" else "USA")
    
    ELIMINATED_ETFS_OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    eliminated_etfs_df.to_csv(ELIMINATED_ETFS_OUTPUT_FILE, index=False)

    classifications = [classify_etf_multidim(row["Security Name"], row["Ticker"], default_geography) for _, row in etf_df.iterrows()]
    if classifications:
        class_df = pd.DataFrame(classifications, index=etf_df.index)
        etf_df = pd.concat([etf_df, class_df], axis=1)
    else:
        for col in ["Asset Class", "Strategy", "Theme", "Geography", "Category Flags"]:
            etf_df[col] = ""

    holdings_detail_df = pd.DataFrame()
    if enrich_holdings:
        print("[INFO] Enriching ETF master with ETF top holdings and weighted sector/industry mixes...")
        etf_df, holdings_detail_df = enrich_etfs_with_holdings(etf_df, master_df, holdings_limit=holdings_limit)
        ETF_HOLDINGS_DETAIL_OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        holdings_detail_df.to_csv(ETF_HOLDINGS_DETAIL_OUTPUT_FILE, index=False)

        if not holdings_detail_df.empty:
            print("[INFO] Building ETF-Stock cross-reference matrices...")
            try:
                # 1. Row(ETF) vs Column(Stock code) Matrix
                etf_stock_matrix = holdings_detail_df.pivot_table(
                    index='ETF Ticker', 
                    columns='Holding Ticker', 
                    values='Holding Weight %', 
                    fill_value=0.0
                )
                ETF_STOCK_MATRIX_FILE.parent.mkdir(parents=True, exist_ok=True)
                etf_stock_matrix.to_csv(ETF_STOCK_MATRIX_FILE)
                
                # 2. Easy Lookup Table (Stock vs ETF and its % holdings)
                holdings_detail_df['Formatted_ETF'] = holdings_detail_df['ETF Ticker'] + " (" + holdings_detail_df['Holding Weight %'].astype(str) + "%)"
                stock_etf_lookup = (
                    holdings_detail_df.sort_values(['Holding Ticker', 'Holding Weight %'], ascending=[True, False])
                    .groupby('Holding Ticker')['Formatted_ETF']
                    .apply(lambda x: '; '.join(x))
                    .reset_index(name='ETFs Holding This Stock')
                )
                STOCK_ETF_LOOKUP_FILE.parent.mkdir(parents=True, exist_ok=True)
                stock_etf_lookup.to_csv(STOCK_ETF_LOOKUP_FILE, index=False)
            except Exception as e:
                print(f"  [ERROR] Cross-reference matrix generation failed: {e}")

    else:
        for col in [
            "Holding Count", "Known Holding Weight %", "Top Holdings", "Weighted Sector Mix",
            "Weighted Industry Mix", "Holdings Classification Text", "Holdings Classification Source"
        ]:
            etf_df[col] = ""

    etf_df = etf_df.sort_values(by=["Asset Class", "Theme", "Ticker"])
    
    us_etfs = etf_df[etf_df["Listing Exchange"] != "NSE"]
    nse_etfs = etf_df[etf_df["Listing Exchange"] == "NSE"]
    
    US_ETF_OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    us_etfs.to_csv(US_ETF_OUTPUT_FILE, index=False)
    
    NSE_ETF_OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    nse_etfs.to_csv(NSE_ETF_OUTPUT_FILE, index=False)

    mapping_columns = [
        "Ticker", "Security Name", "Asset Class", "Strategy", "Theme", "Geography", "Category Flags",
        "Holding Count", "Known Holding Weight %", "Top Holdings", "Weighted Sector Mix",
        "Weighted Industry Mix", "Holdings Classification Text", "Holdings Classification Source"
    ]
    if all(col in etf_df.columns for col in mapping_columns):
        US_CLASSIFICATION_OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        us_etfs[mapping_columns].to_csv(US_CLASSIFICATION_OUTPUT_FILE, index=False)
        
        NSE_CLASSIFICATION_OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        nse_etfs[mapping_columns].to_csv(NSE_CLASSIFICATION_OUTPUT_FILE, index=False)

    us_etfs_retained = len(us_etfs)
    nse_etfs_retained = len(nse_etfs)

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
        "nse_etfs_eliminated": nse_etf_pool_len - nse_etfs_retained,
        "holdings_detail_rows": len(holdings_detail_df)
    }


def main():
    parser = argparse.ArgumentParser(description="Unified Market Data Downloader, Multi-Step Elimination, and ETF Classifier Engine.")
    parser.add_argument("--default-geography", default="United States")
    parser.add_argument("--skip-etf-holdings", action="store_true", help="Skip ETF top-holdings enrichment.")
    parser.add_argument("--etf-holdings-limit", type=int, default=0, help="Process only the first N ETFs for holdings enrichment; 0 means all.")
    args = parser.parse_args()

    print("\n================================================================================")
    print("RUNNING MARKET DATA EXTRACTION, ELIMINATION & CLASSIFICATION ENGINE")
    print("================================================================================")

    print("[STEP 1/3] Fetching raw security listing metrics from global archives...")
    us_df = extract_raw_us_data()
    print(f"  - US Exchanges (NYSE/NASDAQ FTP) pulled: {len(us_df)} rows")
    in_df = extract_raw_nse_data()
    print(f"  - Indian Exchange (NSE Archives) pulled: {len(in_df)} rows")

    master_list = pd.concat([us_df, in_df], ignore_index=True).dropna(subset=["Ticker"])
    if master_list.empty:
        print("[CRITICAL] Ingested raw master compilation table is empty. Aborting execution.")
        return

    BASE_OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    master_list.to_csv(BASE_OUTPUT_FILE, index=False)

    print("[INFO] Fetching fundamental screener market cap layers from NASDAQ endpoints...")
    enrich_df = fetch_enrichment_data()
    if not enrich_df.empty:
        master_list = master_list.merge(enrich_df, on="Ticker", how="left")
        master_list.loc[master_list["ETF"] == "Y", "Industry"] = master_list.loc[master_list["ETF"] == "Y", "Industry"].fillna("ETF")
        print(f"  - Financial enrichment matrices aligned successfully for {len(enrich_df)} symbols.")
    else:
        print("  - Financial enrichment unavailable; continuing with raw listing data.")

    FINAL_OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    master_list.to_csv(FINAL_OUTPUT_FILE, index=False)

    print("[STEP 2/3] Processing segregation logic and active elimination blocks...")
    print("[STEP 3/3] Engineering multi-dimensional target category mapping matrices...")
    metrics = execute_elimination_and_classification(
        master_list,
        args.default_geography,
        enrich_holdings=not args.skip_etf_holdings,
        holdings_limit=args.etf_holdings_limit,
    )

    print("\n================================================================================")
    print("ENGINE EXECUTION ARCHIVE SUMMARY (GEOGRAPHICAL PARALLEL TRACKS)")
    print("================================================================================")
    print(f"  Total Raw Ingested Instruments Pool : {len(master_list)}")
    print(f"  - US Ingested Components            : {len(us_df)}")
    print(f"  - Indian Ingested Components        : {len(in_df)}")
    print("\n  [EQUITY SECURITY ROUTE]")
    print(f"  - Total Stocks Analyzed             : {metrics['stocks_ingested']}")
    print(f"    - US Stocks Pool                  : {metrics['us_stocks_pool']}")
    print(f"    - Indian Stocks Pool              : {metrics['nse_stocks_pool']}")
    print(f"  - Retained Valid Common Equities    : {metrics['stocks_retained']}")
    print(f"    - US Common Stocks Retained       : {metrics['us_stocks_retained']}")
    print(f"    - Indian Common Stocks Retained   : {metrics['nse_stocks_retained']}")
    print(f"  - Eliminated Non-Common Structures  : {metrics['stocks_eliminated']}")
    print(f"    - US Elements Eliminated          : {metrics['us_stocks_eliminated']}")
    print(f"    - Indian Elements Eliminated      : {metrics['nse_stocks_eliminated']}")
    print("\n  [EXCHANGE TRADED FUND ROUTE]")
    print(f"  - Total ETFs Analyzed               : {metrics['etfs_ingested']}")
    print(f"    - US Exchanges pool               : {metrics['us_etfs_pool']}")
    print(f"    - Indian ETFs Pool                : {metrics['nse_etfs_pool']}")
    print(f"  - Retained Structural Clean ETFs    : {metrics['etfs_retained']}")
    print(f"    - US Clean ETFs Retained          : {metrics['us_etfs_retained']}")
    print(f"    - Indian Clean ETFs Retained      : {metrics['nse_etfs_retained']}")
    print(f"  - Excluded ETFs                     : {metrics['etfs_eliminated']}")
    print(f"    - US ETFs Excluded                : {metrics['us_etfs_eliminated']}")
    print(f"    - Indian ETFs Excluded            : {metrics['nse_etfs_eliminated']}")
    print(f"  - ETF Holding Detail Rows           : {metrics['holdings_detail_rows']}")

    print("\n================================================================================")
    print("OUTPUT ARTIFACT LOCATION MANIFEST (SEPARATED ARCHIVES)")
    print("================================================================================")
    print("  [GLOBAL RAW CACHE HISTORIES]")
    print(f"  - Base Ingested Audit Ledger        :\n    {BASE_OUTPUT_FILE.resolve()}")
    print(f"  - Aligned Fundamental Master Sheet  :\n    {FINAL_OUTPUT_FILE.resolve()}")
    print(f"  - Master Eliminated Stocks Library  :\n    {ELIMINATED_STOCKS_OUTPUT_FILE.resolve()}")
    print(f"  - Master Excluded ETFs Library      :\n    {ELIMINATED_ETFS_OUTPUT_FILE.resolve()}")

    print("\n  [UNITED STATES EXCHANGES SPECIFIC MARKETS]")
    print(f"  - US Common Stocks Data Library     :\n    {US_COMMON_STOCK_OUTPUT_FILE.resolve()}")
    print(f"  - US Clean Structured ETF Library   :\n    {US_ETF_OUTPUT_FILE.resolve()}")
    print(f"  - US Matrix Slicing Comparator Map  :\n    {US_CLASSIFICATION_OUTPUT_FILE.resolve()}")
    print(f"  - ETF Holdings Detail Library       :\n    {ETF_HOLDINGS_DETAIL_OUTPUT_FILE.resolve()}")
    print(f"  - ETF to Stock Pivot Matrix         :\n    {ETF_STOCK_MATRIX_FILE.resolve()}")
    print(f"  - Stock to ETF Lookup Table         :\n    {STOCK_ETF_LOOKUP_FILE.resolve()}")

    print("\n  [NATIONAL STOCK EXCHANGE OF INDIA MARKETS]")
    print(f"  - NSE India Common Stocks Library   :\n    {NSE_COMMON_STOCK_OUTPUT_FILE.resolve()}")
    print(f"  - NSE India Structured ETF Library  :\n    {NSE_ETF_OUTPUT_FILE.resolve()}")
    print(f"  - NSE India Matrix Comparator Map   :\n    {NSE_CLASSIFICATION_OUTPUT_FILE.resolve()}")
    print("================================================================================\n")


if __name__ == "__main__":
    main()