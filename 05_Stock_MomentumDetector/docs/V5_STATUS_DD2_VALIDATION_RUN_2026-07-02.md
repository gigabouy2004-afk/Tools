# V5 D/D+1/D+2 Status Validation Run

Date: 2026-07-02

Validation contract:

- `docs/V5_STATUS_VALIDATION_CONTRACT_2026-07-02.md`

Validation script:

- `Validate_V5_Status_DD2.py`

Ticker source:

- `D:/Tools/StockCodeMaster/02_Stock/24-06-US_Common_Stocks_Master_Library-Sector-Technology.csv`

## Runs

### April 12 Single-Date Replay

Command:

```powershell
python .\Validate_V5_Status_DD2.py --ticker-csv D:\Tools\StockCodeMaster\02_Stock\24-06-US_Common_Stocks_Master_Library-Sector-Technology.csv --date 2026-04-12 --period 2y --limit 50 --output D:\TMP\V5_Status_DD2_Validation_Tech50_2026-04-12.csv --summary-output D:\TMP\V5_Status_DD2_Validation_Tech50_2026-04-12_Summary.csv
```

Note:

- 2026-04-12 was a Sunday.
- D resolved to the previous available trading session, 2026-04-10.

Repo artifacts:

- `backtests/V5_Status_DD2_Validation_Tech50_2026-04-12.csv`
- `backtests/V5_Status_DD2_Validation_Tech50_2026-04-12_Summary.csv`

Summary:

| Metric | Value |
|---|---:|
| Rows Validated | 47 |
| Rows Skipped | 3 |
| Actionable Momentum Candidate | 5 |
| Avoid | 42 |
| PASS | 5 |
| PASS_AVOID | 2 |
| FLAG_REVIEW | 40 |
| Status string check | 47 OK |
| Reason string check | 47 OK |

## April 2026 Range Replay

Command:

```powershell
python .\Validate_V5_Status_DD2.py --ticker-csv D:\Tools\StockCodeMaster\02_Stock\24-06-US_Common_Stocks_Master_Library-Sector-Technology.csv --start-date 2026-04-01 --end-date 2026-04-30 --period 2y --limit 50 --output D:\TMP\V5_Status_DD2_Validation_Tech50_2026-04-Range.csv --summary-output D:\TMP\V5_Status_DD2_Validation_Tech50_2026-04-Range_Summary.csv
```

Repo artifacts:

- `backtests/V5_Status_DD2_Validation_Tech50_2026-04-Range.csv`
- `backtests/V5_Status_DD2_Validation_Tech50_2026-04-Range_Summary.csv`

Status coverage:

| D Action Status | Rows |
|---|---:|
| Actionable Momentum Candidate | 127 |
| Watchlist Candidate | 17 |
| Downgraded - Wait | 3 |
| Avoid | 840 |

Validation result:

| Validation Result | Rows |
|---|---:|
| PASS | 110 |
| OBSERVE_CONTINUED | 14 |
| PASS_WATCHLIST_NO_CONFIRMATION | 3 |
| PASS_AVOID | 144 |
| FLAG_REVIEW | 716 |

String checks:

| Check | Result |
|---|---:|
| Status string check | 987 OK |
| Reason string check | 987 OK |

## Interpretation

Positive validation:

- `Actionable Momentum Candidate` had 110 passing rows out of 127.
- These rows satisfied the simple D+2 continuation test: D+1 open, D+2 open, or D+2 close above D close.

Review flags:

- 17 `Actionable Momentum Candidate` rows did not confirm by D+2.
- All 3 `Downgraded - Wait` rows continued by D+2, so the daily pullback wait rule may be too strict for those cases.
- 696 of 840 `Avoid` rows continued by D+2. This does not automatically mean every avoid rule is wrong, because `Avoid` means required engine conditions failed, not that price must immediately fall. However, it does mean the failed reasons require review if the intended output is a near-term exchange decision.

Important limitation:

- Historical April validation uses daily Yahoo bars.
- It cannot replay old intraday hourly statuses such as `Wait - Intraday Selling` or `Wait - Last Hour Bearish`.
- It cannot replay historical extended-hours statuses such as `Wait - Extended Hours Weakness` or `Rejected - Extended Hours Breakdown`.
- Those statuses require recent/live data capture or a historical intraday/extended-hours data source.

## Conclusion

The validation script found no unknown status strings and no unknown reason strings.

The engine is traceable and repeatable, but the April validation shows the decision logic is not fully calibrated for near-term D+2 price continuation. The largest issue is that many `Avoid` rows still continued by D+2, so the engine's hard-failure reasons may be too strict if the desired use is immediate exchange-price action rather than conservative structural filtering.

## Intraday Replay Correction

Correction date: 2026-07-02

The original validation replay used daily bars only. That was not sufficient for the stated validation problem because the D-day decision depends on 1H timing rules such as:

- `Wait - Intraday Selling`
- `Wait - Last Hour Bearish`
- `Failed - Distribution Risk`

`Validate_V5_Status_DD2.py` now fetches historical D/D+1/D+2 session intraday candles:

- 1H candles are passed into `evaluate_intraday_timing()` for status replay.
- 4H candle availability is recorded in the audit output.
- Rows record `D_1H_Bars`, `D_4H_Bars`, and `D_Intraday_Data_Status`, with matching D+1 and D+2 fields.

### April 12 Single-Date Replay With Historical Intraday

Command:

```powershell
python .\Validate_V5_Status_DD2.py --ticker-csv D:\Tools\StockCodeMaster\02_Stock\24-06-US_Common_Stocks_Master_Library-Sector-Technology.csv --date 2026-04-12 --period 2y --limit 50 --output D:\TMP\V5_Status_DD2_Validation_Tech50_2026-04-12_Intraday.csv --summary-output D:\TMP\V5_Status_DD2_Validation_Tech50_2026-04-12_Intraday_Summary.csv
```

Repo artifacts:

- `backtests/V5_Status_DD2_Validation_Tech50_2026-04-12_Intraday.csv`
- `backtests/V5_Status_DD2_Validation_Tech50_2026-04-12_Intraday_Summary.csv`

Summary:

| Metric | Value |
|---|---:|
| Rows Validated | 47 |
| Rows Skipped | 3 |
| Actionable Momentum Candidate | 4 |
| Downgraded - Wait | 1 |
| Rejected - Distribution Risk | 1 |
| Avoid | 41 |
| PASS | 4 |
| PASS_AVOID | 2 |
| FLAG_REVIEW | 41 |
| D intraday data status | 47 OK |

D entry timing coverage:

| D Entry Timing Status | Rows |
|---|---:|
| Clean | 28 |
| Wait - Daily Pullback Risk | 11 |
| Wait - Last Hour Bearish | 5 |
| Wait - Intraday Selling | 2 |
| Failed - Distribution Risk | 1 |

This replaces the daily-only interpretation for recent historical dates where the provider can return 1H/4H candles.
