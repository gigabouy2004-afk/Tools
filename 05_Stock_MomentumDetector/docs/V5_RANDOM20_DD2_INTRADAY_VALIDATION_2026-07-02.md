# V5 Random 20 D/D+1/D+2 Intraday Validation

Date: 2026-07-02

## Purpose

Validate whether the existing V5 engine's D-day score and action status align with D+1/D+2 price behavior for a random sample of 20 tickers.

This validation does not use 21D/63D/126D/252D forward returns. The validation target is the immediate D decision and the next two trading sessions.

## Sample

Ticker source:

- `D:/Tools/StockCodeMaster/02_Stock/24-06-US_Common_Stocks_Master_Library-Sector-Technology.csv`

Randomization:

- Sample size: 20
- Random seed: `20260702`

Sample file:

- `backtests/V5_Random20_TickerInput_20260702.csv`

Sample tickers:

- `AIFF`
- `ZOOZ`
- `FIG`
- `SNAL`
- `MPWR`
- `IBM`
- `ICHR`
- `ZS`
- `DOMO`
- `HPAI`
- `PL`
- `TLS`
- `CDNS`
- `IPGP`
- `FNGR`
- `ASST`
- `INOD`
- `AEYE`
- `VICR`
- `XTIA`

## Validation Run

Requested D date:

- `2026-04-12`

Resolved D date:

- `2026-04-10`

Reason:

- `2026-04-12` was a Sunday, so the validator resolved D to the prior trading session.

Command:

```powershell
python .\Validate_V5_Status_DD2.py --ticker-csv backtests\V5_Random20_TickerInput_20260702.csv --date 2026-04-12 --period 2y --output backtests\V5_Random20_DD2_Intraday_Validation_20260702.csv --summary-output backtests\V5_Random20_DD2_Intraday_Validation_Summary_20260702.csv
```

Outputs:

- `backtests/V5_Random20_DD2_Intraday_Validation_20260702.csv`
- `backtests/V5_Random20_DD2_Intraday_Validation_Summary_20260702.csv`

## Validation Method

For each ticker:

1. Replay the engine as of D using daily data only through D.
2. Fetch historical 1H and 4H candles for D, D+1, and D+2.
3. Pass D-session 1H candles into `evaluate_intraday_timing()`.
4. Calculate D score, D action status, entry timing status, and classification reason.
5. Compare the D action status against D+1/D+2 price behavior.

Continuation definition:

- `Continuation_By_D2 = True` if D+1 open, D+2 open, or D+2 close is above D close.

## Summary

| Metric | Value |
|---|---:|
| Random tickers selected | 20 |
| Rows validated | 19 |
| Rows skipped | 1 |
| Skipped ticker | `FIG` |
| D intraday data available | 19 / 19 |
| Actionable Momentum Candidate | 1 |
| Downgraded - Wait | 1 |
| Rejected - Distribution Risk | 6 |
| Avoid | 11 |
| PASS | 1 |
| PASS_AVOID | 1 |
| FLAG_REVIEW | 17 |

D entry timing coverage:

| D Entry Timing Status | Rows |
|---|---:|
| Clean | 4 |
| Wait - Daily Pullback Risk | 5 |
| Wait - Last Hour Bearish | 4 |
| Failed - Distribution Risk | 6 |

## Ticker-Level Result

| Ticker | D | D+1 | D+2 | D Status | Score | Timing | D Close | D+1 Open | D+2 Open | D+2 Close | Continued | Result |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ICHR | 2026-04-10 | 2026-04-13 | 2026-04-14 | Actionable Momentum Candidate | 100 | Clean | 57.50 | 58.75 | 62.85 | 64.01 | True | PASS |
| PL | 2026-04-10 | 2026-04-13 | 2026-04-14 | Downgraded - Wait | 69 | Wait - Last Hour Bearish | 34.67 | 34.23 | 35.59 | 33.93 | True | FLAG_REVIEW |
| IPGP | 2026-04-10 | 2026-04-13 | 2026-04-14 | Avoid | 40 | Wait - Last Hour Bearish | 127.32 | 126.97 | 129.15 | 124.65 | True | FLAG_REVIEW |
| MPWR | 2026-04-10 | 2026-04-13 | 2026-04-14 | Avoid | 40 | Clean | 1353.85 | 1336.41 | 1372.49 | 1363.42 | True | FLAG_REVIEW |
| VICR | 2026-04-10 | 2026-04-13 | 2026-04-14 | Avoid | 40 | Wait - Last Hour Bearish | 185.61 | 183.99 | 189.00 | 190.10 | True | FLAG_REVIEW |
| XTIA | 2026-04-10 | 2026-04-13 | 2026-04-14 | Rejected - Distribution Risk | 20 | Failed - Distribution Risk | 1.94 | 1.92 | 2.20 | 2.06 | True | FLAG_REVIEW |
| TLS | 2026-04-10 | 2026-04-13 | 2026-04-14 | Avoid | 3 | Wait - Daily Pullback Risk | 3.96 | 3.97 | 4.10 | 4.15 | True | FLAG_REVIEW |
| AEYE | 2026-04-10 | 2026-04-13 | 2026-04-14 | Avoid | 0 | Wait - Daily Pullback Risk | 6.09 | 5.97 | 6.41 | 6.56 | True | FLAG_REVIEW |
| AIFF | 2026-04-10 | 2026-04-13 | 2026-04-14 | Rejected - Distribution Risk | 0 | Failed - Distribution Risk | 1.50 | 1.57 | 1.59 | 1.56 | True | FLAG_REVIEW |
| ASST | 2026-04-10 | 2026-04-13 | 2026-04-14 | Avoid | 0 | Clean | 10.63 | 10.42 | 12.22 | 12.43 | True | FLAG_REVIEW |
| CDNS | 2026-04-10 | 2026-04-13 | 2026-04-14 | Rejected - Distribution Risk | 0 | Failed - Distribution Risk | 265.66 | 266.06 | 293.31 | 292.37 | True | FLAG_REVIEW |
| DOMO | 2026-04-10 | 2026-04-13 | 2026-04-14 | Rejected - Distribution Risk | 0 | Failed - Distribution Risk | 2.42 | 2.42 | 2.70 | 2.71 | True | FLAG_REVIEW |
| FNGR | 2026-04-10 | 2026-04-13 | 2026-04-14 | Avoid | 0 | Clean | 0.85 | 0.85 | 0.84 | 0.92 | True | FLAG_REVIEW |
| HPAI | 2026-04-10 | 2026-04-13 | 2026-04-14 | Avoid | 0 | Wait - Last Hour Bearish | 1.54 | 1.53 | 1.52 | 1.51 | False | PASS_AVOID |
| IBM | 2026-04-10 | 2026-04-13 | 2026-04-14 | Avoid | 0 | Wait - Daily Pullback Risk | 230.76 | 233.63 | 238.75 | 240.27 | True | FLAG_REVIEW |
| INOD | 2026-04-10 | 2026-04-13 | 2026-04-14 | Avoid | 0 | Wait - Daily Pullback Risk | 35.58 | 34.77 | 40.77 | 41.32 | True | FLAG_REVIEW |
| SNAL | 2026-04-10 | 2026-04-13 | 2026-04-14 | Rejected - Distribution Risk | 0 | Failed - Distribution Risk | 0.40 | 0.40 | 0.77 | 1.70 | True | FLAG_REVIEW |
| ZOOZ | 2026-04-10 | 2026-04-13 | 2026-04-14 | Avoid | 0 | Wait - Daily Pullback Risk | 5.92 | 5.90 | 6.26 | 6.30 | True | FLAG_REVIEW |
| ZS | 2026-04-10 | 2026-04-13 | 2026-04-14 | Rejected - Distribution Risk | 0 | Failed - Distribution Risk | 118.05 | 119.05 | 123.54 | 122.68 | True | FLAG_REVIEW |

## Review Finding

The engine correctly identified one actionable setup:

- `ICHR`: `Actionable Momentum Candidate`, score `100`, clean timing, and D+2 continuation confirmed.

The engine also correctly avoided one ticker under the D+2 continuation test:

- `HPAI`: `Avoid`, score `0`, no D+2 continuation.

However, 17 of 19 validated rows were not inline with the D+2 continuation test. Most failures were hard-failure statuses or low-score `Avoid` rows where price still moved above D close by D+2.

This does not prove every rejected or avoided ticker was a good trade. It means the current rule set is not calibrated for the specific stated objective: determine whether D-day momentum/action status aligns with D+1/D+2 price confirmation.

## Required Follow-Up

1. Stop using medium-term forward return columns as validation for this problem.
2. Keep historical 1H replay enabled in all D/D+2 validation runs.
3. Add reason-level D+2 statistics, especially for:
   - `below EMA200`
   - `weekly downtrend`
   - `not outperforming SPY`
   - `distribution cluster`
   - `Failed - Distribution Risk`
4. Reassess whether structural rejection rules should block immediate D+2 continuation signals, or whether the engine needs a separate short-window action status.
5. Do not change production action thresholds until this D/D+2 validation is repeated on larger random samples.
