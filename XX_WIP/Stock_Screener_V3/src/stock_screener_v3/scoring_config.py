from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScoreWeights:
    route: float
    timing: float
    structure: float
    participation: float
    context: float
    risk: float

    def as_label(self) -> str:
        return (
            f"route={_format_number(self.route)},timing={_format_number(self.timing)},"
            f"structure={_format_number(self.structure)},participation={_format_number(self.participation)},"
            f"context={_format_number(self.context)},risk={_format_number(self.risk)}"
        )


@dataclass(frozen=True)
class StageScoreThresholds:
    selected_min: float
    watch_min: float


@dataclass(frozen=True)
class StageScoringConfig:
    weights: ScoreWeights
    thresholds: StageScoreThresholds


@dataclass(frozen=True)
class RouteScoreConfig:
    status_quo: float = 0.0
    fresh_transition: float = 30.0
    near_transition: float = 18.0
    deteriorating_transition: float = 20.0
    pullback_reentry: float = 28.0
    continuation: float = 26.0
    momentum_expansion: float = 22.0
    regular_divergence: float = 30.0
    hidden_divergence: float = 28.0


@dataclass(frozen=True)
class CrossoverRouteThresholds:
    macd_zero_line_max: float = 0.0
    near_transition_distance_abs_max: float = 0.15


@dataclass(frozen=True)
class ComponentReasonThresholds:
    crossover_structure_min: float = 14.0
    crossover_participation_min: float = 10.0
    crossover_context_min: float = 8.0
    setup_structure_min: float = 14.0
    setup_participation_min: float = 10.0
    setup_context_min: float = 8.0
    divergence_structure_min: float = 12.0
    divergence_participation_min: float = 8.0
    divergence_context_min: float = 8.0
    recent_divergence_bars_max: float = 5.0


@dataclass(frozen=True)
class ComponentScoreConfig:
    timing_max: float = 20.0
    crossover_fresh_cross: float = 10.0
    crossover_histogram_direction: float = 10.0
    common_price_vs_ema20: float = 8.0
    common_price_vs_ema200: float = 7.0
    common_short_structure: float = 5.0
    common_relative_volume_min: float = 100.0
    common_relative_volume: float = 8.0
    common_directional_di: float = 7.0
    common_rsi_context: float = 5.0
    common_close_location_context: float = 5.0
    risk_base: float = 10.0
    low_liquidity_penalty: float = 5.0
    below_ema200_penalty: float = 5.0
    rsi_strong: float = 10.0
    rsi_medium: float = 6.0
    rsi_low: float = 2.0
    adx_strong_min: float = 25.0
    adx_medium_min: float = 18.0
    adx_strong: float = 10.0
    adx_medium: float = 6.0
    adx_low: float = 2.0
    setup_histogram_positive: float = 8.0
    setup_histogram_improving: float = 7.0
    setup_ema20_reclaim: float = 5.0
    setup_price_vs_ema20: float = 5.0
    setup_ema20_vs_ema50: float = 5.0
    setup_price_vs_ema200: float = 5.0
    setup_higher_low: float = 3.0
    setup_price_ladder: float = 2.0
    divergence_confirmation_confirmed: float = 10.0
    divergence_confirmation_raw: float = 4.0
    divergence_recent_bars_max: float = 5.0
    divergence_recent_bars_score: float = 10.0
    divergence_stale_bars_max: float = 12.0
    divergence_stale_bars_score: float = 6.0
    divergence_structure_max: float = 15.0
    divergence_hidden_structure: float = 5.0
    divergence_ema20_signal: float = 4.0
    divergence_price_vs_ema200: float = 4.0
    divergence_bear_price_vs_ema200: float = 3.0
    divergence_price_vs_ema20: float = 3.0
    divergence_bear_price_vs_ema20: float = 4.0
    divergence_participation_max: float = 10.0
    divergence_relative_volume: float = 4.0
    divergence_directional_di: float = 6.0
    divergence_context_max: float = 15.0
    divergence_rsi_primary: float = 8.0
    divergence_rsi_secondary: float = 4.0
    divergence_close_location: float = 7.0


@dataclass(frozen=True)
class ComponentThresholdConfig:
    histogram_positive_min: float = 0.0
    common_bullish_rsi_min: float = 45.0
    common_bullish_rsi_max: float = 70.0
    common_bearish_rsi_min: float = 30.0
    common_bearish_rsi_max: float = 55.0
    common_bullish_close_location_min: float = 60.0
    common_bearish_close_location_max: float = 40.0
    rsi_score_strong_min: float = 50.0
    rsi_score_strong_max: float = 65.0
    rsi_score_medium_low_min: float = 45.0
    rsi_score_medium_low_max: float = 50.0
    rsi_score_medium_high_min: float = 65.0
    rsi_score_medium_high_max: float = 72.0
    divergence_bullish_rsi_primary_min: float = 35.0
    divergence_bullish_rsi_primary_max: float = 60.0
    divergence_bullish_rsi_secondary_low_min: float = 30.0
    divergence_bullish_rsi_secondary_low_max: float = 35.0
    divergence_bullish_rsi_secondary_high_min: float = 60.0
    divergence_bullish_rsi_secondary_high_max: float = 68.0
    divergence_bearish_rsi_primary_min: float = 45.0
    divergence_bearish_rsi_primary_max: float = 75.0
    divergence_bearish_rsi_secondary_low_min: float = 38.0
    divergence_bearish_rsi_secondary_low_max: float = 45.0
    divergence_bearish_rsi_secondary_high_min: float = 75.0
    divergence_bearish_rsi_secondary_high_max: float = 82.0
    divergence_bullish_close_location_min: float = 45.0
    divergence_bearish_close_location_max: float = 55.0


@dataclass(frozen=True)
class RankingConfig:
    selected_rank: int = 4
    watch_rank: int = 3
    rejected_rank: int = 2
    status_quo_rank: int = 1
    priority_a_rank: int = 60
    priority_b_rank: int = 50
    priority_needs_manual_review_rank: int = 40
    priority_event_risk_rank: int = 35
    priority_low_liquidity_rank: int = 35
    priority_c_rank: int = 30
    priority_none_rank: int = 0


CROSSOVER_SCORING = StageScoringConfig(
    weights=ScoreWeights(route=30.0, timing=20.0, structure=20.0, participation=15.0, context=10.0, risk=10.0),
    thresholds=StageScoreThresholds(selected_min=72.0, watch_min=58.0),
)

SETUP_SCORING = StageScoringConfig(
    weights=ScoreWeights(route=30.0, timing=20.0, structure=20.0, participation=15.0, context=10.0, risk=10.0),
    thresholds=StageScoreThresholds(selected_min=72.0, watch_min=58.0),
)

DIVERGENCE_SCORING = StageScoringConfig(
    weights=ScoreWeights(route=30.0, timing=20.0, structure=15.0, participation=10.0, context=15.0, risk=10.0),
    thresholds=StageScoreThresholds(selected_min=72.0, watch_min=56.0),
)

ROUTE_SCORES = RouteScoreConfig()
CROSSOVER_ROUTE_THRESHOLDS = CrossoverRouteThresholds()
COMPONENT_REASON_THRESHOLDS = ComponentReasonThresholds()
COMPONENT_SCORES = ComponentScoreConfig()
COMPONENT_THRESHOLDS = ComponentThresholdConfig()
RANKING = RankingConfig()


def _format_number(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return f"{value:g}"
