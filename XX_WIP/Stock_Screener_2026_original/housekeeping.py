#!/usr/bin/env python
"""
Housekeeping script to clean and maintain the stock universe.
Reads StockCodeMaster CSVs, validates exchanges and types, and saves a clean baseline.
"""

import os
import glob
import pandas as pd
from pathlib import Path

# Valid exchanges and types
VALID_EXCHANGES = ['NYSE', 'NASDAQ', 'NSE', 'ARCA']
VALID_TYPES = ['Common Stock', 'ADR', 'ETF', 'American Depositary Shares']

def clean_universe():
    """Clean and validate the stock universe from StockCodeMaster."""
    scm_folder = r"d:\Tools\StockCodeMaster\USA"
    output_file = r"d:\Stock_Screener_2026\clean_universe.csv"
    
    all_symbols = []
    
    # Read all sector CSV files
    for csv_file in glob.glob(os.path.join(scm_folder, "*.csv")):
        try:
            df = pd.read_csv(csv_file, dtype=str)
            print(f"Reading {os.path.basename(csv_file)}: {len(df)} rows")
            
            # Normalize column names
            df.columns = df.columns.str.strip()
            
            # Identify symbol column
            symbol_col = None
            for col in ['Ticker', 'Symbol', 'symbol']:
                if col in df.columns:
                    symbol_col = col
                    break
            
            if not symbol_col:
                print(f"  Skipped: no Symbol column found")
                continue
            
            # Extract relevant columns
            if 'Listing Exchange' in df.columns:
                df_clean = df[[symbol_col, 'Listing Exchange']].copy()
                df_clean.columns = ['Symbol', 'Exchange']
            else:
                df_clean = df[[symbol_col]].copy()
                df_clean.columns = ['Symbol']
                df_clean['Exchange'] = 'NASDAQ'  # default
            
            # Filter by exchange (normalize codes)
            def normalize_exch(code):
                if pd.isna(code):
                    return None
                code = str(code).strip().upper()
                # Map common codes to exchange names
                mapping = {'Q': 'NASDAQ', 'N': 'NYSE', 'A': 'ARCA', 'Z': 'NASDAQ'}
                return mapping.get(code, code)
            
            df_clean['Exchange'] = df_clean['Exchange'].apply(normalize_exch)
            df_clean = df_clean[df_clean['Exchange'].isin(VALID_EXCHANGES)].copy()
            
            # Remove duplicates
            df_clean = df_clean.drop_duplicates(subset=['Symbol'])
            
            all_symbols.append(df_clean)
            print(f"  Kept {len(df_clean)} symbols after exchange filter")
            
        except Exception as e:
            print(f"  Error reading {csv_file}: {e}")
            continue
    
    # Combine all
    if not all_symbols:
        print("No symbols found!")
        return
    
    combined = pd.concat(all_symbols, ignore_index=True).drop_duplicates(subset=['Symbol'])
    combined = combined.sort_values('Symbol').reset_index(drop=True)
    
    # Save
    combined.to_csv(output_file, index=False)
    print(f"\nWrote {len(combined)} clean symbols to {output_file}")
    return combined

if __name__ == "__main__":
    clean_universe()
