# V3 Multi-Date Backtest Summary

- Runs: 2
- Stage families: CROSSOVER, MOMENTUM_SETUP, DIVERGENCE
- Universe file: D:\Tools\Stock_Screener_V3\data\samples\us_usa_folder_nontech_sector_universe_20260605.csv
- Symbols attempted: 400
- Symbols processed: 384
- Symbols skipped: 16
- Candidates found: 315
- Candidate density: 0.8203

## Runs

| D Date | Processed | Skipped | Candidates | Density |
|---|---:|---:|---:|---:|
| 2026-02-11 | 191 | 9 | 163 | 0.8534 |
| 2026-03-11 | 193 | 7 | 152 | 0.7876 |

## Aggregate Forward Outcomes

| Horizon | Evaluated | Positive | Hit Rate | Average Return | Median Return |
|---|---:|---:|---:|---:|---:|
| D+1 | 315 | 94 | 29.84% | -1.76% | -1.90% |
| D+2 | 315 | 109 | 34.60% | -1.52% | -1.34% |
| D+5 | 315 | 125 | 39.68% | -1.22% | -1.08% |
| D+10 | 315 | 161 | 51.11% | 0.77% | 0.30% |
| D+20 | 315 | 150 | 47.62% | -0.28% | -0.59% |

## Ranking Collision Buckets

| Active Families Before Ranking | Rows |
|---|---:|
| CROSSOVER | 93 |
| CROSSOVER+DIVERGENCE | 81 |
| CROSSOVER+MOMENTUM_SETUP | 71 |
| CROSSOVER+DIVERGENCE+MOMENTUM_SETUP | 48 |
| NONE | 40 |
| DIVERGENCE | 23 |
| MOMENTUM_SETUP | 20 |
| DIVERGENCE+MOMENTUM_SETUP | 8 |
