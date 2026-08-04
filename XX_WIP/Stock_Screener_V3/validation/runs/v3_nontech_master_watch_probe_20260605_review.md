# V3 Non-Technology Master Watch Probe Review

Run label: `v3_nontech_master_watch_probe_20260605`

Master source: `D:\Tools\StockCodeMaster\Script\NYSE_NASDAQ_Master_Library.csv`

Derived universe: `data/samples/us_non_technology_master_sample_20260605.csv`

Purpose: test whether the Technology weak-date `WATCH + BELOW_EMA200` pattern appears in a larger non-Technology NYSE/NASDAQ sample.

## Universe

The derived universe contains common stocks only:

- `ETF = N`
- `Sector` is present
- `Sector != Technology`

Rows in derived universe: 5,535.

Sector counts:

| Sector | Rows |
|---|---:|
| Finance | 1578 |
| Health Care | 1095 |
| Consumer Discretionary | 1022 |
| Industrials | 621 |
| Real Estate | 390 |
| Energy | 196 |
| Utilities | 175 |
| Consumer Staples | 150 |
| Basic Materials | 144 |
| Telecommunications | 102 |
| Miscellaneous | 62 |

## Run Setup

- Sample size: 200.
- Random seed: 20260605.
- D dates: `2026-02-11`, `2026-03-11`.
- Stage families: `CROSSOVER,MOMENTUM_SETUP,DIVERGENCE`.
- Forward horizons: D+1, D+2, D+5, D+10, D+20.

Generated artifacts:

- `validation/runs/v3_nontech_master_watch_probe_20260605_20260211_summary.md`
- `validation/runs/v3_nontech_master_watch_probe_20260605_20260311_summary.md`
- `validation/runs/v3_nontech_master_watch_probe_20260605_multi_date_summary.md`

## Run Result

| D date | Attempted | Processed | Skipped | Candidates | Candidate density |
|---|---:|---:|---:|---:|---:|
| 2026-02-11 | 200 | 186 | 14 | 150 | 0.8065 |
| 2026-03-11 | 200 | 186 | 14 | 126 | 0.6774 |

## WATCH / BELOW_EMA200 D+20

| D date | Segment | Candidates | Hit Rate | Average Return |
|---|---|---:|---:|---:|
| 2026-02-11 | SELECTED + NO_RISK_TAG | 87 | 27.59% | -5.69% |
| 2026-02-11 | WATCH + LOW_LIQUIDITY | 42 | 19.05% | -8.87% |
| 2026-02-11 | WATCH + BELOW_EMA200 | 20 | 25.00% | -8.29% |
| 2026-02-11 | WATCH + NO_RISK_TAG | 11 | 18.18% | -10.51% |
| 2026-03-11 | SELECTED + NO_RISK_TAG | 62 | 45.16% | -3.31% |
| 2026-03-11 | WATCH + LOW_LIQUIDITY | 33 | 45.45% | -2.65% |
| 2026-03-11 | WATCH + NO_RISK_TAG | 23 | 60.87% | 1.56% |
| 2026-03-11 | WATCH + BELOW_EMA200 | 17 | 41.18% | -9.12% |

## WATCH + BELOW_EMA200 By Family

| D date | Family / State | Candidates | Hit Rate | Average Return |
|---|---|---:|---:|---:|
| 2026-02-11 | MOMENTUM_SETUP / BULL_PULLBACK_REENTRY | 8 | 25.00% | -5.08% |
| 2026-02-11 | DIVERGENCE / HIDDEN_BULLISH_DIVERGENCE | 6 | 33.33% | -13.98% |
| 2026-02-11 | DIVERGENCE / BULLISH_DIVERGENCE | 4 | 25.00% | -5.92% |
| 2026-02-11 | CROSSOVER / PRE_BULL_CROSSOVER | 2 | 0.00% | -8.75% |
| 2026-03-11 | DIVERGENCE / BULLISH_DIVERGENCE | 8 | 50.00% | -5.88% |
| 2026-03-11 | MOMENTUM_SETUP / BULL_PULLBACK_REENTRY | 6 | 33.33% | -16.79% |
| 2026-03-11 | DIVERGENCE / HIDDEN_BULLISH_DIVERGENCE | 3 | 33.33% | -2.44% |

## Read

The larger non-Technology master-derived sample supports continued caution on `WATCH + BELOW_EMA200`.

It does not justify hiding those signals, but it does support treating bullish continuation/re-entry or bullish Divergence below EMA200 as a higher-risk manual-review segment. The strongest repeated weakness is `MOMENTUM_SETUP / BULL_PULLBACK_REENTRY` below EMA200.

Do not implement a hard rejection rule from this evidence. The next calibration step should test a review-priority downgrade while preserving signal visibility.

## Recommended Rule Experiment

Candidate rule to test, not yet promote:

- If `CandidateClass = WATCH`;
- and route is bullish;
- and `RiskTags` includes `BELOW_EMA200`;
- then preserve the candidate row but assign a clearer low-priority/manual-risk review bucket.

Guardrail:

- Do not apply this to bearish `CROSSOVER` exit/capital-preservation review.
- Do not suppress `WATCH + BELOW_EMA200`; keep it visible for audit and later regime-specific review.

