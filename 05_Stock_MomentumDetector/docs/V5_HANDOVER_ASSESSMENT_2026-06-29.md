# Stock Momentum Detector V5 Handover Assessment

Date: 2026-06-29

## Superseded Output Guidance

This assessment predates the July 2026 single-output decision contract. Any guidance below that says CSV/Excel consumers should sort/read by `Action_Rank`, `Action_Status`, `Score`, or multiple technical columns is historical only.

Current rule as of 2026-07-04:

- The primary user-facing output is `Final_Decision`.
- Allowed values are `MOMENTUM_ACTIVE`, `MOMENTUM_PRESENT_WAIT_CONFIRMATION`, and `REJECT`.
- Internal score/status/rank columns may remain for audit, but they are not the final user-facing message.
- See `docs/V5_CURRENT_OUTPUT_CONTRACT_2026-07-04.md`.

## Current Scope

This assessment covers the current `Momentum_Detector_V5.py` behavior and the latest `V5_Momentum_Execution_Dump.csv` result file.

No additional detector logic changes should be made until confirmed. The last implemented output-level changes were:

- Sort the final output file before writing.
- Fall back to a timestamped CSV filename if the default output file is not writable.
- Keep Office temporary lock files out of Git via `.gitignore`.

## User-Facing Column

Current interpretation supersedes this original assessment:

- Read `Final_Decision` as the final user-facing answer.
- Do not ask the end user to combine `Action_Rank`, `Action_Status`, `Long_Term_Status`, `Entry_Timing_Status`, `Score`, or `Trend_Score`.
- Those fields are internal/audit details only.

The CSV is now sorted as one full unit using this priority:

1. Lower `Action_Rank`
2. Stronger `Long_Term_Status`
3. Cleaner `Entry_Timing_Status`
4. Higher `Score`
5. Higher `Trend_Score`
6. `Ticker` as a stable tie-breaker

Action interpretation:

| Action_Rank | Action_Status | Meaning |
|---:|---|---|
| 1 | Actionable Momentum Candidate | Strong and clean enough for action consideration |
| 2 | Watchlist Candidate | Structurally interesting, but not top-tier action |
| 3 | Downgraded - Wait | Interesting, but current timing/risk requires waiting |
| 4 | Rejected - Distribution Risk | Do not act due to selling/distribution risk |
| 5 | Avoid | Ignore for current action |

Any non-clean timing risk is intentionally downgraded in `Action_Status`.

## Execution Options

The script is self-sufficient on every run. It does not require post-processing.

Default execution uses the configured `TICKER_INPUT_CSV` and `EXECUTION_LOG_CSV` values.

CLI ticker list:

```powershell
python Momentum_Detector_V5.py --tickers AAPL,MSFT,NVDA
```

CLI ticker CSV override:

```powershell
python Momentum_Detector_V5.py --ticker-csv D:\path\to\tickers.csv
```

CLI output file override:

```powershell
python Momentum_Detector_V5.py --tickers AAPL,MSFT --output D:\path\to\output.csv
```

If the target output file is not writable, the script writes a timestamped fallback file beside the requested path.

## Latest Output Summary

File reviewed: `V5_Momentum_Execution_Dump.csv`

Total rows: 921

| Long_Term_Status | Count |
|---|---:|
| Momentum Candidate | 42 |
| Watchlist Candidate | 42 |
| Avoid | 837 |

The latest sorted file starts with clean, high-score momentum names. The first group includes names such as:

`ALOT`, `ATEN`, `CREX`, `EXTR`, `FROG`, `FTNT`, `GEF-B`, `KORE`, `KTCC`, `MEI`, `MOG-A`, `MOG-B`, `NTCT`, `PANW`, `PAYS`, `RAMP`, `TBRG`, `ZD`.

## April Replay Method

The current backtest script is a broad historical signal audit. It does not directly run an exact historical scanner for a single date.

For this assessment, the current V5 engine functions were replayed against the 84 currently identified names from the latest output:

- `Momentum Candidate`
- `Watchlist Candidate`

Replay dates:

- 2026-04-06
- 2026-04-07
- 2026-04-08

Historical intraday hourly bars are not available through the current script for those dates, so the replay used daily-only timing. This means `Entry_Timing_Status` can detect daily pullback risk but not exact historical intraday selling/failure states.

## April Replay Results

### 2026-04-06

| Status | Count |
|---|---:|
| Momentum Candidate | 18 |
| Watchlist Candidate | 3 |
| Avoid | 63 |

Selected count: 21

Top selected names:

`ALCO`, `AVT`, `KORE`, `NTCT`, `OOMA`, `SLAB`, `SNX`, `ATNI`, `ARW`, `ESP`, `CSCO`, `GEF-B`, `ITRN`, `STX`, `BELFA`, `INGM`, `IHS`, `CREX`, `RFIL`, `MOG-A`.

### 2026-04-07

| Status | Count |
|---|---:|
| Momentum Candidate | 17 |
| Watchlist Candidate | 3 |
| Avoid | 64 |

Selected count: 20

Top selected names:

`ALCO`, `AVT`, `GEF-B`, `INGM`, `KORE`, `NTCT`, `OOMA`, `SLAB`, `SNX`, `STX`, `ARW`, `CSCO`, `ESP`, `ITRN`, `BELFA`, `IHS`, `CREX`, `RFIL`, `GFS`, `MOG-A`.

### 2026-04-08

| Status | Count |
|---|---:|
| Momentum Candidate | 19 |
| Watchlist Candidate | 2 |
| Avoid | 63 |

Selected count: 21

Top selected names:

`ALCO`, `AVT`, `GEF-B`, `INGM`, `ITRN`, `KORE`, `NTCT`, `OOMA`, `SLAB`, `SNX`, `ARW`, `ESP`, `GFS`, `STX`, `BELFA`, `CSCO`, `IHS`, `RFIL`, `CREX`, `ATNI`.

## April 7 vs April 8 Stability

Out of 84 currently identified names:

| Match Type | Count |
|---|---:|
| Same `Long_Term_Status` | 81 |
| Same `Entry_Timing_Status` | 80 |
| Same status and timing | 78 |

Changed names from 2026-04-07 to 2026-04-08:

| Ticker | 2026-04-07 | 2026-04-08 |
|---|---|---|
| ATNI | Avoid / Wait - Daily Pullback Risk / Score 62 | Watchlist Candidate / Clean / Score 81 |
| RFIL | Watchlist Candidate / Clean / Score 84 | Momentum Candidate / Clean / Score 87 |
| CVV | Avoid / Wait - Daily Pullback Risk / Score 55 | Avoid / Clean / Score 55 |
| NTAP | Avoid / Wait - Daily Pullback Risk / Score 2 | Avoid / Clean / Score 6 |
| GFS | Watchlist Candidate / Clean / Score 79 | Momentum Candidate / Clean / Score 96 |
| QXL | Avoid / Wait - Daily Pullback Risk / Score 1 | Avoid / Clean / Score 1 |

Assessment:

- April 7 and April 8 are largely consistent.
- The major positive upgrades were `RFIL` and `GFS`, both moving from Watchlist to Momentum Candidate.
- `ATNI` recovered from daily pullback risk into Watchlist Candidate.
- `CVV`, `NTAP`, and `QXL` improved only in timing status but remained Avoid.

## April 6 to April 7 Changes

Changed names from 2026-04-06 to 2026-04-07:

| Ticker | 2026-04-06 | 2026-04-07 |
|---|---|---|
| ATNI | Momentum Candidate / Clean / Score 99 | Avoid / Wait - Daily Pullback Risk / Score 62 |
| NTAP | Avoid / Clean / Score 10 | Avoid / Wait - Daily Pullback Risk / Score 2 |
| QXL | Avoid / Clean / Score 4 | Avoid / Wait - Daily Pullback Risk / Score 1 |

Assessment:

- April 7 introduced daily pullback risk for a small group.
- `ATNI` was the only material classification drop.
- The broader candidate list remained stable.

## Recommendation Before Next Code Change

Do not change scoring or classification logic yet.

The current evidence suggests the immediate issue was output usability, not necessarily signal calculation failure:

- Sorting was previously the main user-facing problem because strong names were buried in ticker order.
- April 7 to April 8 replay is mostly stable across the currently identified names.
- Any future change should be driven by a specific rule decision, for example whether daily pullback risk should demote a stock to Watchlist, Avoid, or only change `Entry_Timing_Status`.

Suggested next discussion point:

Should `Entry_Timing_Status` be purely an action-timing warning, or should it be allowed to materially change `Long_Term_Status`?

## Actionable Backlog

Do not implement while a scan is actively running.

Next output usability enhancement:

- Add a summary block at the top of the generated output before individual ticker assessment rows.
- Summary should include execution timestamp, ticker input source, total codes processed, count by `Action_Rank`, count by `Action_Status`, output file location, and any fallback output filename used because the default path was not writable.
- Individual ticker assessment rows should remain below the summary block.
- CSV/Excel consumer workflow should remain: sort/read by `Action_Rank` and act on `Action_Status`.

Open design detail:

- For plain CSV, a top summary block creates a mixed-layout file that is easier for humans but less clean for automated CSV parsing. Before implementation, decide whether to use one workbook with separate sheets for Excel output, or keep CSV machine-clean and generate a separate summary file.

## Implemented Timing Fixes

Implemented after CREX review:

- Hourly fetch now requests extended-hours data with `prepost=True`.
- The engine now fetches live quote metadata including `marketState`, regular-market price, pre-market price, and post-market price.
- Output rows include `Market_State`, `Live_Price`, `Regular_Market_Price`, `PreMarket_Price`, `PostMarket_Price`, and `Extended_Hours_Change_Pct`.
- Extended-hours weakness is translated into action timing:
  - `Extended_Hours_Change_Pct <= -2%` becomes `Wait - Extended Hours Weakness`.
  - `Extended_Hours_Change_Pct <= -5%` becomes `Rejected - Extended Hours Breakdown`.
- A single bearish final hourly candle now changes timing from `Clean` to `Wait - Last Hour Bearish` when no stronger risk condition already applies.

CREX validation:

- Regular-market price: `4.10`
- Pre-market price: `3.22`
- Market state: `PRE`
- Extended-hours change: about `-21.46%`
- Final action result after fix: `Rejected - Extended Hours Breakdown`

This confirms that a high structural score no longer overrides a severe current-market breakdown.
