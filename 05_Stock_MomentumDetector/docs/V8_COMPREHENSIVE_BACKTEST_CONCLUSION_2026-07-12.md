# V8 Comprehensive 10-Stock Same-Quarter Backtest Conclusion

Date: 2026-07-12

Status: Historical 10-stock conclusion retained. A later 20-stock/four-date enforced-Foundation run passed with stronger D+1 evidence; see `docs/V8_FOUNDATION_VALIDATION_CONCLUSION_2026-07-12.md`. V7 remains the operational baseline pending joint review and broader validation.

Subsequent user-defined directional test:

```text
docs/V8_DIRECTIONAL_PERSISTENCE_CONCLUSION_2026-07-12.md
```

The later test uses D+1 Close above D Close as the primary gate and D+5/D+8 as persistence references. It also did not support activation.

## Canonical Run

```text
Run ID: V8FULL_20260711T192053Z_ffe1567_20260712
Run folder: backtests/V8_Comprehensive/runs/V8FULL_20260711T192053Z_ffe1567_20260712
Test quarter: 2026Q2
Random seed: 20260712
Stocks: 10
Daily stock-date replays: 620
Random test dates: 10, one per stock
Forward horizons: 5, 10, and 21 trading sessions
```

The run used exact source snapshots and frozen downloaded inputs. Its 42 non-checksum artifacts are covered by `checksums.sha256`.

## Scope and Quarter Rule

Tested stocks:

```text
NVDA AAPL MSFT TSLA AMZN META GOOGL COST WMT XOM
```

All accepted ETF holdings validations reported an as-of date of `2026-05-29`, inside calendar quarter `2026Q2`. Every random stock date and every 5/10/21-session exit also fell inside `2026Q2`.

The ETF relationship is labeled:

```text
SAME_CALENDAR_QUARTER_STABILITY_ASSUMPTION
```

This implements the requested assumption that ETF portfolios normally remain stable during a quarter. It is not strict signal-date point-in-time proof because several random stock dates precede the May 29 holdings report. No claim is made that TradingView supplied historical holdings for each signal date.

## Replay Contract

Historical momentum replay used:

```text
DAILY_EOD_NO_ARCHIVED_INTRADAY_OR_LIVE_QUOTE
```

Every historical decision was calculated from stock and SPY rows dated on or before the signal date. The runner sliced inputs at each date before calling V8 calculations.

V8's historical hourly timing, live quote, and extended-hours state were unavailable and were not fabricated. Daily pullback timing rules remained active.

Forward returns used the next trading session's Open as entry and the selected horizon's Close as exit.

## Integrity and Validation Result

Independent validator result:

```text
Validation status: PASS
Stocks checked: 10
Random rows checked: 10
Forward returns independently recomputed: 30
Execution rows checked against score contracts: 620
Same-quarter ETF mapping stocks: 10
Failures: 0
```

Additional integrity results:

- ETF production-style reverse requests: 10.
- Separate holdings validation requests: 26.
- Same-quarter verified mappings used: 11.
- Displayed same-quarter mappings passing top-ten validation: 11/11.
- Score-invariance failures: 0/620.
- Random dates were deterministically selected from dates whose 21-session exits remained inside Q2.
- Repeating the independent validator after checksum creation passed.

## Quarter Decision Population

Across 620 daily EOD replays:

| Final decision | Rows |
|---|---:|
| `MOMENTUM_ACTIVE` | 53 |
| `MOMENTUM_PRESENT_WAIT_CONFIRMATION` | 118 |
| `REJECT` | 449 |

These daily rows overlap heavily through time and are not 620 independent observations.

Using the plan's 21-non-Active-session reset rule, the run identified four independent primary Active episodes.

## Random-Date Results

| Stock | Random date | V8 decision | Score | Stock 21D | Stock minus SPY 21D | Same-quarter ETF mapping |
|---|---|---:|---:|---:|---:|---|
| NVDA | 2026-04-17 | `REJECT` | 40 | 11.17% | 6.96% | VGT 16.77% |
| AAPL | 2026-04-30 | `REJECT` | 35 | 9.84% | 4.67% | VGT 15.25% |
| MSFT | 2026-05-07 | `REJECT` | 18 | -1.35% | -1.94% | VGT 9.87%; VOOG 9.28% |
| TSLA | 2026-04-01 | `REJECT` | 20 | 7.31% | -4.17% | VCR 17.67% |
| AMZN | 2026-05-13 | `REJECT` | 35 | -11.37% | -11.11% | VCR 22.14% |
| META | 2026-05-01 | `REJECT` | 18 | -1.70% | -7.18% | VOX 22.12% |
| GOOGL | 2026-05-12 | `MOMENTUM_ACTIVE` | 100 | -7.22% | -7.12% | VOX 14.10% |
| COST | 2026-05-28 | `REJECT` | 35 | -4.04% | -2.07% | VDC 11.81% |
| WMT | 2026-04-01 | `MOMENTUM_ACTIVE` | 100 | 5.15% | -6.33% | VDC 14.46% |
| XOM | 2026-04-29 | `MOMENTUM_PRESENT_WAIT_CONFIRMATION` | 84 | -4.70% | -10.56% | VDE 21.86% |

Aggregate random-date stock outcomes:

| Horizon | Mean return | Median return | Positive rate | Mean excess versus SPY |
|---|---:|---:|---:|---:|
| 5D | -0.12% | -0.58% | 50.0% | -1.99% |
| 10D | 1.51% | 0.62% | 60.0% | -1.57% |
| 21D | 0.31% | -1.52% | 40.0% | -3.89% |

Random dates were selected without reference to V8 decision or future performance. These figures describe the ten-stock sample, not V8 Active-signal effectiveness.

## Independent Active Episodes

| Stock | Episode date | Score | Stock 21D | Stock minus SPY 21D |
|---|---|---:|---:|---:|
| NVDA | 2026-05-14 | 100 | -7.53% | -9.29% |
| AMZN | 2026-05-01 | 99 | -4.57% | -10.05% |
| GOOGL | 2026-04-28 | 100 | 12.25% | 6.11% |
| XOM | 2026-04-30 | 89 | -2.12% | -7.29% |

Aggregate primary Active-episode outcomes:

| Horizon | Mean return | Median return | Positive rate | Mean excess versus SPY |
|---|---:|---:|---:|---:|
| 5D | 1.20% | -1.25% | 50.0% | -0.25% |
| 10D | 0.43% | -0.81% | 50.0% | -2.62% |
| 21D | -0.49% | -3.34% | 25.0% | -5.13% |

Only four independent Active episodes were available. Three lost money over 21 sessions and only GOOGL beat SPY.

The overlapping daily rows were also weak: among the 50 Active rows with a complete 21-session outcome, mean raw return was `-5.75%`, median was `-7.14%`, positive rate was `14.0%`, and mean SPY-adjusted return was `-8.95%`. Because these rows repeat the same trends, they are descriptive and cannot replace the episode result.

## ETF Mapping and Outcome Result

Same-quarter holdings evidence:

| Stock | ETF | Direct weight | Independently validated rank | Holdings as-of |
|---|---|---:|---:|---|
| NVDA | VGT | 16.77% | 1 | 2026-05-29 |
| AAPL | VGT | 15.25% | 2 | 2026-05-29 |
| MSFT | VGT | 9.87% | 3 | 2026-05-29 |
| MSFT | VOOG | 9.28% | 2 | 2026-05-29 |
| TSLA | VCR | 17.67% | 2 | 2026-05-29 |
| AMZN | VCR | 22.14% | 1 | 2026-05-29 |
| META | VOX | 22.12% | 1 | 2026-05-29 |
| GOOGL | VOX | 14.10% | 2 | 2026-05-29 |
| COST | VDC | 11.81% | 2 | 2026-05-29 |
| WMT | VDC | 14.46% | 1 | 2026-05-29 |
| XOM | VDE | 21.86% | 1 | 2026-05-29 |

ETF forward outcomes from the ten random stock dates:

| Horizon | Mappings | Mean ETF return | Median ETF return | Positive rate | Mean ETF excess versus SPY |
|---|---:|---:|---:|---:|---:|
| 5D | 11 | 1.80% | 2.51% | 72.7% | -0.05% |
| 10D | 11 | 3.20% | 2.65% | 72.7% | 0.30% |
| 21D | 11 | 3.92% | 0.80% | 63.6% | 0.05% |

The ETF sample approximately matched SPY over 21 sessions. It does not establish that the ETFs should replace the stocks, and V8 does not make that recommendation.

Eight of the ten random rows were not production-eligible Active signals. Their ETF outcomes test the same-quarter association and data path only; those mappings would not have been requested by the live V8 trigger on those dates.

## Conclusion

Technical result:

```text
PASS
```

The deterministic replay, random selection, quarter containment, ETF lookup, top-ten validation, Score invariance, frozen artifacts, checksums, and independent outcome recomputation all passed.

Momentum evidence result:

```text
INSUFFICIENT AND UNFAVORABLE IN THIS SAMPLE
```

The four independent Active episodes are far below the comprehensive plan's broad evidence target and produced a negative 21-session mean excess return versus SPY. This sample does not justify V8 operational activation.

ETF evidence result:

```text
FUNCTIONAL VALIDATION PASSED; HISTORICAL CLAIM REMAINS ASSUMPTION-LIMITED
```

All 11 same-quarter mappings were independently confirmed in the ETF top ten. The quarter-stability association satisfied the requested test design, but it is not a substitute for archived holdings on each signal date.

Final status:

```text
V7 = OPERATIONAL BASELINE
V8 = DEVELOPMENT; TECHNICAL SAMPLE COMPLETE; BROAD BACKTEST/SIGNOFF NOT PASSED
```

## Follow-On Foundation Result

The original result in this document predates restoration of the EMA200 plus MACD first filter. The approved follow-on run used mainline Foundation enforcement with MACD `8/21/5`:

```text
backtests/V8_Foundation_Validation/runs/V8FOUND_20260712T182945Z_cf0c908
```

It produced 5 Active rows with positive direction `4/5` at D+1, `5/5` at D+5, and `4/5` at D+8. This supersedes the earlier technical sample for current V8 behavior, but it does not erase the earlier result or authorize operational replacement of V7.

## Delivered Evidence

```text
outputs/execution.log
outputs/execution_log.csv
outputs/random_date_results.csv
outputs/random_etf_outcomes.csv
outputs/etf_mapping_validation.csv
outputs/stock_summary.csv
outputs/aggregate_summary.json
validation/validation_summary.json
validation/independently_recomputed_rows.csv
run_manifest.json
checksums.sha256
```
