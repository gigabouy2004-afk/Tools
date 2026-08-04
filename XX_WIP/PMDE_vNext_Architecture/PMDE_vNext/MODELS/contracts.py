
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class BasicSnapshot:
    symbol: str
    timestamp: datetime
    latest_price: float
    source_timeframe: str
    data_fetch_timestamp: str | None = None


@dataclass
class IndicatorRequest:
    name: str
    timeframes: list[str] = field(default_factory=list)


@dataclass
class L1Result:
    symbol: str
    regime_state: str
    escalation_required: bool
    reason: str
    latest_price: float | None = None
    data_fetch_timestamp: str | None = None


@dataclass
class MACDResult:
    timeframe: str

    macd: float
    signal: float
    histogram: float
    histogram_slope: float
    spread: float
    spread_delta: float
    spread_contracting: bool
    histogram_rising_streak: int
    crossover_distance: float
    state: str


@dataclass
class EMAResult:
    timeframe: str
    ema200: float | None
    latest_price: float
    distance_pct: float | None
    slope_pct: float | None
    slope_state: str
    zone: str
    data_points: int = 0
    is_sufficient: bool = True
    reason: str | None = None


@dataclass
class TacticalDecision:
    symbol: str
    tactical_state: str
    confidence: str
    capital_action: str
    message: str
    indicators_used: list[str] = field(default_factory=list)
    computed_values: dict[str, Any] = field(default_factory=dict)
    setup_happens: bool = False
    setup_score: int | None = None
    rejection_stage: str | None = None


@dataclass
class L1Assessment:
    symbol: str
    l1_result: L1Result
    tactical_decision: TacticalDecision | None
    output_row: dict[str, Any]
    baseline_record: dict[str, Any] | None = None
