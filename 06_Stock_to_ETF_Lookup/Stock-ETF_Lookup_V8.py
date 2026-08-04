import argparse
import os
import time
import datetime
import urllib.request
import json
import io
import pandas as pd
import yfinance as yf
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

DEFAULT_OUTPUT_XLSX = "Stock_ETF_Mapping.xlsx"

STANDARD_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9'
}

def fetch_stock_metadata(stock_ticker):
    print(f"[+] Fetching profile metadata details for {stock_ticker} via YFinance...")
    try:
        t = yf.Ticker(stock_ticker)
        info = t.info
        price = info.get("currentPrice", info.get("regularMarketPrice", 0.0))
        mcap_raw = info.get("marketCap", 0)
        name = info.get("longName", info.get("shortName", stock_ticker))
        exchange = info.get("fullExchangeName", info.get("exchange", "US"))
        
        if mcap_raw >= 1e12: mcap = f"${mcap_raw / 1e12:.2f}T"
        elif mcap_raw >= 1e9: mcap = f"${mcap_raw / 1e9:.2f}B"
        elif mcap_raw > 0: mcap = f"${mcap_raw / 1e6:.2f}M"
        else: mcap = "-"
        
        print(f"    -> {stock_ticker}: {name} | Price: ${price} | Market Cap: {mcap}")
        return {'name': name, 'exchange': exchange, 'price': price, 'market_cap': mcap}
    except Exception as e:
        print(f" [!] Metadata error: {e}")
        return {'name': stock_ticker, 'exchange': 'US', 'price': 0.0, 'market_cap': '-'}

def fetch_live_etf_holdings_for_stock(stock_ticker):
    print(f"[+] Performing direct reverse ETF lookup for {stock_ticker}...")
    
    # Method 1: StockAnalysis.com
    try:
        url = f"https://stockanalysis.com/stocks/{stock_ticker.lower()}/etf-holdings/"
        req = urllib.request.Request(url, headers=STANDARD_HEADERS)
        with urllib.request.urlopen(req, timeout=12) as response:
            html = response.read().decode('utf-8')
        tables = pd.read_html(io.StringIO(html))
        if tables:
            df = tables[0]
            if not df.empty:
                print(f"    -> [stockanalysis.com] Mapped {len(df)} ETFs.")
                return df
    except Exception:
        pass

    # Method 2: ETF.com fallback
    try:
        url = f"https://www.etf.com/stock/{stock_ticker.upper()}"
        req = urllib.request.Request(url, headers=STANDARD_HEADERS)
        with urllib.request.urlopen(req, timeout=12) as response:
            html = response.read().decode('utf-8')
        tables = pd.read_html(io.StringIO(html))
        if tables:
            df = tables[0]
            if not df.empty:
                print(f"    -> [etf.com] Mapped {len(df)} ETFs.")
                return df
    except Exception:
        pass

    # Method 3: Yahoo Finance Quote Summary API (JSON via urllib)
    try:
        url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{stock_ticker.upper()}?modules=topHoldings"
        req = urllib.request.Request(url, headers=STANDARD_HEADERS)
        with urllib.request.urlopen(req, timeout=12) as response:
            data = json.loads(response.read().decode('utf-8'))
            # Note: Yahoo quoteSummary topHoldings returns funds holding the stock if available in some endpoints, 
            # but let's parse if present or fallback to searching popular tech/semiconductor ETFs directly if needed.
    except Exception:
        pass

    # Method 4: Comprehensive Built-in Target ETF Sweep (Fallback when web scrapers are blocked/empty)
    print(f"    -> Web scrapers returned 0 matches or blocked. Running direct constituent sweep across major US ETFs...")
    major_etfs = [
        "QQQ", "SPY", "XLK", "SMH", "SOXX", "XSD", "IGV", "XT", "VGT", "IYW", 
        "FTEC", "TCHI", "SKYY", "CLOU", "WCLD", "CIBR", "HACK", "BUG", "BOTZ", "ROBO"
    ]
    
    matched_etfs = []
    for etf_sym in major_etfs:
        try:
            t = yf.Ticker(etf_sym)
            holdings = t.holdings
            if holdings is not None and not holdings.empty:
                if stock_ticker.upper() in holdings.index or (any(stock_ticker.upper() in str(val).upper() for val in holdings.values.flatten())):
                    matched_etfs.append({"ETF Symbol": etf_sym, "ETF Name": t.info.get("shortName", etf_sym), "Allocation (%)": "Top Holding"})
        except Exception:
            continue

    if matched_etfs:
        print(f"    -> [YFinance Sweep] Mapped {len(matched_etfs)} ETFs holding {stock_ticker}.")
        return pd.DataFrame(matched_etfs)

    return pd.DataFrame()

def generate_exact_wdc_format_report(stock_ticker, stock_meta, holdings_df, output_path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "ETF Holdings Analysis"
    ws.views.sheetView[0].showGridLines = True

    navy_header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    alt_zebra_fill = PatternFill(start_color="F9FAFB", end_color="F9FAFB", fill_type="solid")
    light_tint_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")

    font_white_bold = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
    font_regular = Font(name="Segoe UI", size=11)
    font_bold = Font(name="Segoe UI", size=11, bold=True)
    thin_border = Border(
        left=Side(style='thin', color='E0E0E0'), right=Side(style='thin', color='E0E0E0'),
        top=Side(style='thin', color='E0E0E0'), bottom=Side(style='thin', color='E0E0E0')
    )

    # Section 1: Stock Overview Header (Matches WDC.xlsx exact row structure)
    ws.append(["Stock Summary Information"])
    ws.merge_cells("A1:E1")
    ws.cell(row=1, column=1).fill = navy_header_fill
    ws.cell(row=1, column=1).font = font_white_bold
    ws.cell(row=1, column=1).alignment = Alignment(horizontal="center", vertical="center")

    stock_headers = ["Company Name", "Stock Ticker", "Exchange", "Market Cap", "Price"]
    ws.append(stock_headers)
    for col_idx in range(1, 6):
        cell = ws.cell(row=2, column=col_idx)
        cell.fill = navy_header_fill
        cell.font = font_white_bold
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border

    ws.append([stock_meta['name'], stock_ticker, stock_meta['exchange'], stock_meta['market_cap'], stock_meta['price']])
    for col_idx in range(1, 6):
        cell = ws.cell(row=3, column=col_idx)
        cell.font = font_regular
        cell.border = thin_border
        if col_idx in [1, 3]: cell.alignment = Alignment(horizontal="left", vertical="center")
        elif col_idx in [2, 4]: cell.alignment = Alignment(horizontal="center", vertical="center")
        elif col_idx == 5:
            cell.alignment = Alignment(horizontal="right", vertical="center")
            cell.number_format = '"$"#,##0.00'

    ws.append([]) # Row 4 empty separator

    # Section 2: ETF Table Header (Matches exact WDC.xlsx format)
    etf_headers = ["ETF Ticker", "ETF Name", "ETF Price", f"Weight Held (% in {stock_ticker})"]
    ws.append(etf_headers)
    header_row_idx = 5
    for col_idx in range(1, 5):
        cell = ws.cell(row=header_row_idx, column=col_idx)
        cell.fill = navy_header_fill
        cell.font = font_white_bold
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border
    ws.row_dimensions[header_row_idx].height = 26

    curr_row_idx = 6
    if not holdings_df.empty:
        symbol_col = next((c for c in holdings_df.columns if 'symbol' in str(c).lower() or 'ticker' in str(c).lower() or 'etf' in str(c).lower()), holdings_df.columns[0])
        name_col = next((c for c in holdings_df.columns if 'name' in str(c).lower() or 'fund' in str(c).lower()), holdings_df.columns[1] if len(holdings_df.columns) > 1 else symbol_col)
        weight_col = next((c for c in holdings_df.columns if '%' in str(c) or 'weight' in str(c).lower() or 'allocation' in str(c).lower()), None)

        for _, row in holdings_df.iterrows():
            etf_symbol = str(row[symbol_col]).strip().upper()
            etf_name = str(row[name_col]).strip()
            
            weight_val = 0.0
            if weight_col is not None:
                raw_w = str(row[weight_col]).replace('%', '').strip()
                try: weight_val = float(raw_w) / 100.0
                except ValueError: pass

            ws.append([etf_symbol, etf_name, "-", weight_val])
            is_even = (curr_row_idx % 2 == 0)

            for col_idx in range(1, 5):
                cell = ws.cell(row=curr_row_idx, column=col_idx)
                cell.font = font_regular
                cell.border = thin_border
                if is_even: cell.fill = alt_zebra_fill

                if col_idx == 1:
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                    cell.font = font_bold
                elif col_idx == 2:
                    cell.alignment = Alignment(horizontal="left", vertical="center")
                elif col_idx == 3:
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                elif col_idx == 4:
                    cell.alignment = Alignment(horizontal="right", vertical="center")
                    cell.number_format = '0.00%'
                    cell.fill = light_tint_fill
                    cell.font = font_bold

            ws.row_dimensions[curr_row_idx].height = 22
            curr_row_idx += 1

    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = openpyxl.utils.get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 18)

    abs_out_path = os.path.abspath(output_path)
    wb.save(abs_out_path)
    return abs_out_path, (curr_row_idx - 6)

def run_pipeline(stock_symbol, output_file):
    start_time = time.time()
    stock_ticker = stock_symbol.strip().upper()
    
    stock_meta = fetch_stock_metadata(stock_ticker)
    holdings_df = fetch_live_etf_holdings_for_stock(stock_ticker)
    
    print(f"[+] Compiling extracted data to exact template Excel Report...")
    out_path, match_count = generate_exact_wdc_format_report(stock_ticker, stock_meta, holdings_df, output_file)

    elapsed_time = time.time() - start_time
    time_str = str(datetime.timedelta(seconds=int(elapsed_time)))

    print("\n" + "="*50)
    print("           ETF HOLDINGS REPORT EXECUTION")
    print("="*50)
    print(f"[>] Total matching US ETFs found for {stock_ticker} : {match_count}")
    print(f"[>] Total execution elapsed time          : {time_str}")
    print(f"[>] Output Saved Location                 : {out_path}")
    print("="*50 + "\n")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Exact WDC Format Reverse Stock-to-ETF Lookup Tool with Fallback Sweep")
    parser.add_argument('--stocks', type=str, required=True, help="Target stock ticker (e.g. STX)")
    parser.add_argument('--output', type=str, default=DEFAULT_OUTPUT_XLSX, help="Output destination spreadsheet name")
    
    args = parser.parse_args()
    run_pipeline(args.stocks, args.output)