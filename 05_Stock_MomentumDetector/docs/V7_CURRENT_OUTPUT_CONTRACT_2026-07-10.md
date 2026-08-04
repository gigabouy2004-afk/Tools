# V7 Current Output Contract

Date: 2026-07-10

## User-Facing Rule

In V7, `Score` is a final user-facing confidence score. It must not contradict `Final_Decision`.

`Score = 100` means momentum is active, confirmed, and fit to enter according to the engine rules. A row with `MOMENTUM_PRESENT_WAIT_CONFIRMATION` or `REJECT` must not publish `Score = 100`.

## Score Caps By Final Decision

| Final_Decision | Published Score Meaning | Maximum Published Score |
|---|---|---:|
| `MOMENTUM_ACTIVE` | Momentum is active now and fit to enter. | 100 |
| `MOMENTUM_PRESENT_WAIT_CONFIRMATION` | Momentum/setup may be present, but immediate confirmation is missing. | 84 |
| `REJECT` | Not valid for momentum action. | 49 |

## Score Range And Summary Filter

Published `Score` is always constrained to the inclusive range `0..100`.

`--score-y` is only the minimum score included in the final top-X summary. It does not define or alter any final-decision score cap.

For example:

```text
--score-y 0
```

means the final summary may select from all rows whose published score is zero or higher. It must never produce a score of `-1`.

The fixed caps remain:

```text
MOMENTUM_ACTIVE:                 100 maximum
MOMENTUM_PRESENT_WAIT_CONFIRMATION: 84 maximum
REJECT:                          49 maximum
```

## Execution Log And Final Summary

V7 produces two different CSV artifacts.

### Append-only execution log

Default path:

```text
D:/Tools/Stock_MomentumDetector/Processed_Data/V7_Momentum_Execution_Log.csv
```

Behavior:

- Opened in append mode.
- Contains one complete row for every processed ticker, including rows below `--score-y`, no-data rows, and error rows.
- Written, flushed, synchronized, and closed after every ticker.
- Can be opened read-only by another application while the scan is still running.
- Includes `Run_ID` and `Processed_At` before the complete V7 output fields.
- Preserves earlier runs; `Run_ID` separates rows from different executions.

The path can be changed with:

```text
--log-output <path>
```

### Final summary output

Default base path:

```text
D:/Tools/Stock_MomentumDetector/Processed_Data/V7_Momentum_Execution_Dump.csv
```

Behavior:

- Written after the complete scan finishes.
- Contains only the final sorted top `--count-x` rows selected from scores satisfying `Score >= --score-y`.
- Remains separate from the continuously updated execution log.
- Uses `--output <path>` to select a different final summary location.

The technical component fields remain available for audit:

- `Trend_Score`
- `Relative_Strength_Score`
- `Breakout_Score`
- `Freshness_Score`
- `Accumulation_Score`
- `Volatility_Score`
- `Weekly_Trend_Score`

Those component fields can explain why the setup looked strong internally, but the published `Score` must reflect the final actionability of the row.

## Live Phase Price Rule

V7 scoring is phase-price aware. If Yahoo provides a valid live price for one of these market states, the latest scoring bar is adjusted before indicators, final decision, and published score are calculated:

- `PRE`
- `REGULAR`
- `POST`
- `POSTPOST`

The adjusted price is written as `Close`, while the original regular-session close is retained as `Regular_Session_Close`.

Audit fields:

- `Market_State`
- `Live_Price`
- `Regular_Market_Price`
- `PreMarket_Price`
- `PostMarket_Price`
- `Regular_Session_Close`
- `Score_Price_Source`
- `Score_Price_Change_Pct`
- `Extended_Hours_Change_Pct`

This means a significant pre-market, regular-session, or post-market price shift can change trend, return, breakout, freshness, volatility, relative-strength, final decision, and published score.

## Confirmed Entry Hard Gates

V7 treats modest extension and mildly sub-1.0 relative volume as risk context, not automatic proof that momentum is inactive.

Current hard confirmation gates:

- `Score >= 85`
- `Weekly_Trend = Uptrend`
- `Entry_Timing_Status = Clean`
- `RS_126D_Excess_Pct >= 5.0`
- `ATR_Pct <= 10.0`
- `Return_5D_Pct <= 18.0`
- `Return_10D_Pct <= 30.0`
- `Relative_Volume_20 >= 0.75`
- `Close_Location_Pct >= 50.0`
