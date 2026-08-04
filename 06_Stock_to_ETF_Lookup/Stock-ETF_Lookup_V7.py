import argparse
import os
import time
import datetime
import requests
import pandas as pd
import openpyxl
import io
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

DEFAULT_OUTPUT_XLSX = "Stock_ETF_Mapping.xlsx"

STANDARD_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9'
}

def fetch_live_etf_holdings_for_stock(stock_ticker):
    """
    Performs a single reverse-lookup query to fetch all US ETFs holding the specified stock.
    """
    url = f"https://stockanalysis.com/stocks/{stock_ticker.lower()}/etf-holdings/"
    session = requests.Session()
    session.headers.update(STANDARD_HEADERS)
    
    try:
        response = session.get(url, timeout=12)
        if response.status_code == 200:
            tables = pd.read_html(io.StringIO(response.text))
            if tables:
                df = tables[0]
                return df
    except Exception as e:
        print(f"[-] Error querying inverse ETF holdings for {stock_ticker}: {e}")
    
    return pd.DataFrame()

def fetch_stock_quote_metadata(stock_ticker):
    """
    Fetches stock metadata from primary endpoints.
    """
    url = f"https://query2.finance.yahoo.com/v7/finance/quote?symbols={stock_ticker}"
    session = requests.Session()
    session.headers.update(STANDARD_HEADERS)
    
    try:
        response = session.get(url, timeout=7)
        if response.status_code == 200:
            result = response.json().get('quoteResponse', {}).get('result', [])
            if result:
                info = result[0]
                name = info.get('longName') or info.get('shortName') or stock_ticker
                exchange = info.get('fullExchangeName') or info.get('exchange', 'US')
                price = info.get('regularMarketPrice') or info.get('regularMarketPreviousClose') or 0.0
                mcap_raw = info.get('marketCap', 0)
                
                if mcap_raw >= 1e12: mcap = f"${mcap_raw / 1e12:.2f}T"
                elif mcap_raw >= 1e9: mcap = f"${mcap_raw / 1e9:.2f}B"
                elif mcap_raw > 0: mcap = f"${mcap_raw / 1e6:.2f}M"
                else: mcap = "-"
                
                return {'name': name, 'exchange': exchange, 'price': price, 'market_cap': mcap}
    except Exception:
        pass
        
    return {'name': stock_ticker, 'exchange': 'US', 'price': 0.0, 'market_cap': '-'}

def generate_excel_report(stock_ticker, stock_meta, holdings_df, output_path):
    """
    Generates formatted Excel report from extracted reverse-lookup holdings.
    """
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
        left=Side(style='thin', color='E0E0E0'),
        right=Side(style='thin', color='E0E0E0'),
        top=Side(style='thin', color='E0E0E0'),
        bottom=Side(style='thin', color='E0E0E0')
    )

    # Section 1: Stock Overview Header
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

    ws.append([]) # Empty separator

    # Section 2: ETF Table Header
    etf_headers = ["ETF Ticker", "ETF Name", "% Portfolio Weight", "Shares Held"]
    ws.append(etf_headers)
    header_row_idx = 5
    for col_idx in range(1, 5):
        cell = ws.cell(row=header_row_idx, column=col_idx)
        cell.fill = navy_header_fill
        cell.font = font_white_bold
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border
    ws.row_dimensions[header_row_idx].height = 26

    # Populate Rows from Scraped DataFrame
    curr_row_idx = 6
    if not holdings_df.empty:
        # Standardize expected column names
        symbol_col = [c for c in holdings_df.columns if 'symbol' in str(c).lower() or 'ticker' in str(c).lower() or 'etf' in str(c).lower()]
        name_col = [c for c in holdings_df.columns if 'name' in str(c).lower()]
        weight_col = [c for c in holdings_df.columns if '% ' in str(c).lower() or 'weight' in str(c).lower() or 'portfolio' in str(c).lower()]
        shares_col = [c for c in holdings_df.columns if 'shares' in str(c).lower()]

        s_col = symbol_col[0] if symbol_col else holdings_df.columns[0]
        n_col = name_col[0] if name_col else (holdings_df.columns[1] if len(holdings_df.columns) > 1 else s_col)
        w_col = weight_col[0] if weight_col else (holdings_df.columns[2] if len(holdings_df.columns) > 2 else s_col)
        sh_col = shares_col[0] if shares_col else None

        for _, row in holdings_df.iterrows():
            etf_symbol = str(row[s_col]).strip().upper()
            etf_name = str(row[n_col]).strip()
            
            raw_w = str(row[w_col]).replace('%', '').strip()
            try: weight_val = float(raw_w)
            except ValueError: weight_val = 0.0

            shares_val = str(row[sh_col]).strip() if sh_col else "-"

            ws.append([etf_symbol, etf_name, weight_val / 100.0, shares_val])
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
                    cell.alignment = Alignment(horizontal="right", vertical="center")
                    cell.number_format = '0.00%'
                    cell.fill = light_tint_fill
                    cell.font = font_bold
                elif col_idx == 4:
                    cell.alignment = Alignment(horizontal="right", vertical="center")

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
    
    print(f"[+] Fetching profile metadata details for {stock_ticker}...")
    stock_meta = fetch_stock_quote_metadata(stock_ticker)
    print(f"    -> {stock_ticker}: {stock_meta['name']} | Price: ${stock_meta['price']} | Market Cap: {stock_meta['market_cap']}")

    print(f"[+] Performing direct reverse ETF lookup for {stock_ticker}...")
    holdings_df = fetch_live_etf_holdings_for_stock(stock_ticker)
    
    print(f"[+] Compiling extracted data to Excel Report...")
    out_path, match_count = generate_excel_report(stock_ticker, stock_meta, holdings_df, output_file)

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
    parser = argparse.ArgumentParser(description="Map Custom Lookups Between Stock Universes And ETF Constituents Matrices.")
    parser.add_argument('--stocks', type=str, required=True, help="Target stock ticker (e.g. WDC, MU, PLTR)")
    parser.add_argument('--output', type=str, default=DEFAULT_OUTPUT_XLSX, help="Output destination spreadsheet name")
    
    args = parser.parse_args()
    run_pipeline(args.stocks, args.output)