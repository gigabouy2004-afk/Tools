from __future__ import annotations

import unittest

import pandas as pd

from stock_screener_v3.evaluators import (
    CrossoverEvaluator,
    StageFamilyEvaluator,
    evaluate_crossover,
    evaluate_divergence,
    evaluate_momentum_setup,
    rank_stage_evaluations,
)
from stock_screener_v3.models import CandidateClass, EvidencePack, PriceDataBundle, ReviewPriority, ScoreResult, StageEvaluation, UniverseRecord
from stock_screener_v3.scoring_config import CROSSOVER_SCORING, DIVERGENCE_SCORING, SETUP_SCORING


def make_price_frame(values: list[float]) -> pd.DataFrame:
    index = pd.date_range("2025-10-01", periods=len(values), freq="B")
    close = pd.Series(values, index=index)
    return pd.DataFrame(
        {
            "Open": close.shift(1).fillna(close.iloc[0]),
            "High": close + 1.0,
            "Low": close - 1.0,
            "Close": close,
            "Volume": [250_000 + index_ * 1_000 for index_ in range(len(values))],
        },
        index=index,
    )


class StaticEvidenceBuilder:
    def __init__(self, evidence: EvidencePack):
        self.evidence = evidence

    def build(self, record: UniverseRecord, prices: PriceDataBundle) -> EvidencePack:
        return self.evidence


class CrossoverEvaluatorTests(unittest.TestCase):
    def test_crossover_evaluator_selects_constructive_bull_transition(self) -> None:
        evaluation = evaluate_crossover(make_bull_transition_evidence())

        self.assertIn(evaluation.candidate_class, {CandidateClass.SELECTED, CandidateClass.WATCH})
        self.assertEqual(evaluation.candidate_state, "PRE_BULL_CROSSOVER")
        self.assertIn("MACD_1D_CrossoverState", evaluation.diagnostics)
        self.assertIn("CrossoverOpportunityType", evaluation.diagnostics)
        self.assertIn("CrossoverQualityComponents", evaluation.diagnostics)
        self.assertEqual(evaluation.diagnostics["ScoreWeights"], CROSSOVER_SCORING.weights.as_label())

    def test_crossover_evaluator_returns_status_quo_without_route(self) -> None:
        values = [100 - index * 0.4 for index in range(100)]
        record = UniverseRecord(symbol="BBB", yahoo_symbol="BBB", sector="Energy", exchange="NYSE")
        prices = PriceDataBundle(symbol="BBB", daily=make_price_frame(values))

        evaluation = CrossoverEvaluator().evaluate(record, prices)

        self.assertEqual(evaluation.candidate_class, CandidateClass.STATUS_QUO)
        self.assertEqual(evaluation.candidate_state, "STATUS_QUO")
        self.assertIn("NO_CROSSOVER_ROUTE", evaluation.reason_codes)

    def test_momentum_evaluator_classifies_bull_pullback_reentry(self) -> None:
        evaluation = evaluate_momentum_setup(
            make_evidence(
                structure={"EMA20_Reclaim": True, "HigherLow_5D": False, "PriceLadder_Passed": True},
            )
        )

        self.assertEqual(evaluation.candidate_state, "BULL_PULLBACK_REENTRY")
        self.assertEqual(evaluation.diagnostics["MomentumSetupOpportunityType"], "BULLISH_PULLBACK_REENTRY")
        self.assertIn("BULL_PULLBACK_REENTRY_ROUTE", evaluation.reason_codes)
        self.assertEqual(evaluation.diagnostics["ScoreWeights"], SETUP_SCORING.weights.as_label())

    def test_momentum_pullback_reentry_below_ema200_is_rejected(self) -> None:
        evidence = make_evidence(
            structure={"EMA20_Reclaim": True, "HigherLow_5D": False, "PriceLadder_Passed": True},
        )
        evidence.trend["EMA200"] = 110.0
        evidence.risk_context["BelowEMA200"] = True

        evaluation = evaluate_momentum_setup(evidence)

        self.assertEqual(evaluation.candidate_state, "BULL_PULLBACK_REENTRY")
        self.assertEqual(evaluation.candidate_class, CandidateClass.REJECTED)
        self.assertEqual(evaluation.review_priority, ReviewPriority.C)
        self.assertEqual(evaluation.diagnostics["MomentumSetupContextRule"], "PULLBACK_REENTRY_BELOW_EMA200")
        self.assertEqual(evaluation.diagnostics["MomentumSetupContextAction"], "REJECT")
        self.assertIn("BELOW_EMA200", evaluation.risk_tags)
        self.assertIn("PULLBACK_REENTRY_BELOW_EMA200", evaluation.reason_codes)

    def test_momentum_evaluator_classifies_bull_continuation(self) -> None:
        evaluation = evaluate_momentum_setup(
            make_evidence(
                structure={"EMA20_Reclaim": False, "HigherLow_5D": False, "PriceLadder_Passed": True},
            )
        )

        self.assertEqual(evaluation.candidate_state, "BULL_CONTINUATION_MOMENTUM")
        self.assertEqual(evaluation.diagnostics["MomentumSetupOpportunityType"], "BULLISH_CONTINUATION_MOMENTUM")
        self.assertIn("BULL_CONTINUATION_ROUTE", evaluation.reason_codes)

    def test_crossover_does_not_claim_bull_pullback_reentry(self) -> None:
        evaluation = evaluate_crossover(
            make_evidence(
                structure={"EMA20_Reclaim": True, "HigherLow_5D": False, "PriceLadder_Passed": True},
            )
        )

        self.assertNotEqual(evaluation.candidate_state, "BULL_PULLBACK_REENTRY")

    def test_crossover_does_not_classify_above_zero_bull_continuation_as_pre_bull(self) -> None:
        evidence = make_bull_transition_evidence()
        evidence.momentum["MACD_1D_Value"] = 79.8062
        evidence.momentum["MACD_1D_Signal"] = 67.3786
        evidence.momentum["MACD_1D_Histogram"] = 12.4276
        evidence.momentum["MACD_1D_PreviousHistogram"] = 9.8421

        evaluation = evaluate_crossover(evidence)

        self.assertEqual(evaluation.candidate_state, "STATUS_QUO")
        self.assertEqual(evaluation.diagnostics["CrossoverOpportunityType"], "BULLISH_ABOVE_ZERO_CONTINUATION")
        self.assertIn("BULL_CROSS_ABOVE_ZERO_LINE_CONTINUATION", evaluation.reason_codes)

    def test_crossover_classifies_below_zero_near_bull_transition_only_while_below_signal(self) -> None:
        evidence = make_bull_transition_evidence()
        evidence.momentum["MACD_1D_CrossoverState"] = "BELOW_SIGNAL"
        evidence.momentum["MACD_1D_Value"] = -0.12
        evidence.momentum["MACD_1D_Signal"] = -0.04
        evidence.momentum["MACD_1D_Histogram"] = -0.08
        evidence.momentum["MACD_1D_CrossoverDistance"] = -0.08

        evaluation = evaluate_crossover(evidence)

        self.assertEqual(evaluation.candidate_state, "PRE_BULL_CROSSOVER")
        self.assertEqual(evaluation.diagnostics["CrossoverOpportunityType"], "BULLISH_NEAR_TRANSITION")

    def test_crossover_does_not_classify_mixed_zero_line_pair_as_near_bull(self) -> None:
        evidence = make_bull_transition_evidence()
        evidence.stock_baseline["LatestPrice"] = 16.76
        evidence.stock_baseline["DailyCloseLocationPct"] = 76.7858
        evidence.momentum["MACD_1D_CrossoverState"] = "BELOW_SIGNAL"
        evidence.momentum["MACD_1D_Value"] = -0.0503
        evidence.momentum["MACD_1D_Signal"] = 0.0669
        evidence.momentum["MACD_1D_Histogram"] = -0.1172
        evidence.momentum["MACD_1D_PreviousHistogram"] = -0.1307
        evidence.momentum["MACD_1D_CrossoverDistance"] = -0.1172
        evidence.trend["EMA20"] = 17.0192
        evidence.trend["EMA200"] = 15.651
        evidence.structure["EMA20_Below"] = True
        evidence.structure["PriceLadder_Passed"] = False
        evidence.risk_context["LowLiquidity"] = True

        evaluation = evaluate_crossover(evidence)

        self.assertEqual(evaluation.candidate_state, "STATUS_QUO")
        self.assertEqual(evaluation.diagnostics["CrossoverOpportunityType"], "NO_CROSSOVER_ROUTE")

    def test_stage_family_evaluator_selects_best_enabled_family(self) -> None:
        values = [100 - index * 0.12 for index in range(45)] + [95 + index * 0.55 for index in range(55)]
        record = UniverseRecord(symbol="AAA", yahoo_symbol="AAA", sector="Technology", exchange="NASDAQ")
        prices = PriceDataBundle(symbol="AAA", daily=make_price_frame(values))

        evaluation = StageFamilyEvaluator(stage_families=("CROSSOVER", "MOMENTUM_SETUP")).evaluate(record, prices)

        self.assertIn(evaluation.candidate_class, {CandidateClass.SELECTED, CandidateClass.WATCH, CandidateClass.REJECTED})
        self.assertIn(evaluation.candidate_state, {"PRE_BULL_CROSSOVER", "PRE_BEAR_CROSSOVER", "BULL_PULLBACK_REENTRY", "BULL_CONTINUATION_MOMENTUM"})

    def test_crossover_evaluator_classifies_pre_bear_crossover_for_exit(self) -> None:
        evaluation = evaluate_crossover(make_bear_evidence(crossover_state="BEAR_CROSS"))

        self.assertEqual(evaluation.candidate_state, "PRE_BEAR_CROSSOVER")
        self.assertEqual(evaluation.diagnostics["CrossoverDirection"], "BEARISH")
        self.assertEqual(evaluation.diagnostics["CrossoverOpportunityType"], "BEARISH_TRANSITION_CROSSOVER")
        self.assertIn(evaluation.candidate_class, {CandidateClass.SELECTED, CandidateClass.WATCH})
        self.assertIn("DAILY_MACD_BEAR_CROSS", evaluation.reason_codes)

    def test_crossover_evaluator_classifies_near_bear_transition(self) -> None:
        evaluation = evaluate_crossover(make_bear_evidence(crossover_state="ABOVE_SIGNAL"))

        self.assertEqual(evaluation.candidate_state, "PRE_BEAR_CROSSOVER")
        self.assertEqual(evaluation.diagnostics["CrossoverOpportunityType"], "BEARISH_NEAR_TRANSITION")
        self.assertIn("DAILY_MACD_NEAR_BEAR_TRANSITION", evaluation.reason_codes)

    def test_divergence_evaluator_classifies_regular_bullish_divergence(self) -> None:
        evaluation = evaluate_divergence(make_divergence_evidence("BULLISH_DIVERGENCE"))

        self.assertEqual(evaluation.candidate_state, "BULLISH_DIVERGENCE")
        self.assertEqual(evaluation.diagnostics["DivergenceDirection"], "BULLISH")
        self.assertEqual(evaluation.diagnostics["DivergenceType"], "REGULAR")
        self.assertEqual(evaluation.diagnostics["DivergenceOpportunityType"], "BULLISH_REGULAR_DIVERGENCE")
        self.assertIn(evaluation.candidate_class, {CandidateClass.SELECTED, CandidateClass.WATCH})
        self.assertEqual(evaluation.diagnostics["ScoreWeights"], DIVERGENCE_SCORING.weights.as_label())

    def test_divergence_rejects_raw_bullish_divergence_below_ema200(self) -> None:
        evidence = make_divergence_evidence("BULLISH_DIVERGENCE")
        evidence.structure["DivergenceConfirmationState"] = "RAW"
        evidence.risk_context["BelowEMA200"] = True

        evaluation = evaluate_divergence(evidence)

        self.assertEqual(evaluation.candidate_state, "BULLISH_DIVERGENCE")
        self.assertEqual(evaluation.candidate_class, CandidateClass.REJECTED)
        self.assertEqual(evaluation.review_priority, ReviewPriority.C)
        self.assertIn("BELOW_EMA200", evaluation.risk_tags)
        self.assertIn("RAW_BULLISH_DIVERGENCE_BELOW_EMA200", evaluation.reason_codes)

    def test_divergence_keeps_confirmed_bullish_below_ema200_as_manual_watch(self) -> None:
        evidence = make_divergence_evidence("BULLISH_DIVERGENCE")
        evidence.risk_context["BelowEMA200"] = True

        evaluation = evaluate_divergence(evidence)

        self.assertEqual(evaluation.candidate_state, "BULLISH_DIVERGENCE")
        self.assertEqual(evaluation.candidate_class, CandidateClass.WATCH)
        self.assertEqual(evaluation.review_priority, ReviewPriority.NEEDS_MANUAL_REVIEW)
        self.assertIn("BELOW_EMA200", evaluation.risk_tags)
        self.assertNotIn("RAW_BULLISH_DIVERGENCE_BELOW_EMA200", evaluation.reason_codes)

    def test_divergence_evaluator_classifies_regular_bearish_divergence(self) -> None:
        evaluation = evaluate_divergence(make_divergence_evidence("BEARISH_DIVERGENCE"))

        self.assertEqual(evaluation.candidate_state, "BEARISH_DIVERGENCE")
        self.assertEqual(evaluation.diagnostics["DivergenceDirection"], "BEARISH")
        self.assertEqual(evaluation.diagnostics["DivergenceType"], "REGULAR")
        self.assertEqual(evaluation.diagnostics["DivergenceOpportunityType"], "BEARISH_REGULAR_DIVERGENCE")
        self.assertIn(evaluation.candidate_class, {CandidateClass.SELECTED, CandidateClass.WATCH})

    def test_divergence_evaluator_classifies_hidden_bullish_divergence(self) -> None:
        evaluation = evaluate_divergence(make_divergence_evidence("HIDDEN_BULLISH_DIVERGENCE"))

        self.assertEqual(evaluation.candidate_state, "HIDDEN_BULLISH_DIVERGENCE")
        self.assertEqual(evaluation.diagnostics["DivergenceDirection"], "BULLISH")
        self.assertEqual(evaluation.diagnostics["DivergenceType"], "HIDDEN")
        self.assertEqual(evaluation.diagnostics["DivergenceOpportunityType"], "HIDDEN_BULLISH_CONTINUATION")

    def test_divergence_evaluator_classifies_hidden_bearish_divergence(self) -> None:
        evaluation = evaluate_divergence(make_divergence_evidence("HIDDEN_BEARISH_DIVERGENCE"))

        self.assertEqual(evaluation.candidate_state, "HIDDEN_BEARISH_DIVERGENCE")
        self.assertEqual(evaluation.diagnostics["DivergenceDirection"], "BEARISH")
        self.assertEqual(evaluation.diagnostics["DivergenceType"], "HIDDEN")
        self.assertEqual(evaluation.diagnostics["DivergenceOpportunityType"], "HIDDEN_BEARISH_CONTINUATION")

    def test_divergence_evaluator_returns_status_quo_without_route(self) -> None:
        evaluation = evaluate_divergence(make_divergence_evidence("NONE"))

        self.assertEqual(evaluation.candidate_state, "STATUS_QUO")
        self.assertEqual(evaluation.candidate_class, CandidateClass.STATUS_QUO)
        self.assertEqual(evaluation.diagnostics["DivergenceOpportunityType"], "NO_DIVERGENCE_ROUTE")
        self.assertIn("NO_DIVERGENCE_ROUTE", evaluation.reason_codes)

    def test_stage_family_evaluator_can_dispatch_divergence_family(self) -> None:
        evidence = make_divergence_evidence("BULLISH_DIVERGENCE")
        evaluator = StageFamilyEvaluator(
            stage_families=("DIVERGENCE",),
            evidence_builder=StaticEvidenceBuilder(evidence),  # type: ignore[arg-type]
        )

        evaluation = evaluator.evaluate(evidence.record, PriceDataBundle(symbol="DDD", daily=make_price_frame([100] * 90)))

        self.assertEqual(evaluation.candidate_state, "BULLISH_DIVERGENCE")
        self.assertEqual(evaluation.diagnostics["SelectedStageFamilies"], "DIVERGENCE")
        self.assertEqual(evaluation.diagnostics["TraversalCandidateFamilies"], "DIVERGENCE")

    def test_stage_family_default_includes_divergence_with_ranking_diagnostics(self) -> None:
        evidence = make_divergence_evidence("BULLISH_DIVERGENCE")
        evidence.momentum["MACDHistogramImproving"] = False
        evidence.structure["EMA20_Reclaim"] = False
        evidence.structure["HigherLow_5D"] = False
        evidence.structure["PriceLadder_Passed"] = False
        evaluator = StageFamilyEvaluator(evidence_builder=StaticEvidenceBuilder(evidence))  # type: ignore[arg-type]

        evaluation = evaluator.evaluate(evidence.record, PriceDataBundle(symbol="DDD", daily=make_price_frame([100] * 90)))

        self.assertEqual(evaluation.candidate_state, "BULLISH_DIVERGENCE")
        self.assertEqual(evaluation.diagnostics["RankingContractVersion"], "v1")
        self.assertEqual(evaluation.diagnostics["RankingWinnerFamily"], "DIVERGENCE")
        self.assertEqual(evaluation.diagnostics["RankingEvaluatedFamilies"], "CROSSOVER,MOMENTUM_SETUP,DIVERGENCE")

    def test_ranking_contract_prefers_candidate_class_before_raw_score(self) -> None:
        rejected = make_manual_evaluation(
            family="CROSSOVER",
            state="PRE_BULL_CROSSOVER",
            candidate_class=CandidateClass.REJECTED,
            priority=ReviewPriority.C,
            total_score=95.0,
        )
        watch = make_manual_evaluation(
            family="DIVERGENCE",
            state="BULLISH_DIVERGENCE",
            candidate_class=CandidateClass.WATCH,
            priority=ReviewPriority.B,
            total_score=60.0,
        )

        decision = rank_stage_evaluations([rejected, watch])

        self.assertEqual(decision.winner.candidate_state, "BULLISH_DIVERGENCE")
        self.assertEqual(decision.winner.diagnostics["RankingWinnerFamily"], "DIVERGENCE")
        self.assertEqual(decision.winner.diagnostics["RankingCandidateClasses"], "CROSSOVER:REJECTED|DIVERGENCE:WATCH")

    def test_ranking_contract_uses_selected_family_order_as_final_tiebreaker(self) -> None:
        crossover = make_manual_evaluation(
            family="CROSSOVER",
            state="PRE_BULL_CROSSOVER",
            candidate_class=CandidateClass.WATCH,
            priority=ReviewPriority.B,
            total_score=70.0,
        )
        divergence = make_manual_evaluation(
            family="DIVERGENCE",
            state="BULLISH_DIVERGENCE",
            candidate_class=CandidateClass.WATCH,
            priority=ReviewPriority.B,
            total_score=70.0,
        )

        decision = rank_stage_evaluations([crossover, divergence])

        self.assertEqual(decision.winner.candidate_state, "PRE_BULL_CROSSOVER")
        self.assertEqual(decision.winner.diagnostics["RankingWinnerFamily"], "CROSSOVER")


def make_evidence(structure: dict[str, object]) -> EvidencePack:
    return EvidencePack(
        record=UniverseRecord(symbol="AAA", yahoo_symbol="AAA", sector="Technology", exchange="NASDAQ"),
        as_of=pd.Timestamp("2026-02-11"),
        stock_baseline={"LatestPrice": 105.0, "DailyCloseLocationPct": 72.0},
        momentum={
            "RSI_1D": 56.0,
            "MACD_1D_CrossoverState": "ABOVE_SIGNAL",
            "MACD_1D_Value": 0.3,
            "MACD_1D_Signal": 0.1,
            "MACD_1D_Histogram": 0.2,
            "MACD_1D_CrossoverDistance": 0.2,
            "MACDHistogramImproving": True,
        },
        trend={
            "EMA20": 100.0,
            "EMA50": 96.0,
            "EMA200": 90.0,
            "ADX_1D": 24.0,
            "PlusDI_1D": 28.0,
            "MinusDI_1D": 16.0,
        },
        volume={"IntradayVolumeVs20Avg": 130.0},
        structure=structure,
        risk_context={"LowLiquidity": False, "BelowEMA200": False},
    )


def make_bull_transition_evidence() -> EvidencePack:
    return EvidencePack(
        record=UniverseRecord(symbol="AAA", yahoo_symbol="AAA", sector="Technology", exchange="NASDAQ"),
        as_of=pd.Timestamp("2026-02-11"),
        stock_baseline={"LatestPrice": 102.0, "DailyCloseLocationPct": 76.0},
        momentum={
            "RSI_1D": 54.0,
            "MACD_1D_CrossoverState": "BULL_CROSS",
            "MACD_1D_Value": -0.04,
            "MACD_1D_Signal": -0.10,
            "MACD_1D_Histogram": 0.06,
            "MACD_1D_PreviousHistogram": -0.03,
            "MACD_1D_CrossoverDistance": 0.06,
            "MACDHistogramImproving": True,
        },
        trend={
            "EMA20": 100.0,
            "EMA50": 99.0,
            "EMA200": 96.0,
            "ADX_1D": 23.0,
            "PlusDI_1D": 25.0,
            "MinusDI_1D": 18.0,
        },
        volume={"IntradayVolumeVs20Avg": 125.0},
        structure={
            "EMA20_Below": False,
            "EMA20_Reclaim": True,
            "HigherLow_5D": True,
            "LowerHigh_5D": False,
            "PriceLadder_Passed": True,
        },
        risk_context={"LowLiquidity": False, "BelowEMA200": False},
    )


def make_bear_evidence(crossover_state: str) -> EvidencePack:
    return EvidencePack(
        record=UniverseRecord(symbol="BBB", yahoo_symbol="BBB", sector="Technology", exchange="NASDAQ"),
        as_of=pd.Timestamp("2026-02-11"),
        stock_baseline={"LatestPrice": 88.0, "DailyCloseLocationPct": 24.0},
        momentum={
            "RSI_1D": 42.0,
            "MACD_1D_CrossoverState": crossover_state,
            "MACD_1D_Value": 0.12 if crossover_state == "ABOVE_SIGNAL" else -0.08,
            "MACD_1D_Signal": 0.08 if crossover_state == "ABOVE_SIGNAL" else 0.0,
            "MACD_1D_Histogram": 0.04 if crossover_state == "ABOVE_SIGNAL" else -0.08,
            "MACD_1D_PreviousHistogram": 0.12,
            "MACD_1D_CrossoverDistance": 0.04 if crossover_state == "ABOVE_SIGNAL" else -0.08,
            "MACDHistogramImproving": False,
        },
        trend={
            "EMA20": 92.0,
            "EMA50": 95.0,
            "EMA200": 98.0,
            "ADX_1D": 24.0,
            "PlusDI_1D": 14.0,
            "MinusDI_1D": 31.0,
        },
        volume={"IntradayVolumeVs20Avg": 140.0},
        structure={
            "EMA20_Below": True,
            "EMA20_Reclaim": False,
            "HigherLow_5D": False,
            "LowerHigh_5D": True,
            "PriceLadder_Passed": False,
        },
        risk_context={"LowLiquidity": False, "BelowEMA200": True},
    )


def make_divergence_evidence(candidate: str) -> EvidencePack:
    bullish = candidate in {"BULLISH_DIVERGENCE", "HIDDEN_BULLISH_DIVERGENCE"}
    hidden = candidate in {"HIDDEN_BULLISH_DIVERGENCE", "HIDDEN_BEARISH_DIVERGENCE"}
    return EvidencePack(
        record=UniverseRecord(symbol="DDD", yahoo_symbol="DDD", sector="Technology", exchange="NASDAQ"),
        as_of=pd.Timestamp("2026-02-11"),
        market_context={"MarketRegime": "MIXED"},
        sector_context={"SectorRegime": "MIXED"},
        stock_baseline={
            "LatestPrice": 104.0 if bullish else 96.0,
            "DailyCloseLocationPct": 68.0 if bullish else 28.0,
        },
        momentum={
            "RSI_1D": 52.0 if bullish else 62.0,
            "MACD_1D_State": "BULLISH" if bullish else "BEARISH",
            "MACD_1D_CrossoverState": "ABOVE_SIGNAL" if bullish else "BELOW_SIGNAL",
            "MACD_1D_Histogram": 0.12 if bullish else -0.12,
            "MACD_1D_PreviousHistogram": 0.04 if bullish else -0.04,
            "MACD_1D_CrossoverDistance": 0.12 if bullish else -0.12,
            "MACDHistogramImproving": bullish,
        },
        trend={
            "EMA20": 100.0,
            "EMA50": 98.0 if bullish else 102.0,
            "EMA200": 92.0 if bullish else 106.0,
            "ADX_1D": 22.0,
            "PlusDI_1D": 28.0 if bullish else 16.0,
            "MinusDI_1D": 16.0 if bullish else 30.0,
        },
        volume={"IntradayVolumeVs20Avg": 125.0},
        structure={
            "EMA20_Below": not bullish,
            "EMA20_Reclaim": bullish,
            "HigherLow_5D": bullish and hidden,
            "LowerHigh_5D": (not bullish) and hidden,
            "PriceLadder_Passed": bullish,
            "DivergenceRouteCandidate": candidate,
            "DivergencePriceSwing": _divergence_price_swing(candidate),
            "DivergenceMomentumSwing": _divergence_momentum_swing(candidate),
            "DivergenceBarsAgo": 3,
            "DivergenceConfirmationState": "CONFIRMED" if candidate != "NONE" else "NONE",
            "DivergencePreviousPriceSwingValue": 100.0,
            "DivergenceLatestPriceSwingValue": 95.0 if bullish else 105.0,
            "DivergencePreviousMomentumSwingValue": -0.8 if bullish else 0.8,
            "DivergenceLatestMomentumSwingValue": -0.3 if bullish else 0.3,
        },
        risk_context={"LowLiquidity": False, "BelowEMA200": False},
    )


def make_manual_evaluation(
    *,
    family: str,
    state: str,
    candidate_class: CandidateClass,
    priority: ReviewPriority,
    total_score: float,
) -> StageEvaluation:
    return StageEvaluation(
        symbol="ZZZ",
        candidate_state=state,
        candidate_class=candidate_class,
        review_priority=priority,
        confidence="MEDIUM",
        score=ScoreResult(total_score=total_score, route_score=30.0),
        diagnostics={"StageFamily": family},
    )


def _divergence_price_swing(candidate: str) -> str:
    return {
        "BULLISH_DIVERGENCE": "LOWER_LOW",
        "BEARISH_DIVERGENCE": "HIGHER_HIGH",
        "HIDDEN_BULLISH_DIVERGENCE": "HIGHER_LOW",
        "HIDDEN_BEARISH_DIVERGENCE": "LOWER_HIGH",
    }.get(candidate, "NONE")


def _divergence_momentum_swing(candidate: str) -> str:
    return {
        "BULLISH_DIVERGENCE": "HIGHER_LOW",
        "BEARISH_DIVERGENCE": "LOWER_HIGH",
        "HIDDEN_BULLISH_DIVERGENCE": "LOWER_LOW",
        "HIDDEN_BEARISH_DIVERGENCE": "HIGHER_HIGH",
    }.get(candidate, "NONE")


if __name__ == "__main__":
    unittest.main()
