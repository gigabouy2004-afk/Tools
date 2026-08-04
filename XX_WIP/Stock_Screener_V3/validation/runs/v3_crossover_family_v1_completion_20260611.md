# V3 Crossover Family V1 Completion

Date written: 2026-06-11

## Decision

`CROSSOVER` is V1 complete and tested for the current engine scope.

This means the family has a stable route boundary, regression coverage, generated calibration reporting, and validation artifacts sufficient to move the next implementation focus to `DIVERGENCE`.

This does not freeze future review-priority or score calibration. Any future Crossover change still requires a backtest report and must preserve the family boundary.

## Completed Route Contract

`PRE_BULL_CROSSOVER`:

- New-capital entry review.
- Requires daily bullish MACD transition or near-transition.
- Requires both `MACD_1D_Value <= 0` and `MACD_1D_Signal <= 0`.
- Rejects above-zero bull continuation as Crossover.
- Rejects mixed zero-line pairs such as the MKTW case where MACD is below zero but signal remains above zero.

`PRE_BEAR_CROSSOVER`:

- Existing-capital exit / capital-preservation review.
- Accepts daily bear cross, near bear transition, or below-signal deterioration with supporting bearish structure.
- Remains available in bearish baseline contexts.

## Key Validation Artifacts

- `validation/runs/v3_crossover_zero_line_fix_review_20260609.md`
- `validation/runs/v3_crossover_zero_pair_fix_review_20260609.md`
- `validation/runs/v3_generated_cross_sector_bear_crossover_report_20260611.md`
- `validation/runs/v3_generated_symbol_failure_report_20260611.md`

Generated cross-sector report baseline:

- Detail files: 15.
- Candidate filter: `PRE_BEAR_CROSSOVER`.
- Candidate rows: 725.
- D+20 median worst-low by sector:
  - Technology: -7.00%.
  - Industrials: -8.89%.
  - Energy: -8.63%.
  - Telecommunications: -6.29%.
  - Utilities: -5.26%.

## Test Confirmation

```text
$env:PYTHONPATH='D:\Tools\Stock_Screener_V3\src'
python -m unittest discover -s tests -v
70 tests OK
```

Relevant regression coverage includes:

- Above-zero bull continuation does not become `PRE_BULL_CROSSOVER`.
- Below-zero near bull transition can still become `PRE_BULL_CROSSOVER`.
- Mixed zero-line MKTW-style pair does not become `PRE_BULL_CROSSOVER`.
- Bear cross and near-bear transition produce `PRE_BEAR_CROSSOVER`.
- Baseline routing preserves bearish Crossover exit review while blocking inappropriate bullish entry paths.

## Next Plan

Move implementation focus to `DIVERGENCE`:

1. Validate current regular and hidden Divergence route diagnostics.
2. Build sector/date/outcome review tables for bullish and bearish Divergence separately.
3. Calibrate swing geometry and quality thresholds only after reviewing generated validation evidence.
4. Keep Crossover, Momentum Setup, and Divergence hard gates separate.
