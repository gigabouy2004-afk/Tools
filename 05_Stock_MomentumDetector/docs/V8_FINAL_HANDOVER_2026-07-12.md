# V8 Development Handover

Date: 2026-07-12

Status: the rebuilt research engine now implements EMA200 plus MACD `12/26/9` Foundation, DMI eligibility and the V1 composite Health Score out of 30, with research qualification at 20. The integrated 1,200-row parity replay passed. `Momentum_Detector_V8.py` remains the legacy comparator, and V7 remains operational until broader validation and explicit signoff.

Plain-language analysis update, 2026-07-13: `docs/V8_EXPERIMENT_ANALYSIS_BRIEF_2026-07-13.md` is now the required first-read document. It defines MACD Reset and post-Foundation scoring, separates three MACD non-confirmation states, documents the freshness-score sign defect, and lists all matters requiring user approval.

Charter reset, 2026-07-13: active design authority has moved to `docs/V8_REVISED_DEVELOPMENT_CHARTER_2026-07-13.md` and `docs/MOMENTUM_ENGINE_FOUNDATIONAL_DESIGN_STANDARD_2026-07-13.md`. The current V8 code is a frozen experimental comparator; its inherited post-Foundation rules are not automatically approved.

Rebuild workflow approval, 2026-07-13: begin with a basic V8 engine, add one indicator at a time, fully test its formula/values/scores/gates, and integrate only after explicit user approval. Checkpoint: `docs/V8_BASIC_ENGINE_REBUILD_CHECKPOINT_2026-07-13.md`.

Historical Basic Foundation checkpoint, 2026-07-13: `Momentum_Detector_V8_Basic.py` initially provided a standalone EMA/MACD eligibility path with no Score or post-Foundation indicators. Its frozen 80-row replay remains audit evidence; current behavior is defined by the later Health Score implementation report.

Historical calculation-only checkpoint, corrected 2026-07-13: RSI, ADX/+DI/-DI, True Range/ATR/ATR%, OBV/OBV EMA and Aroon were first added without decision authority. That checkpoint remains audit evidence. DMI and the V1 RSI/ADX/OBV components now have explicitly approved research authority.

Historical RSI placeholder checkpoint, 2026-07-13: the inclusive 30-65 range proved configurable cutoff mechanics only. It is superseded in the active engine by the approved V1 tiered RSI Score values.

Placeholder clarification, 2026-07-13: RSI 30/65 remains historical functional-test evidence and is not active. All current Health Score periods, limits and points are named configuration variables with explicit user-approved-research, non-operational metadata.

V1-V7 indicator audit, 2026-07-13: source-code values and version changes for EMA/MACD/RSI/ADX/DMI/ATR/OBV/Aroon and the V4-V7 replacement framework are consolidated in `docs/V1_V7_INDICATOR_VALUE_AUDIT_2026-07-13.md`. Missing V7 indicators are traced back to their last source implementation rather than inferred.

V1-V3 research baseline, 2026-07-13: the exact V1-V3 indicator values are consolidated in a configurable research-only evaluator and replayed across 20 technology stocks and four dates. All 240 rows passed independent recalculation. V1/V2 qualified 7 observations without improving longer-horizon results over Foundation alone; V3 qualified 11, weakened D+1 direction and showed a small-sample D+8 improvement. The values are frozen for isolated research, not approved for mainstream V8. Report: `docs/V8_V1_V3_INDICATOR_BASELINE_BACKTEST_2026-07-13.md`.

Expanded composite-Score result, 2026-07-13: momentum selection is now explicitly evaluated as the culmination of the configured health signals. The unchanged V1-V3 configurations were replayed on 50 technology and 50 industrial stocks across 12 dates. The 3,600-row run passed independent validation. V1/V2 Score >=20 improved D+1/D+5/D+8 positive rates over the Foundation+DMI cohort, with the strongest separation in technology. V3 added 75 weaker signals, and higher raw Score was not monotonically better. Report: `docs/V8_COMPOSITE_SCORE_EXPANDED_BACKTEST_2026-07-13.md`.

Health Score implementation approval, 2026-07-13: the rebuilt Basic engine now executes EMA200+MACD12/26/9 Foundation, DMI14 eligibility, then the V1 RSI14+ADX14+OBV/EMA20 composite Raw Health Score out of 30. Score >=20 produces research qualification. The integrated 1,200-row replay achieved exact parity with the independently validated V1 evidence. Aroon/opening, ETF and inherited V4-V7 score logic are not included. Report: `docs/V8_BASIC_HEALTH_SCORE_IMPLEMENTATION_2026-07-13.md`.

MACD comparison closure, 2026-07-13: MACD 12/26/9 and 8/21/5 were replayed on 100 stocks and 12 dates with unchanged DMI and Health Score, using D+1/D+3 false positives as the priority. The 2,400-row run passed independent validation. MACD 12/26/9 produced lower false-positive rates overall and materially better technology precision; 8/21/5 did not solve industrial D+1. Retain 12/26/9 and proceed to industrial sector-context research. Report: `docs/V8_MACD_FOUNDATION_COMPARISON_2026-07-13.md`.

## Start Here

Read in this order:

1. `docs/V8_REVISED_DEVELOPMENT_CHARTER_2026-07-13.md`
2. `docs/MOMENTUM_ENGINE_FOUNDATIONAL_DESIGN_STANDARD_2026-07-13.md`
3. `docs/V8_BASIC_HEALTH_SCORE_IMPLEMENTATION_2026-07-13.md`
4. `docs/V8_COMPOSITE_SCORE_EXPANDED_BACKTEST_2026-07-13.md`
5. `docs/V8_MACD_FOUNDATION_COMPARISON_2026-07-13.md`
6. `docs/V8_V1_V3_INDICATOR_BASELINE_BACKTEST_2026-07-13.md`
7. `docs/V1_V7_INDICATOR_VALUE_AUDIT_2026-07-13.md`
8. `docs/V8_BASIC_ENGINE_REBUILD_CHECKPOINT_2026-07-13.md`
9. `docs/V8_BASIC_FOUNDATION_IMPLEMENTATION_2026-07-13.md` for historical checkpoint behavior
10. `docs/V8_CALCULATION_ONLY_INDICATORS_IMPLEMENTATION_2026-07-13.md` for historical checkpoint behavior
11. `docs/V8_RSI_BASE_LAYER_IMPLEMENTATION_2026-07-13.md` for historical placeholder behavior
12. `docs/V8_EXPERIMENT_ANALYSIS_BRIEF_2026-07-13.md`
13. `docs/V8_FOUNDATION_VALIDATION_CONCLUSION_2026-07-12.md`
14. `docs/V8_CURRENT_OUTPUT_CONTRACT_2026-07-10.md` for legacy comparator behavior only
15. `docs/V1_V8_EMA200_MACD_FOUNDATION_DISCOVERY_2026-07-12.md`
16. `docs/V8_COMPREHENSIVE_BACKTEST_PLAN_2026-07-12.md`

## Legacy Comparator Behavior

Legacy entry point:

```text
Momentum_Detector_V8.py
```

Defaults:

```text
MACD fast/slow/signal = 8/21/5
Foundation policy = enforce
Foundation valid = Close > EMA200 AND MACD line > signal AND MACD line > 0
Active threshold = 85
ETF = informational postprocessor only for Active
```

CLI controls:

```text
--macd-fast
--macd-slow
--macd-signal
--foundation-policy enforce|audit
```

`audit` is a regression facility, not the normal operating policy.

New output fields:

```text
Foundation_Status
Foundation_Qualified
Foundation_Reason
Foundation_Policy
```

An existing append-only V8 log with the old header is preserved; V8 opens a timestamped log using the new schema.

## Files Added or Changed

Implementation and shared replay:

```text
Momentum_Detector_V8.py
Backtest_Momentum_Detector_V8.py
```

Focused runner and independent validator:

```text
Backtest_Momentum_Detector_V8_Foundation.py
Validate_Momentum_Detector_V8_Foundation.py
config/V8_Foundation_Validation_Config.json
tests/test_v8_foundation_backtest.py
tests/test_v8_macd.py
```

Canonical frozen run:

```text
backtests/V8_Foundation_Validation/runs/V8FOUND_20260712T182945Z_cf0c908
```

## Result Snapshot

```text
Stocks / dates / rows: 20 / 4 / 80
Foundation Valid: 25
MACD Reset: 28
Below EMA200: 27
Active / Wait / Reject: 5 / 30 / 45
Active D+1: 4/5 positive
Active D+5: 5/5 positive
Active D+8: 4/5 positive
Regression failures: 0
Independent recompute failures: 0
ETF mappings returned / Q2 accepted: 21 / 7
ETF score mutations: 0
Checksum validation: PASS
Focused tests: 22 PASS
```

## Important Interpretation

Foundation Valid materially improved D+1 behavior: 76% positive with +2.21% mean, compared with 53.6% and -0.05% for MACD Reset. This supports the first filter for the user's primary directional objective.

The reset cohort remained strong at D+5/D+8. Five legacy Active rows were blocked by the new MACD rule; only 2/5 were positive at D+1, but 4/5 were positive at D+8. Preserve `FOUNDATION_TREND_VALID_MACD_RESET` as a WAIT state for the joint analysis rather than treating it as a failed trend.

The full scorer remains restrictive after Foundation qualification: 18 Foundation Valid rows were still rejected. Those rows were positive 13/18 at D+1, 16/18 at D+5, and 14/18 at D+8. This suggests the next review should examine downstream Setup/Momentum thresholds independently from the restored Foundation rule.

Detailed review found that all 25 analyzed rows received 12 freshness points because a negative distance-from-high field is compared with positive thresholds. A likely sign correction did not change a Final Decision in this sample, but the formula must be approved, corrected, tested, and replayed before downstream-score signoff.

## Reproduction

Run focused tests:

```powershell
python -m unittest tests.test_v8_macd tests.test_v8_comprehensive_backtest tests.test_v8_directional_persistence tests.test_v8_foundation_backtest tests.test_etf_context_v8
```

Run the frozen-scope workflow again with new provider data:

```powershell
python Backtest_Momentum_Detector_V8_Foundation.py --config config/V8_Foundation_Validation_Config.json --output-root backtests/V8_Foundation_Validation/runs
```

Validate the sealed canonical run, including checksums:

```powershell
python Validate_Momentum_Detector_V8_Foundation.py backtests/V8_Foundation_Validation/runs/V8FOUND_20260712T182945Z_cf0c908
```

## Remaining Gates

- Joint review of the Foundation Valid, MACD Reset, and Foundation-Valid-but-rejected cohorts.
- Multi-regime chronological validation beyond 2026Q2.
- Untouched date and ticker holdouts.
- Industrial-sector expansion using the same frozen contract.
- Historical hourly/live-quote evidence or explicit acceptance of daily-only replay.
- Prospective ETF shadow evidence with more Active rows.
- Explicit user approval before V8 replaces V7.

Current boundary:

```text
V7 = OPERATIONAL BASELINE
V8 = FOUNDATION IMPLEMENTED AND FOCUSED VALIDATION PASSED; DEVELOPMENT ONLY
```
