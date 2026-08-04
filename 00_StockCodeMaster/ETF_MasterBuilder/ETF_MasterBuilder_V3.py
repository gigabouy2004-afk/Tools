import argparse
import pandas as pd
import yfinance as yf
import os
import sys

try:
    import mstarpy as ms
except ImportError:
    print("Critical Error: The 'mstarpy' module is not installed or accessible.")
    print("Ensure you use the correct capitalization 'mstarpy' and it is installed in your current environment.")
    sys.exit(1)

DEFAULT_INPUT_FILE = 'input_etfs.csv'
DEFAULT_OUTPUT_FILE = 'output_etf_data.csv'

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
        print(f"Critical Error: Permission denied to read '{input_filename}'.")
        sys.exit(1)
    except Exception as e:
        print(f"Critical Error reading input file: {e}")
        sys.exit(1)

    results = []
    total_etfs = len(etf_codes)

    try:
        print("Initializing MorningStar Session...")
        ms_session = ms.MorningstarSession()
    except Exception as e:
        print(f"Warning: Failed to initialize MorningstarSession ({e}).")
        ms_session = None

    for idx, code in enumerate(etf_codes, 1):
        print(f"Processing {idx}/{total_etfs}: {code}")
        
        holdings_str = None
        num_holdings = None
        ms_rating = None
        risk_rating = None
        alpha = None
        beta = None
        sharpe = None
        
        # 1. MORNINGSTAR API EXTRACTION
        if ms_session:
            fund = None
            try:
                fund = ms.Funds(code, session=ms_session)
            except Exception as e:
                error_msg = str(e)
                if "Stock should be used" in error_msg or "stock" in error_msg.lower():
                    try:
                        print(f"  [Info] Routing {code} through MorningStar Stock class...")
                        fund = ms.Stock(code, session=ms_session)
                    except Exception as fallback_err:
                        print(f"  [Warning] MStarPy Stock init failed for {code}: {fallback_err}")
                else:
                    print(f"  [Warning] MStarPy Funds init failed for {code}: {e}")

            if fund:
                # A. Extract Holdings
                try:
                    holdings_df = fund.holdings(holdingType='all')
                    if holdings_df is not None and not holdings_df.empty:
                        num_holdings = len(holdings_df) 
                        top_holdings = holdings_df.head(15) 
                        if 'ticker' in top_holdings.columns:
                            holdings_list = top_holdings['ticker'].dropna().tolist()
                            holdings_str = ", ".join([str(h) for h in holdings_list if str(h).strip()])
                        elif 'securityName' in top_holdings.columns:
                            holdings_list = top_holdings['securityName'].dropna().tolist()
                            holdings_str = ", ".join([str(h) for h in holdings_list if str(h).strip()])
                except Exception:
                    pass

                # B. Extract Risk & Ratings (Often requires 3-year history)
                try:
                    risk_data = fund.riskAndRating()
                    if isinstance(risk_data, list):
                        for item in risk_data:
                            if item.get('timePeriod') == 'M36':
                                beta = item.get('beta')
                                ms_rating = item.get('starRating')
                                risk_rating = item.get('riskRating')
                                break
                    elif isinstance(risk_data, dict):
                        beta = risk_data.get('beta')
                        ms_rating = risk_data.get('starRating')
                        risk_rating = risk_data.get('riskRating')
                except Exception:
                    pass
                
                # C. Extract Financial Metrics (Primary source for Alpha/Sharpe)
                try:
                    fin_metrics = fund.financialMetrics()
                    if isinstance(fin_metrics, dict):
                        if not alpha: alpha = fin_metrics.get('alpha')
                        if not sharpe: sharpe = fin_metrics.get('sharpeRatio')
                except Exception:
                    pass

        # 2. YAHOO FINANCE API EXTRACTION (Fallback & Primary Pricing)
        ticker = yf.Ticker(code)
        try:
            info = ticker.info
        except Exception:
            info = {}
            
        # Aggressive YF Fallbacks for Risk Metrics
        if pd.isna(beta) or beta is None:
            beta = info.get('beta3Year', info.get('beta', None))
        
        if pd.isna(alpha) or alpha is None:
            alpha = info.get('fundTraits', {}).get('alpha', None)
            
        if pd.isna(sharpe) or sharpe is None:
            # YF sometimes lists this under different keys
            sharpe = info.get('threeYearAverageReturn', info.get('fundTraits', {}).get('sharpeRatio', None))
            
        # YF Fallback for Holdings
        if not holdings_str or not num_holdings:
            try:
                fd = ticker.funds_data
                if fd and hasattr(fd, 'top_holdings') and fd.top_holdings is not None and not fd.top_holdings.empty:
                    holdings_list = fd.top_holdings.index.tolist()
                    if not holdings_str:
                        holdings_str = ", ".join([str(h) for h in holdings_list])
                    if not num_holdings:
                        num_holdings = len(holdings_list)
            except Exception:
                pass
                
        # Logging for visibility on new funds
        if beta is None and alpha is None:
            print(f"  [Notice] Risk metrics (Alpha/Beta) missing for {code}. Fund likely under 3 years old.")

        # 3. Compile Data Record
        data = {
            'ETF_Code': code,
            'Security Name': info.get('longName', info.get('shortName', None)),
            'Beta': beta,
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

    # 4. Save and Merge Operations
    df_new = pd.DataFrame(results)
    df_new.set_index('ETF_Code', inplace=True)
    
    print(f"Saving data to: {output_filename}")
    
    if os.path.exists(output_filename):
        try:
            df_existing = pd.read_csv(output_filename)
            if 'ETF_Code' in df_existing.columns:
                df_existing.set_index('ETF_Code', inplace=True)
                df_combined = df_new.combine_first(df_existing)
                df_combined.update(df_new) 
            else:
                df_combined = df_new
        except PermissionError:
            print(f"Critical Error: Permission denied to read existing '{output_filename}'. Please close the file if it is open.")
            sys.exit(1)
        except Exception:
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
        print(f"Critical Error: Permission denied to write to '{output_filename}'. Ensure the file is not open in Excel.")
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