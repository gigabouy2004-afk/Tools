# V2 Operational Parity Contract

Date: 2026-06-02

V3 must not regress below V2 in the operator-facing surfaces that made the engine usable for analysis.

## UI Minimum

The V3 UI must preserve or improve the V2 level of control and visibility:

- Universe file selection or upload.
- Output CSV and report path visibility.
- Exchange, sector, industry, price, market-cap, volume, RSI, ADX, Bollinger, and candidate-state filters.
- Stage-family controls for crossover, momentum trading, and divergence families.
- Batch progress, current candidate count, internal state counts, and completion message.
- Wide diagnostic table with at least the V2 visible columns defined by `V2_COMPAT_UI_COLUMNS`.
- Downloadable offline artifacts after every run.
- Clear empty-state and error-state messages.

The first V3 UI can be cleaner than V2, but it cannot hide the diagnostics required to audit why a symbol was selected or skipped.

## Log Minimum

The log file is the execution summary report for the run. It is not a replacement for the output CSV and must not contain the full symbol-detail table as its primary purpose.

Each V3 run must produce a file log that records:

- Run queued.
- Run started.
- Run parameters.
- Universe file and output artifact paths.
- Batch progress or equivalent stage progress.
- Candidate counts and skip counts.
- Completion message.
- Failure message with exception details.

The log location must be visible to the operator and default to `validation/runs/`.

## Offline CSV Minimum

The output CSV is the forensic calculation record for each symbol/code. It captures the detailed per-symbol diagnostics, scores, classifications, reason codes, and forward validation fields needed for offline review.

V3 detail CSV output must keep the V2 offline schema as the leading column block. The exact column contract is defined in `stock_screener_v3.output_contracts.V2_COMPAT_EXPORT_COLUMNS`.

V3-specific fields are appended after the V2-compatible block. Missing diagnostic values should be blank, not omitted.

The CSV writer must emit headers even when a run has zero candidate rows. A blank file is not acceptable because it prevents downstream spreadsheet review and automated validation.

The log file, detail CSV, and summary report must be physically separate files. V3 must reject a run configuration that points any two of those artifacts to the same path.

## Report Minimum

Every historical replay or live scan must produce:

- Detail CSV.
- Human-readable summary report.
- Run log.

HTML can be added after the V3 engine contracts stabilize, but the V3 UI/report layer must retain the same auditability as the V2 HTML report.
