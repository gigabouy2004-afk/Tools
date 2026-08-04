# V15 Intraday and Yahoo-Resilience Validation

Date: 2026-07-28

## Scope

This deployment addresses the all-U.S. Intraday, Auto, and Completed run review
without changing the frozen completed-candle V14 classification rules.

The source exports showed two independent causes for the misleading result:

1. Intraday cumulative volume was compared directly with full-session ADV20,
   suppressing volume confirmation early in the session.
2. The two Auto exports were materially incomplete because Yahoo rate limiting
   produced thousands of error rows. Those runs could not support a
   market-wide conclusion.

Partial BUY candidates were also downgraded to an ordinary HOLD, making them
indistinguishable from non-candidates in the output.

## Implemented contract

### Partial-candle volume

- `raw_volume_ratio` retains cumulative volume divided by ADV20.
- During the regular session, `relative_volume_ratio` uses projected
  full-session volume divided by ADV20.
- `intraday_elapsed_session_fraction`,
  `projected_full_session_volume`, and `volume_ratio_basis` make the adjustment
  auditable.
- Completed candles retain the original full-session volume comparison.
- Premarket partial volume is `PREMARKET_UNCONFIRMED`; it is not projected or
  allowed to masquerade as a completed-session comparison.

### Provisional entries

- A partial candle that otherwise passes the existing BUY logic is reported as
  `PROVISIONAL_BUY`.
- The original qualifying signal and classification are retained in dedicated
  fields.
- Executable `status` and the shadow recommendation remain HOLD until a
  completed candle confirms the setup.
- Extension, ADX, volume, and leadership risk gates retain precedence over the
  provisional-confirmation state.

### Exchange-local Auto

- Market phase is resolved independently for every ticker from its listing
  timezone and provider trading-period metadata.
- Premarket, regular, postmarket, closed, holiday, and early-close conditions
  are not inferred from one global NYSE clock.
- During an active session, Auto evaluates the completed regular-session
  baseline and the live exchange-local overlay in one run.
- A confirmed baseline BUY remains the primary BUY result. The live view is
  attached as supportive, mixed, weakening, unavailable, or provisional.
- When the completed baseline is not BUY, a qualifying live setup remains HOLD
  and is reported as `PROVISIONAL_BUY`.
- Postmarket preview prices do not overwrite official regular-session volume.
- Closed listings use completed data only; no live overlay is fabricated.

### Provider resilience

- All live signal-critical Yahoo requests use process-wide pacing.
- Transient failures and HTTP/rate-limit symptoms use coordinated exponential
  retry/backoff.
- Daily history is reused through an in-memory cache and a cross-process
  persistent cache.
- Non-critical Beta/Alpha enrichment is disabled by default and can be enabled
  explicitly with `--include-beta-alpha`.
- Backtest history uses the same resilient request wrapper.

### Run integrity and output

- Each row records requested mode, effective mode, candle state, confirmation
  state, and whether a fallback occurred.
- The terminal/log summary reports momentum-state counts, provisional symbols,
  effective-mode counts, candle-state counts, fallback count, total error rate,
  and rate-limit error rate.
- Runs above either configurable error threshold are marked `INVALID`, the
  diagnostic workbook is preserved, and the process exits non-zero.
- Case-insensitive duplicate `Message`/`message` headers were replaced with
  unique `Display Message` and `Internal Message` headers.

## Automated validation

Command:

```powershell
python -m unittest discover -s LiveScreener\tests -p 'test_*.py' -v
```

Result: 64 tests passed.

The fifteen deployment tests cover:

- regular-session elapsed fraction;
- adjusted versus raw partial volume;
- unchanged completed-session volume;
- unconfirmed premarket volume;
- explicit provisional BUY preservation;
- entry-risk precedence;
- rate-limit retry;
- invalid-run detection and mode/fallback accounting; and
- case-insensitive output-header uniqueness;
- NYSE premarket, regular, postmarket, and closed boundaries;
- same-instant phase resolution for listings on different exchanges;
- postmarket bar filtering;
- postmarket price preview without corrupting official volume; and
- Auto precedence between confirmed and provisional results.

Both maintained V15 entry points compile successfully.

Both deployed copies are byte-identical:

```text
SHA256 42192C6C689D95595625F7A9BCAAA63C9A0444823D6DA21DBE99467328B5CE6E
```

## Live smoke validation

Symbols: AAPL, MSFT, NVDA

Common controls:

- one worker;
- four Yahoo attempts;
- 0.25-second process-wide minimum request interval;
- persistent daily cache enabled;
- Beta/Alpha enrichment disabled.

| Requested mode | Processed | Errors | Rate limits | Effective mode | Candle state | Fallbacks | AAPL result |
|---|---:|---:|---:|---|---|---:|---|
| Intraday | 3/3 | 0 | 0 | intraday | CURRENT_PARTIAL | 0 | PROVISIONAL_BUY / HOLD |
| Auto | 3/3 | 0 | 0 | auto_dual | LAST_COMPLETED + CURRENT_PARTIAL | 0 | confirmed BUY + live mixed overlay |
| Completed | 3/3 | 0 | 0 | completed | LAST_COMPLETED | 0 | confirmed BUY |

All three smoke runs reported `Run quality: VALID`.

The comparison demonstrates the intended behavior: Auto retains the completed
confirmation and evaluates the active candle at the same time. No second
operator-launched Completed run is required.

### Cross-exchange smoke

One Auto scan evaluated AAPL, RELIANCE.NS, and 7203.T at the same instant:

- AAPL: `REGULAR`, `auto_dual`, completed BUY plus current partial overlay;
- RELIANCE.NS: `CLOSED`, completed-only;
- 7203.T: `CLOSED`, completed-only.

The run processed 3/3 symbols with zero errors, zero rate-limit failures, and
zero fallbacks. The phase breakup was `{'REGULAR': 1, 'CLOSED': 2}`.

## Operational interpretation

A zero confirmed-BUY count in Intraday is not equivalent to “there is no
momentum.” Auto now reports completed BUYs and live provisional candidates
together. Operators should review:

- momentum-state counts;
- confirmed-baseline BUY count and symbols;
- provisional BUY count and symbols;
- Auto combined states and action source;
- exchange-phase and live-overlay breakups;
- requested versus effective mode;
- candle state and fallback count; and
- run-quality status and error-rate fields.

Only a `VALID` run should be used for a universe-wide conclusion.
