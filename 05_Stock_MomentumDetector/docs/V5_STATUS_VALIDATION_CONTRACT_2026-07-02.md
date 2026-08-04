# V5 Status Validation Contract

Date: 2026-07-02

Purpose:

Define exactly which engine statuses must be validated before running another backtest/audit. This file is the traceability record for the validation scope.

## Primary Output Contract

This validation contract predates the final `Final_Decision` implementation. It remains useful for historical validation of old `Action_Status` behavior, but it is not the current end-user output contract.

Current rule as of 2026-07-04:

- The human-facing output is `Final_Decision`.
- Allowed values are `MOMENTUM_ACTIVE`, `MOMENTUM_PRESENT_WAIT_CONFIRMATION`, and `REJECT`.
- `Score`, `Action_Status`, and all other technical/status columns are internal/audit fields only.
- See `docs/V5_CURRENT_OUTPUT_CONTRACT_2026-07-04.md`.

Historical validation rows may still include `Action_Status` and `Score` because they were the fields under test at that time.

## Action Statuses To Validate

These are the final text statuses emitted by `resolve_action_status()`.

| Action_Status | Meaning To Validate | D+1 / D+2 Price Check |
|---|---|---|
| `Actionable Momentum Candidate` | Engine says the stock is commercially ready on D. | Positive validation requires continuation evidence: D+1 open, D+2 open, or D+2 close is above D close. |
| `Watchlist Candidate` | Engine says the stock is structurally promising but below top action threshold. | Positive validation records whether D+1/D+2 continuation happened, but this is not a failure if it does not because the engine did not mark it fully actionable. |
| `Downgraded - Wait` | Engine says structure may be interesting, but timing risk blocks action on D. | Correct validation expects D+1 or D+2 to show unresolved weakness or delayed confirmation. If price immediately confirms strongly, the wait rule may be too strict and must be flagged. |
| `Rejected - Distribution Risk` | Engine says selling/distribution invalidates action on D. | Correct validation expects no clean immediate continuation. If D+1/D+2 strongly confirms upward, the rejection rule must be flagged for review. |
| `Rejected - Extended Hours Breakdown` | Engine says severe extended-hours breakdown invalidates action on D. | Can only be validated when historical/live extended-hours quote data exists. Yahoo daily replay cannot validate this status for April dates. |
| `Avoid` | Engine says the setup is not commercially qualified on D. | Validation must be reason-specific. `Avoid` is not a prediction of an immediate price drop; it means one or more required engine conditions failed. If price confirms upward despite the failed reason, that exact reason is flagged for review. |

## Entry Timing Statuses To Validate

These are the timing statuses emitted by `evaluate_intraday_timing()`.

| Entry_Timing_Status | Validation Scope |
|---|---|
| `Clean` | Fully replayable from daily data plus current available quote fields. |
| `Wait - Daily Pullback Risk` | Replayable from daily data. Validate whether D+1/D+2 remained weak or delayed confirmation. |
| `Failed - Distribution Risk` | Partly replayable. Daily distribution is replayable; historical hourly candle confirmation is not available for old April dates through the current Yahoo path. |
| `Wait - Last Hour Bearish` | Not replayable for April with current Yahoo data because old hourly bars are not available. Validate only in recent/live windows. |
| `Wait - Intraday Selling` | Not replayable for April with current Yahoo data because old hourly bars are not available. Validate only in recent/live windows. |
| `Wait - Extended Hours Weakness` | Not replayable for April unless historical extended-hours quote data is available. |
| `Rejected - Extended Hours Breakdown` | Not replayable for April unless historical extended-hours quote data is available. |
| `Insufficient history` | Replayable. Expected behavior is no commercial score/action because required bars are missing. |

## Classification Reasons To Validate

These are the reason strings currently emitted by the engine.

| Reason | Programmed Condition |
|---|---|
| `below EMA200` | D close is less than or equal to EMA200. |
| `weekly downtrend` | Weekly close is below 30-week SMA and the 30-week SMA is falling. |
| `weekly flat` | 30-week SMA slope is nearly flat. |
| `weekly mixed` | Weekly trend is neither clean uptrend, downtrend, nor flat. |
| `weekly unknown` | Weekly trend fields are unavailable. |
| `not outperforming SPY` | 126-day return does not exceed benchmark 126-day return. |
| `distribution cluster` | 50-day distribution-day count is at least 8. |
| `excess volatility` | ATR percent is greater than 15. |
| `below EMA20 with deep 20D-high pullback` | Daily pullback rule from EMA20, 20-day high distance, and 5-day return. |
| `below EMA20 with early 20D-high pullback` | Early daily pullback rule from EMA20, 20-day high distance, and 5-day return. |
| `lower high and lower low` | Latest daily high and low are both below previous daily high/low. |
| `pullback on above-average volume` | Latest volume exceeds 50-day average and daily change is weak. |
| `daily distribution` | Latest daily change is at or below the distribution threshold. |
| `daily distribution below EMA20` | Daily distribution occurs while below EMA20 and with additional trend-break evidence. |
| `last 3H selling` | Last 3 hourly candles show return at or below the intraday selling threshold. |
| `2+ bearish hourly candles` | At least two of the last three hourly candles are bearish. |
| `last 1H bearish` | Final hourly candle is bearish. |
| `extended-hours weakness` | Live extended-hours price is weak versus latest close. |
| `extended-hours breakdown` | Live extended-hours price has breached the hard rejection threshold. |

## D / D+1 / D+2 Audit Columns Required

Every validation output must include:

- `Ticker`
- `D_Date`
- `D_Action_Status`
- `D_Score`
- `D_Entry_Timing_Status`
- `D_Classification_Reason`
- `D_Close`
- `D1_Date`
- `D1_Open`
- `D1_Close`
- `D1_Action_Status`
- `D1_Score`
- `D2_Date`
- `D2_Open`
- `D2_Close`
- `D2_Action_Status`
- `D2_Score`
- `Continuation_By_D2`
- `Validation_Result`
- `Validation_Note`

## Continuation Definition

For this validation run, `Continuation_By_D2 = True` when at least one of these is true:

- D+1 open is above D close.
- D+2 open is above D close.
- D+2 close is above D close.

This is intentionally simple and auditable. It tests whether the engine's D status aligned with immediate exchange-price confirmation by D+2.

## Regression Guard

The validation script must fail or flag the row when:

- A high `Score` appears with a hard commercial failure reason that should cap the score.
- `Action_Status` contradicts `Score`.
- A status string appears that is not listed in this contract.
- A reason string appears that is not listed in this contract.
- D, D+1, or D+2 cannot be resolved from trading dates.
