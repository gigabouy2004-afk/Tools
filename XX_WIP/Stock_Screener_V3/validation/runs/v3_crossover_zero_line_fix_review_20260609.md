# V3 Crossover Zero-Line Fix Review

Date written: 2026-06-09

## Issue

The V3 `CROSSOVER` evaluator was promoting above-zero bullish MACD continuation names into `PRE_BULL_CROSSOVER`.

That violated the V2/V3 intent:

- `PRE_BULL_CROSSOVER` is a seller-to-buyer transition and must occur below the MACD zero line, or at the zero-line recovery boundary.
- Above-zero bullish signal crosses are continuation or pullback-re-entry evidence and belong in `MOMENTUM_SETUP`, not `CROSSOVER`.

## Code Change

Changed `src/stock_screener_v3/evaluators.py` so bullish Crossover routes now require zero-line context:

- `BULL_CROSS` is valid for `PRE_BULL_CROSSOVER` only when MACD or signal is at/below zero.
- `BULLISH_NEAR_TRANSITION` now requires `BELOW_SIGNAL`, improving histogram, near-signal distance, and below-zero MACD/signal context.
- Above-zero fresh bull crosses are emitted as invalid Crossover diagnostics:
  - `CrossoverOpportunityType = BULLISH_ABOVE_ZERO_CONTINUATION`
  - `ReasonCodes = BULL_CROSS_ABOVE_ZERO_LINE_CONTINUATION`
  - `CandidateClass = STATUS_QUO`

## Regression Tests

Added tests in `tests/test_evaluators.py`:

- above-zero bull continuation must not become `PRE_BULL_CROSSOVER`;
- below-zero near bull transition can still become `PRE_BULL_CROSSOVER`.

Full suite result:

```text
python -m unittest discover -s tests -v
67 tests OK
```

## Validation Rerun

Rerun command:

```powershell
python -m stock_screener_v3.cli backtest-pack --workspace-root D:\Tools\Stock_Screener_V3 --universe-file data\samples\00-NYSE_NASDAQ_Common_Stocks_Sector-Technology.csv --d-dates 2026-05-11,2026-06-11 --forward-days 1,2,5 --stage-family CROSSOVER --run-label v3_crossover_zero_line_fix
```

Artifacts:

- `validation/runs/v3_crossover_zero_line_fix_20260511_details.csv`
- `validation/runs/v3_crossover_zero_line_fix_20260511_summary.md`
- `validation/runs/v3_crossover_zero_line_fix_20260611_details.csv`
- `validation/runs/v3_crossover_zero_line_fix_20260611_summary.md`
- `validation/runs/v3_crossover_zero_line_fix_multi_date_summary.md`

## Before / After

| D date | Run | Candidates | PRE_BULL | PRE_BEAR | PRE_BULL with MACD and signal above zero |
|---|---:|---:|---:|---:|---:|
| 2026-05-11 | old `v3_scan` | 331 | 160 | 171 | 142 |
| 2026-05-11 | fixed | 176 | 5 | 171 | 0 |
| 2026-06-11 | old `v3_scan` | 273 | 33 | 240 | 25 |
| 2026-06-11 | fixed | 241 | 2 | 239 | 0 |

## Symbol Checks

ASML, old 2026-06-11:

```text
CandidateState = PRE_BULL_CROSSOVER
CrossoverOpportunityType = BULLISH_NEAR_TRANSITION
MACD_1D_Value = 64.0542
MACD_1D_Signal = 54.2715
```

ASML, fixed 2026-06-11:

```text
CandidateState = STATUS_QUO
CrossoverOpportunityType = NO_CROSSOVER_ROUTE
MACD_1D_Value = 64.0949
MACD_1D_Signal = 54.2797
```

KLAC, old 2026-06-11:

```text
CandidateState = PRE_BULL_CROSSOVER
CrossoverOpportunityType = BULLISH_NEAR_TRANSITION
MACD_1D_Value = 79.8062
MACD_1D_Signal = 67.3786
```

KLAC, fixed 2026-06-11:

```text
CandidateState = STATUS_QUO
CrossoverOpportunityType = NO_CROSSOVER_ROUTE
MACD_1D_Value = 79.7596
MACD_1D_Signal = 67.3693
```

DUOL, fixed 2026-06-11:

```text
CandidateState = STATUS_QUO
CrossoverOpportunityType = BULLISH_ABOVE_ZERO_CONTINUATION
ReasonCodes = BULL_CROSS_ABOVE_ZERO_LINE_CONTINUATION
MACD_1D_CrossoverState = BULL_CROSS
MACD_1D_Value = 1.8101
MACD_1D_Signal = 1.565
```

## Interpretation

The fix removes the main Crossover contamination: already-bullish above-zero continuation setups are no longer reported as `PRE_BULL_CROSSOVER`.

May 11 bullish Crossover density collapsed from 160 names to 5 names. June 11 bullish Crossover density collapsed from 33 names to 2 names. This is the expected direction for a strict transition family.

The remaining high candidate density on June 11 is bearish Crossover / exit-preservation dominated, not bullish-entry dominated.
