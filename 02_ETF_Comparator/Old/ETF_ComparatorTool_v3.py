import pandas as pd
import yfinance as yf
from pathlib import Path
from datetime import datetime

# --- CONFIG ---
BASE_FOLDER = r"D:/Tools/ETF_Comparator"
INPUT_FILENAME = "D:/Tools/StockCodeMaster/ETF/01_INPUT_USA_Aerospace-Defence_Codes.csv"
OUTPUT_FILENAME = "OUTPUT/Theme_Aerospace-Defence_ETF_Comparator_Results_v1.xlsx"


def load_tickers(input_path):
    if not input_path.exists():
        raise FileNotFoundError(f"Missing input file: {input_path}")

    df = pd.read_csv(input_path)
    col = df.columns[0]  # assume first column contains tickers
    tickers = (
        df[col]
        .dropna()
        .astype(str)
        .str.strip()
        .str.upper()
        .unique()
        .tolist()
    )
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


def compute_returns(prices: pd.Series, ref_date: pd.Timestamp):
    """
    Returns dictionary of time-window returns using nearest valid trading days.
    """

    def nearest_idx(dt, direction="forward"):
        dt = pd.Timestamp(dt)

        if direction == "forward":
            pos = prices.index.searchsorted(dt)
            return pos if pos < len(prices) else None
        else:
            pos = prices.index.searchsorted(dt, side="right") - 1
            return pos if pos >= 0 else None

    def calc(start_dt, end_dt=None):
        s_idx = nearest_idx(start_dt, "forward")
        if s_idx is None:
            return None

        if end_dt:
            e_idx = nearest_idx(end_dt, "backward")
        else:
            e_idx = len(prices) - 1

        if e_idx is None or e_idx <= s_idx:
            return None

        start_val = prices.iloc[s_idx]
        end_val = prices.iloc[e_idx]

        return (end_val / start_val) - 1

    now = ref_date

    results = {}

    # Daily (true previous trading day)
    if len(prices) >= 2:
        results["Since Yesterday"] = ( (prices.iloc[-1] / prices.iloc[-2]) - 1) *100
    else:
        results["Since Yesterday"] = None

    # Weekly (start of week)
    week_start = now - pd.Timedelta(days=now.weekday())
    results["This Week"] = calc(week_start)*100

    # Monthly
    month_start = datetime(now.year, now.month, 1)
    results["MTD"] = calc(month_start)*100

    # Fixed months
    months = {
        "Apr-26": (datetime(2026, 4, 1), datetime(2026, 4, 30)),
        "Mar-26": (datetime(2026, 3, 1), datetime(2026, 3, 31)),
        "Feb-26": (datetime(2026, 2, 1), datetime(2026, 2, 28)),
        "Jan-26": (datetime(2026, 1, 1), datetime(2026, 1, 31)),
    }

    for k, (s, e) in months.items():
        results[k] = calc(s, e)

    # YTD
    results["YTD"] = calc(datetime(now.year, 1, 1))*100

    # Rolling windows
    results["3 Month"] = calc(now - pd.Timedelta(days=90))*100
    results["6 Month"] = calc(now - pd.Timedelta(days=180))*100
    results["9 Month"] = calc(now - pd.Timedelta(days=270))*100
    results["1 yr"] = calc(now - pd.Timedelta(days=365))*100

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

#    input_path = base / INPUT_FILENAME
    input_path = Path(INPUT_FILENAME)
    output_path = base / OUTPUT_FILENAME

    tickers = load_tickers(input_path)
    now = pd.Timestamp(datetime.now())

    results = []

    for t in tickers:
        try:
            tk, prices, price_col = get_price_series(t)

            if prices is None:
                print(f"[SKIP] No data: {t}")
                continue

            current_price = prices.iloc[-1]

            returns = compute_returns(prices, now)
            fundamentals = extract_fundamentals(tk)

            row = {
                "Ticker": t,
                "Price": current_price,
#                "Price Source": price_col,  # audit column
#                "Last Date": prices.index[-1],  # audit column
                **fundamentals,
                **returns,
            }

            results.append(row)

            print(f"[OK] {t}")

        except Exception as e:
            print(f"[ERR] {t}: {e}")

    df = pd.DataFrame(results)

    # enforce column order
    ordered_cols = [
        "Ticker", "Name", "AUM (USD M)", "Price",
#        "Price Source",
#        "Expense Ratio", 
#        "Liquidity (Avg Vol)", 
#        "Last Date",
        "Since Yesterday", "This Week", "MTD",
        "Apr-26", "Mar-26", "Feb-26", "Jan-26",
        "YTD", "3 Month", "6 Month", "9 Month", "1 yr"
    ]

    df = df.reindex(columns=ordered_cols)

    # DO NOT silently coerce missing values
    df.to_excel(output_path, index=False, engine="openpyxl")

    print(f"\nSaved → {output_path}")


if __name__ == "__main__":
    run()