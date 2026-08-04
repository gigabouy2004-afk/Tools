#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ETF Portfolio Mapping and Analysis Engine V4

Input modes:
1. Direct ETF codes:
   python ETF_Portfolio_Mapping_V4.py -t CHPS,PSI,AIS,CHPX

2. ETF code file:
   python ETF_Portfolio_Mapping_V4.py -f ETF_List.txt

3. Theme/classifier mode:
   python ETF_Portfolio_Mapping_V4.py --theme "Europe,Defence" --classifier-file ETF_Master_Classification.csv

Expected classifier CSV columns:
ETF_Code, Geography, Theme, SubTheme, Include

The script generates:
- Run summary with ETF universe and combined stock-code message
- ETF x Company weighted matrix
- ETF summary
- Stock summary
- Raw holdings
- Theme-selected ETF list, when theme mode is used
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
        description="""
ETF Portfolio Mapping Engine V4

You must provide ETF universe using one of these methods:

METHOD 1 - Direct ETF Codes
  python ETF_Portfolio_Mapping_V4.py -t CHPS,PSI,AIS,CHPX

METHOD 2 - ETF List File
  python ETF_Portfolio_Mapping_V4.py -f ETF_List.txt

Example ETF_List.txt:
  CHPS
  PSI
  AIS
  CHPX

METHOD 3 - Theme Based Portfolio
  python ETF_Portfolio_Mapping_V4.py --theme "Europe,Defence" --classifier-file ETF_Master_Classification.csv

  python ETF_Portfolio_Mapping_V4.py --theme "Asia Pacific,Semiconductor,AI-Memory" --classifier-file ETF_Master_Classification.csv

Expected classifier CSV columns:
  ETF_Code, Geography, Theme, SubTheme, Include

Output naming:
  Raw ETF/file mode:
    ETF_Portfolio-DDMM.xlsx

  Theme mode:
    Europe_Defence_Portfolio-DDMM.xlsx
"""
    )

    parser.add_argument(
        "-t",
        "--tickers",
        type=str,
        help="Comma-separated ETF tickers, e.g. CHPS,PSI,AIS,CHPX",
    )

    parser.add_argument(
        "-f",
        "--file",
        type=str,
        help="Path to a file containing ETF tickers. Can be line-separated or comma-separated.",
    )

    parser.add_argument(
        "--theme",
        type=str,
        help='Comma-separated theme terms, e.g. "Europe,Defence" or "Asia Pacific,Semiconductor,AI-Memory"',
    )

    parser.add_argument(
        "--classifier-file",
        type=str,
        help="CSV file containing ETF classification data.",
    )

    parser.add_argument(
        "-o",
        "--output-dir",
        type=str,
        default=".",
        help="Output directory. Default is current folder.",
    )

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    return parser.parse_args()


def extract_tickers_from_file(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Input file does not exist: {file_path}")

    extracted_tickers = []

    with open(file_path, "r", encoding="utf-8-sig") as f:
        for line in f:
            line_content = line.strip()
            if not line_content:
                continue

            parts = [p.strip().upper() for p in line_content.split(",") if p.strip()]
            extracted_tickers.extend(parts)

    return extracted_tickers


def normalize_text(value):
    if pd.isna(value):
        return ""
    return str(value).strip().lower()


def extract_tickers_from_theme(classifier_file, theme_string):
    if not classifier_file:
        raise ValueError("--classifier-file is required when using --theme")

    if not os.path.exists(classifier_file):
        raise FileNotFoundError(f"Classifier file does not exist: {classifier_file}")

    df = pd.read_csv(classifier_file, encoding="utf-8-sig")

    if "ETF_Code" not in df.columns:
        raise ValueError("Classifier file must contain column: ETF_Code")

    searchable_columns = [
        col for col in df.columns
        if col.lower() not in {"etf_code", "include"}
    ]

    if not searchable_columns:
        raise ValueError(
            "Classifier file must contain searchable columns such as Geography, Theme, or SubTheme"
        )

    if "Include" in df.columns:
        df = df[df["Include"].astype(str).str.upper().str.strip().isin(["Y", "YES", "TRUE", "1"])]

    df["_SEARCH_TEXT"] = df[searchable_columns].fillna("").astype(str).agg(" ".join, axis=1).str.lower()

    theme_terms = [term.strip().lower() for term in theme_string.split(",") if term.strip()]

    if not theme_terms:
        raise ValueError("No valid theme terms supplied.")

    filtered = df.copy()

    for term in theme_terms:
        filtered = filtered[filtered["_SEARCH_TEXT"].str.contains(re.escape(term), na=False)]

    selected = (
        filtered["ETF_Code"]
        .astype(str)
        .str.upper()
        .str.strip()
        .replace("", pd.NA)
        .dropna()
        .drop_duplicates()
        .tolist()
    )

    return selected, filtered.drop(columns=["_SEARCH_TEXT"], errors="ignore")


def format_market_cap(value, currency_sym):
    if value is None or pd.isna(value) or value == "N/A":
        return "N/A"

    try:
        val = float(value)

        if val >= 1e12:
            return f"{currency_sym}{val / 1e12:.2f}T"
        if val >= 1e9:
            return f"{currency_sym}{val / 1e9:.2f}B"
        if val >= 1e6:
            return f"{currency_sym}{val / 1e6:.2f}M"

        return f"{currency_sym}{val:,.0f}"

    except Exception:
        return "N/A"


def fetch_company_metadata(ticker):
    try:
        t = yf.Ticker(ticker)
        info = t.info

        market_cap = info.get("marketCap", "N/A")
        price = (
            info.get("currentPrice")
            or info.get("regularMarketPrice")
            or info.get("previousClose")
            or "N/A"
        )

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

        current_price = (
            info.get("currentPrice")
            or info.get("navPrice")
            or info.get("regularMarketPrice")
            or info.get("previousClose")
            or "N/A"
        )

        if isinstance(current_price, (int, float)):
            current_price = round(current_price, 2)

        etf_currency = info.get("currency", "")
        symbol = get_currency_symbol(etf_currency)

        formatted_etf_price = (
            f"{symbol}{float(current_price):.4f}"
            if current_price != "N/A"
            else "Error"
        )

        holdings_list = []

        if hasattr(ticker_obj, "funds_data") and ticker_obj.funds_data is not None:
            holdings_df = ticker_obj.funds_data.top_holdings

            if holdings_df is not None and not holdings_df.empty:
                for comp_ticker, row in holdings_df.iterrows():
                    comp_name = str(row.get("Name", "")).strip()
                    weight = row.get("Holding Percent", 0)

                    if weight > 1.0:
                        weight = weight / 100.0

                    if comp_ticker and str(comp_ticker).lower() != "nan":
                        holdings_list.append(
                            {
                                "Company Ticker": str(comp_ticker).strip().upper(),
                                "Company Name": comp_name,
                                "Weight": float(weight),
                            }
                        )

        return formatted_etf_price, holdings_list, None

    except Exception as e:
        return "Error", [], str(e)


def safe_theme_name(theme_string):
    name = theme_string.strip()
    name = name.replace(",", "_")
    name = name.replace(" ", "")
    name = name.replace("&", "And")
    name = name.replace("/", "_")
    name = re.sub(r"[^A-Za-z0-9_\-]", "", name)
    return name or "Theme"


def build_output_filename(args):
    date_tag = datetime.now().strftime("%d%m")

    if args.theme:
        return f"{safe_theme_name(args.theme)}_Portfolio-{date_tag}.xlsx"

    return f"ETF_Portfolio-{date_tag}.xlsx"


def get_input_source_label(args):
    input_sources = []

    if args.tickers:
        input_sources.append("CLI")

    if args.file:
        input_sources.append("File")

    if args.theme:
        input_sources.append("Theme")

    return " + ".join(input_sources) if input_sources else "Unknown"


def build_run_summary(args, unique_etfs, unique_company_tickers):
    execution_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    etf_code_string = ",".join(unique_etfs)
    stock_code_string = ",".join(unique_company_tickers)
    total_input_etfs = len(unique_etfs)
    total_stock_codes = len(unique_company_tickers)
    stock_vs_etf_summary = f"{total_stock_codes} stock codes / {total_input_etfs} input ETFs"

    output_message = (
        f"ETF Codes ({get_input_source_label(args)}): {etf_code_string} | "
        f"Script: {os.path.basename(__file__)} | "
        f"Execution Date: {execution_date} | "
        f"Total Stock Codes vs Total Input ETF: {stock_vs_etf_summary} | "
        f"All Stock Codes: {stock_code_string}"
    )

    summary_rows = [
        ("Input Source", get_input_source_label(args)),
        ("ETF Codes", etf_code_string),
        ("Script Name", os.path.basename(__file__)),
        ("Execution Date", execution_date),
        ("Total Input ETFs", total_input_etfs),
        ("Total Stock Codes", total_stock_codes),
        ("Total Stock Codes vs Total Input ETF", stock_vs_etf_summary),
        ("All Stock Codes", stock_code_string),
        ("Output Message", output_message),
    ]

    if args.file:
        summary_rows.insert(2, ("Input File", os.path.abspath(args.file)))

    if args.theme:
        summary_rows.insert(2, ("Theme Terms", args.theme))
        if args.classifier_file:
            summary_rows.insert(3, ("Classifier File", os.path.abspath(args.classifier_file)))

    return pd.DataFrame(summary_rows, columns=["Summary Field", "Summary Value"]), output_message


def print_no_etf_message():
    print("\n" + "=" * 80)
    print(" ETF PORTFOLIO MAPPING ENGINE V4")
    print("=" * 80)

    print("\nNo ETF universe was supplied.\n")

    print("Use one of these input methods:\n")

    print("METHOD 1 - Direct ETF Codes")
    print("-" * 40)
    print("python ETF_Portfolio_Mapping_V4.py -t CHPS,PSI,AIS,CHPX")
    print()

    print("METHOD 2 - ETF List File")
    print("-" * 40)
    print("python ETF_Portfolio_Mapping_V4.py -f ETF_List.txt")
    print()

    print("Example ETF_List.txt")
    print("CHPS")
    print("PSI")
    print("AIS")
    print("CHPX")
    print()

    print("METHOD 3 - Theme Based Portfolio")
    print("-" * 40)
    print('python ETF_Portfolio_Mapping_V4.py --theme "Europe,Defence" --classifier-file ETF_Master_Classification.csv')
    print('python ETF_Portfolio_Mapping_V4.py --theme "Asia Pacific,Semiconductor,AI-Memory" --classifier-file ETF_Master_Classification.csv')
    print()

    print("Expected classifier CSV columns")
    print("-" * 40)
    print("ETF_Code, Geography, Theme, SubTheme, Include")
    print()

    print("Expected outputs")
    print("-" * 40)
    print("ETF_Portfolio-DDMM.xlsx")
    print("Europe_Defence_Portfolio-DDMM.xlsx")
    print("AsiaPacific_Semiconductor_AI-Memory_Portfolio-DDMM.xlsx")
    print()

    print("=" * 80)


def main():
    args = parse_arguments()

    combined_tickers = []
    theme_selection_df = None

    if args.tickers:
        cleaned_args = args.tickers.replace("\ufeff", "")
        cli_list = [t.strip().upper() for t in cleaned_args.split(",") if t.strip()]
        combined_tickers.extend(cli_list)

    if args.file:
        try:
            file_list = extract_tickers_from_file(args.file)
            combined_tickers.extend(file_list)
        except Exception as e:
            print(f"\nFile input error: {e}", file=sys.stderr)
            sys.exit(1)

    if args.theme:
        try:
            theme_list, theme_selection_df = extract_tickers_from_theme(
                args.classifier_file,
                args.theme,
            )
            combined_tickers.extend(theme_list)

            print("\nTheme selector activated")
            print("-" * 40)
            print(f"Theme terms      : {args.theme}")
            print(f"Classifier file  : {args.classifier_file}")
            print(f"ETFs selected    : {len(theme_list)}")
            print(f"Selected ETF list: {theme_list}")

        except Exception as e:
            print(f"\nTheme input error: {e}", file=sys.stderr)
            sys.exit(1)

    unique_etfs = sorted(set(combined_tickers))
    total_read = len(unique_etfs)

    if not unique_etfs:
        print_no_etf_message()
        sys.exit(0)

    print(f"\nCombined and sorted ETF tracking set ({total_read} ETFs):")
    print(unique_etfs)
    print()

    master_holdings_records = []
    etf_prices_summary = {}
    failed_etfs = {}
    passed_count = 0
    failed_count = 0

    for etf in unique_etfs:
        print(f"Processing ETF target: {etf}...")

        price, holdings, err_msg = fetch_etf_market_and_holdings(etf)

        if err_msg or price == "Error":
            print(f"  Warning: API extraction issue on {etf}: {err_msg if err_msg else 'Price Error'}")
            failed_etfs[etf] = err_msg if err_msg else "Price Lookup Failed"
            etf_prices_summary[etf] = "Error"
            failed_count += 1
            continue

        etf_prices_summary[etf] = price
        passed_count += 1

        if not holdings:
            print(f"  Warning: No accessible portfolio structure discovered for {etf}.")

        for holding in holdings:
            master_holdings_records.append(
                {
                    "ETF_Code": etf,
                    "Company Ticker": holding["Company Ticker"],
                    "Company Name": holding["Company Name"],
                    "Weight": holding["Weight"],
                }
            )

    print("\n" + "=" * 40)
    print(" ETF PROCESSING SUMMARY")
    print("=" * 40)
    print(f" Total ETFs Read : {total_read}")
    print(f" Passed Cleanly  : {passed_count}")
    print(f" Failed / Errors : {failed_count}")
    print("=" * 40)

    if not master_holdings_records:
        print("\nExecution halted: No portfolio constituents data could be harvested.")
        sys.exit(1)

    raw_df = pd.DataFrame(master_holdings_records)
    raw_df["Company Ticker"] = raw_df["Company Ticker"].astype(str).str.upper().str.strip()

    unique_company_tickers = sorted(
        [
            ticker
            for ticker in raw_df["Company Ticker"].unique().tolist()
            if ticker and ticker != "NAN"
        ]
    )

    print(f"\nFetching metadata for {len(unique_company_tickers)} unique companies...")

    company_metadata = {}

    with ThreadPoolExecutor(max_workers=15) as executor:
        future_to_ticker = {
            executor.submit(fetch_company_metadata, ticker): ticker
            for ticker in unique_company_tickers
        }

        for i, future in enumerate(as_completed(future_to_ticker), 1):
            ticker, market_cap, price, location = future.result()

            company_metadata[ticker] = {
                "Market Cap": market_cap,
                "LTP": price,
                "Location": location,
            }

            if i % 25 == 0 or i == len(unique_company_tickers):
                print(f"  Extracted company metadata: {i}/{len(unique_company_tickers)}")

    raw_df["Listed Exchange"] = raw_df["Company Ticker"].map(
        lambda t: company_metadata.get(t, {}).get("Location", "Unknown")
    )
    raw_df["Company Market Cap"] = raw_df["Company Ticker"].map(
        lambda t: company_metadata.get(t, {}).get("Market Cap", "N/A")
    )
    raw_df["Company LTP"] = raw_df["Company Ticker"].map(
        lambda t: company_metadata.get(t, {}).get("LTP", "N/A")
    )

    print("\nConsolidating raw records into matrix...")

    matrix_df = raw_df.pivot_table(
        index=[
            "Company Name",
            "Company Ticker",
            "Listed Exchange",
            "Company Market Cap",
            "Company LTP",
        ],
        columns="ETF_Code",
        values="Weight",
        aggfunc="first",
        fill_value=0.0,
    )

    matrix_df = matrix_df.reindex(columns=unique_etfs, fill_value=0.0)
    matrix_df["ETF_Count"] = (matrix_df[unique_etfs] > 0).sum(axis=1)
    matrix_df["Total_Weight_Across_ETFs"] = round(matrix_df[unique_etfs].sum(axis=1) * 100, 2)

    matrix_df = matrix_df.sort_values(
        by=["ETF_Count", "Total_Weight_Across_ETFs"],
        ascending=False,
    )

    final_matrix_df = matrix_df.reset_index()

    for etf in unique_etfs:
        final_matrix_df[etf] = final_matrix_df[etf].apply(
            lambda x: f"{x * 100:.2f}%" if x > 0 else ""
        )

    etf_summary_df = (
        raw_df.groupby("ETF_Code")
        .agg(
            Holding_Count=("Company Ticker", "nunique"),
            Total_Holding_Weight=("Weight", "sum"),
            Avg_Holding_Weight=("Weight", "mean"),
            Max_Holding_Weight=("Weight", "max"),
        )
        .reset_index()
    )

    etf_summary_df["Total_Holding_Weight"] *= 100
    etf_summary_df["Avg_Holding_Weight"] *= 100
    etf_summary_df["Max_Holding_Weight"] *= 100
    etf_summary_df["ETF_Price"] = etf_summary_df["ETF_Code"].map(etf_prices_summary)

    stock_summary_df = (
        raw_df.groupby(["Company Ticker", "Company Name"])
        .agg(
            ETF_Count=("ETF_Code", "nunique"),
            Total_Weight_Across_ETFs=("Weight", "sum"),
            Avg_Weight_When_Present=("Weight", "mean"),
            Max_Weight_In_One_ETF=("Weight", "max"),
        )
        .reset_index()
    )

    stock_summary_df["Total_Weight_Across_ETFs"] *= 100
    stock_summary_df["Avg_Weight_When_Present"] *= 100
    stock_summary_df["Max_Weight_In_One_ETF"] *= 100

    stock_summary_df = stock_summary_df.sort_values(
        by=["ETF_Count", "Total_Weight_Across_ETFs"],
        ascending=False,
    )

    run_summary_df, output_message = build_run_summary(
        args,
        unique_etfs,
        unique_company_tickers,
    )

    output_filename = build_output_filename(args)
    output_path = os.path.abspath(os.path.join(args.output_dir, output_filename))

    os.makedirs(args.output_dir, exist_ok=True)

    try:
        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            price_row_df = pd.DataFrame(
                [["", "", "", "", ""] + [str(etf_prices_summary.get(etf, "N/A")) for etf in unique_etfs]],
                columns=[
                    "Stock Ticker",
                    "Company Name",
                    "Exchange",
                    "Market Cap",
                    "Price",
                ] + unique_etfs,
            )

            matrix_export_df = final_matrix_df.rename(
                columns={
                    "Company Ticker": "Stock Ticker",
                    "Listed Exchange": "Exchange",
                    "Company Market Cap": "Market Cap",
                    "Company LTP": "Price",
                }
            )

            combined_matrix_export = pd.concat(
                [price_row_df, matrix_export_df],
                ignore_index=True,
            )

            run_summary_df.to_excel(writer, sheet_name="Run Summary", index=False)
            combined_matrix_export.to_excel(writer, sheet_name="Matrix", index=False)
            etf_summary_df.to_excel(writer, sheet_name="ETF Summary", index=False)
            stock_summary_df.to_excel(writer, sheet_name="Stock Summary", index=False)
            raw_df.to_excel(writer, sheet_name="Raw Holdings", index=False)

            if theme_selection_df is not None:
                theme_selection_df.to_excel(writer, sheet_name="Theme Selection", index=False)

            if failed_etfs:
                failed_df = pd.DataFrame(
                    [{"ETF_Code": k, "Error": v} for k, v in failed_etfs.items()]
                )
                failed_df.to_excel(writer, sheet_name="Failed ETFs", index=False)

        print(f"\nPortfolio workbook exported successfully:")
        print(output_path)
        print("\nOutput message:")
        print(output_message)

    except Exception as e:
        print(f"\nSystem failure when saving file: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
