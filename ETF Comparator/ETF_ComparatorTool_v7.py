import argparse
import pandas as pd
import yfinance as yf
from pathlib import Path

# --- CONFIG ---
BASE_FOLDER = Path("D:/Tools/ETF_Comparator")

INPUT_FILENAME = Path("D:/Tools/StockCodeMaster/ETF/01_INPUT_USA_Semiconductor_ETF_Codes.csv")
OUTPUT_FILENAME = Path("D:/Tools/ETF_Comparator/OUTPUT/Theme_USA_Technology_Semiconductor_ETF_Comparator_Results_v2.xlsx")


def parse_ticker_codes(ticker_text):
    if not ticker_text:
        return []

    tickers = [
        ticker.strip().upper()
        for ticker in ticker_text.split(",")
        if ticker.strip()
    ]
    return sorted(set(tickers))


def load_tickers(input_path, required=False):
    if not input_path.exists():
        if required:
            raise FileNotFoundError(f"Missing input file: {input_path}")
        print(f"[WARN] Input file not found: {input_path}")
        return []

    df = pd.read_csv(input_path, header=None, usecols=[0], dtype=str)
    tickers = (
        df.iloc[:, 0]
        .dropna()
        .astype(str)
        .str.strip()
        .str.upper()
        .unique()
        .tolist()
    )
    header_values = {"TICKER", "TICKERS", "SYMBOL", "SYMBOLS", "STOCK", "STOCK CODE", "STOCKCODE", "CODE"}
    tickers = [ticker for ticker in tickers if ticker and ticker not in header_values]
    return sorted(tickers)


def collect_tickers(input_path, ticker_text=None):
    file_tickers = load_tickers(input_path)
    cli_tickers = parse_ticker_codes(ticker_text)
    tickers = sorted(set(file_tickers + cli_tickers))

    if not tickers:
        raise ValueError("No ETF tickers found. Provide an input file or --tickers SMH,SOXX.")

    print(f"[INFO] File tickers: {len(file_tickers)} | Terminal tickers: {len(cli_tickers)} | Unique tickers: {len(tickers)}")
    return tickers


def get_price_series(ticker):
    tk = yf.Ticker(ticker)
    hist = tk.history(period="max")

    if hist.empty:
        return None, None, None

    hist.index = hist.index.tz_localize(None)

    price_col = "Adj Close" if "Adj Close" in hist.columns else "Close"
    prices = hist[price_col].dropna()

    return tk, prices, price_col


def compute_returns(prices: pd.Series):

    if prices is None or prices.empty or len(prices) < 2:
        return {}

    prices = prices.dropna().sort_index()
    last_date = prices.index[-1]

    def idx_on_or_before(dt):
        pos = prices.index.searchsorted(pd.Timestamp(dt), side="right") - 1
        return pos if pos >= 0 else None

    def idx_before(dt):
        pos = prices.index.searchsorted(pd.Timestamp(dt), side="left") - 1
        return pos if pos >= 0 else None

    def idx_on_or_after(dt):
        pos = prices.index.searchsorted(pd.Timestamp(dt), side="left")
        return pos if pos < len(prices) else None

    def calc_from_indices(s_idx, e_idx):
        if s_idx is None or e_idx is None or e_idx <= s_idx:
            return None

        start_price = prices.iloc[s_idx]
        end_price = prices.iloc[e_idx]
        if pd.isna(start_price) or pd.isna(end_price) or start_price == 0:
            return None

        return (end_price / start_price) - 1

    def calc_return(start_dt, end_dt=None, start_from_previous_close=False):
        """Return between two dates, optionally using the close before start_dt."""
        if end_dt is None:
            end_dt = last_date

        if start_from_previous_close:
            s_idx = idx_before(start_dt)
            if s_idx is None:
                s_idx = idx_on_or_after(start_dt)
        else:
            s_idx = idx_on_or_before(start_dt)
            if s_idx is None:
                s_idx = idx_on_or_after(start_dt)

        e_idx = idx_on_or_before(end_dt)
        return calc_from_indices(s_idx, e_idx)

    def pct(val):
        return round(val * 100, 2) if val is not None else None

    results = {}

    # --- Since Yesterday ---
    results["Since Yesterday (%)"] = (
        round(((prices.iloc[-1] / prices.iloc[-2]) - 1) * 100, 2)
        if len(prices) >= 2 else None
    )

    # --- WTD ---
    week_start = last_date - pd.Timedelta(days=last_date.weekday())
    results["This Week (%)"] = pct(calc_return(week_start, last_date, start_from_previous_close=True))

    # --- MTD ---
    month_start = pd.Timestamp(last_date.year, last_date.month, 1)
    results["MTD (%)"] = pct(calc_return(month_start, last_date, start_from_previous_close=True))

    # --- Fixed months ---
    months = {
        "Apr-26 (%)": (pd.Timestamp(2026, 4, 1), pd.Timestamp(2026, 4, 30)),
        "Mar-26 (%)": (pd.Timestamp(2026, 3, 1), pd.Timestamp(2026, 3, 31)),
        "Feb-26 (%)": (pd.Timestamp(2026, 2, 1), pd.Timestamp(2026, 2, 28)),
        "Jan-26 (%)": (pd.Timestamp(2026, 1, 1), pd.Timestamp(2026, 1, 31)),
        "2025 (%)": (pd.Timestamp(2025, 1, 1), pd.Timestamp(2025, 12, 31)),
    }

    for k, (s, e) in months.items():
        results[k] = pct(calc_return(s, e, start_from_previous_close=True))

    # --- YTD ---
    year_start = pd.Timestamp(last_date.year, 1, 1)
    results["YTD (%)"] = pct(calc_return(year_start, start_from_previous_close=True))

    # --- Rolling / trailing returns ---
    rolling_periods = {
        "3 Month (%)": pd.DateOffset(months=3),
        "6 Month (%)": pd.DateOffset(months=6),
        "9 Month (%)": pd.DateOffset(months=9),
        "1 yr (%)": pd.DateOffset(years=1),
        "3 yr (%)": pd.DateOffset(years=3),
        "5 yr (%)": pd.DateOffset(years=5),
        "7 yr (%)": pd.DateOffset(years=7),
    }

    for label, lookback in rolling_periods.items():
        start_dt = last_date - lookback
        results[label] = pct(calc_return(start_dt))

    return results


def normalize_ratio(value):
    if value is None or pd.isna(value):
        return None

    if isinstance(value, str):
        cleaned = value.strip().replace("%", "")
        if not cleaned:
            return None
        try:
            value = float(cleaned)
        except ValueError:
            return None

    try:
        value = float(value)
    except (TypeError, ValueError):
        return None

    if value > 1:
        value = value / 100

    return round(value, 6)


def get_expense_ratio_from_funds_data(tk):
    try:
        funds_data = tk.get_funds_data()
        fund_operations = funds_data.fund_operations
    except Exception:
        return None

    if fund_operations is None or fund_operations.empty:
        return None

    possible_labels = [
        "Annual Report Expense Ratio",
        "Expense Ratio",
        "Net Expense Ratio",
        "Gross Expense Ratio",
    ]

    for label in possible_labels:
        if label not in fund_operations.index:
            continue

        row = fund_operations.loc[label]
        if isinstance(row, pd.Series):
            for value in row.dropna():
                ratio = normalize_ratio(value)
                if ratio is not None:
                    return ratio
        else:
            ratio = normalize_ratio(row)
            if ratio is not None:
                return ratio

    return None


def get_expense_ratio(info, tk):
    possible_keys = [
        "expenseRatio",
        "annualReportExpenseRatio",
        "netExpenseRatio",
        "grossExpenseRatio",
    ]

    for key in possible_keys:
        ratio = normalize_ratio(info.get(key))
        if ratio is not None:
            return ratio

    return get_expense_ratio_from_funds_data(tk)


def extract_fundamentals(tk):
    try:
        info = tk.info
    except Exception:
        info = {}

    expense_ratio = get_expense_ratio(info, tk)

    aum = info.get("totalAssets") or info.get("marketCap")
    aum_m = aum / 1_000_000 if aum else None

    return {
        "Name": info.get("longName", None),
        "AUM (USD M)": aum_m,
        "Expense Ratio": expense_ratio,
        "Liquidity (Avg Vol)": info.get("averageVolume", None),
    }


def run(ticker_text=None):
    base = Path(BASE_FOLDER)
    base.mkdir(parents=True, exist_ok=True)

    input_path = INPUT_FILENAME if INPUT_FILENAME.is_absolute() else base / INPUT_FILENAME
    output_path = OUTPUT_FILENAME if OUTPUT_FILENAME.is_absolute() else base / OUTPUT_FILENAME
    output_path.parent.mkdir(parents=True, exist_ok=True)

    tickers = collect_tickers(input_path, ticker_text)

    results = []

    for t in tickers:
        try:
            tk, prices, price_col = get_price_series(t)

            if prices is None:
                print(f"[SKIP] No data: {t}")
                continue

            current_price = round(prices.iloc[-1],2)

            returns = compute_returns(prices)
            fundamentals = extract_fundamentals(tk)

            row = {
                "Ticker": t,
                "Price": current_price,
                **fundamentals,
                **returns,
            }

            results.append(row)
            print(f"[OK] {t}")

        except Exception as e:
            print(f"[ERR] {t}: {e}")

    df = pd.DataFrame(results)

    ordered_cols = [
        "Ticker", "Name", "AUM (USD M)", "Price", "Liquidity (Avg Vol)",
        "Since Yesterday (%)", "This Week (%)", "MTD (%)",
        "Apr-26 (%)", "Mar-26 (%)", "Feb-26 (%)", "Jan-26 (%)", "YTD (%)", "3 Month (%)",
        "6 Month (%)", "9 Month (%)", "1 yr (%)", "3 yr (%)", "5 yr (%)", "7 yr (%)", "2025 (%)"

    ]

    df = df.reindex(columns=ordered_cols)

    # --- Sort by MTD ---
    if "MTD (%)" in df.columns:
        df["MTD (%)"] = pd.to_numeric(df["MTD (%)"], errors="coerce")
        df = df.sort_values(by="MTD (%)", ascending=False)

    df.to_excel(output_path, index=False, engine="openpyxl")

    print(f"\nSaved -> {output_path}")


def parse_args():
    parser = argparse.ArgumentParser(description="Compare ETF returns and fundamentals.")
    parser.add_argument(
        "--tickers",
        help="Optional comma-separated ETF tickers to combine with INPUT_FILENAME, e.g. SMH,SOXX,XLK.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(args.tickers)
