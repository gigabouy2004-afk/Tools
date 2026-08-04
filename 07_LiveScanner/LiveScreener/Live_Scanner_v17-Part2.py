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

_TEMP_CACHE_DIR = tempfile.mkdtemp(prefix="momentum_v17_cache_")
os.environ["YFINANCE_CACHE_DIR"] = _TEMP_CACHE_DIR

def _cleanup_cache():
    if os.path.exists(_TEMP_CACHE_DIR):
        try:
            shutil.rmtree(_TEMP_CACHE_DIR)
        except Exception:
            pass

atexit.register(_cleanup_cache)

import yfinance as yf

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

def evaluate_symbol(symbol):
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=90)
    
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'))
        
        if df.empty or len(df) < 2:
            return "Insufficient Data", {"90_Day_Rolling_Return": None}
            
        start_price = float(df['Close'].iloc[0])
        end_price = float(df['Close'].iloc[-1])
        rolling_90d_return = (end_price - start_price) / start_price
        
        diagnostic = {
            "Start_Date": df.index[0].strftime('%Y-%m-%d'),
            "End_Date": df.index[-1].strftime('%Y-%m-%d'),
            "Start_Price": start_price,
            "End_Price": end_price,
            "90_Day_Rolling_Return": rolling_90d_return
        }
        return "Evaluated", diagnostic
    except Exception as e:
        return f"Error: {str(e)}", {"90_Day_Rolling_Return": None}

def parse_arguments():
    parser = argparse.ArgumentParser(description="Momentum Engine V17 Live Scanner")
    
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("-c", "--codes", nargs="+", type=str, 
                             help="Explicit list of stock tickers to evaluate.")
    input_group.add_argument("--universe", choices=["nasdaq", "nyse", "all"], type=str, 
                             help="Market universe to scan at runtime.")
    
    parser.add_argument("--live-candle-mode", choices=["completed", "developing"], 
                        default="completed", help="Current session candle evaluation mode.")
    
    default_output = os.path.join(os.getcwd(), "output", "Momentum_Review.xlsx")
    parser.add_argument("-o", "--output", type=str, default=default_output, 
                        help="Path to output workbook.")
    
    return parser.parse_args()

def generate_workbook(output_path, manifest, review_results, technical_results):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    df_summary = pd.DataFrame([manifest])
    df_review = pd.DataFrame(review_results) if review_results else pd.DataFrame(columns=["Symbol", "Status", "Message"])
    df_technical = pd.DataFrame(technical_results) if technical_results else pd.DataFrame(columns=["Symbol"])
    
    with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
        df_summary.to_excel(writer, sheet_name="Summary", index=False)
        df_review.to_excel(writer, sheet_name="Review", index=False)
        df_technical.to_excel(writer, sheet_name="Technical Data", index=False)
        
        writer.sheets["Technical Data"].hide()

def main():
    args = parse_arguments()
    
    universe_symbols = []
    if args.codes:
        universe_symbols = [c.upper() for c in args.codes]
    elif args.universe:
        print(f"Discovering universe: {args.universe.upper()}")
        universe_symbols = fetch_nasdaq_trader_universe(args.universe)
        print(f"Discovered {len(universe_symbols)} valid symbols.")
    
    manifest = {
        "execution_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "input_scope": "codes" if args.codes else f"universe_{args.universe}",
        "requested_symbols_count": len(args.codes) if args.codes else 0,
        "discovered_universe_count": len(universe_symbols) if args.universe else 0,
        "temporary_cache_dir": _TEMP_CACHE_DIR,
        "live_candle_mode": args.live_candle_mode,
        "output_path": args.output,
        "evidence_label": "CURRENT_SURVIVOR_REFERENCE_ONLY",
        "phase": "R3_Complete"
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
    print(f"Output written to {args.output}")

if __name__ == "__main__":
    main()