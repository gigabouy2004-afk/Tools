import importlib.util
from datetime import date, timedelta
import pandas as pd
import yfinance as yf

V7_PATH = "d:/Tools/07_LiveScanner/Live_Scanner_v7.py"
OUT_DETAIL = "d:/Tools/07_LiveScanner/output/ai_momentum_buy_study_detail.csv"
OUT_SUMMARY = "d:/Tools/07_LiveScanner/output/ai_momentum_buy_study_summary.csv"

spec = importlib.util.spec_from_file_location("v7", V7_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

# AI-focused basket across memory, infrastructure, hyperscalers, networking, software.
STOCK_UNIVERSE = [
    ("MU", "memory"),
    ("MRVL", "memory"),
    ("NVDA", "ai_infra"),
    ("AMD", "ai_infra"),
    ("SMCI", "ai_infra"),
    ("ANET", "networking"),
    ("AVGO", "networking"),
    ("PLTR", "software"),
    ("SNOW", "software"),
    ("CRWD", "software"),
    ("PANW", "software"),
    ("MSFT", "hyperscaler"),
    ("AMZN", "hyperscaler"),
    ("GOOGL", "hyperscaler"),
    ("META", "hyperscaler"),
]

END_DATE = date(2026, 7, 15)
START_DATE = END_DATE - timedelta(days=60)
AS_OF_DATES = pd.bdate_range(START_DATE, END_DATE)


def run_preset_study(preset: str) -> pd.DataFrame:
    config = module.get_config(preset)
    rows = []

    for ticker, bucket in STOCK_UNIVERSE:
        try:
            df = yf.Ticker(ticker).history(period="8y", interval="1d", prepost=True)
            if df.empty:
                continue
            df.columns = [col.lower() for col in df.columns]

            for as_of_ts in AS_OF_DATES:
                as_of_date = as_of_ts.strftime("%Y-%m-%d")
                hist = module.filter_to_as_of_date(df, as_of_date)
                if len(hist) < module.EMA_SLOW_PERIOD:
                    continue

                result = module.evaluate_frame(hist, ticker, config)
                rows.append(
                    {
                        "preset": preset,
                        "as_of_date": as_of_date,
                        "ticker": ticker,
                        "bucket": bucket,
                        "status": result.get("status"),
                        "signal_score": result.get("signal_score"),
                        "message": result.get("message"),
                        "price": result.get("price"),
                        "ema_50": result.get("ema_50"),
                        "ema_200": result.get("ema_200"),
                        "macd": result.get("macd"),
                        "macd_signal": result.get("macd_signal"),
                        "adx": result.get("adx"),
                        "rsi": result.get("rsi"),
                        "stoch_k": result.get("stoch_k"),
                        "stoch_d": result.get("stoch_d"),
                        "volume": result.get("volume"),
                        "volume_avg_20": result.get("volume_avg_20"),
                    }
                )
        except Exception:
            continue

    return pd.DataFrame(rows)


all_frames = []
for preset_name in ["balanced", "aggressive"]:
    frame = run_preset_study(preset_name)
    if not frame.empty:
        all_frames.append(frame)

if not all_frames:
    print("NO_DATA")
    raise SystemExit(0)

detail_df = pd.concat(all_frames, ignore_index=True)
detail_df.to_csv(OUT_DETAIL, index=False)

buy_df = detail_df[detail_df["status"] == module.STATUS_BUY_SIGNAL].copy()

if buy_df.empty:
    summary = pd.DataFrame(
        [
            {
                "preset": "balanced",
                "stocks_with_buy": 0,
                "total_buy_signals": 0,
                "first_buy_date": None,
                "last_buy_date": None,
            },
            {
                "preset": "aggressive",
                "stocks_with_buy": 0,
                "total_buy_signals": 0,
                "first_buy_date": None,
                "last_buy_date": None,
            },
        ]
    )
    summary.to_csv(OUT_SUMMARY, index=False)
    print("BUY_SIGNALS_FOUND 0")
    raise SystemExit(0)

preset_rollup = (
    buy_df.groupby("preset")
    .agg(
        stocks_with_buy=("ticker", "nunique"),
        total_buy_signals=("ticker", "size"),
        first_buy_date=("as_of_date", "min"),
        last_buy_date=("as_of_date", "max"),
    )
    .reset_index()
)

stock_rollup = (
    buy_df.groupby(["preset", "ticker", "bucket"])
    .agg(
        buy_days=("as_of_date", "size"),
        first_buy_date=("as_of_date", "min"),
        last_buy_date=("as_of_date", "max"),
    )
    .reset_index()
)

summary_df = pd.concat([preset_rollup, stock_rollup], ignore_index=True, sort=False)
summary_df.to_csv(OUT_SUMMARY, index=False)

print(f"BUY_SIGNALS_FOUND {len(buy_df)}")
for preset_name in ["balanced", "aggressive"]:
    sub = buy_df[buy_df["preset"] == preset_name]
    print(f"PRESET {preset_name} STOCKS_WITH_BUY {sub['ticker'].nunique()} TOTAL_BUY_ROWS {len(sub)}")
    if not sub.empty:
        top = (
            sub.groupby(["ticker", "bucket"])['as_of_date']
            .count()
            .reset_index(name="buy_days")
            .sort_values(["buy_days", "ticker"], ascending=[False, True])
        )
        for _, row in top.head(10).iterrows():
            print(f"BUY_STOCK {preset_name} {row['ticker']} {row['bucket']} days={int(row['buy_days'])}")
