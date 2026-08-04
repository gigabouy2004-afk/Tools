import pandas as pd
import numpy as np
import yfinance as yf
import datetime as dt
import os
import sys

def extract_dynamic_fund_holders(ticker_obj, ticker_code):
    """
    Dynamically extracts holder data and filters specifically for ETFs or their 
    direct derivatives (e.g., ETF, SPDR, ETN, QQQ), excluding general mutual funds, 
    while enforcing the minimum 0.5% holding threshold.
    """
    holdings = {}
    
    try:
        mf = ticker_obj.mutualfund_holders
        if mf is not None and not mf.empty:
            name_col = None
            pct_col = None
            for col in mf.columns:
                col_str = str(col).lower()
                if 'holder' in col_str or 'organization' in col_str:
                    name_col = col
                if '%' in col_str or 'pct' in col_str or 'held' in col_str:
                    pct_col = col
            
            if name_col is None: name_col = mf.columns[0]
            if pct_col is None and len(mf.columns) > 1: pct_col = mf.columns[1]
            
            for _, row in mf.iterrows():
                name = str(row[name_col]).strip()
                name_lower = name.lower()
                
                # Strict rule: Only allow names containing ETF or its explicit derivatives
                if not ('etf' in name_lower or 'spdr' in name_lower or 'etn' in name_lower or 'qqq' in name_lower):
                    continue
                    
                val = 0.0
                if pct_col is not None:
                    try:
                        val_str = str(row[pct_col]).replace('%', '').strip()
                        val = float(val_str)
                        if 0.0 < val < 1.0 and '%' not in str(row[pct_col]):
                            val = val * 100.0
                    except ValueError:
                        pass
                
                if name and name.lower() != 'nan' and val >= 0.5:
                    holdings[name] = round(val, 4)
    except Exception as e:
        print(f"[INFO] ETF data parsing skipped for {ticker_code}: {e}")
        
    return holdings

def generate_fully_dynamic_matrix(ticker_list):
    # Dynamically generate unique filename with date timestamp (YYYYMMDD_HHMMSS)
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"Dynamic_Global_ETF_Matrix_{timestamp}.xlsx"
    
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
    except NameError:
        script_dir = os.getcwd()
        
    output_filepath = os.path.join(script_dir, output_filename)
    print(f"[INFO] Output target location locked to: {output_filepath}")

    records = []
    discovered_etfs = set()
    
    for ticker in ticker_list:
        ticker = str(ticker).strip().upper()
        print(f"[PROCESSING] Fetching data for stock code: {ticker}...")
        
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="2y")
            
            if hist.empty:
                print(f"[WARNING] No pricing data found for ticker {ticker}. Skipping row calculation.")
                continue
                
            try:
                info = t.info
                comp_name = info.get('longName', info.get('shortName', ticker))
                exchange = info.get('exchange', 'N/A')
            except Exception as e:
                print(f"[INFO] Metadata fetching limited for {ticker}: {e}")
                comp_name = ticker
                exchange = 'N/A'
                
            current_price = round(float(hist['Close'].iloc[-1]), 2)
            latest_date = hist.index[-1].date()
            
            ytd_target = dt.date(latest_date.year - 1, 12, 31)
            mtd_target = latest_date.replace(day=1) - dt.timedelta(days=1)
            wtd_target = latest_date - dt.timedelta(days=latest_date.weekday())
            rolling_90d_target = latest_date - dt.timedelta(days=90)
            
            def get_closest_price(target_date):
                past_data = hist[hist.index.date <= target_date]
                if not past_data.empty:
                    return float(past_data['Close'].iloc[-1])
                return float(hist['Close'].iloc[0])

            ytd_price = get_closest_price(ytd_target)
            mtd_price = get_closest_price(mtd_target)
            wtd_price = get_closest_price(wtd_target)
            rolling_90d_price = get_closest_price(rolling_90d_target)
            
            wtd = (current_price / wtd_price) - 1 if wtd_price else 0.0
            mtd = (current_price / mtd_price) - 1 if mtd_price else 0.0
            rolling_90d = (current_price / rolling_90d_price) - 1 if rolling_90d_price else 0.0
            ytd = (current_price / ytd_price) - 1 if ytd_price else 0.0
            
            base_record = {
                'Stock Code': ticker,
                'Company Name': comp_name,
                'Exchange': exchange,
                'Last Traded Price': current_price,
                'WTD Return': wtd,
                'MTD Return': mtd,
                '90-Day Rolling Return': rolling_90d,
                'YTD Return': ytd,
                '_raw_holdings': {}
            }
            
            holdings = extract_dynamic_fund_holders(t, ticker)
            base_record['_raw_holdings'] = holdings
            
            for etf_label in holdings.keys():
                discovered_etfs.add(etf_label)
                
            records.append(base_record)
            
        except Exception as e:
            print(f"[ERROR] Critical failure processing ticker {ticker}: {e}", file=sys.stderr)
        
    if not records:
        print("[CRITICAL] Process halted: No records generated for the supplied stock list.", file=sys.stderr)
        return

    sorted_etfs = sorted(list(discovered_etfs))
    final_rows = []
    
    for rec in records:
        row = {
            'Stock Code': rec['Stock Code'],
            'Company Name': rec['Company Name'],
            'Exchange': rec['Exchange'],
            'Last Traded Price': rec['Last Traded Price'],
            'WTD Return': rec['WTD Return'],
            'MTD Return': rec['MTD Return'],
            '90-Day Rolling Return': rec['90-Day Rolling Return'],
            'YTD Return': rec['YTD Return']
        }
        
        etf_count = 0
        for etf in sorted_etfs:
            weight = rec['_raw_holdings'].get(etf, 0.0)
            row[etf] = weight
            if weight > 0.0:
                etf_count += 1
                
        row['ETF Count'] = etf_count
        final_rows.append(row)
        
    df = pd.DataFrame(final_rows)
    
    base_cols = ['Stock Code', 'Company Name', 'Exchange', 'ETF Count', 'Last Traded Price', 'WTD Return', 'MTD Return', '90-Day Rolling Return', 'YTD Return']
    ordered_cols = base_cols + sorted_etfs
    df = df[ordered_cols]
    
    total_row = {col: '' for col in ordered_cols}
    total_row['Stock Code'] = 'Total Sum'
    for col in sorted_etfs:
        total_row[col] = df[col].sum()
    df = pd.concat([df, pd.DataFrame([total_row])], ignore_index=True)
    
    try:
        print(f"[WRITING] Compiling structured data matrix to Excel...")
        with pd.ExcelWriter(output_filepath, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='ETF Financial Matrix', index=False)
            worksheet = writer.sheets['ETF Financial Matrix']
            max_row, max_col = worksheet.max_row, worksheet.max_column
            
            etf_count_idx = base_cols.index('ETF Count') + 1
            ltp_idx = base_cols.index('Last Traded Price') + 1
            return_indices = [base_cols.index('WTD Return') + 1, base_cols.index('MTD Return') + 1, base_cols.index('90-Day Rolling Return') + 1, base_cols.index('YTD Return') + 1]
            etf_start_idx = len(base_cols) + 1
            
            for row in range(2, max_row):
                cell = worksheet.cell(row=row, column=ltp_idx)
                if isinstance(cell.value, (int, float)): cell.number_format = '0.00'
                
                count_cell = worksheet.cell(row=row, column=etf_count_idx)
                if count_cell.value != '': count_cell.number_format = '#,##0'
                
                for col_idx in return_indices:
                    r_cell = worksheet.cell(row=row, column=col_idx)
                    if isinstance(r_cell.value, (int, float)): r_cell.number_format = '0.00%'
            
            for row in range(2, max_row + 1):
                for col in range(etf_start_idx, max_col + 1):
                    weight_cell = worksheet.cell(row=row, column=col)
                    if isinstance(weight_cell.value, (int, float)): weight_cell.number_format = '0.00"%"'
                    
            for col in worksheet.columns:
                max_len = max(len(str(cell.value or '')) for cell in col)
                col_letter = col[0].column_letter
                worksheet.column_dimensions[col_letter].width = max(max_len + 3, 12)
                
        print(f"[SUCCESS] File generated and saved directly in script directory: {output_filepath}")
    except Exception as e:
        print(f"[CRITICAL] Excel serialization or cell formatting failed: {e}", file=sys.stderr)

if __name__ == "__main__":
    input_tickers = ["NVDA", "RELIANCE.NS", "ASTS", "AAPL"]
    generate_fully_dynamic_matrix(input_tickers)