import pandas as pd
import yfinance as yf
from pathlib import Path
from datetime import datetime

# --- CONFIG ---
BASE_FOLDER = r"D:/Tools/ETF_Comparator"
INPUT_FILENAME = "INPUT/01_INPUT_USA_Energy_ETF_Codes.csv"
OUTPUT_FILENAME = "OUTPUT/Theme_USA_Energy_ETF_Comparator_Results_v1.xlsx"


def load_tickers(input_path):
    if not input_path.exists():
        raise FileNotFoundError(f"Missing input file: {input_path}")

    df = pd.read_csv(input_path)
    col = df.columns[0]
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

        return ((end_val / start_val) - 1)

    now = ref_date
    results = {}

    # Since Yesterday
    if len(prices) >= 2:
        results["Since Yesterday"] = ((prices.iloc[-1] / prices.iloc[-2]) - 1) * 100
    else:
        results["Since Yesterday"] = None

    # This Week
    week_start = now - pd.Timedelta(days=now.weekday())
    val = calc(week_start)
    results["This Week"] = val * 100 if val is not None else None

    # MTD (FIXED)
    month_start = datetime(now.year, now.month, 1)
    mtd_val = calc(month_start)
    results["MTD"] = mtd_val * 100 if mtd_val is not None else None

    # Fixed months
    months = {
        "Apr-26": (datetime(2026, 4, 1), datetime(2026, 4, 30)),
        "Mar-26": (datetime(2026, 3, 1), datetime(2026, 3, 31)),
        "Feb-26": (datetime(2026, 2, 1), datetime(2026, 2, 28)),
        "Jan-26": (datetime(2026, 1, 1), datetime(2026, 1, 31)),
    }

    for k, (s, e) in months.items():
        val = calc(s, e)
        results[k] = val * 100 if val is not None else None

    # YTD
    val = calc(datetime(now.year, 1, 1))
    results["YTD"] = val * 100 if val is not None else None

    # Rolling
    val = calc(now - pd.Timedelta(days=90))
    results["3 Month"] = val * 100 if val is not None else None

    val = calc(now - pd.Timedelta(days=180))
    results["6 Month"] = val * 100 if val is not None else None

    val = calc(now - pd.Timedelta(days=270))
    results["9 Month"] = val * 100 if val is not None else None

    val = calc(now - pd.Timedelta(days=365))
    results["1 yr"] = val * 100 if val is not None else None

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

    input_path = base / INPUT_FILENAME
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
        "Since Yesterday", "This Week", "MTD",
        "Apr-26", "Mar-26", "3 Month", "YTD", "6 Month", "9 Month", "1 yr"
    ]

    df = df.reindex(columns=ordered_cols)

    # Safe sort (FIXED)
    if "MTD" in df.columns:
        df["MTD"] = pd.to_numeric(df["MTD"], errors="coerce")
        df = df.sort_values(by="MTD", ascending=False)

    df.to_excel(output_path, index=False, engine="openpyxl")

    print(f"\nSaved → {output_path}")


if __name__ == "__main__":
    run()