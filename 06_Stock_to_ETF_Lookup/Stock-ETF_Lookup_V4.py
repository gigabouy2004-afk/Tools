import argparse
import os
import time
import datetime
import requests
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import StringIO

# Global configuration paths and fallback defaults
DEFAULT_ETF_CSV = ""  # <-- Default ETF CSV path for testing
FAIL_SAFE_STOCKCODE = "PLTR"  # <-- Default stock code updated to PLTR
TARGET_MATCH_LIMIT = 20 # <-- Limit set for debugging

# Dynamic date string resolution for output tracking
current_date_str = datetime.datetime.now().strftime("%d%m")
DEFAULT_OUTPUT_XLSX = f"PLTR1.xlsx"

# Standard headers matching current browser definitions
STANDARD_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Connection': 'keep-alive'
}

class YahooSessionManager:
    """Manages session initialization including crumb and cookie tokens to bypass blocks cleanly."""
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(STANDARD_HEADERS)
        self.crumb = None
        self._initialize_session()

    def _initialize_session(self):
        try:
            response = self.session.get("https://finance.yahoo.com", timeout=10)
            if response.status_code == 200:
                crumb_url = "https://query2.finance.yahoo.com/v1/test/getcrumb"
                crumb_res = self.session.get(crumb_url, timeout=5)
                if crumb_res.status_code == 200 and crumb_res.text:
                    self.crumb = crumb_res.text.strip()
        except Exception:
            pass

YF_SESSION = YahooSessionManager()

def fetch_all_us_etfs():
    """Dynamically fetches a comprehensive list of US ETF tickers from public repositories."""
    etf_set = set()
    urls = [
        "https://raw.githubusercontent.com/rreichel3/US-Stock-Symbols/main/csv/nasdaq_tickers.csv",
        "https://raw.githubusercontent.com/rreichel3/US-Stock-Symbols/main/csv/nyse_tickers.csv"
    ]
    for url in urls:
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                df = pd.read_csv(StringIO(res.text))
                if 'ACT Symbol' in df.columns and 'ETF' in df.columns:
                    sub = df[df['ETF'].astype(str).str.upper().isin(['Y', 'TRUE', '1'])]
                    tickers = sub['ACT Symbol'].dropna().astype(str).str.strip().str.upper().tolist()
                    etf_set.update(tickers)
                elif 'Symbol' in df.columns:
                    tickers = df['Symbol'].dropna().astype(str).str.strip().str.upper().tolist()
                    etf_set.update(tickers)
        except Exception:
            pass
            
    if not etf_set:
        return [
            "SPY", "QQQ", "IWM", "VTI", "VOO", "DIA", "EEM", "EFA", "GLD", "SLV",
            "XLF", "XLE", "XLK", "XLV", "XLI", "XLP", "XLU", "XLB", "XLY", "XLRE",
            "ARKK", "SMH", "SOXX", "XBI", "IBB", "KWEB", "EWZ", "FXI", "EWY", "EWT",
            "MCHI", "ASHR", "INDA", "EPI", "EWJ", "VGK", "EWU", "EWG", "EWQ", "EWA",
            "TQQQ", "SQQQ", "SPXL", "SPXS", "UPRO", "TZA", "FAS", "FAZ", "UVXY", "VXX",
            "ARKG", "ARKW", "ARKF", "ARKQ", "VGT", "VUG", "VTV", "VB", "VO",
            "VNQ", "VT", "BND", "AGG", "LQD", "HYG", "TLT", "IEF", "SHY", "BIL",
            "IWN", "IWO", "VBK", "VBR", "SCHA", "SCHB", "ITOT", "IXUS", "IEFA", "QQQM", "IGV", "IWF", "SPYM"
        ]
    return sorted(list(etf_set))

def fetch_etf_holdings_direct_api(etf_ticker):
    """Directly queries public finance endpoints with robust fallbacks including multi-module variations and JSON parsing."""
    crumb_str = f"&crumb={YF_SESSION.crumb}" if YF_SESSION.crumb else ""
    modules_list = ['topHoldings,price,institutionOwnership', 'holdingPercent,price', 'fundHolding,price']
    
    for modules in modules_list:
        url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{etf_ticker}?modules={modules}{crumb_str}"
        try:
            response = YF_SESSION.session.get(url, timeout=7)
            if response.status_code == 200:
                json_data = response.json()
                result = json_data.get('quoteSummary', {}).get('result', [])
                if result:
                    summary = result[0]
                    top_holdings = summary.get('topHoldings', {}).get('holdings', [])
                    price_module = summary.get('price', {})
                    
                    if not top_holdings:
                        inst_ownership = summary.get('institutionOwnership', {}).get('ownershipList', [])
                        for item in inst_ownership:
                            top_holdings.append({
                                'symbol': item.get('organization'),
                                'percent': item.get('pctHeld')
                            })
                    
                    ltp = price_module.get('regularMarketPrice', {}).get('raw') or price_module.get('regularMarketPreviousClose', {}).get('raw') or 0.0
                    currency = price_module.get('currency', 'USD')
                    etf_name = price_module.get('longName') or price_module.get('shortName') or etf_ticker
                    
                    holdings_dict = {}
                    for holding in top_holdings:
                        symbol = str(holding.get('symbol', '')).strip().upper()
                        percent_val = holding.get('percent', 0.0)
                        if isinstance(percent_val, dict):
                            weight = float(percent_val.get('raw', 0.0))
                        else:
                            weight = float(percent_val) if percent_val else 0.0
                            
                        if symbol:
                            if 0.0 < weight < 1.0: weight *= 100
                            holdings_dict[symbol] = weight
                            
                    if holdings_dict:
                        return {'etf_name': etf_name, 'ltp': ltp, 'currency': currency, 'holdings': holdings_dict}
        except Exception: 
            pass

    # Fallback to direct quote API & common ETF static weight mapping check for known heavyholders if web endpoints block requests
    try:
        scraped_url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={etf_ticker}"
        resp = YF_SESSION.session.get(scraped_url, timeout=7)
        if resp.status_code == 200:
            data = resp.json().get('quoteResponse', {}).get('result', [])
            if data:
                item = data[0]
                etf_name = item.get('longName') or item.get('shortName') or etf_ticker
                ltp = item.get('regularMarketPrice') or item.get('regularMarketPreviousClose') or 0.0
                currency = item.get('currency', 'USD')
                return {'etf_name': etf_name, 'ltp': ltp, 'currency': currency, 'holdings': {}}
    except Exception: 
        pass
        
    return None

def fetch_stock_metadata_direct(stock_ticker):
    """Queries public endpoints for stock metrics."""
    crumb_str = f"&crumb={YF_SESSION.crumb}" if YF_SESSION.crumb else ""
    url_primary = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{stock_ticker}?modules=price,summaryDetail{crumb_str}"
    try:
        response = YF_SESSION.session.get(url_primary, timeout=7)
        if response.status_code == 200:
            json_data = response.json()
            result = json_data.get('quoteSummary', {}).get('result', [])
            if result:
                summary = result[0]
                price_mod = summary.get('price', {})
                detail_mod = summary.get('summaryDetail', {})
                
                name = price_mod.get('longName') or price_mod.get('shortName') or 'Unknown Security'
                exchange = price_mod.get('exchangeName') or 'Unknown'
                currency = price_mod.get('currency') or 'USD'
                ltp = price_mod.get('regularMarketPrice', {}).get('raw') or price_mod.get('regularMarketPreviousClose', {}).get('raw') or 0.0
                market_cap_raw = detail_mod.get('marketCap', {}).get('raw') or price_mod.get('marketCap', {}).get('raw') or 0
                currency_symbol = "₹" if currency == "INR" or ".NS" in stock_ticker else "$"
                
                if market_cap_raw >= 1e12: market_cap = f"{currency_symbol}{market_cap_raw / 1e12:.2f}T"
                elif market_cap_raw >= 1e9: market_cap = f"{currency_symbol}{market_cap_raw / 1e9:.2f}B"
                else: market_cap = f"{currency_symbol}{market_cap_raw / 1e6:.2f}M" if market_cap_raw else "-"
                    
                if ltp > 0.0 and name != 'Unknown Security':
                    return {'name': name, 'exchange': exchange, 'market_cap': market_cap, 'ltp': ltp, 'currency': currency}
    except Exception: pass

    url_secondary = f"https://query2.finance.yahoo.com/v7/finance/quote?symbols={stock_ticker}{crumb_str}"
    try:
        response = YF_SESSION.session.get(url_secondary, timeout=7)
        if response.status_code == 200:
            json_data = response.json()
            result = json_data.get('quoteResponse', {}).get('result', [])
            if result:
                stock_info = result[0]
                name = stock_info.get('longName') or stock_info.get('shortName') or 'Unknown Security'
                exchange = stock_info.get('fullExchangeName') or stock_info.get('exchange', 'Unknown')
                currency = stock_info.get('currency', 'USD')
                ltp = stock_info.get('regularMarketPrice') or stock_info.get('regularMarketPreviousClose') or 0.0
                market_cap_raw = stock_info.get('marketCap', 0)
                currency_symbol = "₹" if currency == "INR" or ".NS" in stock_ticker else "$"
                
                if market_cap_raw >= 1e12: market_cap = f"{currency_symbol}{market_cap_raw / 1e12:.2f}T"
                elif market_cap_raw >= 1e9: market_cap = f"{currency_symbol}{market_cap_raw / 1e9:.2f}B"
                else: market_cap = f"{currency_symbol}{market_cap_raw / 1e6:.2f}M" if market_cap_raw else "-"
                    
                return {'name': name, 'exchange': exchange, 'market_cap': market_cap, 'ltp': ltp, 'currency': currency}
    except Exception: pass
    return {'name': 'Unknown Security', 'exchange': 'Unknown', 'market_cap': '-', 'ltp': 0.0, 'currency': 'USD'}

def process_single_etf(yf_etf, orig_etf, target_stocks_yf, stock_mapping):
    data = fetch_etf_holdings_direct_api(yf_etf)
    if not data: return None
        
    holdings = data['holdings']
    matches_found = {}
    has_match = False
    
    for yf_stock in target_stocks_yf:
        orig_stock = stock_mapping[yf_stock]
        stock_clean = yf_stock.split('.')[0]
        
        weight_val = holdings.get(yf_stock) or holdings.get(stock_clean)
        if weight_val is not None:
            matches_found[orig_stock] = weight_val
            has_match = True
            
    if has_match:
        return {
            'orig_etf': orig_etf, 
            'etf_name': data['etf_name'], 
            'ltp': data['ltp'], 
            'currency': data['currency'], 
            'matches': matches_found
        }
    return None

def run_etf_stock_lookup(etf_csv_path, stock_codes_str, output_xlsx_path):
    start_time = time.time()
    
    raw_library_etfs = []
    if etf_csv_path and os.path.exists(os.path.abspath(etf_csv_path)):
        abs_etf_path = os.path.abspath(etf_csv_path)
        print(f"[+] Reading ETF codes from provided local file: {abs_etf_path}")
        try:
            etf_df = pd.read_csv(abs_etf_path)
            etf_col = [col for col in etf_df.columns if col.upper() in ['TICKER', 'ETF', 'SYMBOL', 'CODE']]
            if etf_col: raw_library_etfs = etf_df[etf_col[0]].dropna().astype(str).str.strip().str.upper().tolist()
            else: raw_library_etfs = etf_df.iloc[:, 0].dropna().astype(str).str.strip().str.upper().tolist()
        except Exception as e:
            print(f"[-] Error parsing ETF CSV file: {e}")
            return
    else:
        print("[+] No valid local ETF CSV provided. Dynamically fetching master list of ETFs...")
        raw_library_etfs = fetch_all_us_etfs()

    abs_out_path = os.path.abspath(output_xlsx_path)
    out_dir = os.path.dirname(abs_out_path)
    if not os.path.exists(out_dir) and out_dir != '': os.makedirs(out_dir, exist_ok=True)
            
    raw_stocks = [s.strip().upper() for s in stock_codes_str.split(",") if s.strip()]
    if not raw_stocks: return
        
    target_stocks_yf = [s.replace("XNSE", ".NS") if "XNSE" in s else s for s in raw_stocks]
    stock_mapping = dict(zip(target_stocks_yf, raw_stocks)) 

    etf_list_yf = sorted(list(set([e.replace("XNSE", ".NS") if "XNSE" in e else e for e in raw_library_etfs])))
    etf_mapping = dict(zip(etf_list_yf, raw_library_etfs))
    
    print(f"\n[!!!] HUNT & HALT MODE ACTIVE: Script will stop searching exactly when {TARGET_MATCH_LIMIT} matches are found.")
    print(f"[+] Loaded {len(etf_list_yf)} ETF codes to scan.")
    print(f"[+] Extracting profile metadata details for target stocks...")

    stock_metadata = {}
    for yf_stock in target_stocks_yf:
        orig_stock = stock_mapping[yf_stock]
        stock_metadata[orig_stock] = fetch_stock_metadata_direct(yf_stock)
        print(f"    -> {orig_stock}: {stock_metadata[orig_stock]['name']} | Price: {stock_metadata[orig_stock]['ltp']} | Market Cap: {stock_metadata[orig_stock]['market_cap']}")

    matched_etf_records = []
    etf_read_count = 0
    
    MAX_WORKERS = 10
    print(f"[+] Spawning {MAX_WORKERS} concurrent worker threads across the target matrix...")
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_etf = {executor.submit(process_single_etf, yf_etf, etf_mapping[yf_etf], target_stocks_yf, stock_mapping): yf_etf for yf_etf in etf_list_yf}
        
        for future in as_completed(future_to_etf):
            etf_read_count += 1
            if etf_read_count % 50 == 0:
                print(f"    -> Scanning... ({etf_read_count}/{len(etf_list_yf)} ETFs checked so far)")
                
            result = future.result()
            if result:
                matched_etf_records.append(result)
                print(f"    ⭐ [MATCH {len(matched_etf_records)}/{TARGET_MATCH_LIMIT}] Found {raw_stocks[0]} in ETF: {result['orig_etf']}")
                
                # Check for Early Stop
                if len(matched_etf_records) >= TARGET_MATCH_LIMIT:
                    print(f"\n[+] TARGET REACHED! Found {TARGET_MATCH_LIMIT} ETFs containing {raw_stocks[0]}.")
                    print(f"[+] Halting scanner and cancelling remaining background tasks...")
                    for f in future_to_etf:
                        f.cancel()
                    break

    print(f"[+] Compiling extracted data to Excel Report...")
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
    thin_border = Border(left=Side(style='thin', color='E0E0E0'), right=Side(style='thin', color='E0E0E0'), top=Side(style='thin', color='E0E0E0'), bottom=Side(style='thin', color='E0E0E0'))
    
    # Write Stock Summary Header / Information Block
    ws.append(["Stock Summary Information"])
    ws.merge_cells("A1:E1")
    ws.cell(row=1, column=1).fill = navy_header_fill
    ws.cell(row=1, column=1).font = font_white_bold
    ws.cell(row=1, column=1).alignment = Alignment(horizontal="center", vertical="center")
    
    stock_info_headers = ["Company Name", "Stock Ticker", "Exchange", "Market Cap", "Price"]
    ws.append(stock_info_headers)
    for col_idx in range(1, 6):
        cell = ws.cell(row=2, column=col_idx)
        cell.fill = navy_header_fill
        cell.font = font_white_bold
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border

    stock = raw_stocks[0]
    stock_row = [stock_metadata[stock]['name'], stock, stock_metadata[stock]['exchange'], stock_metadata[stock]['market_cap'], stock_metadata[stock]['ltp']]
    ws.append(stock_row)
    for col_idx in range(1, 6):
        cell = ws.cell(row=3, column=col_idx)
        cell.font = font_regular
        cell.border = thin_border
        if col_idx in [1, 3]: cell.alignment = Alignment(horizontal="left", vertical="center")
        elif col_idx in [2, 4]: cell.alignment = Alignment(horizontal="center", vertical="center")
        elif col_idx == 5:
            cell.alignment = Alignment(horizontal="right", vertical="center")
            cell.number_format = '"₹"#,##0.00' if stock_metadata[stock]['currency'] == 'INR' else '"$"#,##0.00'

    ws.append([]) # Blank row separator
    
    # ETF Holdings Detailed Table Headers
    etf_table_headers = ["ETF Ticker", "ETF Name", "ETF Price", f"Weight Held (% in {stock})"]
    ws.append(etf_table_headers)
    header_row_idx = 5
    for col_idx in range(1, 5):
        cell = ws.cell(row=header_row_idx, column=col_idx)
        cell.fill = navy_header_fill
        cell.font = font_white_bold
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border
    ws.row_dimensions[header_row_idx].height = 26

    # Populate ETF rows
    curr_row_idx = 6
    for rec in matched_etf_records:
        etf_ticker = rec['orig_etf']
        etf_name = rec['etf_name']
        etf_price = rec['ltp']
        weight = rec['matches'].get(stock, 0.0)
        
        row_vals = [etf_ticker, etf_name, etf_price, weight]
        ws.append(row_vals)
        
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
                if cell.value != 0.0:
                    cell.number_format = '"₹"#,##0.00' if rec['currency'] == 'INR' else '"$"#,##0.00'
                else:
                    cell.value = "-"
                    cell.alignment = Alignment(horizontal="center", vertical="center")
            elif col_idx == 4:
                cell.alignment = Alignment(horizontal="right", vertical="center")
                cell.number_format = '0.00"%"'
                cell.fill = light_tint_fill
                cell.font = font_bold
                
        ws.row_dimensions[curr_row_idx].height = 22
        curr_row_idx += 1

    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = openpyxl.utils.get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 18)
        
    wb.save(abs_out_path)
    
    elapsed_time = time.time() - start_time
    time_str = str(datetime.timedelta(seconds=int(elapsed_time)))
    
    print("\n" + "="*50)
    print("           ETF HOLDINGS REPORT EXECUTION")
    print("="*50)
    print(f"[>] ETFs scanned before halting           : {etf_read_count}")
    print(f"[>] Total matching ETFs found for {stock}   : {len(matched_etf_records)}")
    print(f"[>] Total execution elapsed time          : {time_str}")
    print(f"[>] Output Saved Location                 : {abs_out_path}")
    print("="*50 + "\n")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Map Custom Lookups Between Stock Universes And ETF Constituents Matrices.")
    parser.add_argument('--csv', type=str, default=DEFAULT_ETF_CSV, help="Path to input ETF CSV reference")
    parser.add_argument('--stocks', type=str, default=None, help="Comma separated stock symbols to parse lookups for")
    parser.add_argument('--output', type=str, default=DEFAULT_OUTPUT_XLSX, help="Output destination spreadsheet name")
    
    args = parser.parse_args()
    resolved_stocks = args.stocks if args.stocks is not None else FAIL_SAFE_STOCKCODE
    run_etf_stock_lookup(args.csv, resolved_stocks, args.output)