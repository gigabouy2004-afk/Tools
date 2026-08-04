# Changelog

## Unreleased - Daily momentum research foundation

### Added

- Plain previous-session/current-session terminology for visible output.
- Visible `Review` workbook sheet with layman-readable daily, 4-hour and 1-hour
  explanations; implementation flags are retained in a hidden technical sheet.
- Point-in-time daily feature and future-outcome panel builder.
- Observation-only, young-listing, developing-history and established-history
  tracks without synthetic long-history indicators.
- Hypothetical-entry-open 5/10/20-session return, MFE, MAE and provisional
  ATR-path outcomes, where entry is the session immediately after the daily
  foundation.
- Chronological training/calibration/holdout assignment with boundary purging.
- Research protocol, field guide and validation record.

### Changed

- Today remains the current session after its close; its daily candle does not
  become the foundation until the next trading session.
- Only today's completed lower-timeframe bars are exposed. Prior-session
  lower-timeframe records are mathematical warm-up only.
- The first completed lower-timeframe bar today is a starting observation and
  is not compared with yesterday's lower-timeframe bar.

### Validation

- 78 deterministic/regression tests pass.
- A 1,255-row cached-data smoke retained all history tracks and correctly
  excluded outcomes crossing chronological boundaries.
- No classifier or production rule was introduced.

## Unreleased - V17 completed-D1 / MTF shadow

### Added

- U.S.-only V17 research entry point carrying forward the V16 completed-daily
  calculation.
- XNYS calendar handling for sessions, holidays, weekends, early closes and
  completed trading weeks.
- Session-anchored full-duration 1H and 4H diagnostics reconstructed from
  completed regular-session 30-minute bars.
- EMA, MACD, ADX/DI, RSI, ATR, Stochastic and same-slot volume evidence on each
  intraday timeframe.
- Explicit progress/regress fields, support-check availability, short-tail
  exclusions and freshness flags.
- Multi-year completed-D1 backtester, 30-minute archive replay harness and
  descriptive diagnostic analyzer.
- Deterministic V17 calendar, scope, candle, indicator, freshness and replay
  tests.

### Validation

- 64 tracked deterministic/regression tests pass.
- Five-year daily reference replay covered 3,445 strict NYSE/Nasdaq non-ETF
  symbols, processed 3,236 and produced 30,620 non-overlapping five-session
  trades with a -0.0627% gross mean and 0.9756 profit factor.
- The D1 rules fail the promotion gate. Multi-year 4H/1H efficacy remains
  untested pending a replayable several-year 30-minute archive.

### Safety

- Partial daily and extended-hours candles cannot enter V17.
- Short end-of-session tails are excluded rather than relabelled as complete
  1H/4H bars.
- Provider metadata must verify both an equity instrument and NYSE/Nasdaq
  listing.
- V17 always leaves classification activation and true-momentum confirmation
  false.

## Unreleased - V15 shadow momentum quality

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

### Safety

- V15 shadow fields do not modify `status`, `classification`, or
  `output_signal`.
- V14 files remain unchanged and continue to be the operational baseline.
- Historical/as-of rows leave Beta and Alpha blank to avoid present-data
  look-ahead.
- Custom benchmark-relative ranking remains deferred; provider-supplied Beta
  and ETF Alpha are descriptive and non-binding.

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
