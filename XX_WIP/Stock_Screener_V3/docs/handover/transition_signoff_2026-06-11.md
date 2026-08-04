# Stock Screener V3 Transition Signoff

Date: 2026-06-11

Purpose: compact handover for a new session on the same V3 stage-family calibration topic.

## Current Git State

Branch: `main`

Latest pushed commit:

```text
5eda4b5 Backtest divergence below EMA200 rule
```

Known state at signoff:

- local `HEAD` matched `origin/main`;
- worktree was clean before this signoff document was created;
- full test suite passed after the latest engine change, but this was only a current-code smoke/regression check and must not be treated as V3 acceptance against the canonical original intent.

## Completed In This Workstream

### Crossover Family

Status: V1 complete for current engine scope.

Relevant commits:

- `214f6e6 Mark crossover family v1 complete`
- `f56d262 Consolidate validation scan artifacts`

Notes:

- Crossover zero-line and mixed zero-line pair behavior was corrected.
- Bear Crossover path-metric validation was completed across sectors.
- No further Crossover route-boundary work is pending before the next stage.

### Divergence Family

Status: implemented, unit-tested, and backtested after the path-forward rule.

Relevant commits:

- `3fc347b Close divergence family v1 validation`
- `86b0700 Calibrate raw bullish divergence below EMA200`
- `5eda4b5 Backtest divergence below EMA200 rule`

Current rule:

- raw/unconfirmed bullish Divergence below EMA200 remains auditable;
- it is emitted as `REJECTED`;
- reason code: `RAW_BULLISH_DIVERGENCE_BELOW_EMA200`;
- confirmed bullish Divergence below EMA200 can still be `WATCH` with `NEEDS_MANUAL_REVIEW`.

Backtest result:

- 15 fresh post-rule backtests completed.
- Sectors: Technology, Industrial, Energy, Telecom, Utilities.
- Dates: 2026-02-11, 2026-03-11, 2026-04-11.
- Horizons: D+1, D+2, D+5, D+10, D+20.
- Before-rule selected/watch baseline: 3,144.
- Post-rule selected/watch candidates: 3,056.
- Rows directly rejected by the new rule: 33.
- Those 33 rows were mixed overall:
  - 54.55% D+20 hit rate;
  - 0.25% median D+20 endpoint;
  - -7.55% median D+20 worst low.

Decision:

- keep the Divergence rule as a conservative risk-separation guardrail;
- do not add more Divergence tightening from this evidence alone;
- move forward to Momentum Setup path-forward calibration.

Key artifacts:

- `docs/architecture/v3_divergence_contract.md`
- `validation/runs/v3_divergence_rule_backtest_review_20260611.md`
- `validation/runs/v3_divergence_rule_stage_family_calibration_20260611.md`
- `validation/runs/v3_divergence_rule_integrated_calibration_20260611.md`

### Momentum Setup Family

Status: V1 complete, but next path-forward calibration is pending.

Relevant commit:

- `1a10f92 Close momentum setup family v1 validation`

Known weak area:

- `BULL_PULLBACK_REENTRY`
- `BELOW_EMA200`
- weak February-March Industrials

Do not restart with broad discovery. Start from the existing Momentum Setup reports and implement/backtest the focused path-forward rule.

Key artifacts:

- `validation/runs/v3_momentum_setup_stage_family_calibration_20260611.md`
- `validation/runs/v3_momentum_setup_symbol_failure_report_20260611.md`
- `validation/runs/v3_momentum_setup_family_v1_completion_20260611.md`
- `validation/runs/v3_divergence_rule_integrated_calibration_20260611.md`

## Verification Baseline

Latest full regression run:

```text
$env:PYTHONPATH='D:\Tools\Stock_Screener_V3\src'
python -m unittest discover -s tests -v
76 tests OK
```

## New Session Start Instructions

Start here:

1. Read this file first:
   - `docs/handover/transition_signoff_2026-06-11.md`
2. Confirm clean repo:
   - `git status --short`
   - `git rev-parse HEAD`
   - `git rev-parse origin/main`
3. Move directly to Momentum Setup path-forward work:
   - inspect `evaluate_momentum_setup` in `src/stock_screener_v3/evaluators.py`;
   - inspect the existing Momentum Setup tests in `tests/test_evaluators.py`;
   - use the completed reports listed above as the baseline;
   - focus on `BULL_PULLBACK_REENTRY` below EMA200 in weak February-March Industrial contexts.
4. After implementation, run:
   - focused evaluator tests;
   - full regression suite;
   - fresh path-enabled backtests over the same five-sector, three-date matrix used for the Divergence backtest.
5. Update:
   - `docs/architecture/v3_evidence_stage_matrix.md`;
   - `docs/handover/current_session_handover.md`;
   - this signoff file or a new dated signoff;
   - relevant validation markdown under `validation/runs/`.

## Explicit Do-Not-Do

- Do not spend a new session rediscovering Crossover or Divergence completion.
- Do not add more report-only work before the Momentum Setup evaluator path-forward rule.
- Do not tighten Divergence further unless new backtests show a clearly weak, repeatable slice.
- Do not treat bearish Crossover as bullish-entry quality; it remains exit/capital-preservation visibility.

## Useful Commands

Run full tests:

```powershell
$env:PYTHONPATH='D:\Tools\Stock_Screener_V3\src'
python -m unittest discover -s tests -v
```

Run one path-enabled backtest:

```powershell
$env:PYTHONPATH='D:\Tools\Stock_Screener_V3\src'
python -m stock_screener_v3.cli backtest --workspace-root . --universe-file data\samples\00-NYSE_NASDAQ_Common_Stocks_Sector-Industrial.csv --d-date 2026-03-11 --forward-days 1,2,5,10,20 --stage-family CROSSOVER,MOMENTUM_SETUP,DIVERGENCE --run-label v3_momentum_rule_backtest_industrial_20260611
```

Generate stage-family report from detail CSVs:

```powershell
$env:PYTHONPATH='D:\Tools\Stock_Screener_V3\src'
python -m stock_screener_v3.cli stage-family-report --details <comma-separated-detail-csvs> --output validation\runs\v3_momentum_rule_stage_family_calibration.md --stage-family MOMENTUM_SETUP --horizon-days 20
```
