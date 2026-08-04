# V5 Market-Cap Universe Execution

Date: 2026-06-29

## Source File

`D:\Tools\StockCodeMaster\02_Stock\24-06-US_Common_Stocks_Master_Library.csv`

Source columns used:

- `Ticker`
- `Listing Exchange`
- `ETF`
- `Test Issue`
- `MarketCap`
- `Sector`
- `Industry`

Base filter:

- `Listing Exchange = NASDAQ`
- `ETF != Y`
- `Test Issue != Y`
- `MarketCap > 0`

## Generated Universes

### NASDAQ Top 1000 By MarketCap

Ticker input:

`backtests/NASDAQ_Top1000_ByMarketCap_TickerInput_20260629.csv`

Rows: `1000`

Market cap range:

- Max: `4,864,926,000,000`
- Min: `1,195,760,212`

### NASDAQ Technology Top 200 By MarketCap

Ticker input:

`backtests/NASDAQ_Technology_Top200_ByMarketCap_TickerInput_20260629.csv`

Rows: `200`

Market cap range:

- Max: `4,864,926,000,000`
- Min: `1,886,970,996`

## Live Scan Outputs

### NASDAQ Top 1000

Output:

`backtests/V5_NASDAQ_Top1000_ByMarketCap_Live_Scan_20260629.csv`

Rows processed: `1000`

Action counts:

| Action_Status | Count |
|---|---:|
| Avoid | 655 |
| Downgraded - Wait | 131 |
| Actionable Momentum Candidate | 122 |
| Rejected - Distribution Risk | 69 |
| Watchlist Candidate | 23 |

Entry timing counts:

| Entry_Timing_Status | Count |
|---|---:|
| Clean | 380 |
| Wait - Last Hour Bearish | 250 |
| Wait - Intraday Selling | 174 |
| Failed - Distribution Risk | 69 |
| Wait - Daily Pullback Risk | 67 |
| Insufficient history | 60 |

### NASDAQ Technology Top 200

Output:

`backtests/V5_NASDAQ_Technology_Top200_Live_Scan_20260629.csv`

Rows processed: `200`

Action counts:

| Action_Status | Count |
|---|---:|
| Avoid | 168 |
| Actionable Momentum Candidate | 16 |
| Downgraded - Wait | 7 |
| Rejected - Distribution Risk | 6 |
| Watchlist Candidate | 3 |

Actionable Technology names:

`FTNT`, `NTCT`, `OKTA`, `PANW`, `FA`, `CDNS`, `AVT`, `ACLS`, `AMD`, `CRWD`, `MTCH`, `SLAB`, `NTAP`, `PLXS`, `SANM`, `PPLI`

## Daily Historical Calibration

Output files:

- `backtests/V5_MarketCap_Top1000_And_Tech200_Daily_Backtest_Signals_20260629.csv`
- `backtests/V5_MarketCap_Top1000_And_Tech200_Daily_Backtest_Summary_20260629.csv`
- `backtests/V5_MarketCap_Top1000_And_Tech200_Daily_Backtest_Buckets_20260629.csv`

Method:

- Daily data only.
- Historical intraday and extended-hours data not included.
- Signal spacing: 21 trading days.
- Forward return measured from next open to 21D/63D future close.

### Bucket Results

| Universe | Action_Status | Signals | Avg Forward 21D | Avg Forward 63D |
|---|---|---:|---:|---:|
| NASDAQ Top 1000 | Actionable Momentum Candidate | 11431 | 1.56% | 5.07% |
| NASDAQ Top 1000 | Watchlist Candidate | 8137 | 1.41% | 5.30% |
| NASDAQ Top 1000 | Downgraded - Wait | 851 | 1.89% | 7.73% |
| NASDAQ Technology Top 200 | Actionable Momentum Candidate | 2576 | 2.10% | 7.08% |
| NASDAQ Technology Top 200 | Watchlist Candidate | 1610 | 2.06% | 9.21% |
| NASDAQ Technology Top 200 | Downgraded - Wait | 178 | 2.02% | 10.61% |

## Assessment

The market-cap filtered universe is much cleaner than the random-50 sample, and the average returns are positive across all non-avoid buckets.

However, the current ranking is still not professionally calibrated:

- `Actionable Momentum Candidate` does not clearly dominate `Watchlist Candidate`.
- `Downgraded - Wait` has the strongest 63D average in both tested universes, which means timing-risk labels may be too conservative or the forward-return measurement is not aligned with the intended action horizon.
- A large number of names are being downgraded by last-hour or intraday selling; this is useful for live risk control, but historical daily-only backtest cannot fully validate it.

Current conclusion:

- Market-cap filtering improves the test quality.
- The engine is safer after timing fixes.
- The structural score and final action ranking still need calibration before being treated as a professional-grade trading signal.

Recommended next step:

- Add a threshold/scoring matrix runner for the NASDAQ top 1000 universe.
- Test score cutoffs such as `80/85/90`.
- Test daily timing gates against fixed percent and ATR-adjusted thresholds.
- Add liquidity filter using `AvgDollarVolume_50D`.
- Report by sector and market-cap bucket.
