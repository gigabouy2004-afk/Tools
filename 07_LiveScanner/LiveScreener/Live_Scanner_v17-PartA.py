#!/usr/bin/env python3
"""
Momentum Engine V17 - Complete Integrated Live Scanner (Part 1, 3, & 4 Combined + CSV Input Support)
Author: Architecture & Engineering
Description: Executes an independent, zero-persistent-footprint momentum review
using explicit ticker codes, runtime universe discovery, or a fully qualified CSV input file.
"""

import sys
import os
import argparse
import tempfile
import atexit
import shutil
import pandas as pd
import yfinance as yf
from datetime import datetime, timezone, timedelta
import urllib.request
from io import StringIO

# ==========================================
# 1. TEMPORARY CACHE & FOOTPRINT ISOLATION
# ==========================================
TEMP_CACHE_DIR = tempfile.mkdtemp(prefix="momentum_v17_cache_")
os.environ["YFINANCE_CACHE_DIR"] = TEMP_CACHE_DIR

def cleanup_transient_footprint():
    """Ensure all transient temp caches are wiped out cleanly on exit."""
    if os.path.exists(TEMP_CACHE_DIR):
        try:
            shutil.rmtree(TEMP_CACHE_DIR, ignore_errors=True)
        except Exception:
            pass

atexit.register(cleanup_transient_footprint)

# ==========================================
# 2. CLI ARGUMENT PARSING & MUTUAL EXCLUSIVITY
# ==========================================
def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Momentum Engine V17 - Complete Live Scanner with CSV Input Support"
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "-c", "--codes",
        nargs="+",
        help="Space-separated or comma-separated list of stock tickers (e.g., AAPL MSFT)"
    )
    group.add_argument(
        "-u", "--universe",
        choices=["nasdaq", "nyse", "all"],
        help="Dynamic runtime universe discovery scope"
    )
    group.add_argument(
        "--input-file",
        type=str,
        help="Fully qualified path to a CSV file containing stock codes in the first column."
    )
    
    parser.add_argument(
        "-o", "--output",
        default="Momentum_Review.xlsx",
        help="Path for the final output audit workbook"
    )
    parser.add_argument(
        "--live-candle-mode",
        default="completed",
        choices=["completed"],
        help="Restricts execution strictly to completed daily/intraday sessions (D-1 anchoring)"
    )

    args = parser.parse_args()
    
    resolved_codes = []
    
    if args.codes:
        for item in args.codes:
            for sub in item.replace(",", " ").split():
                clean_sub = sub.strip().upper()
                if clean_sub:
                    resolved_codes.append(clean_sub)
                    
    elif args.input_file:
        if not os.path.exists(args.input_file):
            print(f"[!] Critical Error: Input CSV file '{args.input_file}' not found.")
            sys.exit(1)
        try:
            with open(args.input_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.strip().split('\n')
            if lines:
                first_line = lines[0].strip().lower()
                has_header = any(h in first_line for h in ['symbol', 'ticker', 'code', 'stock'])
                
                if has_header:
                    df_csv = pd.read_csv(args.input_file)
                else:
                    df_csv = pd.read_csv(args.input_file, header=None)
                
                raw_tickers = df_csv.iloc[:, 0].dropna().astype(str).str.strip().str.upper().tolist()
                resolved_codes = [t for t in raw_tickers if t and t not in ['SYMBOL', 'TICKER', 'CODE', 'STOCK']]
        except Exception as e:
            print(f"[!] Critical Error reading input CSV file: {e}")
            sys.exit(1)
            
    return args, sorted(list(set(resolved_codes)))

# ==========================================
# 3. UNIVERSE DISCOVERY ADAPTER (R2)
# ==========================================
def discover_universe(scope):
    print(f"[*] Discovering runtime equity universe for scope: [{scope.upper()}]...")
    symbols = set()
    try:
        if scope in ["nasdaq", "all"]:
            nasdaq_url = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
            req = urllib.request.Request(nasdaq_url)
            with urllib.request.urlopen(req) as response:
                nasdaq_data = response.read().decode('utf-8')
            df_nasdaq = pd.read_csv(StringIO(nasdaq_data), sep="|")
            df_nasdaq = df_nasdaq[df_nasdaq['Symbol'].notna() & (~df_nasdaq['Symbol'].str.contains("File Creation Time", na=False))]
            if 'Test Issue' in df_nasdaq.columns:
                df_nasdaq = df_nasdaq[df_nasdaq['Test Issue'] == 'N']
            if 'ETF' in df_nasdaq.columns:
                df_nasdaq = df_nasdaq[df_nasdaq['ETF'] == 'N']
            for sym in df_nasdaq['Symbol'].dropna():
                symbols.add(sym.strip().upper())
                
        if scope in ["nyse", "all"]:
            other_url = "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"
            req = urllib.request.Request(other_url)
            with urllib.request.urlopen(req) as response:
                other_data = response.read().decode('utf-8')
            df_other = pd.read_csv(StringIO(other_data), sep="|")
            df_other = df_other[df_other['CQS Symbol'].notna() & (~df_other['CQS Symbol'].str.contains("File Creation Time", na=False))]
            if 'Exchange' in df_other.columns:
                df_nyse = df_other[df_other['Exchange'] == 'N']
            else:
                df_nyse = df_other
            if 'Test Issue' in df_nyse.columns:
                df_nyse = df_nyse[df_nyse['Test Issue'] == 'N']
            if 'ETF' in df_nyse.columns:
                df_nyse = df_nyse[df_nyse['ETF'] == 'N']
            for sym in df_nyse['CQS Symbol'].dropna():
                symbols.add(sym.strip().upper())
    except Exception as e:
        print(f"[!] Warning: Automated remote universe discovery encountered an issue: {e}")
        symbols = {"AAPL", "MSFT", "NVDA", "WDC", "STX"}

    resolved = sorted(list(symbols))
    print(f"[+] Discovered and filtered {len(resolved)} valid equity symbols.")
    return resolved

# ==========================================
# 4. BULK MARKET DATA & ENGINE EXECUTION (R3)
# ==========================================
def run_momentum_engine(symbols, output_path):
    print(f"[*] Initializing ephemeral data ingestion for {len(symbols)} symbols...")
    
    end_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    start_date = (datetime.now(timezone.utc) - timedelta(days=140)).strftime('%Y-%m-%d')
    
    try:
        raw_data = yf.download(symbols, start=start_date, end=end_date, progress=False, group_by='ticker', threads=True)
    except Exception as e:
        print(f"[!] Critical Error during bulk market data retrieval: {e}")
        sys.exit(1)

    review_records = []
    technical_records = []
    summary_records = []

    timestamp_utc = datetime.now(timezone.utc).isoformat()

    for symbol in symbols:
        try:
            if len(symbols) == 1:
                df = raw_data.copy()
            else:
                if symbol in raw_data.columns.levels[0]:
                    df = raw_data[symbol].copy()
                else:
                    review_records.append({"Symbol": symbol, "Status": "Failed", "Message": "Symbol not found in downloaded data"})
                    continue
            
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(-1)
                
            if 'Close' not in df.columns:
                review_records.append({"Symbol": symbol, "Status": "Failed", "Message": "Missing 'Close' column"})
                continue
                
            df = df.dropna(subset=['Close'])
            if len(df) < 90:
                review_records.append({"Symbol": symbol, "Status": "Rejected", "Message": "Insufficient history (<90 sessions)"})
                continue

            df = df.sort_index()
            end_price = float(df['Close'].iloc[-1])
            start_price_90 = float(df['Close'].iloc[-90])
            rolling_90_return = (end_price - start_price_90) / start_price_90

            technical_records.append({
                "Symbol": symbol,
                "Start_Date": str(df.index[-90].date()),
                "End_Date": str(df.index[-1].date()),
                "Start_Price": start_price_90,
                "End_Price": end_price,
                "90_Day_Rolling_Return": rolling_90_return,
                "Data_Integrity_Flag": "VALID"
            })

            review_records.append({
                "Symbol": symbol,
                "Status": "Evaluated",
                "Message": "Successfully processed via transient engine"
            })

        except Exception as ex:
            review_records.append({
                "Symbol": symbol,
                "Status": "Failed",
                "Message": str(ex)
            })

    summary_records.append({
        "execution_timestamp_utc": timestamp_utc,
        "input_scope": f"{len(symbols)} symbols",
        "cache_allocation_mode": "Transient In-Memory / Isolated Temp Cache",
        "output_path": output_path,
        "phase": "V17_Unified_Complete"
    })

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        pd.DataFrame(summary_records).to_excel(writer, sheet_name='Summary', index=False)
        pd.DataFrame(review_records).to_excel(writer, sheet_name='Review', index=False)
        pd.DataFrame(technical_records).to_excel(writer, sheet_name='Technical Data', index=False)

    print(f"[+] Execution complete. Results securely written to transient output: {output_path}")

# ==========================================
# 5. MAIN ENTRY POINT
# ==========================================
def main():
    args, resolved_codes = parse_arguments()
    
    if args.universe:
        target_symbols = discover_universe(args.universe)
    else:
        target_symbols = resolved_codes
        
    if not target_symbols:
        print("[!] Error: No valid symbols resolved for execution.")
        sys.exit(1)
        
    run_momentum_engine(target_symbols, args.output)

if __name__ == "__main__":
    main()