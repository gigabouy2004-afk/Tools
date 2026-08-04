from dataclasses import dataclass, field

@dataclass
class ScreenerDefaults:
    macd_fast: int = 8
    macd_slow: int = 21
    macd_signal: int = 5
    baseline_macd_fast: int = 12
    baseline_macd_slow: int = 26
    baseline_macd_signal: int = 9
    rsi_period: int = 14
    adx_period: int = 14
    bollinger_period: int = 20
    bollinger_std: int = 2
    setup_price_lookback: int = 5
    setup_price_min_advance_pct: float = 0.5
    setup_rsi_min: float = 45.0
    setup_rsi_max: float = 78.0
    setup_macd_histogram_rising_streak: int = 2
    setup_require_ema200_bull_zone: bool = True
    setup_reject_extended_up: bool = False
    setup_reject_high_atrp: bool = False
    ema200_period: int = 200
    score_macd_weight: float = 0.5
    score_rsi_weight: float = 0.25
    score_adx_weight: float = 0.25

DEFAULTS = ScreenerDefaults()
