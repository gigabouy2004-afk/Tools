# V3 Divergence Family V1 Completion

Date written: 2026-06-11

## Decision

`DIVERGENCE` is V1 complete and tested for the current engine scope.

This means the route contract, evaluator diagnostics, ranking participation, generated stage-family calibration report, and validation artifacts are sufficient to move implementation focus to `MOMENTUM_SETUP`.

This does not freeze future scoring or swing-geometry calibration. Any future Divergence change still requires backtest evidence and must preserve the Divergence family boundary.

## Completed Route Contract

Regular Divergence:

- `BULLISH_DIVERGENCE`
- `BEARISH_DIVERGENCE`

Hidden Divergence:

- `HIDDEN_BULLISH_DIVERGENCE`
- `HIDDEN_BEARISH_DIVERGENCE`

The evaluator emits:

- `DivergenceDirection`
- `DivergenceType`
- `DivergenceOpportunityType`
- `DivergenceConfirmationState`
- `DivergencePriceSwing`
- `DivergenceMomentumSwing`
- `DivergenceBarsAgo`
- `DivergenceQualityScore`
- `DivergenceQualityComponents`
- `DivergenceReasonCodes`

## Validation Artifacts

- `validation/runs/v3_divergence_smoke_20260211_summary.md`
- `validation/runs/v3_divergence_stage_family_calibration_20260611.md`
- `validation/runs/v3_divergence_path_enabled_calibration_20260611.md`

Path-enabled calibration baseline:

- Detail files: 15.
- Candidate rows: 962.
- Horizon: D+20.
- Candidate-state split:
  - `BEARISH_DIVERGENCE`: 210 candidates, 59.52% hit rate, 2.69% median endpoint, -7.57% median worst low.
  - `BULLISH_DIVERGENCE`: 211 candidates, 44.08% hit rate, -1.45% median endpoint, -11.13% median worst low.
  - `HIDDEN_BEARISH_DIVERGENCE`: 284 candidates, 52.82% hit rate, 0.95% median endpoint, -9.31% median worst low.
  - `HIDDEN_BULLISH_DIVERGENCE`: 257 candidates, 56.42% hit rate, 1.23% median endpoint, -7.50% median worst low.

## Calibration Read

- Divergence V1 is producing meaningful, auditable candidate groups.
- `BULLISH_DIVERGENCE` is the weakest current slice and should be the first Divergence slice revisited if future calibration work is needed.
- No route-boundary change is promoted from this pass.
- Keep Divergence independent from Crossover zero-line rules and Momentum Setup bull-continuation gates.

## Test Confirmation

```text
$env:PYTHONPATH='D:\Tools\Stock_Screener_V3\src'
python -m unittest discover -s tests -v
72 tests OK
```

## Next Plan

Move implementation focus to `MOMENTUM_SETUP`:

1. Validate `BULL_PULLBACK_REENTRY` and `BULL_CONTINUATION_MOMENTUM` route behavior.
2. Generate a path-enabled Momentum Setup stage-family calibration report.
3. Review pullback re-entry vs continuation outcomes separately.
4. Close Momentum Setup V1 only after documentation, tests, and validation artifacts are updated.
