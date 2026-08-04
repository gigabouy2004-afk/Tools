#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ETF Portfolio Mapping and Analysis Engine V5 - Robust Clean Extraction Layer

Input modes:
1. Direct ETF codes:
   python ETF_Portfolio_Mapping_V5.py -t CHPS,PSI,AIVC,SMH

2. ETF code file:
   python ETF_Portfolio_Mapping_V5.py -f ETF_List.txt

3. Theme/classifier mode:
   python ETF_Portfolio_Mapping_V5.py --theme "Europe,Defence" --classifier-file ETF_Master_Classification.csv

The script generates a pure, completely agnostic extraction layer:
- ETF x Company weighted matrix (Sorted by ETF coverage frequency and aggregate portfolio weight)
- ETF summary (Constituent count, total assets parsed, price tracking)
- Stock summary (Global visibility counts and weight statistics across the universe)
- Raw holdings data dump
"""

import os
import sys
import argparse
import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import yfinance as yf

CURRENCY_SYMBOLS = {
    "USD": "$",
    "KRW": "₩",
    "TWD": "NT$",
    "EUR": "€",
    "JPY": "¥",
    "GBP": "£",
    "INR": "₹",
    "CHF": "CHF ",
    "CAD": "C$",
    "AUD": "A$",
    "HKD": "HK$",
    "CNY": "¥",
}

def get_currency_symbol(currency_code):
    if not currency_code:
        return ""
    return CURRENCY_SYMBOLS.get(str(currency_code).upper(), f"{currency_code} ")

def parse_arguments():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter,
        description="ETF Portfolio Mapping Engine V5 - Generic Data Extraction"
    )
    parser.add_argument("-t", "--tickers", type=str, help="Comma-separated ETF tickers")
    parser.add_argument("-f", "--file", type=str, help="Path to a file containing ETF tickers")
    parser.add_argument("--theme", type=str, help="Comma-separated theme terms")
    parser.add_argument("--classifier-file", type=str, default ="D:\\Tools\\StockCodeMaster\\03_ETF\\01-07-US_ETF_Classification_Mapping.csv", help="CSV file containing ETF classification data")
    parser.add_argument("-o", "--output-dir", type=str, default="D:/TMP/4-8-2026", help="Output directory")
    
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)
    return parser.parse_args()

def extract_tickers_from_file(file_path):
    if not os.path.exists(file_path):
        print(f"\n[ERROR] Ticker source file not found at: '{file_path}'")
        print("Please check your file path string or provide an alternative workspace directory.")
        raise FileNotFoundError(f"Input file does not exist: {file_path}")
    print(f"[INFO] Reading ETF ticker source file: {file_path}")
    extracted_tickers = []
    with open(file_path, "r", encoding="utf-8-sig") as f:
        for line in f:
            line_content = line.strip()
            if not line_content:
                continue
            parts = [p.strip().upper() for p in line_content.split(",") if p.strip()]
            extracted_tickers.extend(parts)
    print(f"[SUCCESS] Extracted {len(extracted_tickers)} ETF rows from file.")
    return extracted_tickers

def extract_tickers_from_theme(classifier_file, theme_string):
    if not classifier_file:
        print("\n[ERROR] Theme execution missing structural path registry.")
        print("Command execution requires `--classifier-file` argument when defining a target `--theme`.")
        raise ValueError("--classifier-file is required when using --theme mode")
    if not os.path.exists(classifier_file):
        print(f"\n[ERROR] Theme classifier reference file not found at: '{classifier_file}'")
        print("Verify your local registry directory coordinates before repeating theme lookups.")
        raise FileNotFoundError(f"Classifier metadata registry does not exist: {classifier_file}")
    
    print(f"[INFO] Scanning classifier mapping registry: {classifier_file} for theme keys: '{theme_string}'")
    df = pd.read_csv(classifier_file, encoding="utf-8-sig")
    if "ETF_Code" not in df.columns:
        raise ValueError("Classifier file missing mandatory column header: 'ETF_Code'")
        
    searchable_columns = [col for col in df.columns if col.lower() not in {"etf_code", "include"}]
    if "Include" in df.columns:
        df = df[df["Include"].astype(str).str.upper().str.strip().isin(["Y", "YES", "TRUE", "1"])]
        
    df["_SEARCH_TEXT"] = df[searchable_columns].fillna("").astype(str).agg(" ".join, axis=1).str.lower()
    theme_terms = [term.strip().lower() for term in theme_string.split(",") if term.strip()]
    
    filtered = df.copy()
    for term in theme_terms:
        filtered = filtered[filtered["_SEARCH_TEXT"].str.contains(re.escape(term), na=False)]
        
    selected = filtered["ETF_Code"].astype(str).str.upper().str.strip().replace("", pd.NA).dropna().drop_duplicates().tolist()
    if not selected:
        print(f"\n[WARNING] Theme scan completed successfully but returned 0 results for input keys: '{theme_string}'.")
        print("Check if your CSV classification strings contain alternate naming matches.")
    else:
        print(f"[SUCCESS] Theme matching filter selected {len(selected)} operational ETFs: {selected}")
    return selected, filtered.drop(columns=["_SEARCH_TEXT"], errors="ignore")

def format_market_cap(value, currency_sym):
    if value is None or pd.isna(value) or value == "N/A":
        return "N/A"
    try:
        val = float(value)
        if val >= 1e12: return f"{currency_sym}{val / 1e12:.2f}T"
        if val >= 1e9: return f"{currency_sym}{val / 1e9:.2f}B"
        if val >= 1e6: return f"{currency_sym}{val / 1e6:.2f}M"
        return f"{currency_sym}{val:,.0f}"
    except Exception:
        return "N/A"

def fetch_company_metadata(ticker):
    try:
        t = yf.Ticker(ticker)
        info = t.info
        market_cap = info.get("marketCap", "N/A")
        price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose") or "N/A"
        currency_code = info.get("currency", "")
        country = info.get("country", "Unknown")
        exchange = info.get("exchange", "Unknown")
        location = f"{country} ({exchange})" if country != "Unknown" else exchange
        symbol = get_currency_symbol(currency_code)
        formatted_market_cap = format_market_cap(market_cap, symbol)
        formatted_price = f"{symbol}{float(price):.2f}" if price != "N/A" else "N/A"
        return ticker, formatted_market_cap, formatted_price, location
    except Exception:
        return ticker, "N/A", "N/A", "Unknown"

def fetch_etf_market_and_holdings(etf_ticker):
    cleaned_ticker = etf_ticker.strip().upper()
    if cleaned_ticker.startswith("XNSE:"):
        cleaned_ticker = cleaned_ticker.replace("XNSE:", "") + ".NS"
    try:
        ticker_obj = yf.Ticker(cleaned_ticker)
        info = ticker_obj.info
        current_price = info.get("currentPrice") or info.get("navPrice") or info.get("regularMarketPrice") or info.get("previousClose") or "N/A"
        if isinstance(current_price, (int, float)):
            current_price = round(current_price, 2)
        etf_currency = info.get("currency", "")
        symbol = get_currency_symbol(etf_currency)
        formatted_etf_price = f"{symbol}{float(current_price):.4f}" if current_price != "N/A" else "Error"
        
        holdings_dict = {}
        
        # Discovery Method A: Standard fund_data endpoint sweep
        if hasattr(ticker_obj, "funds_data") and ticker_obj.funds_data is not None:
            for source_attr in ["top_holdings", "equity_holdings"]:
                if hasattr(ticker_obj.funds_data, source_attr):
                    holdings_df = getattr(ticker_obj.funds_data, source_attr)
                    if holdings_df is not None and not holdings_df.empty:
                        for comp_ticker, row in holdings_df.iterrows():
                            comp_name = str(row.get("Name", "")).strip()
                            weight = row.get("Holding Percent", 0)
                            if weight > 1.0: weight = weight / 100.0
                            if comp_ticker and str(comp_ticker).lower() != "nan" and str(comp_ticker).strip() != "":
                                t_key = str(comp_ticker).strip().upper()
                                if t_key not in holdings_dict or weight > holdings_dict[t_key]["Weight"]:
                                    holdings_dict[t_key] = {
                                        "Company Ticker": t_key,
                                        "Company Name": comp_name if comp_name else t_key,
                                        "Weight": float(weight),
                                    }

        # Discovery Method B: Comprehensive fallback method execution
        if not holdings_dict and hasattr(ticker_obj, "get_holdings"):
            try:
                fallback_df = ticker_obj.get_holdings()
                if fallback_df is not None and not fallback_df.empty:
                    tick_col = next((c for c in fallback_df.columns if "symbol" in c.lower() or "ticker" in c.lower()), None)
                    name_col = next((c for c in fallback_df.columns if "name" in c.lower() or "company" in c.lower()), None)
                    pct_col = next((c for c in fallback_df.columns if "percent" in c.lower() or "weight" in c.lower() or "holding" in c.lower()), None)
                    
                    if tick_col:
                        for _, row in fallback_df.iterrows():
                            c_tick = str(row[tick_col]).strip().upper()
                            if c_tick and c_tick != "NAN" and c_tick != "":
                                c_name = str(row[name_col]).strip() if name_col else c_tick
                                c_weight = float(row[pct_col]) if pct_col else 0.0
                                if c_weight > 1.0: c_weight = c_weight / 100.0
                                if c_tick not in holdings_dict:
                                    holdings_dict[c_tick] = {"Company Ticker": c_tick, "Company Name": c_name, "Weight": c_weight}
            except Exception:
                pass

        # Discovery Method C: Clean raw property dictionary parsing
        if not holdings_dict and hasattr(ticker_obj, "holdings") and ticker_obj.holdings is not None:
            try:
                raw_dict_holdings = ticker_obj.holdings
                if isinstance(raw_dict_holdings, list):
                    for h_item in raw_dict_holdings:
                        if isinstance(h_item, dict):
                            c_tick = str(h_item.get("symbol", h_item.get("ticker", ""))).strip().upper()
                            if c_tick and c_tick != "NAN" and c_tick != "":
                                c_name = str(h_item.get("name", h_item.get("holdingName", c_tick))).strip()
                                c_weight = float(h_item.get("holdingPercent", h_item.get("weight", 0.0)))
                                if c_weight > 1.0: c_weight = c_weight / 100.0
                                if c_tick not in holdings_dict:
                                    holdings_dict[c_tick] = {"Company Ticker": c_tick, "Company Name": c_name, "Weight": c_weight}
            except Exception:
                pass
                                    
        holdings_list = list(holdings_dict.values())
        print(f"  ├── [PARSED] ETF: {etf_ticker} | Harvested Constituents: {len(holdings_list)}")
        return formatted_etf_price, holdings_list, None
    except Exception as e:
        print(f"  └── [WARNING] Data API extraction failed for target '{etf_ticker}': {e}")
        return "Error", [], str(e)

def safe_theme_name(theme_string):
    name = theme_string.strip().replace(",", "_").replace(" ", "").replace("&", "And").replace("/", "_")
    return re.sub(r"[^A-Za-z0-9_\-]", "", name) or "Theme"

def build_output_filename(args):
    date_tag = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
    if args.theme:
        return f"{safe_theme_name(args.theme)}_Portfolio-{date_tag}.xlsx"
    return f"ETFCode_PortfolioMapping-{date_tag}.xlsx"

def print_no_etf_message():
    print("\n" + "=" * 80 + "\n ❌ CRITICAL CONFIGURATION FAULT: ETF UNIVERSE BLANK\n" + "=" * 80)
    print("\nNo tracking ETF data sources or matching inputs were supplied.")
    print("Please use one of the following clear command execution paths:")
    print("  1. Direct Ticker Entry  : -t SMH,SOXX,QQQ")
    print("  2. Local File Read Path : -f ETF_List.txt")
    print("  3. Thematic Filter Mode : --theme \"Europe,Chips\" --classifier-file ETF_Master_Classification.csv\n")

def is_valid_ticker_symbol(ticker_str):
    """
    Prevents Yahoo benchmark metrics (e.g. 'PRICE/BOOK', 'MEDIAN MARKET CAP') 
    from hitting the background threading execution pool.
    """
    if not ticker_str or pd.isna(ticker_str):
        return False
    t_clean = str(ticker_str).strip().upper()
    if any(metric in t_clean for metric in ["MARKET CAP", "GROWTH", "PRICE/", "VALUATION", "YIELD", "TURNOVER"]):
        return False
    # Drop strings that contain more than 2 blank spaces (identifies pure word titles)
    if len(t_clean.split(" ")) > 2:
        return False
    return True

def main():
    args = parse_arguments()
    combined_tickers = []
    theme_selection_df = None

    if args.tickers:
        combined_tickers.extend([t.strip().upper() for t in args.tickers.replace("\ufeff", "").split(",") if t.strip()])
    if args.file:
        try: combined_tickers.extend(extract_tickers_from_file(args.file))
        except Exception as e: print(f"[CRITICAL ERR] Input configuration file path failed to read: {e}", file=sys.stderr); sys.exit(1)
    if args.theme:
        try:
            theme_list, theme_selection_df = extract_tickers_from_theme(args.classifier_file, args.theme)
            combined_tickers.extend(theme_list)
        except Exception as e: print(f"[CRITICAL ERR] Thematic scanning pipeline error: {e}", file=sys.stderr); sys.exit(1)

    unique_etfs = sorted(set(combined_tickers))
    if not unique_etfs:
        print_no_etf_message()
        sys.exit(0)

    print("\n================================================================================")
    print(f"📡 INITIALIZING WORKLOAD: HARVESTING PORTFOLIOS FOR {len(unique_etfs)} TARGET ETFS")
    print("================================================================================")
    
    master_holdings_records = []
    etf_prices_summary = {}
    failed_etfs = {}

    for etf in unique_etfs:
        price, holdings, err_msg = fetch_etf_market_and_holdings(etf)
        if err_msg or price == "Error":
            failed_etfs[etf] = err_msg if err_msg else "Price Lookup Failed"
            etf_prices_summary[etf] = "Error"
            continue
        etf_prices_summary[etf] = price

        for holding in holdings:
            master_holdings_records.append({
                "ETF_Code": etf,
                "Company Ticker": holding["Company Ticker"],
                "Company Name": holding["Company Name"],
                "Weight": holding["Weight"],
            })

    if not master_holdings_records:
        print("\n[CRITICAL FAILURE] Pipeline halted: No constituent stock rows could be harvested from the specified universe.")
        if failed_etfs:
            print(f"Current Exception Manifest: {failed_etfs}")
        sys.exit(1)

    raw_df = pd.DataFrame(master_holdings_records)
    raw_df["Company Ticker"] = raw_df["Company Ticker"].astype(str).str.upper().str.strip()
    raw_df["Company Name"] = raw_df["Company Name"].fillna(raw_df["Company Ticker"]).astype(str).str.strip()
    
    # Filter the tickers to isolate legitimate corporate tickers
    unique_company_tickers = sorted([t for t in raw_df["Company Ticker"].unique().tolist() if t and t != "NAN" and is_valid_ticker_symbol(t)])

    print(f"\n🚀 Parallel background threading online. Pulling fundamental layers for {len(unique_company_tickers)} stocks...")
    company_metadata = {}
    with ThreadPoolExecutor(max_workers=15) as executor:
        future_to_ticker = {executor.submit(fetch_company_metadata, ticker): ticker for ticker in unique_company_tickers}
        for i, future in enumerate(as_completed(future_to_ticker), 1):
            ticker, market_cap, price, location = future.result()
            company_metadata[ticker] = {"Market Cap": market_cap, "LTP": price, "Location": location}
            if i % 10 == 0 or i == len(unique_company_tickers):
                print(f"  ├── Progress: Aligned context metadata for {i}/{len(unique_company_tickers)} assets.")

    raw_df["Listed Exchange"] = raw_df["Company Ticker"].map(lambda t: company_metadata.get(t, {}).get("Location", "Unknown"))
    raw_df["Company Market Cap"] = raw_df["Company Ticker"].map(lambda t: company_metadata.get(t, {}).get("Market Cap", "N/A"))
    raw_df["Company LTP"] = raw_df["Company Ticker"].map(lambda t: company_metadata.get(t, {}).get("LTP", "N/A"))

    print("\n⚡ Engineering and pivoting baseline allocation tracking cross-tabulation matrix...")
    matrix_df = raw_df.pivot_table(
        index=["Company Name", "Company Ticker", "Listed Exchange", "Company Market Cap", "Company LTP"],
        columns="ETF_Code",
        values="Weight",
        aggfunc="first",
        fill_value=0.0,
    )
    matrix_df = matrix_df.reindex(columns=unique_etfs, fill_value=0.0)
    matrix_df["ETF_Count"] = (matrix_df[unique_etfs] > 0).sum(axis=1)
    matrix_df["Total_Weight_Across_ETFs"] = round( matrix_df[unique_etfs].sum(axis=1) * 100,2)
    matrix_df = matrix_df.sort_values(by=["ETF_Count", "Total_Weight_Across_ETFs"], ascending=[False, False])
    
    final_matrix_df = matrix_df.reset_index()
    for etf in unique_etfs:
        final_matrix_df[etf] = final_matrix_df[etf].apply(lambda x: f"{x * 100:.2f}%" if x > 0 else "")

    etf_summary_df = raw_df.groupby("ETF_Code").agg(
        Holding_Count=("Company Ticker", "nunique"),
        Total_Holding_Weight=("Weight", "sum"),
        Avg_Holding_Weight=("Weight", "mean"),
        Max_Holding_Weight=("Weight", "max"),
    ).reset_index()
    etf_summary_df["Total_Holding_Weight"] *= 100
    etf_summary_df["Avg_Holding_Weight"] *= 100
    etf_summary_df["Max_Holding_Weight"] *= 100
    etf_summary_df["ETF_Price"] = etf_summary_df["ETF_Code"].map(etf_prices_summary)

    stock_summary_df = raw_df.groupby(["Company Ticker", "Company Name"]).agg(
        ETF_Count=("ETF_Code", "nunique"),
        Total_Weight_Across_ETFs=("Weight", "sum"),
        Avg_Weight_When_Present=("Weight", "mean"),
        Max_Weight_In_One_ETF=("Weight", "max"),
    ).reset_index()
    stock_summary_df["Total_Weight_Across_ETFs"] *= 100
    stock_summary_df["Avg_Weight_When_Present"] *= 100
    stock_summary_df["Max_Weight_In_One_ETF"] *= 100
    stock_summary_df = stock_summary_df.sort_values(by=["ETF_Count", "Total_Weight_Across_ETFs"], ascending=[False, False])

    output_filename = build_output_filename(args)
    output_path = os.path.abspath(os.path.join(args.output_dir, output_filename))
    os.makedirs(args.output_dir, exist_ok=True)

    try:
        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            price_row_df = pd.DataFrame(
                [["", "", "", "", ""] + [str(etf_prices_summary.get(etf, "N/A")) for etf in unique_etfs]],
                columns=["Stock Ticker", "Company Name", "Exchange", "Market Cap", "Price"] + unique_etfs,
            )
            matrix_export_df = final_matrix_df.rename(columns={
                "Company Ticker": "Stock Ticker",
                "Listed Exchange": "Exchange",
                "Company Market Cap": "Market Cap",
                "Company LTP": "Price",
            })
            combined_matrix_export = pd.concat([price_row_df, matrix_export_df], ignore_index=True)
            combined_matrix_export.to_excel(writer, sheet_name="Matrix", index=False)
            etf_summary_df.to_excel(writer, sheet_name="ETF Summary", index=False)
            stock_summary_df.to_excel(writer, sheet_name="Stock Summary", index=False)
            raw_df.to_excel(writer, sheet_name="Raw Holdings", index=False)
            if theme_selection_df is not None:
                theme_selection_df.to_excel(writer, sheet_name="Theme Selection", index=False)
            if failed_etfs:
                pd.DataFrame([{"ETF_Code": k, "Error": v} for k, v in failed_etfs.items()]).to_excel(writer, sheet_name="Failed ETFs", index=False)
        
        print("\n================================================================================")
        print("💾 ARTIFACT EXPORT MATRIX COMPLETED SUCCESSFULLY")
        print("================================================================================")
        print(f"  📁 File Target Path : {output_path}")
        print(f"  📊 Unique ETFs      : {len(unique_etfs)} parsed ({len(failed_etfs)} errors noted)")
        print(f"  📊 List of Unique ETFs : {list(unique_etfs)} ")
        print(f"  🏢 Unique Companies : {len(unique_company_tickers)} entities cross-mapped safely.")
        print("================================================================================")
        
    except Exception as e:
        print(f"\n[FATAL ERROR] System I/O block when compiling spreadsheet file: {e}", file=sys.stderr); sys.exit(1)

if __name__ == "__main__":
    main()