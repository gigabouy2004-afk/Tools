# V17 D1/MTF Validation Record — 2026-07-29

> Historical record: this document used `D1` to mean the daily timeframe.
> Human-readable output now uses `1D`, `previous completed session`, `current
> session` and `next session`. The numerical five-year findings remain
> unchanged.

## Decision

V17 remains a non-binding research engine.

The completed-D1 data foundation is reproducible, but the inherited V16 daily
BUY rules did not demonstrate stable positive expectancy over the measured
five-year period. The incremental 4H/1H hypothesis has not been validated
because a several-year, timestamp-correct 30-minute archive is not available
in the workspace.

No output from this work is approved as `TRUE_MOMENTUM_CONFIRMED`, an
operational BUY override, or evidence that V17 genuinely identifies momentum.

## Implemented contract

- Universe: provider-verified equity instruments listed on NYSE or Nasdaq.
- Excluded: NYSE American, NYSE Arca, ETFs, OTC, India and other international
  listings.
- Daily authority: latest fully completed XNYS regular-session candle.
- Calendar: exchange sessions, holidays and early closes from the XNYS
  calendar.
- Extended hours: excluded.
- Intraday source: completed regular-session 30-minute bars only.
- 1H/4H construction: session anchored and never crosses sessions.
- Short tails: the normal 30-minute 1H tail, normal 150-minute 4H tail and
  early-close tails are excluded, counted and never relabelled as full bars.
- Intraday authority: descriptive only; it cannot change the D1 status.
- `TRUE_MOMENTUM_CANDIDATE`: requires a qualifying daily regime plus both a
  fresh completed 4H and fresh completed 1H supportive view.
- `v17_true_momentum_confirmed`: always `False`.

## Five-year completed-D1 reference replay

Command:

```powershell
python .\v17_us_daily_backtest.py `
  --years 5 `
  --history-period 8y `
  --evaluation-windows 1,2,3,5 `
  --output-dir .\output\V17_D1_Backtest_5Y_20260729 `
  --batch-size 50 `
  --batch-pause 0.25 `
  --timeout 30
```

Method:

- measured interval: 2021-07-29 through 2026-07-29;
- 8 years requested to warm EMA200 and 50 completed weekly observations;
- current master-file universe: 3,445 NYSE/Nasdaq non-ETF symbols;
- 3,236 symbols processed, 208 had insufficient history and one had no data;
- signal entry: next trading-session open;
- exit: fifth trading-session close;
- same-symbol trades do not overlap; and
- Yahoo adjusted daily OHLCV was the external source.

Audit status: `PASS`.

| Window | Trades | Win rate | Mean return | Median | Profit factor |
|---|---:|---:|---:|---:|---:|
| 1 year | 8,954 | 50.86% | +0.1836% | +0.1272% | 1.0624 |
| 2 years | 15,124 | 49.66% | +0.0014% | 0.0000% | 1.0005 |
| 3 years | 21,494 | 50.09% | +0.0326% | +0.0177% | 1.0124 |
| 5 years | 30,620 | 49.59% | **-0.0627%** | -0.0110% | **0.9756** |

The five-year 1st/99th-percentile winsorized mean was -0.0813%. An illustrative
20 bp round-trip cost changed the five-year mean to -0.2627% and profit factor
to 0.9015.

The recent period does not rescue the result. The trailing one-year gross mean
was positive, but a 20 bp assumption makes it approximately -0.0164%. The 2026
partial-year slice was +0.1819% gross and -0.0181% after 20 bp.

### Inherited signal families

| Signal | Trades | Mean return | Profit factor |
|---|---:|---:|---:|
| Momentum Extension | 25,107 | -0.1004% | 0.9605 |
| Early Momentum | 5,429 | +0.1099% | 1.0413 |
| EMA20 Midrange Recovery | 69 | +0.6107% | 1.2514 |
| Pullback/Oversold Recovery | 15 | -2.4337% | 0.5592 |

The two small families are too sparse for a conclusion. Early Momentum's gross
advantage does not survive a 20 bp assumption across the complete sample.
Momentum Extension, which supplies 82% of trades, is negative before costs.

### Regime instability

Aggregate yearly gross means ranged from +0.1819% in the partial 2026 slice to
-0.6648% in 2022. The rule set was negative in 2022, 2023, 2024 and 2025, and
the positive 2021 and 2026 slices were negative after the illustrative 20 bp
cost.

This supports the user's requirement for multiple regimes: a recent favorable
window alone would have produced a misleading conclusion.

## Indicator diagnostics

MACD, Stochastic, RSI, ADX/+DI/-DI, volume, ATR, EMA structure, returns and
slopes should remain in V17 from the start as recorded datapoints. Their
weights and gate authority should remain deferred.

The descriptive slices are heterogeneous and non-monotonic:

- ADX >= 50 had 921 trades with a -1.6531% mean, consistent with possible
  exhaustion rather than an automatic momentum advantage.
- RSI >= 80 had 1,999 trades with a -0.6045% mean.
- a quality score of 5 had a +0.3460% mean, while score 6 was -0.3587% and
  score 8 was -0.2580%; the inherited equal-weight score is not calibrated.
- Early Momentum with a 1.00–1.20 daily volume ratio had 1,083 trades and a
  +0.2613% gross mean, but only +0.0613% after 20 bp and no separate holdout
  validation.
- rising five-observation ADX alone was negative on the full descriptive
  sample.

These are overlapping exploratory slices, not deployable gates. They justify
retaining the full diagnostic vector and using calibration, walk-forward and
holdout datasets before changing a threshold.

## Multi-timeframe validation status

The deterministic tests validate candle construction, timestamp cutoffs,
holiday/early-close behavior, completed-week handling, short-tail exclusion,
indicator calculation, freshness and the non-binding daily/MTF contract.

The available Yahoo interface supplies only a recent intraday window and no
native historical 4H series. A recent smoke replay is suitable only for
mechanics and is not accepted as performance evidence. The final live-provider
smoke attempt also timed out while requesting metadata/history, reinforcing
that it must not be used as the research archive.

Required next dataset:

- several years of split-adjusted 30-minute OHLCV;
- regular-session timestamps with exchange timezone and corporate-action
  provenance;
- NYSE/Nasdaq symbols including delisted names or a point-in-time universe;
- enough history for 4H EMA200 warm-up before the measured period; and
- immutable files or versioned vendor extracts for reproducibility.

The replay harness accepts long-form CSV or Parquet daily and 30-minute
archives and records each D1/4H/1H scalar before joining 1-, 5-, 10- and
20-session forward return, MFE and MAE outcomes.

## Known research limitations

- The daily replay uses the current master-file universe and is therefore
  exposed to survivorship and point-in-time membership bias.
- It is a signal-cohort replay, not a capital-constrained portfolio simulation.
- The reported cohort drawdown is not a portfolio drawdown.
- Slippage, spread, borrow, stops, position sizing and portfolio concurrency
  are not modeled.
- Descriptive indicator slices reuse the same sample and can be overfit.
- Daily results cannot establish the incremental value of 4H/1H evidence.

## Gate assessment

| Gate | Status | Evidence |
|---|---|---|
| Completed-candle/calendar mechanics | Pass | Deterministic tests |
| D1 inherited-rule stability | Fail | Negative five-year gross and cost-adjusted result |
| Multi-year MTF increment | Blocked by data | No replayable multi-year 30-minute archive |
| Out-of-sample calibration | Not started | Requires archive and frozen hypotheses |
| Production activation | Not approved | Shadow flags remain non-binding |
