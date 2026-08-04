import argparse
import pandas as pd
import yfinance as yf
import datetime as dt
import sys
import os
import traceback

def handle_ticker(ticker):
    try:
        ticker = str(ticker).strip().upper()
        
        if ticker.startswith("XNSE"):
            return ticker.replace("XNSE", "") + ".NS"
        if ticker.startswith("XBSE"):
            return ticker.replace("XBSE", "") + ".BO"
        if ticker.startswith("NSE:"):
            return ticker.replace("NSE:", "") + ".NS"
        if ticker.startswith("BSE:"):
            return ticker.replace("BSE:", "") + ".BO"
        if ticker.startswith("NASDAQ:"):
            return ticker.replace("NASDAQ:", "")
        if ticker.startswith("NYSE:"):
            return ticker.replace("NYSE:", "")
            
        return ticker
    except Exception as e:
        print(f"[ERROR] Failed to handle ticker format for '{ticker}': {e}")
        return ticker

def get_performance_and_info(ticker_symbol):
    try:
        t = yf.Ticker(ticker_symbol)
        
        try:
            info = t.info
            comp_name = info.get('longName', info.get('shortName', ''))
            exchange = info.get('exchange', '')
        except Exception as e:
            print(f"[WARNING] Could not retrieve basic info for {ticker_symbol}: {e}")
            comp_name = ''
            exchange = ''

        try:
            hist = t.history(period="2y")
        except Exception as e:
            print(f"[WARNING] Could not retrieve price history for {ticker_symbol}: {e}")
            hist = pd.DataFrame()

        if hist.empty:
            print(f"[WARNING] Price history is empty for {ticker_symbol}.")
            return comp_name, exchange, 0.0, 0.0, 0.0, 0.0, 0.0, t
        
        current_price = round(float(hist['Close'].iloc[-1]), 2)
        today = dt.date.today()
        
        last_year_end = dt.date(today.year - 1, 12, 31)
        first_of_month = today.replace(day=1)
        last_month_end = first_of_month - dt.timedelta(days=1)
        last_friday = today - dt.timedelta(days=today.weekday() + 3)
        ninety_days_ago = today - dt.timedelta(days=90)
        
        def get_closest_price(target_date):
            past_data = hist.loc[:str(target_date)]
            if not past_data.empty:
                return past_data['Close'].iloc[-1]
            return current_price

        ytd_price = get_closest_price(last_year_end)
        mtd_price = get_closest_price(last_month_end)
        wtd_price = get_closest_price(last_friday)
        rolling_90d_price = get_closest_price(ninety_days_ago)
        
        ytd = (current_price / ytd_price) - 1 if ytd_price else 0.0
        mtd = (current_price / mtd_price) - 1 if mtd_price else 0.0
        wtd = (current_price / wtd_price) - 1 if wtd_price else 0.0
        rolling_90d = (current_price / rolling_90d_price) - 1 if rolling_90d_price else 0.0
        
        return comp_name, exchange, current_price, wtd, mtd, rolling_90d, ytd, t

    except Exception as e:
        print(f"[ERROR] Unexpected error processing performance for {ticker_symbol}: {e}")
        return '', '', 0.0, 0.0, 0.0, 0.0, 0.0, None

def generate_advanced_etf_matrix(ticker_list, filename="ETF_Comprehensive_Matrix.xlsx"):
    all_records = []
    
    print(f"Retrieving market portfolios for: {ticker_list}...")
    
    for raw_ticker in ticker_list:
        try:
            yf_ticker = handle_ticker(raw_ticker)
            
            comp_name, exchange, curr_price, wtd, mtd, rolling_90d, ytd, t = get_performance_and_info(yf_ticker)
            
            row_dict = {
                'Stock Code': raw_ticker,
                'Company Name': comp_name,
                'Exchange': exchange,
                'Last Traded Price': curr_price,
                'WTD Return': wtd,
                'MTD Return': mtd,
                '90-Day Rolling Return': rolling_90d,
                'YTD Return': ytd
            }
            
            if t is None:
                all_records.append(row_dict)
                continue

            etf_keywords = ['ETF', 'Exchange-Traded', 'Exchange Traded', 'Traded Fund', 'Index', 'Fund', 'Trust']
            found_etfs = False
            
            try:
                holders_dfs = [t.mutualfund_holders, t.institutional_holders]
            except Exception as e:
                print(f"[WARNING] Failed to fetch holder data for {raw_ticker}: {e}")
                holders_dfs = []

            for holders_df in holders_dfs:
                if isinstance(holders_df, pd.DataFrame) and not holders_df.empty:
                    holder_col = next((col for col in ['Holder', 'Organization'] if col in holders_df.columns), None)
                    pct_col = next((col for col in ['% Out', 'pctHeld', 'Shares'] if col in holders_df.columns), None)
                    
                    if holder_col and pct_col:
                        for _, row in holders_df.iterrows():
                            holder_name = str(row[holder_col]).strip()
                            pct_held = row[pct_col]
                            
                            if any(keyword.lower() in holder_name.lower() for keyword in etf_keywords):
                                try:
                                    val = float(str(pct_held).replace('%', ''))
                                    if val < 1.0 and '%' not in str(pct_held):
                                        val = val * 100
                                    row_dict[holder_name] = val
                                    found_etfs = True
                                except (ValueError, TypeError):
                                    pass

            if not found_etfs:
                print(f" -> Skipping {raw_ticker}: No valid ETF holder data available from source.")
                
            all_records.append(row_dict)
            
        except Exception as e:
            print(f"[ERROR] Critical failure processing ticker {raw_ticker}:")
            traceback.print_exc()
        
    if not all_records:
        print("[ERROR] No records generated. Halting execution.")
        return False
        
    try:
        df = pd.DataFrame(all_records)
        
        base_cols_without_count = [
            'Stock Code', 'Company Name', 'Exchange', 'Last Traded Price', 
            'WTD Return', 'MTD Return', '90-Day Rolling Return', 'YTD Return'
        ]
        etf_columns = [col for col in df.columns if col not in base_cols_without_count]
        
        if not etf_columns:
            print("\n[INFO] Note: No ETF ownership columns were found for any processed tickers.")
            
        df[etf_columns] = df[etf_columns].fillna(0.0)
        df['ETF Count'] = (df[etf_columns] > 0.0).sum(axis=1) if etf_columns else 0
        
        ordered_columns = [
            'Stock Code', 'Company Name', 'Exchange', 'ETF Count', 'Last Traded Price', 
            'WTD Return', 'MTD Return', '90-Day Rolling Return', 'YTD Return'
        ] + etf_columns
        
        df = df[ordered_columns]
        
        total_row = {col: '' for col in ordered_columns}
        total_row['Stock Code'] = 'Total Sum'
        for col in etf_columns:
            total_row[col] = df[col].sum()
            
        df = pd.concat([df, pd.DataFrame([total_row])], ignore_index=True)
    except Exception as e:
        print("[ERROR] Failed during dataframe structuring/calculations:")
        traceback.print_exc()
        return False
    
    print("\nFormatting spreadsheet calculations...")
    
    name, ext = os.path.splitext(filename)
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_filename = f"{name}_{timestamp}{ext}"
    abs_path = os.path.abspath(unique_filename)
    output_dir = os.path.dirname(abs_path)

    if not os.path.exists(output_dir) and output_dir != '':
        try:
            os.makedirs(output_dir)
        except Exception as e:
            print(f"[ERROR] Cannot create output directory '{output_dir}': {e}")
            return False

    if output_dir != '' and not os.access(output_dir, os.W_OK):
        print(f"[ERROR] Write permission denied for directory '{output_dir}'.")
        return False

    try:
        with pd.ExcelWriter(abs_path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='ETF Financial Matrix', index=False)
            
            worksheet = writer.sheets['ETF Financial Matrix']
            max_row = worksheet.max_row
            max_col = worksheet.max_column
            
            etf_count_idx = ordered_columns.index('ETF Count') + 1
            ltp_idx = ordered_columns.index('Last Traded Price') + 1
            return_col_indices = [
                ordered_columns.index('WTD Return') + 1,
                ordered_columns.index('MTD Return') + 1,
                ordered_columns.index('90-Day Rolling Return') + 1,
                ordered_columns.index('YTD Return') + 1
            ]
            
            for row in range(2, max_row):
                cell = worksheet.cell(row=row, column=ltp_idx)
                if isinstance(cell.value, (int, float)):
                    cell.number_format = '0.00'

            for row in range(2, max_row): 
                for col_idx in return_col_indices:
                    cell = worksheet.cell(row=row, column=col_idx)
                    if isinstance(cell.value, (int, float)):
                        cell.number_format = '0.00%'
                        
            for row in range(2, max_row): 
                cell = worksheet.cell(row=row, column=etf_count_idx)
                if cell.value != '':
                    cell.number_format = '#,##0'
                    
            for row in range(2, max_row + 1):
                for col in range(ordered_columns.index(ordered_columns[9]) + 1 if len(ordered_columns) > 9 else max_col + 1, max_col + 1):
                    cell = worksheet.cell(row=row, column=col)
                    if isinstance(cell.value, (int, float)):
                        cell.number_format = '0.00"%"'
                        
            for col in worksheet.columns:
                max_len = max(len(str(cell.value or '')) for cell in col)
                col_letter = col[0].column_letter
                worksheet.column_dimensions[col_letter].width = max(max_len + 3, 12)
                
        print(f"\nSuccess! Document saved at:\n{abs_path}")
        return True
        
    except PermissionError:
        print(f"\n[CRITICAL ERROR] Permission denied when saving to '{abs_path}'.")
        print(" -> Is the file currently open in Microsoft Excel or another program? Please close it and try again.")
        return False
    except ModuleNotFoundError as e:
        print(f"\n[CRITICAL ERROR] Missing required library for Excel formatting: {e}")
        print(" -> Please run: pip install openpyxl")
        return False
    except Exception as e:
        print("\n[CRITICAL ERROR] An unexpected error occurred while writing the Excel file:")
        traceback.print_exc()
        return False

def main():
    parser = argparse.ArgumentParser(description="Extract stock properties and ETF holder matrices.")
    parser.add_argument('-t', '--tickers', nargs='+', help="List of stock tickers.")
    parser.add_argument('-c', '--csv', type=str, help="Path to CSV file containing stock tickers.")
    parser.add_argument('-o', '--output', type=str, default="ETF_Comprehensive_Matrix.xlsx", help="Output Excel filename.")
    
    args = parser.parse_args()
    
    tickers = []
    if args.tickers:
        tickers.extend(args.tickers)
        
    if args.csv:
        if os.path.exists(args.csv):
            try:
                df_input = pd.read_csv(args.csv)
                if not df_input.empty:
                    tickers.extend(df_input.iloc[:, 0].dropna().astype(str).tolist())
            except Exception as e:
                print(f"[ERROR] Failed reading CSV file '{args.csv}': {e}")
                sys.exit(1)
        else:
            print(f"[ERROR] CSV file not found: '{args.csv}'.")
            sys.exit(1)

    if not tickers:
        tickers = ["AAPL", "MSFT", "NVDA", "T", "AMZN", "GOOGL", "ASTS"]
        print(f"No tickers provided via CLI. Using default list: {tickers}")

    try:
        generate_advanced_etf_matrix(tickers, filename=args.output)
    except KeyboardInterrupt:
        print("\n[INFO] Script execution cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print("\n[CRITICAL ERROR] Script execution failed due to an unhandled exception:")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()