#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ETF Portfolio Mapping and Analysis Engine
Generates an M x N matrix showing Company allocations across multiple ETFs.
Supports CLI inputs and file inputs via PowerShell/CMD.
"""

import os
import sys
import argparse
from datetime import datetime
import pandas as pd
import yfinance as yf

def parse_arguments():
    """Sets up CLI arguments for PowerShell/CMD execution."""
    parser = argparse.ArgumentParser(
        description="Process ETF tickers from command line or text files and generate a portfolio allocation matrix."
    )
    parser.add_argument(
        '-t', '--tickers',
        type=str,
        help="Comma-separated string of ETF names/tickers (e.g., 'MARS,NASA,MEME')"
    )
    parser.add_argument(
        '-f', '--file',
        type=str,
        help="Path to a line-separated file containing ETF tickers (no header, one ticker per line)"
    )
    return parser.parse_args()

def extract_tickers_from_file(file_path):
    """Safely reads tickers from a file, handling UTF-8 BOM encoding issues."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"The input file path specified does not exist: '{file_path}'")
        
    extracted_tickers = []
    try:
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            for line in f:
                line_content = line.strip()
                if not line_content:
                    continue
                parts = [p.strip().upper() for p in line_content.split(',') if p.strip()]
                extracted_tickers.extend(parts)
    except Exception as e:
        raise IOError(f"Failed to parse or read file content cleanly: {str(e)}")
        
    return extracted_tickers

def fetch_etf_market_and_holdings(etf_ticker):
    """
    Fetches the live price and underlying holding data of an ETF using
    the correct yfinance funds_data property structure.
    """
    cleaned_ticker = etf_ticker.strip().upper()
    
    if cleaned_ticker.startswith("XNSE:"):
        cleaned_ticker = cleaned_ticker.replace("XNSE:", "") + ".NS"

    try:
        ticker_obj = yf.Ticker(cleaned_ticker)
        info = ticker_obj.info
        
        current_price = (
            info.get("currentPrice") or 
            info.get("navPrice") or 
            info.get("regularMarketPrice") or 
            info.get("previousClose") or 
            "N/A"
        )
        
        holdings_list = []
        
        if hasattr(ticker_obj, 'funds_data') and ticker_obj.funds_data is not None:
            holdings_df = ticker_obj.funds_data.top_holdings
            
            if holdings_df is not None and not holdings_df.empty:
                for comp_ticker, row in holdings_df.iterrows():
                    comp_name = str(row.get('Name', '')).strip()
                    weight = row.get('Holding Percent', 0)
                    
                    if weight > 1.0:
                        weight = weight / 100.0
                        
                    if comp_ticker and str(comp_ticker).lower() != 'nan':
                        holdings_list.append({
                            'Company Ticker': str(comp_ticker).strip(),
                            'Company Name': comp_name,
                            'Weight': weight
                        })
        
        return current_price, holdings_list, None
        
    except Exception as e:
        return "Error", [], str(e)

def main():
    args = parse_arguments()
    combined_tickers = []

    if args.tickers:
        cleaned_args = args.tickers.replace('\ufeff', '')
        cli_list = [t.strip().upper() for t in cleaned_args.split(',') if t.strip()]
        combined_tickers.extend(cli_list)

    if args.file:
        try:
            file_list = extract_tickers_from_file(args.file)
            combined_tickers.extend(file_list)
        except Exception as e:
            print(f"❌ File Error: {e}", file=sys.stderr)
            sys.exit(1)

    unique_etfs = sorted(list(set(combined_tickers)))
    total_read = len(unique_etfs)

    if not unique_etfs:
        print("❌ Error: No valid ETF codes provided. Use '-t' for inline parameters or '-f' for file paths.", file=sys.stderr)
        sys.exit(1)

    print(f"🚀 Combined & sorted unique tracking set ({total_read} ETFs): {unique_etfs}\n")

    master_holdings_records = []
    etf_prices_summary = {}
    failed_etfs = {}
    passed_count = 0
    failed_count = 0

    for etf in unique_etfs:
        print(f"Processing target: {etf}...")
        price, holdings, err_msg = fetch_etf_market_and_holdings(etf)
        
        if err_msg or price == "Error":
            print(f"  ⚠️ API Extraction Issue on '{etf}': {err_msg if err_msg else 'Price Error'}")
            failed_etfs[etf] = err_msg if err_msg else "Price Lookup Failed"
            etf_prices_summary[etf] = "Error"
            failed_count += 1
            continue
            
        etf_prices_summary[etf] = price
        passed_count += 1
        
        if not holdings:
            print(f"  ⚠️ Warning: No accessible portfolio structure discovered for '{etf}'.")
            
        for holding in holdings:
            master_holdings_records.append({
                'ETF_Code': etf,
                'Company Ticker': holding['Company Ticker'],
                'Company Name': holding['Company Name'],
                'Weight': holding['Weight']
            })

    # Output Execution Metrics Summary Table to Terminal
    print("\n" + "="*40)
    print("        ETF PROCESSING SUMMARY")
    print("="*40)
    print(f"  Total ETFs Read : {total_read}")
    print(f"  Passed Cleanly  : {passed_count}")
    print(f"  Failed / Errors : {failed_count}")
    print("="*40)

    if not master_holdings_records:
        print("\n❌ Execution halted: No portfolio constituents data could be harvested from any target tickers.")
        sys.exit(1)

    raw_df = pd.DataFrame(master_holdings_records)

    print("\nConsolidating raw records into corporate distribution map matrix...")
    matrix_df = raw_df.pivot_table(
        index=['Company Name', 'Company Ticker'],
        columns='ETF_Code',
        values='Weight',
        aggfunc='first'
    )

    matrix_df = matrix_df.reindex(columns=unique_etfs)
    matrix_df = matrix_df.fillna(0.0)

    matrix_df['Overlap_Volume'] = (matrix_df > 0).sum(axis=1)
    matrix_df = matrix_df.sort_values(by='Overlap_Volume', ascending=False)
    matrix_df = matrix_df.drop(columns=['Overlap_Volume'])

    final_matrix_df = matrix_df.reset_index()
    for etf in unique_etfs:
        final_matrix_df[etf] = final_matrix_df[etf].apply(
            lambda x: f"{x * 100:.2f}%" if x > 0 else ""
        )

    # Clean row structure: Set up the direct single header row with live market price metadata appended to column text
    clean_columns = ['Company Name', 'Company Ticker']
    for etf in unique_etfs:
        price_val = etf_prices_summary.get(etf, "N/A")
        # Format column header explicitly as "TICKER (PRICE)"
        clean_columns.append(f"{etf} ({price_val})")
        
    final_matrix_df.columns = clean_columns

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"ETF_Portfolio-{timestamp}.csv"

    try:
        final_matrix_df.to_csv(output_filename, index=False)
        print(f"\n📊 Target Matrix exported cleanly to: '{os.path.abspath(output_filename)}'")
    except Exception as e:
        print(f"❌ System failure when saving file: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()