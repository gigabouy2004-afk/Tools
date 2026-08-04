# Momentum Identification Research Protocol

## Purpose

This work builds an evidence-based stock-level momentum identification layer.
It does not add another production rule or rename an unvalidated result as
genuine momentum.

The completed-candle machinery remains the data foundation. The research layer
records what was knowable at the time, measures what happened afterwards and
uses chronological evidence to determine which stock-level characteristics are
actually useful.

## Time terminology

The following terms are used in all human-readable material:

| Term | Meaning |
|---|---|
| Previous completed session | The last traded day before the current session |
| Current session | Now/today, whether premarket, regular hours or after close |
| 1D | The daily timeframe; never an abbreviation for next session |

During the current session:

1. The daily foundation contains completed daily and weekly observations only
   through the previous completed session.
2. No 4-hour or 1-hour state from the previous session is displayed, qualified
   or compared with today's progression.
3. Completed lower-timeframe observations from the current session describe
   what is happening now.
4. The first completed current-session bar is explicitly the starting
   observation. It is not described as improving or regressing relative to a
   prior-day lower-timeframe bar.
5. Future sessions are used only after the feature record is frozen, and only
   for research outcomes.

Standard MACD, ADX, RSI and Stochastic calculations need historical
lower-timeframe warm-up observations. Those records may be used internally for
the mathematics, but they never become a previous-session 4-hour/1-hour
opinion, output or progression comparison.

Even after today's official close, today remains the current session. Its
completed daily candle becomes the previous completed-session foundation only
when the next trading session begins.

## Stock-history tracks

Missing stock history is never filled with sector or industry prices.

The initial research tracks are:

| Available completed sessions | Human-readable group | Treatment |
|---:|---|---|
| Fewer than 20 | Observation only | Record data; do not model momentum |
| 20–119 | Young listing | Young-listing research features |
| 120–251 | Developing history | Reduced-history research features |
| 252 or more | Established history | Standard-history research features |

These boundaries are research scaffolding, not approved classifier thresholds.
The final boundaries must be justified by coverage, indicator availability and
chronological outcome stability.

Every newly listed equity remains in the panel. Unavailable EMA200, weekly
EMA50 or other long-history fields remain blank and carry explicit availability
fields. Missing evidence is not counted as positive or negative.

## Sector and industry use

Sector and industry are optional point-in-time context:

- outcome base rates for similar-age listings;
- fixed benchmark-relative strength;
- market/industry regime analysis; and
- cautious statistical shrinkage when a young equity has little history.

They never create synthetic stock indicators. The stock's own observations
must increasingly dominate as its history grows. A later modeling phase must
report whether the estimate uses stock, industry, sector or market-level
context and must lower confidence when only a broad prior exists.

No result may depend on which other symbols happen to be present in the user's
watchlist.

## Daily feature record

One record is created for every completed stock/session combination, not just
for existing scanner BUY rows.

The record includes:

- listing age and eligible research track;
- daily OHLCV;
- EMA20, EMA50 and EMA200 with availability;
- completed weekly price, EMA20 and EMA50;
- MACD, histogram and histogram change;
- ADX, +DI, -DI and five-session ADX change;
- RSI and Stochastic;
- 5-, 10-, 20-, 60- and 120-session historical returns;
- EMA slopes;
- prior-volume ratio and turnover;
- ATR-normalized extension;
- prior 52-week and post-listing range context; and
- plain descriptions of structure, participation and extension.

The descriptions are research aids. They are not a momentum classification.

## Future outcome record

The current provisional research contract uses:

- hypothetical entry at the open of the trading session immediately after the
  daily foundation (the current session in a historical replay);
- forward return, maximum favourable excursion and maximum adverse excursion
  over 5, 10 and 20 sessions; and
- a provisional ten-session path label using +2 ATR and -1 ATR barriers.

If both barriers are touched within one daily candle, the order is reported as
unknown. If the archive ends before the horizon, the outcome is incomplete
rather than assumed flat or successful.

The ATR barriers are starting labels for distribution analysis. They are not
approved trading thresholds and may not be optimized against the final
holdout.

## Required archive

A promotion-quality archive must provide:

- point-in-time NYSE/Nasdaq listing status;
- a stable security identifier that survives ticker changes;
- equity/ETF identification;
- daily split- and distribution-adjusted OHLCV;
- listing and delisting dates;
- delisting returns or terminal-value treatment;
- point-in-time sector and industry where available;
- corporate-action provenance;
- inactive and delisted securities; and
- immutable source/version identifiers.

Using only today's surviving constituents is acceptable for mechanical smoke
testing but not for approval research.

## Chronological research periods

Random train/test splitting is prohibited.

The panel builder separates:

1. training;
2. calibration;
3. untouched holdout.

Observations whose forward outcome crosses a period boundary are removed from
that period. The holdout remains untouched until the feature set, outcome
definition, model family and promotion gates are frozen.

## Development sequence

1. Measure unconditional outcomes by year, market regime and stock-history
   group.
2. Measure the inherited scanner rules against that base rate.
3. Study each feature's stability and interactions without creating a new BUY.
4. Build transparent stock-level probability baselines.
5. Compare a nonlinear challenger only after the transparent model is stable.
6. Freeze the daily model and test it chronologically.
7. Acquire multi-year 30-minute data.
8. Test whether current-session 4-hour/1-hour evidence adds measurable value to
   the identical daily candidates.
9. Run a live shadow period before any activation proposal.

## User-facing output

The visible workbook contains:

- `Summary`: execution and data-quality totals in plain language;
- `Review`: one readable row per stock; and
- a hidden `Technical Data` sheet retained only for reproducibility.

Version identifiers, shadow flags and internal state names are excluded from
the visible review and text log. Research/backtest fields use descriptive
column names and are accompanied by this protocol.

## Current status

The data panel and chronological validation framework are infrastructure only.
No genuine-momentum classifier has been trained, calibrated, validated or
approved.
