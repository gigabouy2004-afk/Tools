# V3 Weak-Date Watch/Priority Review

Run source: `v3_tech_full_pack_20260605`

Dates reviewed:

- `2026-02-11`
- `2026-03-11`

Purpose: evaluate whether `WATCH` and `NEEDS_MANUAL_REVIEW` are separating weaker setups in poor Technology follow-through periods.

## Main Conclusion

The separation is not uniformly calibrated yet.

February `WATCH` rows performed better than `SELECTED` rows at D+20, while March `WATCH` rows performed much worse. This means `WATCH` is currently a context bucket, not a reliable weakness bucket.

The clearest weak-date discriminator is not `WATCH` alone. It is `WATCH` plus `BELOW_EMA200`, especially bullish Divergence and Momentum Setup states.

## Candidate Class Outcomes D+20

| D date | Class | Candidates | Hit Rate | Average Return |
|---|---|---:|---:|---:|
| 2026-02-11 | SELECTED | 257 | 33.46% | -3.00% |
| 2026-02-11 | WATCH | 97 | 40.21% | 1.36% |
| 2026-03-11 | SELECTED | 157 | 49.04% | 0.56% |
| 2026-03-11 | WATCH | 197 | 23.86% | -3.34% |

## Review Priority Outcomes D+20

| D date | Priority | Candidates | Hit Rate | Average Return |
|---|---|---:|---:|---:|
| 2026-02-11 | A | 257 | 33.46% | -3.00% |
| 2026-02-11 | B | 35 | 40.00% | 4.17% |
| 2026-02-11 | NEEDS_MANUAL_REVIEW | 62 | 40.32% | -0.22% |
| 2026-03-11 | A | 157 | 49.04% | 0.56% |
| 2026-03-11 | B | 63 | 30.16% | -4.04% |
| 2026-03-11 | NEEDS_MANUAL_REVIEW | 134 | 20.90% | -3.00% |

## Risk Tag Separation D+20

| D date | Group | Candidates | Hit Rate | Average Return |
|---|---|---:|---:|---:|
| 2026-02-11 | WATCH + BELOW_EMA200 | 43 | 39.53% | -1.06% |
| 2026-02-11 | WATCH + NO_RISK_TAG | 35 | 40.00% | 4.17% |
| 2026-02-11 | WATCH + LOW_LIQUIDITY | 23 | 39.13% | 0.26% |
| 2026-03-11 | WATCH + BELOW_EMA200 | 102 | 10.78% | -8.89% |
| 2026-03-11 | WATCH + NO_RISK_TAG | 63 | 30.16% | -4.04% |
| 2026-03-11 | WATCH + LOW_LIQUIDITY | 39 | 51.28% | 15.03% |

## Weakest March WATCH Segments

| Segment | Candidates | Hit Rate | Average Return |
|---|---:|---:|---:|
| DIVERGENCE + BULLISH_DIVERGENCE + BELOW_EMA200 | 52 | 11.54% | -6.64% |
| MOMENTUM_SETUP + BULL_PULLBACK_REENTRY + BELOW_EMA200 | 37 | 10.81% | -12.60% |
| DIVERGENCE + HIDDEN_BULLISH_DIVERGENCE + BELOW_EMA200 | 8 | 0.00% | -7.08% |
| CROSSOVER + PRE_BULL_CROSSOVER + BELOW_EMA200 | 3 | 0.00% | -8.48% |

## Calibration Direction

Do not suppress these signals yet. They are valid technical observations, but the review priority should better flag weak bullish attempts below the 200 EMA.

Candidate next rule to test, not yet implement:

- keep `WATCH` classification for bullish Divergence or Momentum Setup below EMA200;
- downgrade review priority to a clearer manual-risk bucket when the route is bullish and `BELOW_EMA200` is present;
- preserve bearish `CROSSOVER` review for exit/capital-preservation.

Before changing evaluator thresholds or priority rules, run at least one non-Technology validation pack and confirm whether `WATCH + BELOW_EMA200` behaves similarly outside Technology.

## Reporting Follow-Up

Summary markdown now includes `Risk Tag Outcomes`, so this separation can be monitored automatically in future runs.

