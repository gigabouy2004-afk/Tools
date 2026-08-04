import argparse
import os
import sys
import tempfile
import shutil
import atexit
from datetime import datetime, timezone, timedelta
import pandas as pd
import urllib.request
from io import StringIO

# -----------------------------------------------------------------------------
# Pre-Flight Output Accessibility Check
# -----------------------------------------------------------------------------
def verify_output_accessibility(output_path):
    """
    Validates that the target output directory is writable and the file 
    can be opened for writing before wasting CPU/network time on scans.
    """
    abs_path = os.path.abspath(output_path)
    directory = os.path.dirname(abs_path)
    
    try:
        os.makedirs(directory, exist_ok=True)
    except Exception as e:
        print(f"[CRITICAL ERROR] Cannot create output directory '{directory}': {e}")
        sys.exit(1)
        
    try:
        with open(abs_path, 'a'):
            pass
    except IOError as e:
        print(f"[CRITICAL ERROR] Output file '{abs_path}' is locked or not writable. Please close the file if it is open in Excel: {e}")
        sys.exit(1)

# -----------------------------------------------------------------------------
# Dynamic Cache Allocation & Threshold Logic
# -----------------------------------------------------------------------------
def initialize_cache(cache_arg, symbol_count):
    THRESHOLD_BULK = 5
    
    if cache_arg:
        target_dir = os.path.abspath(cache_arg)
        try:
            os.makedirs(target_dir, exist_ok=True)
            test_file = os.path.join(target_dir, ".write_test")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            os.environ["YFINANCE_CACHE_DIR"] = target_dir
            return target_dir, "User-Provided Writable Cache"
        except Exception as e:
            print(f"[CRITICAL ERROR] Provided cache directory '{target_dir}' is not writable: {e}")
            sys.exit(1)
            
    if symbol_count > THRESHOLD_BULK:
        print(f"[CRITICAL ERROR] Symbol count ({symbol_count}) exceeds threshold ({THRESHOLD_BULK}).")
        print("Bulk or sector scans require a designated writable cache directory.")
        print("Please provide a path using the --cache-dir argument.")
        sys.exit(1)
    else:
        temp_dir = tempfile.mkdtemp(prefix="momentum_v17_memory_cache_")
        os.environ["YFINANCE_CACHE_DIR"] = temp_dir
        return temp_dir, "In-Memory / Isolated Temp Cache"

def cleanup_cache(cache_dir, mode):
    if mode == "In-Memory / Isolated Temp Cache" and os.path.exists(cache_dir):
        try:
            shutil.rmtree(cache_dir)
        except Exception:
            pass

# -----------------------------------------------------------------------------
# Runtime Universe Adapter
# -----------------------------------------------------------------------------
def fetch_nasdaq_trader_universe(target_universe="all"):
    nasdaq_url = "ftp://ftp.nasdaqtrader.com/symboldirectory/nasdaqlisted.txt"
    other_url = "ftp://ftp.nasdaqtrader.com/symboldirectory/otherlisted.txt"
    
    symbols = []
    
    if target_universe in ["nasdaq", "all"]:
        try:
            req = urllib.request.Request(nasdaq_url)
            with urllib.request.urlopen(req) as response:
                nasdaq_data = response.read().decode('utf-8')
            df_nasdaq = pd.read_csv(StringIO(nasdaq_data), sep="|")
            df_nasdaq = df_nasdaq[
                (df_nasdaq['Test Issue'] == 'N') & 
                (df_nasdaq['ETF'] == 'N')
            ]
            symbols.extend(df_nasdaq['Symbol'].dropna().tolist())
        except Exception:
            pass
            
    if target_universe in ["nyse", "all"]:
        try:
            req = urllib.request.Request(other_url)
            with urllib.request.urlopen(req) as response:
                other_data = response.read().decode('utf-8')
            df_other = pd.read_csv(StringIO(other_data), sep="|")
            df_other = df_other[
                (df_other['Test Issue'] == 'N') & 
                (df_other['ETF'] == 'N') &
                (df_other['Exchange'] == 'N')
            ]
            symbols.extend(df_other['NASDAQ Symbol'].dropna().tolist())
        except Exception:
            pass
            
    symbols = [str(s).strip() for s in symbols if isinstance(s, str) and len(str(s).strip()) > 0]
    symbols = [s for s in symbols if not s.startswith("File Creation Time")]
    
    return sorted(list(set(symbols)))

# -----------------------------------------------------------------------------
# Tier 2: Strict D-1 Session Intraday Calculation
# -----------------------------------------------------------------------------
def fetch_previous_session_intraday(ticker_obj):
    try:
        df_intraday = ticker_obj.history(period="5d", interval="60m")
        if df_intraday.empty:
            return "Insufficient Intraday Data", None
            
        if isinstance(df_intraday.columns, pd.MultiIndex):
            df_intraday.columns = df_intraday.columns.get_level_values(0)
            
        df_intraday.index = pd.to_datetime(df_intraday.index)
        unique_dates = df_intraday.index.normalize().unique()
        
        if len(unique_dates) < 2:
            return "Insufficient Session History", None
            
        d_minus_1_date = unique_dates[-2] if unique_dates[-1].date() == datetime.now(timezone.utc).date() else unique_dates[-1]
        df_d1 = df_intraday[df_intraday.index.normalize() == d_minus_1_date]
        
        if df_d1.empty or len(df_d1) < 2:
            return "Insufficient D-1 Intraday Bars", None
            
        session_open = float(df_d1['Open'].iloc[0])
        session_close = float(df_d1['Close'].iloc[-1])
        
        if session_open == 0:
            return "Invalid Zero Open Price", None
            
        d1_return = (session_close - session_open) / session_open
        return "Success", d1_return
        
    except Exception as e:
        err_msg = str(e).lower()
        if "too many requests" in err_msg or "rate limit" in err_msg or "429" in err_msg:
            print(f"[HALT] Data Provider Rate-Limit Block Detected: {e}")
            sys.exit(2)
        return f"Intraday Error: {str(e)}", None

# -----------------------------------------------------------------------------
# Tier 1: Performance Evaluation & Strict D-1 Tail-Anchoring
# -----------------------------------------------------------------------------
def evaluate_symbol(symbol):
    now_utc = datetime.now(timezone.utc)
    d_minus_1 = now_utc - timedelta(days=1)
    start_date = d_minus_1 - timedelta(days=90)
    
    diagnostic = {
        "Start_Date": None,
        "End_Date": None,
        "Start_Price": None,
        "End_Price": None,
        "90_Day_Rolling_Return": None,
        "Daily_Qualified": False,
        "D1_Intraday_Return": "Uncalculated",
        "Data_Integrity_Flag": "VALID"
    }
    
    import yfinance as yf
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start_date.strftime('%Y-%m-%d'), end=(d_minus_1 + timedelta(days=1)).strftime('%Y-%m-%d'))
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        if df.empty or len(df) < 2:
            diagnostic["Data_Integrity_Flag"] = "INSUFFICIENT_DATA"
            return "Insufficient Daily Data", diagnostic
            
        if df['Close'].isnull().any() or (df['Volume'] == 0).all():
            diagnostic["Data_Integrity_Flag"] = "CORRUPT_DATA_REJECTED"
            return "Corrupt Data Flagged", diagnostic
            
        start_price = float(df['Close'].iloc[0])
        end_price = float(df['Close'].iloc[-1])
        rolling_90d_return = (end_price - start_price) / start_price
        
        diagnostic.update({
            "Start_Date": df.index[0].strftime('%Y-%m-%d'),
            "End_Date": df.index[-1].strftime('%Y-%m-%d'),
            "Start_Price": start_price,
            "End_Price": end_price,
            "90_Day_Rolling_Return": rolling_90d_return
        })
        
        if rolling_90d_return > 0:
            diagnostic["Daily_Qualified"] = True
            intraday_status, d1_return = fetch_previous_session_intraday(ticker)
            if d1_return is not None:
                diagnostic["D1_Intraday_Return"] = d1_return
            else:
                diagnostic["D1_Intraday_Return"] = intraday_status
                
        return "Evaluated", diagnostic
    except Exception as e:
        err_msg = str(e).lower()
        if "too many requests" in err_msg or "rate limit" in err_msg or "429" in err_msg:
            print(f"[HALT] Data Provider Rate-Limit Block Detected: {e}")
            sys.exit(2)
        diagnostic["Data_Integrity_Flag"] = "EXCEPTION_ERROR"
        return f"Error: {str(e)}", diagnostic

# -----------------------------------------------------------------------------
# Argument Parsing with Robust Comma/Space Input Support
# -----------------------------------------------------------------------------
def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Momentum Engine V17 Live Scanner",
        epilog="Examples:\n  python script.py -c AAPL MU MSFT\n  python script.py -c AAPL,MU,MSFT\n  python script.py --universe nasdaq"
    )
    
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("-c", "--codes", nargs="+", type=str, 
                             help="Explicit list of stock tickers (space or comma separated).")
    input_group.add_argument("--universe", choices=["nasdaq", "nyse", "all"], type=str, 
                             help="Market universe to scan at runtime.")
    
    parser.add_argument("--cache-dir", type=str, default=None,
                        help="Explicit writable path for provider cache (required for bulk/universe scans).")
    parser.add_argument("--live-candle-mode", choices=["completed", "developing"], 
                        default="completed", help="Current session candle evaluation mode.")
    
    default_output = os.path.join(os.getcwd(), "output", "Momentum_Review.xlsx")
    parser.add_argument("-o", "--output", type=str, default=default_output, 
                        help="Path to output workbook.")
    
    args = parser.parse_args()
    
    # Robustly parse codes whether passed as space-separated or comma-separated items
    processed_codes = []
    if args.codes:
        for item in args.codes:
            # Split by comma in case user passed comma-separated string(s)
            split_items = item.replace(",", " ").split()
            for code in split_items:
                clean_code = code.strip().upper()
                if clean_code:
                    processed_codes.append(clean_code)
        args.codes = processed_codes
        
    return args

# -----------------------------------------------------------------------------
# User-Facing Output Contract
# -----------------------------------------------------------------------------
def generate_workbook(output_path, manifest, review_results, technical_results):
    df_summary = pd.DataFrame([manifest])
    df_review = pd.DataFrame(review_results) if review_results else pd.DataFrame(columns=["Symbol", "Status", "Message"])
    df_technical = pd.DataFrame(technical_results) if technical_results else pd.DataFrame(columns=["Symbol"])
    
    with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
        df_summary.to_excel(writer, sheet_name="Summary", index=False)
        df_review.to_excel(writer, sheet_name="Review", index=False)
        df_technical.to_excel(writer, sheet_name="Technical Data", index=False)
        
        writer.sheets["Technical Data"].hide()

# -----------------------------------------------------------------------------
# Main Orchestration
# -----------------------------------------------------------------------------
def main():
    args = parse_arguments()
    
    # PRE-FLIGHT CHECK: Verify output file is accessible and writable before doing any work
    verify_output_accessibility(args.output)
    
    universe_symbols = []
    if args.codes:
        universe_symbols = args.codes
    elif args.universe:
        print(f"Discovering universe: {args.universe.upper()}")
        universe_symbols = fetch_nasdaq_trader_universe(args.universe)
        print(f"Discovered {len(universe_symbols)} valid symbols.")
        
    symbol_count = len(universe_symbols)
    cache_path, cache_mode = initialize_cache(args.cache_dir, symbol_count)
    atexit.register(lambda: cleanup_cache(cache_path, cache_mode))
    
    manifest = {
        "execution_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "input_scope": "codes" if args.codes else f"universe_{args.universe}",
        "requested_symbols_count": symbol_count,
        "cache_allocation_mode": cache_mode,
        "cache_directory_path": cache_path,
        "live_candle_mode": args.live_candle_mode,
        "output_path": args.output,
        "evidence_label": "CURRENT_SURVIVOR_REFERENCE_ONLY",
        "phase": "R8_Complete"
    }
    
    review_results = []
    technical_results = []
    
    for symbol in universe_symbols:
        status, diagnostics = evaluate_symbol(symbol)
        review_results.append({
            "Symbol": symbol,
            "Status": "Evaluated" if status == "Evaluated" else "Failed",
            "Message": status
        })
        
        tech_data = {"Symbol": symbol}
        tech_data.update(diagnostics)
        technical_results.append(tech_data)
        
    generate_workbook(args.output, manifest, review_results, technical_results)
    print(f"Output successfully written to {args.output}")

if __name__ == "__main__":
    main()