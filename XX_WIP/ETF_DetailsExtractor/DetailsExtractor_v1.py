import argparse
import csv
import sys
import yfinance as yf

def parse_arguments():
    parser = argparse.ArgumentParser(description="Generate ETF master CSV efficiently using yfinance.")
    parser.add_argument("--etfs", type=str, required=True, help="Comma-separated list of ETF ticker codes (e.g., SPY,QQQ)")
    parser.add_argument("--output", type=str, default="etf_master.csv", help="Output CSV file name")
    return parser.parse_args()

def format_number(val):
    try:
        num = float(val)
        return f"{num:,.0f}" if num.is_integer() else f"{num:,.2f}"
    except (ValueError, TypeError):
        return "N/A" if val in [None, ""] else str(val)

def format_aum(val):
    try:
        num = float(val)
        if num >= 1_000_000_000:
            return f"{num / 1_000_000_000:.2f}B"
        elif num >= 1_000_000:
            return f"{num / 1_000_000:.2f}M"
        else:
            return f"{num:,.0f}"
    except (ValueError, TypeError):
        return "N/A"

def extract_keywords(summary):
    if not summary or summary == "N/A":
        return "N/A"
    words = summary.split()
    keywords = [
        word.strip(".,()[]{}'\"")
        for word in words
        if word and word[0].isupper() and len(word) > 4
    ]
    seen = set()
    unique_keywords = [k for k in keywords if not (k in seen or seen.add(k))][:8]
    return ", ".join(unique_keywords) if unique_keywords else "N/A"

def get_etf_data(ticker_symbol):
    ticker = yf.Ticker(ticker_symbol)
    try:
        info = ticker.info
    except Exception as e:
        print(f"Error fetching info for {ticker_symbol}: {e}", file=sys.stderr)
        return None

    # If info is empty or doesn't contain standard fields, fallback gracefully
    if not info or ("regularMarketPrice" not in info and "currentPrice" not in info):
        return {
            "Ticker": ticker_symbol, "Name": "N/A", "LTP": "N/A", "Volume": "N/A", 
            "AUM": "N/A", "Average Trading Volume (3m)": "N/A", "Number of Holdings": "N/A", 
            "Holding Codes": "N/A", "Leveraged": False, "Beta": "N/A", 
            "Price Range (52W)": "N/A", "IsIndexFund": False, "Profile Keywords": "N/A"
        }

    name = info.get("longName") or info.get("shortName") or "N/A"
    
    ltp = info.get("regularMarketPrice", info.get("currentPrice", "N/A"))
    if ltp != "N/A":
        ltp = format_number(ltp)
        
    volume = info.get("regularMarketVolume", info.get("volume", "N/A"))
    if volume != "N/A":
        volume = format_number(volume)

    aum = info.get("totalAssets", "N/A")
    if aum != "N/A":
        aum = format_aum(aum)

    avg_volume_3m = info.get("averageVolume", "N/A")
    if avg_volume_3m != "N/A":
        avg_volume_3m = format_number(avg_volume_3m)

    # Fast, direct holdings extraction via yfinance
    holding_codes = []
    num_holdings = "N/A"
    try:
        top_holdings = ticker.funds_data.top_holdings
        if top_holdings is not None and not top_holdings.empty:
            col = "Symbol" if "Symbol" in top_holdings.columns else "symbol" if "symbol" in top_holdings.columns else None
            if col:
                holding_codes = top_holdings[col].dropna().tolist()
            num_holdings = len(top_holdings)
    except Exception:
        pass

    holding_str = ", ".join(map(str, holding_codes)) if holding_codes else "N/A"
    if num_holdings != "N/A":
        num_holdings = format_number(num_holdings)

    name_lower = name.lower()
    is_leveraged = "leveraged" in name_lower or "2x" in name_lower or "3x" in name_lower or "ultra" in name_lower

    beta = info.get("beta", "N/A")
    if beta == "N/A" or beta is None:
        beta = "N/A"
    else:
        beta = format_number(beta)

    low_52w = info.get("fiftyTwoWeekLow", "N/A")
    high_52w = info.get("fiftyTwoWeekHigh", "N/A")
    if low_52w != "N/A" and high_52w != "N/A":
        price_range_52w = f"{format_number(low_52w)} - {format_number(high_52w)}"
    else:
        price_range_52w = "N/A"

    is_index = "index" in name_lower or "track" in name_lower or "sp 500" in name_lower or "nasdaq" in name_lower

    summary = info.get("longBusinessSummary", "N/A")
    profile_keywords = extract_keywords(summary)

    return {
        "Ticker": ticker_symbol,
        "Name": name,
        "LTP": ltp,
        "Volume": volume,
        "AUM": aum,
        "Average Trading Volume (3m)": avg_volume_3m,
        "Number of Holdings": num_holdings,
        "Holding Codes": holding_str,
        "Leveraged": is_leveraged,
        "Beta": beta,
        "Price Range (52W)": price_range_52w,
        "IsIndexFund": is_index,
        "Profile Keywords": profile_keywords,
    }

def main():
    args = parse_arguments()
    etf_list = [etf.strip().upper() for etf in args.etfs.split(",")]

    fieldnames = [
        "Ticker", "Name", "LTP", "Volume", "AUM", "Average Trading Volume (3m)",
        "Number of Holdings", "Holding Codes", "Leveraged", "Beta",
        "Price Range (52W)", "IsIndexFund", "Profile Keywords"
    ]

    print(f"Starting extraction for ETFs: {', '.join(etf_list)}")

    with open(args.output, mode="w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()

        for etf in etf_list:
            print(f"Fetching data for {etf} via yfinance...")
            data = get_etf_data(etf)
            if data:
                writer.writerow(data)

    print(f"\nProcessing complete. Master CSV saved as '{args.output}'.")

if __name__ == "__main__":
    main()