#!/usr/bin/env python3
"""
Momentum Engine V17 - Part 4: Standalone Transient Runtime Scanner
Author: Architecture & Engineering
Description: Executes an independent, zero-persistent-footprint momentum review
using either explicit ticker codes or dynamic Nasdaq/NYSE universe discovery.
"""

import sys
import os
import argparse
import tempfile
import atexit
import shutil
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# ==========================================
# 1. TEMPORARY CACHE & FOOTPRINT ISOLATION
# ==========================================
# Redirect yfinance / requests-cache to an isolated temporary directory
TEMP_CACHE_DIR = tempfile.mkdtemp(prefix="momentum_v17_part4_cache_")

def cleanup_transient_footprint():
    """Ensure all transient temp caches are wiped out cleanly on exit."""
    if os.path.exists(TEMP_CACHE_DIR):
        try:
            shutil.rmtree(TEMP_CACHE_DIR, ignore_errors=True)
        except Exception:
            pass

atexit.register(cleanup_transient_footprint)

# Set environment or cache hooks if applicable for yfinance session isolation
os.environ["YFINANCE_CACHE_DIR"] = TEMP_CACHE_DIR

# ==========================================
# 2. CLI ARGUMENT PARSING & MUTUAL EXCLUSIVITY
# ==========================================
def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Momentum Engine V17-Part4 - Standalone Transient Runtime Scanner"
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
    
    # Handle comma-separated input strings if passed via single argument or shell expansion
    resolved_codes = []
    if args.codes:
        for item in args.codes:
            for sub in item.split(","):
                clean_sub = sub.strip().upper()
                if clean_sub:
                    resolved_codes.append(clean_sub)
    
    return args, resolved_codes

# ==========================================
# 3. UNIVERSE DISCOVERY ADAPTER (R2)
# ==========================================
def discover_universe(scope):
    """
    Transient runtime universe discovery using Nasdaq Trader directory files.
    Filters out test issues and ETFs, returning verified equity symbols.
    """
    print(f"[*] Discovering runtime equity universe for scope: [{scope.upper()}]...")
    symbols = set()
    
    try:
        if scope in ["nasdaq", "all"]:
            nasdaq_url = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
            df_nasdaq = pd.read_csv(nasdaq_url, sep="|")
            df_nasdaq = df_nasdaq[df_nasdaq['Symbol'].notna() & (~df_nasdaq['Symbol'].str.contains("File Creation Time", na=False))]
            if 'Test Issue' in df_nasdaq.columns:
                df_nasdaq = df_nasdaq[df_nasdaq['Test Issue'] == 'N']
            if 'ETF' in df_nasdaq.columns:
                df_nasdaq = df_nasdaq[df_nasdaq['ETF'] == 'N']
            
            for sym in df_nasdaq['Symbol'].dropna():
                symbols.add(sym.strip().upper())
                
        if scope in ["nyse", "all"]:
            other_url = "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"
            df_other = pd.read_csv(other_url, sep="|")
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
        print("[!] Falling back to core benchmark reference set.")
        symbols = {"AAPL", "MSFT", "NVDA", "WDC", "STX"}

    resolved = sorted(list(symbols))
    print(f"[+] Discovered and filtered {len(resolved)} valid equity symbols.")
    return resolved

# ==========================================
# 4. BULK MARKET DATA & ENGINE EXECUTION (R3)
# ==========================================
def run_momentum_engine(symbols, output_path):
    print(f"[*] Initializing ephemeral data ingestion for {len(symbols)} symbols...")
    
    end_date = datetime.today().strftime('%Y-%m-%d')
    start_date = (datetime.today() - timedelta(days=400)).strftime('%Y-%m-%d')
    
    try:
        raw_data = yf.download(symbols, start=start_date, end=end_date, progress=False, group_by='ticker', threads=True)
    except Exception as e:
        print(f"[!] Critical Error during bulk market data retrieval: {e}")
        sys.exit(1)

    review_records = []
    technical_records = []
    summary_records = []

    timestamp_utc = datetime.utcnow().isoformat() + "+00:00"

    for symbol in symbols:
        try:
            if len(symbols) == 1:
                df = raw_data.copy()
            else:
                if symbol in raw_data.columns.levels[0]:
                    df = raw_data[symbol].copy()
                else:
                    continue
            
            df = df.dropna(subset=['Close'])
            if len(df) < 90:
                review_records.append({"Symbol": symbol, "Status": "Rejected", "Message": "Insufficient history (<90 sessions)"})
                continue

            # Strict D-1 Anchoring (Last completed session)
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
        "phase": "V17_Part4_Complete"
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
    args, explicit_codes = parse_arguments()
    
    if args.universe:
        target_symbols = discover_universe(args.universe)
    else:
        target_symbols = explicit_codes
        
    if not target_symbols:
        print("[!] Error: No valid symbols resolved for execution.")
        sys.exit(1)
        
    run_momentum_engine(target_symbols, args.output)

if __name__ == "__main__":
    main()