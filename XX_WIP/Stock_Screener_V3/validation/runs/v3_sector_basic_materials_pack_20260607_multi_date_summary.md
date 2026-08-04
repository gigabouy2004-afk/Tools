# V3 Multi-Date Backtest Summary

- Runs: 3
- Stage families: CROSSOVER, MOMENTUM_SETUP, DIVERGENCE
- Universe file: D:\Tools\Stock_Screener_V3\data\samples\00-NYSE_NASDAQ_Common_Stocks_Sector-BasicMaterials.csv
- Symbols attempted: 381
- Symbols processed: 361
- Symbols skipped: 20
- Candidates found: 285
- Candidate density: 0.7895

## Runs

| D Date | Processed | Skipped | Candidates | Density |
|---|---:|---:|---:|---:|
| 2026-02-11 | 120 | 7 | 81 | 0.6750 |
| 2026-03-11 | 120 | 7 | 92 | 0.7667 |
| 2026-04-11 | 121 | 6 | 112 | 0.9256 |

## Aggregate Forward Outcomes

| Horizon | Evaluated | Positive | Hit Rate | Average Return | Median Return |
|---|---:|---:|---:|---:|---:|
| D+1 | 285 | 103 | 36.14% | -1.71% | -1.60% |
| D+2 | 285 | 117 | 41.05% | -1.91% | -1.46% |
| D+5 | 285 | 119 | 41.75% | -2.26% | -2.57% |
| D+10 | 285 | 124 | 43.51% | -2.61% | -1.85% |
| D+20 | 285 | 94 | 32.98% | -3.23% | -4.49% |

## Ranking Collision Buckets

| Active Families Before Ranking | Rows |
|---|---:|
| CROSSOVER | 117 |
| CROSSOVER+DIVERGENCE | 65 |
| CROSSOVER+MOMENTUM_SETUP | 59 |
| NONE | 43 |
| CROSSOVER+DIVERGENCE+MOMENTUM_SETUP | 34 |
| DIVERGENCE | 18 |
| MOMENTUM_SETUP | 17 |
| DIVERGENCE+MOMENTUM_SETUP | 8 |
