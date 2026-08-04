import pandas as pd
import yfinance as yf
import os
from pathlib import Path
from datetime import datetime, timedelta

# --- USER CONFIGURATION ---
BASE_FOLDER = r"D:/Tools/ETF_Comparator"
INPUT_FILENAME = "INPUT/01_INPUT_All_Country_ETFCodes_v1.csv"
OUTPUT_FILENAME = "OUTPUT/02_Result_All_Country_ETF_Comparator_v3.xlsx"
HARDCODED_ETFS = [] # Providing an empty list to avoid iteration errors if empty string

def run_etf_comparator():
    # 1. Path Management
    base_path = Path(BASE_FOLDER)
    if not base_path.exists():
        base_path.mkdir(parents=True, exist_ok=True)

    input_path = base_path / INPUT_FILENAME
    output_path = base_path / OUTPUT_FILENAME

    # 2. Gather Unique ETF Codes
    # Handle HARDCODED_ETFS as a list
    etf_set = {ticker.strip().upper() for ticker in HARDCODED_ETFS if isinstance(ticker, str) and ticker.strip()}
    
    if input_path.exists():
        with open(input_path, 'r') as f:
            file_codes = {line.strip().upper() for line in f if line.strip()}
            etf_set.update(file_codes)

    final_etf_list = sorted(list(etf_set))
    
    # 3. Reference Dates
    now = datetime.now() # May 4, 2026
    
    months_2026 = {
        "Apr-26": (datetime(2026, 4, 1), datetime(2026, 4, 30)),
        "Mar-26": (datetime(2026, 3, 1), datetime(2026, 3, 31)),
        "Feb-26": (datetime(2026, 2, 1), datetime(2026, 2, 28)),
        "Jan-26": (datetime(2026, 1, 1), datetime(2026, 1, 31))
    }

    data_list = []
    print(f"Processing {len(final_etf_list)} ETFs...")

    for ticker_symbol in final_etf_list:
        try:
            ticker = yf.Ticker(ticker_symbol)
            hist = ticker.history(period="2y")
            
            if hist.empty:
                continue

            hist.index = hist.index.tz_localize(None)
            current_price = hist['Close'].iloc[-1]
            
            def get_return(start_dt, end_dt=None):
                try:
                    start_mask = hist.index >= pd.Timestamp(start_dt)
                    if not start_mask.any(): return 0
                    start_val = hist.loc[start_mask]['Close'].iloc[0]
                    
                    if end_dt:
                        end_mask = hist.index <= pd.Timestamp(end_dt)
                        if not end_mask.any(): return 0
                        target_val = hist.loc[end_mask]['Close'].iloc[-1]
                    else:
                        target_val = current_price
                        
                    return (target_val - start_val) / start_val
                except:
                    return 0

            info = ticker.info
            
            # --- UPDATED EXPENSE RATIO FALLBACK ---
            # Checks primary info, then nested fees, then falls back to N/A
            exp_ratio = info.get('expenseRatio') or info.get('annualReportExpenseRatio')
            
            if exp_ratio is None:
                try:
                    # Accesses nested fund data if standard info is restricted
                    exp_ratio = ticker.fund_performance.get('fees', {}).get('expenseRatio')
                except:
                    exp_ratio = "N/A"
            
            raw_aum = info.get('totalAssets') or info.get('marketCap') or 0
            
            row = {
                "Ticker": ticker_symbol,
                "Name": info.get('longName', 'N/A'),
                "AUM (USD M)": raw_aum / 1_000_000,
                "Price": current_price,
#                "Expense Ratio": exp_ratio,
                "Liquidity (Avg Vol)": info.get('averageVolume', 'N/A'),
                "Since Yesterday": get_return(now - timedelta(days=1)),
                "This Week": get_return(now - timedelta(days=now.weekday())),
                "MTD": get_return(datetime(now.year, now.month, 1)),
                "Apr-26": get_return(*months_2026["Apr-26"]),
                "Mar-26": get_return(*months_2026["Mar-26"]),
                "Feb-26": get_return(*months_2026["Feb-26"]),
                "Jan-26": get_return(*months_2026["Jan-26"]),
                "YTD": get_return(datetime(2026, 1, 1)),
                "3 Month": get_return(now - timedelta(days=90)),
                "6 Month": get_return(now - timedelta(days=180)),
                "9 Month": get_return(now - timedelta(days=270)),
                "1 yr": get_return(now - timedelta(days=365))
            }
            data_list.append(row)
            print(f"[+] Processed: {ticker_symbol} | Expense: {exp_ratio}")
        except Exception as e:
            print(f"[!] Error {ticker_symbol}: {e}")

    # 4. Final Output Generation
    if data_list:
        df = pd.DataFrame(data_list)
        column_order = [
            "Ticker", "Name", "AUM (USD M)", "Price", 
            #"Expense Ratio", 
            "Liquidity (Avg Vol)",
            "Since Yesterday", "This Week", "MTD", "Apr-26", "Mar-26", "Feb-26", "Jan-26",
            "YTD", "3 Month", "6 Month", "9 Month", "1 yr"
        ]
        df = df[column_order]
        df = df.sort_values(by="Apr-26", ascending=False)
        
        try:
            df.to_excel(output_path, index=False, engine='openpyxl')
            print(f"\nSuccess! Consolidated report saved to: {output_path}")
        except Exception as e:
            print(f"\nSave Error: {e}")

if __name__ == "__main__":
    run_etf_comparator()