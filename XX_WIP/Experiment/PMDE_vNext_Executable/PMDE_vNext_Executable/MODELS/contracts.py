
from dataclasses import dataclass
from datetime import datetime


@dataclass
class MarketContext:
    symbol: str
    timestamp: datetime
    timeframe: str

    latest_price: float

    ema200: float
    ema_distance_pct: float

    macd: float
    signal: float
    histogram: float
    histogram_slope: float


@dataclass
class L1Result:
    regime_state: str
    escalation_required: bool
    reason: str


@dataclass
class MACDResult:
    timeframe: str

    macd: float
    signal: float
    histogram: float
    histogram_slope: float
    crossover_distance: float


@dataclass
class TacticalDecision:
    symbol: str
    tactical_state: str
    confidence: str
    message: str
