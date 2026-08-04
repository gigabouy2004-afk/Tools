# V3 Industrial Momentum Remaining Failure Review

Date: 2026-06-13

Scope: Industrial 2026-02-11 and 2026-03-11, post `PULLBACK_REENTRY_BELOW_EMA200` rule.

Filter:

- `StageFamily = MOMENTUM_SETUP`
- `CandidateStateRaw = BULL_PULLBACK_REENTRY`
- `CandidateClass in SELECTED,WATCH`
- excludes `BELOW_EMA200`

## Summary

- Focus rows: 260
- D+20 hit rate: 19.23%
- D+20 average endpoint: -8.46%
- D+20 median endpoint: -10.87%
- D+20 median worst low: -15.03%
- D+20 median best high: 4.43%
- Failed rows: 210
- High-score rows (`TotalScore >= 85`): 165
- High-score failed rows: 127

## By D Date

| D Date | Rows | Hit Rate | Failed | Avg Endpoint | Median Endpoint | Median Worst Low | Median Best High |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-02-11 | 219 | 14.61% | 187 | -9.83% | -11.39% | -14.97% | 3.98% |
| 2026-03-11 | 41 | 43.90% | 23 | -1.17% | -3.24% | -16.53% | 9.95% |

## By Review Priority

| Review Priority | Rows | Hit Rate | Failed | Avg Endpoint | Median Endpoint | Median Worst Low | Median Best High |
|---|---:|---:|---:|---:|---:|---:|---:|
| B | 2 | 0.00% | 2 | -26.05% | -26.05% | -34.20% | 3.50% |
| A | 233 | 18.88% | 189 | -8.32% | -10.85% | -14.97% | 4.42% |
| NEEDS_MANUAL_REVIEW | 25 | 24.00% | 19 | -8.42% | -12.30% | -15.24% | 4.43% |

## By Score Bucket

| Score Bucket | Rows | Hit Rate | Failed | Avg Endpoint | Median Endpoint | Median Worst Low | Median Best High |
|---|---:|---:|---:|---:|---:|---:|---:|
| 72-79.99 | 52 | 9.62% | 47 | -11.23% | -11.60% | -14.72% | 3.34% |
| 80-84.99 | 37 | 13.51% | 32 | -10.97% | -10.80% | -14.47% | 3.46% |
| 85-89.99 | 80 | 21.25% | 63 | -8.36% | -10.90% | -13.95% | 5.54% |
| 90+ | 85 | 24.71% | 64 | -6.03% | -9.59% | -16.12% | 5.54% |
| 58-71.99 | 6 | 33.33% | 4 | -4.86% | -7.05% | -12.15% | 7.58% |

## By Confirmation Components

| Components | Rows | Hit Rate | Failed | Avg Endpoint | Median Endpoint | Median Worst Low | Median Best High |
|---|---:|---:|---:|---:|---:|---:|---:|
| BULL_PHASE_STRUCTURE_SUPPORT | 104 | 16.35% | 87 | -9.87% | -10.95% | -14.22% | 3.52% |
| BULL_PHASE_STRUCTURE_SUPPORT+PARTICIPATION_SUPPORT | 98 | 18.37% | 80 | -7.57% | -10.28% | -14.71% | 4.49% |
| BULL_PHASE_STRUCTURE_SUPPORT+PARTICIPATION_SUPPORT+ACCEPTANCE_SUPPORT | 21 | 19.05% | 17 | -8.50% | -13.49% | -18.20% | 7.80% |
| BULL_PHASE_STRUCTURE_SUPPORT+ACCEPTANCE_SUPPORT | 26 | 23.08% | 20 | -9.41% | -14.49% | -19.20% | 4.17% |
| ACCEPTANCE_SUPPORT | 3 | 33.33% | 2 | -1.27% | -8.47% | -14.47% | 9.52% |
| ROUTE_ONLY | 5 | 40.00% | 3 | -0.30% | -7.25% | -17.31% | 9.32% |
| PARTICIPATION_SUPPORT | 2 | 50.00% | 1 | -4.05% | -4.05% | -18.51% | 9.57% |
| PARTICIPATION_SUPPORT+ACCEPTANCE_SUPPORT | 1 | 100.00% | 0 | 4.66% | 4.66% | -3.63% | 15.54% |

## By Ranking Collision Bucket

| Ranking Bucket | Rows | Hit Rate | Failed | Avg Endpoint | Median Endpoint | Median Worst Low | Median Best High |
|---|---:|---:|---:|---:|---:|---:|---:|
| MOMENTUM_SETUP | 137 | 15.33% | 116 | -10.21% | -11.66% | -15.86% | 3.92% |
| CROSSOVER+MOMENTUM_SETUP | 13 | 15.38% | 11 | -15.19% | -13.97% | -19.33% | 2.21% |
| MOMENTUM_SETUP+DIVERGENCE | 106 | 24.53% | 80 | -5.88% | -7.73% | -13.05% | 6.61% |
| CROSSOVER+MOMENTUM_SETUP+DIVERGENCE | 4 | 25.00% | 3 | 4.60% | -14.23% | -21.74% | 2.81% |

## Worst High-Score Failures

| D Date | Symbol | Score | Priority | Endpoint | Worst Low | Best High | Components | Ranking Bucket |
|---|---|---:|---|---:|---:|---:|---|---|
| 2026-02-11 | HRI | 93.00 | A | -38.36% | -38.66% | 1.85% | BULL_PHASE_STRUCTURE_SUPPORT+PARTICIPATION_SUPPORT | MOMENTUM_SETUP |
| 2026-02-11 | RAIL | 93.00 | A | -36.13% | -37.09% | 9.64% | BULL_PHASE_STRUCTURE_SUPPORT+PARTICIPATION_SUPPORT | MOMENTUM_SETUP |
| 2026-02-11 | CMCO | 88.00 | A | -33.82% | -34.33% | 1.89% | BULL_PHASE_STRUCTURE_SUPPORT+PARTICIPATION_SUPPORT | MOMENTUM_SETUP+DIVERGENCE |
| 2026-03-11 | NIU | 93.00 | A | -32.70% | -35.32% | 0.95% | BULL_PHASE_STRUCTURE_SUPPORT+PARTICIPATION_SUPPORT | MOMENTUM_SETUP+DIVERGENCE |
| 2026-02-11 | WNC | 85.00 | A | -32.40% | -32.40% | 6.41% | BULL_PHASE_STRUCTURE_SUPPORT | MOMENTUM_SETUP |
| 2026-02-11 | KWR | 85.00 | A | -31.98% | -32.29% | 2.95% | BULL_PHASE_STRUCTURE_SUPPORT | MOMENTUM_SETUP+DIVERGENCE |
| 2026-02-11 | TWI | 86.00 | A | -30.09% | -30.61% | 2.63% | BULL_PHASE_STRUCTURE_SUPPORT+PARTICIPATION_SUPPORT | MOMENTUM_SETUP |
| 2026-02-11 | PSIX | 98.00 | A | -29.45% | -43.49% | 24.04% | BULL_PHASE_STRUCTURE_SUPPORT+PARTICIPATION_SUPPORT+ACCEPTANCE_SUPPORT | MOMENTUM_SETUP |
| 2026-02-11 | MTUS | 90.00 | A | -29.24% | -29.61% | 0.60% | BULL_PHASE_STRUCTURE_SUPPORT+ACCEPTANCE_SUPPORT | MOMENTUM_SETUP+DIVERGENCE |
| 2026-02-11 | CECO | 98.00 | A | -28.73% | -34.23% | 7.27% | BULL_PHASE_STRUCTURE_SUPPORT+PARTICIPATION_SUPPORT+ACCEPTANCE_SUPPORT | MOMENTUM_SETUP+DIVERGENCE |
| 2026-02-11 | ACNT | 88.00 | NEEDS_MANUAL_REVIEW | -27.10% | -30.21% | 1.19% | BULL_PHASE_STRUCTURE_SUPPORT+PARTICIPATION_SUPPORT | MOMENTUM_SETUP |
| 2026-02-11 | ASTL | 85.00 | A | -27.08% | -27.37% | 1.98% | BULL_PHASE_STRUCTURE_SUPPORT | MOMENTUM_SETUP+DIVERGENCE |
| 2026-02-11 | SND | 98.00 | A | -25.25% | -26.76% | 12.45% | BULL_PHASE_STRUCTURE_SUPPORT+PARTICIPATION_SUPPORT+ACCEPTANCE_SUPPORT | MOMENTUM_SETUP+DIVERGENCE |
| 2026-02-11 | GFF | 86.00 | A | -25.23% | -25.60% | 1.60% | BULL_PHASE_STRUCTURE_SUPPORT+PARTICIPATION_SUPPORT | MOMENTUM_SETUP+DIVERGENCE |
| 2026-02-11 | OC | 85.00 | A | -25.03% | -25.34% | 3.29% | BULL_PHASE_STRUCTURE_SUPPORT | MOMENTUM_SETUP |
| 2026-02-11 | SXC | 90.00 | A | -24.74% | -32.88% | 0.96% | BULL_PHASE_STRUCTURE_SUPPORT+ACCEPTANCE_SUPPORT | MOMENTUM_SETUP+DIVERGENCE |
| 2026-02-11 | NX | 93.00 | A | -23.71% | -26.85% | 2.82% | BULL_PHASE_STRUCTURE_SUPPORT+PARTICIPATION_SUPPORT | MOMENTUM_SETUP+DIVERGENCE |
| 2026-02-11 | ESAB | 85.00 | A | -22.99% | -24.23% | 2.16% | BULL_PHASE_STRUCTURE_SUPPORT | MOMENTUM_SETUP |
| 2026-02-11 | IOSP | 88.00 | A | -22.16% | -22.34% | 4.21% | BULL_PHASE_STRUCTURE_SUPPORT+PARTICIPATION_SUPPORT | MOMENTUM_SETUP+DIVERGENCE |
| 2026-02-11 | TNC | 86.00 | A | -22.10% | -26.02% | 5.23% | BULL_PHASE_STRUCTURE_SUPPORT+PARTICIPATION_SUPPORT | MOMENTUM_SETUP+DIVERGENCE |
| 2026-02-11 | GOLD | 88.00 | A | -21.89% | -23.39% | 1.01% | BULL_PHASE_STRUCTURE_SUPPORT+PARTICIPATION_SUPPORT | MOMENTUM_SETUP |
| 2026-02-11 | CRH | 85.00 | A | -21.71% | -22.03% | -0.60% | BULL_PHASE_STRUCTURE_SUPPORT | MOMENTUM_SETUP |
| 2026-02-11 | DCI | 88.00 | A | -21.12% | -21.96% | 2.33% | BULL_PHASE_STRUCTURE_SUPPORT+PARTICIPATION_SUPPORT | MOMENTUM_SETUP+DIVERGENCE |
| 2026-02-11 | MAS | 98.00 | A | -20.35% | -20.54% | 3.01% | BULL_PHASE_STRUCTURE_SUPPORT+PARTICIPATION_SUPPORT+ACCEPTANCE_SUPPORT | MOMENTUM_SETUP |
| 2026-02-11 | MEC | 93.00 | A | -20.24% | -21.16% | 3.35% | BULL_PHASE_STRUCTURE_SUPPORT+PARTICIPATION_SUPPORT | MOMENTUM_SETUP |

## Readout

- The remaining Industrial February-March pullback re-entry problem is not isolated to missing confirmation; the common `BULL_PHASE_STRUCTURE_SUPPORT+PARTICIPATION_SUPPORT` group is also weak.
- High score is not protective in this slice: `TotalScore >= 85` still has weak D+20 endpoint behavior and deep median worst-low exposure.
- `ReviewPriority` does not separate this failure mode because most rows are priority `A`.
- Ranking collisions show weakness both in standalone Momentum Setup rows and in rows where Crossover/Divergence also had candidates.
- Do not introduce a second hard rule from this split alone. The next safer step is to add a reportable Industrial Feb-Mar caution tag/diagnostic or broaden date-regime context, then validate on more dates before suppressing more candidates.
