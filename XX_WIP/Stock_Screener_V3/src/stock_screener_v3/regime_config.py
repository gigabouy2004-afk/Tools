from __future__ import annotations

from dataclasses import dataclass, field

from stock_screener_v3.models import UniverseRecord


@dataclass(frozen=True)
class RegimeBenchmarkConfig:
    market_benchmarks_by_exchange: dict[str, str] = field(default_factory=dict)
    market_benchmarks_by_geography: dict[str, str] = field(default_factory=dict)
    sector_benchmarks: dict[str, str] = field(default_factory=dict)
    theme_benchmarks: dict[str, str] = field(default_factory=dict)
    default_market_benchmark: str = "SPY"

    @classmethod
    def default(cls) -> "RegimeBenchmarkConfig":
        return cls(
            market_benchmarks_by_exchange={
                "NASDAQ": "QQQ",
                "Q": "QQQ",
                "NYSE": "SPY",
                "N": "SPY",
                "AMEX": "SPY",
                "A": "SPY",
                "NSE": "^NSEI",
                "BSE": "^BSESN",
            },
            market_benchmarks_by_geography={
                "US": "SPY",
                "INDIA": "^NSEI",
            },
            sector_benchmarks={
                "COMMUNICATION SERVICES": "XLC",
                "TELECOM": "XLC",
                "TELECOMMUNICATIONS": "XLC",
                "CONSUMER DISCRETIONARY": "XLY",
                "CONSUMER STAPLES": "XLP",
                "ENERGY": "XLE",
                "FINANCIALS": "XLF",
                "HEALTH CARE": "XLV",
                "HEALTHCARE": "XLV",
                "INDUSTRIALS": "XLI",
                "BASIC MATERIALS": "XLB",
                "MATERIALS": "XLB",
                "REAL ESTATE": "XLRE",
                "TECHNOLOGY": "XLK",
                "INFORMATION TECHNOLOGY": "XLK",
                "UTILITIES": "XLU",
            },
            theme_benchmarks={},
            default_market_benchmark="SPY",
        )

    def market_symbol_for(self, record: UniverseRecord) -> str:
        exchange = _normalize(record.exchange)
        if exchange and exchange in self.market_benchmarks_by_exchange:
            return self.market_benchmarks_by_exchange[exchange]
        geography = _geography_from_exchange(exchange)
        if geography and geography in self.market_benchmarks_by_geography:
            return self.market_benchmarks_by_geography[geography]
        return self.default_market_benchmark

    def sector_symbol_for(self, record: UniverseRecord) -> str | None:
        sector = _normalize(record.sector)
        if sector and sector in self.sector_benchmarks:
            return self.sector_benchmarks[sector]
        return None

    def theme_symbol_for(self, theme: str | None) -> str | None:
        normalized = _normalize(theme)
        if normalized and normalized in self.theme_benchmarks:
            return self.theme_benchmarks[normalized]
        return None


def _normalize(value: str | None) -> str | None:
    cleaned = (value or "").strip().upper()
    return cleaned or None


def _geography_from_exchange(exchange: str | None) -> str | None:
    if exchange in {"NASDAQ", "NYSE", "AMEX", "Q", "N", "A"}:
        return "US"
    if exchange in {"NSE", "BSE"}:
        return "INDIA"
    return None
