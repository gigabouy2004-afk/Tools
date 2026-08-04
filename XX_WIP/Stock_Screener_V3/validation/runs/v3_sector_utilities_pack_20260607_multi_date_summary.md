# V3 Multi-Date Backtest Summary

- Runs: 3
- Stage families: CROSSOVER, MOMENTUM_SETUP, DIVERGENCE
- Universe file: D:\Tools\Stock_Screener_V3\data\samples\00-NYSE_NASDAQ_Common_Stocks_Sector-Utilities.csv
- Symbols attempted: 369
- Symbols processed: 366
- Symbols skipped: 3
- Candidates found: 331
- Candidate density: 0.9044

## Runs

| D Date | Processed | Skipped | Candidates | Density |
|---|---:|---:|---:|---:|
| 2026-02-11 | 122 | 1 | 111 | 0.9098 |
| 2026-03-11 | 122 | 1 | 107 | 0.8770 |
| 2026-04-11 | 122 | 1 | 113 | 0.9262 |

## Aggregate Forward Outcomes

| Horizon | Evaluated | Positive | Hit Rate | Average Return | Median Return |
|---|---:|---:|---:|---:|---:|
| D+1 | 331 | 152 | 45.92% | -0.55% | -0.17% |
| D+2 | 331 | 169 | 51.06% | 0.26% | 0.10% |
| D+5 | 331 | 166 | 50.15% | 0.33% | 0.04% |
| D+10 | 331 | 157 | 47.43% | 0.73% | -0.28% |
| D+20 | 331 | 175 | 52.87% | 0.66% | 0.49% |

## Ranking Collision Buckets

| Active Families Before Ranking | Rows |
|---|---:|
| CROSSOVER+DIVERGENCE | 90 |
| CROSSOVER | 83 |
| CROSSOVER+MOMENTUM_SETUP | 76 |
| CROSSOVER+DIVERGENCE+MOMENTUM_SETUP | 55 |
| MOMENTUM_SETUP | 21 |
| DIVERGENCE+MOMENTUM_SETUP | 15 |
| DIVERGENCE | 13 |
| NONE | 13 |
