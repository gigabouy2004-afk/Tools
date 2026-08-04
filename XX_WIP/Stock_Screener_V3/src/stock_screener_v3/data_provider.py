from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import pandas as pd
import yfinance as yf


REQUIRED_PRICE_COLUMNS = ("Open", "High", "Low", "Close", "Volume")


class PriceProvider(Protocol):
    def daily(self, symbol: str) -> pd.DataFrame:
        """Return daily historical data for the symbol from the active provider."""


def normalize_price_columns(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    normalized = frame.copy()
    if isinstance(normalized.columns, pd.MultiIndex):
        normalized.columns = [
            next((str(part) for part in column if part), str(column[0]))
            for column in normalized.columns
        ]
    rename_map = {column: str(column).strip().capitalize() for column in normalized.columns}
    normalized = normalized.rename(columns=rename_map)
    available = [column for column in REQUIRED_PRICE_COLUMNS if column in normalized.columns]
    return normalized[available].copy()


@dataclass(frozen=True)
class YahooFinancePriceProvider:
    start: str | None = None
    end: str | None = None
    period: str | None = "2y"
    interval: str = "1d"
    auto_adjust: bool = True

    def daily(self, symbol: str) -> pd.DataFrame:
        kwargs: dict[str, object] = {
            "interval": self.interval,
            "auto_adjust": self.auto_adjust,
            "progress": False,
        }
        if self.start or self.end:
            if self.start:
                kwargs["start"] = self.start
            if self.end:
                kwargs["end"] = self.end
        else:
            kwargs["period"] = self.period or "2y"
        frame = yf.download(symbol, **kwargs)
        normalized = normalize_price_columns(frame)
        if normalized.empty:
            raise ValueError(f"No daily data for {symbol}.")
        return normalized


# Backward-compatible alias while the codebase migrates toward provider-neutral naming.
YahooPriceProvider = YahooFinancePriceProvider
