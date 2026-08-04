The two-year V16 backtest is complete. The result is clear: V16 finds momentum historically, but the current BUY framework does not produce a positive five-session expectancy.
Overall result
Period: 29 July 2024–28 July 2026
Universe: 5,997 symbols — 3,637 U.S. and 2,360 India
Successfully processed: 5,549 symbols (92.53%)
Symbols producing BUY trades: 3,852
Trades: 24,902
Win rate: 47.31%
Average return: -0.1418%
Median return: -0.3231%
Profit factor: 0.952
At an illustrative 20-bps round-trip cost: -0.3418% average, profit factor 0.8883
Market	Trades	Win rate	Avg. return	Profit factor
U.S.	15,805	49.49%	-0.0367%	0.9877
India	9,097	43.52%	-0.3246%	0.8885

Entry-type diagnosis
Entry type	Trades	Avg. return	Profit factor
Momentum Extension	19,767	-0.1830%	0.9385
Early Momentum	5,030	+0.0094%	1.0033
EMA20 Recovery	79	+0.7868%	1.4252
Oversold Recovery	26	-0.9556%	0.7136

The main problem is Buy_Momentum_Extension: it represents 79.4% of all trades and is the largest source of negative expectancy. India also requires separate calibration; applying essentially the same entry framework produces materially worse results there.
The earlier zero-live-BUY situation is therefore not evidence that V16 cannot recognize momentum—the historical replay generated 24,902 signals. However, simply loosening the live conditions would increase exposure to a strategy that is presently unprofitable.
Validation passed:
AAPL vectorized replay matched all 7 production V16 signals.
RELIANCE.NS matched the production V16 signal.
Audit: no duplicate signals, ticker-level overlaps, date-order errors, or reconciliation failures.
All 72 regression tests passed.
Exclusions: 447 symbols lacked sufficient history; SVA returned no Yahoo data.
This used completed daily adjusted OHLCV with next-session-open entry and five-session-close exit. It does not simulate historical intraday partial candles, slippage, stops, or capital-constrained portfolio allocation.
Files:
[Summary JSON](D:/Tools/07_LiveScanner/output/V16_Backtest_2Y_20260729/V16_Backtest_2Y_Summary.json)
[All 24,902 trades](D:/Tools/07_LiveScanner/output/V16_Backtest_2Y_20260729/V16_Backtest_2Y_Trades.csv)
[Market/year/signal breakdown](D:/Tools/07_LiveScanner/output/V16_Backtest_2Y_20260729/V16_Backtest_2Y_Breakdown.csv)
[Symbol coverage and exclusions](D:/Tools/07_LiveScanner/output/V16_Backtest_2Y_20260729/V16_Backtest_2Y_Coverage.csv)
[Reproducible V16 backtest harness](D:/Tools/07_LiveScanner/v16_two_year_backtest.py)
My recommendation is to keep production V16 unchanged until Momentum Extension is redesigned and separately walk-forward-tested for U.S. and India.