import argparse
import pandas as pd
import yfinance as yf
from mstarpy import Funds
import os
import sys

DEFAULT_INPUT_FILE = 'input_etfs.csv'
DEFAULT_OUTPUT_FILE = 'output_etf_data2.csv'

def extract_etf_metrics(input_filename, output_filename):
    print(f"Reading input from: {input_filename}")
    
    if not os.path.isfile(input_filename):
        print(f"Critical Error: Input file '{input_filename}' does not exist.")
        sys.exit(1)
        
    try:
        df_input = pd.read_csv(input_filename)
        if df_input.empty:
            print(f"Critical Error: Input CSV '{input_filename}' is empty.")
            sys.exit(1)
        etf_codes = df_input.iloc[:, 0].dropna().unique().tolist()
    except pd.errors.EmptyDataError:
        print(f"Critical Error: Input file '{input_filename}' is completely empty or invalid.")
        sys.exit(1)
    except PermissionError:
        print(f"Critical Error: Permission denied to read '{input_filename}'. Please close the file if it is open in another program.")
        sys.exit(1)
    except Exception as e:
        print(f"Critical Error reading input file: {e}")
        sys.exit(1)

    results = []
    total_etfs = len(etf_codes)

    for idx, code in enumerate(etf_codes, 1):
        print(f"Processing {idx}/{total_etfs}: {code}")
        ticker = yf.Ticker(code)
        
        try:
            info = ticker.info
        except Exception:
            info = {}
        
        holdings_str = None
        num_holdings = None
        ms_rating = None
        risk_rating = None
        alpha = None
        sharpe = None
        
        try:
            fund = Funds(term=code, country="us")
            
            try:
                holdings_df = fund.holdings(holdingType='all')
                if holdings_df is not None and not holdings_df.empty:
                    num_holdings = len(holdings_df)
                    if 'ticker' in holdings_df.columns:
                        holdings_list = holdings_df['ticker'].dropna().tolist()
                        holdings_str = ", ".join([str(h) for h in holdings_list])
                    elif 'securityName' in holdings_df.columns:
                        holdings_list = holdings_df['securityName'].dropna().tolist()
                        holdings_str = ", ".join([str(h) for h in holdings_list])
            except Exception:
                pass
            
            try:
                risk_rating_data = fund.riskAndRating()
                if isinstance(risk_rating_data, dict):
                    ms_rating = risk_rating_data.get('starRating')
                    risk_rating = risk_rating_data.get('riskRating')
            except Exception:
                pass
                
            try:
                financial_metrics = fund.financialMetrics()
                if isinstance(financial_metrics, dict):
                    alpha = financial_metrics.get('alpha')
                    sharpe = financial_metrics.get('sharpeRatio')
            except Exception:
                pass
                
        except Exception:
            pass

        if not holdings_str:
            try:
                fd = ticker.funds_data
                if fd and hasattr(fd, 'top_holdings') and fd.top_holdings is not None and not fd.top_holdings.empty:
                    holdings_list = fd.top_holdings.index.tolist()
                    holdings_str = ", ".join([str(h) for h in holdings_list])
                    num_holdings = len(holdings_list)
            except Exception:
                pass
            
        data = {
            'ETF_Code': code,
            'Security Name': info.get('longName', info.get('shortName', None)),
            'Beta': info.get('beta3Year', info.get('beta', None)),
            'Alpha': alpha, 
            'Sharpe Ratio (3years)': sharpe, 
            'Daily Trading Volume': info.get('volume', None),
            'Portfolio Holdings': holdings_str,
            'AUM': info.get('totalAssets', None),
            'Expense Ratio': info.get('annualReportExpenseRatio', None),
            'Current traded Price (LTP)': info.get('currentPrice', info.get('regularMarketPrice', None)),
            'Liquidity (3 month)': info.get('averageDailyVolume3Month', None),
            'Number of holdings': num_holdings,
            'Ratings - MorningStar': ms_rating,
            'Risk Rating': risk_rating,
            'ETF Category': info.get('category', None)
        }
        
        results.append(data)

    df_new = pd.DataFrame(results)
    df_new.set_index('ETF_Code', inplace=True)
    
    print(f"Saving data to: {output_filename}")
    
    if os.path.exists(output_filename):
        try:
            df_existing = pd.read_csv(output_filename)
            if 'ETF_Code' in df_existing.columns:
                df_existing.set_index('ETF_Code', inplace=True)
                df_combined = df_new.combine_first(df_existing)
            else:
                print(f"Warning: Existing output file '{output_filename}' missing 'ETF_Code' column. Overwriting file.")
                df_combined = df_new
        except PermissionError:
            print(f"Critical Error: Permission denied to read existing '{output_filename}'. Please close the file if it is open in another program.")
            sys.exit(1)
        except Exception as e:
            print(f"Error reading existing output file ({e}). Overwriting with new data.")
            df_combined = df_new
    else:
        df_combined = df_new

    df_combined.reset_index(inplace=True)
    
    columns_order = [
        'ETF_Code', 'Security Name', 'Beta', 'Alpha', 'Sharpe Ratio (3years)', 
        'Daily Trading Volume', 'Portfolio Holdings', 'AUM', 'Expense Ratio', 
        'Current traded Price (LTP)', 'Liquidity (3 month)', 'Number of holdings', 
        'Ratings - MorningStar', 'Risk Rating', 'ETF Category'
    ]
    
    for col in columns_order:
        if col not in df_combined.columns:
            df_combined[col] = None
            
    df_combined = df_combined.reindex(columns=columns_order)
    
    try:
        df_combined.to_csv(output_filename, index=False)
        print("Process completed successfully.")
    except PermissionError:
        print(f"Critical Error: Permission denied to write to '{output_filename}'. Ensure the file is not open in Excel or another program.")
        sys.exit(1)
    except OSError as e:
         print(f"Critical OS Error writing to output file: {e}")
         sys.exit(1)
    except Exception as e:
        print(f"Critical Error writing to output file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ETF Master Tracker Builder")
    parser.add_argument('-i', '--input', type=str, default=DEFAULT_INPUT_FILE, help=f'Input CSV file containing ETF codes (default: {DEFAULT_INPUT_FILE})')
    parser.add_argument('-o', '--output', type=str, default=DEFAULT_OUTPUT_FILE, help=f'Output CSV file for the Master Tracker (default: {DEFAULT_OUTPUT_FILE})')
    
    args = parser.parse_args()
    
    extract_etf_metrics(args.input, args.output)