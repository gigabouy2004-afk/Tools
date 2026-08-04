# Backtesting Engine Requirements

Date: 2026-06-04

The backtesting engine is a first-class deliverable for this rebuild.

## Purpose

Run the production signal engine as of a historical D date and validate the resulting candidates against future bars that were unavailable on D.

## Core Requirements

- Execute the same signal engine used by live scans.
- Prevent look-ahead bias.
- Preserve universe metadata.
- Support deterministic random samples.
- Support sector-filtered samples.
- Support full-universe ranked runs.
- Report candidate density.
- Report D+1, D+2, and D+5 results.
- Produce detail CSV and summary markdown.
- Produce aggregate comparison scorecards.

## V1 Foundation Status

Implemented foundation pieces:

- Backtest engine shell.
- Price provider protocol.
- Stage evaluator protocol.
- In-memory price provider for tests.
- Yahoo price provider wrapper.
- Historical as-of slicing.
- Benchmark as-of loading for market and sector regime context.
- Same production evidence builder and stage-family evaluator used by CLI runs.
- Default holistic V3 execution across `CROSSOVER`, `MOMENTUM_SETUP`, and `DIVERGENCE`.
- Formal ranking diagnostics for the winning stage-family row.
- Candidate-density calculation.
- Candidate-only forward hit-rate summary.
- Average and median forward-return summary.
- Hit-rate, average-return, and median-return breakdowns by score bucket, sector, and review priority.
- Outcome-category classification for candidate follow-through.
- Failure-category classification for failed candidate follow-through.
- Candidate score-bucket summary reporting.
- Detail CSV writer.
- Summary markdown writer.
- Run artifact path manager with dated default CSV, summary, and log filenames.
- Workspace-safe input and output path validation.
- File-backed run logger for queued/started/completed/failed run evidence.
- Reusable `run_backtest(...)` orchestrator.
- CLI adapter through `python -m stock_screener_v3.cli backtest`.
- Multi-date `run_backtest_pack(...)` orchestrator.
- CLI adapter through `python -m stock_screener_v3.cli backtest-pack`.

Remaining gaps:

- Broader historical calibration packs for ranking, scoring, Divergence thresholds, and regime thresholds.
- Persistence conventions for promoted multi-date validation baselines.

## Required Run Modes

| Mode | Purpose | Status |
|---|---|---|
| Single-date replay | Debug one D date | Implemented |
| Multi-date replay | Validate across regimes | Implemented through `backtest-pack` |
| Random-lot replay | Avoid cherry-picking | Implemented through deterministic sample size/seed |
| Full-universe ranked replay | Simulate real scanner behavior | Implemented for one D date |

## Current CLI Contract

Run the full V3 engine from PowerShell:

```powershell
$env:PYTHONPATH='D:\Tools\Stock_Screener_V3\src'
python -m stock_screener_v3.cli backtest `
  --workspace-root D:\Tools\Stock_Screener_V3 `
  --universe-file data\samples\us_master_sample.csv `
  --d-date 2026-02-11 `
  --forward-days 1,2,5 `
  --stage-family CROSSOVER,MOMENTUM_SETUP,DIVERGENCE `
  --run-label v3_full_engine_smoke
```

`--stage-family` is optional. The default is now:

```text
CROSSOVER,MOMENTUM_SETUP,DIVERGENCE
```

The command writes three separate artifacts under `validation/runs/` unless explicit output paths are supplied:

- detail CSV: forensic per-symbol calculation and diagnostics record.
- summary markdown: human-readable run summary.
- log file: execution status and run parameters.

The detail CSV preserves V2-compatible columns first, then appends V3 fields including traversal, ranking, regime, Divergence, outcome, and forward-return diagnostics.

Run a multi-date V3 pack from PowerShell:

```powershell
$env:PYTHONPATH='D:\Tools\Stock_Screener_V3\src'
python -m stock_screener_v3.cli backtest-pack `
  --workspace-root D:\Tools\Stock_Screener_V3 `
  --universe-file data\samples\us_master_sample.csv `
  --d-dates 2026-02-11,2026-03-11 `
  --forward-days 1,2,5 `
  --run-label v3_full_engine_pack
```

The pack command writes normal per-date CSV/summary/log artifacts and one aggregate multi-date markdown summary.

## Required Output Metrics

- Universe size: implemented as symbols attempted.
- Symbols processed: implemented.
- Symbols skipped: implemented.
- Skip reasons: implemented.
- Candidates found: implemented.
- Candidate density: implemented.
- D+1 hit rate: implemented for candidate rows.
- D+2 hit rate: implemented for candidate rows.
- D+5 hit rate: implemented for candidate rows.
- Average forward return: implemented.
- Median forward return: implemented.
- Pass rate by sector: implemented in summary markdown.
- Pass rate by score bucket: implemented in summary markdown.
- Pass rate by review priority: implemented in summary markdown.
- Failure reason-code distribution: implemented as first-pass failure category summary.

## Anti-Bias Rules

- Do not use future bars in signal generation.
- Do not use current profile metadata as historical truth without tagging it.
- Do not report only winners.
- Do not hide skipped symbols.
- Do not compare first-N-candidate tests against ranked full-universe tests as equivalent.
- Do not tune rules from a single ticker.

## Latest Verification

As of 2026-06-04:

- Unit suite: `58 tests` passing.
- Live Yahoo-backed smoke command was run against `data\samples\us_master_sample.csv` for D date `2026-02-11` with default full V3 families.
- Multi-date pack command exists and is covered by unit tests; live pack validation should be run before promoting a calibration baseline.
- Live validation artifacts are intentionally not committed unless a summary is promoted as a named validation baseline.
