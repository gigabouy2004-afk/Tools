import importlib.util
import pandas as pd
import yfinance as yf

V7_PATH = "d:/Tools/07_LiveScanner/Live_Scanner_v7.py"
SEED_FILE = "d:/Tools/07_LiveScanner/input/seed_energy_codes_core.csv"
OUT_DETAIL = "d:/Tools/07_LiveScanner/output/energy_seed_date_study_detail.csv"
OUT_SUMMARY = "d:/Tools/07_LiveScanner/output/energy_seed_date_study_summary.csv"

DATES = ["2026-03-17", "2026-04-15", "2026-06-17", "2026-07-14"]

spec = importlib.util.spec_from_file_location("v7", V7_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

config = module.get_config("aggressive")
seed_df = pd.read_csv(SEED_FILE)
tickers = seed_df.iloc[:, 0].dropna().astype(str).str.strip().str.upper().unique().tolist()

rows = []

for ticker in tickers:
    try:
        df = yf.Ticker(ticker).history(period="8y", interval="1d", prepost=True)
        if df.empty:
            for d in DATES:
                rows.append({"as_of_date": d, "ticker": ticker, "status": module.STATUS_ERROR, "message": "No history returned."})
            continue
        df.columns = [c.lower() for c in df.columns]

        for d in DATES:
            hist = module.filter_to_as_of_date(df, d)
            if len(hist) < module.EMA_SLOW_PERIOD:
                rows.append({"as_of_date": d, "ticker": ticker, "status": module.STATUS_ERROR, "message": f"Insufficient history up to {d}."})
                continue
            r = module.evaluate_frame(hist, ticker, config)
            rows.append(
                {
                    "as_of_date": d,
                    "ticker": ticker,
                    "status": r.get("status"),
                    "signal_score": r.get("signal_score"),
                    "message": r.get("message"),
                    "price": r.get("price"),
                    "ema_50": r.get("ema_50"),
                    "ema_200": r.get("ema_200"),
                    "macd": r.get("macd"),
                    "macd_signal": r.get("macd_signal"),
                    "adx": r.get("adx"),
                    "rsi": r.get("rsi"),
                    "stoch_k": r.get("stoch_k"),
                    "stoch_d": r.get("stoch_d"),
                    "volume": r.get("volume"),
                    "volume_avg_20": r.get("volume_avg_20"),
                }
            )
    except Exception as e:
        for d in DATES:
            rows.append({"as_of_date": d, "ticker": ticker, "status": module.STATUS_ERROR, "message": f"Internal error: {e}"})


detail = pd.DataFrame(rows)
detail.to_csv(OUT_DETAIL, index=False)

summary = (
    detail.groupby(["as_of_date", "status"]).size().reset_index(name="count").sort_values(["as_of_date", "status"])
)
summary.to_csv(OUT_SUMMARY, index=False)

buy_rows = detail[detail["status"] == module.STATUS_BUY_SIGNAL].copy()

print(f"TICKERS {len(tickers)}")
print(f"DETAIL_FILE {OUT_DETAIL}")
print(f"SUMMARY_FILE {OUT_SUMMARY}")

for d in DATES:
    sub = detail[detail["as_of_date"] == d]
    counts = sub["status"].value_counts().to_dict()
    print(f"DATE {d} COUNTS {counts}")

print(f"BUY_ROWS {len(buy_rows)}")
if not buy_rows.empty:
    for _, row in buy_rows.sort_values(["as_of_date", "ticker"]).iterrows():
        print(f"BUY {row['as_of_date']} {row['ticker']} score={row.get('signal_score')} msg={row.get('message')}")
