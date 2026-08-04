# V5 NASDAQ Random-50 Backtest

Date: 2026-06-29

## Source Universe

Source file:

`D:\Tools\StockCodeMaster\02_Stock\24-06-US_Common_Stocks_Master_Library.csv`

Filter:

- `Listing Exchange == NASDAQ`
- `ETF != Y`
- `Test Issue != Y`

Available NASDAQ rows after filtering: `3339`

Fixed random seed: `20260629`

Selected 50 tickers:

`GDRX`, `ECPG`, `VC`, `ADP`, `ROKU`, `PCT`, `WRAP`, `MOBI`, `BAER`, `ENLV`, `LOPE`, `DFLI`, `ISBA`, `LASR`, `MCHX`, `SCZM`, `ZUMZ`, `LWLG`, `PEPG`, `WIX`, `MYSZ`, `MTRX`, `GPRE`, `VRTX`, `MBWM`, `NEO`, `FIZZ`, `ORIQ`, `BSRR`, `ATOM`, `FRBA`, `ALMU`, `JCSE`, `HAVA`, `FLEX`, `PLSM`, `FSV`, `RDI`, `SHOO`, `QTTB`, `LTRN`, `LUCY`, `BEAG`, `XOMA`, `MGIH`, `CHRW`, `PLBC`, `CJMB`, `WAFU`, `BANL`

## Live Scan

Output file:

`backtests/V5_NASDAQ_Random50_Live_Scan_20260629.csv`

Live action counts:

| Action_Status | Count |
|---|---:|
| Avoid | 37 |
| Downgraded - Wait | 6 |
| Actionable Momentum Candidate | 4 |
| Watchlist Candidate | 1 |
| Rejected - Extended Hours Breakdown | 1 |
| Rejected - Distribution Risk | 1 |

Names not ignored:

| Ticker | Action_Status | Entry_Timing_Status | Score |
|---|---|---|---:|
| ECPG | Actionable Momentum Candidate | Clean | 100 |
| XOMA | Actionable Momentum Candidate | Clean | 100 |
| ROKU | Actionable Momentum Candidate | Clean | 92 |
| MBWM | Actionable Momentum Candidate | Clean | 89 |
| VRTX | Watchlist Candidate | Clean | 72 |
| BSRR | Downgraded - Wait | Wait - Last Hour Bearish | 100 |
| PLBC | Downgraded - Wait | Wait - Last Hour Bearish | 100 |
| MTRX | Downgraded - Wait | Wait - Last Hour Bearish | 82 |
| NEO | Downgraded - Wait | Wait - Last Hour Bearish | 82 |
| QTTB | Downgraded - Wait | Wait - Extended Hours Weakness | 89 |
| CHRW | Downgraded - Wait | Wait - Daily Pullback Risk | 83 |
| ATOM | Rejected - Distribution Risk | Failed - Distribution Risk | 60 |
| MYSZ | Rejected - Extended Hours Breakdown | Rejected - Extended Hours Breakdown | 0 |

## Daily Historical Backtest

Output files:

- `backtests/V5_NASDAQ_Random50_Daily_Backtest_Signals_20260629.csv`
- `backtests/V5_NASDAQ_Random50_Daily_Backtest_Summary_20260629.csv`

Method:

- Daily historical data only.
- Historical intraday and extended-hours data not included.
- Signal spacing: 21 trading days.
- Forward return measured from next open to 21D/63D future close.

Signals generated: `715`

Action bucket results:

| Action_Status | Signals | Avg Forward 21D | Avg Forward 63D |
|---|---:|---:|---:|
| Actionable Momentum Candidate | 374 | -0.46% | 0.32% |
| Watchlist Candidate | 315 | 0.71% | 2.08% |
| Downgraded - Wait | 26 | -0.83% | 1.10% |

## Assessment

This larger random sample is not supportive enough to claim the current scoring model is professionally calibrated.

Important findings:

- Rank-1 `Actionable Momentum Candidate` did not outperform `Watchlist Candidate` on average in this sample.
- The action timing gates are functioning, but the structural scoring/ranking still needs stronger validation.
- Some individual names had very strong historical results, but the aggregate bucket behavior is weak.
- The current scoring system may be too permissive across broad NASDAQ names, especially lower-quality or highly volatile names.

Current conclusion:

- The recent timing fixes are directionally correct.
- The strategy is not yet production-grade for broad-universe action decisions.
- A larger threshold and scoring calibration pass is required before relying on `Action_Rank = 1` as a professional-grade action signal.

Recommended next step:

- Build a threshold matrix across at least several hundred NASDAQ symbols.
- Compare score cutoffs, daily timing gates, volatility filters, liquidity filters, and RS thresholds.
- Add quality filters such as minimum market cap, minimum average dollar volume, and maximum ATR bucket.
- Measure forward return, win rate, max adverse excursion, and drawdown by `Action_Status`.
