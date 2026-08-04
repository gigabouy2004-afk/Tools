# Stock Screener V3_Charter Current Session Handover

Last updated: 2026-06-16

Repo: `D:\Tools\Stock_Screener_V3`

GitHub: `https://github.com/gigabouy2004-afk/Stock_Screener_V3.git`

Branch: `V3_Charter`

## Current Restart Source

Use this file only as a compact pointer.

Primary restart/signoff document:

- [v3_charter_restart_signoff_20260616.md](/D:/Tools/Stock_Screener_V3/docs/handover/v3_charter_restart_signoff_20260616.md)

Primary offline master charter:

- [v3_charter_consolidated_engine_design.md](/D:/Tools/Stock_Screener_V3/docs/charter/v3_charter_consolidated_engine_design.md)

Original seed charter:

- [v3_original_intent_and_handover.md](/D:/Tools/Stock_Screener_V3/docs/charter/v3_original_intent_and_handover.md)

## Current Status

- Current charter version: `V1.6`
- Local and GitHub should match on `V3_Charter`
- Reviewed seed code file:
  - [C:\Users\dell\OneDrive\Desktop\Stock_Engine3_Pythoncode.py](/C:/Users/dell/OneDrive/Desktop/Stock_Engine3_Pythoncode.py)
- That external file is accepted as a seed scaffold only, not as the active engine script

## Current Next Step

- integrate accepted manifest, slicing, and EMA-high logic from the reviewed seed file into the package under `src/stock_screener_v3`
- keep `web_app_v3.py` as the active UI surface
- do not create a parallel desktop-engine path

## Sync Check

```powershell
cd D:\Tools\Stock_Screener_V3
git status --short --branch
git log --oneline --decorate -8
```

Expected state:

```text
## V3_Charter...origin/V3_Charter
```

## Canonical Immutable Scope

Read this document first in every future session:

```text
docs/charter/v3_original_intent_and_handover.md
```

Then read the standalone consolidated charter:

```text
docs/charter/v3_charter_consolidated_engine_design.md
```

It is the authoritative source for `V3_Charter` intent: user CSV input, exactly three analysis paths (`CROSSOVER`, `DIVERGENCE`, `SETUP`), V2 L0/L1/L2/L3-style path-first architecture, D-date processing, D+X self-backtesting, and the rule that local documentation and GitHub must be updated before ending a completed step.

This canonical document supersedes any scattered handover, validation, sector/regime, or calibration artifact that appears to broaden the core V3 scope without explicit user approval.

Carry forward only user-confirmed processing logic: API-based data retrieval per calculation, V2-style two-year historical pull where applicable, backtesting utility, D-date and D+X future processing, EMA200 evidence/risk handling, EMA lifetime-high percentage style datapoints, bounded market-regime context, bounded sector context when requested, one-month candle behavior, lifetime high/low boundary checks, and future AI/sentiment evidence. Do not carry forward the prior broad market-regime, sector, or cross-sector calibration work as V3 direction.

Do not describe OHLCV as the universal V3 input requirement. V2's MACD/Momentum baseline used Close series; other fields should be requested from the API only when a selected evidence module needs them.

Single-engine construction rule: V2 details such as EMA200, lifetime high, EMA lifetime-high percentage, RSI, one-month candles, sector context, and market-regime context can refine confidence/risk/explanation only inside a selected path trajectory. They must not become base-level drivers, route selectors, or overrides of Crossover, Divergence, or Momentum Setup.

The canonical document now includes a V2 Design Intent Validation Matrix. Use that matrix as the starting checklist for engine construction; do not rediscover V2 intent from scattered artifacts.

The canonical document also records the Stage-Family Indicator Matrix requirement. Use `docs/architecture/v3_evidence_stage_matrix.md` as the current matrix reference and `docs/architecture/v3_stage_family_indicator_working_matrix.md` as the editable working table for adding/subtracting/modifying individual V2/V3 indicator rows before coding.

The working matrix now includes a `Backtesting / D+X` column: user supplies a historical D-date, the API/provider fetches data, the same selected path runs as of D, and D+X price is loaded only afterward for simple price validation and optional best-high/worst-low metrics.

## Low-Token Restart Pointer

For the next session on this same topic, read the canonical document above first, then read this compact signoff:

```text
docs/handover/transition_signoff_2026-06-11.md
```

It contains the current pushed commit, completed Crossover/Divergence/Momentum status, the Divergence backtest result, and the exact next path. Do not rediscover the long history below unless a referenced artifact is missing.

## Purpose Of This Document

This is the restart trace for the next session. Keep this document updated whenever the working direction, completed foundation, next step, or open risk changes.

Canonical original-intent and handover document:

- `docs/charter/v3_original_intent_and_handover.md`

Canonical signoff/restart document for the current transition:

- `docs/handover/transition_signoff_2026-06-02.md`

If the computer/session restarts, start here first, then run:

```powershell
cd D:\Tools\Stock_Screener_V3
git status --short --branch
git log --oneline --decorate -8
```

Expected status at this handover:

```text
## V3_Charter...origin/V3_Charter
```

## Test Status Warning

Do not carry forward any existing test-count statement, including "77 tests passing", as proof that V3 satisfies the original engine intent.

The current automated tests are only current-code smoke/regression checks. They are not the acceptance tests for the canonical V3 engine.

The required acceptance tests still need to be derived from `docs/charter/v3_original_intent_and_handover.md`, especially:

- CSV-only universe processing.
- exactly three user paths: `CROSSOVER`, `DIVERGENCE`, `SETUP`.
- L1 baseline and L2 routing preventing path leakage.
- V2 parity for Crossover, Divergence, and Momentum Setup / Bull Extension.
- D-date no-lookahead processing.
- D+X forward validation of actual price movement.

## Current Decision

Do not continue tuning the old V2 Crossover monolith.

V3 is a clean rebuild that should preserve the useful V2 operating model, output visibility, and validation discipline while rebuilding the engine logic with cleaner module boundaries.

The same engine must support both new capital entry and existing capital exit/preservation:

- `PRE_BULL_CROSSOVER`: bull transition / new capital entry review.
- `PRE_BEAR_CROSSOVER`: bear transition / exit or capital-preservation review.

Momentum Setup is a bull-phase continuation/re-entry family, not the same thing as classical MACD crossover transition.

The actual production signal engine/stage evaluators are not yet complete.

## Completed Groundwork

Documentation and architecture:

- Canonical V3 original-intent and handover document.
- Fresh program charter.
- V2 gap analysis against the fresh charter.
- V3 initial analysis and way-forward plan.
- V3 module contracts.
- V3 evidence-to-stage matrix.
- V3 baseline decision tree.
- V3 Divergence contract.
- Backtesting engine requirements.
- V2 operational parity contract.
- Validation baseline acceptance pack.

Foundation code:

- Python package skeleton under `src/stock_screener_v3`.
- Core dataclasses:
  - `UniverseRecord`
  - `PriceDataBundle`
  - `EvidencePack`
  - `ScoreResult`
  - `StageEvaluation`
  - `BacktestRunConfig`
  - `BacktestResult`
- CSV universe loader with metadata preservation for mixed NSE/BSE/NYSE/NASDAQ files.
- Baseline universe metadata contract for enriched NYSE/NASDAQ master universe fields.
- Sector/exchange filtering.
- Deterministic sampling.
- Historical as-of slicing helpers.
- Forward-return helper.
- Backtest engine shell with pluggable price provider and stage evaluator.
- In-memory test price provider.
- Yahoo price provider wrapper.
- Detail CSV writer.
- Summary markdown writer.
- Run path and artifact helpers.
- File and console run logger with explicit close support for Windows.
- V2-compatible offline CSV column contract.
- Guardrail that log, detail CSV, and summary report must be physically separate files.
- First production Crossover evaluator slice.
- Daily evidence builder for MACD, RSI, ADX, Bollinger, EMA, volume, and price structure.
- Crossover route classifier focused on bull/bear phase transition.
- Direction-aware Crossover scoring for bull transition entry signals and bear transition exit/preservation signals.
- Dedicated Momentum Setup evaluator for bull-phase pullback re-entry and continuation candidates.
- Dedicated Divergence evaluator for regular and hidden bullish/bearish divergence candidates.
- Stage-family dispatcher that can evaluate Crossover, Momentum Setup, Divergence, or selected subsets from a shared evidence pack.
- Baseline router that classifies market, sector, and stock regimes before stage-family selection.
- Configurable regime benchmark mapping for exchanges, geographies, sectors, and themes.
- Non-fatal benchmark loading into `PriceDataBundle.benchmarks` for market/sector regime classification.
- Positive-elimination guardrail that blocks bullish entry/Momentum Setup when market, sector, and stock are all bearish, while preserving bear Crossover exit review.
- Explicit `StockTraversalPlan` route object between `BaselineDecision` and stage-family evaluators.
- Traversal diagnostics for selected families, evaluable families, blocked families, and traversal route reason.
- Divergence diagnostics for route candidate, price/momentum swing, confirmation state, direction, type, opportunity, quality components, and reason codes.
- Formal V3 ranking contract for choosing the reported `StageEvaluation` after multi-family traversal.
- Ranking diagnostics for winning rows: contract version, rule, winner family, evaluated families, candidate states/classes, priorities, and scores.
- Divergence included in the default holistic stage-family set after ranking diagnostics were made explicit.
- Divergence direction now participates in baseline bullish-route blocking, matching Crossover and Momentum Setup traversal behavior.
- CLI/run parameter support for comma-separated stage families.
- Reusable run orchestrator.
- CLI entry point.
- Python scanner console for user-selected V3 scans with visible stage classifications and V2-style diagnostics.
- Backtest outcome classification for candidate follow-through.
- Failure-category summary reporting for failed candidate follow-through.
- Candidate score-bucket summary reporting.
- Average and median forward-return summary reporting.
- Score-bucket, sector, and review-priority outcome breakdowns for calibration.
- Stage-family outcome breakdowns for calibration.
- Risk-tag outcome breakdowns for calibration.
- Ranking collision bucket reporting in single-date and multi-date summaries.
- Multi-date backtest pack runner and CLI command.
- Web app support for user-facing scan runs using the shared V3 runner path.
- Web UI stage classification cards for `PRE_BULL_CROSSOVER`, `PRE_BEAR_CROSSOVER`, Divergence states, Momentum Setup states, and `STATUS_QUO`.
- Web UI review-intent split that separates `PRE_BEAR_CROSSOVER` as exit/capital-preservation review from bullish entry/re-entry candidates.

Tests:

- Universe loader tests.
- Backtesting utility tests.
- Backtest engine tests.
- Data provider tests.
- Report/output contract tests, including score-bucket and failure-category summaries.
- Stage evaluator tests for Crossover transition, Momentum Setup re-entry/continuation, and family dispatch.
- Divergence evaluator tests for regular bullish, regular bearish, hidden bullish, hidden bearish, status quo, and stage-family dispatch.
- Baseline router tests for market/sector/stock positive elimination and bearish Crossover preservation.
- Stock traversal plan tests for family blocking, user family restriction preservation, aliases, and status-quo diagnostics.
- Regime benchmark configuration tests.
- Run I/O and log artifact tests.

## Artifact Purpose Definitions

These definitions are settled and should not drift:

- Log file: execution summary report for the run.
- Output CSV: forensic calculation record for each symbol/code.
- Summary markdown: human-readable run summary.

The output CSV must preserve the V2-compatible header block first, then append V3-specific fields.

The CSV writer must emit headers even when zero candidates are found.

## Important Files

Core source:

- `src/stock_screener_v3/models.py`
- `src/stock_screener_v3/universe.py`
- `src/stock_screener_v3/backtesting.py`
- `src/stock_screener_v3/backtest_engine.py`
- `src/stock_screener_v3/data_provider.py`
- `src/stock_screener_v3/reports.py`
- `src/stock_screener_v3/run_io.py`
- `src/stock_screener_v3/output_contracts.py`
- `src/stock_screener_v3/indicators.py`
- `src/stock_screener_v3/evidence.py`
- `src/stock_screener_v3/evaluators.py`
- `src/stock_screener_v3/runner.py`
- `src/stock_screener_v3/cli.py`
- `web_app_v3.py`

Key docs:

- `docs/charter/engine_program_charter_fresh_2026-06-01.md`
- `docs/analysis/current_engine_gap_analysis_against_fresh_charter_2026-06-01.md`
- `docs/analysis/v3_initial_engine_analysis_and_way_forward_2026-06-01.md`
- `docs/architecture/v3_module_contracts.md`
- `docs/architecture/v3_evidence_stage_matrix.md`
- `docs/architecture/v3_divergence_contract.md`
- `docs/architecture/v3_ranking_contract.md`
- `docs/architecture/v3_baseline_decision_tree.md`
- `docs/architecture/rebuild_way_forward_plan.md`
- `docs/architecture/v2_operational_parity_contract.md`
- `docs/backtesting/backtesting_engine_requirements.md`
- `validation/baselines/v3_baseline_acceptance_pack.md`

Tests:

- `tests/test_universe.py`
- `tests/test_backtesting.py`
- `tests/test_backtest_engine.py`
- `tests/test_data_provider.py`
- `tests/test_reports.py`
- `tests/test_run_io.py`

## Recent Commit Trace

```text
6df0f7e Mark regime engine v1 complete
f635e3d Add configurable regime benchmarks
d9dc18d Add baseline regime router
b915718 Add V3 evidence stage matrix
faf5398 Add momentum setup stage evaluator
bd5d782 Add bear transition crossover route
bd693ac Split crossover route opportunity states
2dc2e6f Add backtest failure category reporting
021c9e0 Support mixed exchange universe inputs
4e4dcce Add first V3 crossover engine slice
```

## Last Pushed Restart Snapshot

This session checkpoint has been committed and pushed to GitHub.

Pushed checkpoint:

Backtesting expansion checkpoint after `f8daec9 Close V3 ranking and divergence default path`.

Implemented in this checkpoint:

- Explicit `StockTraversalPlan` route object and traversal diagnostics.
- Divergence contract document.
- Divergence v1 evaluator and diagnostics for regular/hidden bullish/bearish divergence.
- Output contract additions for traversal and Divergence diagnostics.
- Focused tests for traversal and Divergence.
- Formal ranking contract and winning-row ranking diagnostics.
- Default holistic traversal with `CROSSOVER,MOMENTUM_SETUP,DIVERGENCE`.
- Backtesting documentation update for the full V3 execution path.
- Multi-date backtest pack command and aggregate summary.
- Average/median forward returns plus score-bucket, sector, and review-priority outcomes.
- Parallel architecture track for enriched NYSE/NASDAQ master-universe filter fields.
- Smoke summaries:
  - `validation/runs/v3_traversal_plan_smoke_20260211_summary.md`
  - `validation/runs/v3_divergence_smoke_20260211_summary.md`
- Live full-engine smoke, not committed as an artifact:
  - command label: `v3_full_engine_live_smoke`
  - D date: `2026-02-11`
  - stage families: `CROSSOVER,MOMENTUM_SETUP,DIVERGENCE`
  - sample: `data\samples\us_master_sample.csv`
  - processed 3 symbols, skipped 0, found 2 candidates
  - CSV confirmed traversal, ranking, and Divergence diagnostic columns
- Live multi-date pack smoke, not committed as an artifact:
  - command label: `v3_pack_live_smoke`
  - D dates: `2026-02-11,2026-03-11`
  - stage families: `CROSSOVER,MOMENTUM_SETUP,DIVERGENCE`
  - sample: `data\samples\us_master_sample.csv`
  - processed 6 symbol-date rows, skipped 0, found 3 candidates
  - aggregate summary confirmed per-date density and aggregate D+1/D+2/D+5 outcomes
- Web app HTTP smoke, not committed as artifacts:
  - URL: `http://127.0.0.1:8010`
  - single-date web POST used `v3_web_http_smoke`
  - multi-date web POST used `v3_web_pack_http_smoke`
  - both returned rendered result summaries and artifact paths
- Web UI stage-classification correction smoke, not committed as artifacts:
  - command label: `v3_ui_stage_http_smoke`
  - confirmed initial page shows stage taxonomy
  - confirmed result table includes V2-visible diagnostic fields such as `CandidateStateRaw`, `MACD_1D_CrossoverState`, and `RSI_1D`
- Web UI scanner-framing correction:
  - removed visible backtest/multi-date pack controls from the operator UI
  - retained D as the scan/as-of date used by the shared V3 execution path
  - backtesting remains a CLI/validation harness, not the primary web UI model

## 2026-06-05 Validation Checkpoint

Full Technology-universe validation started from:

- `data/samples/00-NYSE_NASDAQ_Common_Stocks_Sector-Technology.csv`
- 525 NYSE/NASDAQ Technology symbols attempted per date
- stage families: `CROSSOVER,MOMENTUM_SETUP,DIVERGENCE`
- forward horizons: D+1, D+2, D+5, D+10, D+20

The initial full `backtest-pack` command completed all three per-date runs but hit the shell timeout before writing the built-in aggregate markdown. The completed date artifacts were preserved, and a manual aggregate summary was written from the per-date detail CSVs:

- `validation/runs/v3_tech_full_pack_20260605_20260211_summary.md`
- `validation/runs/v3_tech_full_pack_20260605_20260311_summary.md`
- `validation/runs/v3_tech_full_pack_20260605_20260411_summary.md`
- `validation/runs/v3_tech_full_pack_20260605_aggregate_summary.md`
- `validation/runs/v3_tech_full_pack_20260605_calibration_review.md`
- `validation/runs/v3_tech_weak_watch_priority_review_20260605.md`
- `validation/runs/v3_nontech_master_watch_probe_20260605_20260211_summary.md`
- `validation/runs/v3_nontech_master_watch_probe_20260605_20260311_summary.md`
- `validation/runs/v3_nontech_master_watch_probe_20260605_multi_date_summary.md`
- `validation/runs/v3_nontech_master_watch_probe_20260605_review.md`
- `validation/runs/v3_usa_folder_nontech_watch_probe_20260605_20260211_summary.md`
- `validation/runs/v3_usa_folder_nontech_watch_probe_20260605_20260311_summary.md`
- `validation/runs/v3_usa_folder_nontech_watch_probe_20260605_multi_date_summary.md`
- `validation/runs/v3_usa_folder_nontech_watch_probe_20260605_review.md`

Per-date results:

| D date | Symbols processed | Symbols skipped | Candidates | Candidate density |
|---|---:|---:|---:|---:|
| 2026-02-11 | 512 | 13 | 354 | 0.6914 |
| 2026-03-11 | 514 | 11 | 354 | 0.6887 |
| 2026-04-11 | 514 | 11 | 450 | 0.8755 |

Aggregate candidate outcomes across 1,158 candidates:

| Horizon | Evaluated | Positive | Hit Rate | Average Return | Median Return |
|---|---:|---:|---:|---:|---:|
| D+1 | 1158 | 531 | 45.85% | 0.19% | -0.27% |
| D+2 | 1158 | 595 | 51.38% | 0.98% | 0.16% |
| D+5 | 1158 | 662 | 57.17% | 3.39% | 1.31% |
| D+10 | 1158 | 668 | 57.69% | 5.15% | 2.39% |
| D+20 | 1158 | 619 | 53.45% | 8.86% | 1.56% |

Candidate family mix:

| D date | CROSSOVER | MOMENTUM_SETUP | DIVERGENCE |
|---|---:|---:|---:|
| 2026-02-11 | 153 | 82 | 119 |
| 2026-03-11 | 104 | 83 | 167 |
| 2026-04-11 | 162 | 174 | 114 |

Diagnostic confirmation:

- all processed rows in all three detail CSVs include ranking diagnostics;
- all processed rows include traversal diagnostics;
- all processed rows include Divergence diagnostic fields;
- `MOMENTUM_SETUP` was blocked when stock baseline was bearish while bearish `CROSSOVER` remained available;
- `DIVERGENCE` meaningfully competed for the winning family, especially on 2026-03-11.

Initial calibration read:

- February and March Technology runs had high candidate density but weak forward outcomes.
- April Technology behavior was broadly strong and heavily lifted the aggregate result.
- Active-family collision buckets confirmed that ranking makes real choices among competing stage-family interpretations, not just cosmetic ordering.
- `WATCH` and `NEEDS_MANUAL_REVIEW` are not yet reliable weakness separators by themselves:
  - February `WATCH` D+20: 97 candidates, 40.21% hit rate, 1.36% average return.
  - March `WATCH` D+20: 197 candidates, 23.86% hit rate, -3.34% average return.
- The clearest weak-date discriminator is `WATCH + BELOW_EMA200`, especially bullish Divergence and Momentum Setup:
  - March `WATCH + BELOW_EMA200` D+20: 102 candidates, 10.78% hit rate, -8.89% average return.
  - March `DIVERGENCE + BULLISH_DIVERGENCE + BELOW_EMA200` D+20: 52 candidates, 11.54% hit rate, -6.64% average return.
  - March `MOMENTUM_SETUP + BULL_PULLBACK_REENTRY + BELOW_EMA200` D+20: 37 candidates, 10.81% hit rate, -12.60% average return.
- Automatic summary reporting now includes `Stage Family Outcomes`, `Risk Tag Outcomes`, and `Ranking Collision Buckets`.
- Larger non-Technology validation from `D:\Tools\StockCodeMaster\Script\NYSE_NASDAQ_Master_Library.csv` was run using a derived 5,535-row non-Technology common-stock universe:
  - derived file: `data/samples/us_non_technology_master_sample_20260605.csv`;
  - run label: `v3_nontech_master_watch_probe_20260605`;
  - sample size: 200, random seed: 20260605;
  - February processed 186 symbols, found 150 candidates;
  - March processed 186 symbols, found 126 candidates;
  - February `WATCH + BELOW_EMA200` D+20: 20 candidates, 25.00% hit rate, -8.29% average return;
  - March `WATCH + BELOW_EMA200` D+20: 17 candidates, 41.18% hit rate, -9.12% average return;
  - March `MOMENTUM_SETUP / BULL_PULLBACK_REENTRY + BELOW_EMA200` D+20: 6 candidates, 33.33% hit rate, -16.79% average return.
- USA-folder sector validation was run from `D:\Tools\StockCodeMaster\USA`:
  - derived file: `data/samples/us_usa_folder_nontech_sector_universe_20260605.csv`;
  - run label: `v3_usa_folder_nontech_watch_probe_20260605`;
  - source files: Basic Materials, Energy, Industrial, Misc, Telecom, and Utilities;
  - sample size: 200, random seed: 20260605;
  - February processed 191 symbols, found 163 candidates;
  - March processed 193 symbols, found 152 candidates;
  - February `WATCH + BELOW_EMA200` D+20: 11 candidates, 27.27% hit rate, -0.12% average return;
  - March `WATCH + BELOW_EMA200` D+20: 19 candidates, 57.89% hit rate, 5.88% average return;
  - this does not confirm generic March `WATCH + BELOW_EMA200` weakness for USA-folder sectors.
- This is a first promoted validation baseline, not a rule-tuning justification. More dates and sectors are required before changing thresholds.

Reporting smoke after the calibration review:

- command label: `v3_collision_report_smoke`
- sample: `data\samples\us_master_sample.csv`
- dates: `2026-02-11,2026-03-11`
- confirmed single-date summaries include `Stage Family Outcomes` and `Ranking Collision Buckets`;
- confirmed multi-date summary includes `Ranking Collision Buckets`.
- command label: `v3_risk_tag_report_smoke`
- confirmed single-date summaries include `Risk Tag Outcomes`.

Last verification before restart:

```text
python -m unittest discover -s tests -v
58 tests passing
```

## 2026-06-07 Sector-Folder Validation Checkpoint

Resumed from the 2026-06-05 handover and ran the recommended sector-by-sector validation packs from `D:\Tools\StockCodeMaster\USA`.

Validation command shape:

```powershell
$env:PYTHONPATH='D:\Tools\Stock_Screener_V3\src'
python -m stock_screener_v3.cli backtest-pack --workspace-root . --universe-file <sector-file> --d-dates 2026-02-11,2026-03-11,2026-04-11 --forward-days 1,2,5,10,20 --stage-family CROSSOVER,MOMENTUM_SETUP,DIVERGENCE --run-label <sector-label>
```

Sector files copied into `data/samples`:

- `00-NYSE_NASDAQ_Common_Stocks_Sector-BasicMaterials.csv`
- `00-NYSE_NASDAQ_Common_Stocks_Sector-Energy.csv`
- `00-NYSE_NASDAQ_Common_Stocks_Sector-Industrial.csv`
- `00-NYSE_NASDAQ_Common_Stocks_Sector-Misc.csv`
- `00-NYSE_NASDAQ_Common_Stocks_Sector-Telecom.csv`
- `00-NYSE_NASDAQ_Common_Stocks_Sector-Utilities.csv`
- `00-NYSE_NASDAQ_Common_Stocks_Sector-Technology-Semiconductor.csv`

New review artifact:

- `validation/runs/v3_sector_folder_validation_review_20260607.md`
- `validation/runs/v3_cross_sector_calibration_review_20260607.md`

Aggregate summaries:

- `validation/runs/v3_sector_basic_materials_pack_20260607_multi_date_summary.md`
- `validation/runs/v3_sector_energy_pack_20260607_multi_date_summary.md`
- `validation/runs/v3_sector_industrial_pack_20260607_multi_date_summary.md`
- `validation/runs/v3_sector_misc_pack_20260607_multi_date_summary.md`
- `validation/runs/v3_sector_telecom_pack_20260607_multi_date_summary.md`
- `validation/runs/v3_sector_utilities_pack_20260607_multi_date_summary.md`
- `validation/runs/v3_sector_technology_semiconductor_pack_20260607_multi_date_summary.md`

Candidate outcomes, where candidates mean `SELECTED` plus `WATCH`:

| Sector | Processed | Candidates | Density | D+20 Hit Rate | D+20 Average | D+20 Median |
|---|---:|---:|---:|---:|---:|---:|
| Basic Materials | 361 | 285 | 0.7895 | 32.98% | -3.23% | -4.49% |
| Energy | 402 | 358 | 0.8905 | 60.89% | 4.10% | 2.53% |
| Industrial | 1370 | 1140 | 0.8321 | 48.51% | 0.74% | -0.43% |
| Misc | 194 | 146 | 0.7526 | 41.10% | -1.83% | -3.08% |
| Telecom | 191 | 161 | 0.8429 | 50.31% | 3.64% | 0.01% |
| Utilities | 366 | 331 | 0.9044 | 52.87% | 0.66% | 0.49% |
| Technology Semiconductor | 255 | 189 | 0.7412 | 58.20% | 18.11% | 8.69% |

Calibration read:

- Candidate density remains high across all sector-folder packs.
- Basic Materials and Misc were weak at D+20.
- Energy and Technology Semiconductor were strongest at D+20, though Semiconductor was heavily lifted by April 2026.
- Industrial and Utilities were date-sensitive rather than uniformly strong or weak.
- `WATCH + BELOW_EMA200` did not reproduce as a generic weak filter in these sector-folder runs.
- Cross-sector review confirmed that date regime dominates several sectors and that family behavior is sector-specific.
- No scoring or threshold changes were made from this validation pass.

Follow-up symbol-level review:

- `validation/runs/v3_symbol_level_failure_review_20260607.md`
- Basic Materials Crossover D+20 remained weak:
  - 94 candidates, 21.28% hit rate, -7.79% average return, -8.20% median return;
  - weakness was concentrated in February and March;
  - `PRE_BEAR_CROSSOVER` was worse than `PRE_BULL_CROSSOVER`, which reinforces that bearish Crossover should be interpreted as exit/capital-preservation visibility, not bullish-entry quality.
- The Basic Materials sector file uses `Basic Materials`, but the default regime config only mapped `MATERIALS` to `XLB`.
- Added `BASIC MATERIALS -> XLB` to `RegimeBenchmarkConfig.default()` and added a regression test.
- Reran Basic Materials with run label `v3_sector_basic_materials_regime_alias_check_20260607`:
  - processed 361 rows across three dates;
  - found 285 candidates;
  - sector regimes changed from all `UNKNOWN` to 241 `BULLISH` and 120 `MIXED`;
  - candidate counts and outcomes were unchanged, confirming the Crossover weakness was not only a missing-sector-context artifact.
- Misc Divergence D+20 remained weak:
  - 52 candidates, 34.62% hit rate, -1.24% average return, -4.05% median return;
  - hidden and bullish variants were weaker, but more dates are needed before changing Divergence thresholds.

Bear Crossover drawdown review:

- `validation/runs/v3_basic_materials_bear_crossover_drawdown_review_20260607.md`
- Added path-aware forward validation detail columns:
  - `DPlus{N}WorstLowReturnPct`;
  - `DPlus{N}BestHighReturnPct`.
- These columns are additive and do not change existing endpoint-return summaries.
- Reran Basic Materials with run label `v3_basic_materials_path_metrics_20260607`.
- Basic Materials `PRE_BEAR_CROSSOVER` D+20 path result:
  - 50 candidates;
  - endpoint average -10.14%, endpoint median -10.86%;
  - worst-low average -23.00%, worst-low median -25.36%;
  - 86.00% had a D+20 worst-low drawdown of at least 10%.
- March 2026 `PRE_BEAR_CROSSOVER` was the clearest exit-review window:
  - 32 candidates;
  - D+20 worst-low average -26.00%;
  - D+20 worst-low median -27.22%.
- Interpretation: `PRE_BEAR_CROSSOVER` should remain visible as exit/capital-preservation review, not be scored as bullish-entry quality.

Path-metric reporting update:

- Single-date summaries now include:
  - `Stage Family Path Outcomes D+N`;
  - `Candidate State Path Outcomes D+N`.
- Multi-date summaries now include:
  - `Aggregate Forward Path Outcomes`;
  - `Stage Family Path Outcomes D+N`;
  - `Candidate State Path Outcomes D+N`.
- Regenerated `v3_basic_materials_path_metrics_20260607` markdown summaries to include the new path sections.
- The regenerated multi-date summary now exposes the Basic Materials `PRE_BEAR_CROSSOVER` D+20 path result directly:
  - 50 candidates;
  - average worst low -23.00%;
  - median worst low -25.36%;
  - average best high 7.21%;
  - median best high 2.17%.

Cross-sector Bear Crossover drawdown review:

- Completed in requested order: Technology, Industrial, Energy, Telecom, Utilities.
- Review artifact: `validation/runs/v3_cross_sector_bear_crossover_drawdown_review_20260607.md`.
- Run labels:
  - `v3_bear_crossover_path_technology_20260607`;
  - `v3_bear_crossover_path_industrial_20260607`;
  - `v3_bear_crossover_path_energy_20260607`;
  - `v3_bear_crossover_path_telecom_20260607`;
  - `v3_bear_crossover_path_telecom_alias_check_20260607`;
  - `v3_bear_crossover_path_utilities_20260607`.
- The Telecom sector file uses `Telecom`; added `TELECOM -> XLC` and `TELECOMMUNICATIONS -> XLC` aliases to `RegimeBenchmarkConfig.default()` and added a regression test.
- Aggregate `PRE_BEAR_CROSSOVER` D+20 worst-low medians:
  - Technology: -7.00%;
  - Industrial: -8.89%;
  - Energy: -8.63%;
  - Telecom: -6.29%;
  - Utilities: -5.26%.
- Aggregate `PRE_BEAR_CROSSOVER` D+20 worst-low <= -10% rates:
  - Technology: 39.72%;
  - Industrial: 44.83%;
  - Energy: 39.13%;
  - Telecom: 30.00%;
  - Utilities: 16.98%.
- Calibration read:
  - Technology and Industrial have the strongest broad evidence after Basic Materials;
  - Energy and Telecom are moderate;
  - Utilities is materially milder;
  - no review-priority threshold change was promoted from this pass.

Verification after restart:

```text
python -m unittest discover -s tests -v
61 tests passing
```

Live scanner UI intent split:

- Updated `web_app_v3.py` so submitted scan results include a `Review Split` panel.
- Added `ReviewIntent` to the candidate table.
- `PRE_BEAR_CROSSOVER` now renders as `Exit / preservation` with distinct row and chip styling.
- Bullish Crossover, bullish Divergence, and Momentum Setup candidates render as `Bullish entry / re-entry`.
- Bearish Divergence states render as `Bearish risk review`.
- Added renderer regression tests in `tests/test_web_app_v3.py`.
- Local HTTP smoke confirmed the scanner page still serves at `http://127.0.0.1:8010`.

Verification after UI intent split:

```text
$env:PYTHONPATH='D:\Tools\Stock_Screener_V3\src'
python -m unittest discover -s tests -v
63 tests passing
```

## What Is Not Yet Built

The actual V3 production engine logic is progressing stage family by stage family:

- Crossover V1 is complete and tested for the current engine scope.
- Crossover remains direction-aware for bull/bear transition:
  - `PRE_BULL_CROSSOVER` is new-capital entry review and requires a clean below-zero MACD/signal pair for bullish transition.
  - `PRE_BEAR_CROSSOVER` is exit/capital-preservation review and remains available in bearish baseline contexts.
  - future Crossover changes should be limited to review-priority/scoring calibration backed by backtest reports, not route-boundary rewrites.
- Momentum Setup v1 exists for bull pullback re-entry and bull continuation, but still needs calibration.
- Market/sector/stock regime determination v1 is complete for the current engine layer:
  - configurable benchmark mappings exist in `RegimeBenchmarkConfig`;
  - benchmark loading is wired through the backtest engine;
  - benchmark failures degrade to `UNKNOWN` instead of skipping the stock;
  - market, sector, and stock regimes are emitted in the output CSV.
- Remaining regime-engine expansion is configuration ergonomics and coverage, not core architecture:
  - user-editable mapping file or config loader;
  - broader NSE/BSE sector-index mapping;
  - theme benchmark mapping conventions;
  - calibrated regime thresholds after validation.
- Failure categories are first-pass diagnostics and still need validation against broader historical runs.
- Multi-date backtest pack exists, the first Technology full-universe validation baseline is documented, and the 2026-06-07 USA sector-folder validation baseline is documented.
- Divergence v1 is now part of the default holistic stage-family set, but swing geometry and thresholds still need historical calibration.
- No scoring calibration beyond data model contracts.
- Enriched NYSE/NASDAQ master universe CSV is not complete yet. This parallel WIP should populate universe filter/cache fields such as `CompanyName`, `MarketCap`, P/E fields, dividend dates, earnings date, beta, shares/float, and volume/profile metadata so scans can run on narrower symbol sets instead of always using `ALL_CODES`.
- V3 web app is operational for local scan execution, but deeper UI ergonomics can remain on hold while engine calibration proceeds.
- CLI exists for single-date backtest execution.

## Recommended Next Session Start

All three stage families are now V1 complete for the current engine scope. Move to integrated holistic validation and review-priority calibration, not UI expansion and not new indicator tuning.

Current traversal layer status:

- `StockTraversalPlan` exists in `src/stock_screener_v3/baseline_router.py`.
- `StageFamilyEvaluator` now builds a traversal plan before dispatching family evaluators.
- Current behavior is preserved:
  - all-bearish context blocks bullish entry;
  - all-bearish context blocks `MOMENTUM_SETUP`;
  - bearish `CROSSOVER` remains available for exit/capital-preservation review;
  - user-selected family restrictions and aliases are preserved;
- traversal diagnostics are emitted for selected, blocked, and `STATUS_QUO` outputs.
- ranking diagnostics are emitted on the winning reported row.
- default holistic traversal now evaluates `CROSSOVER`, `MOMENTUM_SETUP`, and `DIVERGENCE`.
- Smoke run `v3_traversal_plan_smoke` on 2026-02-11 processed 3 sample symbols, found 2 candidates, skipped 0 symbols, and emitted traversal diagnostics on selected and `STATUS_QUO` rows.
- Smoke run `v3_divergence_smoke` on 2026-02-11 used `--stage-family DIVERGENCE`, processed 3 sample symbols, found 0 candidates, skipped 0 symbols, and emitted Divergence diagnostics on `STATUS_QUO` rows.

Completed in the 2026-06-04 closure pass:

1. Defined the formal ranking contract beyond current best-`StageEvaluation` selection.
2. Added tests around ranking order, tie-break behavior, default Divergence dispatch, and bullish Divergence baseline blocking.
3. Included `DIVERGENCE` in the default holistic stage-family set after ranking diagnostics were explicit.

Recommended next implementation order:

1. Validate ranking collisions across the closed families:
   - `CROSSOVER`
   - `DIVERGENCE`
   - `MOMENTUM_SETUP`
2. Review review-priority calibration across sectors, D dates, stage families, and risk tags.
3. Decide whether a sector/date/context urgency layer is warranted.
4. Keep enriched universe metadata/filtering as the parallel data-quality track.
5. Do not change route boundaries without a new validation report.

Parallel WIP track:

1. Define the enriched NYSE/NASDAQ master universe CSV schema.
2. Add or revive the metadata enrichment workflow for company/profile/financial filter fields.
3. Add universe pre-filter support for predicates such as `TrailingPE < 25`, market-cap ranges, dividend yield, beta, average volume, sector, and industry.
4. Preserve enriched fields for filtering, output, and UI detail use without treating current profile metadata as historical signal truth.
5. Add loader/filter/output tests for required enriched metadata fields.

Current external code-list source rule:

- Use `D:\Tools\StockCodeMaster\USA` for sector-folder validation and sector-specific code lists.
- Use `D:\Tools\StockCodeMaster\Script\NYSE_NASDAQ_Master_Library.csv` when a broad all-sector NYSE/NASDAQ common-stock universe is required.
- The `USA` folder currently has full-schema sector files for Basic Materials, Energy, Industrial, Misc, Technology, Telecom, and Utilities, plus smaller symbol-only theme/subsector files.

## Carry-Forward Rules

- Do not hide technical signal validity because of quality/context concerns. Use `CandidateClass`, `ReviewPriority`, and risk tags instead.
- Do not tune a rule from one stock/event.
- Do not promote signal-rule changes without a backtest report.
- Preserve sector/exchange metadata from the input universe in output rows.
- Use enriched master-universe metadata for pre-scan filters before price loading and stage evaluation.
- Prefer enriched master-universe metadata for UI detail panes before making live profile calls.
- Accept mixed-market CSV inputs with NSE, BSE, NYSE, and NASDAQ codes.
- Normalize NSE symbols to `.NS` and BSE symbols to `.BO`; keep NYSE/NASDAQ unsuffixed unless `YahooSymbol` is provided.
- Preserve V2-compatible offline CSV headers.
- Keep log, output CSV, and summary report separate.
- Keep the handover document updated after every meaningful change.

## 2026-06-11 Continuation Update

MKTW zero-line status:

- Confirmed the mixed zero-line MKTW case is already covered by production evaluator logic and regression coverage.
- `PRE_BULL_CROSSOVER` now requires both `MACD_1D_Value <= 0` and `MACD_1D_Signal <= 0`.
- `test_crossover_does_not_classify_mixed_zero_line_pair_as_near_bull` remains green and verifies that the MKTW-style `MACD < 0 / Signal > 0` pair resolves to `STATUS_QUO`.

Forward execution completed from the pending handover item:

- Added reusable generated calibration report support in `src/stock_screener_v3/reports.py`.
- Added CLI commands in `src/stock_screener_v3/cli.py`:
  - `cross-sector-report`
  - `symbol-failure-report`
- Added regression tests in `tests/test_reports.py` for both generated report paths.
- Generated artifacts:
  - `validation/runs/v3_generated_cross_sector_bear_crossover_report_20260611.md`
  - `validation/runs/v3_generated_symbol_failure_report_20260611.md`

Generated cross-sector report baseline:

- Input: 15 existing D+20 bear-crossover detail files across Technology, Industrial, Energy, Telecom alias-check, and Utilities.
- Candidate filter: `PRE_BEAR_CROSSOVER`.
- Candidate rows: 725.
- Sector path outcomes reproduce the earlier manual calibration shape:
  - Technology: 360 candidates, D+20 median worst low -7.00%.
  - Industrials: 203 candidates, D+20 median worst low -8.89%.
  - Energy: 69 candidates, D+20 median worst low -8.63%.
  - Telecommunications: 40 candidates, D+20 median worst low -6.29%.
  - Utilities: 53 candidates, D+20 median worst low -5.26%.

Verification:

```text
$env:PYTHONPATH='D:\Tools\Stock_Screener_V3\src'
python -m unittest discover -s tests -v
70 tests OK
```

Current Crossover closure:

- Crossover family status: V1 complete and tested for current engine scope.
- Full test suite status: `70 tests OK`.
- Documentation updated in README and `docs/architecture/v3_evidence_stage_matrix.md`.
- Generated report commands are available for future calibration checks:
  - `cross-sector-report`
  - `symbol-failure-report`

Next recommended work:

1. Generate an integrated ranking/review-priority calibration report from the same path-enabled multi-date sector detail CSVs.
2. Compare winning family outcomes against `RankingCandidateStates` collision buckets.
3. Review weak slices already identified:
   - Momentum Setup / Industrials / February-March.
   - Divergence / `BULLISH_DIVERGENCE`.
   - Bear Crossover sector urgency differences.
4. Continue calibration review before introducing any new signal threshold changes.

## 2026-06-11 Divergence Closure Update

Divergence status:

- `DIVERGENCE` is V1 complete and tested for the current engine scope.
- Route states covered:
  - `BULLISH_DIVERGENCE`
  - `BEARISH_DIVERGENCE`
  - `HIDDEN_BULLISH_DIVERGENCE`
  - `HIDDEN_BEARISH_DIVERGENCE`
- Generated report support now includes generic `stage-family-report`.
- Validation artifacts:
  - `validation/runs/v3_divergence_stage_family_calibration_20260611.md`
  - `validation/runs/v3_divergence_path_enabled_calibration_20260611.md`
  - `validation/runs/v3_divergence_family_v1_completion_20260611.md`

Path-enabled baseline:

- Input: 15 existing D+20 path-enabled sector detail files across Technology, Industrial, Energy, Telecom alias-check, and Utilities.
- Candidate rows: 962.
- `BULLISH_DIVERGENCE` is the weakest current Divergence slice:
  - 211 candidates;
  - 44.08% D+20 endpoint hit rate;
  - -1.45% median D+20 endpoint;
  - -11.13% median D+20 worst low.
- No Divergence route-boundary change is promoted from this pass.

Verification after Divergence closure:

```text
$env:PYTHONPATH='D:\Tools\Stock_Screener_V3\src'
python -m unittest discover -s tests -v
72 tests OK
```

## 2026-06-11 Momentum Setup Closure Update

Momentum Setup status:

- `MOMENTUM_SETUP` is V1 complete and tested for the current engine scope.
- Route states covered:
  - `BULL_PULLBACK_REENTRY`
  - `BULL_CONTINUATION_MOMENTUM`
- Opportunity subtypes covered:
  - `BULLISH_PULLBACK_REENTRY`
  - `BULLISH_CONTINUATION_MOMENTUM`
  - `BULLISH_MOMENTUM_EXPANSION`
- Generated report support now includes filtered `symbol-failure-report`.
- Validation artifacts:
  - `validation/runs/v3_momentum_setup_stage_family_calibration_20260611.md`
  - `validation/runs/v3_momentum_setup_symbol_failure_report_20260611.md`
  - `validation/runs/v3_momentum_setup_family_v1_completion_20260611.md`

Path-enabled baseline:

- Input: 15 existing D+20 path-enabled sector detail files across Technology, Industrial, Energy, Telecom alias-check, and Utilities.
- Candidate rows: 1,279.
- `BULL_PULLBACK_REENTRY`: 1,246 candidates, 49.28% hit rate, -0.39% median endpoint, -7.36% median worst low.
- `BULL_CONTINUATION_MOMENTUM`: 33 candidates, 51.52% hit rate, 0.36% median endpoint, -6.01% median worst low.
- Weaker slices:
  - Industrials: 39.79% hit rate, -3.75% median endpoint.
  - February 2026: 34.46% hit rate, -6.06% median endpoint.
- No Momentum Setup route-boundary change is promoted from this pass.

Verification after Momentum Setup closure:

```text
$env:PYTHONPATH='D:\Tools\Stock_Screener_V3\src'
python -m unittest discover -s tests -v
73 tests OK
```

## 2026-06-11 Integrated Holistic Validation Update

Integrated validation status:

- Added repeatable CLI support:
  - `integrated-report`
- Generated validation artifact:
  - `validation/runs/v3_integrated_holistic_calibration_20260611.md`
- Input: 15 existing D+20 path-enabled sector detail files across Technology, Industrial, Energy, Telecom alias-check, and Utilities.
- Candidate rows: 3,144 selected/watch rows.

Stage-family baseline:

- `CROSSOVER`: 903 candidates, 55.37% D+20 hit rate, 2.00% median endpoint.
- `DIVERGENCE`: 962 candidates, 53.33% D+20 hit rate, 0.97% median endpoint.
- `MOMENTUM_SETUP`: 1,279 candidates, 49.34% D+20 hit rate, -0.39% median endpoint.

Ranking collision baseline:

- `CROSSOVER`: 675 candidates, 54.96% hit rate, 1.91% median endpoint.
- `CROSSOVER+DIVERGENCE`: 765 candidates, 55.95% hit rate, 1.59% median endpoint.
- `CROSSOVER+DIVERGENCE+MOMENTUM_SETUP`: 520 candidates, 53.46% hit rate, 1.09% median endpoint.
- `CROSSOVER+MOMENTUM_SETUP`: 626 candidates, 53.04% hit rate, 1.11% median endpoint.
- Weak collision buckets:
  - `MOMENTUM_SETUP`: 198 candidates, 32.32% hit rate, -4.64% median endpoint.
  - `DIVERGENCE+MOMENTUM_SETUP`: 126 candidates, 39.68% hit rate, -2.64% median endpoint.

Review-priority/risk baseline:

- `A`: 1,999 candidates, 53.28% hit rate, 1.37% median endpoint.
- `B`: 489 candidates, 54.81% hit rate, 1.25% median endpoint.
- `NEEDS_MANUAL_REVIEW`: 656 candidates, 47.41% hit rate, -0.42% median endpoint.
- `BELOW_EMA200`: 385 candidates, 42.08% hit rate, -2.34% median endpoint.

Verification after integrated validation:

```text
$env:PYTHONPATH='D:\Tools\Stock_Screener_V3\src'
python -m unittest discover -s tests -v
74 tests OK
```

Recommended next session start:

1. Start from `validation/runs/v3_integrated_holistic_calibration_20260611.md`.
2. Calibrate the weak ranking buckets before introducing new signal thresholds:
   - `MOMENTUM_SETUP`
   - `DIVERGENCE+MOMENTUM_SETUP`
3. Split those buckets by sector/date and inspect whether weakness is driven by:
   - `NEEDS_MANUAL_REVIEW`;
   - `BELOW_EMA200`;
   - February-March Industrials;
   - standalone Momentum Setup candidates.
4. Decide whether review-priority or context urgency should be adjusted before any family route-boundary change.

## 2026-06-11 Divergence Path-Forward Implementation Update

Correction to execution path:

- The next required work was not just another report; Divergence needed a concrete path-forward calibration rule from the validated weak slices.
- Implemented rule: raw/unconfirmed bullish Divergence below EMA200 is no longer promoted into the normal `WATCH` path.
- The signal remains auditable as its Divergence candidate state, but is emitted as `REJECTED` with:
  - `BELOW_EMA200`
  - `RAW_BULLISH_DIVERGENCE_BELOW_EMA200`
- Confirmed bullish Divergence below EMA200 remains eligible for `WATCH` with `NEEDS_MANUAL_REVIEW`.

Files changed:

- `src/stock_screener_v3/evaluators.py`
- `tests/test_evaluators.py`
- `docs/architecture/v3_divergence_contract.md`

Verification:

```text
$env:PYTHONPATH='D:\Tools\Stock_Screener_V3\src'
python -m unittest discover -s tests -v
76 tests OK
```

Next exact path:

1. Quantify this Divergence path-forward rule by rerunning the path-enabled sector validation packs and comparing candidate counts for:
   - `BULLISH_DIVERGENCE`
   - `HIDDEN_BULLISH_DIVERGENCE`
   - `BELOW_EMA200`
   - `RAW_BULLISH_DIVERGENCE_BELOW_EMA200`
2. Then move to the analogous Momentum Setup action item:
   - `BULL_PULLBACK_REENTRY`
   - `BELOW_EMA200`
   - weak February-March Industrials
3. Do not add more reporting before completing the Momentum Setup evaluator path-forward rule.

## 2026-06-11 Divergence Rule Backtest Update

Comprehensive backtest completed after the raw bullish Divergence below-EMA200 rule.

Executed:

- Full unit/regression suite:
  - `python -m unittest discover -s tests -v`
  - `76 tests OK`
- 15 fresh post-rule backtests:
  - Technology, Industrial, Energy, Telecom, Utilities.
  - 2026-02-11, 2026-03-11, 2026-04-11.
  - Horizons: D+1, D+2, D+5, D+10, D+20.

Validation artifacts:

- `validation/runs/v3_divergence_rule_backtest_review_20260611.md`
- `validation/runs/v3_divergence_rule_stage_family_calibration_20260611.md`
- `validation/runs/v3_divergence_rule_integrated_calibration_20260611.md`

Backtest read:

- Before-rule selected/watch candidate baseline: 3,144.
- Post-rule selected/watch candidates: 3,056.
- Rows directly rejected by `RAW_BULLISH_DIVERGENCE_BELOW_EMA200`: 33.
- Those 33 rows were mixed overall:
  - 54.55% D+20 hit rate;
  - 0.25% median D+20 endpoint;
  - -7.55% median D+20 worst low.
- The weak concentration remains date/sector-specific:
  - Technology March 2026: 7 rows, 14.29% hit rate, -2.92% median endpoint.
  - Telecom March 2026: 3 rows, 0.00% hit rate, -0.23% median endpoint.

Decision:

- Keep the Divergence rule as a conservative risk-separation guardrail.
- Do not add further Divergence tightening from this evidence alone.
- Move implementation focus to the Momentum Setup path-forward rule:
  - `BULL_PULLBACK_REENTRY`
  - `BELOW_EMA200`
  - weak February-March Industrials

## 2026-06-12 Momentum Setup Path-Forward Implementation Update

Implemented the Momentum Setup risk-separation rule called out by the June 11 calibration handover.

Rule:

- `BULL_PULLBACK_REENTRY` below EMA200 is no longer promoted into the normal selected/watch path.
- The route remains auditable as `BULL_PULLBACK_REENTRY`.
- It is emitted as `REJECTED` with:
  - `BELOW_EMA200`;
  - `PULLBACK_REENTRY_BELOW_EMA200`;
  - `MomentumSetupContextRule = PULLBACK_REENTRY_BELOW_EMA200`;
  - `MomentumSetupContextAction = REJECT`.

Files changed:

- `src/stock_screener_v3/evaluators.py`
- `src/stock_screener_v3/output_contracts.py`
- `tests/test_evaluators.py`
- `docs/architecture/v3_evidence_stage_matrix.md`

Verification:

```text
$env:PYTHONPATH='D:\Tools\Stock_Screener_V3\src'
python -m unittest discover -s tests -v
77 tests OK
```

## 2026-06-13 Momentum Setup Rule Backtest Update

Completed the post-rule sector/date validation for:

- Technology;
- Industrial;
- Energy;
- Telecom;
- Utilities.

Dates:

- 2026-02-11;
- 2026-03-11;
- 2026-04-11.

Validation artifacts:

- `validation/runs/v3_momentum_pullback_rule_validation_review_20260612.md`
- `validation/runs/v3_momentum_pullback_rule_stage_family_calibration_20260612.md`
- `validation/runs/v3_momentum_pullback_rule_integrated_calibration_20260612.md`
- `validation/runs/v3_momentum_pullback_rule_symbol_failure_20260612.md`

Data availability note:

- Utilities 2026-03-11 and 2026-04-11 processed zero rows because the live Yahoo provider returned no daily data for the sector file during this run.
- Rule-impact interpretation uses the comparable core set: Technology, Industrial, Energy, and Telecom.

Comparable core before/after:

- Before-rule processed rows: 3,503.
- After-rule processed rows: 3,503.
- Selected/watch candidates fell from 2,737 to 2,602.
- Momentum Setup selected/watch rows fell from 1,131 to 974.
- `BULL_PULLBACK_REENTRY + BELOW_EMA200` selected/watch rows fell from 157 to 0.
- Rule-rejected rows after implementation: 154.

Industrial February-March focus:

- Before: 701 selected/watch candidates; 297 Momentum Setup; 30 pullback re-entry below EMA200.
- After: 674 selected/watch candidates; 267 Momentum Setup; 27 rule-rejected rows.
- Before Industrial February-March Momentum Setup D+20:
  - 297 rows;
  - 19.53% hit rate;
  - -7.93% average;
  - -10.48% median;
  - -15.01% median worst low.
- After Industrial February-March Momentum Setup D+20:
  - 267 rows;
  - 19.48% hit rate;
  - -8.37% average;
  - -10.80% median;
  - -14.97% median worst low.

Decision:

- Keep `PULLBACK_REENTRY_BELOW_EMA200` as a broad conservative risk-separation guardrail.
- Do not add another Momentum Setup threshold change yet.
- The remaining weak area is high-score Industrial February-March `BULL_PULLBACK_REENTRY` without `BELOW_EMA200`.

Next exact path:

1. Inspect remaining Industrial February-March Momentum Setup failures, especially high-score `BULL_PULLBACK_REENTRY` rows without `BELOW_EMA200`.
2. Split those failures by confirmation components:
   - `BULL_PHASE_STRUCTURE_SUPPORT`;
   - `PARTICIPATION_SUPPORT`;
   - `ACCEPTANCE_SUPPORT`;
   - `ReviewPriority`;
   - ranking collision bucket.
3. Only then decide whether a second Momentum Setup calibration rule is justified.

## 2026-06-13 Industrial Momentum Remaining Failure Review

Completed the focused review of remaining Industrial February-March Momentum Setup failures after the `PULLBACK_REENTRY_BELOW_EMA200` rule.

Review artifact:

- `validation/runs/v3_industrial_momentum_remaining_failure_review_20260613.md`

Scope:

- Industrial only.
- D dates:
  - 2026-02-11;
  - 2026-03-11.
- `StageFamily = MOMENTUM_SETUP`.
- `CandidateStateRaw = BULL_PULLBACK_REENTRY`.
- `CandidateClass in SELECTED,WATCH`.
- Excludes `BELOW_EMA200`.

Readout:

- Focus rows: 260.
- D+20 hit rate: 19.23%.
- D+20 average endpoint: -8.46%.
- D+20 median endpoint: -10.87%.
- D+20 median worst low: -15.03%.
- High-score rows with `TotalScore >= 85`: 165.
- High-score failed rows: 127.

Component split:

- `BULL_PHASE_STRUCTURE_SUPPORT`: 104 rows, 16.35% hit rate, -10.95% median endpoint.
- `BULL_PHASE_STRUCTURE_SUPPORT+PARTICIPATION_SUPPORT`: 98 rows, 18.37% hit rate, -10.28% median endpoint.
- `BULL_PHASE_STRUCTURE_SUPPORT+PARTICIPATION_SUPPORT+ACCEPTANCE_SUPPORT`: 21 rows, 19.05% hit rate, -13.49% median endpoint.
- `BULL_PHASE_STRUCTURE_SUPPORT+ACCEPTANCE_SUPPORT`: 26 rows, 23.08% hit rate, -14.49% median endpoint.

Decision:

- Do not introduce a second hard Momentum Setup suppression rule from this split alone.
- The weakness is not isolated to missing confirmation; even rows with participation and acceptance support remain weak.
- High score and ReviewPriority do not separate the failure mode cleanly.
- The next safer implementation path is broader date/regime context or a reportable caution diagnostic, validated on more dates before suppressing additional candidates.

Next exact path:

1. Add broader date/regime context to calibration reporting before changing evaluator thresholds again.
2. Review whether February 2026 Industrial weakness coincides with market/sector regime deterioration, ranking collision patterns, or cross-family bearish warnings.
3. If a diagnostic is added, keep it report-only first; do not demote more Momentum Setup candidates until validated across more dates.
