# V5 Threshold Refinement And Random-20 Backtest

Date: 2026-06-29

## Scope

This pass addressed the brittle daily timing threshold exposed by BTX.

The prior rule could leave a symbol actionable even when it had:

- a daily distribution move,
- close below EMA20,
- lower high and lower low,
- but `Distance_From_20D_High_Pct` had not crossed the fixed `-8%` threshold.

BTX was the concrete example:

- `Daily_Change_Pct`: about `-3.63%`
- `Close_Below_EMA20`: `True`
- `Distance_From_20D_High_Pct`: about `-7.26%`
- `Lower_High_Day`: `True`
- `Lower_Low_Day`: `True`

Under the refined rule, BTX becomes:

- `Entry_Timing_Status`: `Wait - Daily Pullback Risk`
- `Action_Status`: `Downgraded - Wait`

## Code Changes

The hardcoded timing values were moved into named constants:

- `DAILY_PULLBACK_DEEP_20D_HIGH_PCT = -8.0`
- `DAILY_PULLBACK_EARLY_20D_HIGH_PCT = -5.0`
- `DAILY_PULLBACK_5D_RETURN_PCT = -3.0`
- `DAILY_DISTRIBUTION_DROP_PCT = -3.0`
- `HIGH_VOLUME_PULLBACK_MAX_GAIN_PCT = 0.5`
- `INTRADAY_SELLING_3H_RETURN_PCT = -1.0`
- `BEARISH_HOURLY_CANDLES_CONFIRMATION = 2`

The added daily timing gate is:

- If the stock is below EMA20,
- and has a daily distribution drop,
- and has lower-high/lower-low or above-average-volume pullback,
- then downgrade timing to `Wait - Daily Pullback Risk`.

This reduces cliff behavior around the old `-8%` distance threshold.

## Random Sample

Fixed random seed: `20260629`

Sample tickers:

`FTCI`, `DOCU`, `STX`, `AEIS`, `PPLI`, `NVNI`, `TMS`, `MBLY`, `AUID`, `DUOT`, `LASR`, `CYCU`, `INFY`, `KBDC`, `LITE`, `QNT`, `UIS`, `XTIA`, `LDOS`, `NXTT`

## Live Current-State Scan

Output file:

`backtests/V5_Random20_Live_Scan_20260629.csv`

Action counts:

| Action_Status | Count |
|---|---:|
| Avoid | 16 |
| Downgraded - Wait | 2 |
| Watchlist Candidate | 1 |
| Rejected - Distribution Risk | 1 |

Names requiring attention:

| Ticker | Action_Status | Entry_Timing_Status | Score |
|---|---|---|---:|
| UIS | Watchlist Candidate | Clean | 79 |
| PPLI | Downgraded - Wait | Wait - Last Hour Bearish | 81 |
| STX | Downgraded - Wait | Wait - Daily Pullback Risk | 75 |
| LITE | Rejected - Distribution Risk | Failed - Distribution Risk | 39 |

## Daily Historical Backtest

Output files:

- `backtests/V5_Random20_Daily_Backtest_Signals_20260629.csv`
- `backtests/V5_Random20_Daily_Backtest_Summary_20260629.csv`

Method:

- Daily data only.
- Historical intraday and extended-hours data were not used.
- Non-overlapping signal spacing: 21 trading days.
- Forward returns measured at 21D and 63D from next open to future close.

Signals generated: `250`

Action bucket summary:

| Action_Status | Signals | Avg Forward 21D | Avg Forward 63D |
|---|---:|---:|---:|
| Actionable Momentum Candidate | 153 | 3.56% | 9.93% |
| Watchlist Candidate | 89 | 1.07% | 7.16% |
| Downgraded - Wait | 8 | 4.33% | 12.17% |

## Assessment

The fix is directionally correct because it prevents BTX-style daily damage from remaining actionable.

The random-20 backtest does not prove the thresholds are optimal:

- Sample size is small.
- Downgraded bucket has only 8 historical signals.
- Historical intraday and extended-hours behavior is not included.
- No regime segmentation, liquidity segmentation, or market-cap segmentation was applied.

What the sample does confirm:

- The engine still finds rank-1 signals after the stricter rule.
- Rank-1 signals outperformed rank-2 signals on average in this sample.
- The new daily downgrade gate is not globally suppressing all candidates.

Next required professional-grade step:

- Run a threshold matrix over larger samples.
- Compare fixed thresholds vs ATR-adjusted thresholds.
- Track forward return, max adverse excursion, win rate, drawdown, and false-positive reduction by `Action_Status`.
