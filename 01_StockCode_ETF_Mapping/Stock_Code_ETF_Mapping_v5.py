import pandas as pd
import yfinance as yf
import argparse
import sys
import os
import logging
import requests
import datetime
import re
import csv
import io
from functools import lru_cache

# =====================================================================
# DEFAULT CONFIGURATION (HARDCODE YOUR LOCATIONS AND EMBEDDED LISTS HERE)
# =====================================================================
# If CLI arguments are omitted, the script falls back to these values.

# 1. ETF Master Universe Configurations
DEFAULT_ETF_MASTER_PATH = "D:/Tools/00_StockCodeMaster/03_ETF/22-07-US_ETF_Master_Library.csv"   # Set to None or "" to skip file lookup

# 2. Seed Stock Configurations
DEFAULT_SEED_FILE_PATH = "D:/TMP/StockCode_ETFMapping-Codes.csv"   # Set to None or "" to skip file lookup

# 3. Stock Master Name Lookup Configuration
DEFAULT_STOCK_MASTER_PATH = "D:/TMP/YahooFinance_Codes_Energy-Oil.csv"   # Set to None or "" to skip local stock-name lookup
# =====================================================================

# Configure systematic tracking logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

def clean_ticker(ticker: str) -> str:
    """
    Normalizes operational market tickers across geographical zones.
    Converts legacy XNSE prefixes into standard .NS suffixes for Yahoo Finance routing.
    """
    if not isinstance(ticker, str):
        return ""
    
    ticker = ticker.strip().upper()
    if ticker.startswith("XNSE:"):
        ticker = ticker.replace("XNSE:", "") + ".NS"
    return ticker

def is_probable_header(value: str) -> bool:
    """
    Identifies common first-column CSV headers so files with or without headers
    can be read through the same first-column path.
    """
    normalized = str(value).strip().lower().replace("_", " ").replace("-", " ")
    header_tokens = (
        "stock", "ticker", "symbol", "code", "security", "company", "name",
        "etf", "fund"
    )
    return any(token in normalized for token in header_tokens)

def is_valid_ticker_text(value: str) -> bool:
    """
    Applies a conservative ticker shape check after market-specific normalization.
    """
    return bool(re.fullmatch(r"[A-Z0-9][A-Z0-9.\-^=]*", value))

def normalize_header(value: str) -> str:
    return str(value).strip().lower().replace("_", " ").replace("-", " ")

def extract_tickers_from_csv(file_path: str) -> list:
    """
    Safely accesses a CSV file and extracts targets from the primary index column.
    Does not depend on hardcoded header names; isolates index 0 column directly.
    """
    if not file_path or not os.path.exists(file_path):
        logging.error(f"File Access Error: File path '{file_path}' does not exist or is empty.")
        return []
        
    try:
        df = pd.read_csv(
            file_path,
            encoding='utf-8-sig',
            header=None,
            usecols=[0],
            dtype=str,
            keep_default_na=False,
            low_memory=False
        )
        if df.empty:
            logging.warning(f"File handling notification: Entity at '{file_path}' contains zero rows.")
            return []
        
        raw_tickers = df.iloc[:, 0].dropna().astype(str).tolist()
        if raw_tickers and is_probable_header(raw_tickers[0]):
            raw_tickers = raw_tickers[1:]
        
        cleaned_tickers = [
            clean_ticker(t)
            for t in raw_tickers
            if t.strip() and is_valid_ticker_text(clean_ticker(t))
        ]
        seen = set()
        deduped = [x for x in cleaned_tickers if not (x in seen or seen.add(x))]
        logging.info(f"Successfully read {len(deduped)} unique codes from '{file_path}'.")
        return deduped
        
    except pd.errors.EmptyDataError:
        logging.warning(f"Parsing Warning: File allocation at '{file_path}' is empty or corrupt.")
        return []
    except Exception as e:
        logging.error(f"File IO System Exception during read operation on '{file_path}': {str(e)}")
        return []

def load_code_name_map(file_path: str) -> dict:
    """
    Loads a mapping of clean tickers to display names.
    Column 0 is the code column. If a header row exists, known name columns are
    preferred; without a header, column 1 is treated as the optional name.
    """
    mapping = {}
    if file_path and os.path.exists(file_path):
        try:
            header_probe = pd.read_csv(
                file_path,
                encoding='utf-8-sig',
                header=None,
                nrows=1,
                dtype=str,
                keep_default_na=False,
                low_memory=False
            )
            if header_probe.empty or len(header_probe.columns) < 2:
                return mapping

            first_row = [str(value).strip() for value in header_probe.iloc[0].tolist()]
            has_header = bool(first_row and is_probable_header(first_row[0]))
            name_col_index = None
            skiprows = None

            if has_header:
                preferred_name_headers = ("security name", "company name", "name", "fund name", "etf name")
                for index, header in enumerate(first_row):
                    if normalize_header(header) in preferred_name_headers:
                        name_col_index = index
                        break
                skiprows = 1
            else:
                name_col_index = 1

            if name_col_index is None:
                logging.info(f"No recognized name column found in '{file_path}'.")
                return mapping

            df = pd.read_csv(
                file_path,
                encoding='utf-8-sig',
                header=None,
                usecols=[0, name_col_index],
                skiprows=skiprows,
                dtype=str,
                keep_default_na=False,
                low_memory=False
            )

            for _, row in df.iterrows():
                ticker = clean_ticker(str(row.iloc[0]))
                display_name = str(row.iloc[1]).strip()
                if ticker and display_name:
                    mapping[ticker] = display_name
        except Exception as e:
            logging.error(f"Error loading security names from '{file_path}': {str(e)}")
    return mapping

def load_security_names(file_path: str) -> dict:
    """
    Backward-compatible wrapper for seed stock security names.
    """
    return load_code_name_map(file_path)

def parse_inline_codes(raw_codes: str, label: str) -> list:
    """
    Parses comma-separated CLI code lists and rejects empty or malformed entries.
    """
    parsed_codes = []
    invalid_codes = []
    for code in str(raw_codes).split(','):
        cleaned_code = clean_ticker(code)
        if not cleaned_code:
            continue
        if is_valid_ticker_text(cleaned_code):
            parsed_codes.append(cleaned_code)
        else:
            invalid_codes.append(code.strip())

    if invalid_codes:
        logging.error(f"{label} CLI validation failed. Invalid code(s): {', '.join(invalid_codes)}")
        return []

    seen = set()
    deduped = [x for x in parsed_codes if not (x in seen or seen.add(x))]
    if not deduped:
        logging.error(f"{label} CLI validation failed. No valid codes were supplied.")
    return deduped

def resolve_seed_source(execution_arguments) -> tuple:
    """
    Resolves seed stocks using strict precedence:
    CLI seed codes, CLI seed file, default seed file only when no CLI seed input exists.
    """
    snapshot = {
        "Seed Source": "",
        "Seed Source Detail": "",
        "Seed Status": "FAIL",
        "Seed Count": 0
    }

    if execution_arguments.seed_codes:
        logging.info("Extracting Seed Codes passed via CLI inline parameter.")
        seed_codes = parse_inline_codes(execution_arguments.seed_codes, "Seed Codes")
        snapshot.update({
            "Seed Source": "CLI --seed_codes",
            "Seed Source Detail": execution_arguments.seed_codes,
            "Seed Count": len(seed_codes),
            "Seed Status": "OK" if seed_codes else "FAIL"
        })
        return seed_codes, "", snapshot

    if execution_arguments.seed_file:
        logging.info(f"Extracting Seed Codes from CLI file path: {execution_arguments.seed_file}")
        seed_codes = extract_tickers_from_csv(execution_arguments.seed_file)
        snapshot.update({
            "Seed Source": "CLI --seed_file",
            "Seed Source Detail": execution_arguments.seed_file,
            "Seed Count": len(seed_codes),
            "Seed Status": "OK" if seed_codes else "FAIL"
        })
        return seed_codes, execution_arguments.seed_file if seed_codes else "", snapshot

    if DEFAULT_SEED_FILE_PATH:
        logging.info(f"Extracting Seed Codes from script config path: {DEFAULT_SEED_FILE_PATH}")
        seed_codes = extract_tickers_from_csv(DEFAULT_SEED_FILE_PATH)
        snapshot.update({
            "Seed Source": "DEFAULT_SEED_FILE_PATH",
            "Seed Source Detail": DEFAULT_SEED_FILE_PATH,
            "Seed Count": len(seed_codes),
            "Seed Status": "OK" if seed_codes else "FAIL"
        })
        return seed_codes, DEFAULT_SEED_FILE_PATH if seed_codes else "", snapshot

    logging.error("No CLI seed input was provided and DEFAULT_SEED_FILE_PATH is empty.")
    snapshot.update({
        "Seed Source": "NONE",
        "Seed Source Detail": "No CLI seed input and no default seed path configured."
    })
    return [], "", snapshot

def resolve_etf_source(execution_arguments) -> tuple:
    """
    Resolves ETF universe using strict precedence:
    CLI ETF codes, CLI ETF file, default ETF file only when no CLI ETF input exists.
    """
    snapshot = {
        "ETF Source": "",
        "ETF Source Detail": "",
        "ETF Status": "FAIL",
        "ETF Count": 0
    }

    if execution_arguments.etf_codes:
        logging.info("Extracting ETF Codes passed via CLI inline parameter.")
        etf_codes = parse_inline_codes(execution_arguments.etf_codes, "ETF Codes")
        snapshot.update({
            "ETF Source": "CLI --etf_codes",
            "ETF Source Detail": execution_arguments.etf_codes,
            "ETF Count": len(etf_codes),
            "ETF Status": "OK" if etf_codes else "FAIL"
        })
        return etf_codes, "", snapshot

    if execution_arguments.etf_master:
        logging.info(f"Loading ETF Master Universe from CLI path: {execution_arguments.etf_master}")
        etf_codes = extract_tickers_from_csv(execution_arguments.etf_master)
        snapshot.update({
            "ETF Source": "CLI --etf_master",
            "ETF Source Detail": execution_arguments.etf_master,
            "ETF Count": len(etf_codes),
            "ETF Status": "OK" if etf_codes else "FAIL"
        })
        return etf_codes, execution_arguments.etf_master if etf_codes else "", snapshot

    if DEFAULT_ETF_MASTER_PATH:
        logging.info(f"Loading ETF Master Universe from script config path: {DEFAULT_ETF_MASTER_PATH}")
        etf_codes = extract_tickers_from_csv(DEFAULT_ETF_MASTER_PATH)
        snapshot.update({
            "ETF Source": "DEFAULT_ETF_MASTER_PATH",
            "ETF Source Detail": DEFAULT_ETF_MASTER_PATH,
            "ETF Count": len(etf_codes),
            "ETF Status": "OK" if etf_codes else "FAIL"
        })
        return etf_codes, DEFAULT_ETF_MASTER_PATH if etf_codes else "", snapshot

    logging.error("No CLI ETF input was provided and DEFAULT_ETF_MASTER_PATH is empty.")
    snapshot.update({
        "ETF Source": "NONE",
        "ETF Source Detail": "No CLI ETF input and no default ETF path configured."
    })
    return [], "", snapshot

def resolve_stock_name_source(execution_arguments) -> tuple:
    """
    Resolves the optional local stock-name master used to enrich seed stock rows.
    This source does not control engine execution; it only improves display names.
    """
    stock_master_path = execution_arguments.stock_master or DEFAULT_STOCK_MASTER_PATH
    snapshot = {
        "Stock Name Source": "NONE",
        "Stock Name Source Detail": "",
        "Stock Name Source Status": "SKIPPED"
    }

    if not stock_master_path:
        return "", snapshot

    if os.path.exists(stock_master_path):
        source_label = "CLI --stock_master" if execution_arguments.stock_master else "DEFAULT_STOCK_MASTER_PATH"
        snapshot.update({
            "Stock Name Source": source_label,
            "Stock Name Source Detail": stock_master_path,
            "Stock Name Source Status": "OK"
        })
        return stock_master_path, snapshot

    logging.warning(f"Stock-name master file was not found: {stock_master_path}")
    snapshot.update({
        "Stock Name Source": "CLI --stock_master" if execution_arguments.stock_master else "DEFAULT_STOCK_MASTER_PATH",
        "Stock Name Source Detail": stock_master_path,
        "Stock Name Source Status": "NOT FOUND"
    })
    return "", snapshot

def print_execution_snapshot(execution_snapshot: dict):
    print("\n" + "="*50)
    print(" EXECUTION SNAPSHOT")
    print("="*50)
    for key, value in execution_snapshot.items():
        print(f"{key:<25}: {value}")
    print("="*50 + "\n")

def csv_summary_row(label: str, value) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="")
    writer.writerow([label, value])
    return buffer.getvalue() + "\n"

def get_ltp(ticker: str) -> float:
    """
    Fetches Last Traded Price (Close of the most recent day) via yfinance.
    """
    try:
        ticker_instance = yf.Ticker(ticker)
        hist = ticker_instance.history(period="1d")
        if not hist.empty:
            return float(hist['Close'].iloc[-1])
    except Exception:
        pass
    return 0.0

@lru_cache(maxsize=1024)
def get_security_display_name(ticker: str) -> str:
    """
    Best-effort lookup for a stock or ETF full name when no CSV name is available.
    """
    try:
        ticker_instance = yf.Ticker(ticker)
        info = ticker_instance.get_info()
        return str(info.get("longName") or info.get("shortName") or "").strip()
    except Exception:
        return ""

def parse_weight_value(raw_value) -> float:
    """
    Extracts numerical allocation matrices safely from raw values.
    Handles percentage strings (e.g. '4.5%'), standard floats, and fractional variants.
    """
    if pd.isna(raw_value):
        return 0.0
        
    if isinstance(raw_value, str):
        raw_value = raw_value.replace('%', '').strip()
        
    try:
        weight = float(raw_value)
        if 0.0 < weight < 1.0:
            weight = weight * 100.0
        return weight
    except (ValueError, TypeError):
        return 0.0

def process_etf_portfolio_data(etf_ticker: str) -> dict:
    """
    Queries full ETF holdings from the alternate iShares/Yahoo holdings page or underlying json endpoints.
    Alternative approach using direct web scrape/API fallback to bypass the yfinance top 10 limits.
    """
    holdings_extracted = {}
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        url = f"https://query2.finance.yahoo.com/v1/finance/etfProfile?symbol={etf_ticker}"
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            holdings = data.get('finance', {}).get('result', [])
            if holdings and 'holdings' in holdings[0]:
                for h in holdings[0]['holdings']:
                    symbol = clean_ticker(h.get('symbol', ''))
                    if not symbol:
                        continue
                    holding_percent = h.get('holdingPercent', 0)
                    weight = parse_weight_value(holding_percent)
                    holdings_extracted[symbol] = weight
                return holdings_extracted
    except Exception as e:
        logging.debug(f"Alternative ETF holdings endpoint bypassed for {etf_ticker}: {str(e)}")

    try:
        ticker_instance = yf.Ticker(etf_ticker)
        try:
            fund_holdings = ticker_instance.funds_data.holdings
            if fund_holdings is not None and not fund_holdings.empty:
                for idx, row in fund_holdings.iterrows():
                    symbol = clean_ticker(str(idx))
                    if not symbol:
                        continue
                    col_name = [c for c in row.index if 'weight' in str(c).lower() or 'percent' in str(c).lower()][0]
                    holdings_extracted[symbol] = parse_weight_value(row[col_name])
                return holdings_extracted
        except Exception:
            pass

        holdings_df = ticker_instance.funds_data.top_holdings
        if holdings_df is not None and not holdings_df.empty:
            holdings_df.columns = [str(c).lower().strip() for c in holdings_df.columns]
            if 'symbol' in holdings_df.columns:
                holdings_df = holdings_df.set_index('symbol')
            weight_column = [c for c in holdings_df.columns if any(kw in c for kw in ['percent', 'holding', 'weight', 'allocation'])][0]
            for index_ticker, row in holdings_df.iterrows():
                symbol_key = clean_ticker(index_ticker)
                if not symbol_key:
                    continue
                holdings_extracted[symbol_key] = parse_weight_value(row[weight_column])
    except Exception as e:
        logging.warning(f"API profile extract failed for {etf_ticker}. Skipping. ({str(e)})")
        
    return holdings_extracted

def execute_coverage_mapping(
    seed_stocks: list,
    etf_universe: list,
    min_weight_pct: float,
    output_path: str,
    seed_file_path: str,
    etf_file_path: str,
    stock_master_file_path: str,
    allow_yfinance_names: bool,
    execution_snapshot: dict
):
    """
    Executes cross-referencing analysis across all specified matrices.
    Maps core assets to qualifying institutional allocations, calculates ETF stock counts,
    sorts ETF columns by total seed stock coverage count, and writes to CSV.
    """
    cleaned_seed_targets = [clean_ticker(s) for s in seed_stocks if clean_ticker(s)]
    relational_matrix = {stock: {} for stock in cleaned_seed_targets}
    
    etf_cols = [clean_ticker(e) for e in etf_universe if str(e).strip()]
    
    logging.info(f"System Operational Initialization: Scanning {len(etf_cols)} ETFs across {len(cleaned_seed_targets)} targeted seed assets.")
    
    etf_stock_holdings_count = {etf: 0 for etf in etf_cols}
    
    for etf in etf_cols:
        etf_clean = str(etf).strip().upper()
        if not etf_clean:
            continue
            
        logging.info(f"Analyzing Fund Assets: {etf_clean}...")
        portfolio_composition = process_etf_portfolio_data(etf_clean)
        
        if not portfolio_composition:
            continue
            
        for seed_stock in cleaned_seed_targets:
            if seed_stock in portfolio_composition:
                allocation_weight = portfolio_composition[seed_stock]
                if allocation_weight >= min_weight_pct:
                    relational_matrix[seed_stock][etf_clean] = allocation_weight
                    etf_stock_holdings_count[etf_clean] += 1

    # Eliminate ETFs that do not contain any of the seed stock codes
    valid_etf_cols = [etf for etf in etf_cols if etf_stock_holdings_count[etf] > 0]
    sorted_etf_cols = sorted(valid_etf_cols, key=lambda e: etf_stock_holdings_count[e], reverse=True)

    logging.info(f"Analysis Complete. {len(sorted_etf_cols)} out of {len(etf_cols)} ETFs contained matching seed stock(s).")

    seed_security_names_map = load_code_name_map(stock_master_file_path)
    seed_security_names_map.update(load_security_names(seed_file_path))
    etf_security_names_map = load_code_name_map(etf_file_path)
    execution_snapshot["Seed Names Resolved Locally"] = sum(1 for stock in cleaned_seed_targets if stock in seed_security_names_map)
    execution_snapshot["ETF Names Resolved Locally"] = sum(1 for etf in sorted_etf_cols if etf in etf_security_names_map)

    count_row = {
        "Stock Code": "Stock# in this ETF",
        "Company Name": "",
        "LTP": "",
        "Total ETF Count": ""
    }
    etf_name_row = {
        "Stock Code": "ETF Full Name",
        "Company Name": "",
        "LTP": "",
        "Total ETF Count": ""
    }
    for etf_id in sorted_etf_cols:
        count_row[etf_id] = str(etf_stock_holdings_count[etf_id])
        etf_name_row[etf_id] = etf_security_names_map.get(etf_id, "")
        if not etf_name_row[etf_id] and allow_yfinance_names:
            etf_name_row[etf_id] = get_security_display_name(etf_id)

    matrix_output_records = [count_row, etf_name_row]
    
    seed_stocks_matched = 0
    
    for stock_symbol in cleaned_seed_targets:
        sec_name = seed_security_names_map.get(stock_symbol, "")
        if not sec_name and allow_yfinance_names:
            sec_name = get_security_display_name(stock_symbol)
        ltp_val = get_ltp(stock_symbol)
        
        row_data = {
            "Stock Code": stock_symbol,
            "Company Name": sec_name,
            "LTP": f"{ltp_val:.2f}" if ltp_val > 0.0 else ""
        }
        
        etf_count = 0
        for etf_id in sorted_etf_cols:
            weight = relational_matrix[stock_symbol].get(etf_id, 0.0)
            if weight > 0.0:
                row_data[etf_id] = f"{weight:.2f}"
                etf_count += 1
            else:
                row_data[etf_id] = ""
                
        row_data["Total ETF Count"] = etf_count
        if etf_count > 0:
            seed_stocks_matched += 1
            
        matrix_output_records.append(row_data)
        
    header_df = pd.DataFrame(matrix_output_records[:2])
    stocks_df = pd.DataFrame(matrix_output_records[2:])
    
    if not stocks_df.empty and "Total ETF Count" in stocks_df.columns:
        stocks_df = stocks_df.sort_values(by="Total ETF Count", ascending=False)
        
    output_dataframe = pd.concat([header_df, stocks_df], ignore_index=True)
    
    base_cols = ["Stock Code", "Company Name", "LTP", "Total ETF Count"]
    all_cols = base_cols + sorted_etf_cols
    
    for col in all_cols:
        if col not in output_dataframe.columns:
            output_dataframe[col] = ""
            
    output_dataframe = output_dataframe[all_cols]
    
    # Calculate Summary Details
    total_seed_codes_read = len(cleaned_seed_targets)
    total_etf_processed = len(etf_cols)
    matching_etf_count = len(sorted_etf_cols)
    seed_stocks_not_found = total_seed_codes_read - seed_stocks_matched
    etf_not_matching = total_etf_processed - matching_etf_count
    
    execution_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        script_name = os.path.basename(__file__)
    except NameError:
        script_name = os.path.basename(sys.argv[0])
        
    summary_rows = [
        ("Summary Information", ""),
        ("Script Code Name", script_name),
        ("Time of Execution", execution_time),
        ("Engine Status", execution_snapshot.get('Engine Status', '')),
        ("Seed Source", execution_snapshot.get('Seed Source', '')),
        ("Seed Source Detail", execution_snapshot.get('Seed Source Detail', '')),
        ("Seed Source Status", execution_snapshot.get('Seed Status', '')),
        ("Seed Source Count", execution_snapshot.get('Seed Count', '')),
        ("ETF Source", execution_snapshot.get('ETF Source', '')),
        ("ETF Source Detail", execution_snapshot.get('ETF Source Detail', '')),
        ("ETF Source Status", execution_snapshot.get('ETF Status', '')),
        ("ETF Source Count", execution_snapshot.get('ETF Count', '')),
        ("Stock Name Source", execution_snapshot.get('Stock Name Source', '')),
        ("Stock Name Source Detail", execution_snapshot.get('Stock Name Source Detail', '')),
        ("Stock Name Source Status", execution_snapshot.get('Stock Name Source Status', '')),
        ("Seed Names Resolved Locally", execution_snapshot.get('Seed Names Resolved Locally', '')),
        ("ETF Names Resolved Locally", execution_snapshot.get('ETF Names Resolved Locally', '')),
        ("Total Seed Codes Read", total_seed_codes_read),
        ("Total ETF Processed", total_etf_processed),
        ("Matching Codes vs ETF Count", f"{seed_stocks_matched} vs {matching_etf_count}"),
        ("Seed Stock Codes Not Found", seed_stocks_not_found),
        ("ETF Not Matching", etf_not_matching),
        ("Output File Name", os.path.basename(output_path)),
    ]
    summary_csv_text = "".join(csv_summary_row(label, value) for label, value in summary_rows) + "\n"
    
    # Display summary to user via console
    print("\n" + "="*50)
    print(" EXECUTION SUMMARY")
    print("="*50)
    print(f"Script Code Name            : {script_name}")
    print(f"Time of Execution           : {execution_time}")
    print(f"Engine Status               : {execution_snapshot.get('Engine Status', '')}")
    print(f"Seed Source                 : {execution_snapshot.get('Seed Source', '')}")
    print(f"Seed Source Detail          : {execution_snapshot.get('Seed Source Detail', '')}")
    print(f"Seed Source Status          : {execution_snapshot.get('Seed Status', '')}")
    print(f"ETF Source                  : {execution_snapshot.get('ETF Source', '')}")
    print(f"ETF Source Detail           : {execution_snapshot.get('ETF Source Detail', '')}")
    print(f"ETF Source Status           : {execution_snapshot.get('ETF Status', '')}")
    print(f"Stock Name Source           : {execution_snapshot.get('Stock Name Source', '')}")
    print(f"Stock Name Source Status    : {execution_snapshot.get('Stock Name Source Status', '')}")
    print(f"Seed Names Resolved Locally : {execution_snapshot.get('Seed Names Resolved Locally', '')}")
    print(f"ETF Names Resolved Locally  : {execution_snapshot.get('ETF Names Resolved Locally', '')}")
    print(f"Total Seed Codes Read       : {total_seed_codes_read}")
    print(f"Total ETF Processed         : {total_etf_processed}")
    print(f"Matching Codes vs ETF Count : {seed_stocks_matched} vs {matching_etf_count}")
    print(f"Seed Stock Codes Not Found  : {seed_stocks_not_found}")
    print(f"ETF Not Matching            : {etf_not_matching}")
    print(f"Output File Name            : {os.path.basename(output_path)}")
    print("="*50 + "\n")
    
    try:
        directory_check = os.path.dirname(output_path)
        if directory_check and not os.path.exists(directory_check):
            os.makedirs(directory_check, exist_ok=True)
            
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            f.write(summary_csv_text)
            output_dataframe.to_csv(f, index=False)
            
        logging.info(f"Analysis Routine Terminated Satisfactorily. Data saved directly to resource path: '{output_path}'")
        
    except Exception as e:
        logging.error(f"Critical System Failure: Storage array conversion error at location target '{output_path}': {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    engine_help_text = """
Stock Code to ETF Mapping Engine

Purpose:
  Builds a stock-to-ETF coverage matrix. For every seed stock code, the engine
  scans the selected ETF universe, checks ETF holdings, and records allocation
  weights where the stock is present.

Input precedence:
  Seed stocks are resolved independently from ETFs.

  Seed stocks:
    1. --seed_codes / -c: explicit comma-separated stock codes.
    2. --seed_file / -f: CSV file; first column is read as stock code.
    3. DEFAULT_SEED_FILE_PATH: used only when no seed CLI input is supplied.
    4. Failure: invalid explicit CLI seed input fails the engine.

  ETF universe:
    1. --etf_codes: explicit comma-separated ETF codes.
    2. --etf_master / -e: CSV file; first column is read as ETF code.
    3. DEFAULT_ETF_MASTER_PATH: used only when no ETF CLI input is supplied.
    4. Failure: invalid explicit CLI ETF input fails the engine.

CSV handling:
  - Only the first column is used for seed and ETF code extraction.
  - Files may have a header row or no header row.
  - Tickers are normalized, deduplicated, and validated.
  - XNSE: symbols are converted to .NS Yahoo Finance symbols.
  - CSV name enrichment is header-aware. Known name columns include
    Security Name, Company Name, Name, Fund Name, and ETF Name.

Name enrichment:
  - Seed company names are loaded from --stock_master or
    DEFAULT_STOCK_MASTER_PATH, then overridden by names in --seed_file when
    the seed file has a recognized name column.
  - ETF full names are loaded from the selected ETF master file when it has a
    recognized name column such as Security Name.
  - Yahoo name lookup is disabled by default; use --name_lookup yfinance to
    fill missing local names through yfinance.

Output CSV layout:
  - A summary block is written first.
  - Matrix columns are:
      Stock Code, Company Name, LTP, Total ETF Count, <ETF columns...>
  - First matrix row: Stock# in this ETF.
  - Second matrix row: ETF Full Name.
  - Remaining rows: one row per seed stock, sorted by Total ETF Count.

Examples:
  python Stock_Code_ETF_Mapping_v5.py -f D:/input/seeds.csv --output D:/TMP/out.csv
  python Stock_Code_ETF_Mapping_v5.py -c MU,TSLA --etf_codes SPY,QQQ
  python Stock_Code_ETF_Mapping_v5.py -f seeds.csv -e etfs.csv --stock_master stocks.csv
"""
    execution_parser = argparse.ArgumentParser(
        description=engine_help_text,
        formatter_class=argparse.RawTextHelpFormatter,
        add_help=False
    )
    execution_parser.add_argument("-h", "-?", "--help", action="help", help="Show this help message and exit.")
    # Added aliasing for flags with single dashes to prevent unrecognized arguments errors
    execution_parser.add_argument("-e", "--etf_master", "-etf_master", type=str, help="Path validation pointer for global Master ETF CSV repository.")
    execution_parser.add_argument("-etf_codes", "--etf_codes", type=str, help="CLI inline comma-separated ETF targets override parameter (e.g. SPY,QQQ).")
    execution_parser.add_argument("-f", "--seed_file", "-seed_file", type=str, help="Path validation pointer for targeted evaluation Seed stock CSV repository.")
    execution_parser.add_argument("-c", "--seed_codes", "-seed_codes", type=str, help="CLI inline comma-separated targets override parameter (e.g. MPWR,TSLA,XNSE:TCS).")
    execution_parser.add_argument("--stock_master", "-stock_master", type=str, help="Optional local stock master CSV for seed company-name enrichment.")
    execution_parser.add_argument("--name_lookup", choices=["local", "yfinance"], default="local", help="Name enrichment mode. Default 'local' avoids extra Yahoo name lookups.")
    execution_parser.add_argument("-w", "--min_weight", "-min_weight", type=float, default=0.0, help="Minimum percentage boundary allocation threshold value.")
    execution_parser.add_argument("-o", "--output", "-output", type=str, default="D:/TMP/Stock_Code_ETF_Mapping/StockCode-ETF-Mapping-Output-{date}.csv", help="System destination target file layout path.")
    
    execution_arguments = execution_parser.parse_args()
    
    etf_master_universe, resolved_etf_file, etf_snapshot = resolve_etf_source(execution_arguments)
    aggregated_seeds, resolved_seed_file, seed_snapshot = resolve_seed_source(execution_arguments)
    resolved_stock_master_file, stock_name_snapshot = resolve_stock_name_source(execution_arguments)
    execution_snapshot = {
        "Engine Status": "OK",
        **seed_snapshot,
        **etf_snapshot,
        **stock_name_snapshot
    }
            
    operational_seeds_deduped = []
    seen_seeds = set()
    for raw_seed in aggregated_seeds:
        processed_seed = clean_ticker(raw_seed)
        if processed_seed and processed_seed not in seen_seeds:
            seen_seeds.add(processed_seed)
            operational_seeds_deduped.append(processed_seed)
            
    if not operational_seeds_deduped:
        execution_snapshot["Engine Status"] = "FAIL"
        logging.error("Execution Constraint Failure: Seed validation failed. No valid stock targets resolved.")
        logging.error("Please supply a valid seed code via -seed_codes 'TICKER' or a valid file via -seed_file 'path/to/file.csv'.")
        print_execution_snapshot(execution_snapshot)
        sys.exit(1)

    if not etf_master_universe:
        execution_snapshot["Engine Status"] = "FAIL"
        logging.error("Execution Constraint Failure: System could not resolve any valid ETF tickers to scan.")
        print_execution_snapshot(execution_snapshot)
        sys.exit(1)
        
    logging.info(f"Final Validation: Ready to process {len(operational_seeds_deduped)} distinct seed codes against {len(etf_master_universe)} ETF codes.")
        
    execute_coverage_mapping(
        seed_stocks=operational_seeds_deduped,
        etf_universe=etf_master_universe,
        min_weight_pct=execution_arguments.min_weight,
        output_path=execution_arguments.output,
        seed_file_path=resolved_seed_file,
        etf_file_path=resolved_etf_file,
        stock_master_file_path=resolved_stock_master_file,
        allow_yfinance_names=execution_arguments.name_lookup == "yfinance",
        execution_snapshot=execution_snapshot
    )
