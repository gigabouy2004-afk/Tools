# V3 Technology Full-Universe Calibration Review

Run reviewed: `v3_tech_full_pack_20260605`

Source artifacts:

- `validation/runs/v3_tech_full_pack_20260605_20260211_details.csv`
- `validation/runs/v3_tech_full_pack_20260605_20260311_details.csv`
- `validation/runs/v3_tech_full_pack_20260605_20260411_details.csv`
- `validation/runs/v3_tech_full_pack_20260605_aggregate_summary.md`

## Purpose

This review captures ranking and stage-family behavior from the first full Technology-universe validation pass. It is a calibration input, not a threshold-change approval.

## Main Read

The engine is producing useful route diagnostics, but current candidate density is high. February and March show that high candidate density alone is not enough; April shows that the same rules can perform strongly when the sector regime broadly follows through.

The immediate calibration target should be ranking and review-priority separation, not adding new indicators.

## Candidate Density

| D date | Processed rows | Candidates | Candidate density |
|---|---:|---:|---:|
| 2026-02-11 | 512 | 354 | 0.6914 |
| 2026-03-11 | 514 | 354 | 0.6887 |
| 2026-04-11 | 514 | 450 | 0.8755 |

The April density is especially high. That is acceptable for a broad scanner if review-priority ranking is strong, but it is too broad for a final trade list.

## Winner Family Mix

| D date | CROSSOVER | MOMENTUM_SETUP | DIVERGENCE |
|---|---:|---:|---:|
| 2026-02-11 | 153 | 82 | 119 |
| 2026-03-11 | 104 | 83 | 167 |
| 2026-04-11 | 162 | 174 | 114 |

Interpretation:

- `DIVERGENCE` is not a minor path; it won many rows, especially on 2026-03-11.
- `MOMENTUM_SETUP` became dominant in the April continuation environment.
- `CROSSOVER` remained relevant across all three dates, including bearish preservation/exit states.

## Active-Family Collision Buckets

Rows often had more than one non-`STATUS_QUO` family available before ranking:

| D date | Top collision buckets |
|---|---|
| 2026-02-11 | `CROSSOVER`: 174; `CROSSOVER+DIVERGENCE`: 118; `CROSSOVER+DIVERGENCE+MOMENTUM_SETUP`: 40 |
| 2026-03-11 | `CROSSOVER+DIVERGENCE`: 110; `CROSSOVER`: 106; `DIVERGENCE`: 70 |
| 2026-04-11 | `CROSSOVER`: 159; `CROSSOVER+MOMENTUM_SETUP`: 112; `CROSSOVER+DIVERGENCE`: 106; all three: 69 |

This confirms the ranking layer is not cosmetic. It is making real winner choices among competing family interpretations.

## Family D+20 Outcomes

| D date | Family | Candidates | Hit Rate | Average Return |
|---|---|---:|---:|---:|
| 2026-02-11 | CROSSOVER | 153 | 43.14% | 0.01% |
| 2026-02-11 | DIVERGENCE | 119 | 34.45% | -1.74% |
| 2026-02-11 | MOMENTUM_SETUP | 82 | 21.95% | -5.26% |
| 2026-03-11 | MOMENTUM_SETUP | 83 | 36.14% | 0.96% |
| 2026-03-11 | DIVERGENCE | 167 | 34.73% | -1.81% |
| 2026-03-11 | CROSSOVER | 104 | 34.62% | -3.33% |
| 2026-04-11 | MOMENTUM_SETUP | 174 | 85.06% | 29.31% |
| 2026-04-11 | CROSSOVER | 162 | 81.48% | 24.44% |
| 2026-04-11 | DIVERGENCE | 114 | 78.95% | 21.11% |

Early read:

- `MOMENTUM_SETUP` looks weak in February but very strong in April. It needs stricter regime/context distinction before calibration.
- `DIVERGENCE` should remain in the default holistic path, but its review-priority separation needs work because March had many Divergence winners with weak forward returns.
- `CROSSOVER` had the most stable D+20 behavior in the weak February environment, but March was still weak.

## Failure Categories

| D date | Leading failure categories |
|---|---|
| 2026-02-11 | `ACCEPTANCE_CONTEXT_FAILURE`: 41; `PARTICIPATION_FAILURE`: 41; `STRUCTURE_FAILURE`: 27 |
| 2026-03-11 | `PARTICIPATION_FAILURE`: 60; `STRUCTURE_FAILURE`: 59; `LIQUIDITY_RISK`: 10 |
| 2026-04-11 | `PARTICIPATION_FAILURE`: 2; `LIQUIDITY_RISK`: 1 |

Weak-date failures are concentrated around participation and structure. This points toward calibration of confirmation/review priority rather than suppressing route candidates.

## Diagnostics Confirmed

All processed rows in the three detail CSVs have:

- `RankingContractVersion`
- `RankingEvaluatedFamilies`
- `RankingCandidateStates`
- `RankingCandidateClasses`
- `RankingReviewPriorities`
- `RankingTotalScores`
- `TraversalCandidateFamilies`
- `TraversalBlockedFamilies`
- `TraversalRouteReason`
- Divergence diagnostic columns

## Recommended Next Calibration Work

1. Do not add new indicator rules yet.
2. Add a compact ranking-collision report to the CLI or report layer so these collision buckets are generated automatically.
3. Review `NEEDS_MANUAL_REVIEW` and `WATCH` rows from February/March to see whether review priority is separating weak setups strongly enough.
4. Run a non-Technology NYSE/NASDAQ pack before touching thresholds.
5. Calibrate `MOMENTUM_SETUP` only after separating bearish/weak-sector pullback traps from true continuation environments.
