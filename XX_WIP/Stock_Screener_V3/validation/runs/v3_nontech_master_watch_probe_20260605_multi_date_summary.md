# V3 Multi-Date Backtest Summary

- Runs: 2
- Stage families: CROSSOVER, MOMENTUM_SETUP, DIVERGENCE
- Universe file: D:\Tools\Stock_Screener_V3\data\samples\us_non_technology_master_sample_20260605.csv
- Symbols attempted: 400
- Symbols processed: 372
- Symbols skipped: 28
- Candidates found: 276
- Candidate density: 0.7419

## Runs

| D Date | Processed | Skipped | Candidates | Density |
|---|---:|---:|---:|---:|
| 2026-02-11 | 186 | 14 | 150 | 0.8065 |
| 2026-03-11 | 186 | 14 | 126 | 0.6774 |

## Aggregate Forward Outcomes

| Horizon | Evaluated | Positive | Hit Rate | Average Return | Median Return |
|---|---:|---:|---:|---:|---:|
| D+1 | 276 | 70 | 25.36% | -1.51% | -1.36% |
| D+2 | 276 | 94 | 34.06% | -0.50% | -1.31% |
| D+5 | 276 | 96 | 34.78% | -1.39% | -1.45% |
| D+10 | 276 | 103 | 37.32% | -2.15% | -1.73% |
| D+20 | 276 | 96 | 34.78% | -5.12% | -3.49% |

## Ranking Collision Buckets

| Active Families Before Ranking | Rows |
|---|---:|
| CROSSOVER | 116 |
| CROSSOVER+DIVERGENCE | 91 |
| NONE | 50 |
| CROSSOVER+DIVERGENCE+MOMENTUM_SETUP | 42 |
| CROSSOVER+MOMENTUM_SETUP | 35 |
| MOMENTUM_SETUP | 18 |
| DIVERGENCE | 15 |
| DIVERGENCE+MOMENTUM_SETUP | 5 |
