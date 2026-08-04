# V3_Charter Execution Plan

Last updated: 2026-06-19

Repo root: `D:\Tools\Stock_Screener_V3`

Branch: `V3_Charter`

GitHub: `https://github.com/gigabouy2004-afk/Stock_Screener_V3.git`

## Purpose

This document is the working execution plan for building the V3 engine from the consolidated charter and the stage-family indicator matrix.

It is not a replacement for the charter or the matrix. It is the planning layer that keeps matrix finalization, implementation, validation, handover, README updates, and GitHub synchronization aligned with the original engine intent.

Every future implementation session should start by reviewing:

1. the original plan and charter contract;
2. the stage-family indicator matrix and its current finalization status;
3. what has already been achieved;
4. what remains to be built;
5. the next approved execution step.

## Source Of Truth

The source documents are:

- `docs/charter/v3_charter_consolidated_engine_design.md`
- `docs/charter/v3_original_intent_and_handover.md`
- `docs/architecture/v3_stage_family_indicator_working_matrix.md`
- `docs/handover/current_session_handover.md`

The active implementation root is:

```text
D:\Tools\Stock_Screener_V3
```

The active Git branch is:

```text
V3_Charter
```

All project code, documentation, tests, validation artifacts, reports, and handover updates must be created or modified inside this root and on this branch.

External stock-code master folders may be used as read-only input sources only. They are not implementation roots and must not receive V3 engine updates.

## Core Build Control: The Matrix

The stage-family indicator matrix is the core construction artifact for the engine:

```text
docs/architecture/v3_stage_family_indicator_working_matrix.md
```

The charter defines why the engine exists and what boundaries it must obey. The matrix defines what the engine actually computes.

The matrix must be finalized before additional algorithm coding begins. Coding directly from memory, V2 fragments, old scripts, or evaluator convenience is not allowed.

Each matrix row must define:

- the indicator or evidence family;
- the provider/API input required;
- the V3 level that owns it;
- the meaning under `CROSSOVER`;
- the meaning under `DIVERGENCE`;
- the meaning under `SETUP`;
- whether the row is route, timing, quality, context, scoring, audit, or validation;
- the D / D+X validation role;
- the primary output fields;
- inclusion rules;
- exclusion rules;
- guardrails that prevent the row from overriding another path.

The matrix is not a list of indicators to calculate globally. It is the path-specific contract for when an indicator is allowed to matter and what it is allowed to mean.

Examples:

- `MACD` in `CROSSOVER` is transition route/timing evidence.
- `MACD` in `DIVERGENCE` is price-versus-momentum disagreement evidence.
- `MACD` in `SETUP` supports continuation or pullback re-entry logic.
- `EMA200` may be risk/context/headroom evidence, but it is not a universal hard route gate unless the matrix explicitly says so.

## Matrix Finalization Objective

The first objective is to have the actual plan ready with the matrix as its core.

Before further coding, the project must produce a matrix-finalization pass that answers:

- Are all required V2/V3 indicator families represented as rows?
- Does every row have explicit path-specific meaning for `CROSSOVER`, `DIVERGENCE`, and `SETUP`?
- Does every row state its required input data?
- Does every row state its output fields?
- Does every row state inclusion and exclusion behavior?
- Does every row state whether it is route, timing, quality, context, scoring, audit, or validation?
- Does every row state what it must not override?
- Does every row state whether it is approved for current implementation, future implementation, or still TBD?

Rows with unclear meaning must remain `TBD` and must not be implemented.

Rows approved for implementation must be precise enough that a developer can map them to code without reinterpreting the charter.

## Original Engine Plan

V3 is a CSV-based, user-directed equity screening engine.

The engine answers one focused question:

```text
From the user-supplied equity universe, which tickers currently qualify for the selected technical opportunity family, and why?
```

The engine has exactly three user-facing paths:

- `CROSSOVER`
- `DIVERGENCE`
- `SETUP`

No fourth user-facing path is allowed unless the charter is explicitly revised.

Business meaning:

- `CROSSOVER` contains `PRE_BULL_CROSSOVER` for early bull-phase entry review and `PRE_BEAR_CROSSOVER` for capital-preservation review on existing long-held equities.
- `DIVERGENCE` validates whether a credible investment opportunity may be developing through disagreement between price and momentum behavior.
- `SETUP` is a pure-play market-based entry path for continuation, pullback re-entry, recovery, or extension behavior inside an existing or developing bull structure.

The engine is not:

- an automated trading system;
- a portfolio-management system;
- a stop-loss engine;
- a position-sizing engine;
- a broad hidden market scanner;
- a sector-calibration platform by default.

## Execution Principles

Implementation must preserve these principles:

- The user-supplied CSV is the universe.
- User-selected paths control which evaluators may run.
- Filters are first-class inputs before candidate display.
- Provider data is fetched only as required by the selected path and evidence rows.
- Matrix row approval is required before an indicator/evidence behavior is implemented.
- D-date computation must be isolated from D+X validation data.
- Route logic comes before scoring.
- Score is family-specific and post-qualification.
- Market and sector context are audit/context rows with zero default scoring weight unless the charter is revised.
- Every pass, rejection, skipped symbol, and provider failure must be auditable.
- No signal-rule change is promoted without validation evidence.

## Conceptual Execution Flow

The V3 engine executes as one cohesive pipeline:

```text
CSV input
-> selected path/family restrictions
-> metadata and filter qualification
-> provider symbol resolution
-> API/provider data retrieval
-> D-date slicing when historical
-> L1 baseline facts
-> L2 route eligibility
-> L3 path-specific evidence
-> L4 classification, scoring, and reason codes
-> L5 output, audit, and D+X validation
```

The web UI, CLI, backtesting, reports, and future automation must all call the same engine path. They must not create parallel engines.

The execution flow is subordinate to the matrix. Each L1-L5 computation must trace back to an approved matrix row or to core engine infrastructure such as input loading, provider access, logging, or report writing.

## Filtering Logic

Filtering is an engine-level contract, not just display behavior.

Filter sources:

- CSV metadata supplied by the user;
- enriched master stock-code data when used as read-only input;
- provider/profile cache only when explicitly supported;
- run parameters from CLI or UI.

Filter examples:

- exchange;
- sector;
- industry;
- instrument type;
- market cap;
- average daily volume;
- average monthly volume;
- user-selected code list.

Filter order:

1. Load and normalize CSV records.
2. Preserve all supplied metadata.
3. Apply metadata filters before price loading where possible.
4. Resolve provider symbols for remaining records.
5. Record filtered-out rows or counts in audit output where the run contract requires it.
6. Run technical evaluation only for filter-qualified records.

Filtering must not:

- silently expand the universe;
- convert a non-qualifying symbol into a candidate;
- hide the fact that a symbol was skipped or filtered;
- use future or unstable metadata in historical D-date mode unless a point-in-time snapshot exists.

## Computation Phases

### L0: Input, Data, And Date Preparation

Deliverables:

- CSV loader and symbol normalizer.
- Metadata-preserving universe records.
- Workspace-safe path handling.
- Provider abstraction.
- D-date and D+X run configuration.
- Deep-copy active computation slice through D.
- Separate forward-validation data zone after D.
- Per-symbol provider failure capture.

Current status:

- Mostly implemented in package foundation.
- D-date slicing helpers and provider abstraction exist.
- Deep-copy/no-lookahead behavior must continue to be hardened as accepted seed logic is integrated.

### L1: Baseline

Deliverables:

- Neutral technical facts for each symbol.
- MACD state.
- moving-average context.
- structure context.
- volume/liquidity context where needed.
- market/sector context as audit/context only.

Current status:

- Baseline evidence builder and router exist.
- Market/sector regime diagnostics exist, but must remain bounded and non-routing except where explicitly approved by charter guardrails.

### L2: Route

Deliverables:

- Route-isolated family eligibility.
- Strict enforcement of selected families.
- No fallback from one family into another unselected family.
- Explicit route diagnostics.

Current status:

- Stage-family dispatcher and traversal plan exist.
- Crossover, Divergence, and Momentum Setup evaluator paths exist.
- User-facing naming must remain aligned to charter: `SETUP` is the external path, even if internal code still contains `MOMENTUM_SETUP` compatibility names.

### L3: Path-Specific Evidence

Deliverables:

- Indicator-family rows finalized in the working matrix before implementation.
- Matrix-to-code traceability for every implemented evidence row.
- Path-specific evidence packaging.
- Provider-backed calculations.
- Lower-timeframe evidence nested under daily route only.
- `4H` and `1H` MACD initially restricted to `CROSSOVER`.
- Long-boundary calculations such as `EMA52High` and `EMA200High` implemented with approved definitions.

Current status:

- Daily MACD/RSI/ADX/EMA/volume/structure evidence exists.
- Divergence and Setup evidence slices exist.
- Remaining matrix rows must be finalized before coding.
- Existing implemented rows still need a formal matrix-to-code assessment.

### L4: Classification, Scoring, And Interpretation

Deliverables:

- Candidate state.
- Candidate class.
- Review priority.
- Confidence.
- Family-specific weighted score.
- Reason codes.
- Risk tags.
- Rejection diagnostics.
- Scoring defaults owned by config or manifest rather than hidden evaluator literals.

Current status:

- Crossover, Divergence, and Setup-family scoring exists.
- Selected/watch thresholds exist.
- Recent work moved more scoring constants into `scoring_config.py`.
- Long-term target remains a declarative scoring manifest such as `config/scoring_manifest.json`.

### L5: Output, Audit, And Validation

Deliverables:

- V2-compatible detail CSV.
- Summary markdown.
- Run log.
- Candidate density.
- Score-bucket behavior.
- Failure categories.
- D+1, D+2, D+5 and optional longer horizon validation.
- Candidate-only and all-row audit visibility as appropriate.
- Repeatable calibration reports.
- Regression datasets and test matrix under `tests/regression/`.

Current status:

- Detail CSV, summary markdown, run logging, report generation, and backtest summaries exist.
- Multi-date pack support exists.
- Regression gate and manifest-driven validation still need full build-out.

## Deliverables

### Documentation Deliverables

- Consolidated charter kept as the master design source.
- Stage-family indicator working matrix finalized before further algorithm implementation.
- Matrix rows maintained as the primary inclusion/exclusion contract for indicators and evidence.
- Execution plan kept current after meaningful implementation changes.
- README restart path points to the execution plan and charter.
- Handover documents start from original plan review, achieved state, and next work.
- Working matrix updated and signed off before indicator behavior is implemented.
- Matrix-to-code implementation assessment maintained as the bridge from plan to package.
- Validation artifacts stored under `validation/`.

### Code Deliverables

- Package implementation under `src/stock_screener_v3`.
- Active web UI surface in `web_app_v3.py`.
- CLI entry points for scan/backtest/report flows.
- Provider abstraction with Yahoo Finance as current default.
- Config/manifest layer for scoring and thresholds.
- Path-isolated evaluators for `CROSSOVER`, `DIVERGENCE`, and `SETUP`.
- Shared runner path used by UI, CLI, and validation.

### Test Deliverables

- Unit tests for universe loading, filtering, provider normalization, evidence, evaluators, routing, reports, run I/O, and runner behavior.
- No-lookahead D-date slicing tests.
- Route-isolation tests.
- Regression datasets and test-matrix gate for accepted historical scenarios.
- Tests for manifest/config defaults and drift tolerance.

### Validation Deliverables

- Single-date backtest summaries.
- Multi-date pack summaries.
- Family-specific calibration reports.
- Integrated ranking/review-priority reports.
- Symbol failure reports.
- Rule-change before/after validation reports.

### Sync Deliverables

- Local `D:\Tools\Stock_Screener_V3` and GitHub `origin/V3_Charter` stay synchronized after each completed step.
- `git status --short --branch` should return a clean `V3_Charter...origin/V3_Charter` state after committed/pushed milestones.
- Any deliberate uncommitted work must be called out in the handover before pausing.

## Achieved State

The current package already includes:

- Python package skeleton under `src/stock_screener_v3`.
- CSV universe loading with metadata preservation.
- Mixed NSE/BSE/NYSE/NASDAQ symbol handling.
- Deterministic sampling and sector/exchange filters.
- Provider abstraction and Yahoo Finance wrapper.
- Historical slicing helpers.
- Backtest engine and forward-return helpers.
- Detail CSV and summary markdown writers.
- Run I/O helpers and logging.
- V2-compatible output header ordering.
- Evidence builder for daily MACD, RSI, ADX, EMA, volume, and price structure.
- Crossover evaluator for bull and bear transition routes.
- Divergence evaluator for regular and hidden bullish/bearish routes.
- Setup-family evaluator for pullback re-entry and continuation routes.
- Stage-family traversal and ranking diagnostics.
- Baseline router and regime diagnostics.
- CLI and reusable runner.
- `web_app_v3.py` scanner console.
- Calibration and generated report commands.
- Unit test suite with current passing baseline.

Recent local implementation work:

- Scoring defaults and evaluator constants have been moved further into `src/stock_screener_v3/scoring_config.py`.
- `src/stock_screener_v3/evaluators.py` now reads those constants from config.
- Verification for that step: `78 tests OK`.

## Remaining Work

Priority order:

1. Finalize the stage-family indicator matrix as the core build-control artifact.
2. Produce a matrix-to-code implementation assessment, not a generic gap table.
3. Classify each matrix row as implemented, partial, missing, naming-misaligned, validation-needed, not yet manifest/config-owned, future/TBD, or blocked.
4. Normalize user-facing `SETUP` naming across UI, CLI, reports, docs, and internals where safe, preserving compatibility where needed.
5. Build or expand the manifest/config layer so scoring defaults are declarative and versioned.
6. Integrate approved L0 deep-copy slicing and D-vs-D+X isolation rules throughout provider/execution paths.
7. Implement approved long-boundary calculations, including `EMA52High` and `EMA200High`, in package indicator code.
8. Add regression dataset layout and acceptance test matrix under `tests/regression/`.
9. Add manifest drift-tolerance and regression-gate tests.
10. Continue matrix-approved evidence rows only after their condition logic is signed off.
11. Validate each signal-rule change with before/after backtest evidence before promotion.
12. Keep web UI, CLI, reports, and validation on the same runner path.

## Session Execution Process

Every future work session should follow this sequence:

1. Verify root and branch:

```powershell
cd D:\Tools\Stock_Screener_V3
git status --short --branch
git log --oneline --decorate -8
```

2. Read the restart docs in this order:

- `docs/charter/v3_charter_execution_plan.md`
- `docs/charter/v3_charter_consolidated_engine_design.md`
- `docs/architecture/v3_stage_family_indicator_working_matrix.md`
- `docs/handover/current_session_handover.md`
- `README.md`

3. State the current matrix status, achieved state, and next intended step before editing code.

4. If the step changes indicator behavior, route behavior, scoring behavior, inclusion/exclusion behavior, or output evidence, update/finalize the working matrix first.

5. Make scoped code/doc changes only under `D:\Tools\Stock_Screener_V3`.

6. Run the appropriate tests.

7. Update handover and README if the achieved state or next step changed.

8. Commit and push to `origin/V3_Charter` after the step is complete.

9. End with local and GitHub in sync, or explicitly state why sync is blocked.

## Current Next Step

The next step is documentation and analysis, not algorithm coding:

```text
Finalize the stage-family indicator matrix and produce a matrix-to-code implementation assessment before additional engine behavior changes.
```

The assessment should include:

- matrix row;
- required input;
- V3 level;
- `CROSSOVER` meaning;
- `DIVERGENCE` meaning;
- `SETUP` meaning;
- inclusion rule;
- exclusion rule;
- primary outputs;
- current code location;
- test coverage;
- validation coverage;
- status;
- required action.

No additional algorithm coding should start until this matrix-first assessment is available.
