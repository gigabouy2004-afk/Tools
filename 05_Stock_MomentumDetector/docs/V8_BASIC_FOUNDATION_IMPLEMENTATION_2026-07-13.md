# V8 Basic Foundation Implementation

Date: 2026-07-13

Status: historical Foundation-only schema and frozen baseline remain valid as audit evidence. The active Basic engine has now advanced to Foundation -> DMI -> V1 composite Health Score under explicit user research approval. See `docs/V8_BASIC_HEALTH_SCORE_IMPLEMENTATION_2026-07-13.md`. Statements below describing a no-Score engine refer to the earlier checkpoint, not current behavior.

## 1. Delivered Scope

The basic engine contains only:

- deterministic daily price handling;
- sufficient-history validation;
- configurable long-term EMA;
- configurable MACD;
- exact Foundation eligibility and non-eligibility substates;
- plain-language reasons;
- raw Foundation values;
- versioned configuration;
- append-only execution logging;
- reproducible historical cutoff support;
- frozen replay and independent validation.

It contains no:

- composite Score;
- SPY or other benchmark;
- ETF processing;
- weekly-trend calculation;
- distribution/accumulation rule;
- breakout or high-proximity rule;
- freshness score;
- ATR/volatility rule;
- volume, close-location or liquidity rule;
- extension rule;
- intraday or extended-hours rule;
- analyst, EPS or event message.

## 2. Implementation Files

```text
Momentum_Detector_V8_Basic.py
config/V8_Basic_Foundation_Config.json
tests/test_v8_basic_foundation.py
Backtest_Momentum_Detector_V8_Basic_Foundation.py
Validate_Momentum_Detector_V8_Basic_Foundation.py
```

The existing `Momentum_Detector_V8.py` is preserved unchanged as the legacy comparator.

## 3. Current Foundation Configuration

```text
EMA period: 200
MACD fast/slow/signal: 8/21/5
Minimum history: 300 trading bars
Price data: unadjusted OHLC
Decision scope: FOUNDATION_ONLY_NO_SCORE
```

The periods can be overridden from the command line. Overrides are written into the effective Configuration ID so a non-default result cannot be mistaken for the baseline.

## 4. Eligibility Rule

A row is Foundation eligible only when:

```text
Close > EMA200
AND MACD Line > MACD Signal Line
AND MACD Line > 0
```

The rule awards no points. The result is a Boolean eligibility value plus an exact state and reason.

## 5. Published States

| State | Exact meaning | Eligible now? |
|---|---|---:|
| `FOUNDATION_ELIGIBLE_BULLISH_POSITIVE_MACD` | Close above EMA; MACD line above signal and zero | Yes |
| `FOUNDATION_NOT_ELIGIBLE_BELOW_OR_AT_EMA` | Close at or below EMA | No |
| `FOUNDATION_NOT_ELIGIBLE_MACD_POSITIVE_PULLBACK` | Close above EMA; MACD positive but at/below signal | No |
| `FOUNDATION_NOT_ELIGIBLE_MACD_EARLY_RECOVERY_BELOW_ZERO` | Close above EMA; MACD above signal but at/below zero | No |
| `FOUNDATION_NOT_ELIGIBLE_MACD_NEGATIVE_WEAKENING` | Close above EMA; MACD at/below both signal and zero | No |
| `FOUNDATION_INSUFFICIENT_DATA` | Fewer than the configured history bars or unavailable indicator values | No |

“Not eligible” means the present Foundation rule did not qualify the row. It is not a forecast that price will decline.

The early-recovery state remains non-eligible because the three positive historical examples are insufficient to approve a new rule. It is now visible for future research rather than hidden inside an ambiguous reset label.

## 6. Basic Output Contract

Every successful evaluation publishes:

```text
Engine version and configuration ID
Ticker
Evaluation and as-of dates
First price date and bars used
Minimum required history
Data status
Foundation eligible Boolean
Exact Foundation state
Plain-language reason
Close
EMA period and value
MACD periods
MACD line, signal and histogram
Price-adjustment policy
```

The schema intentionally has no `Score` field.

## 7. Functional Tests

Nine focused tests pass:

1. EMA and MACD formulas match independent pandas EWM calculations.
2. Every eligibility/substate boundary is explicit, including equality at zero, signal and EMA.
3. Insufficient history cannot fabricate eligibility.
4. Changing future prices cannot change a prior as-of result.
5. Basic output contains no Score, benchmark, ETF, weekly or ATR fields.
6. Invalid MACD periods are rejected.
7. Insufficient minimum-history configuration is rejected.
8. CLI overrides are visible in Configuration ID.
9. Duplicate dates are rejected and old append-only log schemas are preserved/rotated.

All active V8 tests also pass after adding this engine.

## 8. Frozen Foundation-Only Replay

Canonical run:

```text
backtests/V8_Basic_Foundation/runs/V8BASICFOUND_20260712T204114Z_36c2e24
```

Scope:

```text
20 technology stocks
4 predeclared 2026Q2 dates
80 stock/date rows
D+1, D+5 and D+8 from next-session open
Frozen price inputs reused from the validated experiment
```

State counts:

| State | Rows |
|---|---:|
| Eligible bullish-positive MACD | 25 |
| Below/at EMA | 27 |
| Positive MACD pullback | 22 |
| Early recovery below zero | 3 |
| Negative weakening | 3 |

Directional results:

| State | D+1 positive / mean | D+5 positive / mean | D+8 positive / mean |
|---|---:|---:|---:|
| Eligible | 19/25, +2.21% | 23/25, +8.16% | 18/25, +10.24% |
| Below/at EMA | 15/27, -0.99% | 16/27, +2.48% | 13/27, +2.27% |
| Positive pullback | 12/22, -0.01% | 19/22, +5.07% | 16/22, +6.76% |
| Early recovery below zero | 3/3, +1.71% | 3/3, +8.05% | 3/3, +8.85% |
| Negative weakening | 0/3, -2.10% | 2/3, +0.99% | 2/3, +0.38% |

This replay reproduces the previously observed 25 Foundation-qualified cases without invoking any later V8 indicator or decision rule.

## 9. Independent Validation

Validation result:

```text
20 unique stocks: PASS
4 unique dates: PASS
80 complete rows: PASS
Foundation-only schema: PASS
No Score output: PASS
Independent EMA/MACD/state recomputation: PASS
Independent D+1/D+5/D+8 recomputation: PASS
Frozen checksums: PASS
Failures: 0
```

The checksum manifest excludes only the validation summary and validator console because those files are regenerated when validation is rerun. Inputs, source snapshots, results and independently recomputed rows are checksummed.

## 10. Commands

Evaluate current daily data:

```powershell
python Momentum_Detector_V8_Basic.py NVDA AAPL MSFT
```

Evaluate a historical cutoff:

```powershell
python Momentum_Detector_V8_Basic.py NVDA --as-of 2026-05-07
```

Use alternate MACD periods:

```powershell
python Momentum_Detector_V8_Basic.py NVDA --macd-fast 12 --macd-slow 26 --macd-signal 9
```

Run the frozen replay:

```powershell
python Backtest_Momentum_Detector_V8_Basic_Foundation.py
```

Validate the canonical run:

```powershell
python Validate_Momentum_Detector_V8_Basic_Foundation.py backtests/V8_Basic_Foundation/runs/V8BASICFOUND_20260712T204114Z_36c2e24
```

## 11. Approval Boundary and Next Step

Implemented and validated:

```text
Basic Foundation engine mechanics
Raw EMA/MACD output
Eligibility and explicit substates
No-look-ahead evaluation
Frozen replay and independent validation
```

Not decided by this implementation:

```text
Whether 8/21/5 is the final universal MACD setting
Whether early recovery can become a future research candidate
Whether positive pullback should support a re-entry workflow
Any post-Foundation indicator, score or gate
V8 operational promotion
```

The next action is user review of the basic Foundation implementation. Only after that review should the first post-Foundation indicator be selected and its research specification frozen.
