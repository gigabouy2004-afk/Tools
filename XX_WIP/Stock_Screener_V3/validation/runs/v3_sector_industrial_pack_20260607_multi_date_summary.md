# V3 Multi-Date Backtest Summary

- Runs: 3
- Stage families: CROSSOVER, MOMENTUM_SETUP, DIVERGENCE
- Universe file: D:\Tools\Stock_Screener_V3\data\samples\00-NYSE_NASDAQ_Common_Stocks_Sector-Industrial.csv
- Symbols attempted: 1404
- Symbols processed: 1370
- Symbols skipped: 34
- Candidates found: 1140
- Candidate density: 0.8321

## Runs

| D Date | Processed | Skipped | Candidates | Density |
|---|---:|---:|---:|---:|
| 2026-02-11 | 455 | 13 | 385 | 0.8462 |
| 2026-03-11 | 457 | 11 | 337 | 0.7374 |
| 2026-04-11 | 458 | 10 | 418 | 0.9127 |

## Aggregate Forward Outcomes

| Horizon | Evaluated | Positive | Hit Rate | Average Return | Median Return |
|---|---:|---:|---:|---:|---:|
| D+1 | 1140 | 477 | 41.84% | -0.71% | -0.53% |
| D+2 | 1140 | 515 | 45.18% | -0.54% | -0.31% |
| D+5 | 1140 | 529 | 46.40% | -0.07% | -0.42% |
| D+10 | 1140 | 575 | 50.44% | 1.00% | 0.11% |
| D+20 | 1140 | 553 | 48.51% | 0.74% | -0.43% |

## Ranking Collision Buckets

| Active Families Before Ranking | Rows |
|---|---:|
| CROSSOVER+MOMENTUM_SETUP | 262 |
| CROSSOVER | 257 |
| CROSSOVER+DIVERGENCE+MOMENTUM_SETUP | 239 |
| CROSSOVER+DIVERGENCE | 226 |
| NONE | 152 |
| MOMENTUM_SETUP | 99 |
| DIVERGENCE | 79 |
| DIVERGENCE+MOMENTUM_SETUP | 56 |
