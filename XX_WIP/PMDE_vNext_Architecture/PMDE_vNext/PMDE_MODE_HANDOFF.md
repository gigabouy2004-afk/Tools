# PMDE Mode Handoff

Last updated: 2026-05-14

This note captures the intended operating model for PMDE vNext so a new chat can continue without reopening the full design discussion.

## Engine Modes

PMDE has three supported modes in `CONFIG/settings.py`:

```python
ENGINE_MODE_FULL_BASELINE = "FULL_BASELINE"
ENGINE_MODE_QUICK_CROSSOVER = "QUICK_CROSSOVER"
ENGINE_MODE_QUICK_SETUP = "QUICK_SETUP"
```

Current selected mode is controlled by:

```python
ENGINE_MODE = ENGINE_MODE_QUICK_CROSSOVER
```

## Full Baseline

Purpose: build and maintain the active PMDE registry.

Data flow:

```text
Input symbols -> full/deep PMDE processing -> update ACTIVE_BASELINE.csv
```

Rules:

- Uses symbols from `INPUT_FILE`, `HARDCODED_SYMBOLS`, and `FALLBACK_SYMBOLS`.
- Adds new symbols to `STORAGE/ACTIVE_BASELINE.csv`.
- Replaces existing symbol rows with the latest processed row.
- Leaves symbols not present in the current run untouched.
- Produces the full baseline report.

`ACTIVE_BASELINE.csv` is a latest-state registry, not historical storage.

## Quick Crossover

Purpose: recheck symbols previously near crossover/divergence, plus any new input symbols explicitly provided.

Data flow:

```text
ACTIVE_BASELINE rows in QUICK_CROSSOVER_BASELINE_STATES
plus explicit input symbols
-> L2 crossover review
-> update ACTIVE_BASELINE.csv
-> write CRS report for configured probable states
```

Rules:

- Pulls baseline watchlist symbols from `ACTIVE_BASELINE.csv` where `tactical_state` is in:

```python
QUICK_CROSSOVER_BASELINE_STATES = [
    "PRE_BULL_CROSSOVER",
    "PRE_BEAR_CROSSOVER"
]
```

- Also includes any symbols explicitly provided through `INPUT_FILE`, `HARDCODED_SYMBOLS`, or `FALLBACK_SYMBOLS`.
- If a new input symbol is not already in the baseline, CRS still processes it fully and adds it to the baseline after success.
- CRS updates `ACTIVE_BASELINE.csv` for every successfully processed symbol.
- CRS report is filtered to `QUICK_CROSSOVER_STATES` when `QUICK_CROSSOVER_OUTPUT_ONLY_PROBABLES=True`.

Current CRS report states:

```python
QUICK_CROSSOVER_STATES = [
    "PRE_BULL_CROSSOVER",
    "PRE_BEAR_CROSSOVER",
    "EARLY_RECOVERY_INSIDE_BEAR_STRUCTURE"
]
```

## Quick Setup

Purpose: quick standalone setup scan for a random or targeted input list.

Data flow:

```text
Input symbols only -> setup scan -> setup report
```

Rules:

- Does not read `ACTIVE_BASELINE.csv`.
- Does not update `ACTIVE_BASELINE.csv`.
- Runs the setup policy:

```text
P(x) daily close progression
-> MACD 8,21,5 top-down 1D -> 4H -> 1H
-> support filters
```

- Writes only confirmed setup rows when `SETUP_OUTPUT_ONLY_CONFIRMED=True`.

## Baseline Registry Rules

`STORAGE/ACTIVE_BASELINE.csv` should contain one latest row per symbol.

Fields include latest PMDE state, processing timestamp, and `data_fetch_timestamp`.

No append-only baseline history is needed because historical prices and helper inputs are externally reproducible. Yahoo Finance remains the market-data source of truth.

## Important Files

- `CONFIG/settings.py`: mode selection and thresholds.
- `main.py`: mode routing, symbol loading, report filtering, baseline update control.
- `CORE/baseline_registry.py`: active baseline load/update behavior.
- `LAYERS/L1/l1_engine.py`: mode entry tags and baseline record creation.
- `LAYERS/L2/l2_orchestrator.py`: normal crossover decisioning and quick setup policy.
- `LAYERS/L3/l3_compute_layer.py`: indicator and setup fact computation.
- `OUTPUT/execution_reporter.py`: report generation.

## Current Status

Implemented:

- Explicit FB / CRS / QS mode constants.
- CRS source list as baseline watchlist plus explicit input symbols.
- FB and CRS update `ACTIVE_BASELINE.csv`.
- QS remains standalone.
- Baseline update is case-insensitive by symbol.
- Baseline rows include `data_fetch_timestamp`.

Recommended next checks:

- Run `python -m py_compile` across the project.
- Run `main.load_symbols()` for CRS and confirm symbol counts.
- Run a small CRS execution and inspect `ACTIVE_BASELINE.csv` updates.
