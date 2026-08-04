# V3 Multi-Date Backtest Summary

- Runs: 3
- Stage families: CROSSOVER, MOMENTUM_SETUP, DIVERGENCE
- Universe file: D:\Tools\Stock_Screener_V3\data\samples\00-NYSE_NASDAQ_Common_Stocks_Sector-Technology-Semiconductor.csv
- Symbols attempted: 255
- Symbols processed: 255
- Symbols skipped: 0
- Candidates found: 189
- Candidate density: 0.7412

## Runs

| D Date | Processed | Skipped | Candidates | Density |
|---|---:|---:|---:|---:|
| 2026-02-11 | 85 | 0 | 64 | 0.7529 |
| 2026-03-11 | 85 | 0 | 46 | 0.5412 |
| 2026-04-11 | 85 | 0 | 79 | 0.9294 |

## Aggregate Forward Outcomes

| Horizon | Evaluated | Positive | Hit Rate | Average Return | Median Return |
|---|---:|---:|---:|---:|---:|
| D+1 | 189 | 74 | 39.15% | -0.46% | -1.18% |
| D+2 | 189 | 92 | 48.68% | 0.64% | -0.42% |
| D+5 | 189 | 103 | 54.50% | 3.55% | 1.72% |
| D+10 | 189 | 125 | 66.14% | 12.11% | 7.26% |
| D+20 | 189 | 110 | 58.20% | 18.11% | 8.69% |

## Ranking Collision Buckets

| Active Families Before Ranking | Rows |
|---|---:|
| CROSSOVER+MOMENTUM_SETUP | 53 |
| CROSSOVER+DIVERGENCE+MOMENTUM_SETUP | 46 |
| CROSSOVER | 43 |
| NONE | 42 |
| CROSSOVER+DIVERGENCE | 35 |
| DIVERGENCE | 19 |
| DIVERGENCE+MOMENTUM_SETUP | 9 |
| MOMENTUM_SETUP | 8 |
