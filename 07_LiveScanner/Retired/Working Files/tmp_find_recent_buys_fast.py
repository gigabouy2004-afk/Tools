import importlib.util
import pandas as pd
import yfinance as yf

spec = importlib.util.spec_from_file_location("v7", "d:/Tools/07_LiveScanner/Live_Scanner_v7.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

config = module.get_config("aggressive")

# Broad momentum-focused universe for baseline discovery
TICKERS = [
    "NVDA", "AMD", "AVGO", "PLTR", "HOOD", "RKLB", "SMCI", "MSTR", "TSLA", "COIN",
    "META", "AMZN", "AAPL", "MSFT", "QCOM", "ANET", "PANW", "CRWD", "SNOW", "SHOP", "UBER",
    "NET", "DDOG", "RBLX", "SOFI", "AFRM", "UPST", "APP", "CELH", "ENPH", "FSLR",
    "MRVL", "ARM", "ADBE", "NFLX", "ORCL", "INTC", "TXN", "MU", "PINS", "TTD"
]

# Last month window relative to current context date (2026-07-16)
START = pd.Timestamp("2026-06-01")
END = pd.Timestamp("2026-07-15")

found = []

for ticker in TICKERS:
    try:
        df = yf.Ticker(ticker).history(period="8y", interval="1d", prepost=True)
        if df.empty or len(df) < module.EMA_SLOW_PERIOD:
            continue
        df.columns = [c.lower() for c in df.columns]

        for day in pd.bdate_range(START, END):
            hist = module.filter_to_as_of_date(df, day.strftime("%Y-%m-%d"))
            if len(hist) < module.EMA_SLOW_PERIOD:
                continue
            result = module.evaluate_frame(hist, ticker, config)
            if result.get("status") == module.STATUS_BUY_SIGNAL:
                found.append(
                    {
                        "date": day.strftime("%Y-%m-%d"),
                        "ticker": ticker,
                        "price": result.get("price"),
                        "score": result.get("signal_score"),
                        "rsi": result.get("rsi"),
                        "macd": result.get("macd"),
                        "macd_signal": result.get("macd_signal"),
                        "stoch_k": result.get("stoch_k"),
                        "stoch_d": result.get("stoch_d"),
                        "volume": result.get("volume"),
                        "volume_avg_20": result.get("volume_avg_20"),
                        "message": result.get("message"),
                    }
                )
                break
    except Exception:
        continue

print(f"FOUND_COUNT {len(found)}")
for row in found[:20]:
    print(
        "FOUND",
        row["date"],
        row["ticker"],
        row["price"],
        row["score"],
        row["rsi"],
        row["macd"],
        row["macd_signal"],
        row["stoch_k"],
        row["stoch_d"],
        row["volume"],
        row["volume_avg_20"],
        row["message"],
        sep=" | ",
    )
