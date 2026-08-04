from __future__ import annotations

import csv
import random
from datetime import date
from pathlib import Path
from typing import Iterable

from stock_screener_v3.models import UniverseRecord


def _clean(value: object) -> str | None:
    text = "" if value is None else str(value).strip()
    return text or None


def _upper(value: object) -> str | None:
    text = _clean(value)
    return text.upper() if text else None


def _float_or_none(value: object) -> float | None:
    text = _clean(value)
    if text is None:
        return None
    try:
        return float(text.replace(",", ""))
    except ValueError:
        return None


def _date_or_none(value: object) -> date | None:
    text = _clean(value)
    if text is None:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _get(row: dict[str, str], *names: str) -> str | None:
    normalized = {key.strip().lower(): value for key, value in row.items()}
    for name in names:
        value = normalized.get(name.strip().lower())
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def normalize_yahoo_symbol(symbol: str, exchange: str | None = None, source_is_nse: bool = False) -> str:
    normalized = symbol.strip().upper()
    exchange_norm = (exchange or "").strip().upper()
    if normalized and "." not in normalized and (source_is_nse or exchange_norm in {"NSE", "NSI"}):
        return f"{normalized}.NS"
    if normalized and "." not in normalized and exchange_norm in {"BSE", "BOM"}:
        return f"{normalized}.BO"
    return normalized


def looks_like_nse_equity_master(fieldnames: Iterable[str]) -> bool:
    fields = {field.strip().upper() for field in fieldnames}
    return {"SYMBOL", "SERIES", "ISIN NUMBER"}.issubset(fields)


def load_universe_records(path: str | Path) -> list[UniverseRecord]:
    source = Path(path)
    records: list[UniverseRecord] = []
    seen: set[str] = set()
    with source.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            return []
        source_is_nse = looks_like_nse_equity_master(reader.fieldnames)
        for row in reader:
            symbol = _upper(_get(row, "Symbol", "Ticker"))
            if not symbol:
                continue
            exchange = _upper(_get(row, "Exchange", "Listing Exchange"))
            yahoo_symbol = _upper(_get(row, "YahooSymbol", "Yahoo Symbol")) or normalize_yahoo_symbol(
                symbol,
                exchange,
                source_is_nse,
            )
            if yahoo_symbol in seen:
                continue
            seen.add(yahoo_symbol)
            records.append(
                UniverseRecord(
                    symbol=symbol,
                    yahoo_symbol=yahoo_symbol,
                    company_name=_clean(_get(row, "CompanyName", "Company Name", "Security Name", "NAME OF COMPANY")),
                    exchange=exchange,
                    sector=_clean(_get(row, "Sector")),
                    industry=_clean(_get(row, "Industry")),
                    instrument_type=_clean(_get(row, "InstrumentType", "Instrument Type", "ETF")),
                    market_cap=_float_or_none(_get(row, "MarketCap", "Market Cap")),
                    avg_daily_volume=_float_or_none(_get(row, "AvgDailyVolume", "Average Daily Volume")),
                    source_file=str(source),
                    last_profile_refresh_date=_date_or_none(_get(row, "LastProfileRefreshDate")),
                )
            )
    return records


def filter_records(
    records: Iterable[UniverseRecord],
    sectors: Iterable[str] = (),
    exchanges: Iterable[str] = (),
) -> list[UniverseRecord]:
    sector_set = {sector.strip().upper() for sector in sectors if sector.strip()}
    exchange_set = {exchange.strip().upper() for exchange in exchanges if exchange.strip()}
    filtered: list[UniverseRecord] = []
    for record in records:
        if sector_set and (record.sector or "").strip().upper() not in sector_set:
            continue
        if exchange_set and (record.exchange or "").strip().upper() not in exchange_set:
            continue
        filtered.append(record)
    return filtered


def deterministic_sample(
    records: list[UniverseRecord],
    sample_size: int | None,
    random_seed: int | None,
) -> list[UniverseRecord]:
    if sample_size is None or sample_size >= len(records):
        return list(records)
    if sample_size < 0:
        raise ValueError("sample_size cannot be negative.")
    rng = random.Random(random_seed)
    return rng.sample(records, sample_size)
