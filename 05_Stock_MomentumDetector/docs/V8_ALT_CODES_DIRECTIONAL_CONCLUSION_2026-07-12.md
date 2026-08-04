# V8 Alternate-Codes Directional Conclusion

Date: 2026-07-12

Status: Alternate 10-stock execution and validation complete. PANW successfully replaced XOM and demonstrated strong multi-day movement, but the common-date D+1 Active-signal gate still did not pass.

## Alternate Universe

XOM was removed as requested and replaced with PANW:

```text
NVDA AAPL MSFT TSLA AMZN META GOOGL COST WMT PANW
```

PANW satisfied the existing ETF requirement:

```text
ETF: HACK
Direct holding weight: 9.65%
Independent top-ten rank: 1
Holdings as-of: 2026-06-30
Quarter: 2026Q2
```

The mapping therefore remained inside the same Q2 calendar-quarter assumption used by the earlier test.

## Canonical Runs

Alternate 10-stock Q2 replay:

```text
backtests/V8_Comprehensive/runs/V8FULL_20260711T194644Z_3ed85d1_20260713
```

Alternate D+1/D+5/D+8 run:

```text
backtests/V8_Directional_Persistence/runs/V8DIR_20260711T195008Z_3ed85d1
```

## April Common-Date Result

The unchanged date-selection rule again chose April 30, 2026 because it had the largest April Active count without inspecting forward outcomes.

Active signals after replacing XOM:

```text
GOOGL COST WMT
```

| Stock | Score | D+1 vs D Close | D+1 | D+5 vs D Close | D+5 | D+8 vs D Close | D+8 |
|---|---:|---:|---|---:|---|---:|---|
| GOOGL | 100 | 0.23% | PASS | 3.43% | PASS | 0.66% | PASS |
| COST | 100 | -0.28% | FAIL | -0.24% | FAIL | 0.72% | PASS |
| WMT | 98 | -0.25% | FAIL | -1.31% | FAIL | -1.20% | FAIL |

Aggregate Active results:

| Test | Pass rate | Mean move versus D Close |
|---|---:|---:|
| D+1 direction | 1/3 = 33.3% | -0.10% |
| D+5 persistence | 1/3 = 33.3% | 0.62% |
| D+8 persistence | 2/3 = 66.7% | 0.06% |

Removing XOM improved the mean D+5 and D+8 results, but the primary D+1 gate still failed because only one of three Active signals closed above the signal-day Close.

## PANW Timing Finding

On the common April 30 date, PANW was:

```text
Final_Decision: REJECT
Score: 16
Reason: weekly downtrend | not outperforming benchmark SPY
```

Its subsequent movement was:

| PANW test from April 30 | Move versus D Close | Result |
|---|---:|---|
| D+1 | 0.98% | PASS |
| D+5 | 9.60% | PASS |
| D+8 | 20.23% | PASS |

PANW was selected as the alternate code before these outcomes were examined. This is therefore a legitimate false-negative/timing observation within the alternate test, not a ticker selected because of its later gain.

V8's first Q2 PANW Active signal occurred on June 9, 2026:

```text
Score: 100
Reason: all confirmation gates passed
```

Performance after the first Active signal:

| PANW first-Active test | Move versus D Close | Result |
|---|---:|---|
| D+1 | 1.04% | PASS |
| D+5 | 7.44% | PASS |
| D+8 | 9.93% | PASS |

The first-Active PANW signal passed all three requested horizons. The important issue is timing: V8 detected the trend after the large early-May move rather than at its April 30 start.

## Validation

Alternate comprehensive run:

```text
Stocks: 10
Daily rows checked: 620
Random forward returns independently recomputed: 30
Score-invariance failures: 0
Validation failures: 0
```

Alternate directional run:

```text
Stocks checked: 10
Directional/persistence metrics independently recomputed: 88
Validation failures: 0
```

All 10 automated V8 backtest and ETF tests passed.

## Conclusion

Replacing XOM with PANW was appropriate and produced a more useful momentum case.

The results show two different findings:

1. The common-date Active cohort still failed the primary D+1 gate at `1/3`.
2. PANW's eventual Active signal was excellent across D+1, D+5, and D+8, but the engine recognized it substantially later than the April breakout phase.

This points toward a possible confirmation-lag problem in the weekly-trend and benchmark-relative-strength gates. It does not authorize changing those gates without a larger, predeclared false-negative study.

Final status:

```text
V7 = OPERATIONAL BASELINE
V8 = DEVELOPMENT; PANW CASE PASSED AFTER ACTIVATION, BUT COMMON D+1 GATE NOT PASSED
```

## Delivered Evidence

```text
Alternate comprehensive execution log:
backtests/V8_Comprehensive/runs/V8FULL_20260711T194644Z_3ed85d1_20260713/outputs/execution_log.csv

Alternate fixed-date results:
backtests/V8_Directional_Persistence/runs/V8DIR_20260711T195008Z_3ed85d1/outputs/all_stock_results.csv

PANW first-Active result:
backtests/V8_Directional_Persistence/runs/V8DIR_20260711T195008Z_3ed85d1/outputs/focus_ticker_first_active_result.csv
```
