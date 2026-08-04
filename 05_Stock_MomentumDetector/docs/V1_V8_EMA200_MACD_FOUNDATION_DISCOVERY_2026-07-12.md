# V1-V8 EMA200 and MACD Foundation Discovery

Date: 2026-07-12

Status: Discovery complete and recommendation implemented. EMA200 was retained; MACD was removed during the V3-to-V4 long-term-engine rewrite without a recorded rationale. Mainline V8 now restores EMA200 plus configurable `8/21/5` MACD as the first filter.

## Question

Determine where and how the original first filter stopped requiring EMA200 and MACD, and assess the consequences of restoring that foundation before Setup/Momentum analysis.

## Source Limitation

Git history cannot establish the author's reason for the change. V1, V2, V3, V4, and V5 were all added together in the initial repository commit:

```text
e9b470d Initial Stock Momentum Detector snapshot
Commit date: 2026-06-29 12:25:52 +0530
```

File timestamps and code structure show the implementation sequence:

| Version | File timestamp |
|---|---|
| V1 | 2026-06-26 20:18 |
| V2 | 2026-06-28 23:51 |
| V3 | 2026-06-29 02:04 |
| V4 | 2026-06-29 03:44 |

Because the versions were not committed separately, any rationale beyond the code is an inference and is labeled as such below.

## V1-V3 Original Architecture

V1-V3 implemented an explicit two-phase pipeline.

### Phase 1: strict elimination foundation

```text
Close > EMA_200
AND +DI > -DI
AND MACD_Line > Signal_Line
AND MACD_Line > 0
```

The code named these conditions:

```text
macro_trend
directional_dominance
trajectory
```

Failure immediately wrote a disqualified audit row and executed `continue`. Phase 2 scoring did not run for that ticker.

### Phase 2: setup/momentum scoring

Only Phase-1 survivors received the RSI, ADX, OBV, structural, and Aroon scoring appropriate to the version.

Important implementation nuance: V1-V3 calculated the indicator frame before Phase 1 because EMA200, DMI, and MACD were needed for the gate. The staged design skipped downstream scoring and candidate consideration; it did not avoid the historical price download or all indicator calculations.

## Exact Discontinuation Point

The discontinuation occurred in `Momentum_Detector_V4.py`.

V4 was explicitly retitled:

```text
MOMENTUM DETECTOR V4 - LONG-TERM ENGINE
```

The following V3 elements were removed:

- MACD calculation.
- `MACD_Line` and `Signal_Line` output fields.
- `check_phase1_gates()`.
- MACD positive/bullish trajectory gate.
- DMI `+DI > -DI` as a hard first-stage gate.
- RSI and Aroon from the primary V4 model.

They were replaced by `check_long_term_gates()`:

```text
Close > EMA_200
EMA_50 > EMA_200
EMA_200 slope over 50 sessions > 0
126-day return > 0
ATR percent <= 15
```

V4 then scored:

- EMA50/EMA150/EMA200 trend structure.
- 63/126/252-day returns.
- proximity to the 52-week high.
- volume and OBV confirmation.
- ADX.
- ATR risk quality.

This was a wholesale model redesign, not an isolated deletion of MACD.

## EMA200 Was Not Discontinued

EMA200 remained foundational throughout the lineage.

| Version | EMA200 treatment |
|---|---|
| V1-V3 | Hard gate: `Close > EMA200`. |
| V4 | Stronger hard structure: Close above EMA200, EMA50 above EMA200, and rising EMA200. |
| V5-V8 | Close at/below EMA200 creates an `Avoid` reason and commercial score cap; EMA stack/slope also contribute to trend score. |

The actual lineage break concerns MACD, not EMA200.

## What Replaced MACD After V4

V4 replaced the short/medium trajectory test with slower structural evidence. V5-V8 continued that direction and added:

- bullish EMA stack.
- weekly 30-week trend.
- 126-day performance relative to SPY.
- breakout/high proximity.
- accumulation/distribution behavior.
- volatility, extension, volume, and close-location gates.

By V5-V8 the engine could classify a structurally strong stock without an explicit current MACD trajectory confirmation.

## Why MACD May Have Been Removed

There is no documented reason. The following are plausible engineering inferences from the V4 code:

1. V4 changed the objective from a shorter trajectory scanner to a long-term engine.
2. EMA stack, EMA200 slope, multi-horizon returns, and 52-week-high proximity may have been intended to replace MACD with slower structural evidence.
3. MACD overlaps mathematically with EMA-derived trend fields, so the author may have viewed it as redundant.
4. A hard MACD gate can whipsaw during normal pullbacks and can exclude strong trends while the MACD line temporarily falls below its signal.
5. The fixed `12/26/9` definition may have appeared too slow or regime-sensitive for the revised objective.

These points explain why a designer might remove MACD, but the repository contains no validation proving that removal improved the engine.

## Impact of Excluding MACD From the Foundation

### Benefits

- Higher recall: structurally strong trends are not rejected during a MACD reset.
- Less dependence on one parameter triple.
- Reduced duplication among EMA-based signals.
- Better accommodation of steady trends that lack a fresh MACD crossover.
- Fewer hard discontinuities caused by small changes around the signal line.

### Costs

- Loss of the original explicit price-trajectory confirmation.
- Setup analysis can proceed when long-term structure is valid but current acceleration is not.
- Slower weekly and relative-strength gates can recognize an emerging move late.
- The engine no longer has a clearly auditable Foundation -> Setup -> Momentum pipeline.
- V1-V3 design intent and later V4-V8 behavior are not directly traceable.
- False-negative and confirmation-lag diagnosis becomes harder because no MACD state is recorded.

PANW demonstrates the timing issue. V8 rejected PANW on April 30 and first marked it Active on June 9. A combined EMA200+MACD foundation identified valid earlier episodes, including an `8/21/5` episode on May 7 that preceded V8 Active by 33 calendar days and was followed by strong D+1/D+5/D+8 movement.

## Impact of Restoring MACD as a Hard First Filter

### Benefits

- Restores the original foundational contract.
- Separates macro trend from current trajectory before expensive or interpretive setup analysis.
- Provides a direct, configurable early-detection control.
- Makes rejection reasons more explicit and auditable.
- Reduces candidates that have structure but no current positive trajectory.

### Risks

- A Boolean MACD gate can reject valid trends during shallow resets.
- Faster settings create more episodes and potentially more false positives.
- Slower settings improve persistence but may recreate the current confirmation lag.
- `Close > EMA200` and `MACD_Line > 0` are both lagging conditions; together they cannot identify the earliest reversal below the long-term average.
- Parameter selection from the same data used to judge outcomes would overfit the engine.
- Computational savings are modest because price history and foundation indicators must still be calculated before the gate.

## Combined EMA200+MACD Research Result

The corrected research rule matches the intended foundation:

```text
Close > EMA200
AND MACD_Line > MACD_Signal_Line
AND MACD_Line > 0
AND prior session was not in that combined state
```

Canonical run:

```text
backtests/V8_MACD_Research/runs/V8MACD_20260712T072722Z_1f1ac52
```

Across 122 independent foundation episodes:

| Setting | Episodes | D+1 pass | D+5 pass | D+8 pass |
|---|---:|---:|---:|---:|
| `8/21/5` | 27 | 62.96% | 62.96% | 62.96% |
| `8/21/8` | 24 | 62.50% | 66.67% | 66.67% |
| `13/34/8` | 18 | 61.11% | 77.78% | 72.22% |
| `5/13/5` | 34 | 58.82% | 52.94% | 64.71% |
| `12/26/9` | 19 | 52.63% | 73.68% | 73.68% |

This supports configurability. Faster `8/21/5` improved D+1 direction over the standard setting, while standard and `13/34/8` provided stronger longer persistence. No setting dominated every requirement.

## Discovery Conclusion

1. EMA200 was never discontinued.
2. MACD was removed at V4 as part of an undocumented long-term structural rewrite.
3. The repository contains no evidence-based justification for permanently excluding MACD from the foundation.
4. There are valid reasons not to use MACD as an immediate hard production gate: whipsaw, redundancy, parameter sensitivity, and false-negative risk.
5. The original staged architecture is credible and should be restored first as an explicit, auditable `Foundation_Status` contract.
6. The exact MACD periods and whether failure means hard rejection or `WAIT_FOUNDATION_RESET` require multi-regime holdout validation.

## Recommended Architecture for Review

```text
Stage 0: Data sufficiency

Stage 1: Foundation
  Close > EMA200
  MACD bullish-positive using configured periods

Stage 2: Setup
  EMA stack/slope
  weekly trend
  relative strength
  breakout proximity
  accumulation/distribution
  liquidity and volatility

Stage 3: Momentum confirmation
  score and confirmed-entry gates
  D+1 directional validation contract

Stage 4: ETF context
  informational only after MOMENTUM_ACTIVE
```

Initial research statuses should distinguish:

```text
FOUNDATION_VALID
FOUNDATION_TREND_VALID_MACD_RESET
FOUNDATION_INVALID_BELOW_EMA200
FOUNDATION_INSUFFICIENT_DATA
```

This preserves the user's foundational requirement while allowing the backtest to measure whether a temporary MACD reset should be a hard rejection or a wait state.

Implementation decision: a MACD reset is a zero-score `MOMENTUM_PRESENT_WAIT_CONFIRMATION` state; below EMA200 and insufficient data are zero-score `REJECT` states. Only `FOUNDATION_VALID` proceeds to Setup/Momentum and ETF processing. The frozen 20-stock/four-date result and independent validation are recorded in `docs/V8_FOUNDATION_VALIDATION_CONCLUSION_2026-07-12.md`.
