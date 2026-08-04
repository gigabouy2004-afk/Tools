# V3 Ranking Contract

Date: 2026-06-04

Purpose: define how V3 chooses one reported `StageEvaluation` after traversal sends a stock through one or more stage-family evaluators.

## Scope

Ranking is a reporting and prioritization layer. It must not mutate family-specific signal logic, suppress evidence, or convert a weak route into a stronger route.

Each selected family still produces its own `StageEvaluation`. Ranking chooses the best current row to report for the stock and emits diagnostics explaining the choice.

## Contract V1

Ranking order:

1. `CandidateClass`
2. `ReviewPriority`
3. `ScoreResult.total_score`
4. `ScoreResult.route_score`
5. selected stage-family order

Candidate-class order:

```text
SELECTED > WATCH > REJECTED > STATUS_QUO
```

Priority order:

```text
A > B > NEEDS_MANUAL_REVIEW > EVENT_RISK / LOW_LIQUIDITY > C > NONE
```

Selected family order is only a final deterministic tie-breaker. It must not override candidate class, priority, total score, or route score.

## Diagnostics

The winning row must include:

- `StageFamily`
- `RankingContractVersion`
- `RankingRule`
- `RankingWinnerFamily`
- `RankingEvaluatedFamilies`
- `RankingCandidateStates`
- `RankingCandidateClasses`
- `RankingReviewPriorities`
- `RankingTotalScores`

These fields make the final reported row auditable without requiring all intermediate family evaluations to be exported as separate rows.

## Default Holistic Traversal

After this contract, the default selected stage-family set is:

```text
CROSSOVER,MOMENTUM_SETUP,DIVERGENCE
```

User-selected stage-family restrictions remain authoritative. For example, `--stage-family DIVERGENCE` still runs only Divergence.

## Guardrails

- Ranking cannot hide a higher-class candidate behind a higher raw score from a lower candidate class.
- Positive elimination still applies before ranking. A blocked bullish route is returned as `STATUS_QUO` with block diagnostics before it enters ranking.
- Divergence uses `DivergenceDirection` for the same bullish-route baseline block used by Crossover and Momentum Setup.
- Divergence calibration remains separate from ranking. The V1 ranking layer makes Divergence dispatch auditable; it does not claim that Divergence thresholds are historically calibrated.

## Validation Baseline

2026-06-11 integrated validation artifact:

```text
validation/runs/v3_integrated_holistic_calibration_20260611.md
```

Baseline input:

- 15 path-enabled D+20 sector detail files.
- 3,144 selected/watch candidate rows across Crossover, Divergence, and Momentum Setup.

Current findings:

- `CROSSOVER`: 903 candidates, 55.37% D+20 endpoint hit rate, 2.00% median endpoint.
- `DIVERGENCE`: 962 candidates, 53.33% D+20 endpoint hit rate, 0.97% median endpoint.
- `MOMENTUM_SETUP`: 1,279 candidates, 49.34% D+20 endpoint hit rate, -0.39% median endpoint.
- Weak ranking buckets to review before threshold changes:
  - `MOMENTUM_SETUP`: 198 candidates, 32.32% hit rate, -4.64% median endpoint.
  - `DIVERGENCE+MOMENTUM_SETUP`: 126 candidates, 39.68% hit rate, -2.64% median endpoint.
- `NEEDS_MANUAL_REVIEW` and `BELOW_EMA200` remain the first review-priority/risk-tag slices to calibrate.
