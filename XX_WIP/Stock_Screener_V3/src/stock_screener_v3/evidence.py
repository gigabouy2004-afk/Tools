from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from stock_screener_v3.baseline_router import classify_benchmark_regime
from stock_screener_v3.indicators import adx, bollinger, ema, latest_number, macd, rsi
from stock_screener_v3.models import EvidencePack, PriceDataBundle, UniverseRecord


MIN_DAILY_BARS = 60


@dataclass(frozen=True)
class EvidenceBuilder:
    min_daily_bars: int = MIN_DAILY_BARS

    def build(self, record: UniverseRecord, prices: PriceDataBundle) -> EvidencePack:
        daily = _normalized_daily(prices.daily)
        if len(daily) < self.min_daily_bars:
            raise ValueError(f"Insufficient daily history for {record.yahoo_symbol}: {len(daily)} bars.")

        close = daily["Close"]
        high = daily["High"]
        low = daily["Low"]
        volume = daily["Volume"]
        open_ = daily["Open"]

        macd_frame = macd(close)
        adx_frame = adx(high, low, close)
        bollinger_frame = bollinger(close)
        ema20 = ema(close, 20)
        ema50 = ema(close, 50)
        ema200 = ema(close, 200)

        latest_close = latest_number(close)
        latest_high = latest_number(high)
        latest_low = latest_number(low)
        latest_open = latest_number(open_)
        latest_volume = latest_number(volume)
        volume20 = latest_number(volume.rolling(20, min_periods=10).mean())
        daily_range = (high - low).replace(0, pd.NA)
        close_location = ((close - low) / daily_range) * 100
        range20 = latest_number((high - low).rolling(20, min_periods=10).mean())
        latest_range = latest_number(high - low)
        range_vs_20 = _pct(latest_range, range20)
        high20 = latest_number(high.rolling(20, min_periods=10).max())
        high60 = latest_number(high.rolling(60, min_periods=30).max())

        latest_macd = latest_number(macd_frame["MACD"])
        latest_signal = latest_number(macd_frame["Signal"])
        latest_hist = latest_number(macd_frame["Histogram"])
        prev_hist = _previous_number(macd_frame["Histogram"])
        macd_distance = None if latest_macd is None or latest_signal is None else round(latest_macd - latest_signal, 4)
        macd_state = _macd_state(latest_macd, latest_signal)
        crossover_state = _crossover_state(macd_frame["MACD"], macd_frame["Signal"])

        latest_ema20 = latest_number(ema20)
        latest_ema50 = latest_number(ema50)
        latest_ema200 = latest_number(ema200)
        distance_to_ema200 = _distance_pct(latest_close, latest_ema200)
        distance_to_20_high = _distance_pct(latest_close, high20)
        distance_to_60_high = _distance_pct(latest_close, high60)

        latest_adx = latest_number(adx_frame["ADX"])
        plus_di = latest_number(adx_frame["PlusDI"])
        minus_di = latest_number(adx_frame["MinusDI"])
        bollinger_pct_b = latest_number(bollinger_frame["BollingerPctB"])
        bollinger_bandwidth = latest_number(bollinger_frame["BollingerBandwidthPct"])

        stock_baseline = {
            "LatestPrice": latest_close,
            "LatestOpen": latest_open,
            "LatestHigh": latest_high,
            "LatestLow": latest_low,
            "DailyCloseLocationPct": latest_number(close_location),
            "DailyRangeVs20Avg": range_vs_20,
        }
        momentum = {
            "RSI_1D": latest_number(rsi(close)),
            "MACD_1D_State": macd_state,
            "MACD_1D_CrossoverState": crossover_state,
            "MACD_1D_Value": latest_macd,
            "MACD_1D_Signal": latest_signal,
            "MACD_1D_Histogram": latest_hist,
            "MACD_1D_PreviousHistogram": prev_hist,
            "MACD_1D_CrossoverDistance": macd_distance,
            "MACDHistogramImproving": _is_improving(prev_hist, latest_hist),
        }
        trend = {
            "EMA20": latest_ema20,
            "EMA50": latest_ema50,
            "EMA200": latest_ema200,
            "DistanceToEMA200Pct": distance_to_ema200,
            "EMA200SlopeState": _slope_state(ema200, lookback=10),
            "ADX_1D": latest_adx,
            "ADX_State": _adx_state(latest_adx),
            "PlusDI_1D": plus_di,
            "MinusDI_1D": minus_di,
        }
        volatility = {
            "Bollinger_PctB": bollinger_pct_b,
            "Bollinger_BandwidthPct": bollinger_bandwidth,
            "DistanceTo20DHighPct": distance_to_20_high,
            "DistanceTo60DHighPct": distance_to_60_high,
        }
        volume_context = {
            "VolumeLatest": latest_volume,
            "Volume20Avg": volume20,
            "IntradayVolumeVs20Avg": _pct(latest_volume, volume20),
        }
        structure = {
            "EMA20_Above": _above(latest_close, latest_ema20),
            "EMA20_Below": _below(latest_close, latest_ema20),
            "EMA20_Reclaim": _reclaimed(close, ema20),
            "HigherLow_5D": _higher_low(low, lookback=5),
            "LowerHigh_5D": _lower_high(high, lookback=5),
            "RangeBreakoutUp_20D": _breakout(close, high, lookback=20),
            "RangeBreakdownDown_20D": _breakdown(close, low, lookback=20),
            "PriceLadder_Passed": _above(latest_close, latest_ema20) and _above(latest_ema20, latest_ema50),
        }
        structure.update(_divergence_context(close, macd_frame["Histogram"]))

        return EvidencePack(
            record=record,
            as_of=prices.as_of or pd.Timestamp(daily.index.max()),
            market_context=_market_context(prices),
            sector_context=_sector_context(prices),
            stock_baseline=stock_baseline,
            momentum=momentum,
            trend=trend,
            volatility=volatility,
            volume=volume_context,
            structure=structure,
            risk_context={
                "LowLiquidity": bool(latest_volume is not None and latest_volume < 100_000),
                "BelowEMA200": bool(latest_close is not None and latest_ema200 is not None and latest_close < latest_ema200),
            },
        )


def evidence_to_diagnostics(evidence: EvidencePack) -> dict[str, Any]:
    diagnostics: dict[str, Any] = {}
    for section in (
        evidence.market_context,
        evidence.sector_context,
        evidence.stock_baseline,
        evidence.momentum,
        evidence.trend,
        evidence.volatility,
        evidence.volume,
        evidence.structure,
        evidence.risk_context,
    ):
        diagnostics.update(section)
    return diagnostics


def _market_context(prices: PriceDataBundle) -> dict[str, Any]:
    benchmark = _benchmark_frame(prices, "market")
    return {"MarketRegime": classify_benchmark_regime(benchmark).value}


def _sector_context(prices: PriceDataBundle) -> dict[str, Any]:
    benchmark = _benchmark_frame(prices, "sector")
    return {"SectorRegime": classify_benchmark_regime(benchmark).value}


def _benchmark_frame(prices: PriceDataBundle, kind: str) -> pd.DataFrame | None:
    if kind in prices.benchmarks:
        return prices.benchmarks[kind]
    aliases = {
        "market": ("SPY", "QQQ", "NIFTY50", "^NSEI"),
        "sector": ("SECTOR",),
    }
    for alias in aliases[kind]:
        if alias in prices.benchmarks:
            return prices.benchmarks[alias]
    return None


def _normalized_daily(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"Open", "High", "Low", "Close", "Volume"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Missing daily price columns: {', '.join(sorted(missing))}.")
    normalized = frame.copy()
    normalized.index = pd.to_datetime(normalized.index)
    return normalized.sort_index()


def _previous_number(series: pd.Series) -> float | None:
    cleaned = pd.to_numeric(series, errors="coerce").dropna()
    if len(cleaned) < 2:
        return None
    return round(float(cleaned.iloc[-2]), 4)


def _macd_state(value: float | None, signal: float | None) -> str:
    if value is None or signal is None:
        return "UNKNOWN"
    return "BULLISH" if value >= signal else "BEARISH"


def _crossover_state(macd_line: pd.Series, signal_line: pd.Series) -> str:
    if len(macd_line.dropna()) < 2 or len(signal_line.dropna()) < 2:
        return "UNKNOWN"
    previous = float(macd_line.iloc[-2] - signal_line.iloc[-2])
    current = float(macd_line.iloc[-1] - signal_line.iloc[-1])
    if previous <= 0 < current:
        return "BULL_CROSS"
    if previous >= 0 > current:
        return "BEAR_CROSS"
    if current > 0:
        return "ABOVE_SIGNAL"
    if current < 0:
        return "BELOW_SIGNAL"
    return "AT_SIGNAL"


def _is_improving(previous: float | None, current: float | None) -> bool:
    return bool(previous is not None and current is not None and current > previous)


def _distance_pct(value: float | None, reference: float | None) -> float | None:
    if value is None or reference in (None, 0):
        return None
    return round(((value - reference) / reference) * 100, 4)


def _pct(value: float | None, reference: float | None) -> float | None:
    if value is None or reference in (None, 0):
        return None
    return round((value / reference) * 100, 4)


def _slope_state(series: pd.Series, lookback: int) -> str:
    cleaned = pd.to_numeric(series, errors="coerce").dropna()
    if len(cleaned) <= lookback:
        return "UNKNOWN"
    return "RISING" if float(cleaned.iloc[-1]) > float(cleaned.iloc[-lookback - 1]) else "FALLING"


def _adx_state(value: float | None) -> str:
    if value is None:
        return "UNKNOWN"
    if value >= 25:
        return "TRENDING"
    if value >= 18:
        return "DEVELOPING"
    return "WEAK"


def _above(value: float | None, reference: float | None) -> bool:
    return bool(value is not None and reference is not None and value >= reference)


def _below(value: float | None, reference: float | None) -> bool:
    return bool(value is not None and reference is not None and value <= reference)


def _reclaimed(close: pd.Series, reference: pd.Series) -> bool:
    if len(close.dropna()) < 2 or len(reference.dropna()) < 2:
        return False
    return bool(close.iloc[-2] < reference.iloc[-2] and close.iloc[-1] >= reference.iloc[-1])


def _higher_low(low: pd.Series, lookback: int) -> bool:
    cleaned = pd.to_numeric(low, errors="coerce").dropna()
    if len(cleaned) <= lookback:
        return False
    return bool(cleaned.iloc[-1] > cleaned.iloc[-lookback:-1].min())


def _lower_high(high: pd.Series, lookback: int) -> bool:
    cleaned = pd.to_numeric(high, errors="coerce").dropna()
    if len(cleaned) <= lookback:
        return False
    return bool(cleaned.iloc[-1] < cleaned.iloc[-lookback:-1].max())


def _breakout(close: pd.Series, high: pd.Series, lookback: int) -> bool:
    if len(close.dropna()) <= lookback or len(high.dropna()) <= lookback:
        return False
    prior_high = high.iloc[-lookback - 1 : -1].max()
    return bool(close.iloc[-1] > prior_high)


def _breakdown(close: pd.Series, low: pd.Series, lookback: int) -> bool:
    if len(close.dropna()) <= lookback or len(low.dropna()) <= lookback:
        return False
    prior_low = low.iloc[-lookback - 1 : -1].min()
    return bool(close.iloc[-1] < prior_low)


def _divergence_context(close: pd.Series, momentum: pd.Series, lookback: int = 60, recency: int = 12) -> dict[str, object]:
    low_candidate = _divergence_from_swings(
        close=close,
        momentum=momentum,
        swing_kind="LOW",
        lookback=lookback,
        recency=recency,
    )
    high_candidate = _divergence_from_swings(
        close=close,
        momentum=momentum,
        swing_kind="HIGH",
        lookback=lookback,
        recency=recency,
    )
    for candidate in (low_candidate, high_candidate):
        if candidate["DivergenceRouteCandidate"] != "NONE":
            return candidate
    return _empty_divergence_context()


def _divergence_from_swings(
    *,
    close: pd.Series,
    momentum: pd.Series,
    swing_kind: str,
    lookback: int,
    recency: int,
) -> dict[str, object]:
    close_values = pd.to_numeric(close, errors="coerce").dropna()
    momentum_values = pd.to_numeric(momentum, errors="coerce")
    if len(close_values) < 10:
        return _empty_divergence_context()

    swings = _swing_points(close_values.tail(lookback), kind=swing_kind)
    if len(swings) < 2:
        return _empty_divergence_context()

    previous_index, previous_price = swings[-2]
    latest_index, latest_price = swings[-1]
    bars_ago = _bars_ago(close_values, latest_index)
    if bars_ago is None or bars_ago > recency:
        return _empty_divergence_context()

    previous_momentum = _value_at(momentum_values, previous_index)
    latest_momentum = _value_at(momentum_values, latest_index)
    if previous_momentum is None or latest_momentum is None:
        return _empty_divergence_context()

    price_swing = _price_swing_label(swing_kind, previous_price, latest_price)
    momentum_swing = _momentum_swing_label(swing_kind, previous_momentum, latest_momentum)
    latest_close = latest_number(close_values)
    confirmation = _divergence_confirmation(swing_kind, latest_close, latest_price)
    candidate = _divergence_candidate(price_swing, momentum_swing)

    return {
        "DivergenceRouteCandidate": candidate,
        "DivergencePriceSwing": price_swing,
        "DivergenceMomentumSwing": momentum_swing,
        "DivergenceBarsAgo": bars_ago,
        "DivergenceConfirmationState": confirmation,
        "DivergencePreviousPriceSwingValue": round(float(previous_price), 4),
        "DivergenceLatestPriceSwingValue": round(float(latest_price), 4),
        "DivergencePreviousMomentumSwingValue": round(float(previous_momentum), 4),
        "DivergenceLatestMomentumSwingValue": round(float(latest_momentum), 4),
    }


def _empty_divergence_context() -> dict[str, object]:
    return {
        "DivergenceRouteCandidate": "NONE",
        "DivergencePriceSwing": "NONE",
        "DivergenceMomentumSwing": "NONE",
        "DivergenceBarsAgo": None,
        "DivergenceConfirmationState": "NONE",
        "DivergencePreviousPriceSwingValue": None,
        "DivergenceLatestPriceSwingValue": None,
        "DivergencePreviousMomentumSwingValue": None,
        "DivergenceLatestMomentumSwingValue": None,
    }


def _swing_points(series: pd.Series, kind: str, width: int = 2) -> list[tuple[pd.Timestamp, float]]:
    points: list[tuple[pd.Timestamp, float]] = []
    values = pd.to_numeric(series, errors="coerce").dropna()
    if len(values) < (width * 2) + 1:
        return points
    for index in range(width, len(values) - width):
        window = values.iloc[index - width : index + width + 1]
        value = float(values.iloc[index])
        if kind == "LOW" and value <= float(window.min()):
            points.append((values.index[index], value))
        elif kind == "HIGH" and value >= float(window.max()):
            points.append((values.index[index], value))
    return points


def _bars_ago(series: pd.Series, index: pd.Timestamp) -> int | None:
    try:
        location = series.index.get_loc(index)
    except KeyError:
        return None
    if not isinstance(location, int):
        return None
    return len(series) - 1 - location


def _value_at(series: pd.Series, index: pd.Timestamp) -> float | None:
    try:
        value = series.loc[index]
    except KeyError:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _price_swing_label(swing_kind: str, previous: float, latest: float) -> str:
    if swing_kind == "LOW":
        return "LOWER_LOW" if latest < previous else "HIGHER_LOW"
    return "HIGHER_HIGH" if latest > previous else "LOWER_HIGH"


def _momentum_swing_label(swing_kind: str, previous: float, latest: float) -> str:
    if swing_kind == "LOW":
        return "HIGHER_LOW" if latest > previous else "LOWER_LOW"
    return "LOWER_HIGH" if latest < previous else "HIGHER_HIGH"


def _divergence_candidate(price_swing: str, momentum_swing: str) -> str:
    if price_swing == "LOWER_LOW" and momentum_swing == "HIGHER_LOW":
        return "BULLISH_DIVERGENCE"
    if price_swing == "HIGHER_HIGH" and momentum_swing == "LOWER_HIGH":
        return "BEARISH_DIVERGENCE"
    if price_swing == "HIGHER_LOW" and momentum_swing == "LOWER_LOW":
        return "HIDDEN_BULLISH_DIVERGENCE"
    if price_swing == "LOWER_HIGH" and momentum_swing == "HIGHER_HIGH":
        return "HIDDEN_BEARISH_DIVERGENCE"
    return "NONE"


def _divergence_confirmation(swing_kind: str, latest_close: float | None, swing_price: float) -> str:
    if latest_close is None:
        return "RAW"
    if swing_kind == "LOW" and latest_close > swing_price:
        return "CONFIRMED"
    if swing_kind == "HIGH" and latest_close < swing_price:
        return "CONFIRMED"
    return "RAW"

