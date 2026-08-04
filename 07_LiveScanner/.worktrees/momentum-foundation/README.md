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

- Release date: 2026-07-25
- Reference baseline: `Live_Scanner_v14.py`
- Carried daily calculation: completed previous-session calculation
- Current research engine: `Live_Scanner_v17.py`
- V17 status: non-binding; not approved as a momentum classifier
- Python: 3.10 or later
- Market data: Yahoo Finance through `yfinance`
- Default concurrency: 3 independent ticker workers
- Output: multi-sheet XLSX plus a text execution log

## Quick start

Install the dependencies:

```powershell
python -m pip install -r requirements.txt
```

Run a CSV watchlist:

```powershell
python .\Live_Scanner_v14_Enhanced.py `
  -i "D:\path\watchlist.csv" `
  -o "D:\path\scan-output.xlsx" `
  --workers 3
```

Run selected symbols:

```powershell
python .\Live_Scanner_v14_Enhanced.py `
  -c CAT GE RTX UNP DE `
  -o "D:\path\selected-symbols.xlsx"
```

Run historical as-of validation:

```powershell
python .\Live_Scanner_v14_Enhanced.py `
  -c CAT GE RTX UNP DE `
  --as-of-dates 2026-07-22,2026-07-23,2026-07-24 `
  --live-candle-mode completed `
  -o "D:\path\historical-validation.xlsx"
```

Run V15 shadow validation without changing V14 classifications:

```powershell
python .\Live_Scanner_v15.py `
  -i "D:\path\watchlist.csv" `
  --live-candle-mode completed `
  -o "D:\path\v15-shadow-output.xlsx"
```

In the V15 `Details` worksheet, Beta and Alpha are placed immediately after
Price and Currency. The pane is frozen at `L2`, so columns A through K and the
header row remain visible while scrolling.

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

The next research stage is described in
`docs/MOMENTUM_RESEARCH_PROTOCOL.md`. It builds a completed-daily observation
and outcome panel for every eligible stock/session, retains young listings
without fabricating missing history, and uses chronological training,
calibration and holdout periods. It does not introduce a new BUY rule.

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
5. Legacy engines retain their documented market routing. V17 is deliberately
   restricted to provider-verified NYSE/Nasdaq equities and the XNYS calendar.

## Repository contents

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

- `Live_Scanner_v14.py` — unchanged V14 reference baseline.
- `Live_Scanner_v14_Enhanced.py` — enhanced threaded and historically
  contextual scanner.
- `Live_Scanner_v15.py` — experimental shadow scanner with frozen V14 output
  classifications and separate momentum/entry audit states.
- `docs/ENGINE_V15_SHADOW.md` — V15 hypotheses, thresholds, state logic, and
  activation safeguards.
- `docs/VALIDATION_V15_SHADOW_2026-07-27.md` — V14 parity, unit, and historical
  shadow-state validation.
- `docs/VALIDATION_V15_BETA_ALPHA_2026-07-28.md` — V15 Beta/Alpha contract,
  live-provider smoke evidence, workbook checks, and regression results.
- `docs/HANDOVER_V15_BETA_ALPHA_SIGNOFF_2026-07-28.md` — owner sign-off package,
  synchronization manifest, risks, runbook, and rollback boundary.
- `docs/HANDOVER_V14_TO_V15_AND_APPROVAL_2026-07-27.md` — complete V14 intent,
  V15 scope, controls, I/O and messaging contracts, deployment manifest, and
  owner-approval record.
- `docs/ENGINE_V14_ENHANCED.md` — complete engine and operator documentation.
- `docs/VALIDATION_2026-07-25.md` — XLI regression, full-U.S. run, and
  independent live-feed audit.
- `docs/VALIDATION_P1_HARDENING_2026-07-27.md` — approved volume, U.S.
  liquidity, extreme-extension, and data-through hardening evidence.
- `docs/VALIDATION_POSITIVE_REGIME_2026-07-27.md` — positive-regime scope,
  GLOSTER correction, invariant checks, and historical replay evidence.
- `docs/HANDOVER_AND_SESSION_SIGNOFF_2026-07-25.md` — closure state, runbook,
  hashes, open risks, and restart instructions.
- `CHANGELOG.md` — release history.

## Release status

Implementation and reproducibility validation are complete. The owner-approved
hardening policies now require a `0.60` current-volume floor, require USD
1 million ADV20 turnover for U.S. BUY candidates, and label BUY candidates more
than 5 ATR above EMA50 as `BUY_EXTENDED_REVIEW`.

BUY#4 additionally requires a fresh MACD signal-line crossover above zero with
a positive histogram. Momentum continuation requires a sustained expansion
window with its latest two histogram bars positive. Negative-histogram
improvement cannot qualify or strengthen a signal, and the engine does not
classify pre-bull or pre-bear crossover candidates.

International absolute liquidity thresholds remain intentionally disabled until
currency-aware or exchange-specific policies are defined. Low-liquidity
daily-versus-intraday feed-quality warnings remain a documented future item.
