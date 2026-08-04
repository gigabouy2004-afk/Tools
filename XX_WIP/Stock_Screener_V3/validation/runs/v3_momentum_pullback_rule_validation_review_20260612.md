# V3 Momentum Pullback Below EMA200 Rule Validation

Date: 2026-06-13

Rule under validation: `BULL_PULLBACK_REENTRY` below EMA200 remains auditable but is emitted as `REJECTED` with `PULLBACK_REENTRY_BELOW_EMA200`.

## Artifact Set

- Before-rule detail files: 15 (`v3_divergence_rule_backtest_*_20260611_*_details.csv`).
- After-rule detail files: 15 (`v3_momentum_pullback_rule_*_20260612_*_details.csv`).
- Generated reports:
  - `validation/runs/v3_momentum_pullback_rule_stage_family_calibration_20260612.md`
  - `validation/runs/v3_momentum_pullback_rule_integrated_calibration_20260612.md`
  - `validation/runs/v3_momentum_pullback_rule_symbol_failure_20260612.md`

## Data Availability Note

Utilities 2026-03-11 and 2026-04-11 reruns processed zero rows because the live Yahoo provider returned no daily data for the sector file during this run. Overall before/after interpretation therefore uses the comparable core set: Technology, Industrial, Energy, and Telecom.

## Before/After Selected-Watch Counts

| Scope | Processed Before | Candidates Before | Momentum Before | Pullback Before | Pullback Below EMA200 Before | Processed After | Candidates After | Momentum After | Pullback After | Rule Rejected Rows |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| All files | 3869 | 3056 | 1280 | 1246 | 167 | 3595 | 2679 | 1028 | 996 | 156 |
| Comparable core ex-Utilities | 3503 | 2737 | 1131 | 1099 | 157 | 3503 | 2602 | 974 | 942 | 154 |

## Sector Counts

| Sector | Candidates Before | Momentum Before | Pullback Below EMA200 Before | Candidates After | Momentum After | Rule Rejected Rows |
|---|---:|---:|---:|---:|---:|---:|
| Technology | 1128 | 339 | 79 | 1059 | 260 | 80 |
| Industrial | 1114 | 569 | 69 | 1052 | 500 | 68 |
| Energy | 343 | 149 | 4 | 340 | 145 | 4 |
| Telecom | 152 | 74 | 5 | 151 | 69 | 2 |
| Utilities | 319 | 149 | 10 | 77 | 54 | 2 |

## Industrial February-March Focus

- Before: 701 selected/watch candidates; 297 Momentum Setup; 30 pullback re-entry below EMA200.
- After: 674 selected/watch candidates; 267 Momentum Setup; 27 rule-rejected rows.
- Before Industrial Feb-Mar Momentum Setup D+20: 297 rows, 19.53% hit rate, -7.93% average, -10.48% median, -15.01% median worst low.
- After Industrial Feb-Mar Momentum Setup D+20: 267 rows, 19.48% hit rate, -8.37% average, -10.80% median, -14.97% median worst low.

## Rule Rejections By Sector And Date

| Sector | D Date | Rejected Rows |
|---|---|---:|
| Energy | 2026-02-11 | 2 |
| Energy | 2026-04-11 | 2 |
| Industrial | 2026-02-11 | 16 |
| Industrial | 2026-03-11 | 11 |
| Industrial | 2026-04-11 | 41 |
| Technology | 2026-02-11 | 7 |
| Technology | 2026-03-11 | 37 |
| Technology | 2026-04-11 | 36 |
| Telecom | 2026-03-11 | 1 |
| Telecom | 2026-04-11 | 1 |
| Utilities | 2026-02-11 | 2 |

## Readout

- On the comparable core set, the rule removed 135 selected/watch candidates overall and 157 selected/watch Momentum Setup rows; this difference reflects ranking shifts after some candidates moved to other winning families.
- It removed all 157 comparable-core `BULL_PULLBACK_REENTRY + BELOW_EMA200` selected/watch rows from the promoted candidate set.
- Industrial February-March selected/watch candidates fell by 66; Momentum Setup rows fell by 66, matching the weak slice targeted by the rule.
- Remaining Industrial February-March Momentum Setup rows are still weak, so below-EMA200 was only part of the problem; the next calibration pass should inspect high-score pullback re-entry failures without `BELOW_EMA200`.
- Keep the rule as a conservative risk-separation guardrail. Do not add another Momentum Setup threshold change until the remaining high-score Industrial failures are reviewed.
