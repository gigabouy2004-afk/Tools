#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ETF Portfolio Mapping and Analysis Engine
Generates an M x N matrix showing Company allocations across multiple ETFs.
Includes real-time Market Cap, Last Traded Price (LTP), Country of Origin, 
and local currency formatting for all underlying companies.
"""

import os
import sys
import argparse
import csv
from datetime import datetime
import pandas as pd
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed

# Standard currency symbol mapping for global markets
CURRENCY_SYMBOLS = {
    'USD': '$',    # US Dollar
    'KRW': '₩',    # South Korean Won
    'TWD': 'NT$',  # New Taiwan Dollar
    'EUR': '€',    # Euro
    'JPY': '¥',    # Japanese Yen
    'GBP': '£',    # British Pound
    'INR': '₹',    # Indian Rupee
    'CHF': 'CHF ', # Swiss Franc
    'CAD': 'C$',   # Canadian Dollar
    'AUD': 'A$',   # Australian Dollar
    'HKD': 'HK$',  # Hong Kong Dollar
    'CNY': '¥'     # Chinese Yuan
}

def get_currency_symbol(currency_code):
    """Returns the correct local currency symbol based on the ISO code."""
    if not currency_code:
        return ""
    currency_code = currency_code.upper()
    return CURRENCY_SYMBOLS.get(currency_code, f"{currency_code} ")

def parse_arguments():
    """Sets up CLI arguments for PowerShell/CMD execution."""
    parser = argparse.ArgumentParser(
        description="Process ETF tickers and generate a portfolio allocation matrix with Market Cap, Location, and Local Currency LTP."
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

def format_market_cap(value, currency_sym):
    """Converts raw market cap numeric values into readable string formats with local currency."""
    if value is None or pd.isna(value) or value == "N/A":
        return "N/A"
    try:
        val = float(value)
        if val >= 1e12:
            return f"{currency_sym}{val/1e12:.2f}T"
        elif val >= 1e9:
            return f"{currency_sym}{val/1e9:.2f}B"
        elif val >= 1e6:
            return f"{currency_sym}{val/1e6:.2f}M"
        else:
            return f"{currency_sym}{val:,.0f}"
    except:
        return "N/A"

def fetch_company_metadata(ticker):
    """Fetches Market Cap, Last Traded Price, Country, and Currency for an individual company."""
    try:
        t = yf.Ticker(ticker)
        info = t.info
        
        mc = info.get("marketCap", "N/A")
        price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose") or "N/A"
        currency_code = info.get("currency", "")
        country = info.get("country", "Unknown")
        exchange = info.get("exchange", "Unknown")
        
        # Combine country and exchange for a clean location column
        location = f"{country} ({exchange})" if country != "Unknown" else exchange
        
        # Resolve currency symbol
        sym = get_currency_symbol(currency_code)
        
        # Format values cleanly
        formatted_mc = format_market_cap(mc, sym)
        formatted_price = f"{sym}{float(price):.2f}" if price != "N/A" else "N/A"
        
        return ticker, formatted_mc, formatted_price, location
    except:
        return ticker, "N/A", "N/A", "Unknown"

def fetch_etf_market_and_holdings(etf_ticker):
    """Fetches the live price (with currency) and underlying holding data of an ETF."""
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
        current_price = round(current_price, 2) if isinstance(current_price, (int, float)) else current_price
        
        etf_currency = info.get("currency", "")
        sym = get_currency_symbol(etf_currency)
        formatted_etf_price = f"{sym}{float(current_price):.4f}" if current_price != "N/A" else "Error"
        
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
        
        return formatted_etf_price, holdings_list, None
        
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

    # Phase 1: Fetch ETF Data and Holdings
    for etf in unique_etfs:
        print(f"Processing ETF target: {etf}...")
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
    unique_company_tickers = sorted(raw_df['Company Ticker'].unique().tolist())
    
    # Phase 2: Rapidly fetch Company Metadata using Multithreading
    print(f"\n🚀 Fetching Location, Market Cap, and Currency/LTP for {len(unique_company_tickers)} unique companies...")
    company_metadata = {}
    
    with ThreadPoolExecutor(max_workers=15) as executor:
        future_to_ticker = {executor.submit(fetch_company_metadata, ticker): ticker for ticker in unique_company_tickers}
        
        for i, future in enumerate(as_completed(future_to_ticker), 1):
            ticker, mc, price, location = future.result()
            company_metadata[ticker] = {
                'Market Cap': mc, 
                'LTP': price, 
                'Location': location
            }
            if i % 25 == 0 or i == len(unique_company_tickers):
                print(f"  -> Extracted company metadata: {i}/{len(unique_company_tickers)}")

    # Map the new data back to the raw DataFrame
    raw_df['Listed Exchange'] = raw_df['Company Ticker'].map(lambda t: company_metadata[t]['Location'])
    raw_df['Company Market Cap'] = raw_df['Company Ticker'].map(lambda t: company_metadata[t]['Market Cap'])
    raw_df['Company LTP'] = raw_df['Company Ticker'].map(lambda t: company_metadata[t]['LTP'])

    # Phase 3: Matrix Pivot and Consolidation
    print("\nConsolidating raw records into corporate distribution map matrix...")
    matrix_df = raw_df.pivot_table(
        index=['Company Name', 'Company Ticker', 'Listed Exchange', 'Company Market Cap', 'Company LTP'],
        columns='ETF_Code',
        values='Weight',
        aggfunc='first'
    )

    matrix_df = matrix_df.reindex(columns=unique_etfs)
    matrix_df = matrix_df.fillna(0.0)

    # Sort items based on cross-fund overlap concentrations
    matrix_df['Overlap_Volume'] = (matrix_df > 0).sum(axis=1)
    matrix_df = matrix_df.sort_values(by='Overlap_Volume', ascending=False)
    matrix_df = matrix_df.drop(columns=['Overlap_Volume'])

    final_matrix_df = matrix_df.reset_index()
    for etf in unique_etfs:
        final_matrix_df[etf] = final_matrix_df[etf].apply(
            lambda x: f"{x * 100:.2f}%" if x > 0 else ""
        )

    # Output Execution
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"ETF_Portfolio-{timestamp}.csv"

    try:
        with open(output_filename, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            
            # Row 1: 5 empty spacer columns to align with the Location column, then ETF prices
            price_row = ["", "", "", "", ""] + [str(etf_prices_summary.get(etf, "N/A")) for etf in unique_etfs]
            writer.writerow(price_row)
            
            # Row 2: Custom Data Headers for the CSV
            header_row = [
                "Company Name", 
                "Stock Ticker", 
                "Exchange", 
                "Market Cap", 
                "Price"
            ] + unique_etfs
            writer.writerow(header_row)
            
            # Row 3 onwards: Map over the respective company dimensions
            for _, row in final_matrix_df.iterrows():
                data_row = [
                    row['Company Name'], 
                    row['Company Ticker'],
                    row['Listed Exchange'],
                    row['Company Market Cap'],
                    row['Company LTP']
                ]
                for etf in unique_etfs:
                    data_row.append(row[etf])
                writer.writerow(data_row)
                
        print(f"\n📊 Target Matrix exported cleanly to: '{os.path.abspath(output_filename)}'")
    except Exception as e:
        print(f"❌ System failure when saving file: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()