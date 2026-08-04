# V8 Configurable MACD Research Conclusion

Date: 2026-07-12

Status: Historical research conclusion retained. After this comparison, the user explicitly approved `8/21/5` as the configurable V8 Foundation default. Enforcement and follow-on validation are documented in `docs/V8_FOUNDATION_VALIDATION_CONCLUSION_2026-07-12.md`.

## Baseline Finding

V8 did not contain MACD before this work. MACD existed only in V1-V3, where the standard `12/26/9` definition participated in a trajectory gate.

V8 now calculates configurable MACD fields with production defaults:

```text
Fast: 12
Slow: 26
Signal: 9
```

CLI controls:

```text
--macd-fast
--macd-slow
--macd-signal
```

Changing these controls changes the published MACD fields only. It does not yet change `Score`, component scores, `Final_Decision`, ETF triggering, or ranking.

The proposed `8/21/5` triple is a faster Fibonacci-based setting. The periods are numerically shorter than `12/26/9`, so “faster” is more precise than “higher.”

## Research Rule

To compare settings without inventing score weights, the historical V1-V3 macro-trend and trajectory concepts were converted into independent foundation episodes:

```text
Close > EMA200
AND MACD_Line > MACD_Signal_Line
AND MACD_Line > 0
AND prior session was not in that combined state
```

Primary outcome:

```text
D+1 Close > D Close
```

Persistence references:

```text
D+5 Close > D Close
D+8 Close > D Close
```

## Canonical Run

```text
Run ID: V8MACD_20260712T072722Z_1f1ac52
Run folder: backtests/V8_MACD_Research/runs/V8MACD_20260712T072722Z_1f1ac52
Frozen prices: V8FULL_20260711T194644Z_3ed85d1_20260713
Quarter: 2026Q2
Stocks: 10
Variants: 5
Combined EMA200+MACD foundation episodes: 122
```

Tested universe:

```text
NVDA AAPL MSFT TSLA AMZN META GOOGL COST WMT PANW
```

## Variant Results

| Rank | Setting | Episodes | Tickers | D+1 pass | Mean D+1 | D+5 pass | Mean D+5 | D+8 pass | Mean D+8 |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | Fibonacci fast `8/21/5` | 27 | 10 | 62.96% | 0.93% | 62.96% | 2.10% | 62.96% | 1.27% |
| 2 | Fibonacci balanced `8/21/8` | 24 | 10 | 62.50% | 0.82% | 66.67% | 1.89% | 66.67% | 1.32% |
| 3 | Fibonacci medium `13/34/8` | 18 | 10 | 61.11% | 0.83% | 77.78% | 1.94% | 72.22% | 1.00% |
| 4 | Fibonacci short `5/13/5` | 34 | 10 | 58.82% | 0.86% | 52.94% | 1.99% | 64.71% | 1.69% |
| 5 | Standard `12/26/9` | 19 | 10 | 52.63% | 0.40% | 73.68% | 2.63% | 73.68% | 1.99% |

The descriptive rank prioritizes D+1 pass rate, then D+5, D+8, and sample size. It is not a production ranking.

## Interpretation

### 8/21/5 versus 12/26/9

`8/21/5` produced:

- 27 episodes versus 19.
- D+1 pass rate `62.96%` versus `52.63%`.
- Mean D+1 move `0.93%` versus `0.40%`.
- D+5 pass rate `62.96%` versus `73.68%`.
- D+8 pass rate `62.96%` versus `73.68%`.

The proposed Fibonacci setting therefore improved early detection and immediate direction in this sample, but its D+5 and D+8 persistence rates were lower than the standard setting.

### Other Fibonacci settings

- `5/13/5` had the largest episode count but the lowest Fibonacci D+1 and D+5 pass rates.
- `8/21/8` was the most balanced fast setting across D+1, D+5, and D+8.
- `13/34/8` had the strongest D+5 pass rate, consistent with slower confirmation and better persistence.
- Standard `12/26/9` had the strongest D+8 persistence and tied `13/34/8` closely at D+5.

There is no single setting that dominates every horizon.

## PANW Early-Detection Case

On April 30, the combined `Close > EMA200` and `8/21/5` bullish state identified:

```text
GOOGL COST WMT PANW
```

This is the original V8 Active cohort plus PANW, which V8 rejected because of weekly downtrend and benchmark-relative weakness.

For PANW, the combined foundation blocked the earlier below-EMA200 MACD signals. `8/21/5` began a later foundation episode on May 7:

| Horizon | PANW move | Result |
|---|---:|---|
| D+1 | 5.78% | PASS |
| D+5 | 21.21% | PASS |
| D+8 | 22.18% | PASS |

That episode occurred 33 calendar days before PANW's first V8 Active signal on June 9.

This illustrates the foundation tradeoff: EMA200 prevents the earliest reversal call, while the faster MACD can still re-open Setup analysis materially before the full V8 confirmation stack.

## Validation

```text
Episode rows checked: 122
Metrics independently recomputed: 1,586
Validation failures: 0
Automated tests: 15 passed
No-look-ahead MACD test: passed
Production Score changes: none
```

## Conclusion

The hypothesis is directionally supported:

```text
8/21/5 detected more early bullish episodes and improved D+1 performance versus 12/26/9.
```

It is not yet proven as the required production setting:

```text
One quarter, ten stocks, and five compared variants are vulnerable to selection and regime bias.
```

Current evidence suggests two candidates for the next frozen study:

1. `8/21/5` when early detection and D+1 direction are primary.
2. `8/21/8` when early detection and D+5 persistence need better balance.

`5/13/5` remains an exploratory upper-speed bound because its higher event frequency may increase false positives. `13/34/8` remains the slower persistence comparator.

This recommendation was superseded for the V8 development line by explicit user approval to restore the first filter immediately. The multi-regime and untouched-holdout work remains required before operational signoff.

Final status:

```text
V7 = OPERATIONAL BASELINE
V8 = DEVELOPMENT
MACD = CONFIGURABLE; 8/21/5 ENFORCED AS A FOUNDATION GATE IN THE V8 DEVELOPMENT LINE
```

## Delivered Evidence

```text
outputs/macd_episode_results.csv
outputs/same_date_comparison.csv
outputs/variant_summary.csv
outputs/aggregate_summary.json
validation/independently_recomputed_metrics.csv
validation/validation_summary.json
run_manifest.json
checksums.sha256
```
