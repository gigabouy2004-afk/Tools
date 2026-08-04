from __future__ import annotations

import unittest

import pandas as pd

from stock_screener_v3.baseline_router import Regime, build_baseline_decision, build_stock_traversal_plan, classify_benchmark_regime
from stock_screener_v3.evaluators import StageFamilyEvaluator
from stock_screener_v3.models import CandidateClass, EvidencePack, PriceDataBundle, UniverseRecord


class StaticEvidenceBuilder:
    def __init__(self, evidence: EvidencePack):
        self.evidence = evidence

    def build(self, record: UniverseRecord, prices: PriceDataBundle) -> EvidencePack:
        return self.evidence


class BaselineRouterTests(unittest.TestCase):
    def test_classify_benchmark_regime_detects_bearish_index(self) -> None:
        frame = price_frame([120 - index for index in range(90)])

        self.assertEqual(classify_benchmark_regime(frame), Regime.BEARISH)

    def test_build_baseline_decision_blocks_bullish_entries_when_all_bearish(self) -> None:
        decision = build_baseline_decision(make_bearish_evidence(crossover_state="ABOVE_SIGNAL"))

        self.assertFalse(decision.allow_bullish)
        self.assertTrue(decision.allow_bearish)
        self.assertIn("MOMENTUM_SETUP", decision.blocked_stage_families)

    def test_stock_traversal_plan_blocks_momentum_but_preserves_bear_crossover_review(self) -> None:
        plan = build_stock_traversal_plan(
            make_bearish_evidence(crossover_state="BEAR_CROSS"),
            ("CROSSOVER", "MOMENTUM_SETUP"),
        )

        self.assertEqual(plan.selected_stage_families, ("CROSSOVER", "MOMENTUM_SETUP"))
        self.assertEqual(plan.evaluable_stage_families, ("CROSSOVER",))
        self.assertEqual(plan.blocked_stage_families, ("MOMENTUM_SETUP",))
        self.assertFalse(plan.allow_bullish)
        self.assertTrue(plan.allow_bearish)

    def test_stock_traversal_plan_preserves_user_family_restrictions_and_aliases(self) -> None:
        plan = build_stock_traversal_plan(make_bullish_evidence(), ("MOMENTUM",))

        self.assertEqual(plan.selected_stage_families, ("MOMENTUM_SETUP",))
        self.assertEqual(plan.evaluable_stage_families, ("MOMENTUM_SETUP",))
        self.assertTrue(plan.allow_bullish)
        self.assertEqual(plan.blocked_stage_families, ())

    def test_stage_family_evaluator_blocks_momentum_setup_in_bearish_context(self) -> None:
        evidence = make_bearish_evidence(crossover_state="ABOVE_SIGNAL")
        evaluator = StageFamilyEvaluator(
            stage_families=("MOMENTUM_SETUP",),
            evidence_builder=StaticEvidenceBuilder(evidence),  # type: ignore[arg-type]
        )

        evaluation = evaluator.evaluate(evidence.record, PriceDataBundle(symbol="BBB", daily=price_frame([1] * 90)))

        self.assertEqual(evaluation.candidate_class, CandidateClass.STATUS_QUO)
        self.assertIn("BASELINE_BLOCKED_MOMENTUM_SETUP", evaluation.reason_codes)
        self.assertEqual(evaluation.diagnostics["BlockedStageFamilies"], "BULLISH_ENTRY,MOMENTUM_SETUP")

    def test_stage_family_evaluator_allows_bear_crossover_in_bearish_context(self) -> None:
        evidence = make_bearish_evidence(crossover_state="BEAR_CROSS")
        evaluator = StageFamilyEvaluator(
            stage_families=("CROSSOVER",),
            evidence_builder=StaticEvidenceBuilder(evidence),  # type: ignore[arg-type]
        )

        evaluation = evaluator.evaluate(evidence.record, PriceDataBundle(symbol="BBB", daily=price_frame([1] * 90)))

        self.assertEqual(evaluation.candidate_state, "PRE_BEAR_CROSSOVER")
        self.assertIn(evaluation.candidate_class, {CandidateClass.SELECTED, CandidateClass.WATCH})
        self.assertEqual(evaluation.diagnostics["AllowedBullishStages"], False)
        self.assertEqual(evaluation.diagnostics["AllowedBearishStages"], True)
        self.assertEqual(evaluation.diagnostics["SelectedStageFamilies"], "CROSSOVER")
        self.assertEqual(evaluation.diagnostics["TraversalCandidateFamilies"], "CROSSOVER")

    def test_stage_family_evaluator_blocks_bullish_divergence_in_all_bearish_context(self) -> None:
        evidence = make_bearish_evidence(crossover_state="BELOW_SIGNAL")
        evidence.structure.update(
            {
                "DivergenceRouteCandidate": "BULLISH_DIVERGENCE",
                "DivergencePriceSwing": "LOWER_LOW",
                "DivergenceMomentumSwing": "HIGHER_LOW",
                "DivergenceBarsAgo": 3,
                "DivergenceConfirmationState": "CONFIRMED",
            }
        )
        evaluator = StageFamilyEvaluator(
            stage_families=("DIVERGENCE",),
            evidence_builder=StaticEvidenceBuilder(evidence),  # type: ignore[arg-type]
        )

        evaluation = evaluator.evaluate(evidence.record, PriceDataBundle(symbol="BBB", daily=price_frame([1] * 90)))

        self.assertEqual(evaluation.candidate_class, CandidateClass.STATUS_QUO)
        self.assertEqual(evaluation.diagnostics["BaselineBlockedOriginalState"], "BULLISH_DIVERGENCE")
        self.assertIn("BASELINE_BLOCKED_BULLISH_ENTRY", evaluation.reason_codes)

    def test_stage_family_evaluator_emits_traversal_diagnostics_for_status_quo(self) -> None:
        evidence = make_status_quo_evidence()
        evaluator = StageFamilyEvaluator(
            stage_families=("CROSSOVER",),
            evidence_builder=StaticEvidenceBuilder(evidence),  # type: ignore[arg-type]
        )

        evaluation = evaluator.evaluate(evidence.record, PriceDataBundle(symbol="CCC", daily=price_frame([1] * 90)))

        self.assertEqual(evaluation.candidate_class, CandidateClass.STATUS_QUO)
        self.assertEqual(evaluation.diagnostics["SelectedStageFamilies"], "CROSSOVER")
        self.assertEqual(evaluation.diagnostics["TraversalCandidateFamilies"], "CROSSOVER")
        self.assertIn("BaselineRouteReason", evaluation.diagnostics)


def make_bearish_evidence(crossover_state: str) -> EvidencePack:
    return EvidencePack(
        record=UniverseRecord(symbol="BBB", yahoo_symbol="BBB", sector="Technology", exchange="NASDAQ"),
        as_of=pd.Timestamp("2026-02-11"),
        market_context={"MarketRegime": "BEARISH"},
        sector_context={"SectorRegime": "BEARISH"},
        stock_baseline={"LatestPrice": 80.0, "DailyCloseLocationPct": 22.0},
        momentum={
            "RSI_1D": 38.0,
            "MACD_1D_State": "BEARISH",
            "MACD_1D_CrossoverState": crossover_state,
            "MACD_1D_Histogram": -0.12,
            "MACD_1D_PreviousHistogram": -0.04,
            "MACD_1D_CrossoverDistance": -0.12,
            "MACDHistogramImproving": False,
        },
        trend={
            "EMA20": 86.0,
            "EMA50": 90.0,
            "EMA200": 95.0,
            "ADX_1D": 24.0,
            "PlusDI_1D": 12.0,
            "MinusDI_1D": 32.0,
        },
        volume={"IntradayVolumeVs20Avg": 130.0},
        structure={
            "EMA20_Below": True,
            "EMA20_Reclaim": False,
            "HigherLow_5D": False,
            "LowerHigh_5D": True,
            "PriceLadder_Passed": False,
        },
        risk_context={"LowLiquidity": False, "BelowEMA200": True},
    )


def make_bullish_evidence() -> EvidencePack:
    return EvidencePack(
        record=UniverseRecord(symbol="AAA", yahoo_symbol="AAA", sector="Technology", exchange="NASDAQ"),
        as_of=pd.Timestamp("2026-02-11"),
        market_context={"MarketRegime": "BULLISH"},
        sector_context={"SectorRegime": "BULLISH"},
        stock_baseline={"LatestPrice": 110.0, "DailyCloseLocationPct": 72.0},
        momentum={
            "RSI_1D": 58.0,
            "MACD_1D_State": "BULLISH",
            "MACD_1D_CrossoverState": "ABOVE_SIGNAL",
            "MACD_1D_Histogram": 0.18,
            "MACD_1D_PreviousHistogram": 0.12,
            "MACD_1D_CrossoverDistance": 0.18,
            "MACDHistogramImproving": True,
        },
        trend={
            "EMA20": 104.0,
            "EMA50": 100.0,
            "EMA200": 92.0,
            "ADX_1D": 24.0,
            "PlusDI_1D": 31.0,
            "MinusDI_1D": 14.0,
        },
        volume={"IntradayVolumeVs20Avg": 125.0},
        structure={
            "EMA20_Below": False,
            "EMA20_Reclaim": False,
            "HigherLow_5D": True,
            "LowerHigh_5D": False,
            "PriceLadder_Passed": True,
        },
        risk_context={"LowLiquidity": False, "BelowEMA200": False},
    )


def make_status_quo_evidence() -> EvidencePack:
    return EvidencePack(
        record=UniverseRecord(symbol="CCC", yahoo_symbol="CCC", sector="Energy", exchange="NYSE"),
        as_of=pd.Timestamp("2026-02-11"),
        market_context={"MarketRegime": "MIXED"},
        sector_context={"SectorRegime": "MIXED"},
        stock_baseline={"LatestPrice": 100.0, "DailyCloseLocationPct": 50.0},
        momentum={
            "RSI_1D": 50.0,
            "MACD_1D_State": "BULLISH",
            "MACD_1D_CrossoverState": "ABOVE_SIGNAL",
            "MACD_1D_Histogram": 0.5,
            "MACD_1D_PreviousHistogram": 0.52,
            "MACD_1D_CrossoverDistance": 0.5,
            "MACDHistogramImproving": False,
        },
        trend={
            "EMA20": 99.0,
            "EMA50": 98.0,
            "EMA200": 97.0,
            "ADX_1D": 18.0,
            "PlusDI_1D": 22.0,
            "MinusDI_1D": 18.0,
        },
        volume={"IntradayVolumeVs20Avg": 90.0},
        structure={
            "EMA20_Below": False,
            "EMA20_Reclaim": False,
            "HigherLow_5D": False,
            "LowerHigh_5D": False,
            "PriceLadder_Passed": False,
        },
        risk_context={"LowLiquidity": False, "BelowEMA200": False},
    )


def price_frame(values: list[float]) -> pd.DataFrame:
    index = pd.date_range("2025-10-01", periods=len(values), freq="B")
    close = pd.Series(values, index=index)
    return pd.DataFrame(
        {
            "Open": close,
            "High": close + 1.0,
            "Low": close - 1.0,
            "Close": close,
            "Volume": 200_000,
        },
        index=index,
    )


if __name__ == "__main__":
    unittest.main()
