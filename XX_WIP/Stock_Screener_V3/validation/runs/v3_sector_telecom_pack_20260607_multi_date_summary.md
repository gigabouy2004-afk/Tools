# V3 Multi-Date Backtest Summary

- Runs: 3
- Stage families: CROSSOVER, MOMENTUM_SETUP, DIVERGENCE
- Universe file: D:\Tools\Stock_Screener_V3\data\samples\00-NYSE_NASDAQ_Common_Stocks_Sector-Telecom.csv
- Symbols attempted: 192
- Symbols processed: 191
- Symbols skipped: 1
- Candidates found: 161
- Candidate density: 0.8429

## Runs

| D Date | Processed | Skipped | Candidates | Density |
|---|---:|---:|---:|---:|
| 2026-02-11 | 63 | 1 | 54 | 0.8571 |
| 2026-03-11 | 64 | 0 | 50 | 0.7812 |
| 2026-04-11 | 64 | 0 | 57 | 0.8906 |

## Aggregate Forward Outcomes

| Horizon | Evaluated | Positive | Hit Rate | Average Return | Median Return |
|---|---:|---:|---:|---:|---:|
| D+1 | 161 | 76 | 47.20% | -0.01% | -0.25% |
| D+2 | 161 | 82 | 50.93% | 0.34% | 0.07% |
| D+5 | 161 | 90 | 55.90% | 2.21% | 0.72% |
| D+10 | 161 | 86 | 53.42% | 2.11% | 0.74% |
| D+20 | 161 | 81 | 50.31% | 3.64% | 0.01% |

## Ranking Collision Buckets

| Active Families Before Ranking | Rows |
|---|---:|
| CROSSOVER | 53 |
| CROSSOVER+MOMENTUM_SETUP | 37 |
| CROSSOVER+DIVERGENCE | 36 |
| CROSSOVER+DIVERGENCE+MOMENTUM_SETUP | 24 |
| NONE | 13 |
| DIVERGENCE+MOMENTUM_SETUP | 11 |
| MOMENTUM_SETUP | 10 |
| DIVERGENCE | 7 |
