# V3 Non-Technology Watch Probe Review

Run label: `v3_nontech_watch_probe_20260605`

Universe file: `data/samples/us_non_technology_liquid_seed.csv`

Purpose: check whether the Technology weak-date pattern `WATCH + BELOW_EMA200` also appears in a non-Technology NYSE/NASDAQ liquid-stock sample.

## Run Setup

- Universe seed size: 74 non-Technology liquid US stocks.
- Sample size: 45.
- Random seed: 20260605.
- D dates: `2026-02-11`, `2026-03-11`.
- Stage families: `CROSSOVER,MOMENTUM_SETUP,DIVERGENCE`.
- Forward horizons: D+1, D+2, D+5, D+10, D+20.

Generated artifacts:

- `validation/runs/v3_nontech_watch_probe_20260605_20260211_summary.md`
- `validation/runs/v3_nontech_watch_probe_20260605_20260311_summary.md`
- `validation/runs/v3_nontech_watch_probe_20260605_multi_date_summary.md`

## Aggregate Result

| Runs | Processed | Skipped | Candidates | Density |
|---:|---:|---:|---:|---:|
| 2 | 90 | 0 | 68 | 0.7556 |

| Horizon | Evaluated | Positive | Hit Rate | Average Return | Median Return |
|---|---:|---:|---:|---:|---:|
| D+1 | 68 | 27 | 39.71% | -0.25% | -0.40% |
| D+2 | 68 | 35 | 51.47% | 0.07% | 0.11% |
| D+5 | 68 | 30 | 44.12% | -0.66% | -1.23% |
| D+10 | 68 | 31 | 45.59% | -0.37% | -0.59% |
| D+20 | 68 | 37 | 54.41% | -0.45% | 1.02% |

## WATCH / BELOW_EMA200 Comparison

| D date | Segment | Candidates | D+20 hit rate | D+20 average return |
|---|---|---:|---:|---:|
| 2026-02-11 | SELECTED | 36 | 44.44% | -2.62% |
| 2026-02-11 | WATCH | 1 | 0.00% | -3.58% |
| 2026-02-11 | WATCH + BELOW_EMA200 | 0 | n/a | n/a |
| 2026-03-11 | SELECTED | 21 | 71.43% | 2.90% |
| 2026-03-11 | WATCH | 10 | 60.00% | 0.62% |
| 2026-03-11 | WATCH + BELOW_EMA200 | 4 | 100.00% | 5.35% |

## Read

This small non-Technology probe does not confirm the Technology weak-date `WATCH + BELOW_EMA200` weakness.

In the Technology run, March `WATCH + BELOW_EMA200` had 102 candidates with 10.78% D+20 hit rate and -8.89% average return. In this non-Technology probe, March `WATCH + BELOW_EMA200` had only 4 candidates and all had positive D+20 outcomes.

Do not promote a generic `WATCH + BELOW_EMA200` downgrade rule from the Technology-only evidence.

## Next Calibration Direction

1. Keep `WATCH + BELOW_EMA200` as a monitored risk segment in reports.
2. Do not change priority rules yet.
3. Expand non-Technology validation with larger sector-specific universes before changing thresholds.
4. Treat the Technology weakness as sector/regime-specific until broader samples prove otherwise.

