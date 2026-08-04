import pandas as pd
import yfinance as yf
from pathlib import Path

# --- CONFIG ---
BASE_FOLDER = Path("D:/Tools/ETF_Comparator")

INPUT_FILENAME = Path("D:/Tools/StockCodeMaster/ETF/00_NYSE_NASDAQ_ETF_Master_Library-PlainETF.csv")
OUTPUT_FILENAME = Path("D:/Tools/ETF_Comparator/OUTPUT/Result_NYSE-NASDAQ_AllETF_Comparison.xlsx")


def load_tickers(input_path):
    if not input_path.exists():
        raise FileNotFoundError(f"Missing input file: {input_path}")

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

    def calc_period_return(period_start, end_dt=None):
        """Return from the close immediately before period_start to end_dt."""
        if end_dt is None:
            end_dt = last_date

        s_idx = idx_before(period_start)
        if s_idx is None:
            s_idx = idx_on_or_after(period_start)

        e_idx = idx_on_or_before(end_dt)
        return calc_from_indices(s_idx, e_idx)

    def calc_trailing_return(start_dt, end_dt=None):
        if end_dt is None:
            end_dt = last_date

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
    results["This Week (%)"] = pct(calc_period_return(week_start, last_date))

    # --- MTD ---
    month_start = pd.Timestamp(last_date.year, last_date.month, 1)
    results["MTD (%)"] = pct(calc_period_return(month_start, last_date))

    # --- Fixed months ---
    months = {
        "Apr-26 (%)": (pd.Timestamp(2026, 4, 1), pd.Timestamp(2026, 4, 30)),
        "Mar-26 (%)": (pd.Timestamp(2026, 3, 1), pd.Timestamp(2026, 3, 31)),
        "Feb-26 (%)": (pd.Timestamp(2026, 2, 1), pd.Timestamp(2026, 2, 28)),
        "Jan-26 (%)": (pd.Timestamp(2026, 1, 1), pd.Timestamp(2026, 1, 31)),
    }

    for k, (s, e) in months.items():
        results[k] = pct(calc_period_return(s, e))

    # --- YTD ---
    year_start = pd.Timestamp(last_date.year, 1, 1)
    results["YTD (%)"] = pct(calc_period_return(year_start))

    # --- Rolling ---
    rolling_days = {
        "3 Month (%)": 90,
        "6 Month (%)": 180,
        "9 Month (%)": 270,
        "1 yr (%)": 365,
    }

    for label, days in rolling_days.items():
        start_dt = last_date - pd.Timedelta(days=days)
        results[label] = pct(calc_trailing_return(start_dt))

    return results


def extract_fundamentals(tk):
    try:
        info = tk.info
    except Exception:
        info = {}

    expense_ratio = (
        info.get("expenseRatio")
        or info.get("annualReportExpenseRatio")
        or None
    )

    aum = info.get("totalAssets") or info.get("marketCap")
    aum_m = aum / 1_000_000 if aum else None

    return {
        "Name": info.get("longName", None),
        "AUM (USD M)": aum_m,
        "Expense Ratio": expense_ratio,
        "Liquidity (Avg Vol)": info.get("averageVolume", None),
    }


def run():
    base = Path(BASE_FOLDER)
    base.mkdir(parents=True, exist_ok=True)

    input_path = INPUT_FILENAME if INPUT_FILENAME.is_absolute() else base / INPUT_FILENAME
    output_path = OUTPUT_FILENAME if OUTPUT_FILENAME.is_absolute() else base / OUTPUT_FILENAME
    output_path.parent.mkdir(parents=True, exist_ok=True)

    tickers = load_tickers(input_path)

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
        "6 Month (%)", "9 Month (%)", "1 yr (%)"
    ]

    df = df.reindex(columns=ordered_cols)

    # --- Sort by MTD ---
    if "MTD (%)" in df.columns:
        df["MTD (%)"] = pd.to_numeric(df["MTD (%)"], errors="coerce")
        df = df.sort_values(by="MTD (%)", ascending=False)

    df.to_excel(output_path, index=False, engine="openpyxl")

    print(f"\nSaved -> {output_path}")


if __name__ == "__main__":
    run()
