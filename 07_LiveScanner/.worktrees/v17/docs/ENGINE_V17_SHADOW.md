# U.S. Previous-Session / Current-Session Momentum Review

Document role: supporting calculation and candle-construction specification

Primary authority: `MOMENTUM_ENGINE_MASTER_BLUEPRINT.md`

Status: implemented research mechanics; classification remains non-binding

## Purpose

V17 tests one narrow proposition:

> A momentum interpretation begins with the traded session before today.
> Completed 4-hour and 1-hour observations from today may describe how that
> daily thesis is developing, but may not rewrite the daily result.

V17 covers NYSE- and Nasdaq-listed U.S. equities only. Provider metadata must
verify both an equity instrument and a NYSE/Nasdaq venue. NYSE American, NYSE
Arca, ETFs, OTC instruments, India/NSE/BSE and other international markets are
out of scope.

V17 is a measurement engine. Its multi-timeframe classifications are shadow
diagnostics and are not approved entry rules.

## Immutable daily baseline

V17 carries forward V16's completed-daily calculation:

- daily EMA20, EMA50 and EMA200;
- completed weekly EMA20 and EMA50;
- MACD 12/26/9 and histogram behavior;
- ADX14 with +DI and -DI;
- RSI14;
- ATR14;
- Stochastic K9/D6;
- completed daily volume versus the prior 20 completed sessions;
- 20-, 60- and 120-session returns;
- EMA slopes, prior 52-week-high proximity and ATR extension; and
- V16's `NONE`, `WEAK`, `DEVELOPING` and `LEADER` shadow states.

The foundation is the traded session immediately before the current session,
not the previous calendar date. The XNYS exchange calendar resolves weekends,
market holidays and early closes for both NYSE and Nasdaq timing.

Today remains the current session before, during and after its official close.
Today's daily candle becomes the previous-session foundation only when the
next trading session begins.

Premarket, postmarket and partially formed daily candles never enter the daily
calculation.

## Intraday source and completion contract

V17 requests regular-session 30-minute adjusted OHLCV with `prepost=False`.
Only a source bar whose scheduled end is at or before the execution cutoff is
retained.

Completed source bars are aggregated without crossing a session boundary:

- `1h`: session-anchored 60-minute bars;
- `4h`: session-anchored 240-minute bars.

The U.S. regular session is 390 minutes, so it does not divide evenly into
60- or 240-minute observations. V17 does not relabel the resulting tails as
full timeframe candles:

- the final 30-minute normal-session tail is excluded from 1H indicators;
- the final 150-minute normal-session tail is excluded from 4H indicators;
- incomplete in-progress buckets are also excluded; and
- early-close sessions contribute only genuinely full-duration buckets.

Each timeframe reports the numbers of excluded short-tail and incomplete
buckets. Every retained 1H/4H observation reports its source count and duration
and has `bar_is_short = False`.

An active source, 1H or 4H bar is excluded. A prior-session lower-timeframe bar
may provide internal mathematical warm-up, but no prior-session 4H/1H state is
exposed, qualified or used as today's progression comparison.

## Indicator decision

MACD, Stochastic, RSI, ADX/DI, volume, ATR and EMA/price structure are
calculated on both completed intraday timeframes from the start.

They are retained now because backtesting needs the raw datapoints in order to
measure which indicators discriminate future outcomes. Their inclusion does
not mean that their weights or thresholds are approved.

Each timeframe reports:

- latest completed OHLCV and bar return;
- EMA20, EMA50 and EMA200 when sufficient history exists;
- MACD, signal, histogram and one-bar histogram change;
- ADX, +DI, -DI and one-bar ADX change;
- RSI and one-bar RSI change;
- ATR;
- Stochastic K, D, spread, spread change and bullish/bearish crosses;
- volume per minute, prior same-session-slot average and same-slot ratio;
- up to six descriptive support checks plus an explicit availability flag for
  every check;
- improved and regressed component lists;
- `BULLISH`, `SUPPORTIVE`, `MIXED` or `BEARISH` bias;
- `PROGRESSED`, `REGRESSED`, `MIXED` or `STABLE` progression; and
- `SUPPORTIVE`, `REGRESSING`, `MIXED` or `UNAVAILABLE` relation to the
  completed daily thesis.

ADX, RSI, Stochastic and MACD values are never compared numerically across
daily, 4H and 1H timeframes. Each is calculated and interpreted inside its own
history.

The bias uses only observed checks as its denominator. A missing EMA50, for
example, is reported as an unavailable trend check rather than silently
counted as bearish. Fewer than four observed checks produces
`INDICATORS_INCOMPLETE`.

## Volume normalization

Intraday volume is not compared with a full-session ADV20 and is not linearly
projected.

For each timeframe:

1. bar volume is divided by the bar's actual duration;
2. the resulting volume-per-minute rate is compared with up to 20 prior bars
   in the same session bucket; and
3. the current ratio and its change are reported.

This prevents an opening bar or an early-close/full-session tail from being
silently compared with a different category of volume observation.

## Combined shadow states

The daily status, daily signal and daily momentum state remain authoritative.
The completed current-session evidence produces a separate internal
development state:

| State | Meaning |
|---|---|
| `DAILY_UNQUALIFIED` | The completed daily primary regime is absent. |
| `INTRADAY_IGNITION_DAILY_UNQUALIFIED` | Both fresh intraday views are supportive, but the daily regime is absent. |
| `DAILY_MOMENTUM_INTRADAY_UNAVAILABLE` | Daily momentum exists, but no fresh completed intraday view is available. |
| `DAILY_MOMENTUM_REGRESSING` | At least one fresh completed intraday view is regressing. |
| `DAILY_MOMENTUM_PARTIALLY_SUPPORTED` | One fresh completed intraday view is supportive. |
| `DAILY_MOMENTUM_MIXED` | Fresh evidence exists but is not directionally decisive. |
| `TRUE_MOMENTUM_CANDIDATE` | The daily primary regime passes and both fresh completed 4H and 1H views are supportive. |

`TRUE_MOMENTUM_CANDIDATE` is deliberately not `TRUE_MOMENTUM_CONFIRMED`.
V17 always reports:

```text
v17_classification_active = False
v17_true_momentum_confirmed = False
v17_operational_status_unchanged = True
```

## Backtesting contract

Daily-only replay can use many years of adjusted OHLCV and can test whether the
previous-session context is reproducible. It cannot validate the incremental
value of current-session 4H/1H evidence.

A valid V17 multi-timeframe replay must have historical 30-minute regular-
session bars and must simulate a defined execution cutoff. At each replay
point:

1. the daily calculation sees data only through the traded session before the
   replay date;
2. the intraday calculation exposes only current-session source bars completed
   by the cutoff;
3. the 1H/4H aggregation is reconstructed using the exchange schedule known at
   that timestamp;
4. the complete diagnostic vector is saved before forward outcomes are joined;
5. entry-session and multiple forward-horizon returns, MFE and MAE are
   measured;
6. U.S. development states are compared out-of-sample; and
7. costs, slippage, liquidity and overlapping-position effects are disclosed.

Required evaluation periods include multiple bull, bear, high-volatility and
low-volatility regimes. Training/calibration periods must remain separate from
walk-forward and final holdout periods.

The current Yahoo interface provides only recent intraday history and no native
4H interval. It is sufficient for live diagnostics and short smoke replays,
not for a several-year 1H/4H conclusion. A multi-year 30-minute archive or
licensed data source is therefore a prerequisite for activation.

No V17 or V17 variant may be described as genuinely identifying momentum until
the multi-year, timestamp-correct, out-of-sample evidence is positive and the
owner approves a separate activation change.

## Runtime delivery profile

The planned runtime path uses free-access sources only and keeps downloaded
market history in memory for the current run. It must not require a local
universe file, historical database, historical-data folder, persistent
market-data cache or resume checkpoint.

For a small explicit code list, every verified symbol receives the daily
foundation and current-session enrichment. For a large list or the complete
runtime Nasdaq/NYSE universe, daily history is downloaded in bulk and the
unchanged daily calculation is applied to every accepted symbol first. Only
daily-qualified candidates receive the slower metadata and recent 30-minute
enrichment.

Execution-lane choice, batch size, concurrency and input population may change
speed only. They may not change a shared stock's daily foundation,
classification or completed 1-hour/4-hour construction. Provider failures and
omitted enrichment must be visible and may not be interpreted as negative
market evidence.

## Running the live shadow

```powershell
python .\Live_Scanner_v17.py `
  -c AAPL MSFT NVDA `
  --live-candle-mode completed `
  -o .\output\Momentum_Review.xlsx
```

The visible workbook records the previous-session daily foundation and
plain-language current-session 4H/1H review. Technical diagnostics are retained
in a hidden sheet for reproducibility.

The `--universe nasdaq|nyse|all` interface is approved in the execution plan
but is not implemented at this planning baseline.
