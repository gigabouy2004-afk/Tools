# Changelog

## Unreleased - V16 simplified U.S./India track

### Added

- Independent `Live_Scanner_v16.py` executable created from the simplified
  suffix-based U.S./India implementation.
- V16-specific runtime identifiers, diagnostic fields, output filenames, cache
  directory, worker labels, documentation, and routing tests.

### Version boundary

- V15 is frozen. Further implementation work belongs to V16.

## Unreleased - V15 shadow momentum quality

### Changed

- Simplified live market routing to two suffix-based rules: `.NS`/`.BO` use
  India regular hours in IST; every other code or ETF uses U.S. regular hours
  in New York time.
- Removed metadata-driven exchange/timezone switching and all premarket and
  postmarket evaluation paths. Outside regular hours Auto uses completed daily
  data only.

### Added

- Independent `Live_Scanner_v15.py` entry point based on validated V14 Enhanced
  commit `20641f5`.
- Non-binding `LEADER`, `DEVELOPING`, `WEAK`, and `NONE` momentum-quality
  states.
- Non-binding entry states that distinguish confirmed candidates from ADX,
  volume, extension, leadership, and V14-trigger waits.
- Shadow measurements for EMA50/EMA200 slopes, 20/60/120-session returns,
  positive/negative directional movement, five-session ADX change, proximity
  to the prior 52-week high, volume confirmation, and ATR extension.
- Explicit shadow summaries in terminal, log, and workbook output.
- Focused unit coverage for quality scoring, entry-state precedence, and the
  frozen-classification contract.
- Approval-ready V14-to-V15 handover covering engine intent, checks and
  balances, input/output and messaging contracts, local/GitHub manifests,
  Phase 2 boundaries, and explicit owner signoff.
- Focused regression coverage for compact and spaced comma-separated direct
  code strings, mixed argument segments, normalization, and duplicate removal.
- Live Beta for equity and ETF rows, with live three-year Alpha for ETF rows.
- `Details` worksheet placement immediately after Price and Currency, with the
  pane frozen at `L2` after Alpha.
- Focused provider parsing, stock/ETF contract, missing-data, and workbook
  layout coverage for Beta and Alpha.
- Elapsed-session-adjusted relative volume for regular-session partial candles,
  while retaining the raw partial-volume ratio and projected full-session
  volume as separate audit fields.
- Explicit `PROVISIONAL_BUY` reporting for BUY setups formed on a partial
  candle. The executable status remains HOLD until a completed candle confirms
  the setup.
- Requested/effective candle modes, candle state, confirmation state, and
  fallback use in every detail row and the post-run summary.
- Process-wide Yahoo request pacing, coordinated exponential retry/backoff, and
  a reusable persistent daily-history cache.
- Run-quality thresholds that mark materially incomplete or rate-limited runs
  `INVALID` and return a non-zero process exit after preserving the output.
- Unique user-facing `Display Message` and `Internal Message` spreadsheet
  headers, replacing the previous case-insensitive `Message`/`message`
  collision.
- Nine focused regression tests for intraday relative volume, provisional
  entries, rate-limit retry, run validity, mode accounting, and output schema.
- Exchange-local Auto resolution for each ticker using listing timezone and
  provider trading-period metadata, including early-close and holiday state.
- Dual-state Auto evaluation: the completed regular-session baseline and the
  available premarket, regular-session, or postmarket overlay are evaluated in
  one run.
- Explicit confirmed-baseline, live-overlay, combined-state, exchange-phase,
  and action-source fields in detail rows and terminal/log summaries.
- A postmarket price-preview path that preserves official regular-session
  volume and treats all extended-hours measurements as provisional.
- Six regression tests for NYSE phase boundaries, same-instant cross-exchange
  resolution, postmarket filtering/merging, and Auto result precedence.

### Changed

- Beta/Alpha enrichment is now opt-in with `--include-beta-alpha`, preventing
  non-critical enrichment requests from consuming the live signal-data quota.
- Backtest history requests now use the same pacing, retry, and empty-response
  handling as live history requests.

### Validation

- 64/64 V15 and inherited V14 regression tests pass.
- Live AAPL/MSFT/NVDA smoke runs in Intraday, Auto, and Completed modes each
  processed 3/3 symbols with zero errors and zero rate-limit failures.
- Exchange-local Auto retained AAPL's completed-candle BUY while simultaneously
  evaluating its current NYSE regular-session overlay.
- One mixed AAPL/RELIANCE.NS/7203.T run independently resolved one `REGULAR`
  U.S. listing and two `CLOSED` Asian listings, with zero errors or fallbacks.

### Safety

- Completed-candle V14 classifications remain unchanged. Auto selects that
  completed result as the primary action when it is a confirmed BUY and
  reports the live view separately.
- V14 files remain unchanged and continue to be the operational baseline.
- Historical/as-of rows leave Beta and Alpha blank to avoid present-data
  look-ahead.
- Custom benchmark-relative ranking remains deferred; provider-supplied Beta
  and ETF Alpha are descriptive and non-binding.
- Partial-candle candidates never become executable BUY rows: they remain HOLD
  with an explicit provisional classification until completed-candle
  confirmation.
- Premarket volume is labeled unconfirmed rather than being compared with a
  full-session ADV20.

## 2026-07-27 - V14 Enhanced positive-regime scope correction

- Removed pre-bull/pre-bear crossover concepts from V14 Enhanced classification.
- Removed the generic one-bar histogram-improvement shortcut from continuation,
  pullback, confidence scoring, and HOLD labels.
- Required MACD, signal, and histogram to confirm an established positive MACD
  regime before any pullback BUY path can qualify.
- Required the configured histogram window to be strictly expanding, with its
  latest two bars positive, for momentum-continuation BUY eligibility.
- Added strict HOLD outcomes for positive price trends whose MACD momentum is
  unconfirmed or whose MACD zero gate is not met.
- Gated ADX, volume, price-response, and recovery score contributions behind
  daily trend, weekly trend, and established positive MACD confirmation.
- Added boundary tests covering negative histogram improvement, negative-to-
  positive transitions, non-sustained one-bar improvement, and positive cooling.
- Applied the live BUY quality-policy layer during built-in historical replay so
  backtest classifications match live/as-of engine policy.

### Validation

- Original and enhanced engines compile.
- 24/24 focused unit tests pass.
- GLOSTERLTD.NS on 2026-07-24 is strict HOLD/NO_BUY with a capped 4/10 setup
  score.
- XLI regression BUY counts are 0, 2, and 3 for 2026-07-22 through 2026-07-24.
- The 19-symbol audit produces 3 BUY, 11 HOLD, 2 IGNORE, and 3 ERROR rows.
- All retained BUYs pass the positive EMA/MACD/histogram invariants.
- A three-year, five-session XLI replay produces 124 trades, a 52.42% win rate,
  and a 0.43% average return before costs and execution assumptions.

## Unreleased

### Added

- Prominent `DataThrough` reporting in per-run messages, terminal/log summaries,
  and the workbook Summary sheet.
- Approved P1 quality fields for the mandatory volume floor, U.S. ADV20
  liquidity floor, and extreme-extension review state.
- Unit coverage for single-session, mixed-market, and all-error data-through
  summaries, plus boundary coverage for all three P1 policies.

### Changed

- Detail rows now report the actual final daily session included in the
  evaluation frame instead of repeating a weekend, holiday, or requested
  historical as-of label.
- BUY#4 now requires a fresh bullish MACD signal-line crossover with both lines
  above zero and a positive histogram. Negative-histogram improvement is outside
  the engine's signal mandate and receives no pre-crossover classification.
- Current volume ratio must be at least `0.60` before the immediate-ratio or
  one-year-percentile volume-support paths can qualify a BUY.
- U.S. BUY candidates must have at least USD 1 million prior-20-session average
  daily turnover; candidates below the floor become HOLD/`NO_BUY`.
- BUY candidates more than 5 ATR above EMA50 retain BUY status but are labeled
  `BUY_EXTENDED_REVIEW`.
- Detail output expanded from 107 to 113 columns for explicit policy audit
  fields.

## 2026-07-25 — V14 Enhanced handover

### Added

- Bounded concurrent polling with deterministic input-order result retention.
- Poll-boundary `Max-Count` and `Max-Buys` continuation triggers.
- Independent per-ticker one-year RSI, ADX, stochastic, price, and volume
  context.
- Advisory adaptive historical guidance:
  - 100 or fewer input tickers: maximum available history.
  - 101–1,000 input tickers: five years.
  - More than 1,000 input tickers: one year.
- Positive-phase early-momentum and momentum-continuation signal paths.
- Previous-positive-session stochastic relaxation after a BUY is detected.
- Multi-market session and listing-currency metadata in the output.
- Historical as-of and multi-date validation modes.
- Workbook output expanded to 107 columns.
- Engine guide, validation report, and session handover/signoff documentation.

### Changed

- RSI and ADX upper values are historical context rather than universal hard
  rejection limits.
- ADX current value versus the ticker's prior maximum is reported as confidence
  context and is not a qualification gate.
- Volume support may come from either the current 20-day volume ratio or the
  ticker's one-year absolute-volume percentile.
- Price and indicator historical guidance is calculated without including the
  current candle.

### Validation

- XLI top-ten regression produced 2, 5, and 3 BUYs on 2026-07-22,
  2026-07-23, and 2026-07-24 respectively.
- Full U.S. scan processed 3,636 symbols in 19 minutes 14 seconds.
- Independent fresh-data audit reproduced all 19 sampled statuses, signals,
  prices, and indicator values.

### Known limitations

- The current volume-support OR rule can qualify a ticker even when its current
  volume is materially below its 20-day average.
- No minimum average daily turnover or minimum local-currency price gate is
  enabled.
- Highly extended momentum can remain a BUY with an elevated risk label.
- The run-level `AsOf` label can be a non-trading date; use `session_date` and
  `candle_state` to identify the actual data-through session.
- Sparse/low-liquidity Yahoo daily bars can disagree with intraday quote data.
