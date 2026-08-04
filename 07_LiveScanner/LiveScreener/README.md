# LiveScreener

LiveScreener is a per-ticker technical baseline scanner. The current development
baseline is `Live_Scanner_v14_Enhanced.py`; `Live_Scanner_v14.py` is retained as
the unchanged V14 reference. `Live_Scanner_v16.py` is the active V16 shadow
track; `Live_Scanner_v15.py` is retained as its frozen predecessor. V16
preserves completed-candle V14 classifications while recording stricter
momentum-quality and entry-quality assessments. Partial-candle BUY
setups are retained as explicit, non-executable `PROVISIONAL_BUY` candidates.
Optional live Beta for equities and ETFs and three-year Alpha for ETFs can be
enabled with `--include-beta-alpha`; stock Alpha is intentionally blank.

The engine is a screener, not an automated trading system. It reports a
repeatable status for each ticker and expects the end user to perform offline
verification before acting on a candidate.

## Current release

- Release date: 2026-07-28
- Reference baseline: `Live_Scanner_v14.py`
- Current development baseline: `Live_Scanner_v14_Enhanced.py`
- Active shadow track: `Live_Scanner_v16.py`
- Frozen predecessor: `Live_Scanner_v15.py`
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

Run V16 shadow validation without changing V14 classifications:

```powershell
python .\Live_Scanner_v16.py `
  -i "D:\path\watchlist.csv" `
  --live-candle-mode completed `
  -o "D:\path\v16-shadow-output.xlsx"
```

Run V16 against the current regular-session candle:

```powershell
python .\Live_Scanner_v16.py `
  -i "D:\path\watchlist.csv" `
  --live-candle-mode intraday `
  --workers 3 `
  -o "D:\path\v16-intraday-output.xlsx"
```

V16 applies one process-wide Yahoo request policy: four attempts,
exponential retry/backoff, a minimum request interval, and a six-hour
persistent daily-history cache. The defaults can be overridden with
`--yahoo-max-attempts`, `--yahoo-retry-base-seconds`,
`--yahoo-min-request-interval`, `--daily-cache-dir`, and
`--daily-cache-ttl-minutes`.

Every run reports requested and effective candle modes, candle-state counts,
fallback counts, total error rate, and rate-limit error rate. A run exceeding
the configured quality thresholds is written for diagnosis, marked `INVALID`,
and exits non-zero. The thresholds are controlled by `--max-error-rate-pct`
and `--max-rate-limit-error-rate-pct`.

Auto uses one suffix-only market rule for each ticker:

- `.NS` and `.BO` use the India clock (`Asia/Kolkata`) and the 09:15-15:30
  regular session.
- Every other code or ETF uses the U.S. clock (`America/New_York`) and the
  09:30-16:00 regular session.

Provider exchange metadata cannot change this routing. Premarket and
postmarket data are ignored. During a regular session Auto evaluates:

- the latest completed regular-session candle as the confirmed baseline; and
- the appropriate live preview or partial candle as a separate overlay.

Confirmed baseline BUYs remain visible in the main BUY count while live
continuation, weakening, or a new provisional candidate is reported in
dedicated Auto fields. Outside regular hours the ticker is `CLOSED` and uses
completed daily data only.

For a regular-session partial candle, the engine compares projected
full-session volume with ADV20 and separately records the raw partial-volume
ratio. A regular-session partial candle that otherwise qualifies as BUY is
emitted as `PROVISIONAL_BUY` with HOLD status. Auto performs the completed
confirmation internally; the operator does not need a second Completed run.

In the V16 `Details` worksheet, Beta and Alpha are placed immediately after
Price and Currency. The pane is frozen at `L2`, so columns A through K and the
header row remain visible while scrolling.

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
5. Market routing is suffix-only: `.NS`/`.BO` use India regular hours; every
   other code uses U.S. regular hours. Extended-hours data is ignored.

## Repository contents

- `Live_Scanner_v14.py` — unchanged V14 reference baseline.
- `Live_Scanner_v14_Enhanced.py` — enhanced threaded and historically
  contextual scanner.
- `Live_Scanner_v15.py` — hardened shadow scanner with suffix-based U.S./India
  Auto confirmation and separate momentum/entry audit states.
- `Live_Scanner_v16.py` — active V16 continuation of the simplified
  suffix-based U.S./India track.
- `docs/ENGINE_V15_SHADOW.md` — V15 hypotheses, thresholds, state logic, and
  activation safeguards.
- `docs/ENGINE_V16_SHADOW.md` — active V16 engine contract.
- `docs/VALIDATION_V15_SHADOW_2026-07-27.md` — V14 parity, unit, and historical
  shadow-state validation.
- `docs/VALIDATION_V15_BETA_ALPHA_2026-07-28.md` — V15 Beta/Alpha contract,
  live-provider smoke evidence, workbook checks, and regression results.
- `docs/VALIDATION_V15_INTRADAY_RESILIENCE_2026-07-28.md` — volume correction,
  provisional-candidate contract, rate-limit resilience, mode accounting, and
  live Intraday/Auto/Completed smoke evidence.
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
