# V5 Handover - Single Output Column Requirement

Date: 2026-07-02

Current output contract reference:

- `docs/V5_CURRENT_OUTPUT_CONTRACT_2026-07-04.md`

Codex/future-agent instruction:

- Do not summarize V5 as a multi-column ranking system for the end user.
- Do not say the user must combine `Score`, `Action_Status`, trend, timing, relative strength, or other technical columns to make the final call.
- The final user-facing output is one field: `Final_Decision`.
- Technical columns are permitted only as internal/audit details.

## Repository State

Current committed HEAD before this handover document:

- `6f9bdf6 Add V5 indicator revalidation diagnosis`

Remote:

- `origin/main`
- `https://github.com/gigabouy2004-afk/Stock_MomentumDetector.git`

Important local note:

- `V5_Momentum_Execution_Dump.csv` is locally modified but was not part of controlled validation work.
- Several ad hoc runtime CSV/XLSX files remain untracked.
- These runtime dumps are intentionally not included in this handover unless explicitly requested.

## Work Completed In This Session

Committed validation work:

- `d19f6d3 Add historical intraday D+2 validation artifacts`
- `68f1b9b Add random20 D+2 intraday validation report`
- `cc978de Add May random20 D+2 validation rounds`
- `6f9bdf6 Add V5 indicator revalidation diagnosis`

Key artifacts:

- `Validate_V5_Status_DD2.py`
- `docs/V5_STATUS_DD2_VALIDATION_RUN_2026-07-02.md`
- `docs/V5_RANDOM20_DD2_INTRADAY_VALIDATION_2026-07-02.md`
- `docs/V5_RANDOM20_MAY06_MAY19_MULTIROUND_VALIDATION_2026-07-02.md`
- `docs/V5_INDICATOR_REVALIDATION_DIAGNOSIS_2026-07-02.md`
- `backtests/V5_Random20_May06_May19_Consolidated_20260702_133607.csv`
- `backtests/V5_Backtest_Iteration_Log.csv`

## Current Finding

The engine's current `Actionable Momentum Candidate` output is not reliable enough as a direct immediate-entry decision.

Observed issue:

- On 2026-05-06, the engine produced 5 actionable momentum calls.
- 3 of those failed D+2 continuation.
- `PL`, `CVV`, and `ETN` were marked actionable but did not confirm through D+1/D+2.

The failure is not primarily a CSV/reporting issue. The decision layer is overconfident.

## User Requirement Going Forward

The user does not want multiple interpretive columns as the final user-facing decision.

Required final behavior:

- The execution report must provide one decisive final column.
- That column must be reliable enough to read directly.
- Internal forks, gates, sub-scores, setup/entry distinctions, and diagnostics can exist internally, but they must collapse into one final output field.

Recommended final column name:

- `Final_Decision`

Recommended possible values:

- `MOMENTUM_ACTIVE`
- `MOMENTUM_PRESENT_WAIT_CONFIRMATION`
- `REJECT`

The exact labels can be changed, but the output must remain one final decision column.

## Implementation Constraint

Do not continue adding more user-facing score/status columns as a substitute for fixing the decision.

Any next engine revision should:

1. Keep internals private or diagnostic-only.
2. Produce one final decision column.
3. Backtest that final column against D+1/D+2 behavior.
4. Treat any `MOMENTUM_ACTIVE` that fails D+1/D+2 as a direct engine failure.

## Technical Direction For Next Work

The next version should not merely add more text explanations. It should revise the decision logic.

Likely internal changes needed:

- Split structural setup from confirmed entry internally.
- Tighten relative-strength interpretation.
- Add extension/exhaustion control.
- Add relative-volume confirmation or downgrade logic.
- Add D-day candle and close-quality interpretation.
- Add benchmark/market context.
- Add D+1 confirmation mode for live use where required.

But the final execution report should expose one primary decision column only.

## Handover Position

V5 is currently useful as a diagnostic momentum setup engine, but not as a safe immediate-entry engine.

Before any new feature work, the next task should be to rebuild the final decision layer around a single output column and validate that column across randomized D/D+1/D+2 tests.
