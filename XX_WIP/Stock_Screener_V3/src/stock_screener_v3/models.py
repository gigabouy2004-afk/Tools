from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from enum import StrEnum
from typing import Any

import pandas as pd


class CandidateClass(StrEnum):
    SELECTED = "SELECTED"
    WATCH = "WATCH"
    REJECTED = "REJECTED"
    STATUS_QUO = "STATUS_QUO"


class ReviewPriority(StrEnum):
    A = "A"
    B = "B"
    C = "C"
    EVENT_RISK = "EVENT_RISK"
    LOW_LIQUIDITY = "LOW_LIQUIDITY"
    NEEDS_MANUAL_REVIEW = "NEEDS_MANUAL_REVIEW"
    NONE = "NONE"


@dataclass(frozen=True)
class UniverseRecord:
    symbol: str
    yahoo_symbol: str
    company_name: str | None = None
    exchange: str | None = None
    sector: str | None = None
    industry: str | None = None
    instrument_type: str | None = None
    market_cap: float | None = None
    avg_daily_volume: float | None = None
    source_file: str | None = None
    last_profile_refresh_date: date | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if self.last_profile_refresh_date is not None:
            data["last_profile_refresh_date"] = self.last_profile_refresh_date.isoformat()
        return data


@dataclass(frozen=True)
class PriceDataBundle:
    symbol: str
    daily: pd.DataFrame
    intraday: pd.DataFrame | None = None
    benchmarks: dict[str, pd.DataFrame] = field(default_factory=dict)
    as_of: pd.Timestamp | None = None
    provider: str | None = None


@dataclass(frozen=True)
class EvidencePack:
    record: UniverseRecord
    as_of: pd.Timestamp
    market_context: dict[str, Any] = field(default_factory=dict)
    sector_context: dict[str, Any] = field(default_factory=dict)
    stock_baseline: dict[str, Any] = field(default_factory=dict)
    momentum: dict[str, Any] = field(default_factory=dict)
    trend: dict[str, Any] = field(default_factory=dict)
    volatility: dict[str, Any] = field(default_factory=dict)
    volume: dict[str, Any] = field(default_factory=dict)
    structure: dict[str, Any] = field(default_factory=dict)
    risk_context: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ScoreResult:
    total_score: float
    route_score: float = 0.0
    timing_score: float = 0.0
    structure_score: float = 0.0
    participation_score: float = 0.0
    context_score: float = 0.0
    risk_score: float = 0.0
    labels: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StageEvaluation:
    symbol: str
    candidate_state: str
    candidate_class: CandidateClass
    review_priority: ReviewPriority
    confidence: str
    score: ScoreResult
    reason_codes: tuple[str, ...] = ()
    risk_tags: tuple[str, ...] = ()
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def is_candidate(self) -> bool:
        return self.candidate_class in {CandidateClass.SELECTED, CandidateClass.WATCH}

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["candidate_class"] = self.candidate_class.value
        data["review_priority"] = self.review_priority.value
        return data


@dataclass(frozen=True)
class BacktestRunConfig:
    universe_file: str
    d_date: date
    stage_families: tuple[str, ...]
    forward_days: tuple[int, ...] = (1, 2, 5)
    sector_filters: tuple[str, ...] = ()
    exchange_filters: tuple[str, ...] = ()
    sample_mode: str = "full"
    sample_size: int | None = None
    random_seed: int | None = None
    engine_version: str = "v3"


@dataclass(frozen=True)
class BacktestResult:
    config: BacktestRunConfig
    generated_at: datetime
    symbols_attempted: int
    symbols_processed: int
    symbols_skipped: int
    candidates_found: int
    detail_rows: tuple[dict[str, Any], ...] = ()
    skip_reasons: dict[str, int] = field(default_factory=dict)

    @property
    def candidate_density(self) -> float:
        if self.symbols_processed == 0:
            return 0.0
        return self.candidates_found / self.symbols_processed

    def summary_dict(self) -> dict[str, Any]:
        return {
            "d_date": self.config.d_date.isoformat(),
            "symbols_attempted": self.symbols_attempted,
            "symbols_processed": self.symbols_processed,
            "symbols_skipped": self.symbols_skipped,
            "candidates_found": self.candidates_found,
            "candidate_density": self.candidate_density,
            "skip_reasons": dict(self.skip_reasons),
        }
