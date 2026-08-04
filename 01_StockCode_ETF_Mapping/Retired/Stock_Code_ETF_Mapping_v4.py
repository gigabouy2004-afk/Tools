import pandas as pd
import yfinance as yf
import argparse
import sys
import os
import logging
import requests

# =====================================================================
# DEFAULT CONFIGURATION (HARDCODE YOUR LOCATIONS AND EMBEDDED LISTS HERE)
# =====================================================================
# If CLI arguments are omitted, the script falls back to these values.

# 1. ETF Master Universe Configurations
DEFAULT_ETF_MASTER_PATH = "D:/Tools/StockCodeMaster/03_ETF/18-06-US_ETF_Master_Library.csv"   # Set to None or "" to skip file lookup

# 2. Seed Stock Configurations
DEFAULT_SEED_FILE_PATH = "D:/TMP/Seed_Stocks.csv"   # Set to None or "" to skip file lookup

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

def extract_tickers_from_csv(file_path: str) -> list:
    """
    Safely accesses a CSV file and extracts targets from the primary index column.
    Does not depend on hardcoded header names; isolates index 0 column directly.
    """
    if not file_path or not os.path.exists(file_path):
        return []
        
    try:
        df = pd.read_csv(file_path, encoding='utf-8')
        if df.empty:
            logging.warning(f"File handling notification: Entity at '{file_path}' contains zero rows.")
            return []
        
        first_column_identifier = df.columns[0]
        raw_tickers = df[first_column_identifier].dropna().astype(str).tolist()
        
        cleaned_tickers = [clean_ticker(t) for t in raw_tickers if t.strip()]
        seen = set()
        return [x for x in cleaned_tickers if not (x in seen or seen.add(x))]
        
    except pd.errors.EmptyDataError:
        logging.warning(f"Parsing Warning: File allocation at '{file_path}' is empty or corrupt.")
        return []
    except Exception as e:
        logging.error(f"File IO System Exception during read operation on '{file_path}': {str(e)}")
        return []

def load_security_names(file_path: str) -> dict:
    """
    Loads a mapping of clean tickers to Security (Company) Names from the seed stock CSV.
    """
    mapping = {}
    if file_path and os.path.exists(file_path):
        try:
            df = pd.read_csv(file_path, encoding='utf-8')
            if len(df.columns) >= 2:
                for _, row in df.iterrows():
                    ticker = clean_ticker(str(row.iloc[0]))
                    if ticker:
                        mapping[ticker] = str(row.iloc[1])
        except Exception as e:
            logging.error(f"Error loading security names from '{file_path}': {str(e)}")
    return mapping

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
        # If it's fractional (0.0 to 1.0), convert to percentage
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
        # Fallback to direct Yahoo Finance holding JSON endpoint / web scrape approach
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
                    # Ensure it's correctly mapped to a percentage (e.g., 0.05 -> 5.0)
                    weight = parse_weight_value(holding_percent)
                    holdings_extracted[symbol] = weight
                return holdings_extracted
    except Exception as e:
        logging.debug(f"Alternative ETF holdings endpoint bypassed for {etf_ticker}: {str(e)}")

    # Fallback to yfinance standard methods if alternative endpoint fails
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
        logging.warning(f"Comprehensive API failure extracting profile for {etf_ticker}: {str(e)}")
        
    return holdings_extracted

def execute_coverage_mapping(seed_stocks: list, etf_universe: list, min_weight_pct: float, output_path: str, seed_file_path: str):
    """
    Executes cross-referencing analysis across all specified matrices.
    Maps core assets to qualifying institutional allocations, calculates ETF stock counts,
    sorts ETF columns by total seed stock coverage count, and writes to CSV.
    """
    cleaned_seed_targets = [clean_ticker(s) for s in seed_stocks if clean_ticker(s)]
    relational_matrix = {stock: {} for stock in cleaned_seed_targets}
    
    # Restrict output columns strictly to parsed/configured ETF list entries
    etf_cols = [clean_ticker(e) for e in etf_universe if str(e).strip()]
    
    logging.info(f"System Operational Initialization: Scanning {len(etf_cols)} ETFs across {len(cleaned_seed_targets)} targeted underlying assets.")
    
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

    sorted_etf_cols = sorted(etf_cols, key=lambda e: etf_stock_holdings_count[e], reverse=True)

    count_row = {
        "Stock Code": "Stock# in this ETF",
        "Security Name": "",
        "LTP": "",
        "Total ETF Count": ""
    }
    for etf_id in sorted_etf_cols:
        count_row[etf_id] = str(etf_stock_holdings_count[etf_id])

    matrix_output_records = [count_row]
    security_names_map = load_security_names(seed_file_path)
    
    for stock_symbol in cleaned_seed_targets:
        sec_name = security_names_map.get(stock_symbol, "")
        ltp_val = get_ltp(stock_symbol)
        
        row_data = {
            "Stock Code": stock_symbol,
            "Security Name": sec_name,
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
        matrix_output_records.append(row_data)
        
    header_df = pd.DataFrame([matrix_output_records[0]])
    stocks_df = pd.DataFrame(matrix_output_records[1:])
    
    if not stocks_df.empty and "Total ETF Count" in stocks_df.columns:
        stocks_df = stocks_df.sort_values(by="Total ETF Count", ascending=False)
        
    output_dataframe = pd.concat([header_df, stocks_df], ignore_index=True)
    
    base_cols = ["Stock Code", "Security Name", "LTP", "Total ETF Count"]
    all_cols = base_cols + sorted_etf_cols
    
    for col in all_cols:
        if col not in output_dataframe.columns:
            output_dataframe[col] = ""
            
    output_dataframe = output_dataframe[all_cols]
    
    try:
        directory_check = os.path.dirname(output_path)
        if directory_check and not os.path.exists(directory_check):
            os.makedirs(directory_check, exist_ok=True)
            
        output_dataframe.to_csv(output_path, index=False, encoding='utf-8')
        logging.info(f"Analysis Routine Terminated Satisfactorily. Data saved directly to resource path: '{output_path}'")
        
    except Exception as e:
        logging.error(f"Critical System Failure: Storage array conversion error at location target '{output_path}': {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    execution_parser = argparse.ArgumentParser(
        description="Cross-platform Equity System Portfolio Architecture Analysis Engine."
    )
    execution_parser.add_argument("--etf_master", type=str, help="Path validation pointer for global Master ETF CSV repository.")
    execution_parser.add_argument("--seed_file", type=str, help="Path validation pointer for targeted evaluation Seed stock CSV repository.")
    execution_parser.add_argument("--seed_codes", type=str, help="CLI inline comma-separated targets override parameter (e.g. MPWR,TSLA,XNSE:TCS).")
    execution_parser.add_argument("--min_weight", type=float, default=0.0, help="Minimum percentage boundary allocation threshold value.")
    execution_parser.add_argument("--output", type=str, default="etf_coverage_matrix.csv", help="System destination target file layout path.")
    
    execution_arguments = execution_parser.parse_args()
    
    etf_master_universe = []
    resolved_etf_file = ""
    
    if execution_arguments.etf_master:
        logging.info(f"Loading ETF Master Universe from CLI path: {execution_arguments.etf_master}")
        etf_master_universe = extract_tickers_from_csv(execution_arguments.etf_master)
        resolved_etf_file = execution_arguments.etf_master
    elif DEFAULT_ETF_MASTER_PATH and os.path.exists(DEFAULT_ETF_MASTER_PATH):
        logging.info(f"Loading ETF Master Universe from script config path: {DEFAULT_ETF_MASTER_PATH}")
        etf_master_universe = extract_tickers_from_csv(DEFAULT_ETF_MASTER_PATH)
        resolved_etf_file = DEFAULT_ETF_MASTER_PATH
        
    if not etf_master_universe:
        logging.error("Execution Constraint Failure: System could not resolve any valid ETF tickers to scan via CLI or Master Path CSV.")
        sys.exit(1)

    aggregated_seeds = []
    resolved_seed_file = ""
    
    if execution_arguments.seed_codes:
        logging.info("Using Seed Codes passed via CLI parameter.")
        cli_entries = [code.strip() for code in execution_arguments.seed_codes.split(',') if code.strip()]
        aggregated_seeds.extend(cli_entries)
        if execution_arguments.seed_file and os.path.exists(execution_arguments.seed_file):
            resolved_seed_file = execution_arguments.seed_file
        elif DEFAULT_SEED_FILE_PATH and os.path.exists(DEFAULT_SEED_FILE_PATH):
            resolved_seed_file = DEFAULT_SEED_FILE_PATH
    elif execution_arguments.seed_file:
        logging.info(f"Extracting Seed Codes from CLI file path: {execution_arguments.seed_file}")
        aggregated_seeds.extend(extract_tickers_from_csv(execution_arguments.seed_file))
        resolved_seed_file = execution_arguments.seed_file
    elif DEFAULT_SEED_FILE_PATH and os.path.exists(DEFAULT_SEED_FILE_PATH):
        logging.info(f"Extracting Seed Codes from script config path: {DEFAULT_SEED_FILE_PATH}")
        aggregated_seeds.extend(extract_tickers_from_csv(DEFAULT_SEED_FILE_PATH))
        resolved_seed_file = DEFAULT_SEED_FILE_PATH
            
    operational_seeds_deduped = []
    seen_seeds = set()
    for raw_seed in aggregated_seeds:
        processed_seed = clean_ticker(raw_seed)
        if processed_seed and processed_seed not in seen_seeds:
            seen_seeds.add(processed_seed)
            operational_seeds_deduped.append(processed_seed)
            
    if not operational_seeds_deduped:
        logging.error("Execution Constraint Failure: Seed validation failed. No valid stock targets resolved.")
        sys.exit(1)
        
    execute_coverage_mapping(
        seed_stocks=operational_seeds_deduped,
        etf_universe=etf_master_universe,
        min_weight_pct=execution_arguments.min_weight,
        output_path=execution_arguments.output,
        seed_file_path=resolved_seed_file
    )