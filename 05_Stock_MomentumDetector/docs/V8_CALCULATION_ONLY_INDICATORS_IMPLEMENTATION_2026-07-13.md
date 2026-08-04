# V8 Calculation-Only Indicators Implementation

Date: 2026-07-13

Status: historical calculation-only milestone, retained for audit. The EMA200/MACD Foundation is evaluated first and only Foundation-eligible stocks enter the indicator module. A subsequent approved base-layer step gave RSI an inclusive configurable 30-65 continuation gate; see `docs/V8_RSI_BASE_LAYER_IMPLEMENTATION_2026-07-13.md`. ADX, ATR, OBV and Aroon remain calculation-only.

Architectural correction: schema `V8_BASIC_FOUNDATION_2` calculated the indicator set before Foundation classification. That execution order was incorrect even though the calculations had no decision authority. Schema `V8_BASIC_FOUNDATION_3` supersedes it and enforces the Foundation boundary in code, tests, output status and independent validation.

## 1. User-Authorized Scope

Add calculations for existing basic stock indicators while preserving the already validated Foundation result.

Mandatory execution order:

```text
1. Calculate EMA200 and MACD only.
2. Determine Foundation eligibility.
3. If Foundation_Eligible = False: stop; do not call the indicator module.
4. If Foundation_Eligible = True: calculate RSI/ADX/ATR/OBV/Aroon.
```

This phase is calculation only. It does not decide:

- desirable indicator values;
- overbought/oversold bands;
- trend-strength thresholds;
- scores or weights;
- WAIT conditions;
- hard gates;
- Active/Reject behaviour.

Those decisions require separate backtests and explicit approval for each indicator.

## 2. OTR Clarification

No indicator named `OTR` exists in Momentum Detector V1-V7 or its documentation. The historical code consistently used `ATR`, Average True Range.

This implementation therefore provides both:

```text
True_Range = raw one-session true range
ATR = configured moving average of True Range
```

If OTR was intended to mean a different indicator, it remains outside this implementation until its exact formula is supplied.

## 3. Calculation Set

Indicator set ID:

```text
V1_V3_RAW_INDICATORS_1
```

Authority:

```text
CALCULATION_ONLY
```

| Indicator | Default period | Published fields | Historical source |
|---|---:|---|---|
| RSI | 14 | `RSI` | V1-V3 |
| ADX and DMI | 14 | `ADX`, `DMI_Positive`, `DMI_Negative` | V1-V4 |
| True Range | 1 session | `True_Range` | Underlying ATR calculation |
| ATR | 14 | `ATR`, `ATR_Pct` | V1-V7 |
| On-Balance Volume | Cumulative | `OBV` | V1-V4 |
| EMA of OBV | 20 | `OBV_EMA` | V1-V3 |
| Aroon | 14 | `Aroon_Up`, `Aroon_Down` | V3 |

EMA200 and configurable MACD remain the separate Foundation calculations.

## 4. Exact Formula Source

RSI, ADX/DMI, ATR, OBV, OBV EMA and Aroon use the same Python `ta` library definitions used by the original V1-V3 source.

True Range is independently and explicitly calculated as:

```text
maximum of:
  Current High - Current Low
  absolute(Current High - Previous Close)
  absolute(Current Low - Previous Close)
```

ATR percentage is:

```text
ATR / Close * 100
```

No formula applies a threshold or interpretation.

## 5. Configuration

Current defaults:

```text
RSI period: 14
ADX period: 14
ATR period: 14
OBV EMA period: 20
Aroon period: 14
```

Configuration file:

```text
config/V8_Basic_Foundation_Config.json
```

All periods are positive-integer validated and can be overridden through CLI options:

```text
--rsi-period
--adx-period
--atr-period
--obv-ema-period
--aroon-period
```

Every override is embedded into the effective Configuration ID.

## 6. Basic Engine Output Update

Active development engine:

```text
Momentum_Detector_V8_Basic.py
Engine version: V8_BASIC_FOUNDATION_3
```

New fields:

```text
Indicator_Set_ID
Indicator_Authority
Indicator_Module_Status
Indicator_Module_Reason
RSI_Period
RSI
ADX_Period
ADX
DMI_Positive
DMI_Negative
True_Range
ATR_Period
ATR
ATR_Pct
OBV
OBV_EMA_Period
OBV_EMA
Aroon_Period
Aroon_Up
Aroon_Down
```

Still absent:

```text
Score
Benchmark_Ticker
ETF_Ticker
Weekly_Trend
Any indicator score
Any indicator gate
```

`Indicator_Module_Status` is auditable:

```text
EXECUTED_FOUNDATION_ELIGIBLE
NOT_RUN_FOUNDATION_INELIGIBLE
```

For an ineligible stock, all post-Foundation indicator value fields are blank.

## 7. Functional Tests

The basic-engine test module contains 15 focused tests. The complete repository suite contains 37 tests.

Calculation coverage:

- RSI equals the original `ta` formula.
- ADX, +DI and −DI equal the original `ta` formulas.
- ATR and ATR% equal the original `ta` formulas.
- OBV and OBV EMA equal the original `ta` formulas.
- Aroon Up/Down equal the original `ta` formulas.
- raw True Range equals an independent three-component calculation.
- custom indicator periods are applied and recorded.
- all fields preserve no-look-ahead historical evaluation.
- the indicator function rejects calls without confirmed Foundation eligibility;
- ineligible stocks never call the indicator function;
- eligible stocks call the indicator function only after Foundation classification;
- ineligible output rows contain no post-Foundation indicator values.

Existing Foundation coverage remains:

- EMA/MACD formula verification;
- explicit state boundaries;
- insufficient history;
- duplicate-date rejection;
- no Score/benchmark/ETF output;
- append-only log schema rotation.

## 8. Frozen Calculation Validation

Canonical run:

```text
backtests/V8_Basic_Foundation/runs/V8BASICFOUND_20260712T211805Z_7b3a3a0
```

Scope:

```text
20 technology stocks
4 predeclared dates
80 stock/date observations
Frozen price inputs
```

Independent validation:

```text
Complete 20 x 4 grid: PASS
Foundation-only decision schema: PASS
No Score output: PASS
Calculation-only authority: PASS
Foundation-first execution gate: PASS
EMA/MACD/Foundation recomputation: PASS
RSI recomputation for 25 eligible rows: PASS
ADX/+DI/-DI recomputation for 25 eligible rows: PASS
True Range/ATR/ATR% recomputation for 25 eligible rows: PASS
OBV/OBV EMA recomputation for 25 eligible rows: PASS
Aroon recomputation for 25 eligible rows: PASS
Indicator module executions: 25 eligible rows only
Indicator module skipped: all 55 ineligible rows
Ineligible rows containing indicator values: 0
D+1/D+5/D+8 recomputation: PASS
Checksums: PASS
Failures: 0
```

## 9. Foundation Regression

The calculation layer was compared row-by-row with the previously committed Foundation-only baseline.

Compared fields:

```text
Foundation eligible Boolean
Foundation state
Close
EMA value
MACD line
MACD signal
MACD histogram
```

Result:

```text
Rows compared: 80
Rows changed: 0
Foundation regression failures: 0
```

Therefore, adding raw calculations did not alter Foundation eligibility or its historical performance result.

## 10. Calculation Range Sanity Check

Across the 25 Foundation-eligible observations for which the indicator module executed:

| Field | Minimum | Mean | Maximum |
|---|---:|---:|---:|
| RSI | 57.85 | 69.12 | 87.40 |
| ADX | 13.96 | 25.12 | 50.91 |
| +DI | 29.07 | 38.42 | 59.70 |
| -DI | 6.75 | 16.82 | 25.35 |
| ATR% | 2.31% | 4.31% | 5.56% |
| Aroon Up | 85.71 | 98.86 | 100.00 |
| Aroon Down | 0.00 | 28.86 | 64.29 |

These ranges are a calculation sanity check only. They are not proposed bands and do not authorize scoring or gating.

OBV is cumulative and depends on the starting history and volume scale, so its absolute value should not be compared directly across stocks without a separately approved normalization method.

## 11. Commands

Current calculation:

```powershell
python Momentum_Detector_V8_Basic.py NVDA AAPL MSFT
```

Historical calculation:

```powershell
python Momentum_Detector_V8_Basic.py NVDA --as-of 2026-05-07
```

Alternate calculation periods:

```powershell
python Momentum_Detector_V8_Basic.py NVDA --rsi-period 10 --adx-period 12 --atr-period 16 --obv-ema-period 30 --aroon-period 20
```

Validate frozen calculations:

```powershell
python Validate_Momentum_Detector_V8_Basic_Foundation.py backtests/V8_Basic_Foundation/runs/V8BASICFOUND_20260712T211805Z_7b3a3a0
```

## 12. Approval Boundary and Next Step

Approved by this milestone:

```text
The calculations are correctly implemented and auditable.
They do not alter Foundation eligibility.
They have no decision authority.
They execute only after Foundation eligibility is confirmed.
```

Not approved:

```text
Any RSI value or band
Any ADX/+DI/-DI interpretation
Any ATR or ATR% band
Any OBV comparison/crossover rule
Any Aroon interpretation
Any points, weight, WAIT condition or rejection gate
```

The next step is to select one indicator for isolated historical analysis. That indicator's values and candidate rules must be frozen and backtested before any score or gate is proposed for main V8.
