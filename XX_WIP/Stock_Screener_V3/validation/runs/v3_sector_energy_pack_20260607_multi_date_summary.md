# V3 Multi-Date Backtest Summary

- Runs: 3
- Stage families: CROSSOVER, MOMENTUM_SETUP, DIVERGENCE
- Universe file: D:\Tools\Stock_Screener_V3\data\samples\00-NYSE_NASDAQ_Common_Stocks_Sector-Energy.csv
- Symbols attempted: 417
- Symbols processed: 402
- Symbols skipped: 15
- Candidates found: 358
- Candidate density: 0.8905

## Runs

| D Date | Processed | Skipped | Candidates | Density |
|---|---:|---:|---:|---:|
| 2026-02-11 | 134 | 5 | 120 | 0.8955 |
| 2026-03-11 | 134 | 5 | 119 | 0.8881 |
| 2026-04-11 | 134 | 5 | 119 | 0.8881 |

## Aggregate Forward Outcomes

| Horizon | Evaluated | Positive | Hit Rate | Average Return | Median Return |
|---|---:|---:|---:|---:|---:|
| D+1 | 358 | 166 | 46.37% | -0.57% | -0.34% |
| D+2 | 358 | 134 | 37.43% | -0.62% | -1.10% |
| D+5 | 358 | 197 | 55.03% | 0.65% | 0.58% |
| D+10 | 358 | 232 | 64.80% | 3.94% | 2.53% |
| D+20 | 358 | 218 | 60.89% | 4.10% | 2.53% |

## Ranking Collision Buckets

| Active Families Before Ranking | Rows |
|---|---:|
| CROSSOVER | 102 |
| CROSSOVER+DIVERGENCE | 94 |
| CROSSOVER+MOMENTUM_SETUP | 75 |
| CROSSOVER+DIVERGENCE+MOMENTUM_SETUP | 63 |
| DIVERGENCE | 21 |
| NONE | 19 |
| MOMENTUM_SETUP | 18 |
| DIVERGENCE+MOMENTUM_SETUP | 10 |
