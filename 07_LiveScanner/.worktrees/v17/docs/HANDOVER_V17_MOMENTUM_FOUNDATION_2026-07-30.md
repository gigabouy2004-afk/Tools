# V17 Momentum Foundation — Baseline Handover

Document role: immutable handover for the tagged V17 foundation baseline

Primary authority for current development:
`MOMENTUM_ENGINE_MASTER_BLUEPRINT.md`

Handover status: foundation evidence remains valid; continuation starts from
the master blueprint and active action plan

Date: 2026-07-30

Baseline branch: `V17`

Baseline commit: `3586f24cb4e8390e66476e30f895e1a3ce3ff430`

Baseline tag: `baseline-v17-momentum-foundation-2026-07-30`

## Baseline decision

This is the approved starting point for subsequent U.S. momentum-identification
research. It supersedes the earlier V17 research state as the branch baseline.

The baseline is approved as research infrastructure, not as a genuine-momentum
classifier and not as a new production BUY rule.

## Time contract

All continuation work must preserve these meanings:

- **Previous completed session** is the last traded NYSE session before today.
  Its completed daily and completed-weekly information supplies the foundation.
- **Current session** means now/today, including premarket, regular trading
  hours and after close.
- Today remains the current session after its official close. Today's daily
  candle becomes the previous completed-session foundation only when the next
  trading session begins.
- Only completed 4-hour/1-hour observations belonging to the current session
  may be displayed or used to describe current development.
- No previous-session 4-hour/1-hour opinion may be displayed, qualified or
  used as the comparison point for current-session progression.
- Historical lower-timeframe bars may be used internally only to warm up
  MACD, ADX, RSI, Stochastic and related calculations.
- The first completed intraday observation of the current session is a starting
  observation, not an improvement or regression from a prior-day intraday bar.

## What is included

### Live research review

`Live_Scanner_v17.py` carries forward the completed-daily calculation and adds
non-binding current-session 4-hour/1-hour diagnostics.

The visible workbook contains:

- `Summary` — run totals and data-quality information;
- `Review` — one plain-language row per equity; and
- hidden `Technical Data` — internal reproducibility fields.

Version identifiers, implementation flags and internal state names are not
needed to read the visible workbook or text execution log.

### Completed-daily research panel

`momentum_research.py` creates one point-in-time record for every supplied
equity/session, including rows that were not selected by inherited rules.

It records:

- stock-history group and feature availability;
- EMA, completed-weekly context, MACD, ADX/DI, RSI, Stochastic and ATR;
- historical returns, trend slopes, volume participation and turnover;
- 52-week/post-listing range and ATR-normalized extension;
- plain descriptions of structure, participation and extension;
- hypothetical entry at the open of the session immediately after the daily
  foundation;
- 5-, 10- and 20-session return, MFE and MAE; and
- a provisional ten-session +2 ATR/-1 ATR path outcome with same-session
  ambiguity reported explicitly.

The ATR path is a research label, not an approved trading threshold.

### New and young listings

Every valid completed observation is retained:

| Available stock history | Research treatment |
|---:|---|
| Fewer than 20 sessions | Observation only |
| 20–119 sessions | Young-listing research |
| 120–251 sessions | Reduced-history research |
| 252 or more sessions | Standard-history research |

Missing long-history indicators remain blank and carry explicit availability
fields. Sector and industry may provide point-in-time context later, but never
replace the stock's missing price history or manufacture stock-level evidence.

These history boundaries are provisional research scaffolding.

## Data contract for the next phase

A promotion-quality daily archive must contain:

- stable security identifiers that survive ticker changes;
- point-in-time tickers and NYSE/Nasdaq listing exchange;
- equity/ETF identification;
- adjusted daily OHLCV;
- listing and delisting dates;
- inactive and delisted securities;
- delisting return or terminal-value treatment;
- point-in-time sector/industry where available; and
- immutable source and corporate-action provenance.

The panel builder intentionally refuses an archive without the required
identity and scope fields. A current-survivor-only universe may be used for
mechanical smoke testing, but never for efficacy or promotion evidence.

## Reproduction commands

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Run the live research review:

```powershell
python .\Live_Scanner_v17.py `
  -c AAPL MSFT NVDA `
  --live-candle-mode completed `
  -o .\output\Momentum_Review.xlsx
```

Build a research panel from a compliant long-form archive:

```powershell
python .\build_momentum_research_panel.py `
  D:\path\us_equity_daily_archive.parquet `
  --output-dir .\output\Momentum_Research_Panel
```

Assign fixed chronological periods and create unconditional outcome summaries:

```powershell
python .\validate_momentum_research_panel.py `
  .\output\Momentum_Research_Panel\Momentum_Research_Panel.parquet `
  --training-end 2021-12-31 `
  --calibration-end 2023-12-29 `
  --output-dir .\output\Momentum_Research_Validation
```

The dates above are command examples, not approved research boundaries. Freeze
the actual dates before examining final holdout results.

Run deterministic validation:

```powershell
python -m unittest discover -s tests -p "test_*.py"
python -m py_compile `
  Live_Scanner_v17.py v17_mtf.py v17_mtf_replay.py `
  momentum_research.py plain_language_output.py `
  build_momentum_research_panel.py `
  validate_momentum_research_panel.py
git diff --check
```

## Evidence at handover

- 78 deterministic/regression tests pass.
- All changed Python modules compile.
- Git whitespace validation passes.
- A bounded 1,255-row cached-data smoke exercised all history groups, forward
  outcomes and chronological-boundary purging.
- The cached smoke contained only one surviving security and therefore has no
  predictive or economic meaning.

Detailed evidence is in
`docs/VALIDATION_MOMENTUM_RESEARCH_FOUNDATION_2026-07-30.md`.

## Required next sequence

1. Acquire and version the compliant point-in-time daily archive.
2. Audit coverage, corporate-action adjustment, delisting treatment and stable
   security identity before examining momentum results.
3. Freeze training, calibration and holdout dates.
4. Measure unconditional outcomes by year, history group, liquidity, sector
   and broad market regime.
5. Measure inherited scanner conditions against those base rates.
6. Study individual daily features and stable interactions without creating a
   new BUY classification.
7. Compare transparent probability models only after the feature and outcome
   contracts are frozen.
8. Keep final holdout results untouched until all promotion gates are fixed.
9. Acquire multi-year 30-minute archives and test whether current-session
   4-hour/1-hour evidence adds value to the identical daily candidates.
10. Require a live research-only observation period before proposing any
    production activation.

## Guardrails

- Do not use random train/test splitting.
- Do not optimize thresholds on the final holdout.
- Do not silently treat incomplete outcomes as flat, failed or successful.
- Do not calculate a feature using information later than its recorded daily
  foundation.
- Do not let watchlist membership or another stock change a stock's result.
- Do not generalize missing stock history into synthetic sector-derived
  indicators.
- Do not call the present output genuine momentum.

## File map

- `docs/MOMENTUM_ENGINE_MASTER_BLUEPRINT.md` — primary, self-contained
  development authority.
- `docs/ACTION_PLAN_V17_CONTINUATION_2026-07-30.md` — active ordered gates and
  immediate continuation steps.
- `docs/MOMENTUM_RESEARCH_PROTOCOL.md` — supporting point-in-time research
  contract.
- `docs/MOMENTUM_RESEARCH_FIELD_GUIDE.md` — plain-language panel dictionary.
- `docs/VALIDATION_MOMENTUM_RESEARCH_FOUNDATION_2026-07-30.md` — validation
  record and bounded smoke results.
- `docs/VALIDATION_V17_D1_MTF_2026-07-29.md` — five-year inherited-rule and
  multi-timeframe gate evidence.
- `docs/ENGINE_V17_SHADOW.md` — inherited calculation and safety detail.
- `CHANGELOG.md` — active implementation and documentation transition record.
- `momentum_research.py` — feature, outcome and chronological-split library.
- `build_momentum_research_panel.py` — strict archive ingestion and panel
  writer.
- `validate_momentum_research_panel.py` — chronological outcome audit.
- `plain_language_output.py` — readable workbook presentation.
- `v17_mtf.py` — U.S. calendar and current-session intraday construction.
- `v17_mtf_replay.py` — historical intraday cutoff replay.

Superseded pre-V17 documentation and generated baseline results are stored
under `Retired` for recovery and audit only. They do not govern current
development. The master blueprint governs all new work and human-readable
terminology.
