
from dataclasses import dataclass, field
from typing import Dict, List, Optional
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
    macd_signal: float
    macd_histogram: float
    macd_histogram_slope: float

    spy_state: Optional[str] = None
    qqq_state: Optional[str] = None
    nifty_state: Optional[str] = None


@dataclass
class L1Result:
    symbol: str
    regime_state: str
    escalation_required: bool
    explanation: List[str] = field(default_factory=list)


@dataclass
class MACDResult:
    symbol: str
    timeframe: str

    macd: float
    signal: float
    histogram: float
    histogram_slope: float

    crossover_distance: float

    diagnostics: Dict = field(default_factory=dict)


@dataclass
class TacticalDecision:
    symbol: str
    tactical_state: str
    decision_reason: str
    confidence: str
