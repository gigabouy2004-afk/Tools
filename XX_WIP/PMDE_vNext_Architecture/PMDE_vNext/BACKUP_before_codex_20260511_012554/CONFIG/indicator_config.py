
"""Indicator configuration registry."""

INPUT_CONFIG = {
    "input_file": "D:/Tools/StockCodeMaster/01_nasdaq_EnergyCodes.csv",
    "symbol_column": None,
    "exchange_column": None,
    "default_exchange": None,
    "fallback_symbols": [],
    "sort_unique": True
}

MACD_CONFIG = {
    "fast": 8,
    "slow": 21,
    "signal": 5,
    "primary_timeframe": "1d",
    "confirmation_timeframe": "4h"
}

EMA_CONFIG = {
    "ema_primary": 200
}
