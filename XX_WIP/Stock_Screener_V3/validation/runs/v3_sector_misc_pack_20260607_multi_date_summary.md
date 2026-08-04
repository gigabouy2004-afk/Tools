# V3 Multi-Date Backtest Summary

- Runs: 3
- Stage families: CROSSOVER, MOMENTUM_SETUP, DIVERGENCE
- Universe file: D:\Tools\Stock_Screener_V3\data\samples\00-NYSE_NASDAQ_Common_Stocks_Sector-Misc.csv
- Symbols attempted: 225
- Symbols processed: 194
- Symbols skipped: 31
- Candidates found: 146
- Candidate density: 0.7526

## Runs

| D Date | Processed | Skipped | Candidates | Density |
|---|---:|---:|---:|---:|
| 2026-02-11 | 64 | 11 | 43 | 0.6719 |
| 2026-03-11 | 65 | 10 | 49 | 0.7538 |
| 2026-04-11 | 65 | 10 | 54 | 0.8308 |

## Aggregate Forward Outcomes

| Horizon | Evaluated | Positive | Hit Rate | Average Return | Median Return |
|---|---:|---:|---:|---:|---:|
| D+1 | 146 | 52 | 35.62% | -0.85% | -1.24% |
| D+2 | 146 | 61 | 41.78% | -0.32% | -0.55% |
| D+5 | 146 | 71 | 48.63% | 0.64% | -0.05% |
| D+10 | 146 | 78 | 53.42% | 1.34% | 0.78% |
| D+20 | 146 | 60 | 41.10% | -1.83% | -3.08% |

## Ranking Collision Buckets

| Active Families Before Ranking | Rows |
|---|---:|
| CROSSOVER | 57 |
| CROSSOVER+DIVERGENCE | 41 |
| CROSSOVER+MOMENTUM_SETUP | 41 |
| CROSSOVER+DIVERGENCE+MOMENTUM_SETUP | 18 |
| NONE | 17 |
| DIVERGENCE | 13 |
| MOMENTUM_SETUP | 6 |
| DIVERGENCE+MOMENTUM_SETUP | 1 |
