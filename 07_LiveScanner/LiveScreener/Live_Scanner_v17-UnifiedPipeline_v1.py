#!/usr/bin/env python3
"""
Momentum Engine V17 - Unified Pipeline (Baseline + Multi-Window + Tiered Classification + Technical Overlay)
Author: Architecture & Engineering
Description: Complete end-to-end scanner capturing baseline metrics, multi-window historical 
returns, three-tiered regime classifications, and technical overlays into a structured multi-tab Excel workbook.
"""

import sys
import os
import argparse
import tempfile
import atexit
import shutil
import pandas as pd
import yfinance as yf
from datetime import datetime, timezone, timedelta
import urllib.request
from io import StringIO

# ==========================================
# 0. CONFIGURABLE ENGINE PARAMETERS
# ==========================================
WINDOW_SHORT_SESSIONS = 21    # ~30 calendar days
WINDOW_MEDIUM_SESSIONS = 63   # ~90 calendar days (Primary)
WINDOW_LONG_SESSIONS = 126    # ~180 calendar days

TIER_1_THRESHOLD = 0.20       # >= +20% (Strong Bullish)
TIER_2_THRESHOLD = -0.10      # >= -10% and < +20% (Neutral / Accumulation)

# ==========================================
# 1. TEMPORARY CACHE & FOOTPRINT ISOLATION
# ==========================================
TEMP_CACHE_DIR = tempfile.mkdtemp(prefix="momentum_v17_unified_cache_")
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
    parser = argparse.ArgumentParser(
        description="Momentum Engine V17 - Unified Pipeline (Baseline, Multi-Window, Tiered Classification & Technical Overlay)"
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "-c", "--codes",
        nargs="+",
        help="Space-separated or comma-separated list of stock tickers (e.g., AAPL MSFT DELL)"
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
        "-o", "--output",
        default="Momentum_Review_Unified.xlsx",
        help="Path for the final output audit workbook"
    )

    args = parser.parse_args()
    resolved_codes = []
    
    if args.codes:
        for item in args.codes:
            for sub in item.replace(",", " ").split():
                clean_sub = sub.strip().upper()
                if clean_sub:
                    resolved_codes.append(clean_sub)
                    
    elif args.input_file:
        if not os.path.exists(args.input_file):
            print(f"[!] Critical Error: Input file '{args.input_file}' not found.")
            sys.exit(1)
        try:
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
        except Exception as e:
            print(f"[!] Critical Error reading input file: {e}")
            sys.exit(1)
            
    return args, sorted(list(set(resolved_codes)))

# ==========================================
# 3. UNIVERSE DISCOVERY ADAPTER
# ==========================================
def discover_universe(scope):
    print(f"[*] Discovering runtime equity universe for scope: [{scope.upper()}]...")
    symbols = set()
    try:
        if scope in ["nasdaq", "all"]:
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
    print(f"[+] Discovered and filtered {len(resolved)} valid equity symbols.")
    return resolved

# ==========================================
# 4. UNIFIED PIPELINE ENGINE WITH TECHNICAL OVERLAYS
# ==========================================
def run_unified_momentum_engine(symbols, output_path):
    print(f"[*] Initializing unified baseline, multi-window & technical overlay ingestion for {len(symbols)} symbols...")
    
    end_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    start_date = (datetime.now(timezone.utc) - timedelta(days=WINDOW_LONG_SESSIONS * 3)).strftime('%Y-%m-%d')
    
    try:
        raw_data = yf.download(symbols, start=start_date, end=end_date, progress=False, group_by='ticker', threads=True)
    except Exception as e:
        print(f"[!] Critical Error during bulk market data retrieval: {e}")
        sys.exit(1)

    review_records = []
    baseline_records = []
    technical_records = []
    scoring_records = []
    summary_records = []

    timestamp_utc = datetime.now(timezone.utc).isoformat()

    for symbol in symbols:
        try:
            if len(symbols) == 1:
                df = raw_data.copy()
            else:
                if symbol in raw_data.columns.levels[0]:
                    df = raw_data[symbol].copy()
                else:
                    review_records.append({"Symbol": symbol, "Status": "Failed", "Message": "Symbol not found in downloaded data"})
                    continue
            
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(-1)
                
            if 'Close' not in df.columns:
                review_records.append({"Symbol": symbol, "Status": "Failed", "Message": "Missing 'Close' column"})
                continue
                
            df = df.dropna(subset=['Close']).sort_index()
            
            if len(df) < WINDOW_SHORT_SESSIONS:
                review_records.append({"Symbol": symbol, "Status": "Rejected", "Message": f"Insufficient history (<{WINDOW_SHORT_SESSIONS} sessions)"})
                continue

            end_price = float(df['Close'].iloc[-1])
            end_date_str = str(df.index[-1].date())
            start_price_baseline = float(df['Close'].iloc[0])
            start_date_baseline = str(df.index[0].date())

            # --- Baseline Information ---
            baseline_records.append({
                "Symbol": symbol,
                "Baseline_Start_Date": start_date_baseline,
                "Baseline_Start_Price": start_price_baseline,
                "Current_Date": end_date_str,
                "Current_Price": end_price,
                "Total_Sessions_Available": len(df)
            })

            # --- Multi-Window Momentum Capture ---
            idx_short = min(WINDOW_SHORT_SESSIONS, len(df))
            start_price_short = float(df['Close'].iloc[-idx_short])
            start_date_short = str(df.index[-idx_short].date())
            ret_short = (end_price - start_price_short) / start_price_short if start_price_short else 0.0

            idx_med = min(WINDOW_MEDIUM_SESSIONS, len(df))
            start_price_med = float(df['Close'].iloc[-idx_med])
            start_date_med = str(df.index[-idx_med].date())
            ret_med = (end_price - start_price_med) / start_price_med if start_price_med else 0.0

            idx_long = min(WINDOW_LONG_SESSIONS, len(df))
            start_price_long = float(df['Close'].iloc[-idx_long])
            start_date_long = str(df.index[-idx_long].date())
            ret_long = (end_price - start_price_long) / start_price_long if start_price_long else 0.0

            # --- Phase 2 Technical Overlays (SMA & Volume) ---
            sma_50 = float(df['Close'].iloc[-50].mean()) if len(df) >= 50 else float(df['Close'].mean())
            sma_200 = float(df['Close'].iloc[-200].mean()) if len(df) >= 200 else float(df['Close'].mean())
            
            avg_vol_21 = float(df['Volume'].iloc[-21].mean()) if 'Volume' in df.columns and len(df) >= 21 else 0.0
            last_vol = float(df['Volume'].iloc[-1]) if 'Volume' in df.columns else 0.0
            vol_ratio = last_vol / avg_vol_21 if avg_vol_21 > 0 else 1.0

            technical_records.append({
                "Symbol": symbol,
                "Current_Price": end_price,
                "As_Of_Date": end_date_str,
                "Short_Window_Sessions": WINDOW_SHORT_SESSIONS,
                "Start_Date_Short": start_date_short,
                "Return_Short": ret_short,
                "Medium_Window_Sessions": WINDOW_MEDIUM_SESSIONS,
                "Start_Date_Medium": start_date_med,
                "Return_Medium": ret_med,
                "Long_Window_Sessions": WINDOW_LONG_SESSIONS,
                "Start_Date_Long": start_date_long,
                "Return_Long": ret_long,
                "SMA_50": sma_50,
                "Price_vs_SMA50_%": ((end_price - sma_50) / sma_50) * 100,
                "SMA_200": sma_200,
                "Price_vs_SMA200_%": ((end_price - sma_200) / sma_200) * 100,
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
                "Primary_Evaluation_Window": f"{WINDOW_MEDIUM_SESSIONS}-Day Rolling",
                "Primary_Return": ret_med,
                "Regime_Tier": tier,
                "Action_Bias": action,
                "Short_Return": ret_short,
                "Medium_Return": ret_med,
                "Long_Return": ret_long,
                "Multi_Window_Alignment": "Fully Aligned" if (ret_short > 0 and ret_med > 0 and ret_long > 0) else ("Mixed" if ret_med > 0 else "Bearish Alignment")
            })

            review_records.append({
                "Symbol": symbol,
                "Status": "Evaluated",
                "Message": "Successfully processed baseline, multi-window momentum, tiered classification & technical overlay"
            })

        except Exception as ex:
            review_records.append({
                "Symbol": symbol,
                "Status": "Failed",
                "Message": str(ex)
            })

    summary_records.append({
        "execution_timestamp_utc": timestamp_utc,
        "input_scope": f"{len(symbols)} symbols",
        "engine_architecture": "V17 Unified Pipeline (Baseline + Multi-Window + Tiered + Technical Overlay)",
        "window_short_sessions": WINDOW_SHORT_SESSIONS,
        "window_medium_sessions": WINDOW_MEDIUM_SESSIONS,
        "window_long_sessions": WINDOW_LONG_SESSIONS,
        "tier_1_threshold": TIER_1_THRESHOLD,
        "tier_2_threshold": TIER_2_THRESHOLD,
        "output_path": output_path
    })

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        pd.DataFrame(summary_records).to_excel(writer, sheet_name='Summary', index=False)
        pd.DataFrame(review_records).to_excel(writer, sheet_name='Review', index=False)
        pd.DataFrame(baseline_records).to_excel(writer, sheet_name='Baseline Info', index=False)
        pd.DataFrame(technical_records).to_excel(writer, sheet_name='Technical Data', index=False)
        pd.DataFrame(scoring_records).to_excel(writer, sheet_name='Scoring', index=False)

    print(f"[+] Unified pipeline execution complete. Results securely written to: {output_path}")

# ==========================================
# 5. MAIN ENTRY POINT
# ==========================================
def main():
    args, resolved_codes = parse_arguments()
    target_symbols = discover_universe(args.universe) if args.universe else resolved_codes
    if not target_symbols:
        print("[!] Error: No valid symbols resolved for execution.")
        sys.exit(1)
    run_unified_momentum_engine(target_symbols, args.output)

if __name__ == "__main__":
    main()