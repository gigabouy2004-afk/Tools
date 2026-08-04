import contextlib
import io
import time
from pathlib import Path
import pandas as pd

try:
    import yfinance as yf
except ImportError:
    yf = None

# --- FULLY QUALIFIED INPUT & OUTPUT FILE VARIABLES ---
#NASDAQ_ETF_MASTER_FILE = Path(r"D:\TMP\1-8-2026\XX-US_ETF_Master_Library.csv")
NASDAQ_ETF_MASTER_FILE = Path(r"D:\Tools\00_StockCodeMaster\03_ETF\22-07-US_ETF_Master_Library.csv")
TARGET_ETF_HOLDINGS_FILE = Path(r"D:\TMP\1-8-2026\XX-US-ETF_Holdings_Detail.csv")


def parse_weight_value(raw_value):
    if pd.isna(raw_value):
        return 0.0
    text = str(raw_value).replace("%", "").strip()
    try:
        weight = float(text)
    except (TypeError, ValueError):
        return 0.0
    return weight * 100.0 if 0.0 < weight < 1.0 else weight


def lookup_holding_metadata(ticker, external_metadata_cache):
    ticker = str(ticker).strip().upper()
    if not ticker:
        return {
            "Holding Name": "",
            "Holding MarketCap": None,
            "Holding Metadata Source": "External / Unmapped",
        }
    if ticker in external_metadata_cache:
        return external_metadata_cache[ticker]

    record = {
        "Holding Name": "",
        "Holding MarketCap": None,
        "Holding Metadata Source": "External / Unmapped",
    }

    if yf is not None:
        try:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                info = yf.Ticker(ticker).get_info()
            name = info.get("longName") or info.get("shortName") or ""
            market_cap = info.get("marketCap")
            if name or market_cap:
                record = {
                    "Holding Name": name,
                    "Holding MarketCap": market_cap,
                    "Holding Metadata Source": "Yahoo Finance",
                }
        except Exception:
            pass

    external_metadata_cache[ticker] = record
    return record


def fetch_all_etf_holdings(etf_ticker):
    holdings = {}
    etf_ticker = str(etf_ticker).strip().upper()
    if not etf_ticker or yf is None:
        return holdings

    try:
        ticker_instance = yf.Ticker(etf_ticker)
        
        # 1. Attempt fetching complete holdings via funds_data.holdings
        try:
            fund_holdings = ticker_instance.funds_data.holdings
            if fund_holdings is not None and not fund_holdings.empty:
                for idx, row in fund_holdings.iterrows():
                    symbol = str(idx).strip().upper()
                    weight_cols = [c for c in row.index if "weight" in str(c).lower() or "percent" in str(c).lower()]
                    if symbol and weight_cols:
                        holdings[symbol] = parse_weight_value(row[weight_cols[0]])
                if holdings:
                    return holdings
        except Exception:
            pass

        # 2. Fallback to top holdings
        top_holdings = ticker_instance.funds_data.top_holdings
        if top_holdings is not None and not top_holdings.empty:
            top_holdings.columns = [str(c).lower().strip() for c in top_holdings.columns]
            if "symbol" in top_holdings.columns:
                top_holdings = top_holdings.set_index("symbol")
            weight_cols = [
                c for c in top_holdings.columns
                if any(term in c for term in ["percent", "holding", "weight", "allocation"])
            ]
            if weight_cols:
                for idx, row in top_holdings.iterrows():
                    symbol = str(idx).strip().upper()
                    if symbol:
                        holdings[symbol] = parse_weight_value(row[weight_cols[0]])
    except Exception as e:
        print(f"  [WARN] Failed to fetch holdings for {etf_ticker}: {e}")

    return holdings


def process_nasdaq_etf_holdings():
    print("\n================================================================================")
    print("RUNNING NASDAQ ETF HOLDINGS GENERATION ENGINE (WITH FULL METADATA)")
    print("================================================================================")
    print(f"Input Master File: {NASDAQ_ETF_MASTER_FILE}")
    print(f"Output Holdings File: {TARGET_ETF_HOLDINGS_FILE}")

    if not NASDAQ_ETF_MASTER_FILE.exists():
        print(f"[CRITICAL] Input master file not found: {NASDAQ_ETF_MASTER_FILE}")
        return

    try:
        df_etfs = pd.read_csv(NASDAQ_ETF_MASTER_FILE)
    except Exception as e:
        print(f"[CRITICAL] Could not read NASDAQ ETF master file: {e}")
        return

    ticker_col = None
    for col in ["Symbol", "Ticker", "ETF Ticker"]:
        if col in df_etfs.columns:
            ticker_col = col
            break
    if not ticker_col:
        ticker_col = df_etfs.columns[0]

    name_col = None
    for col in ["Security Name", "ETF Name", "Name"]:
        if col in df_etfs.columns:
            name_col = col
            break

    etf_rows = df_etfs[[ticker_col]].dropna().drop_duplicates()
    etf_tickers = etf_rows[ticker_col].tolist()

    if not etf_tickers:
        print("[CRITICAL] No ETF tickers found in master file. Aborting.")
        return

    detail_records = []
    external_metadata_cache = {}
    total_etfs = len(etf_tickers)

    for idx, etf_ticker in enumerate(etf_tickers, start=1):
        etf_ticker_str = str(etf_ticker).strip().upper()
        
        # Retrieve ETF Name from master if available
        etf_name = ""
        if name_col:
            match_row = df_etfs[df_etfs[ticker_col] == etf_ticker]
            if not match_row.empty:
                val = match_row.iloc[0][name_col]
                if pd.notna(val):
                    etf_name = str(val)

        print(f"  - Processing ETF {idx}/{total_etfs}: {etf_ticker_str} ({etf_name})")
        holdings = fetch_all_etf_holdings(etf_ticker_str)

        for holding_ticker, holding_weight in sorted(holdings.items(), key=lambda item: item[1], reverse=True):
            holding_meta = lookup_holding_metadata(holding_ticker, external_metadata_cache)

            detail_records.append({
                "ETF Ticker": etf_ticker_str,
                "ETF Name": etf_name,
                "Holding Ticker": holding_ticker,
                "Holding Name": holding_meta.get("Holding Name", ""),
                "Holding Weight %": round(holding_weight, 4),
                "Holding Sector": "External / Unmapped",
                "Holding Industry": "External / Unmapped",
                "Holding Market Region": "External",
                "Holding MarketCap": holding_meta.get("Holding MarketCap"),
                "Holding Metadata Source": holding_meta.get("Holding Metadata Source", "External / Unmapped"),
                "Holdings Source": "Yahoo Finance Full Holdings",
            })
        time.sleep(0.5)

    if detail_records:
        detail_df = pd.DataFrame(detail_records)
        TARGET_ETF_HOLDINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        detail_df.to_csv(TARGET_ETF_HOLDINGS_FILE, index=False)
        print(f"\n[SUCCESS] ETF Holdings Detail successfully saved to:\n  {TARGET_ETF_HOLDINGS_FILE.resolve()}")
        print(f"  Total holding rows recorded: {len(detail_df)}")
    else:
        print("\n[CRITICAL] No holdings data retrieved for any ETF.")


if __name__ == "__main__":
    process_nasdaq_etf_holdings()