# V5 Runtime Observation Log

Purpose: capture runtime observations from actual engine outputs, including the observed stock row details, suspected issue, validation performed, and whether a code change is authorized.

Rule: this log is for traceability only. No code change should be made from an observation unless explicitly authorized/requested.

## Observation Template

Use this structure for each new observation:

- Observation ID:
- Date/time captured:
- Source output file:
- Ticker:
- User observation:
- Full output row:
- Live validation performed:
- Engine calculation status:
- Suspected issue:
- Proposed future fix:
- Authorization status:
- Follow-up artifacts:

---

## OBS-20260629-001 - TENB Early Momentum Blocked By Weekly Transition Gate

Date captured: 2026-06-29

Source output file:

`V5_Momentum_Execution_Dump.csv`

Ticker:

`TENB`

User observation:

TENB moved more than 21% over the last week on price action, but the engine classified it as `Avoid`.

Full output row observed:

| Field | Value |
|---|---|
| Ticker | TENB |
| Live_Price | 32.715 |
| Action_Rank | 5 |
| Action_Status | Avoid |
| Long_Term_Status | Avoid |
| Entry_Timing_Status | Clean |
| Classification_Reason | weekly Transition |
| Market_State | REGULAR |
| Regular_Market_Price | 32.715 |
| PreMarket_Price |  |
| PostMarket_Price |  |
| Extended_Hours_Change_Pct |  |
| Close | 32.71500015 |
| Score | 66 |
| Trend_Score | 12 |
| Relative_Strength_Score | 12 |
| Breakout_Score | 20 |
| Accumulation_Score | 10 |
| Volatility_Score | 7 |
| Weekly_Stage_Score | 5 |
| Weekly_Stage | Transition |
| Weekly_Close | 30.21999931 |
| Weekly_SMA_30 | 22.59300016 |
| Weekly_SMA_30_Slope_Pct_10W | -4.763309785 |
| EMA_20 | 27.64540707 |
| EMA_50 | 25.31272314 |
| EMA_150 | 24.35992979 |
| EMA_200 | 25.16656145 |
| EMA_200_Slope_Pct_50D | -0.493356571 |
| Return_63D_Pct | 97.79321851 |
| Return_126D_Pct | 35.35374452 |
| Return_252D_Pct | -1.668170416 |
| Benchmark_Return_126D_Pct | 7.055537766 |
| RS_126D_Excess_Pct | 28.29820675 |
| RS_Ratio | 0.044263891 |
| RS_SMA_50 | 0.033294582 |
| RS_SMA_200 | 0.035278612 |
| RS_Slope_Pct_50D | 63.20651196 |
| Return_5D_Pct | 24.20273334 |
| Return_10D_Pct | 22.07089957 |
| High_20D | 32.95999908 |
| High_55D | 32.95999908 |
| High_100D | 32.95999908 |
| High_252D | 35.68999863 |
| Distance_From_20D_High_Pct | -0.743322023 |
| Distance_From_52W_High_Pct | 8.3356643 |
| Lower_High_Day | FALSE |
| Lower_Low_Day | FALSE |
| Close_Below_EMA20 | FALSE |
| ATR_14 | 1.622142928 |
| ATR_Pct | 4.958407215 |
| Volume | 2484563 |
| Volume_Avg_50 | 3435771.26 |
| Accumulation_Days_50 | 12 |
| Distribution_Days_50 | 7 |
| Net_Accumulation_50 | 5 |
| Latest_Distribution_Day | FALSE |
| Daily_Change_Pct | 8.256124738 |
| Last_3H_Return_Pct | 0.909938311 |
| Bearish_1H_Candles_Last3 | 0 |
| Last_1H_Bearish | FALSE |

Live validation performed:

The current engine was rerun for `TENB` using live yfinance data.

Validation result:

| Field | Live validation value |
|---|---|
| Live_Price | 32.9175 |
| Action_Rank | 5 |
| Action_Status | Avoid |
| Long_Term_Status | Avoid |
| Entry_Timing_Status | Clean |
| Classification_Reason | weekly Transition |
| Market_State | REGULAR |
| Score | 66 |
| Trend_Score | 12 |
| Weekly_Stage | Transition |
| Weekly_SMA_30_Slope_Pct_10W | -4.763309785 |
| Return_5D_Pct | 24.971523734 |
| Return_10D_Pct | 22.826494326 |
| Daily_Change_Pct | 8.92620877 |
| Last_3H_Return_Pct | 1.534550899 |
| Bearish_1H_Candles_Last3 | 0 |
| Last_1H_Bearish | False |

Engine calculation status:

Calculation appears correct under the current rule set.

Why current engine avoided it:

- `Weekly_Stage = Transition`
- `Weekly_Close > Weekly_SMA_30`
- but `Weekly_SMA_30_Slope_Pct_10W` is still negative, around `-4.76%`
- current Stage 2 gate requires positive weekly SMA slope

Suspected issue:

The engine may be burying strong early momentum names as plain `Avoid` when the weekly stage has not fully turned into confirmed Stage 2.

Proposed future fix:

Consider adding a separate output bucket such as:

- `Emerging Momentum Watch`
- `Early Momentum / Transition Breakout`

This bucket should not replace `Actionable Momentum Candidate`. It should make early transition breakouts visible while still distinguishing them from confirmed Stage 2 momentum setups.

Authorization status:

Not authorized for code change. Observation only.

Follow-up artifacts:

- `docs/V5_STAGE_GATE_REASSESSMENT_OBSERVATIONS.md`
