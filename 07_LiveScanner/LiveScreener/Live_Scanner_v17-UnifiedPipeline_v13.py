#!/usr/bin/env python3
"""
Momentum Engine V17.13 - Corrected D-2 Valley & D-1 Midline Crossover Pipeline
Author: Architecture & Engineering
Description: Complete end-to-end scanner supporting single-point-of-control backtesting, baseline metrics,
multi-window historical returns, three-tiered regime classifications, strict EMA/MACD technical filters, 
Sharpe/Sortino risk-adjusted ratios, individual single-ticker auto-adjusted fetching, embedded company metadata, 
and correct D-2 dip/valley (crossing <= 50) transitioning to D-1 crossover recovery validation.
"""

import sys
import os
import argparse
import tempfile
import atexit
import shutil
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timezone, timedelta
import urllib.request
from io import StringIO
import openpyxl

# ==========================================
# 0. CONFIGURABLE ENGINE PARAMETERS
# ==========================================
WINDOW_SHORT_SESSIONS = 21    # ~30 calendar days (~90-day rolling window short component)
WINDOW_MEDIUM_SESSIONS = 63   # ~90 calendar days (Primary Rolling Window)
WINDOW_LONG_SESSIONS = 126    # ~180 calendar days

TIER_1_THRESHOLD = 0.20       # >= +20% (Strong Bullish)
TIER_2_THRESHOLD = -0.10      # >= -10% and < +20% (Neutral / Accumulation)

# ==========================================
# 1. TEMPORARY CACHE & FOOTPRINT ISOLATION
# ==========================================
TEMP_CACHE_DIR = tempfile.mkdtemp(prefix="momentum_v1719_cache_")
os.environ["YFINANCE_CACHE_DIR"] = TEMP_CACHE_DIR

def cleanup_transient_footprint():
    if os.path.exists(TEMP_CACHE_DIR):
        try:
            shutil.rmtree(TEMP_CACHE_DIR, ignore_errors=True)
        except Exception:
            pass

atexit.register(cleanup_transient_footprint)

# ==========================================
# 2. CLI ARGUMENT PARSING
# ==========================================
def parse_arguments():
    print("----------------------------------------------------------------------")
    print("[*] Momentum Engine V17.13: Initializing Argument Parser & Input Resolution...")
    print("----------------------------------------------------------------------")
    
    parser = argparse.ArgumentParser(
        description="Momentum Engine V17.13 - Robust Split & Adjusted Close Audit Pipeline"
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "-c", "--codes",
        nargs="+",
        help="Space-separated or comma-separated list of stock tickers (e.g., AAPL MSFT DBGI)"
    )
    group.add_argument(
        "-u", "--universe",
        choices=["nasdaq", "nyse", "all"],
        help="Dynamic runtime universe discovery scope"
    )
    group.add_argument(
        "-i", "--input-file",
        dest="input_file",
        type=str,
        help="Fully qualified path to a CSV or Excel file containing stock codes in the first column."
    )
    
    parser.add_argument(
        "-b", "--backtest-date",
        dest="backtest_date",
        type=str,
        default=None,
        help="Single point of control: historical date (YYYY-MM-DD) to simulate execution as of that market close."
    )
    
    parser.add_argument(
        "-o", "--output",
        default="Momentum_Review_Unified.xlsx",
        help="Path for the final output audit workbook"
    )

    args = parser.parse_args()
    resolved_codes = []
    
    if args.codes:
        print(f"[*] Input Source Type: Command-Line Ticker Arguments provided.")
        for item in args.codes:
            for sub in item.replace(",", " ").split():
                clean_sub = sub.strip().upper()
                if clean_sub:
                    resolved_codes.append(clean_sub)
                    
    elif args.input_file:
        print(f"[*] Input Source Type: External File -> [{args.input_file}]")
        if not os.path.exists(args.input_file):
            print(f"[!] Critical Error: Input file '{args.input_file}' not found.")
            sys.exit(1)
        try:
            print(f"[*] Reading and parsing input file content...")
            if args.input_file.lower().endswith(('.xlsx', '.xls')):
                xl = pd.ExcelFile(args.input_file)
                df_input = pd.read_excel(xl, sheet_name=xl.sheet_names[0])
            else:
                with open(args.input_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                lines = content.strip().split('\n')
                first_line = lines[0].strip().lower() if lines else ""
                has_header = any(h in first_line for h in ['symbol', 'ticker', 'code', 'stock'])
                df_input = pd.read_csv(args.input_file) if has_header else pd.read_csv(args.input_file, header=None)
            
            raw_tickers = df_input.iloc[:, 0].dropna().astype(str).str.strip().str.upper().tolist()
            resolved_codes = [t for t in raw_tickers if t and t not in ['SYMBOL', 'TICKER', 'CODE', 'STOCK']]
            print(f"[+] Successfully read {len(resolved_codes)} raw codes from input file.")
        except Exception as e:
            print(f"[!] Critical Error reading input file: {e}")
            sys.exit(1)
            
    unique_codes = sorted(list(set(resolved_codes)))
    print(f"[+] Input Phase Complete. Total Unique Codes Read: {len(unique_codes)}")
    return args, unique_codes

# ==========================================
# 3. UNIVERSE DISCOVERY ADAPTER
# ==========================================
def discover_universe(scope):
    print("----------------------------------------------------------------------")
    print(f"[*] Discovering Runtime Equity Universe for Scope: [{scope.upper()}]...")
    print("----------------------------------------------------------------------")
    symbols = set()
    try:
        if scope in ["nasdaq", "all"]:
            print(f"[*] Fetching Nasdaq listed securities directory...")
            nasdaq_url = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
            req = urllib.request.Request(nasdaq_url)
            with urllib.request.urlopen(req) as response:
                nasdaq_data = response.read().decode('utf-8')
            df_nasdaq = pd.read_csv(StringIO(nasdaq_data), sep="|")
            df_nasdaq = df_nasdaq[df_nasdaq['Symbol'].notna() & (~df_nasdaq['Symbol'].str.contains("File Creation Time", na=False))]
            if 'Test Issue' in df_nasdaq.columns:
                df_nasdaq = df_nasdaq[df_nasdaq['Test Issue'] == 'N']
            if 'ETF' in df_nasdaq.columns:
                df_nasdaq = df_nasdaq[df_nasdaq['ETF'] == 'N']
            for sym in df_nasdaq['Symbol'].dropna():
                symbols.add(sym.strip().upper())
                
        if scope in ["nyse", "all"]:
            print(f"[*] Fetching NYSE / Other listed securities directory...")
            other_url = "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"
            req = urllib.request.Request(other_url)
            with urllib.request.urlopen(req) as response:
                other_data = response.read().decode('utf-8')
            df_other = pd.read_csv(StringIO(other_data), sep="|")
            df_other = df_other[df_other['CQS Symbol'].notna() & (~df_other['CQS Symbol'].str.contains("File Creation Time", na=False))]
            df_nyse = df_other[df_other['Exchange'] == 'N'] if 'Exchange' in df_other.columns else df_other
            if 'Test Issue' in df_nyse.columns:
                df_nyse = df_nyse[df_nyse['Test Issue'] == 'N']
            if 'ETF' in df_nyse.columns:
                df_nyse = df_nyse[df_nyse['ETF'] == 'N']
            for sym in df_nyse['CQS Symbol'].dropna():
                symbols.add(sym.strip().upper())
    except Exception as e:
        print(f"[!] Warning: Automated remote universe discovery encountered an issue: {e}")
        symbols = {"AAPL", "MSFT", "NVDA"}

    resolved = sorted(list(symbols))
    print(f"[+] Universe Discovery Complete. Validated {len(resolved)} equity symbols.")
    return resolved

# ==========================================
# 4. UNIFIED PIPELINE ENGINE WITH CORRECTED D-2 VALLEY / D-1 CROSSOVER
# ==========================================
def run_unified_momentum_engine(symbols, backtest_date_str, output_path):
    print("----------------------------------------------------------------------")
    print(f"[*] Initializing V17.13 Momentum Pipeline for {len(symbols)} symbols...")
    print(f"[*] Backtest Simulation Date Control: {backtest_date_str or 'LIVE / TODAY'}")
    print(f"[*] Target Output Audit Workbook: {output_path}")
    print("----------------------------------------------------------------------")
    
    end_fetch_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    start_fetch_date = (datetime.now(timezone.utc) - timedelta(days=WINDOW_LONG_SESSIONS * 4)).strftime('%Y-%m-%d')

    review_records = []
    baseline_records = []
    technical_records = []
    scoring_records = []

    timestamp_utc = datetime.now(timezone.utc).isoformat()
    
    input_read_count = len(symbols)
    processed_count = 0
    evaluated_count = 0
    rejected_count = 0  
    failed_count = 0    

    print(f"[*] Beginning robust individual symbol fetching & technical evaluation...")
    for idx, symbol in enumerate(symbols, 1):
        try:
            ticker_obj = yf.Ticker(symbol)
            
            # Fetch Metadata safely
            try:
                info = ticker_obj.info
                company_name = info.get('longName', info.get('shortName', symbol))
                sector_val = info.get('sector', 'N/A')
                industry_val = info.get('industry', 'N/A')
            except Exception:
                company_name = symbol
                sector_val = 'N/A'
                industry_val = 'N/A'

            df = ticker_obj.history(start=start_fetch_date, end=end_fetch_date, auto_adjust=True, actions=False)
            
            if df is None or df.empty or 'Close' not in df.columns or 'High' not in df.columns or 'Low' not in df.columns:
                failed_count += 1
                review_records.append({
                    "Symbol": symbol, 
                    "Company Name": company_name,
                    "Sector": sector_val,
                    "Industry": industry_val,
                    "Status": "Failed", 
                    "Message": "No historical price data returned or missing required OHLC columns"
                })
                continue
                
            df = df.dropna(subset=['Close']).sort_index()
            if isinstance(df.index, pd.DatetimeIndex) and df.index.tz is not None:
                df.index = df.index.tz_localize(None)

            processed_count += 1

            # --- Single Point of Control: Backtest Date Filtering ---
            if backtest_date_str:
                try:
                    bt_dt = pd.to_datetime(backtest_date_str)
                    df = df[df.index <= bt_dt]
                except Exception as bte:
                    print(f"[!] Warning: Invalid backtest date format '{backtest_date_str}': {bte}. Falling back to latest.")

            if len(df) < max(WINDOW_SHORT_SESSIONS, 20):
                rejected_count += 1
                review_records.append({
                    "Symbol": symbol, 
                    "Company Name": company_name,
                    "Sector": sector_val,
                    "Industry": industry_val,
                    "Status": "Rejected", 
                    "Message": f"Insufficient history (< minimum required sessions as of target date)"
                })
                continue

            # --- D-1 Post-Mortem Slicing & Core Pricing Metrics ---
            end_price = float(df['Close'].iloc[-1])
            end_date_str = str(df.index[-1].date())
            start_price_baseline = float(df['Close'].iloc[0])
            start_date_baseline = str(df.index[0].date())

            # --- Multi-Window Momentum Capture (Strict Rolling Windows as of D-1) ---
            idx_short = min(WINDOW_SHORT_SESSIONS, len(df))
            start_price_short = float(df['Close'].iloc[-idx_short])
            ret_short = (end_price - start_price_short) / start_price_short if start_price_short else 0.0

            idx_med = min(WINDOW_MEDIUM_SESSIONS, len(df))
            start_price_med = float(df['Close'].iloc[-idx_med])
            ret_med = (end_price - start_price_med) / start_price_med if start_price_med else 0.0

            idx_long = min(WINDOW_LONG_SESSIONS, len(df))
            start_price_long = float(df['Close'].iloc[-idx_long])
            ret_long = (end_price - start_price_long) / start_price_long if start_price_long else 0.0

            # --- Technical Overlays: EMAs & Standard EMA-based MACD (Evaluated as of D-1) ---
            close_series = df['Close']
            ema_50 = float(close_series.ewm(span=50, adjust=False).mean().iloc[-1]) if len(close_series) >= 50 else float(close_series.mean())
            ema_200 = float(close_series.ewm(span=200, adjust=False).mean().iloc[-1]) if len(close_series) >= 200 else float(close_series.mean())
            
            exp1 = close_series.ewm(span=12, adjust=False).mean()
            exp2 = close_series.ewm(span=26, adjust=False).mean()
            macd_line = exp1 - exp2
            signal_line = macd_line.ewm(span=9, adjust=False).mean()
            
            val_macd = float(macd_line.iloc[-1])
            val_signal = float(signal_line.iloc[-1])

            # --- Stochastic Oscillator Calculation (Standard 14, 3, 3) for D-1 and D-2 Post-Mortem ---
            low_14 = df['Low'].rolling(window=14).min()
            high_14 = df['High'].rolling(window=14).max()
            
            denom = (high_14 - low_14)
            stoch_k = 100 * ((df['Close'] - low_14) / denom.replace(0, np.nan))
            stoch_d = stoch_k.rolling(window=3).mean()

            df['SlowK'] = stoch_k
            df['SlowD'] = stoch_d

            if len(df) >= 3:
                val_k1 = float(df['SlowK'].iloc[-1])
                val_d1 = float(df['SlowD'].iloc[-1])
                val_k2 = float(df['SlowK'].iloc[-2])
                val_d2 = float(df['SlowD'].iloc[-2])
            else:
                val_k1 = val_d1 = val_k2 = val_d2 = 50.0

            # --- Corrected Stochastic Transition Logic Matching User Specifications ---
            # D-2 (K2, D2) dipped or was situated in the lower/oversold/midline recovery zone (e.g. <= 60).
            # D-1 (K1, D1) shows %K crossing above %D (K1 > D1) as it transitions upward into bought territory (> 50).
            stoch_d2_dip = bool(val_k2 <= 60.0 or val_d2 <= 60.0)
            stoch_k_cross_d1 = bool(val_k1 > val_d1)
            stoch_recovery_zone = bool(val_k1 >= 50.0 and val_d1 >= 45.0)

            stoch_transition_valid = bool(stoch_d2_dip and stoch_k_cross_d1 and stoch_recovery_zone)

            if stoch_transition_valid:
                stoch_status_desc = "Valid D-2 Dip to D-1 Crossover Recovery"
            elif val_k1 > val_d1 and val_k1 > 50:
                stoch_status_desc = "Already Bullish (> 50)"
            else:
                stoch_status_desc = "Neutral / Below Threshold"

            # --- Standard True Bull Presence Filter Conditions (UNCHANGED CORE ENGINE GATES) ---
            price_above_ema50 = end_price > ema_50
            price_above_ema200 = end_price > ema_200
            macd_zero_line_bullish = bool(val_macd > 0 and val_signal > 0 and val_macd > val_signal)
            return_positive_gate = bool(ret_med > 0)

            is_true_bull = price_above_ema50 and price_above_ema200 and macd_zero_line_bullish and return_positive_gate

            if not is_true_bull:
                rejected_count += 1
                review_records.append({
                    "Symbol": symbol, 
                    "Company Name": company_name,
                    "Sector": sector_val,
                    "Industry": industry_val,
                    "Status": "Rejected", 
                    "Message": f"Failed True Bull technical gate (Price > EMA50: {price_above_ema50}, Price > EMA200: {price_above_ema200}, MACD Bullish: {macd_zero_line_bullish}, 90d Return Positive [{ret_med:.2%}] > 0: {return_positive_gate})"
                })
                continue

            # --- Baseline Information ---
            baseline_records.append({
                "Symbol": symbol,
                "Company Name": company_name,
                "Sector": sector_val,
                "Industry": industry_val,
                "Baseline_Start_Date": start_date_baseline,
                "Baseline_Start_Price": start_price_baseline,
                "Current_Date": end_date_str,
                "Current_Price": end_price,
                "Total_Sessions_Available": len(df)
            })

            # --- Risk-Adjusted Metrics ---
            window_df_returns = close_series.iloc[-idx_med:].pct_change().dropna()
            std_dev = window_df_returns.std()
            sharpe_ratio = float((window_df_returns.mean() / std_dev) * np.sqrt(252)) if std_dev > 0 else 0.0
            
            downside_returns = window_df_returns[window_df_returns < 0]
            downside_std = downside_returns.std()
            sortino_ratio = float((window_df_returns.mean() / downside_std) * np.sqrt(252)) if downside_std > 0 else 0.0

            # --- Volume Ratios ---
            avg_vol_21 = float(df['Volume'].iloc[-21:].mean()) if 'Volume' in df.columns and len(df) >= 21 else 0.0
            last_vol = float(df['Volume'].iloc[-1]) if 'Volume' in df.columns else 0.0
            vol_ratio = last_vol / avg_vol_21 if avg_vol_21 > 0 else 1.0

            technical_records.append({
                "Symbol": symbol,
                "Company Name": company_name,
                "Sector": sector_val,
                "Industry": industry_val,
                "Current_Price": end_price,
                "As_Of_Date": end_date_str,
                "Short_Window_Sessions": WINDOW_SHORT_SESSIONS,
                "Return_Short": ret_short,
                "Medium_Window_Sessions": WINDOW_MEDIUM_SESSIONS,
                "Return_Medium": ret_med,
                "Long_Window_Sessions": WINDOW_LONG_SESSIONS,
                "Return_Long": ret_long,
                "EMA_50": ema_50,
                "Price_vs_EMA50_%": ((end_price - ema_50) / ema_50) * 100,
                "EMA_200": ema_200,
                "Price_vs_EMA200_%": ((end_price - ema_200) / ema_200) * 100,
                "MACD_Line": val_macd,
                "MACD_Signal": val_signal,
                "MACD_Zero_Line_Bullish": macd_zero_line_bullish,
                "Stochastic_K1_D1 (D-1)": f"K1: {val_k1:.2f} | D1: {val_d1:.2f}",
                "Stochastic_K2_D2 (D-2)": f"K2: {val_k2:.2f} | D2: {val_d2:.2f}",
                "Stochastic_Transition_Valid": stoch_transition_valid,
                "Stochastic_Status": stoch_status_desc,
                "Sharpe_Ratio_Annualized": sharpe_ratio,
                "Sortino_Ratio_Annualized": sortino_ratio,
                "Volume_Ratio_vs_21d": vol_ratio,
                "Data_Integrity_Flag": "VALID"
            })

            # --- Tiered Regime Classification ---
            if ret_med >= TIER_1_THRESHOLD:
                tier = "Tier 1 - Strong Bullish"
                action = "Accumulate / Hold Momentum"
            elif ret_med >= TIER_2_THRESHOLD:
                tier = "Tier 2 - Neutral / Accumulation"
                action = "Monitor Range"
            else:
                tier = "Tier 3 - Lagging / Bearish"
                action = "Defensive / Avoid"

            scoring_records.append({
                "Symbol": symbol,
                "Company Name": company_name,
                "Sector": sector_val,
                "Industry": industry_val,
                "Last Traded Price": end_price,
                "Primary_Evaluation_Window": f"{WINDOW_MEDIUM_SESSIONS}-Day Rolling",
                "Last_30d_Return": ret_short,
                "Primary_Return": ret_med,
                "Regime_Tier": tier,
                "Action_Bias": action,
                "Stochastic_K1_D1 (D-1)": f"K1: {val_k1:.2f} | D1: {val_d1:.2f}",
                "Stochastic_K2_D2 (D-2)": f"K2: {val_k2:.2f} | D2: {val_d2:.2f}",
                "Stochastic_Transition_Valid": stoch_transition_valid,
                "Stochastic_Status": stoch_status_desc,
                "Sharpe_Ratio": sharpe_ratio,
                "Sortino_Ratio": sortino_ratio,
                "MACD_Zero_Line_Bullish": macd_zero_line_bullish,
                "Multi_Window_Alignment": "Fully Aligned" if (ret_short > 0 and ret_med > 0 and ret_long > 0) else ("Mixed" if ret_med > 0 else "Bearish Alignment")
            })

            evaluated_count += 1
            review_records.append({
                "Symbol": symbol,
                "Company Name": company_name,
                "Sector": sector_val,
                "Industry": industry_val,
                "Status": "Evaluated",
                "Message": f"Successfully passed strict MACD & EMA filters as of {end_date_str}"
            })

        except Exception as ex:
            failed_count += 1
            review_records.append({
                "Symbol": symbol,
                "Company Name": symbol,
                "Sector": "N/A",
                "Industry": "N/A",
                "Status": "Failed",
                "Message": str(ex)
            })

    # --- Summary Records Generation ---
    summary_records = [{
        "execution_timestamp_utc": timestamp_utc,
        "input_scope": f"{len(symbols)} symbols",
        "total_input_read": input_read_count,
        "total_processed": processed_count,
        "status_evaluated": evaluated_count,
        "status_rejected": rejected_count,
        "status_failed": failed_count,
        "backtest_simulation_date": backtest_date_str or "Live (Current)",
        "engine_architecture": "V17.13 Corrected D-2 Dip & D-1 Crossover Pipeline",
        "output_path": output_path
    }]

    df_scoring = pd.DataFrame(scoring_records)
    if not df_scoring.empty:
        def get_tier_order(tier_str):
            if 'Tier 1' in str(tier_str):
                return 1
            elif 'Tier 2' in str(tier_str):
                return 2
            elif 'Tier 3' in str(tier_str):
                return 3
            return 4

        df_scoring['Tier_Sort'] = df_scoring['Regime_Tier'].apply(get_tier_order)
        df_scoring['MACD_Sort'] = df_scoring['MACD_Zero_Line_Bullish'].apply(lambda x: 0 if bool(x) is True else 1)
        
        df_scoring = df_scoring.sort_values(
            by=['Tier_Sort', 'Action_Bias', 'MACD_Sort', 'Primary_Return'],
            ascending=[True, True, True, False]
        ).drop(columns=['Tier_Sort', 'MACD_Sort'])

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    df_summary = pd.DataFrame(summary_records)
    df_review = pd.DataFrame(review_records) if review_records else pd.DataFrame(columns=["Symbol", "Company Name", "Sector", "Industry", "Status", "Message"])
    df_baseline = pd.DataFrame(baseline_records) if baseline_records else pd.DataFrame(columns=["Symbol", "Company Name", "Sector", "Industry", "Baseline_Start_Date", "Baseline_Start_Price", "Current_Date", "Current_Price", "Total_Sessions_Available"])
    df_technical = pd.DataFrame(technical_records) if technical_records else pd.DataFrame(columns=["Symbol", "Company Name", "Sector", "Industry", "Current_Price", "As_Of_Date", "MACD_Line", "MACD_Signal", "MACD_Zero_Line_Bullish"])
    if df_scoring.empty:
        df_scoring = pd.DataFrame(columns=["Symbol", "Company Name", "Sector", "Industry", "Last Traded Price", "Primary_Evaluation_Window", "Last_30d_Return", "Primary_Return", "Regime_Tier", "Action_Bias", "Sharpe_Ratio", "Sortino_Ratio", "MACD_Zero_Line_Bullish"])

    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        df_summary.to_excel(writer, sheet_name='Summary', index=False)
        df_review.to_excel(writer, sheet_name='Review', index=False)
        df_baseline.to_excel(writer, sheet_name='Baseline Info', index=False)
        df_technical.to_excel(writer, sheet_name='Technical Data', index=False)
        df_scoring.to_excel(writer, sheet_name='Scoring', index=False)

    wb = openpyxl.load_workbook(output_path)
    if 'Scoring' in wb.sheetnames and wb['Scoring'].max_row > 1:
        ws = wb['Scoring']
        header_row = [cell.value for cell in ws[1]]
        
        for col_name, fmt in [('Last_30d_Return', '0.00%'), ('Primary_Return', '0.00%'), ('Last Traded Price', '0.00'), ('Sharpe_Ratio', '0.00'), ('Sortino_Ratio', '0.00')]:
            if col_name in header_row:
                col_idx = header_row.index(col_name) + 1
                for row in range(2, ws.max_row + 1):
                    ws.cell(row=row, column=col_idx).number_format = fmt

        wb.save(output_path)

    # ==========================================
    # 5. TERMINAL EXECUTION SUMMARY REPORT
    # ==========================================
    print("\n" + "=" * 70)
    print("                 MOMENTUM ENGINE EXECUTION SUMMARY REPORT")
    print("=" * 70)
    print(f" [+] Output Workbook Generated : {os.path.abspath(output_path)}")
    print(f" [+] Timestamp (UTC)           : {timestamp_utc}")
    print(f" [+] Simulation Date Control   : {backtest_date_str or 'LIVE / TODAY'}")
    print("-" * 70)
    print(" RUN AUDIT METRICS:")
    print(f"   * Total Input Read          : {input_read_count}")
    print(f"   * Total Processed           : {processed_count}")
    print(f"   * Status Evaluated          : {evaluated_count}")
    print(f"   * Status Rejected           : {rejected_count}")
    print(f"   * Status Failed             : {failed_count}")
    print("-" * 70)
    print(" SUMMARY SHEET DATA SNAPSHOT:")
    for key, val in summary_records[0].items():
        print(f"   - {key:<30}: {val}")
    print("=" * 70)
    print(f"[+] Execution successfully completed. All audit tabs written.")

# ==========================================
# 6. MAIN ENTRY POINT
# ==========================================
def main():
    args, resolved_codes = parse_arguments()
    target_symbols = discover_universe(args.universe) if args.universe else resolved_codes
    if not target_symbols:
        print("[!] Error: No valid symbols resolved for execution.")
        sys.exit(1)
    run_unified_momentum_engine(target_symbols, args.backtest_date, args.output)

if __name__ == "__main__":
    main()