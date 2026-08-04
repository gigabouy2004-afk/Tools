# Momentum Detector V5 Final Handover

Date: 2026-06-30

## Superseded Output Guidance

This document predates the July 2026 single-output decision contract. Any guidance below that says the end user should sort/read by `Action_Rank`, `Action_Status`, `Score`, or multiple technical columns is historical only.

Current rule as of 2026-07-04:

- The primary user-facing output is `Final_Decision`.
- Allowed values are `MOMENTUM_ACTIVE`, `MOMENTUM_PRESENT_WAIT_CONFIRMATION`, and `REJECT`.
- Internal score/status/rank columns may remain for audit, but the end user must not be asked to combine multiple columns or formulas.
- See `docs/V5_CURRENT_OUTPUT_CONTRACT_2026-07-04.md`.

Repository:

`https://github.com/gigabouy2004-afk/Stock_MomentumDetector`

Primary engine:

`Momentum_Detector_V5.py`

## Current Status

Momentum Detector V5 is usable as a self-contained execution engine for scanning ticker lists and producing CSV output.

Current user-facing output rule:

- Read `Final_Decision` as the final user-facing answer.
- Do not ask the user to combine `Action_Rank`, `Action_Status`, `Long_Term_Status`, `Entry_Timing_Status`, `Score`, `Trend_Score`, or `Classification_Reason`.
- Those fields are internal/audit details only.

## Action Status Meaning

| Action_Rank | Action_Status | Meaning |
|---:|---|---|
| 1 | Actionable Momentum Candidate | Structurally strong and timing-clean candidate |
| 2 | Watchlist Candidate | Structurally interesting but below top action threshold |
| 3 | Downgraded - Wait | Interesting/strong but current timing risk requires waiting |
| 4 | Rejected - Distribution Risk | Do not act due to selling/distribution risk |
| 4 | Rejected - Extended Hours Breakdown | Do not act due to severe extended-hours breakdown |
| 5 | Avoid | Skip for current action |

## Execution Inputs

Default ticker input:

`D:/Tools/StockCodeMaster/02_Stock/24-06-US_Common_Stocks_Master_Library-Sector-Technology.csv`

CLI ticker list:

```powershell
python Momentum_Detector_V5.py --tickers AAPL,MSFT,NVDA
```

CLI ticker CSV:

```powershell
python Momentum_Detector_V5.py --ticker-csv D:\path\to\tickers.csv
```

CLI output file:

```powershell
python Momentum_Detector_V5.py --ticker-csv D:\path\to\tickers.csv --output D:\path\to\output.csv
```

Current output behavior:

- If `--output` is supplied, the engine writes to that path.
- If no `--output` is supplied, the engine writes to `EXECUTION_LOG_CSV`.
- If the selected output path is not writable, the engine writes a timestamped fallback path.

Known open item:

- Default output is not yet always timestamped. The code currently timestamps only as fallback when the requested/default path is not writable.

## Important Runtime Fixes Already Implemented

### Extended-Hours Fetch And Rejection

Issue found with `CREX`: regular close was still strong, but pre-market price had collapsed.

Implemented behavior:

- `fetch_hourly_data()` uses `prepost=True`.
- Live quote fetch captures `Market_State`, `Live_Price`, `Regular_Market_Price`, `PreMarket_Price`, and `PostMarket_Price`.
- Output includes `Extended_Hours_Change_Pct`.
- Extended-hours drop `<= -2%` becomes `Wait - Extended Hours Weakness`.
- Extended-hours drop `<= -5%` becomes `Rejected - Extended Hours Breakdown`.

CREX validation after fix:

- `Regular_Market_Price`: about `4.10`
- `PreMarket_Price`: about `3.22`
- `Extended_Hours_Change_Pct`: about `-21.5%`
- Final result: `Rejected - Extended Hours Breakdown`

### Last-Hour Bearish Translation

Issue found: last 1-hour bearish candle was originally captured only as a reason but did not affect action.

Implemented behavior:

- If the final hourly candle is bearish and no stronger status already applies, `Entry_Timing_Status` becomes `Wait - Last Hour Bearish`.
- This translates to `Action_Status = Downgraded - Wait`.

### Daily Pullback Refinement

Issue found with `BTX`: a daily distribution day plus EMA20 break was still close to actionable because the old `-8% from 20D high` threshold was too brittle.

Implemented behavior:

- Key timing thresholds were moved into named constants.
- Added early daily trend-break logic:
  - below EMA20,
  - daily distribution drop,
  - and lower-high/lower-low or high-volume pullback,
  - then `Wait - Daily Pullback Risk`.

BTX after fix:

- `Action_Status`: `Downgraded - Wait`
- `Entry_Timing_Status`: `Wait - Daily Pullback Risk`

## Current Key Constants

| Constant | Value |
|---|---:|
| `MIN_HISTORY_BARS` | 300 |
| `MIN_MOMENTUM_SCORE` | 70 |
| `EXTENDED_HOURS_WAIT_DROP_PCT` | -2.0 |
| `EXTENDED_HOURS_REJECT_DROP_PCT` | -5.0 |
| `DAILY_PULLBACK_DEEP_20D_HIGH_PCT` | -8.0 |
| `DAILY_PULLBACK_EARLY_20D_HIGH_PCT` | -5.0 |
| `DAILY_PULLBACK_5D_RETURN_PCT` | -3.0 |
| `DAILY_DISTRIBUTION_DROP_PCT` | -3.0 |
| `HIGH_VOLUME_PULLBACK_MAX_GAIN_PCT` | 0.5 |
| `INTRADAY_SELLING_3H_RETURN_PCT` | -1.0 |
| `BEARISH_HOURLY_CANDLES_CONFIRMATION` | 2 |

Handover note:

These constants are visible and auditable, but not fully optimized. They need a larger threshold/scoring calibration pass before being treated as professionally calibrated.

## Validation And Backtest Artifacts

### Random 20

Files:

- `backtests/V5_Random20_Live_Scan_20260629.csv`
- `backtests/V5_Random20_Daily_Backtest_Signals_20260629.csv`
- `backtests/V5_Random20_Daily_Backtest_Summary_20260629.csv`
- `docs/V5_THRESHOLD_REFINEMENT_BACKTEST_2026-06-29.md`

Result summary:

- 250 historical daily signals.
- Rank-1 signals were positive on average in this small sample.
- Sample too small for threshold optimization.

### NASDAQ Random 50

Files:

- `backtests/V5_NASDAQ_Random50_Live_Scan_20260629.csv`
- `backtests/V5_NASDAQ_Random50_Daily_Backtest_Signals_20260629.csv`
- `backtests/V5_NASDAQ_Random50_Daily_Backtest_Summary_20260629.csv`
- `docs/V5_NASDAQ_RANDOM50_BACKTEST_2026-06-29.md`

Result summary:

- 715 historical daily signals.
- Random-50 result was not strong enough to claim professional-grade scoring calibration.
- `Actionable Momentum Candidate` did not clearly outperform `Watchlist Candidate`.

### Market-Cap Universes

Files:

- `backtests/NASDAQ_Top1000_ByMarketCap_TickerInput_20260629.csv`
- `backtests/NASDAQ_Technology_Top200_ByMarketCap_TickerInput_20260629.csv`
- `backtests/V5_NASDAQ_Top1000_ByMarketCap_Live_Scan_20260629.csv`
- `backtests/V5_NASDAQ_Technology_Top200_Live_Scan_20260629.csv`
- `backtests/V5_MarketCap_Top1000_And_Tech200_Daily_Backtest_Buckets_20260629.csv`
- `backtests/V5_MarketCap_Top1000_And_Tech200_Daily_Backtest_Signals_20260629.csv`
- `backtests/V5_MarketCap_Top1000_And_Tech200_Daily_Backtest_Summary_20260629.csv`
- `docs/V5_MARKETCAP_UNIVERSE_EXECUTION_2026-06-29.md`

NASDAQ Top 1000 live action counts:

| Action_Status | Count |
|---|---:|
| Avoid | 655 |
| Downgraded - Wait | 131 |
| Actionable Momentum Candidate | 122 |
| Rejected - Distribution Risk | 69 |
| Watchlist Candidate | 23 |

Technology Top 200 live action counts:

| Action_Status | Count |
|---|---:|
| Avoid | 168 |
| Actionable Momentum Candidate | 16 |
| Downgraded - Wait | 7 |
| Rejected - Distribution Risk | 6 |
| Watchlist Candidate | 3 |

Market-cap daily calibration:

| Universe | Action_Status | Signals | Avg 21D | Avg 63D |
|---|---|---:|---:|---:|
| NASDAQ Top 1000 | Actionable Momentum Candidate | 11431 | 1.56% | 5.07% |
| NASDAQ Top 1000 | Watchlist Candidate | 8137 | 1.41% | 5.30% |
| NASDAQ Top 1000 | Downgraded - Wait | 851 | 1.89% | 7.73% |
| Technology Top 200 | Actionable Momentum Candidate | 2576 | 2.10% | 7.08% |
| Technology Top 200 | Watchlist Candidate | 1610 | 2.06% | 9.21% |
| Technology Top 200 | Downgraded - Wait | 178 | 2.02% | 10.61% |

Assessment:

- Market-cap filtering improves test quality.
- Average returns are positive across non-avoid buckets.
- Ranking is still not fully calibrated because `Actionable` does not clearly dominate `Watchlist` or `Downgraded` on 63D returns.

## Runtime Observation Logs

Runtime observations are now tracked separately from code changes.

Files:

- `docs/V5_RUNTIME_OBSERVATION_LOG.md`
- `docs/V5_STAGE_GATE_REASSESSMENT_OBSERVATIONS.md`

Current logged observation:

- `TENB` showed a strong short-term price move but was classified as `Avoid` because weekly stage was `Transition`.
- Live validation confirmed the calculation was correct under current rules.
- Suspected product gap: strong early transition breakouts may need a separate bucket such as `Emerging Momentum Watch`.
- Code change is not authorized from this observation unless explicitly requested.

## Current Local Runtime Output

At handover time, local `V5_Momentum_Execution_Dump.csv` shows:

| Action_Status | Count |
|---|---:|
| Avoid | 815 |
| Downgraded - Wait | 34 |
| Actionable Momentum Candidate | 33 |
| Rejected - Distribution Risk | 21 |
| Watchlist Candidate | 18 |

Note:

- This local runtime CSV is modified relative to the last committed version at the time this document was created.
- It was not committed as part of this handover document unless separately synced.

## Known Gaps

1. Default output filename is not always unique.
   - Current behavior only timestamps if target file is not writable.
   - Desired behavior may be: default runs always produce timestamped output unless `--output` is explicitly supplied.

2. Output summary block is not yet implemented.
   - Requested future enhancement: execution timestamp, ticker source, output path, total processed, count by `Action_Rank`, count by `Action_Status`, then individual ticker rows.
   - Open design question: mixed-layout CSV vs separate summary file vs Excel workbook with summary/detail sheets.

3. Stage gate may hide early momentum.
   - TENB observation shows `weekly Transition` can bury strong short-term momentum under `Avoid`.
   - Requires explicit authorization before code change.

4. Thresholds are not fully optimized.
   - Constants are now visible, but not professionally calibrated.
   - Need threshold/scoring matrix across market-cap filtered universes.

5. Historical backtests are daily-only.
   - Historical intraday and extended-hours behavior are not fully validated.
   - Live timing gates were validated with examples, but not historically across large universes.

6. No liquidity filter in the production scan yet.
   - Market-cap filtering was used for calibration.
   - Recommended future addition: `AvgDollarVolume_50D`.

## Recommended Next Work, Only If Authorized

1. Add unique default output filenames.
2. Add run summary output.
3. Add optional `Emerging Momentum Watch` bucket and compare against current Stage 2 gate.
4. Build threshold/scoring matrix runner for NASDAQ Top 1000.
5. Add liquidity/dollar-volume filters.
6. Re-run calibration by sector, market-cap bucket, and volatility bucket.

## Sign-Off Position

The engine is suitable for continued controlled use as a ranked momentum-screening tool with explicit action/status columns.

It should not yet be considered a professionally calibrated trading signal engine.

Primary safe-use rule:

- Use `Final_Decision` as the final decision column.
- Treat `MOMENTUM_ACTIVE` as the only actionable output.
- Treat `MOMENTUM_PRESENT_WAIT_CONFIRMATION` and `REJECT` as no-action until conditions improve or confirmation appears.
