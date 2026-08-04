# V8 Foundation, Directional, Regression, and ETF Validation Conclusion

Date: 2026-07-12

Status: Mainline implementation and focused validation passed. EMA200 plus configurable MACD `8/21/5` is now the enforced V8 first filter. The evidence supports continued V8 development and joint analysis, not operational replacement of V7.

Plain-language supplement: `docs/V8_EXPERIMENT_ANALYSIS_BRIEF_2026-07-13.md` defines every engine term, decomposes the combined MACD Reset state, explains the full post-Foundation scoring path, records a freshness-score sign defect, and provides the user-approval checklist. Use that document for offline analysis or restart.

## Decision Implemented

V8 restores the V1-V3 staged architecture:

```text
Foundation -> Setup/Momentum -> Confirmation -> ETF context
```

The production-default Foundation rule is:

```text
Close > EMA200
AND MACD_Line(8,21,5) > MACD_Signal_Line(8,21,5)
AND MACD_Line(8,21,5) > 0
```

The MACD periods remain configurable. `--foundation-policy enforce` is the default. `audit` is retained only to calculate the prior downstream decision for regression comparison.

State behavior:

| Foundation status | Downstream behavior | Published decision | Score |
|---|---|---|---:|
| `FOUNDATION_VALID` | Run full V8 Setup/Momentum and confirmation | Full V8 result | Full V8 score |
| `FOUNDATION_TREND_VALID_MACD_RESET` | Stop before Setup/Momentum | `MOMENTUM_PRESENT_WAIT_CONFIRMATION` | 0 |
| `FOUNDATION_INVALID_BELOW_EMA200` | Stop before Setup/Momentum | `REJECT` | 0 |
| `FOUNDATION_INSUFFICIENT_DATA` | Stop before Setup/Momentum | `REJECT` | 0 |

ETF lookup remains post-decision and informational. It runs only for `MOMENTUM_ACTIVE` at Score 85 or above and cannot mutate Score.

## Canonical Frozen Run

```text
Run ID: V8FOUND_20260712T182945Z_cf0c908
Folder: backtests/V8_Foundation_Validation/runs/V8FOUND_20260712T182945Z_cf0c908
```

Scope:

- 20 technology stocks.
- Four predeclared Q2 dates: April 8, April 30, May 7, and June 9, 2026.
- 80 complete stock/date rows.
- Daily EOD historical replay with no historical hourly or extended-hours reconstruction.
- Entry at D+1 open; exits at D+1, D+5, and D+8 close.
- SPY benchmark outcomes.
- Enforced-versus-audit regression comparison.
- ETF source lookup for all 20 stocks, with historical acceptance only where the independent holdings date is in 2026Q2.

Seed set:

```text
NVDA AAPL MSFT GOOGL META AMD AVGO ORCL CRM NOW
PANW CRWD ANET MU QCOM AMAT LRCX KLAC PLTR APP
```

## Foundation Distribution

| Status | Rows | Share |
|---|---:|---:|
| Foundation Valid | 25 | 31.25% |
| Above EMA200, MACD Reset | 28 | 35.00% |
| Below EMA200 | 27 | 33.75% |
| Insufficient data | 0 | 0.00% |

All 25 Foundation Valid rows ran full Setup/Momentum analysis. All 55 non-qualified rows stopped with Score 0.

## Directional Results by Foundation State

| Foundation state | Rows | D+1 positive | D+1 mean | D+5 positive | D+5 mean | D+8 positive | D+8 mean |
|---|---:|---:|---:|---:|---:|---:|---:|
| Valid | 25 | 19/25 (76.0%) | +2.21% | 23/25 (92.0%) | +8.16% | 18/25 (72.0%) | +10.24% |
| MACD Reset | 28 | 15/28 (53.6%) | -0.05% | 24/28 (85.7%) | +4.95% | 21/28 (75.0%) | +6.30% |
| Below EMA200 | 27 | 15/27 (55.6%) | -0.99% | 16/27 (59.3%) | +2.48% | 13/27 (48.1%) | +2.27% |

The strongest discrimination is at D+1. Foundation Valid improved D+1 positive rate by more than 20 percentage points versus each non-valid state and produced a positive mean where both non-valid states had non-positive means.

Longer-horizon interpretation is more nuanced. MACD-reset rows frequently continued upward at D+5 and D+8, so the reset state should remain a visible WAIT state rather than being described as a failed long-term trend.

## Final V8 Decisions

| Final decision | Rows | D+1 positive | D+5 positive | D+8 positive | Mean D+1 | Mean D+5 | Mean D+8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| `MOMENTUM_ACTIVE` | 5 | 4/5 (80%) | 5/5 (100%) | 4/5 (80%) | +1.32% | +7.35% | +11.11% |
| `MOMENTUM_PRESENT_WAIT_CONFIRMATION` | 30 | 17/30 (56.7%) | 26/30 (86.7%) | 21/30 (70.0%) | +0.34% | +5.01% | +5.72% |
| `REJECT` | 45 | 28/45 (62.2%) | 32/45 (71.1%) | 27/45 (60.0%) | +0.23% | +4.95% | +5.93% |

Active rows:

| Ticker | Signal date | Score | D+1 | D+5 | D+8 | Accepted same-quarter ETF |
|---|---|---:|---:|---:|---:|---|
| GOOGL | 2026-04-30 | 100 | +1.06% | +4.29% | +1.50% | VOX 14.10% |
| GOOGL | 2026-05-07 | 100 | +0.96% | +1.03% | -2.35% | VOX 14.10% |
| AMD | 2026-04-30 | 100 | +2.46% | +16.08% | +27.40% | None dated in Q2 |
| AMAT | 2026-04-08 | 100 | +3.26% | +2.34% | +1.65% | None returned |
| AMAT | 2026-06-09 | 100 | -1.15% | +13.02% | +27.33% | None returned |

The D+1 target passed in this focused sample, but the denominator is five Active rows. This is encouraging implementation evidence, not a statistically broad signoff.

## Regression Result

The audit policy reproduced the pre-enforcement downstream calculation on all 80 rows.

- All 25 Foundation Valid rows had exactly matching audit/enforced Score and Final Decision.
- All 55 non-valid rows passed the zero-score/non-Active short-circuit contract.
- 24 Final Decisions changed because of the new state policy.
- Five legacy/audit Active rows became MACD-reset WAIT rows.
- Those five blocked Active rows were positive `2/5` at D+1, `3/5` at D+5, and `4/5` at D+8; mean returns were `-0.08%`, `+0.66%`, and `+4.53%`.

The gate therefore removed a weak D+1 cohort in this sample, while also delaying some longer-duration winners. That is the central tradeoff for the joint review.

## ETF Mapping Result

The production reverse-source path was queried for all 20 stocks.

- 21 conservative top-ten mappings were returned.
- Every returned mapping was independently checked on its ETF holdings page.
- Only 7 mappings had a validated holdings date in 2026Q2 and were accepted for historical association.
- Q3-dated mappings were excluded even when validation passed.
- Accepted mappings covered NVDA/VGT, AAPL/VGT, MSFT/VGT and VOOG, GOOGL/VOX, META/VOX, and PANW/HACK.
- Only GOOGL combined an Active row with an accepted Q2 mapping, producing two VOX outcome rows.
- Score-invariance failures: 0.

GOOGL versus VOX:

| Signal date | Stock D+1 / D+5 / D+8 | VOX D+1 / D+5 / D+8 |
|---|---|---|
| 2026-04-30 | +1.06% / +4.29% / +1.50% | -0.06% / +0.65% / -1.16% |
| 2026-05-07 | +0.96% / +1.03% / -2.35% | -0.10% / -0.14% / -1.61% |

ETF evidence is complete for the requested mapping contract. The two Active outcome comparisons are retained as historical audit rows only; ETF return prediction is not part of the approved engine function. No Q3 holding was back-cast into Q2.

## Independent Validation

The independent validator passed every check:

```text
Exactly 20 stocks
Exactly 4 dates
Exactly 80 unique stock/date rows
MACD 8/21/5
Foundation policy enforced
80 foundation and forward-outcome rows independently recomputed
Valid-row regression
Invalid-row short circuit
Strict ETF same-quarter acceptance
Score invariance
Manifest counts
Frozen-file checksums
```

Recompute failures: 0.

Focused automated tests: 22 passed, covering MACD calculation/configuration/no-look-ahead, Foundation states, stop behavior, legacy-log schema rotation, replay outcomes, and ETF postprocessor contracts.

## Limitations and Decision

Limitations:

- One technology-heavy quarter is not a multi-regime market test.
- Purposeful seed selection does not estimate whole-market precision.
- Historical daily replay cannot reconstruct hourly, live-quote, or extended-hours gates.
- Only five Active rows were observed.
- Same-quarter ETF holdings evidence was available for 7 mappings. Two Active ETF outcome rows were recorded, but they have no scoring or predictive mandate.
- The run does not address delisted-symbol survivorship, transaction costs, or a final untouched ticker holdout.

Decision:

```text
FOUNDATION IMPLEMENTATION = COMPLETE AND VALIDATED
FOCUSED D+1/D+5/D+8 RESULT = PASSED
ETF MAPPING CONTRACT = PASSED WITH STRICT SAME-QUARTER FILTER
V8 OPERATIONAL REPLACEMENT OF V7 = NOT YET APPROVED
```

The next action is the requested joint analysis of whether the five blocked legacy Actives justify a MACD-reset re-entry rule, followed by multi-regime/holdout testing if the present contract is retained.

## Delivered Evidence

```text
outputs/execution_console.log
outputs/execution_log.csv
outputs/regression_comparison.csv
outputs/ticker_summary.csv
outputs/date_summary.csv
outputs/etf_stock_summary.csv
outputs/etf_mapping_validation.csv
outputs/active_etf_outcomes.csv
outputs/aggregate_summary.json
validation/independently_recomputed_rows.csv
validation/validation_summary.json
validation/validator_console.txt
run_manifest.json
checksums.sha256
```
