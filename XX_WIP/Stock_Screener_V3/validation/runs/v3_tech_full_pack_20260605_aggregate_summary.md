# V3 Technology Full-Universe Multi-Date Validation Summary

Run date: 2026-06-05

Universe file: `data/samples/00-NYSE_NASDAQ_Common_Stocks_Sector-Technology.csv`

Stage families: `CROSSOVER,MOMENTUM_SETUP,DIVERGENCE`

Forward horizons: D+1, D+2, D+5, D+10, D+20

Note: the original `backtest-pack` command produced all three per-date CSV/summary/log artifacts but timed out before writing the aggregate markdown. This file summarizes the completed per-date artifacts.

## Completed Date Runs

| D date | Symbols processed | Symbols skipped | Candidates | Candidate density |
|---|---:|---:|---:|---:|
| 2026-02-11 | 512 | 13 | 354 | 0.6914 |
| 2026-03-11 | 514 | 11 | 354 | 0.6887 |
| 2026-04-11 | 514 | 11 | 450 | 0.8755 |

## Aggregate Forward Outcomes

| Horizon | Evaluated | Positive | Hit Rate | Average Return | Median Return |
|---|---:|---:|---:|---:|---:|
| D+1 | 1158 | 531 | 45.85% | 0.19% | -0.27% |
| D+2 | 1158 | 595 | 51.38% | 0.98% | 0.16% |
| D+5 | 1158 | 662 | 57.17% | 3.39% | 1.31% |
| D+10 | 1158 | 668 | 57.69% | 5.15% | 2.39% |
| D+20 | 1158 | 619 | 53.45% | 8.86% | 1.56% |

## Per-Date Forward Outcomes

| D date | Horizon | Evaluated | Positive | Hit Rate | Average Return | Median Return |
|---|---|---:|---:|---:|---:|---:|
| 2026-02-11 | D+1 | 354 | 61 | 17.23% | -2.26% | -2.73% |
| 2026-02-11 | D+2 | 354 | 115 | 32.49% | -0.88% | -1.54% |
| 2026-02-11 | D+5 | 354 | 129 | 36.44% | -1.00% | -1.80% |
| 2026-02-11 | D+10 | 354 | 154 | 43.50% | 0.20% | -1.10% |
| 2026-02-11 | D+20 | 354 | 125 | 35.31% | -1.80% | -5.40% |
| 2026-03-11 | D+1 | 354 | 61 | 17.23% | -2.10% | -2.17% |
| 2026-03-11 | D+2 | 354 | 73 | 20.62% | -2.54% | -2.44% |
| 2026-03-11 | D+5 | 354 | 110 | 31.07% | -2.83% | -2.62% |
| 2026-03-11 | D+10 | 354 | 120 | 33.90% | -2.51% | -3.70% |
| 2026-03-11 | D+20 | 354 | 124 | 35.03% | -1.61% | -4.98% |
| 2026-04-11 | D+1 | 450 | 409 | 90.89% | 3.93% | 3.35% |
| 2026-04-11 | D+2 | 450 | 407 | 90.44% | 5.22% | 4.28% |
| 2026-04-11 | D+5 | 450 | 423 | 94.00% | 11.73% | 10.39% |
| 2026-04-11 | D+10 | 450 | 394 | 87.56% | 15.06% | 11.31% |
| 2026-04-11 | D+20 | 450 | 370 | 82.22% | 25.48% | 18.27% |

## Candidate Family Mix

| D date | CROSSOVER | MOMENTUM_SETUP | DIVERGENCE |
|---|---:|---:|---:|
| 2026-02-11 | 153 | 82 | 119 |
| 2026-03-11 | 104 | 83 | 167 |
| 2026-04-11 | 162 | 174 | 114 |

## Diagnostic Coverage

All processed rows in the three detail CSVs include traversal, ranking, and Divergence diagnostic fields.

| D date | Detail rows | Ranking diagnostics | Traversal diagnostics | Divergence diagnostics |
|---|---:|---:|---:|---:|
| 2026-02-11 | 512 | 512 | 512 | 512 |
| 2026-03-11 | 514 | 514 | 514 | 514 |
| 2026-04-11 | 514 | 514 | 514 | 514 |

## Initial Calibration Notes

- February and March Technology runs produced high candidate density but weak forward outcomes, especially in short horizons.
- April 2026 produced very strong broad Technology follow-through across all horizons, so aggregate performance is heavily regime-dependent.
- `DIVERGENCE` meaningfully competes with `CROSSOVER` and `MOMENTUM_SETUP`; it was the leading candidate family on 2026-03-11.
- `MOMENTUM_SETUP` became the leading candidate family on 2026-04-11, matching the strong bull continuation/re-entry environment.
- `MOMENTUM_SETUP` blocking fired through traversal diagnostics on all three dates when stock baseline was bearish, while bearish `CROSSOVER` remained available for exit/capital-preservation review.
- This is a validation baseline, not a rule-tuning justification. Do not tune thresholds from these three Technology-only dates alone.

