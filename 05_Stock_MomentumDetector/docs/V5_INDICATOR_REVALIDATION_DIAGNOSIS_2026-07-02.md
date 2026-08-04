# V5 Indicator Revalidation Diagnosis

Date: 2026-07-02

## Scope

Review why V5 failed to safely and confidently identify immediate momentum on several D/D+1/D+2 validation rows.

This diagnosis uses the May 6 and May 19 random-20 multi-round validation artifacts:

- `backtests/V5_Random20_May06_May19_Consolidated_20260702_133607.csv`
- `backtests/V5_Random20_May06_May19_Round_Summary_20260702_133607.csv`
- `backtests/V5_Actionable_Momentum_Diagnostics_20260702.csv`

No production engine code was changed for this diagnosis.

## Current V5 Momentum Gate

The engine classifies a row as `Momentum Candidate` when:

- There are no hard-failure reasons.
- Raw score is at least 85.
- Entry timing is `Clean`.

Hard failures currently include:

- Close below/equal EMA200.
- Weekly trend not `Uptrend`.
- 126D relative strength not outperforming SPY.
- Distribution days 50D at least 8.
- ATR percent above 15.

The current actionable criteria are therefore broad structural conditions:

- Above EMA200.
- EMA stack is bullish.
- Weekly trend is up.
- 126D RS is positive.
- Distribution count is below hard cap.
- ATR is below hard cap.
- D-session timing is clean.

## Actionable Signal Result

Across the six random-20 rounds:

| D Date | Actionable Signals | Passed D+2 | Failed D+2 |
|---|---:|---:|---:|
| 2026-05-06 | 5 | 2 | 3 |
| 2026-05-19 | 4 | 4 | 0 |

Failed actionable rows:

- `PL`
- `CVV`
- `ETN`

Passed actionable rows:

- `CAMT`
- `RNG`
- `KLIC`
- `ALOT`
- `INTC`
- `COHR`

## Failed Actionable Indicator Review

| Ticker | Score | D Close | D+1 Open | D+1 Close | D+2 Close | 5D Return | 10D Return | ATR % | RS Excess | RelVol20 | D Close Location | Diagnosis |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `PL` | 91 | 39.69 | 39.52 | 35.24 | 39.04 | 16.46% | 0.56% | 7.63% | 193.52% | 0.73 | 98.35% | Strong close after a sharp 5D move, but low relative volume and immediate D+1 failure. Current engine treats this as clean momentum. |
| `CVV` | 93 | 8.05 | 7.95 | 6.98 | 7.09 | 23.09% | 38.32% | 11.47% | 98.49% | 1.41 | 76.92% | Very extended and high volatility. ATR below 15 avoids hard rejection, but this should not be treated as safe actionable momentum. |
| `ETN` | 95 | 421.39 | 419.00 | 399.15 | 401.51 | 2.59% | 1.82% | 3.51% | 1.62% | 1.23 | 82.74% | Structural trend is strong, but RS excess is barely positive. The current RS gate accepts any positive value. |

## Indicator Interpretation Problems

### 1. RS Gate Is Too Loose

Current hard gate:

- Reject only when `RS_126D_Excess_Pct <= 0`.

Problem:

- `ETN` passed with only `1.62%` RS excess.
- That is technically outperforming SPY, but not strong enough to support a high-confidence momentum signal.

Recommendation:

- For `Actionable Momentum Candidate`, require stronger RS confirmation, such as:
  - `RS_126D_Excess_Pct >= 5`, preferably `>= 10` for high-confidence action.
  - `RS_Slope_Pct_50D > 0`.
  - `RS_Ratio > RS_SMA_50 > RS_SMA_200`.

### 2. Volatility Gate Is Too Loose

Current hard gate:

- Reject only when `ATR_Pct > 15`.

Problem:

- `CVV` passed as actionable with `ATR_Pct = 11.47`.
- That is too volatile for a safe immediate-entry momentum signal.

Recommendation:

- Treat `ATR_Pct > 10` as at least `Watchlist` or `Downgraded - Wait`.
- For safe actionable momentum, prefer `ATR_Pct <= 8` unless liquidity and trend quality are exceptional.

### 3. Extension/Exhaustion Is Not Penalized Enough

Current logic:

- There is no hard block for very sharp 5D/10D runs.
- Breakout proximity is rewarded.

Problem:

- `PL`: 5D return `16.46%`.
- `CVV`: 5D return `23.09%`, 10D return `38.32%`.
- These look more like short-term extension/exhaustion risk than fresh safe entries.

Recommendation:

- Add an actionable cap or wait status when:
  - `Return_5D_Pct > 12`, or
  - `Return_10D_Pct > 20`, or
  - close is near the top of the day after a sharp multi-day run but without strong relative volume.

### 4. Volume Confirmation Is Missing

Current scoring:

- Accumulation/distribution count is used.
- Latest relative volume is not required for actionable momentum.

Problem:

- `PL` had `D_RelVolume20 = 0.73`, yet it was actionable.
- `CAMT`, also a pass, had low relative volume too, so volume alone is not enough. But low volume after a stretched move should reduce confidence.

Recommendation:

- Add a relative-volume confirmation layer:
  - Require `D_RelVolume20 >= 1.0` for fresh breakout action, or
  - downgrade if `D_RelVolume20 < 1.0` and `Return_5D_Pct > 10`.

### 5. D-Day Candle Quality Is Not Enough

Current timing:

- Last 3 hourly candles and final 1H bearish checks are used.
- If they do not trigger, status remains `Clean`.

Problem:

- `PL` had D close location near the high of day, but D+1 failed immediately.
- `CVV` and `ETN` also passed clean timing, but next day rejected.

Interpretation:

- D close strength alone does not guarantee next-session continuation.
- The current D-only timing layer is useful but incomplete.

Recommendation:

- Add next-session validation to the backtest contract.
- For live operation, do not treat D close as final actionable confirmation unless D+1 open confirms above D close or above a defined breakout level.

### 6. Market/Session Context Is Missing

Observation:

- May 6 actionable signals passed only 2 of 5.
- May 19 actionable signals passed 4 of 4.

Problem:

- The same scoring framework worked on one date and failed on another.
- That suggests market/session context is material.

Recommendation:

- Add benchmark and sector confirmation:
  - SPY/QQQ above EMA20/EMA50.
  - Benchmark D+1 gap/continuation filter for backtest analysis.
  - Sector ETF confirmation where possible.

## Required Additional Indicators

To safely identify immediate momentum, V5 needs more than trend, RS, breakout proximity, accumulation, ATR, and weekly trend.

Recommended additions:

1. `Relative_Volume_20D`
   - Latest volume divided by 20D average volume.

2. `Close_Location_Value`
   - `(Close - Low) / (High - Low)`.
   - Useful, but should be interpreted together with extension and volume.

3. `Extension_Risk`
   - Based on 5D/10D return, ATR distance, and distance from EMA20.

4. `Gap_Risk`
   - Prior gap-up/down behavior and whether D itself was a gap extension.

5. `Market_Context`
   - SPY/QQQ trend and same-day confirmation.

6. `Sector_Context`
   - Sector ETF trend and same-day confirmation.

7. `D+1 Confirmation Mode`
   - For practical use, the engine should distinguish:
     - `D Momentum Setup`
     - `D+1 Confirmed Entry`
   - The failed May 6 rows show that D setup alone is not safe enough.

## Thresholds That Need Fine Tuning

Current thresholds requiring revision:

| Area | Current V5 Behavior | Issue | Recommended Direction |
|---|---|---|---|
| Minimum RS | Any positive `RS_126D_Excess_Pct` passes hard gate | Too loose; `ETN` passed with only 1.62% | Require at least 5-10% for actionable |
| ATR hard cap | Reject only above 15% | Too loose for safe entry; `CVV` passed at 11.47% | Downgrade above 10%, prefer actionable below 8% |
| 5D extension | No actionable cap | `PL` and `CVV` were stretched | Downgrade if 5D > 12% without strong volume |
| 10D extension | No actionable cap | `CVV` had 38.32% 10D return | Downgrade if 10D > 20% |
| Relative volume | Not required for action | Low-volume moves can be overtrusted | Require or combine with extension filter |
| Market context | Not used | May 6 vs May 19 behavior differs materially | Add SPY/QQQ/sector context |

## Diagnosis

V5 is not broken because it calculates the indicators incorrectly. It is broken for the immediate-entry objective because the interpretation layer is too permissive.

The current engine identifies structural momentum setups. It does not reliably identify safe, confident, immediate D/D+1/D+2 momentum entries.

The largest failure is that `Actionable Momentum Candidate` is being assigned from D-only structural conditions. The label is stronger than the evidence supports.

## Recommendation

Do not tune one threshold in isolation.

Next implementation should split the output into two layers:

1. `Momentum Setup`
   - Structural trend, RS, weekly trend, breakout proximity.

2. `Confirmed Momentum Entry`
   - Requires setup plus:
     - stronger RS,
     - controlled extension,
     - acceptable ATR,
     - volume confirmation,
     - D+1 open/price confirmation or a live equivalent,
     - market/sector support.

Until that split exists, the current `Actionable Momentum Candidate` label should be treated as overconfident.
