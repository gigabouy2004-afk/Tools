# V3 Crossover Zero-Pair Fix Review

Date written: 2026-06-09

## Issue

The first zero-line fix removed above-zero bullish continuation names from `PRE_BULL_CROSSOVER`, but the near-bull route still accepted mixed zero-line pairs:

```text
MACD <= 0
Signal > 0
Histogram improving
```

MKTW exposed this. TradingView showed broad technical `Sell`, with moving averages selling and MACD level negative. V3 still emitted:

```text
CandidateState = PRE_BULL_CROSSOVER
CandidateClass = WATCH
CrossoverOpportunityType = BULLISH_NEAR_TRANSITION
MACD_1D_Value = -0.0503
MACD_1D_Signal = 0.0669
MACD_1D_Histogram = -0.1172
MACD_1D_PreviousHistogram = -0.1307
```

That is not a clean below-zero bullish Crossover pair because the signal line remained above zero.

## Code Change

Changed `src/stock_screener_v3/evaluators.py` so bullish Crossover requires both MACD and signal at/below zero:

```text
MACD_1D_Value <= 0
MACD_1D_Signal <= 0
```

This applies to both:

- `BULLISH_TRANSITION_CROSSOVER`
- `BULLISH_NEAR_TRANSITION`

## Regression Test

Added `test_crossover_does_not_classify_mixed_zero_line_pair_as_near_bull` in `tests/test_evaluators.py`.

Full suite result:

```text
python -m unittest discover -s tests -v
68 tests OK
```

## Validation Rerun

Rerun command:

```powershell
python -m stock_screener_v3.cli backtest --workspace-root D:\Tools\Stock_Screener_V3 --universe-file data\samples\00-NYSE_NASDAQ_Common_Stocks_Sector-Technology.csv --d-date 2026-06-11 --forward-days 1,2,5 --stage-family CROSSOVER --run-label v3_crossover_zero_pair_fix
```

Artifacts:

- `validation/runs/v3_crossover_zero_pair_fix_20260611_details.csv`
- `validation/runs/v3_crossover_zero_pair_fix_20260611_summary.md`

## Result

June 11 Crossover-only rerun:

```text
Processed = 520
Candidates = 240
PRE_BEAR_CROSSOVER = 239
PRE_BULL_CROSSOVER = 1
```

MKTW after fix:

```text
CandidateState = STATUS_QUO
CandidateClass = STATUS_QUO
CrossoverOpportunityType = NO_CROSSOVER_ROUTE
ReasonCodes = NO_CROSSOVER_ROUTE
MACD_1D_Value = -0.0503
MACD_1D_Signal = 0.0669
MACD_1D_Histogram = -0.1172
MACDHistogramImproving = True
```

The only remaining June 11 bullish Crossover candidate is EPAC:

```text
CandidateState = PRE_BULL_CROSSOVER
CrossoverOpportunityType = BULLISH_TRANSITION_CROSSOVER
MACD_1D_Value = -0.4355
MACD_1D_Signal = -0.5051
ReasonCodes = DAILY_MACD_BULL_CROSS,PARTICIPATION_SUPPORT,ACCEPTANCE_SUPPORT
```

This now matches the intended Crossover definition: bullish Crossover is a below-zero seller-to-buyer transition, not a broad oversold bounce or mixed-regime technical summary disagreement.
