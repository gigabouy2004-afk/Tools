# Stock Screener V3_Charter

This repository is the active `V3_Charter` workspace for the stock screener engine.

It exists to keep the new program charter, architecture analysis, backtesting plan, implementation work, and validation evidence in one Git-tracked folder.

## Intent

Canonical `V3_Charter` intent is recorded in [docs/charter/v3_original_intent_and_handover.md](docs/charter/v3_original_intent_and_handover.md). The standalone consolidated charter is [docs/charter/v3_charter_consolidated_engine_design.md](docs/charter/v3_charter_consolidated_engine_design.md) and should be used as the single offline master document for full engine intent, matrix, interpretation, and scoring behavior.

The working execution plan is [docs/charter/v3_charter_execution_plan.md](docs/charter/v3_charter_execution_plan.md). Use it at the start of every implementation session to review the original plan, matrix-finalization status, achieved state, remaining deliverables, execution process, filtering logic, computation phases, and current next step before changing code.

The core build-control artifact is [docs/architecture/v3_stage_family_indicator_working_matrix.md](docs/architecture/v3_stage_family_indicator_working_matrix.md). The matrix defines each indicator/evidence row, its inclusion and exclusion rules, required input, outputs, path-specific meaning, and guardrails. Additional algorithm coding should not start until the relevant matrix rows are finalized and mapped to code.

At the core, `V3_Charter` is a CSV-based, user-directed stock analysis engine with exactly three user-facing analysis paths:

- `CROSSOVER`
- `DIVERGENCE`
- `SETUP`

Path intent:

- `CROSSOVER` includes both `PRE_BULL_CROSSOVER` for early bull-phase entry and `PRE_BEAR_CROSSOVER` for capital-preservation review on existing long-held equities.
- `DIVERGENCE` validates whether an investment opportunity may be developing.
- `SETUP` is a pure-play market-based entry path where technical-analysis indicators provide confidence for entries that may be shorter-lived than full Pre-Bull phase capture.

The engine must preserve the V2 path-first architecture, including baseline analysis, path routing, path-specific evidence, date processing, and D+X self-backtesting.

All indicator processing is API/provider-driven. The current default backend is Yahoo Finance through `yfinance`, but the engine must remain behind a swappable provider abstraction so another free backend can replace it later without changing matrix logic or evaluator meaning.

Broader context work below is historical/background unless explicitly requested by the user for a specific step.

Previous broad rebuild language:

- Load a user-selected CSV universe containing NSE, BSE, NYSE, and NASDAQ stock codes.
- Establish market, sector, and stock context.
- Route stocks into stage families.
- Produce explainable candidates.
- Separate technical signal validity from quality, context risk, and review priority.
- Backtest the same production engine as of historical dates.

The engine is not intended to perform automated trading, position sizing, capital allocation, or order execution.
It also does not implement stop-loss trading logic or portfolio-management automation.

## Restart First

For any new session, start in this order:

Single-folder restart pack:

- [docs/restart](/D:/Tools/Stock_Screener_V3/docs/restart)

1. [docs/charter/v3_charter_execution_plan.md](/D:/Tools/Stock_Screener_V3/docs/charter/v3_charter_execution_plan.md)
2. [docs/handover/v3_charter_restart_signoff_20260616.md](/D:/Tools/Stock_Screener_V3/docs/handover/v3_charter_restart_signoff_20260616.md)
3. [docs/charter/v3_charter_consolidated_engine_design.md](/D:/Tools/Stock_Screener_V3/docs/charter/v3_charter_consolidated_engine_design.md)
4. [docs/charter/v3_original_intent_and_handover.md](/D:/Tools/Stock_Screener_V3/docs/charter/v3_original_intent_and_handover.md)
5. [docs/handover/current_session_handover.md](/D:/Tools/Stock_Screener_V3/docs/handover/current_session_handover.md)
6. Verify local/GitHub sync:

```powershell
cd D:\Tools\Stock_Screener_V3
git status --short --branch
git log --oneline --decorate -8
```

Expected active branch:

```text
## V3_Charter...origin/V3_Charter
```

Latest restart-relevant commits:

- `bb50871 Record V1.6 charter revision hash`
- `9c11379 Advance master charter to V1.6`
- `5e8180a Record V1.5 charter revision hash`

Current restart reading note:

- use [docs/architecture/v3_stage_family_indicator_working_matrix.md](/D:/Tools/Stock_Screener_V3/docs/architecture/v3_stage_family_indicator_working_matrix.md) as the editable matrix and core build-control artifact
- finalize matrix row definitions, inclusion/exclusion behavior, required inputs, outputs, and guardrails before algorithm coding
- read it as a plain-English signoff table, not as shorthand role codes
- use [C:\Users\dell\OneDrive\Desktop\Stock_Engine3_Pythoncode.py](/C:/Users/dell/OneDrive/Desktop/Stock_Engine3_Pythoncode.py) only as a reviewed seed scaffold, not as the active engine file

## Source Documents

- Working V3 execution plan: [docs/charter/v3_charter_execution_plan.md](docs/charter/v3_charter_execution_plan.md)
- Canonical V3 original intent and handover: [docs/charter/v3_original_intent_and_handover.md](docs/charter/v3_original_intent_and_handover.md)
- Standalone consolidated charter: [docs/charter/v3_charter_consolidated_engine_design.md](docs/charter/v3_charter_consolidated_engine_design.md)
- Core build-control indicator matrix: [docs/architecture/v3_stage_family_indicator_working_matrix.md](docs/architecture/v3_stage_family_indicator_working_matrix.md)
- Current engine gap analysis: [docs/analysis/current_engine_gap_analysis_against_fresh_charter_2026-06-01.md](docs/analysis/current_engine_gap_analysis_against_fresh_charter_2026-06-01.md)
- V2 operational parity contract: [docs/architecture/v2_operational_parity_contract.md](docs/architecture/v2_operational_parity_contract.md)
- V2 scoring logic extraction: [docs/architecture/v2_scoring_logic_and_interpretation_extraction.md](docs/architecture/v2_scoring_logic_and_interpretation_extraction.md)
- V3 evidence-stage matrix: [docs/architecture/v3_evidence_stage_matrix.md](docs/architecture/v3_evidence_stage_matrix.md)
- V3 baseline decision tree: [docs/architecture/v3_baseline_decision_tree.md](docs/architecture/v3_baseline_decision_tree.md)
- Current handover: [docs/handover/current_session_handover.md](docs/handover/current_session_handover.md)

Archived reference documents from the previous engine are kept under `docs/`.

## Current Decision

Do not continue tuning the old Crossover monolith.

Keep useful parts from the previous engine:

- Indicator calculations.
- Reason-code practice.
- Web app operating model.
- Historical replay concept.
- Validation artifacts and lessons.

Rebuild or refactor:

- Decision layer.
- Evidence-pack model.
- Candidate class and review-priority output.
- Backtesting subsystem.
- Metadata baseline.

## Repository Structure

```text
data/
  samples/              Sample or fixture data only. No large raw market dumps.
docs/
  analysis/             Gap analyses and current-state reviews.
  architecture/         Target architecture and module contracts.
  backtesting/          Backtesting design and validation methodology.
  charter/              Program charter and scope documents.
scripts/                Utility scripts.
src/                    Future engine implementation.
tests/                  Automated tests.
validation/
  baselines/            Accepted baseline validation summaries.
  runs/                 Dated validation outputs and notes.
```

## GitHub Remote Setup

GitHub CLI is not installed on this machine at creation time, so the remote repository was not created automatically.

After creating an empty GitHub repository manually, connect it with:

```powershell
git remote add origin https://github.com/<owner>/<repo>.git
git branch -M main
git push -u origin main
```

## Development Rule

No signal-rule change should be promoted without a backtest report that includes:

- D date or date range.
- Universe and filters.
- Symbols processed.
- Candidates found.
- Candidate density.
- D+1, D+2, and D+5 outcome.
- Score-bucket behavior.
- Failure categories.

## Current Implementation Status

Sprint 1 has produced the foundation layer and a V1-complete Crossover family:

- Python package skeleton under `src/stock_screener_v3`.
- Core dataclasses for universe records, evidence packs, stage evaluations, scores, and backtest results.
- CSV universe loader with metadata preservation for mixed NSE/BSE/NYSE/NASDAQ files.
- Sector/exchange filtering and deterministic sampling.
- Historical slicing helpers for no-lookahead tests.
- BacktestEngine v1 with pluggable price provider and stage evaluator contracts.
- Candidate-density and candidate-only forward hit-rate summaries.
- Yahoo data-provider wrapper behind a provider interface.
- Detail CSV and summary markdown report writers.
- Run I/O helpers for V2-style artifact naming under `validation/runs/`.
- V2-compatible offline CSV header contract.
- Workspace-safe input/output path resolution.
- File and console run logging with explicit logger close support for Windows.
- Crossover stage family V1 complete for the current engine scope:
  - deterministic daily MACD/RSI/ADX/EMA/volume/structure evidence;
  - direction-aware bull transition entry and bear transition exit/preservation routes;
  - below-zero MACD pair requirement for bullish Crossover transition;
  - explicit rejection of above-zero bull continuation as Crossover;
  - generated cross-sector and symbol-level calibration reports from existing detail CSVs.
- First Setup evaluator slice for bull pullback re-entry and bull continuation.
- Stage-family dispatcher and CLI stage-family selection for Crossover, Setup, Divergence, or any restricted subset.
- Formal ranking diagnostics for choosing the reported stage-family result after holistic traversal.
- Baseline router with market/sector/stock regime diagnostics and positive elimination.
- Configurable market/sector/theme benchmark mapping for regime determination.
- Single-date backtest CLI that runs the same V3 evidence, traversal, ranking, and report path used by the production engine layer.
- Reusable run orchestrator and CLI entry point.
- Python scanner console in `web_app_v3.py` for user-selected V3 scans with V2-style stage classifications and visible diagnostics.
- Standard-library unit tests under `tests/`.

Run tests with:

```powershell
$env:PYTHONPATH='D:\Tools\Stock_Screener_V3\src'
python -m unittest discover -s tests -v
```

Run a V3 backtest from PowerShell:

```powershell
$env:PYTHONPATH='D:\Tools\Stock_Screener_V3\src'
python -m stock_screener_v3.cli backtest --workspace-root D:\Tools\Stock_Screener_V3 --universe-file data\samples\us_master_sample.csv --d-date 2026-02-11 --forward-days 1,2,5
```

The default stage-family set is `CROSSOVER,SETUP,DIVERGENCE`. Use `--stage-family` only when intentionally restricting the engine path.

Run a multi-date V3 backtest pack:

```powershell
$env:PYTHONPATH='D:\Tools\Stock_Screener_V3\src'
python -m stock_screener_v3.cli backtest-pack --workspace-root D:\Tools\Stock_Screener_V3 --universe-file data\samples\us_master_sample.csv --d-dates 2026-02-11,2026-03-11 --forward-days 1,2,5
```

Generate Crossover calibration reports from existing detail CSVs:

```powershell
$env:PYTHONPATH='D:\Tools\Stock_Screener_V3\src'
python -m stock_screener_v3.cli cross-sector-report --details <comma-separated-detail-csvs> --output validation\runs\cross_sector_report.md --horizon-days 20 --candidate-state PRE_BEAR_CROSSOVER
python -m stock_screener_v3.cli symbol-failure-report --details <comma-separated-detail-csvs> --output validation\runs\symbol_failure_report.md --horizon-days 20
python -m stock_screener_v3.cli stage-family-report --details <comma-separated-detail-csvs> --output validation\runs\stage_family_report.md --stage-family DIVERGENCE --horizon-days 20
python -m stock_screener_v3.cli integrated-report --details <comma-separated-detail-csvs> --output validation\runs\integrated_report.md --horizon-days 20
```

Run the V3 web console:

```powershell
python D:\Tools\Stock_Screener_V3\web_app_v3.py
```

The UI opens at `http://127.0.0.1:8010`.

## Current Next Plan

The current coding direction on `V3_Charter` is:

- start every implementation pass from [docs/charter/v3_charter_execution_plan.md](docs/charter/v3_charter_execution_plan.md)
- keep the June 13 charter as the only seed/source-of-truth
- treat [docs/architecture/v3_stage_family_indicator_working_matrix.md](docs/architecture/v3_stage_family_indicator_working_matrix.md) as the core engine construction table
- finalize the matrix before additional algorithm behavior changes
- preserve per-ticker, category-specific scoring grouped by stage family
- keep indicator processing API-driven behind a provider abstraction
- represent the working matrix at the indicator-family row level with explicit condition logic inside each stage-family cell
- remove hardcoded evaluator thresholds and score weights from inline logic
- move scoring/interpretation defaults into explicit config or matrix-owned structures without changing current behavior unless approved

Completed recent steps:

- `9fde1b7` aligned `V3_Charter` seed documentation
- `6bd0daf` clarified the charter scoring rule: per-ticker score, grouped display by stage family
- `f62421b` started code extraction of stage scoring defaults into `src/stock_screener_v3/scoring_config.py`
- local 2026-06-19 pass created the charter execution plan and moved additional evaluator scoring constants into `src/stock_screener_v3/scoring_config.py`

The next coding focus is:

- finalize the stage-family indicator matrix before additional engine behavior changes
- produce a matrix-to-code implementation assessment, not a generic gap table
- classify each matrix row as implemented, partial, missing, naming-misaligned, validation-needed, not yet manifest/config-owned, future/TBD, or blocked
- keep local `D:\Tools\Stock_Screener_V3` and `origin/V3_Charter` synchronized after each completed step
