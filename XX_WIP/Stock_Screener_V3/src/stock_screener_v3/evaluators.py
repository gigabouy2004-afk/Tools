from __future__ import annotations

from dataclasses import dataclass, replace

from stock_screener_v3.baseline_router import StockTraversalPlan, apply_traversal_plan, build_stock_traversal_plan
from stock_screener_v3.evidence import EvidenceBuilder, evidence_to_diagnostics
from stock_screener_v3.models import (
    CandidateClass,
    EvidencePack,
    PriceDataBundle,
    ReviewPriority,
    ScoreResult,
    StageEvaluation,
    UniverseRecord,
)
from stock_screener_v3 import scoring_config as score_config


@dataclass(frozen=True)
class CrossoverRoute:
    candidate_state: str
    opportunity_type: str
    direction: str
    route_score: float
    reason_code: str
    timing_profile: str

    @property
    def is_valid(self) -> bool:
        return self.route_score > 0


@dataclass(frozen=True)
class DivergenceRoute:
    candidate_state: str
    opportunity_type: str
    direction: str
    divergence_type: str
    route_score: float
    reason_code: str
    timing_profile: str

    @property
    def is_valid(self) -> bool:
        return self.route_score > 0


@dataclass(frozen=True)
class StageRankingDecision:
    winner: StageEvaluation
    evaluated_families: tuple[str, ...]
    candidate_states: tuple[str, ...]
    candidate_classes: tuple[str, ...]
    review_priorities: tuple[str, ...]
    total_scores: tuple[float, ...]

    def to_diagnostics(self) -> dict[str, object]:
        return {
            "RankingContractVersion": "v1",
            "RankingRule": "candidate_class>review_priority>total_score>route_score>selected_family_order",
            "RankingWinnerFamily": str(self.winner.diagnostics.get("StageFamily") or ""),
            "RankingEvaluatedFamilies": ",".join(self.evaluated_families),
            "RankingCandidateStates": "|".join(self.candidate_states),
            "RankingCandidateClasses": "|".join(self.candidate_classes),
            "RankingReviewPriorities": "|".join(self.review_priorities),
            "RankingTotalScores": "|".join(f"{score:.2f}" for score in self.total_scores),
        }


@dataclass(frozen=True)
class CrossoverEvaluator:
    evidence_builder: EvidenceBuilder = EvidenceBuilder()

    def evaluate(self, record: UniverseRecord, prices: PriceDataBundle) -> StageEvaluation:
        evidence = self.evidence_builder.build(record, prices)
        return evaluate_crossover(evidence)


@dataclass(frozen=True)
class MomentumSetupEvaluator:
    evidence_builder: EvidenceBuilder = EvidenceBuilder()

    def evaluate(self, record: UniverseRecord, prices: PriceDataBundle) -> StageEvaluation:
        evidence = self.evidence_builder.build(record, prices)
        return evaluate_momentum_setup(evidence)


@dataclass(frozen=True)
class DivergenceEvaluator:
    evidence_builder: EvidenceBuilder = EvidenceBuilder()

    def evaluate(self, record: UniverseRecord, prices: PriceDataBundle) -> StageEvaluation:
        evidence = self.evidence_builder.build(record, prices)
        return evaluate_divergence(evidence)


@dataclass(frozen=True)
class StageFamilyEvaluator:
    stage_families: tuple[str, ...] = ("CROSSOVER", "MOMENTUM_SETUP", "DIVERGENCE")
    evidence_builder: EvidenceBuilder = EvidenceBuilder()

    def evaluate(self, record: UniverseRecord, prices: PriceDataBundle) -> StageEvaluation:
        evidence = self.evidence_builder.build(record, prices)
        traversal_plan = build_stock_traversal_plan(evidence, self.stage_families)
        evaluations: list[StageEvaluation] = []
        for family in traversal_plan.selected_stage_families:
            if family not in traversal_plan.evaluable_stage_families:
                evaluations.append(_traversal_blocked_evaluation(evidence, traversal_plan, family))
            elif family == "CROSSOVER":
                evaluations.append(apply_traversal_plan(_with_stage_family(evaluate_crossover(evidence), family), traversal_plan))
            elif family == "MOMENTUM_SETUP":
                evaluations.append(apply_traversal_plan(_with_stage_family(evaluate_momentum_setup(evidence), family), traversal_plan))
            elif family == "DIVERGENCE":
                evaluations.append(apply_traversal_plan(_with_stage_family(evaluate_divergence(evidence), family), traversal_plan))
            else:
                raise ValueError(f"Unsupported stage family: {family}.")
        if not evaluations:
            raise ValueError("At least one stage family is required.")
        return rank_stage_evaluations(evaluations).winner


def evaluate_crossover(evidence: EvidencePack) -> StageEvaluation:
    scoring = score_config.CROSSOVER_SCORING
    diagnostics = evidence_to_diagnostics(evidence)
    momentum = evidence.momentum
    trend = evidence.trend
    volume = evidence.volume
    structure = evidence.structure
    risk = evidence.risk_context

    crossover_state = str(momentum.get("MACD_1D_CrossoverState") or "UNKNOWN")
    macd_value = _number(momentum.get("MACD_1D_Value"))
    macd_signal = _number(momentum.get("MACD_1D_Signal"))
    macd_distance = _number(momentum.get("MACD_1D_CrossoverDistance"))
    histogram = _number(momentum.get("MACD_1D_Histogram"))
    previous_histogram = _number(momentum.get("MACD_1D_PreviousHistogram"))
    rsi = _number(momentum.get("RSI_1D"))
    close_location = _number(evidence.stock_baseline.get("DailyCloseLocationPct"))
    volume_vs_20 = _number(volume.get("IntradayVolumeVs20Avg"))
    latest_price = _number(evidence.stock_baseline.get("LatestPrice"))
    ema20 = _number(trend.get("EMA20"))
    ema50 = _number(trend.get("EMA50"))
    ema200 = _number(trend.get("EMA200"))
    plus_di = _number(trend.get("PlusDI_1D"))
    minus_di = _number(trend.get("MinusDI_1D"))

    histogram_improving = bool(momentum.get("MACDHistogramImproving"))
    histogram_deteriorating = _is_deteriorating(previous_histogram, histogram)
    route = _classify_crossover_route(
        crossover_state=crossover_state,
        macd_value=macd_value,
        macd_signal=macd_signal,
        macd_distance=macd_distance,
        histogram=histogram,
        histogram_improving=histogram_improving,
        histogram_deteriorating=histogram_deteriorating,
        latest_price=latest_price,
        ema20=ema20,
        ema50=ema50,
        plus_di=plus_di,
        minus_di=minus_di,
        ema20_reclaim=bool(structure.get("EMA20_Reclaim")),
        higher_low=bool(structure.get("HigherLow_5D")),
        lower_high=bool(structure.get("LowerHigh_5D")),
        ema20_below=bool(structure.get("EMA20_Below")),
        price_ladder=bool(structure.get("PriceLadder_Passed")),
    )
    route_score = route.route_score
    timing_score = _timing_score(route.direction, crossover_state, histogram_improving, histogram_deteriorating)
    structure_score = _structure_score(
        route.direction,
        latest_price,
        ema20,
        ema200,
        bool(structure.get("HigherLow_5D")),
        bool(structure.get("LowerHigh_5D")),
    )
    participation_score = _participation_score(route.direction, volume_vs_20, plus_di, minus_di)
    context_score = _context_score(route.direction, rsi, close_location)
    risk_score = _risk_score(route.direction, bool(risk.get("LowLiquidity")), bool(risk.get("BelowEMA200")))
    total = round(route_score + timing_score + structure_score + participation_score + context_score + risk_score, 2)

    reason_codes: list[str] = []
    risk_tags: list[str] = []
    reason_codes.append(route.reason_code)

    if structure_score >= score_config.COMPONENT_REASON_THRESHOLDS.crossover_structure_min:
        reason_codes.append("CONSTRUCTIVE_PRICE_STRUCTURE" if route.direction == "BULLISH" else "BEARISH_PRICE_STRUCTURE")
    if participation_score >= score_config.COMPONENT_REASON_THRESHOLDS.crossover_participation_min:
        reason_codes.append("PARTICIPATION_SUPPORT" if route.direction == "BULLISH" else "SELLER_PARTICIPATION_SUPPORT")
    if context_score >= score_config.COMPONENT_REASON_THRESHOLDS.crossover_context_min:
        reason_codes.append("ACCEPTANCE_SUPPORT" if route.direction == "BULLISH" else "BEARISH_ACCEPTANCE_SUPPORT")
    if risk.get("LowLiquidity"):
        risk_tags.append("LOW_LIQUIDITY")
    if route.direction == "BULLISH" and risk.get("BelowEMA200"):
        risk_tags.append("BELOW_EMA200")

    if not route.is_valid:
        candidate_state = "STATUS_QUO"
        candidate_class = CandidateClass.STATUS_QUO
        priority = ReviewPriority.NONE
        confidence = "LOW"
    elif total >= scoring.thresholds.selected_min and not risk_tags:
        candidate_state = route.candidate_state
        candidate_class = CandidateClass.SELECTED
        priority = ReviewPriority.A
        confidence = "HIGH"
    elif total >= scoring.thresholds.watch_min:
        candidate_state = route.candidate_state
        candidate_class = CandidateClass.WATCH
        priority = ReviewPriority.B if not risk_tags else ReviewPriority.NEEDS_MANUAL_REVIEW
        confidence = "MEDIUM"
    else:
        candidate_state = route.candidate_state
        candidate_class = CandidateClass.REJECTED
        priority = ReviewPriority.C
        confidence = "LOW"

    diagnostics.update(
        {
            "CandidateStateRaw": candidate_state,
            "WeightedScore": total if candidate_class != CandidateClass.STATUS_QUO else None,
            "MACDScore": route_score + timing_score,
            "RSIScore": _rsi_score(rsi),
            "ADXScore": _adx_score(_number(trend.get("ADX_1D"))),
            "ScoreWeights": scoring.weights.as_label(),
            "ConfirmationScore": round(timing_score + structure_score + participation_score, 2),
            "QualityContextScore": round(context_score + risk_score, 2),
            "CrossoverInternalState": crossover_state,
            "CrossoverOpportunityType": route.opportunity_type,
            "CrossoverDirection": route.direction,
            "CrossoverConfidence": confidence,
            "CrossoverQualityScore": total,
            "CrossoverQualityComponents": (
                f"route={route_score};timing={timing_score};structure={structure_score};"
                f"participation={participation_score};context={context_score};risk={risk_score}"
            ),
            "CrossoverTimingProfile": route.timing_profile,
            "CrossoverReason": "; ".join(reason_codes),
            "CrossoverReasonCodes": ",".join(reason_codes),
            "SetupPassed": candidate_class in {CandidateClass.SELECTED, CandidateClass.WATCH},
            "SetupScore": total,
        }
    )

    return StageEvaluation(
        symbol=evidence.record.yahoo_symbol,
        candidate_state=candidate_state,
        candidate_class=candidate_class,
        review_priority=priority,
        confidence=confidence,
        score=ScoreResult(
            total_score=total,
            route_score=route_score,
            timing_score=timing_score,
            structure_score=structure_score,
            participation_score=participation_score,
            context_score=context_score,
            risk_score=risk_score,
            labels=tuple(reason_codes),
        ),
        reason_codes=tuple(reason_codes),
        risk_tags=tuple(risk_tags),
        diagnostics=diagnostics,
    )


def _classify_crossover_route(
    *,
    crossover_state: str,
    macd_value: float | None,
    macd_signal: float | None,
    macd_distance: float | None,
    histogram: float | None,
    histogram_improving: bool,
    histogram_deteriorating: bool,
    latest_price: float | None,
    ema20: float | None,
    ema50: float | None,
    plus_di: float | None,
    minus_di: float | None,
    ema20_reclaim: bool,
    higher_low: bool,
    lower_high: bool,
    ema20_below: bool,
    price_ladder: bool,
) -> CrossoverRoute:
    if crossover_state == "BULL_CROSS":
        if not _macd_pair_is_below_zero_line(macd_value, macd_signal):
            return CrossoverRoute(
                candidate_state="STATUS_QUO",
                opportunity_type="BULLISH_ABOVE_ZERO_CONTINUATION",
                direction="NONE",
                route_score=score_config.ROUTE_SCORES.status_quo,
                reason_code="BULL_CROSS_ABOVE_ZERO_LINE_CONTINUATION",
                timing_profile="none",
            )
        return CrossoverRoute(
            candidate_state="PRE_BULL_CROSSOVER",
            opportunity_type="BULLISH_TRANSITION_CROSSOVER",
            direction="BULLISH",
            route_score=score_config.ROUTE_SCORES.fresh_transition,
            reason_code="DAILY_MACD_BULL_CROSS",
            timing_profile="fresh",
        )
    if crossover_state == "BEAR_CROSS":
        return CrossoverRoute(
            candidate_state="PRE_BEAR_CROSSOVER",
            opportunity_type="BEARISH_TRANSITION_CROSSOVER",
            direction="BEARISH",
            route_score=score_config.ROUTE_SCORES.fresh_transition,
            reason_code="DAILY_MACD_BEAR_CROSS",
            timing_profile="fresh",
        )
    if crossover_state == "ABOVE_SIGNAL":
        if (
            histogram_deteriorating
            and macd_distance is not None
            and histogram is not None
            and macd_distance < score_config.CROSSOVER_ROUTE_THRESHOLDS.near_transition_distance_abs_max
            and histogram < score_config.CROSSOVER_ROUTE_THRESHOLDS.near_transition_distance_abs_max
            and (ema20_below or lower_high or _di_supports_bears(plus_di, minus_di))
        ):
            return CrossoverRoute(
                candidate_state="PRE_BEAR_CROSSOVER",
                opportunity_type="BEARISH_NEAR_TRANSITION",
                direction="BEARISH",
                route_score=score_config.ROUTE_SCORES.near_transition,
                reason_code="DAILY_MACD_NEAR_BEAR_TRANSITION",
                timing_profile="early",
            )
    if crossover_state == "BELOW_SIGNAL" and histogram_deteriorating and (ema20_below or lower_high):
        return CrossoverRoute(
            candidate_state="PRE_BEAR_CROSSOVER",
            opportunity_type="BEARISH_BELOW_SIGNAL_DETERIORATING",
            direction="BEARISH",
            route_score=score_config.ROUTE_SCORES.deteriorating_transition,
            reason_code="DAILY_MACD_BELOW_SIGNAL_DETERIORATING",
            timing_profile="developing",
        )
    if (
        crossover_state == "BELOW_SIGNAL"
        and histogram_improving
        and macd_distance is not None
        and histogram is not None
        and macd_distance > -score_config.CROSSOVER_ROUTE_THRESHOLDS.near_transition_distance_abs_max
        and histogram > -score_config.CROSSOVER_ROUTE_THRESHOLDS.near_transition_distance_abs_max
        and _macd_pair_is_below_zero_line(macd_value, macd_signal)
    ):
        return CrossoverRoute(
            candidate_state="PRE_BULL_CROSSOVER",
            opportunity_type="BULLISH_NEAR_TRANSITION",
            direction="BULLISH",
            route_score=score_config.ROUTE_SCORES.near_transition,
            reason_code="DAILY_MACD_NEAR_BULL_TRANSITION",
            timing_profile="early",
        )
    return CrossoverRoute(
        candidate_state="STATUS_QUO",
        opportunity_type="NO_CROSSOVER_ROUTE",
        direction="NONE",
        route_score=score_config.ROUTE_SCORES.status_quo,
        reason_code="NO_CROSSOVER_ROUTE",
        timing_profile="none",
    )


def _macd_pair_is_below_zero_line(macd_value: float | None, macd_signal: float | None) -> bool:
    if macd_value is None or macd_signal is None:
        return False
    return (
        macd_value <= score_config.CROSSOVER_ROUTE_THRESHOLDS.macd_zero_line_max
        and macd_signal <= score_config.CROSSOVER_ROUTE_THRESHOLDS.macd_zero_line_max
    )


def evaluate_momentum_setup(evidence: EvidencePack) -> StageEvaluation:
    scoring = score_config.SETUP_SCORING
    diagnostics = evidence_to_diagnostics(evidence)
    momentum = evidence.momentum
    trend = evidence.trend
    volume = evidence.volume
    structure = evidence.structure
    risk = evidence.risk_context

    crossover_state = str(momentum.get("MACD_1D_CrossoverState") or "UNKNOWN")
    histogram = _number(momentum.get("MACD_1D_Histogram"))
    rsi = _number(momentum.get("RSI_1D"))
    close_location = _number(evidence.stock_baseline.get("DailyCloseLocationPct"))
    volume_vs_20 = _number(volume.get("IntradayVolumeVs20Avg"))
    latest_price = _number(evidence.stock_baseline.get("LatestPrice"))
    ema20 = _number(trend.get("EMA20"))
    ema50 = _number(trend.get("EMA50"))
    ema200 = _number(trend.get("EMA200"))
    plus_di = _number(trend.get("PlusDI_1D"))
    minus_di = _number(trend.get("MinusDI_1D"))

    histogram_improving = bool(momentum.get("MACDHistogramImproving"))
    route = _classify_momentum_route(
        crossover_state=crossover_state,
        histogram=histogram,
        histogram_improving=histogram_improving,
        latest_price=latest_price,
        ema20=ema20,
        ema50=ema50,
        ema20_reclaim=bool(structure.get("EMA20_Reclaim")),
        higher_low=bool(structure.get("HigherLow_5D")),
        price_ladder=bool(structure.get("PriceLadder_Passed")),
        plus_di=plus_di,
        minus_di=minus_di,
    )
    route_score = route.route_score
    timing_score = _momentum_timing_score(histogram, histogram_improving, bool(structure.get("EMA20_Reclaim")))
    structure_score = _momentum_structure_score(
        latest_price,
        ema20,
        ema50,
        ema200,
        bool(structure.get("HigherLow_5D")),
        bool(structure.get("PriceLadder_Passed")),
    )
    participation_score = _participation_score("BULLISH", volume_vs_20, plus_di, minus_di)
    context_score = _context_score("BULLISH", rsi, close_location)
    risk_score = _risk_score("BULLISH", bool(risk.get("LowLiquidity")), bool(risk.get("BelowEMA200")))
    total = round(route_score + timing_score + structure_score + participation_score + context_score + risk_score, 2)

    reason_codes: list[str] = [route.reason_code]
    risk_tags: list[str] = []
    if structure_score >= score_config.COMPONENT_REASON_THRESHOLDS.setup_structure_min:
        reason_codes.append("BULL_PHASE_STRUCTURE_SUPPORT")
    if participation_score >= score_config.COMPONENT_REASON_THRESHOLDS.setup_participation_min:
        reason_codes.append("PARTICIPATION_SUPPORT")
    if context_score >= score_config.COMPONENT_REASON_THRESHOLDS.setup_context_min:
        reason_codes.append("ACCEPTANCE_SUPPORT")
    if risk.get("LowLiquidity"):
        risk_tags.append("LOW_LIQUIDITY")
    if risk.get("BelowEMA200"):
        risk_tags.append("BELOW_EMA200")
    pullback_reentry_below_ema200 = route.candidate_state == "BULL_PULLBACK_REENTRY" and bool(risk.get("BelowEMA200"))
    if pullback_reentry_below_ema200:
        reason_codes.append("PULLBACK_REENTRY_BELOW_EMA200")

    if not route.is_valid:
        candidate_state = "STATUS_QUO"
        candidate_class = CandidateClass.STATUS_QUO
        priority = ReviewPriority.NONE
        confidence = "LOW"
    elif pullback_reentry_below_ema200:
        candidate_state = route.candidate_state
        candidate_class = CandidateClass.REJECTED
        priority = ReviewPriority.C
        confidence = "LOW"
    elif total >= scoring.thresholds.selected_min and not risk_tags:
        candidate_state = route.candidate_state
        candidate_class = CandidateClass.SELECTED
        priority = ReviewPriority.A
        confidence = "HIGH"
    elif total >= scoring.thresholds.watch_min:
        candidate_state = route.candidate_state
        candidate_class = CandidateClass.WATCH
        priority = ReviewPriority.B if not risk_tags else ReviewPriority.NEEDS_MANUAL_REVIEW
        confidence = "MEDIUM"
    else:
        candidate_state = route.candidate_state
        candidate_class = CandidateClass.REJECTED
        priority = ReviewPriority.C
        confidence = "LOW"

    diagnostics.update(
        {
            "CandidateStateRaw": candidate_state,
            "WeightedScore": total if candidate_class != CandidateClass.STATUS_QUO else None,
            "MACDScore": route_score + timing_score,
            "RSIScore": _rsi_score(rsi),
            "ADXScore": _adx_score(_number(trend.get("ADX_1D"))),
            "ScoreWeights": scoring.weights.as_label(),
            "ConfirmationScore": round(timing_score + structure_score + participation_score, 2),
            "QualityContextScore": round(context_score + risk_score, 2),
            "MomentumSetupOpportunityType": route.opportunity_type,
            "MomentumSetupDirection": route.direction,
            "MomentumSetupConfidence": confidence,
            "MomentumSetupQualityScore": total,
            "MomentumSetupQualityComponents": (
                f"route={route_score};timing={timing_score};structure={structure_score};"
                f"participation={participation_score};context={context_score};risk={risk_score}"
            ),
            "MomentumSetupContextRule": "PULLBACK_REENTRY_BELOW_EMA200" if pullback_reentry_below_ema200 else "NONE",
            "MomentumSetupContextAction": "REJECT" if pullback_reentry_below_ema200 else "NONE",
            "MomentumSetupTimingProfile": route.timing_profile,
            "MomentumSetupReason": "; ".join(reason_codes),
            "MomentumSetupReasonCodes": ",".join(reason_codes),
            "SetupPassed": candidate_class in {CandidateClass.SELECTED, CandidateClass.WATCH},
            "SetupScore": total,
        }
    )
    return StageEvaluation(
        symbol=evidence.record.yahoo_symbol,
        candidate_state=candidate_state,
        candidate_class=candidate_class,
        review_priority=priority,
        confidence=confidence,
        score=ScoreResult(
            total_score=total,
            route_score=route_score,
            timing_score=timing_score,
            structure_score=structure_score,
            participation_score=participation_score,
            context_score=context_score,
            risk_score=risk_score,
            labels=tuple(reason_codes),
        ),
        reason_codes=tuple(reason_codes),
        risk_tags=tuple(risk_tags),
        diagnostics=diagnostics,
    )


def evaluate_divergence(evidence: EvidencePack) -> StageEvaluation:
    scoring = score_config.DIVERGENCE_SCORING
    diagnostics = evidence_to_diagnostics(evidence)
    structure = evidence.structure
    trend = evidence.trend
    momentum = evidence.momentum
    volume = evidence.volume
    risk = evidence.risk_context

    route = _classify_divergence_route(str(structure.get("DivergenceRouteCandidate") or "NONE"))
    bars_ago = _number(structure.get("DivergenceBarsAgo"))
    confirmation_state = str(structure.get("DivergenceConfirmationState") or "NONE")
    latest_price = _number(evidence.stock_baseline.get("LatestPrice"))
    ema20 = _number(trend.get("EMA20"))
    ema200 = _number(trend.get("EMA200"))
    rsi = _number(momentum.get("RSI_1D"))
    close_location = _number(evidence.stock_baseline.get("DailyCloseLocationPct"))
    volume_vs_20 = _number(volume.get("IntradayVolumeVs20Avg"))
    plus_di = _number(trend.get("PlusDI_1D"))
    minus_di = _number(trend.get("MinusDI_1D"))

    route_score = route.route_score
    timing_score = _divergence_timing_score(bars_ago, confirmation_state)
    structure_score = _divergence_structure_score(
        route.direction,
        route.divergence_type,
        latest_price,
        ema20,
        ema200,
        bool(structure.get("HigherLow_5D")),
        bool(structure.get("LowerHigh_5D")),
        bool(structure.get("EMA20_Reclaim")),
        bool(structure.get("EMA20_Below")),
    )
    participation_score = _divergence_participation_score(route.direction, volume_vs_20, plus_di, minus_di)
    context_score = _divergence_context_score(route.direction, rsi, close_location)
    risk_score = _risk_score(route.direction, bool(risk.get("LowLiquidity")), bool(risk.get("BelowEMA200")))
    total = round(route_score + timing_score + structure_score + participation_score + context_score + risk_score, 2)

    reason_codes: list[str] = [route.reason_code]
    risk_tags: list[str] = []
    if confirmation_state == "CONFIRMED":
        reason_codes.append("DIVERGENCE_CONFIRMED")
    if bars_ago is not None and bars_ago <= score_config.COMPONENT_REASON_THRESHOLDS.recent_divergence_bars_max:
        reason_codes.append("RECENT_DIVERGENCE")
    if structure_score >= score_config.COMPONENT_REASON_THRESHOLDS.divergence_structure_min:
        reason_codes.append("DIVERGENCE_STRUCTURE_SUPPORT")
    if participation_score >= score_config.COMPONENT_REASON_THRESHOLDS.divergence_participation_min:
        reason_codes.append("DIVERGENCE_PARTICIPATION_CONTEXT")
    if context_score >= score_config.COMPONENT_REASON_THRESHOLDS.divergence_context_min:
        reason_codes.append("DIVERGENCE_ACCEPTANCE_CONTEXT")
    if risk.get("LowLiquidity"):
        risk_tags.append("LOW_LIQUIDITY")
    if route.direction == "BULLISH" and risk.get("BelowEMA200"):
        risk_tags.append("BELOW_EMA200")
    raw_bullish_below_ema200 = (
        route.direction == "BULLISH"
        and risk.get("BelowEMA200")
        and confirmation_state != "CONFIRMED"
    )
    if raw_bullish_below_ema200:
        reason_codes.append("RAW_BULLISH_DIVERGENCE_BELOW_EMA200")

    if not route.is_valid:
        candidate_state = "STATUS_QUO"
        candidate_class = CandidateClass.STATUS_QUO
        priority = ReviewPriority.NONE
        confidence = "LOW"
    elif total >= scoring.thresholds.selected_min and not risk_tags and confirmation_state == "CONFIRMED":
        candidate_state = route.candidate_state
        candidate_class = CandidateClass.SELECTED
        priority = ReviewPriority.A
        confidence = "HIGH"
    elif total >= scoring.thresholds.watch_min and not raw_bullish_below_ema200:
        candidate_state = route.candidate_state
        candidate_class = CandidateClass.WATCH
        priority = ReviewPriority.B if not risk_tags else ReviewPriority.NEEDS_MANUAL_REVIEW
        confidence = "MEDIUM"
    else:
        candidate_state = route.candidate_state
        candidate_class = CandidateClass.REJECTED
        priority = ReviewPriority.C
        confidence = "LOW"

    diagnostics.update(
        {
            "CandidateStateRaw": candidate_state,
            "WeightedScore": total if candidate_class != CandidateClass.STATUS_QUO else None,
            "MACDScore": route_score + timing_score,
            "RSIScore": _rsi_score(rsi),
            "ADXScore": _adx_score(_number(trend.get("ADX_1D"))),
            "ScoreWeights": scoring.weights.as_label(),
            "ConfirmationScore": round(timing_score + structure_score + participation_score, 2),
            "QualityContextScore": round(context_score + risk_score, 2),
            "DivergenceDirection": route.direction,
            "DivergenceType": route.divergence_type,
            "DivergenceOpportunityType": route.opportunity_type,
            "DivergenceQualityScore": total,
            "DivergenceQualityComponents": (
                f"route={route_score};timing={timing_score};structure={structure_score};"
                f"participation={participation_score};context={context_score};risk={risk_score}"
            ),
            "DivergenceTimingProfile": route.timing_profile,
            "DivergenceReason": "; ".join(reason_codes),
            "DivergenceReasonCodes": ",".join(reason_codes),
            "SetupPassed": candidate_class in {CandidateClass.SELECTED, CandidateClass.WATCH},
            "SetupScore": total,
        }
    )
    return StageEvaluation(
        symbol=evidence.record.yahoo_symbol,
        candidate_state=candidate_state,
        candidate_class=candidate_class,
        review_priority=priority,
        confidence=confidence,
        score=ScoreResult(
            total_score=total,
            route_score=route_score,
            timing_score=timing_score,
            structure_score=structure_score,
            participation_score=participation_score,
            context_score=context_score,
            risk_score=risk_score,
            labels=tuple(reason_codes),
        ),
        reason_codes=tuple(reason_codes),
        risk_tags=tuple(risk_tags),
        diagnostics=diagnostics,
    )


def _classify_divergence_route(candidate: str) -> DivergenceRoute:
    if candidate == "BULLISH_DIVERGENCE":
        return DivergenceRoute(
            candidate_state="BULLISH_DIVERGENCE",
            opportunity_type="BULLISH_REGULAR_DIVERGENCE",
            direction="BULLISH",
            divergence_type="REGULAR",
            route_score=score_config.ROUTE_SCORES.regular_divergence,
            reason_code="BULLISH_REGULAR_DIVERGENCE_ROUTE",
            timing_profile="reversal_watch",
        )
    if candidate == "BEARISH_DIVERGENCE":
        return DivergenceRoute(
            candidate_state="BEARISH_DIVERGENCE",
            opportunity_type="BEARISH_REGULAR_DIVERGENCE",
            direction="BEARISH",
            divergence_type="REGULAR",
            route_score=score_config.ROUTE_SCORES.regular_divergence,
            reason_code="BEARISH_REGULAR_DIVERGENCE_ROUTE",
            timing_profile="exit_watch",
        )
    if candidate == "HIDDEN_BULLISH_DIVERGENCE":
        return DivergenceRoute(
            candidate_state="HIDDEN_BULLISH_DIVERGENCE",
            opportunity_type="HIDDEN_BULLISH_CONTINUATION",
            direction="BULLISH",
            divergence_type="HIDDEN",
            route_score=score_config.ROUTE_SCORES.hidden_divergence,
            reason_code="HIDDEN_BULLISH_DIVERGENCE_ROUTE",
            timing_profile="continuation",
        )
    if candidate == "HIDDEN_BEARISH_DIVERGENCE":
        return DivergenceRoute(
            candidate_state="HIDDEN_BEARISH_DIVERGENCE",
            opportunity_type="HIDDEN_BEARISH_CONTINUATION",
            direction="BEARISH",
            divergence_type="HIDDEN",
            route_score=score_config.ROUTE_SCORES.hidden_divergence,
            reason_code="HIDDEN_BEARISH_DIVERGENCE_ROUTE",
            timing_profile="failed_recovery",
        )
    return DivergenceRoute(
        candidate_state="STATUS_QUO",
        opportunity_type="NO_DIVERGENCE_ROUTE",
        direction="NONE",
        divergence_type="NONE",
        route_score=score_config.ROUTE_SCORES.status_quo,
        reason_code="NO_DIVERGENCE_ROUTE",
        timing_profile="none",
    )


def _divergence_timing_score(bars_ago: float | None, confirmation_state: str) -> float:
    score = 0.0
    if confirmation_state == "CONFIRMED":
        score += score_config.COMPONENT_SCORES.divergence_confirmation_confirmed
    elif confirmation_state == "RAW":
        score += score_config.COMPONENT_SCORES.divergence_confirmation_raw
    if bars_ago is not None:
        if bars_ago <= score_config.COMPONENT_SCORES.divergence_recent_bars_max:
            score += score_config.COMPONENT_SCORES.divergence_recent_bars_score
        elif bars_ago <= score_config.COMPONENT_SCORES.divergence_stale_bars_max:
            score += score_config.COMPONENT_SCORES.divergence_stale_bars_score
    return min(score, score_config.COMPONENT_SCORES.timing_max)


def _divergence_structure_score(
    direction: str,
    divergence_type: str,
    price: float | None,
    ema20: float | None,
    ema200: float | None,
    higher_low: bool,
    lower_high: bool,
    ema20_reclaim: bool,
    ema20_below: bool,
) -> float:
    score = 0.0
    if direction == "BULLISH":
        if divergence_type == "HIDDEN" and higher_low:
            score += score_config.COMPONENT_SCORES.divergence_hidden_structure
        if ema20_reclaim:
            score += score_config.COMPONENT_SCORES.divergence_ema20_signal
        if price is not None and ema200 is not None and price >= ema200:
            score += score_config.COMPONENT_SCORES.divergence_price_vs_ema200
        if price is not None and ema20 is not None and price >= ema20:
            score += score_config.COMPONENT_SCORES.divergence_price_vs_ema20
    if direction == "BEARISH":
        if divergence_type == "HIDDEN" and lower_high:
            score += score_config.COMPONENT_SCORES.divergence_hidden_structure
        if ema20_below:
            score += score_config.COMPONENT_SCORES.divergence_ema20_signal
        if price is not None and ema20 is not None and price <= ema20:
            score += score_config.COMPONENT_SCORES.divergence_bear_price_vs_ema20
        if price is not None and ema200 is not None and price <= ema200:
            score += score_config.COMPONENT_SCORES.divergence_bear_price_vs_ema200
    return min(score, score_config.COMPONENT_SCORES.divergence_structure_max)


def _divergence_participation_score(direction: str, volume_vs_20: float | None, plus_di: float | None, minus_di: float | None) -> float:
    score = 0.0
    if volume_vs_20 is not None and volume_vs_20 >= score_config.COMPONENT_SCORES.common_relative_volume_min:
        score += score_config.COMPONENT_SCORES.divergence_relative_volume
    if direction == "BULLISH" and plus_di is not None and minus_di is not None and plus_di >= minus_di:
        score += score_config.COMPONENT_SCORES.divergence_directional_di
    if direction == "BEARISH" and plus_di is not None and minus_di is not None and minus_di >= plus_di:
        score += score_config.COMPONENT_SCORES.divergence_directional_di
    return min(score, score_config.COMPONENT_SCORES.divergence_participation_max)


def _divergence_context_score(direction: str, rsi: float | None, close_location: float | None) -> float:
    score = 0.0
    thresholds = score_config.COMPONENT_THRESHOLDS
    if direction == "BULLISH" and rsi is not None:
        if thresholds.divergence_bullish_rsi_primary_min <= rsi <= thresholds.divergence_bullish_rsi_primary_max:
            score += score_config.COMPONENT_SCORES.divergence_rsi_primary
        elif (
            thresholds.divergence_bullish_rsi_secondary_low_min
            <= rsi
            < thresholds.divergence_bullish_rsi_secondary_low_max
            or thresholds.divergence_bullish_rsi_secondary_high_min
            < rsi
            <= thresholds.divergence_bullish_rsi_secondary_high_max
        ):
            score += score_config.COMPONENT_SCORES.divergence_rsi_secondary
    if direction == "BEARISH" and rsi is not None:
        if thresholds.divergence_bearish_rsi_primary_min <= rsi <= thresholds.divergence_bearish_rsi_primary_max:
            score += score_config.COMPONENT_SCORES.divergence_rsi_primary
        elif (
            thresholds.divergence_bearish_rsi_secondary_low_min
            <= rsi
            < thresholds.divergence_bearish_rsi_secondary_low_max
            or thresholds.divergence_bearish_rsi_secondary_high_min
            < rsi
            <= thresholds.divergence_bearish_rsi_secondary_high_max
        ):
            score += score_config.COMPONENT_SCORES.divergence_rsi_secondary
    if direction == "BULLISH" and close_location is not None and close_location >= thresholds.divergence_bullish_close_location_min:
        score += score_config.COMPONENT_SCORES.divergence_close_location
    if direction == "BEARISH" and close_location is not None and close_location <= thresholds.divergence_bearish_close_location_max:
        score += score_config.COMPONENT_SCORES.divergence_close_location
    return min(score, score_config.COMPONENT_SCORES.divergence_context_max)


def _classify_momentum_route(
    *,
    crossover_state: str,
    histogram: float | None,
    histogram_improving: bool,
    latest_price: float | None,
    ema20: float | None,
    ema50: float | None,
    ema20_reclaim: bool,
    higher_low: bool,
    price_ladder: bool,
    plus_di: float | None,
    minus_di: float | None,
) -> CrossoverRoute:
    bull_phase = crossover_state == "ABOVE_SIGNAL" and _above(latest_price, ema20)
    if bull_phase and (ema20_reclaim or higher_low):
        return CrossoverRoute(
            candidate_state="BULL_PULLBACK_REENTRY",
            opportunity_type="BULLISH_PULLBACK_REENTRY",
            direction="BULLISH",
            route_score=score_config.ROUTE_SCORES.pullback_reentry,
            reason_code="BULL_PULLBACK_REENTRY_ROUTE",
            timing_profile="reentry",
        )
    if bull_phase and price_ladder and _above(ema20, ema50) and _di_supports_bulls(plus_di, minus_di):
        return CrossoverRoute(
            candidate_state="BULL_CONTINUATION_MOMENTUM",
            opportunity_type="BULLISH_CONTINUATION_MOMENTUM",
            direction="BULLISH",
            route_score=score_config.ROUTE_SCORES.continuation,
            reason_code="BULL_CONTINUATION_ROUTE",
            timing_profile="continuation",
        )
    if bull_phase and histogram_improving and histogram is not None and histogram > score_config.COMPONENT_THRESHOLDS.histogram_positive_min:
        return CrossoverRoute(
            candidate_state="BULL_CONTINUATION_MOMENTUM",
            opportunity_type="BULLISH_MOMENTUM_EXPANSION",
            direction="BULLISH",
            route_score=score_config.ROUTE_SCORES.momentum_expansion,
            reason_code="BULL_MOMENTUM_EXPANSION_ROUTE",
            timing_profile="expansion",
        )
    return CrossoverRoute(
        candidate_state="STATUS_QUO",
        opportunity_type="NO_MOMENTUM_SETUP_ROUTE",
        direction="NONE",
        route_score=score_config.ROUTE_SCORES.status_quo,
        reason_code="NO_MOMENTUM_SETUP_ROUTE",
        timing_profile="none",
    )


def _momentum_timing_score(histogram: float | None, improving: bool, ema20_reclaim: bool) -> float:
    score = 0.0
    if histogram is not None and histogram > score_config.COMPONENT_THRESHOLDS.histogram_positive_min:
        score += score_config.COMPONENT_SCORES.setup_histogram_positive
    if improving:
        score += score_config.COMPONENT_SCORES.setup_histogram_improving
    if ema20_reclaim:
        score += score_config.COMPONENT_SCORES.setup_ema20_reclaim
    return min(score, score_config.COMPONENT_SCORES.timing_max)


def _momentum_structure_score(
    price: float | None,
    ema20: float | None,
    ema50: float | None,
    ema200: float | None,
    higher_low: bool,
    price_ladder: bool,
) -> float:
    score = 0.0
    if price is not None and ema20 is not None and price >= ema20:
        score += score_config.COMPONENT_SCORES.setup_price_vs_ema20
    if ema20 is not None and ema50 is not None and ema20 >= ema50:
        score += score_config.COMPONENT_SCORES.setup_ema20_vs_ema50
    if price is not None and ema200 is not None and price >= ema200:
        score += score_config.COMPONENT_SCORES.setup_price_vs_ema200
    if higher_low:
        score += score_config.COMPONENT_SCORES.setup_higher_low
    if price_ladder:
        score += score_config.COMPONENT_SCORES.setup_price_ladder
    return score


def _timing_score(direction: str, crossover_state: str, improving: bool, deteriorating: bool) -> float:
    score = 0.0
    if direction == "BULLISH" and crossover_state == "BULL_CROSS":
        score += score_config.COMPONENT_SCORES.crossover_fresh_cross
    if direction == "BEARISH" and crossover_state == "BEAR_CROSS":
        score += score_config.COMPONENT_SCORES.crossover_fresh_cross
    if direction == "BULLISH" and improving:
        score += score_config.COMPONENT_SCORES.crossover_histogram_direction
    if direction == "BEARISH" and deteriorating:
        score += score_config.COMPONENT_SCORES.crossover_histogram_direction
    return min(score, score_config.COMPONENT_SCORES.timing_max)


def _structure_score(
    direction: str,
    price: float | None,
    ema20: float | None,
    ema200: float | None,
    higher_low: bool,
    lower_high: bool,
) -> float:
    score = 0.0
    if direction == "BULLISH" and price is not None and ema20 is not None and price >= ema20:
        score += score_config.COMPONENT_SCORES.common_price_vs_ema20
    if direction == "BEARISH" and price is not None and ema20 is not None and price <= ema20:
        score += score_config.COMPONENT_SCORES.common_price_vs_ema20
    if direction == "BULLISH" and price is not None and ema200 is not None and price >= ema200:
        score += score_config.COMPONENT_SCORES.common_price_vs_ema200
    if direction == "BEARISH" and price is not None and ema200 is not None and price <= ema200:
        score += score_config.COMPONENT_SCORES.common_price_vs_ema200
    if direction == "BULLISH" and higher_low:
        score += score_config.COMPONENT_SCORES.common_short_structure
    if direction == "BEARISH" and lower_high:
        score += score_config.COMPONENT_SCORES.common_short_structure
    return score


def _participation_score(direction: str, volume_vs_20: float | None, plus_di: float | None, minus_di: float | None) -> float:
    score = 0.0
    if volume_vs_20 is not None and volume_vs_20 >= score_config.COMPONENT_SCORES.common_relative_volume_min:
        score += score_config.COMPONENT_SCORES.common_relative_volume
    if direction == "BULLISH" and plus_di is not None and minus_di is not None and plus_di >= minus_di:
        score += score_config.COMPONENT_SCORES.common_directional_di
    if direction == "BEARISH" and plus_di is not None and minus_di is not None and minus_di >= plus_di:
        score += score_config.COMPONENT_SCORES.common_directional_di
    return score


def _context_score(direction: str, rsi: float | None, close_location: float | None) -> float:
    score = 0.0
    thresholds = score_config.COMPONENT_THRESHOLDS
    if direction == "BULLISH" and rsi is not None and thresholds.common_bullish_rsi_min <= rsi <= thresholds.common_bullish_rsi_max:
        score += score_config.COMPONENT_SCORES.common_rsi_context
    if direction == "BEARISH" and rsi is not None and thresholds.common_bearish_rsi_min <= rsi <= thresholds.common_bearish_rsi_max:
        score += score_config.COMPONENT_SCORES.common_rsi_context
    if direction == "BULLISH" and close_location is not None and close_location >= thresholds.common_bullish_close_location_min:
        score += score_config.COMPONENT_SCORES.common_close_location_context
    if direction == "BEARISH" and close_location is not None and close_location <= thresholds.common_bearish_close_location_max:
        score += score_config.COMPONENT_SCORES.common_close_location_context
    return score


def _risk_score(direction: str, low_liquidity: bool, below_ema200: bool) -> float:
    score = score_config.COMPONENT_SCORES.risk_base
    if low_liquidity:
        score -= score_config.COMPONENT_SCORES.low_liquidity_penalty
    if direction == "BULLISH" and below_ema200:
        score -= score_config.COMPONENT_SCORES.below_ema200_penalty
    return max(score, 0.0)


def _rsi_score(rsi: float | None) -> float:
    if rsi is None:
        return 0.0
    thresholds = score_config.COMPONENT_THRESHOLDS
    if thresholds.rsi_score_strong_min <= rsi <= thresholds.rsi_score_strong_max:
        return score_config.COMPONENT_SCORES.rsi_strong
    if (
        thresholds.rsi_score_medium_low_min <= rsi < thresholds.rsi_score_medium_low_max
        or thresholds.rsi_score_medium_high_min < rsi <= thresholds.rsi_score_medium_high_max
    ):
        return score_config.COMPONENT_SCORES.rsi_medium
    return score_config.COMPONENT_SCORES.rsi_low


def _adx_score(adx_value: float | None) -> float:
    if adx_value is None:
        return 0.0
    if adx_value >= score_config.COMPONENT_SCORES.adx_strong_min:
        return score_config.COMPONENT_SCORES.adx_strong
    if adx_value >= score_config.COMPONENT_SCORES.adx_medium_min:
        return score_config.COMPONENT_SCORES.adx_medium
    return score_config.COMPONENT_SCORES.adx_low


def _number(value: object) -> float | None:
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None


def _is_deteriorating(previous: float | None, current: float | None) -> bool:
    return bool(previous is not None and current is not None and current < previous)


def _di_supports_bulls(plus_di: float | None, minus_di: float | None) -> bool:
    return bool(plus_di is not None and minus_di is not None and plus_di >= minus_di)


def _di_supports_bears(plus_di: float | None, minus_di: float | None) -> bool:
    return bool(plus_di is not None and minus_di is not None and minus_di >= plus_di)


def _above(value: float | None, reference: float | None) -> bool:
    return bool(value is not None and reference is not None and value >= reference)


def rank_stage_evaluations(evaluations: list[StageEvaluation]) -> StageRankingDecision:
    if not evaluations:
        raise ValueError("At least one stage evaluation is required.")
    ranked = sorted(enumerate(evaluations), key=lambda item: _evaluation_rank(item[1], item[0]), reverse=True)
    winner = ranked[0][1]
    decision = StageRankingDecision(
        winner=winner,
        evaluated_families=tuple(str(evaluation.diagnostics.get("StageFamily") or "") for evaluation in evaluations),
        candidate_states=tuple(
            f"{evaluation.diagnostics.get('StageFamily') or ''}:{evaluation.candidate_state}" for evaluation in evaluations
        ),
        candidate_classes=tuple(
            f"{evaluation.diagnostics.get('StageFamily') or ''}:{evaluation.candidate_class.value}" for evaluation in evaluations
        ),
        review_priorities=tuple(
            f"{evaluation.diagnostics.get('StageFamily') or ''}:{evaluation.review_priority.value}" for evaluation in evaluations
        ),
        total_scores=tuple(evaluation.score.total_score for evaluation in evaluations),
    )
    diagnostics = dict(winner.diagnostics)
    diagnostics.update(decision.to_diagnostics())
    return replace(decision, winner=replace(winner, diagnostics=diagnostics))


def _evaluation_rank(evaluation: StageEvaluation, order_index: int) -> tuple[int, int, float, float, int]:
    class_rank = {
        CandidateClass.SELECTED: score_config.RANKING.selected_rank,
        CandidateClass.WATCH: score_config.RANKING.watch_rank,
        CandidateClass.REJECTED: score_config.RANKING.rejected_rank,
        CandidateClass.STATUS_QUO: score_config.RANKING.status_quo_rank,
    }
    return (
        class_rank[evaluation.candidate_class],
        _priority_rank(evaluation.review_priority),
        evaluation.score.total_score,
        evaluation.score.route_score,
        -order_index,
    )


def _priority_rank(priority: ReviewPriority) -> int:
    return {
        ReviewPriority.A: score_config.RANKING.priority_a_rank,
        ReviewPriority.B: score_config.RANKING.priority_b_rank,
        ReviewPriority.NEEDS_MANUAL_REVIEW: score_config.RANKING.priority_needs_manual_review_rank,
        ReviewPriority.EVENT_RISK: score_config.RANKING.priority_event_risk_rank,
        ReviewPriority.LOW_LIQUIDITY: score_config.RANKING.priority_low_liquidity_rank,
        ReviewPriority.C: score_config.RANKING.priority_c_rank,
        ReviewPriority.NONE: score_config.RANKING.priority_none_rank,
    }[priority]


def _with_stage_family(evaluation: StageEvaluation, stage_family: str) -> StageEvaluation:
    diagnostics = dict(evaluation.diagnostics)
    diagnostics["StageFamily"] = stage_family
    return replace(evaluation, diagnostics=diagnostics)


def _traversal_blocked_evaluation(evidence: EvidencePack, traversal_plan: StockTraversalPlan, stage_family: str) -> StageEvaluation:
    diagnostics = evidence_to_diagnostics(evidence)
    diagnostics.update(traversal_plan.to_diagnostics())
    diagnostics["StageFamily"] = stage_family
    diagnostics["BlockedStageFamily"] = stage_family
    diagnostics["CandidateStateRaw"] = "STATUS_QUO"
    return StageEvaluation(
        symbol=evidence.record.yahoo_symbol,
        candidate_state="STATUS_QUO",
        candidate_class=CandidateClass.STATUS_QUO,
        review_priority=ReviewPriority.NONE,
        confidence="LOW",
        score=ScoreResult(total_score=0.0, labels=(f"BASELINE_BLOCKED_{stage_family}",)),
        reason_codes=(f"BASELINE_BLOCKED_{stage_family}",),
        diagnostics=diagnostics,
    )
