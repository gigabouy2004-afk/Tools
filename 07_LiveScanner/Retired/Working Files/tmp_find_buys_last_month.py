import importlib.util

spec = importlib.util.spec_from_file_location("v7", "d:/Tools/07_LiveScanner/Live_Scanner_v7.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

config = module.get_config("balanced")
tickers = [
    "NVDA", "AMD", "AVGO", "PLTR", "HOOD", "RKLB", "SMCI", "MSTR", "TSLA", "COIN",
    "META", "AMZN", "AAPL", "MSFT", "PARR", "CHRN", "QCOM", "ANET", "PANW", "CRWD",
    "SNOW", "SHOP", "UBER"
]
dates = ["2026-06-10", "2026-06-17", "2026-06-24", "2026-07-01", "2026-07-08", "2026-07-15"]

buys = []
for as_of_date in dates:
    for ticker in tickers:
        result = module.evaluate_stock_momentum(ticker, config=config, history_years=8, as_of_date=as_of_date)
        if result.get("status") == module.STATUS_BUY_SIGNAL:
            buys.append(
                {
                    "date": as_of_date,
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

print(f"BUY_COUNT {len(buys)}")
for row in buys:
    print(
        "BUY",
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
