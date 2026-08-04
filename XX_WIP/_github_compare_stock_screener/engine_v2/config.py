from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MacdConfig:
    fast: int = 8
    slow: int = 21
    signal: int = 5


@dataclass(frozen=True)
class BaselineMacdConfig:
    fast: int = 12
    slow: int = 26
    signal: int = 9


@dataclass(frozen=True)
class IndicatorConfig:
    macd: MacdConfig = MacdConfig()
    baseline_macd: BaselineMacdConfig = BaselineMacdConfig()
    rsi_period: int = 14
    adx_period: int = 14
    bollinger_period: int = 20
    bollinger_std: int = 2


@dataclass(frozen=True)
class DataConfig:
    daily_period: str = "1y"
    daily_interval: str = "1d"
    intraday_period: str = "60d"
    one_hour_interval: str = "1h"
    four_hour_interval: str = "1h"


@dataclass(frozen=True)
class EngineConfig:
    indicators: IndicatorConfig = IndicatorConfig()
    data: DataConfig = DataConfig()


DEFAULT_ENGINE_CONFIG = EngineConfig()

