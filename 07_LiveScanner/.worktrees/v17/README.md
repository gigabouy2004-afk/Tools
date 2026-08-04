# LiveScreener

LiveScreener is a per-ticker technical baseline scanner. The `V17` research
branch adds a U.S.-only research engine whose daily foundation is the traded
session before today. Full-duration completed 4H and 1H observations from the
current session describe whether that thesis is developing; they cannot change
the daily result.

The engine is a screener, not an automated trading system. It reports a
repeatable status for each ticker and expects the end user to perform offline
verification before acting on a candidate.

## Current release

- Baseline date: 2026-07-30
- Branch: `V17`
- Baseline commit: `3586f24cb4e8390e66476e30f895e1a3ce3ff430`
- Current research engine: `Live_Scanner_v17.py`
- V17 status: non-binding; not approved as a momentum classifier
- Runtime-only plan: approved; implementation gates R1-R8 not yet started
- Python: 3.10 or later
- Market data: Yahoo Finance through `yfinance`
- Default concurrency: 3 independent ticker workers
- Output: multi-sheet XLSX plus a text execution log

## Quick start

Install the dependencies:

```powershell
python -m pip install -r requirements.txt
```

Run the momentum review:

```powershell
python .\Live_Scanner_v17.py `
  -c AAPL MSFT NVDA `
  --live-candle-mode completed `
  -o .\output\Momentum_Review.xlsx
```

V17 accepts only provider-verified NYSE/Nasdaq equity listings. Premarket,
postmarket, partial daily candles, ETFs, NYSE American/Arca and international
listings are excluded.

The target zero-setup interface below is approved but not implemented yet:

```powershell
python .\Live_Scanner_v17.py --universe nasdaq
python .\Live_Scanner_v17.py --universe nyse
python .\Live_Scanner_v17.py --universe all
```

It will discover listings and download history from free-access sources at
runtime. Normal execution will not require a local universe master, historical
database, historical-data folder, persistent market-data cache or resume
checkpoint. A small code list receives full enrichment; an all-market run
bulk-calculates the daily foundation first and performs slower current-session
enrichment only for daily-qualified candidates.

The primary, self-contained development authority is
`docs/MOMENTUM_ENGINE_MASTER_BLUEPRINT.md`. Start there in every new session.
It contains the complete foundation, calculation contract, research design,
evidence, development gates, interim goals and final activation criteria.

Its living checkpoint is the only restart authority between Codex sessions.
Every implementation-progress commit must update the master blueprint, active
action plan and changelog together. The continuity regression test rejects a
committed implementation state newer than the master and rejects a dirty
implementation handoff unless all three continuity documents are being
updated.

## Design contract

The engine follows five non-negotiable rules:

1. Every ticker is evaluated independently. Classification cannot depend on the
   input universe, another ticker, sector performance, or thread completion
   order.
2. Thread pooling changes execution speed only.
3. `Max-Count` and `Max-Buys` are optional poll-boundary continuation triggers.
   The complete final poll is retained.
4. The fixed core calculation window determines the signal. Adaptive
   MAX/5Y/1Y history is advisory output only.
5. V17 is restricted to provider-verified NYSE/Nasdaq equities and the XNYS
   calendar.

## Repository contents

- `docs/MOMENTUM_ENGINE_MASTER_BLUEPRINT.md` — primary standalone development
  authority for the complete Momentum Engine program.
- `Live_Scanner_v17.py` — previous-session daily foundation plus non-binding
  current-session 4H/1H evidence.
- `v17_mtf.py` — U.S. exchange-calendar, candle-construction and diagnostic
  module.
- `v17_us_daily_backtest.py` — vectorized multi-year completed-D1 reference
  replay.
- `v17_mtf_replay.py` — timestamp-correct daily/30-minute archive replay.
- `v17_analyze_daily_results.py` — descriptive indicator cohort analysis.
- `docs/ENGINE_V17_SHADOW.md` — V17 calculation and safety contract.
- `docs/VALIDATION_V17_D1_MTF_2026-07-29.md` — five-year evidence, limitations
  and activation-gate decision.
- `momentum_research.py` — age-aware completed-daily feature, outcome and
  chronological-split foundation.
- `build_momentum_research_panel.py` — point-in-time archive panel builder.
- `validate_momentum_research_panel.py` — unconditional chronological outcome
  audit.
- `plain_language_output.py` — compact visible workbook review without
  internal flags.
- `docs/MOMENTUM_RESEARCH_PROTOCOL.md` — nomenclature, data and validation
  contract for the next identification layer.
- `docs/MOMENTUM_RESEARCH_FIELD_GUIDE.md` — plain explanation of backtest
  columns.
- `docs/HANDOVER_V17_MOMENTUM_FOUNDATION_2026-07-30.md` — immutable
  tagged-baseline evidence and reproduction record.
- `docs/ACTION_PLAN_V17_CONTINUATION_2026-07-30.md` — current prioritized
  continuation plan and promotion gates.
- `CHANGELOG.md` — release history.

## Release status

V17 is research infrastructure only. No genuine-momentum classifier or
production BUY change is approved. The next work is runtime gates R1-R3:
remove required local historical inputs and persistence, implement runtime
Nasdaq/NYSE discovery, and prove bulk-daily calculation parity.

Free runtime downloads can support operational review and a
current-survivor-only reference backtest. They cannot supply point-in-time
inactive/delisted coverage or several years of 30-minute history, so scientific
promotion gates G1-G8 remain blocked or not started.

Historical documentation and generated test evidence are stored under
`Retired`. Retired material is non-authoritative and must not be used for
current requirements or decisions unless the owner explicitly reactivates it.

When a calculation, data contract, outcome, gate, goal or activation status
changes, update the master blueprint, affected supporting documents and this
changelog in the same commit.
