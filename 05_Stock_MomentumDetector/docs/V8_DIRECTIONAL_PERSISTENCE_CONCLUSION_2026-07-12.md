# V8 D+1 Direction and D+5/D+8 Persistence Conclusion

Date: 2026-07-12

Status: Execution and independent validation passed. The primary D+1 directional hypothesis was not supported in the selected April sample.

Subsequent alternate-code run replaced XOM with PANW:

```text
docs/V8_ALT_CODES_DIRECTIONAL_CONCLUSION_2026-07-12.md
```

## User-Defined Intent

V8 is intended to identify longer-duration momentum trades, not predict intraday movement.

The amended validation contract is:

```text
Primary direction test:
  D+1 Close > D Close

Required D+1 audit prices:
  D Close
  D+1 Open
  D+1 Close

Persistence references:
  D+5 Close > D Close
  D+8 Close > D Close
```

The D+1 Open-to-Close move is retained as a diagnostic only. It is not the primary pass rule.

Price persistence cannot by itself prove a fundamental business change. It tests whether the market move continued for the requested duration.

## Canonical Run

```text
Run ID: V8DIR_20260711T193832Z_0568444
Run folder: backtests/V8_Directional_Persistence/runs/V8DIR_20260711T193832Z_0568444
Frozen source run: V8FULL_20260711T192053Z_ffe1567_20260712
```

The analysis reused the frozen, checksum-verified Q2 stock and ETF prices. It made no new price or ETF request.

## April Date Selection

The date was selected without inspecting forward returns:

```text
Month: 2026-04
Rule: maximum V8 Active count, then earliest date if tied
Selected date: 2026-04-30
Active signals: 4
```

April 30 had the largest Active population among April dates in the frozen ten-stock universe:

```text
GOOGL COST WMT XOM
```

This date is earlier than the `2026-05-29` ETF holdings report and remains in the same Q2 calendar quarter under the documented quarter-stability assumption.

## Active Signal Results

| Stock | Score | D Close | D+1 Open | D+1 Close | D+1 vs D Close | D+1 result | D+5 vs D Close | D+5 result | D+8 vs D Close | D+8 result |
|---|---:|---:|---:|---:|---:|---|---:|---|---:|---|
| GOOGL | 100 | 384.80 | 381.63 | 385.69 | 0.23% | PASS | 3.43% | PASS | 0.66% | PASS |
| COST | 100 | 1014.53 | 1015.38 | 1011.70 | -0.28% | FAIL | -0.24% | FAIL | 0.72% | PASS |
| WMT | 98 | 131.93 | 131.92 | 131.60 | -0.25% | FAIL | -1.31% | FAIL | -1.20% | FAIL |
| XOM | 89 | 154.33 | 152.61 | 152.75 | -1.02% | FAIL | -5.02% | FAIL | -2.40% | FAIL |

Aggregate Active results:

| Test | Passes | Pass rate | Mean move versus D Close |
|---|---:|---:|---:|
| D+1 direction | 1/4 | 25% | -0.33% |
| D+5 persistence | 1/4 | 25% | -0.79% |
| D+8 persistence | 2/4 | 50% | -0.55% |

Two of four Active stocks closed D+1 above the D+1 Open, but only GOOGL closed above the signal-day Close. This demonstrates why intraday Open-to-Close movement is not an adequate substitute for the primary directional rule.

GOOGL was the only signal that passed D+1, D+5, and D+8. COST recovered above the signal close by D+8. WMT and XOM failed all three directional/persistence checks.

## ETF Reference Results

| Stock | ETF | D+1 vs D Close | D+1 result | D+5 vs D Close | D+5 result | D+8 vs D Close | D+8 result |
|---|---|---:|---|---:|---|---:|---|
| GOOGL | VOX | -0.06% | FAIL | 0.65% | PASS | -1.16% | FAIL |
| COST | VDC | -0.23% | FAIL | -0.95% | FAIL | -0.67% | FAIL |
| WMT | VDC | -0.23% | FAIL | -0.95% | FAIL | -0.67% | FAIL |
| XOM | VDE | -1.21% | FAIL | -6.06% | FAIL | -3.49% | FAIL |

ETF reference pass rates:

```text
D+1: 0/4
D+5: 1/4
D+8: 0/4
```

ETF results remain informational. V8 does not recommend substituting the ETF for the stock and does not modify `Score` from ETF performance.

## Independent Validation

```text
Validation status: PASS
Stocks checked: 10
Metrics independently recomputed: 80
Failures: 0
```

The run package contains exact source snapshots, the configuration, the frozen source-run checksum inventory, outputs, validation results, and its own checksum inventory.

## Conclusion

Engineering conclusion:

```text
PASS
```

The amended D+1/D+5/D+8 calculation and validation pipeline is deterministic and reproducible.

Signal conclusion:

```text
PRIMARY_D1_DIRECTION_NOT_SUPPORTED_IN_SELECTED_SAMPLE
```

The selected April date produced four Active signals, but only one moved in the required direction by the D+1 close. Persistence improved to two of four at D+8, which is still insufficient to demonstrate dependable stupendous momentum.

This result reinforces the previous decision not to activate V8. It does not prove that V8 cannot work in other periods; it shows that the current evidence does not yet support the required D+1 directional behavior.

Final status:

```text
V7 = OPERATIONAL BASELINE
V8 = DEVELOPMENT; D+1 DIRECTIONAL GATE NOT PASSED
```

## Delivered Files

```text
outputs/execution.log
outputs/all_stock_results.csv
outputs/active_signal_results.csv
outputs/active_etf_reference_results.csv
outputs/aggregate_summary.json
validation/validation_summary.json
validation/independently_recomputed_metrics.csv
run_manifest.json
checksums.sha256
```
