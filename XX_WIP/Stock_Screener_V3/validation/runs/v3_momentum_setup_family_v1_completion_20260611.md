# V3 Momentum Setup Family V1 Completion

Date written: 2026-06-11

## Decision

`MOMENTUM_SETUP` is V1 complete and tested for the current engine scope.

This means bull pullback re-entry and bull continuation route behavior, diagnostics, baseline blocking, generated stage-family calibration reporting, and validation artifacts are sufficient to close the stage-family implementation pass.

This does not freeze future review-priority or scoring calibration. Any future Momentum Setup change still requires backtest evidence and must preserve the family boundary.

## Completed Route Contract

`BULL_PULLBACK_REENTRY`:

- Bull-phase pullback/re-entry review.
- Requires daily MACD already above signal and price above/reclaiming EMA20.
- Uses EMA20 reclaim or higher-low behavior as route evidence.

`BULL_CONTINUATION_MOMENTUM`:

- Bull-phase continuation review.
- Requires daily MACD already above signal and price above EMA20.
- Uses trend ladder/DMI support or positive expanding histogram as route evidence.
- Current opportunity subtypes:
  - `BULLISH_CONTINUATION_MOMENTUM`
  - `BULLISH_MOMENTUM_EXPANSION`

## Validation Artifacts

- `validation/runs/v3_momentum_setup_smoke_20260211_summary.md`
- `validation/runs/v3_momentum_setup_stage_family_calibration_20260611.md`
- `validation/runs/v3_momentum_setup_symbol_failure_report_20260611.md`

Path-enabled calibration baseline:

- Detail files: 15.
- Candidate rows: 1,279.
- Horizon: D+20.
- Candidate-state split:
  - `BULL_PULLBACK_REENTRY`: 1,246 candidates, 49.28% hit rate, -0.39% median endpoint, -7.36% median worst low.
  - `BULL_CONTINUATION_MOMENTUM`: 33 candidates, 51.52% hit rate, 0.36% median endpoint, -6.01% median worst low.

Sector/date read:

- Stronger slices:
  - Energy: 71.81% hit rate, 4.21% median endpoint.
  - Technology: 57.82% hit rate, 6.30% median endpoint.
  - April 2026: 63.54% hit rate, 5.06% median endpoint.
- Weaker slices:
  - Industrials: 39.79% hit rate, -3.75% median endpoint, -9.66% median worst low.
  - February 2026: 34.46% hit rate, -6.06% median endpoint, -10.82% median worst low.
  - March 2026: -10.24% median worst low.

## Calibration Read

- Momentum Setup V1 is producing auditable route groups and should remain visible.
- `BULL_PULLBACK_REENTRY` is the dominant route and carries the main failure risk.
- Industrial and weak-date pullback re-entry should be reviewed first if future priority/scoring calibration is needed.
- No route-boundary change is promoted from this pass.

## Test Confirmation

```text
$env:PYTHONPATH='D:\Tools\Stock_Screener_V3\src'
python -m unittest discover -s tests -v
73 tests OK
```

## Next Plan

All three stage families now have V1 closure for the current engine scope:

- `CROSSOVER`
- `DIVERGENCE`
- `MOMENTUM_SETUP`

Next implementation focus should shift to integrated holistic validation:

1. Validate ranking collisions across the closed families.
2. Review review-priority calibration across sectors/dates.
3. Decide whether to add a sector/date/context urgency layer.
4. Keep enriched universe metadata/filtering as the parallel data-quality track.
