# V3 Multi-Date Backtest Summary

- Runs: 2
- Stage families: CROSSOVER
- Universe file: D:\Tools\Stock_Screener_V3\data\samples\00-NYSE_NASDAQ_Common_Stocks_Sector-Technology.csv
- Symbols attempted: 1050
- Symbols processed: 1037
- Symbols skipped: 13
- Candidates found: 417
- Candidate density: 0.4021

## Runs

| D Date | Processed | Skipped | Candidates | Density |
|---|---:|---:|---:|---:|
| 2026-05-11 | 517 | 8 | 176 | 0.3404 |
| 2026-06-11 | 520 | 5 | 241 | 0.4635 |

## Aggregate Forward Outcomes

| Horizon | Evaluated | Positive | Hit Rate | Average Return | Median Return |
|---|---:|---:|---:|---:|---:|
| D+1 | 176 | 49 | 27.84% | -1.73% | -1.71% |
| D+2 | 176 | 37 | 21.02% | -3.72% | -3.70% |
| D+5 | 175 | 74 | 42.29% | -1.61% | -0.76% |

## Aggregate Forward Path Outcomes

| Horizon | Evaluated | Avg Worst Low | Median Worst Low | Avg Best High | Median Best High |
|---|---:|---:|---:|---:|---:|
| D+1 | 176 | -3.56% | -3.10% | 1.73% | 1.43% |
| D+2 | 176 | -6.59% | -6.00% | 2.45% | 1.68% |
| D+5 | 175 | -8.84% | -7.86% | 4.30% | 3.09% |

## Stage Family Path Outcomes D+1

| Group | Candidates | Evaluated | Avg Worst Low | Median Worst Low | Avg Best High | Median Best High |
|---|---:|---:|---:|---:|---:|---:|
| CROSSOVER | 417 | 176 | -3.56% | -3.10% | 1.73% | 1.43% |

## Stage Family Path Outcomes D+2

| Group | Candidates | Evaluated | Avg Worst Low | Median Worst Low | Avg Best High | Median Best High |
|---|---:|---:|---:|---:|---:|---:|
| CROSSOVER | 417 | 176 | -6.59% | -6.00% | 2.45% | 1.68% |

## Stage Family Path Outcomes D+5

| Group | Candidates | Evaluated | Avg Worst Low | Median Worst Low | Avg Best High | Median Best High |
|---|---:|---:|---:|---:|---:|---:|
| CROSSOVER | 417 | 175 | -8.84% | -7.86% | 4.30% | 3.09% |

## Candidate State Path Outcomes D+1

| Group | Candidates | Evaluated | Avg Worst Low | Median Worst Low | Avg Best High | Median Best High |
|---|---:|---:|---:|---:|---:|---:|
| PRE_BEAR_CROSSOVER | 410 | 171 | -3.50% | -3.05% | 1.70% | 1.43% |
| PRE_BULL_CROSSOVER | 7 | 5 | -5.65% | -5.33% | 2.68% | 2.13% |

## Candidate State Path Outcomes D+2

| Group | Candidates | Evaluated | Avg Worst Low | Median Worst Low | Avg Best High | Median Best High |
|---|---:|---:|---:|---:|---:|---:|
| PRE_BEAR_CROSSOVER | 410 | 171 | -6.52% | -5.98% | 2.42% | 1.67% |
| PRE_BULL_CROSSOVER | 7 | 5 | -8.88% | -6.34% | 3.47% | 3.67% |

## Candidate State Path Outcomes D+5

| Group | Candidates | Evaluated | Avg Worst Low | Median Worst Low | Avg Best High | Median Best High |
|---|---:|---:|---:|---:|---:|---:|
| PRE_BEAR_CROSSOVER | 410 | 170 | -8.76% | -7.82% | 4.11% | 3.05% |
| PRE_BULL_CROSSOVER | 7 | 5 | -11.80% | -10.43% | 10.65% | 6.99% |

## Ranking Collision Buckets

| Active Families Before Ranking | Rows |
|---|---:|
| CROSSOVER | 576 |
| NONE | 461 |
