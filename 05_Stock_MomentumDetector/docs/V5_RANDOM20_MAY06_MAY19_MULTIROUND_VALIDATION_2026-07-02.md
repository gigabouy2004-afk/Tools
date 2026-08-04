# V5 Random 20 Multi-Round D/D+1/D+2 Validation

Date: 2026-07-02

## Purpose

Test whether the existing V5 engine's D-day `Actionable Momentum Candidate` output is actually supported by D+1 and D+2 price behavior.

No production engine code was changed for this run.

## Test Design

Random rounds:

- May 6, 2026: 3 random-20 rounds.
- May 19, 2026: 3 random-20 rounds.

Validation rule:

- D+2 continuation is true when D+1 open, D+2 open, or D+2 close is above D close.
- `Actionable Momentum Candidate` must continue by D+2 to pass.
- `Avoid` passes only when it does not continue by D+2.

Captured per ticker:

- D status and score.
- D close.
- D+1 open and close.
- D+2 open and close.
- D entry timing status.
- Score components.
- Momentum selection rationale.
- Criteria flags used by the engine.

## Output Files

Consolidated result:

- `backtests/V5_Random20_May06_May19_Consolidated_20260702_133607.csv`

Round summary:

- `backtests/V5_Random20_May06_May19_Round_Summary_20260702_133607.csv`

Round-level outputs:

- `backtests/V5_May06_Round1_ExistingRandom20_DD2_Enriched_20260702_133607.csv`
- `backtests/V5_May06_Round2_Random20_DD2_Enriched_20260702_133607.csv`
- `backtests/V5_May06_Round3_Random20_DD2_Enriched_20260702_133607.csv`
- `backtests/V5_May19_Round1_Random20_DD2_Enriched_20260702_133607.csv`
- `backtests/V5_May19_Round2_Random20_DD2_Enriched_20260702_133607.csv`
- `backtests/V5_May19_Round3_Random20_DD2_Enriched_20260702_133607.csv`

Iteration log:

- `backtests/V5_Backtest_Iteration_Log.csv`

## Round Summary

| Round | D | D+1 | D+2 | Validated | Skipped | Actionable | Actionable PASS | Actionable FLAG_REVIEW | Total FLAG_REVIEW |
|---|---|---|---|---:|---:|---:|---:|---:|---:|
| May06 Round1 | 2026-05-06 | 2026-05-07 | 2026-05-08 | 19 | 1 | 1 | 0 | 1 | 13 |
| May06 Round2 | 2026-05-06 | 2026-05-07 | 2026-05-08 | 18 | 2 | 2 | 1 | 1 | 11 |
| May06 Round3 | 2026-05-06 | 2026-05-07 | 2026-05-08 | 18 | 2 | 2 | 1 | 1 | 14 |
| May19 Round1 | 2026-05-19 | 2026-05-20 | 2026-05-21 | 20 | 0 | 1 | 1 | 0 | 14 |
| May19 Round2 | 2026-05-19 | 2026-05-20 | 2026-05-21 | 20 | 0 | 2 | 2 | 0 | 12 |
| May19 Round3 | 2026-05-19 | 2026-05-20 | 2026-05-21 | 19 | 1 | 1 | 1 | 0 | 11 |

## Overall Result

Validated rows:

- Total: 114
- May 6 rows: 55
- May 19 rows: 59

Actionable Momentum Candidate rows:

- Total: 9
- Passed D+2 continuation: 6
- Failed D+2 continuation: 3

By date:

| D Date | Actionable Signals | Passed | Failed |
|---|---:|---:|---:|
| 2026-05-06 | 5 | 2 | 3 |
| 2026-05-19 | 4 | 4 | 0 |

## Actionable Signal Detail

| D Date | Round | Ticker | Score | D Close | D+1 Open | D+1 Close | D+2 Open | D+2 Close | Continued | Result |
|---|---|---|---:|---:|---:|---:|---:|---:|---|---|
| 2026-05-06 | May06 Round1 | PL | 91 | 39.69 | 39.52 | 35.24 | 36.40 | 39.04 | False | FLAG_REVIEW |
| 2026-05-06 | May06 Round2 | CAMT | 100 | 202.54 | 199.90 | 193.08 | 194.28 | 205.54 | True | PASS |
| 2026-05-06 | May06 Round2 | CVV | 93 | 8.05 | 7.95 | 6.98 | 6.98 | 7.09 | False | FLAG_REVIEW |
| 2026-05-06 | May06 Round3 | ETN | 95 | 421.39 | 419.00 | 399.15 | 400.56 | 401.51 | False | FLAG_REVIEW |
| 2026-05-06 | May06 Round3 | RNG | 88 | 45.72 | 46.88 | 45.39 | 44.64 | 45.63 | True | PASS |
| 2026-05-19 | May19 Round1 | KLIC | 87 | 97.62 | 99.37 | 101.23 | 100.76 | 101.09 | True | PASS |
| 2026-05-19 | May19 Round2 | ALOT | 100 | 14.02 | 14.08 | 14.08 | 14.00 | 14.18 | True | PASS |
| 2026-05-19 | May19 Round2 | INTC | 87 | 110.80 | 116.22 | 118.96 | 116.58 | 118.50 | True | PASS |
| 2026-05-19 | May19 Round3 | COHR | 88 | 353.63 | 362.97 | 358.50 | 361.00 | 378.00 | True | PASS |

## Momentum Selection Criteria Observed

For all nine actionable signals, the engine selected Momentum using the same broad rationale:

- Close above EMA200.
- Bullish EMA stack.
- Weekly uptrend.
- 126-day relative strength outperforming SPY.
- Distribution days below hard cap.
- ATR within hard cap.
- Entry timing clean.

This rationale was not enough to prevent false actionable signals on May 6.

Failed actionable rows:

- `PL`: D+1 open and D+1 close both below D close; D+2 close still below D close.
- `CVV`: D+1 open, D+1 close, D+2 open, and D+2 close all below D close.
- `ETN`: D+1 open, D+1 close, D+2 open, and D+2 close all below D close.

## Non-Momentum Result

The engine generated many `Avoid`, `Downgraded - Wait`, and `Rejected - Distribution Risk` rows that still continued by D+2.

This means the current structural failure rules are not aligned with the immediate D+2 continuation validation target. Those rows are not automatically good trades, but they show that the current status labels do not reliably separate near-term continuation from near-term non-continuation.

## Assessment

The engine is not consistently reliable as an immediate D/D+1/D+2 momentum-entry engine.

Evidence:

- May 6 actionable hit rate was weak: 2 passed, 3 failed.
- The failed May 6 actionable rows had clean timing and strong structural momentum scores, but price moved against the signal immediately.
- May 19 actionable hit rate was strong: 4 passed, 0 failed.
- The difference between dates suggests market/session context matters and is not adequately represented in the current score.

Current diagnosis:

- The engine can identify structurally strong names.
- The engine does not yet have a reliable immediate-entry confirmation layer.
- A high D score plus clean D intraday timing is insufficient by itself.

Before any threshold change, the next audit should isolate why May 6 failed:

1. Compare D close location against D intraday range for actionable rows.
2. Add next-session gap-risk diagnostics.
3. Compare last 30-minute or final-hour behavior against full-day close strength.
4. Add market/sector condition on D and D+1.
5. Review whether an actionable signal must require D+1 open confirmation before being considered valid for entry.
