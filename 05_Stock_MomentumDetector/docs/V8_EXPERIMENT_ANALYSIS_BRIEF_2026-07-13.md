# V8 Experiment Analysis Brief — Plain-Language Restart Document

Date: 2026-07-13

Purpose: provide a self-contained, non-cryptic explanation of the V8 experiment, its terminology, implementation, evidence, observations, unresolved issues, and decisions requiring user approval. This is the first document to read if the analysis is restarted offline or in a new session.

Status: the EMA200 plus MACD Foundation was implemented and technically validated. The experiment produced encouraging D+1/D+5/D+8 results, but it also exposed important questions in the post-Foundation scoring rules. V8 is not approved to replace V7 operationally.

## 1. Executive Summary in Plain Language

V8 now performs a simple first qualification before doing its more complicated analysis.

A stock qualifies for further analysis only when:

1. its closing price is above its 200-day exponential moving average, called EMA200; and
2. its configured MACD line is above the MACD signal line; and
3. the MACD line itself is above zero.

For this experiment, MACD used the faster `8/21/5` setting:

- 8-session exponential average for the fast line;
- 21-session exponential average for the slow line; and
- 5-session exponential average for the signal line.

If all three conditions pass, V8 calls the stock `FOUNDATION_VALID` and continues to the more detailed trend, relative-strength, breakout, volume, volatility, weekly-trend, and entry-confirmation checks.

If price is still above EMA200 but MACD does not satisfy both MACD conditions, V8 currently calls the state `FOUNDATION_TREND_VALID_MACD_RESET`. The stock is not treated as Active. It is published as `MOMENTUM_PRESENT_WAIT_CONFIRMATION` with Score 0.

The term “MACD reset” was too vague in the earlier summary. It does not mean that MACD was reset by the software. It also does not necessarily mean that a new MACD crossover happened on that date. It is simply the current name for this condition:

```text
Price is above EMA200
BUT
MACD line is not above both its signal line and zero
```

The experiment tested 20 technology stocks on four dates, creating 80 stock/date observations. Twenty-five observations passed the Foundation. Five ultimately became `MOMENTUM_ACTIVE` after the remaining V8 checks.

Those five Active observations were positive:

- 4 of 5 at D+1;
- 5 of 5 at D+5; and
- 4 of 5 at D+8.

This is encouraging, especially for the primary D+1 objective, but five Active observations are not enough for broad statistical or operational approval.

The experiment also found two matters requiring discussion:

1. Most MACD-reset cases were not structurally weak. They had MACD above zero but temporarily below the signal line, and many continued higher over D+5 and D+8.
2. The detailed scoring stage rejected 18 of the 25 Foundation-valid observations. Many of those rejected observations subsequently rose. One existing freshness-score formula also has a sign error and must be corrected.

## 2. What “Foundation” Means

The Foundation is the first technical qualification stage. Its purpose is to answer a narrow question before the engine performs more expensive or more subjective analysis:

```text
Is the stock in a valid long-term trend, and does it presently have positive MACD momentum?
```

The implemented rule is:

```text
Close > EMA200
AND MACD_Line(8,21,5) > MACD_Signal_Line(8,21,5)
AND MACD_Line(8,21,5) > 0
```

EMA200 provides the long-term-trend test. MACD provides the current momentum-direction test.

The Foundation does not award points. It determines whether the stock is eligible to be scored at all.

## 3. What MACD Means

MACD stands for Moving Average Convergence Divergence. It compares a faster exponential moving average with a slower exponential moving average.

For `8/21/5`:

```text
MACD Line = 8-session EMA minus 21-session EMA
Signal Line = 5-session EMA of the MACD Line
MACD Histogram = MACD Line minus Signal Line
```

Interpretation used by this engine:

- `MACD Line > 0`: the faster average is above the slower average, suggesting positive intermediate momentum.
- `MACD Line > Signal Line`: MACD is currently accelerating or recovering relative to its own recent average.
- Both true: bullish-positive MACD and a valid Foundation, provided price is also above EMA200.

## 4. What “MACD Reset” Actually Contained

There were 28 observations labelled MACD Reset. They were not all the same type.

| More precise description | Technical condition | Rows | D+1 positive | D+5 positive | D+8 positive |
|---|---|---:|---:|---:|---:|
| Positive MACD pullback | MACD above zero, but at or below signal | 22 | 12/22 | 19/22 | 16/22 |
| Early MACD recovery below zero | MACD at or below zero, but above signal | 3 | 3/3 | 3/3 | 3/3 |
| Negative and weakening MACD | MACD at or below zero and at or below signal | 3 | 0/3 | 2/3 | 2/3 |

Mean returns by subtype:

| Subtype | Mean D+1 | Mean D+5 | Mean D+8 |
|---|---:|---:|---:|
| Positive MACD pullback | -0.01% | +5.07% | +6.76% |
| Early recovery below zero | +1.71% | +8.05% | +8.85% |
| Negative and weakening | -2.10% | +0.99% | +0.38% |

This distinction matters. The current single reset label combines:

- a normal pullback inside a positive MACD regime;
- a potentially useful early recovery signal; and
- a genuinely weaker negative state.

Recommended terminology for the next version of the output contract:

```text
FOUNDATION_MACD_POSITIVE_PULLBACK
FOUNDATION_MACD_EARLY_RECOVERY_BELOW_ZERO
FOUNDATION_MACD_NEGATIVE_WEAKENING
```

These names are proposed for discussion; they have not been approved or implemented.

## 5. What “Downstream Scoring” Means

“Downstream” means every analysis stage that happens after a stock passes the Foundation. A clearer phrase is:

```text
post-Foundation Setup/Momentum scoring and decision gates
```

It is not a single calculation. It is a sequence:

1. calculate detailed daily and weekly indicators;
2. award component points;
3. cap the score for commercial-readiness risks;
4. assign a long-term classification;
5. apply final entry-confirmation gates;
6. return Active, Wait, or Reject;
7. only for Active, fetch external messages and ETF context.

### 5.1 Trend score — maximum 30 points

V8 checks the ordering of price and moving averages:

| Condition | Points |
|---|---:|
| Close > EMA50 > EMA150 > EMA200 | 20 |
| Otherwise, Close > EMA200 and EMA50 > EMA200 | 12 |
| EMA200 rose more than 2% over 50 sessions | 10 |
| Otherwise, EMA200 rose more than 0% | 5 |

### 5.2 Relative-strength score — maximum 25 points

Relative strength compares the stock’s 126-session return with SPY’s 126-session return.

| Condition | Points |
|---|---:|
| Stock exceeded SPY by more than 20 percentage points | 12 |
| Exceeded SPY by more than 5 points | 8 |
| Exceeded SPY by more than 0 points | 4 |
| Stock/SPY ratio above its 50- and 200-session averages, with positive 50-session slope | 13 |

### 5.3 Breakout score — maximum 20 points

| Condition | Points |
|---|---:|
| Close within 2% of the 55-session high | 6 |
| Close within 3% of the 100-session high | 6 |
| Close within 10% of the 52-week high | 8 |
| Otherwise, within 20% of the 52-week high | 4 |

### 5.4 Freshness score — intended to measure proximity to the 20-day high

The intended idea is to reward a stock that is near a recent high without being excessively extended.

However, the current implementation contains a sign mismatch:

```text
Distance_From_20D_High_Pct = (Close / High_20D - 1) * 100
```

This value is normally zero or negative. For example, 5% below the high is approximately `-5`.

The code then checks whether this value is `<= 2`, `<= 5`, and so on. Because nearly every legitimate value is already less than or equal to positive 2, all 25 fully analyzed observations received 12 freshness points. The intended extension penalties also compared the negative distance with positive 10 or 15, so those conditions could not operate as intended.

Likely correction:

| Correct negative-distance interpretation | Intended points |
|---|---:|
| At or above -2% | 12 |
| At or above -5% | 8 |
| At or above -10% | 5 |
| At or above -20% | 2 |

A provisional offline recalculation produced:

- 13 rows at 12 points;
- 6 rows at 8 points; and
- 6 rows at 5 points.

This provisional correction did not change any Final Decision in the 25 Foundation-valid observations, including the five Active rows. AMAT on June 9 would lose seven freshness points but would remain at the raw-score ceiling of 100. Nevertheless, this is a correctness defect and should be fixed and regression-tested before the downstream score is signed off.

The proposed formula is an inference from the field name and point thresholds. User approval of the intended freshness definition is required before code modification.

### 5.5 Accumulation/distribution score — maximum 15 points, with penalties

An accumulation day is a daily gain of at least 1% on volume above the 50-day average. A distribution day is a daily loss of at least 1% on volume above the 50-day average.

| Condition | Points |
|---|---:|
| Net accumulation over 50 sessions at least 3 | 10 |
| Otherwise, net accumulation positive | 6 |
| Five or fewer distribution days | 5 |
| Ten or more distribution days | -5 |
| Latest day is a distribution day | -8 |

Separate from these points, eight or more distribution days over 50 sessions is currently a hard classification reason that causes `Avoid` and therefore `REJECT`.

### 5.6 Volatility score — maximum 10 points

ATR means Average True Range. ATR as a percentage of price measures typical daily movement.

| ATR percentage | Points |
|---|---:|
| 4% or less | 10 |
| More than 4%, up to 7% | 7 |
| More than 7%, up to 10% | 3 |
| More than 15% | -5 |

### 5.7 Weekly-trend score — from -10 to +15 points

Weekly bars are compared with a 30-week simple moving average.

| Weekly condition | Classification | Points |
|---|---|---:|
| Weekly close above 30-week average and average slope positive | Uptrend | 15 |
| Mixed conditions | Mixed | 5 |
| Weekly close below average and average slope negative | Downtrend | -10 |

Flat or unknown conditions receive no weekly points.

### 5.8 Raw score

The component points are added and restricted to a range of 0 to 100. The theoretical component total can exceed 100, so several strong observations reach the 100-point ceiling.

## 6. Score Caps and Hard Classification Rules

After the raw points are calculated, V8 applies risk caps:

| Condition | Maximum final score |
|---|---:|
| Price at or below EMA200 | 20 |
| Weekly downtrend | 25 |
| Weekly state not Uptrend | 45 |
| 126-day return not exceeding SPY | 35 |
| Eight or more distribution days | 40 |
| ATR above 15% | 30 |
| Daily/intraday timing warning | 69 |
| Confirmed distribution failure | 25 |
| Extended-hours breakdown | 0 |

V8 also has hard classification reasons. If any of the following is true, the stock becomes `Avoid` and therefore `REJECT`, regardless of other positive evidence:

- price is at or below EMA200;
- weekly trend is not Uptrend;
- 126-session return did not beat SPY;
- eight or more distribution days occurred in 50 sessions; or
- ATR is above 15%.

Because Foundation enforcement already removes price-below-EMA200 observations, the most relevant remaining hard reasons are weekly trend, SPY underperformance, and distribution count.

### 6.1 Why the displayed Score may not equal the raw score

After the Final Decision is selected, the published Score is capped again so that decision labels and displayed scores cannot contradict each other:

| Final Decision | Highest published Score |
|---|---:|
| `MOMENTUM_ACTIVE` | 100 |
| `MOMENTUM_PRESENT_WAIT_CONFIRMATION` | 84 |
| `REJECT` | 49 |

Therefore, a displayed Score of 84 does not necessarily mean the component calculation totalled exactly 84. It can mean that a higher-scoring stock was changed to WAIT by an entry-confirmation blocker and its published Score was then capped at 84. Similarly, a rejected stock may have earned more raw component points before its published Score was capped at 49.

This is one reason a single Score column is insufficient for offline diagnosis and why separate raw-score, capped-score, and blocker fields are proposed.

## 7. Final Entry-Confirmation Gates

Even a high raw score is not automatically Active. To become `MOMENTUM_ACTIVE`, the stock must pass all of these:

| Confirmation | Required value |
|---|---|
| Final score | At least 85 |
| Weekly trend | Uptrend |
| Entry timing | Clean |
| 126-day excess return over SPY | At least 5 percentage points |
| ATR | No more than 10% |
| Recent extension | 5-day return no more than 18%; 10-day return no more than 30% |
| Relative volume | At least 0.75 times the 20-day average |
| Daily close location | At least halfway up the day’s high-low range |
| Liquidity | Above the configured average-dollar-volume threshold |

If a Momentum Candidate fails one or more confirmation gates, it becomes `MOMENTUM_PRESENT_WAIT_CONFIRMATION`.

In the historical experiment, true historical hourly bars, live quotes, and extended-hours quotes were unavailable. Therefore, the replay used daily timing evidence only. Live V8 can be stricter than this replay.

## 8. Meaning of the Three Final Decisions

### `MOMENTUM_ACTIVE`

The stock passed Foundation, detailed scoring, hard classification rules, and all entry-confirmation gates. It is the only state that triggers ETF context and external-message enrichment.

### `MOMENTUM_PRESENT_WAIT_CONFIRMATION`

Momentum or trend evidence exists, but at least one required confirmation is missing. In the new Foundation policy, this also includes price-above-EMA200 stocks whose MACD is not bullish-positive.

WAIT does not mean the stock is expected to fall. It means V8 is not authorizing an Active signal at that observation.

### `REJECT`

At least one hard structural, risk, or classification rule failed. REJECT is an engine eligibility decision, not a forecast that the stock must fall.

The experiment demonstrates why this distinction is important: several rejected stocks subsequently rose.

## 9. Exact Backtest Contract

The frozen run is:

```text
backtests/V8_Foundation_Validation/runs/V8FOUND_20260712T182945Z_cf0c908
```

Stocks:

```text
NVDA AAPL MSFT GOOGL META AMD AVGO ORCL CRM NOW
PANW CRWD ANET MU QCOM AMAT LRCX KLAC PLTR APP
```

Predeclared signal dates:

```text
2026-04-08
2026-04-30
2026-05-07
2026-06-09
```

All dates are in calendar quarter 2026Q2.

Outcome measurement:

- D is the signal day.
- D+1 return uses the next trading session’s opening price as entry and that same session’s closing price as exit.
- D+5 uses the D+1 opening price as entry and the fifth trading session’s close as exit.
- D+8 uses the D+1 opening price as entry and the eighth trading session’s close as exit.
- These are trading-session counts, not calendar-day counts.
- No stop loss, profit target, transaction cost, slippage, or position-sizing rule was applied.

The dates were fixed before execution. The technology seed was purposeful rather than a random whole-market sample.

## 10. Experiment Results

### 10.1 Foundation states

| Foundation state | Rows | D+1 positive / mean | D+5 positive / mean | D+8 positive / mean |
|---|---:|---:|---:|---:|
| Valid | 25 | 19/25, +2.21% | 23/25, +8.16% | 18/25, +10.24% |
| Combined MACD Reset | 28 | 15/28, -0.05% | 24/28, +4.95% | 21/28, +6.30% |
| Below EMA200 | 27 | 15/27, -0.99% | 16/27, +2.48% | 13/27, +2.27% |

Plain-language observation: Foundation Valid provided the clearest improvement at D+1. It also had the strongest average return at every horizon. The combined MACD-reset group was much weaker immediately but frequently recovered over the longer horizons.

### 10.2 Final decisions

| Final decision | Rows | D+1 positive / mean | D+5 positive / mean | D+8 positive / mean |
|---|---:|---:|---:|---:|
| Active | 5 | 4/5, +1.32% | 5/5, +7.35% | 4/5, +11.11% |
| Wait | 30 | 17/30, +0.34% | 26/30, +5.01% | 21/30, +5.72% |
| Reject | 45 | 28/45, +0.23% | 32/45, +4.95% | 27/45, +5.93% |

The Active sample passed the requested directional test, but the denominator of five is too small for a broad claim.

### 10.3 Active observations

| Stock/date | D+1 | D+5 | D+8 |
|---|---:|---:|---:|
| GOOGL 2026-04-30 | +1.06% | +4.29% | +1.50% |
| GOOGL 2026-05-07 | +0.96% | +1.03% | -2.35% |
| AMD 2026-04-30 | +2.46% | +16.08% | +27.40% |
| AMAT 2026-04-08 | +3.26% | +2.34% | +1.65% |
| AMAT 2026-06-09 | -1.15% | +13.02% | +27.33% |

### 10.4 Former Active observations blocked by MACD

The audit comparison calculated what V8 would have decided without enforcing the new Foundation stop. Five observations would previously have been Active but became MACD-reset WAIT:

| Stock/date | MACD line | Signal line | D+1 | D+5 | D+8 |
|---|---:|---:|---:|---:|---:|
| AMD 2026-06-09 | 26.31 | 35.62 | -3.33% | +8.40% | +17.88% |
| AVGO 2026-04-30 | 21.64 | 24.10 | +1.49% | -0.61% | +1.01% |
| PANW 2026-06-09 | 16.18 | 20.88 | +1.70% | +8.15% | +10.66% |
| ANET 2026-04-30 | 9.94 | 11.00 | -0.17% | -18.06% | -17.60% |
| AMAT 2026-04-30 | 7.27 | 10.08 | -0.10% | +5.44% | +10.72% |

All five had MACD above zero but below the signal line. As a group:

- D+1: 2/5 positive, mean -0.08%;
- D+5: 3/5 positive, mean +0.66%;
- D+8: 4/5 positive, mean +4.53%.

Interpretation: the MACD gate removed a weak immediate-entry group, which supports the D+1 objective. It also delayed several longer-duration winners, which argues for retaining a visible pullback/WAIT category and testing a re-entry rule.

## 11. Foundation-Valid Stocks Rejected by Later Rules

Of the 25 Foundation-valid observations:

- 5 became Active;
- 2 became Wait after detailed analysis; and
- 18 became Reject.

The 18 rejected observations were positive:

- 13/18 at D+1, mean +2.06%;
- 16/18 at D+5, mean +8.65%; and
- 14/18 at D+8, mean +11.41%.

This does not automatically prove that the rejections were wrong; the backtest did not measure drawdown, risk, or execution quality. It does show that the downstream rules are restrictive and need separate validation.

### 11.1 Distribution-cluster hard rejection

Ten Foundation-valid rejected rows had eight or more distribution days in the previous 50 sessions.

Their outcomes were:

- D+1: 8/10 positive, mean +2.68%;
- D+5: 10/10 positive, mean +8.87%;
- D+8: 8/10 positive, mean +11.79%.

This is the strongest warning in the downstream rules. A raw count of eight distribution days may be too blunt for volatile technology leaders, or it may need context such as net accumulation, recency, price recovery, and benchmark-relative strength. It should not be changed solely from ten rows, but it should be tested as a penalty or WAIT condition rather than an automatic Reject.

### 11.2 Weekly-downtrend hard rejection

Six Foundation-valid rejected rows were classified as weekly downtrends. Their outcomes were:

- D+1: 3/6 positive, mean +1.22%;
- D+5: 5/6 positive, mean +9.88%;
- D+8: 4/6 positive, mean +12.24%.

This rule is deliberately slow because it uses a 30-week average. It can protect against weak long-term structures, but it can also reject early recoveries such as PANW and CRWD.

### 11.3 SPY-underperformance hard rejection

Eight Foundation-valid rejected rows had not beaten SPY over the prior 126 sessions. Their outcomes were:

- D+1: 5/8 positive, mean +1.14%;
- D+5: 7/8 positive, mean +8.56%;
- D+8: 6/8 positive, mean +11.44%.

The 126-session comparison is a long lookback. It may reject a stock at the beginning of a new recovery because old underperformance remains in the measurement window.

The weekly, relative-strength, and distribution cohorts overlap, so their counts must not be added together.

### 11.4 Foundation-valid Wait observations

Two Foundation-valid rows became Wait after detailed scoring:

- AMD on May 7: the published Score was capped at 84 because 10-day extension exceeded 30% and the close finished below the midpoint of the daily range. It gained +8.74% at D+1 and +7.43% at D+5, then was -1.08% at D+8.
- AMAT on May 7: the published Score was capped at 84 because of a daily distribution/pullback warning. It gained +2.91% at D+1 and +4.12% at D+5, then was -3.83% at D+8.

These examples show why WAIT is useful: both moved up immediately, but neither sustained that gain through D+8.

## 12. ETF Experiment Explained

ETF mapping is not part of the momentum Score. It is additional context shown only after a stock becomes Active.

The ETF mapping process:

1. asks which US ETFs have the stock as a sufficiently large direct holding;
2. excludes leveraged/inverse funds and unverified mappings;
3. independently checks that the stock is in the ETF’s top ten holdings; and
4. for historical association, accepts only holdings evidence dated in the same calendar quarter as the stock signal.

Results:

- all 20 stocks were queried;
- 21 candidate top-ten mappings were returned and independently checked;
- 7 mappings had Q2-dated holdings evidence and were accepted;
- Q3-dated evidence was not back-cast into Q2;
- only GOOGL combined an Active observation with an accepted Q2 mapping;
- therefore only two Active stock/ETF comparisons were available;
- ETF processing changed no stock Score.

The ETF implementation contract passed. No predictive conclusion is required or authorized because ETF mapping is portfolio context, not momentum evidence. The two recorded stock/ETF outcome rows remain historical audit data only.

## 13. What the Experiment Proved

The evidence supports these statements:

1. V8 can calculate and enforce EMA200 plus configurable MACD `8/21/5` without look-ahead.
2. Non-qualified stocks stop before Setup/Momentum and ETF work.
3. All 80 Foundation and return rows were independently recomputed without failure.
4. Foundation Valid produced materially stronger immediate D+1 behavior than either non-valid state in this sample.
5. The five Active observations passed the requested D+1/D+5/D+8 directional test at 4/5, 5/5, and 4/5.
6. Strict same-quarter ETF evidence handling worked and did not mutate Score.
7. Existing append-only logs are protected when the output schema changes.

## 14. What the Experiment Did Not Prove

The experiment did not prove:

1. that `8/21/5` is optimal across different market regimes;
2. that every MACD-reset state should be blocked in the same way;
3. that five Active rows provide reliable statistical precision;
4. that the downstream hard-rejection rules are calibrated correctly;
5. that daily historical replay exactly reproduces live hourly and extended-hours behavior;
6. that the results generalize beyond the selected technology cohort;
7. any relationship between ETF membership and stock return; that question is outside the approved ETF function and was not tested as a signal hypothesis;
8. that V8 is ready to replace V7 operationally;
9. that transaction costs, stops, drawdowns, and position sizing would preserve the reported returns.

## 15. Messaging Rules for Future Reports

Future V8 reports should follow these rules:

1. Define every engine term when first used.
2. Do not say only “MACD reset.” State the exact condition: positive pullback, early recovery below zero, or negative weakening.
3. Replace “downstream scoring” with “post-Foundation Setup/Momentum scoring and decision gates,” followed by a brief list of the relevant gates.
4. State that WAIT and REJECT are eligibility decisions, not forecasts of a price decline.
5. State the entry and exit convention whenever D+1/D+5/D+8 results are quoted.
6. Separate implementation validation from predictive evidence.
7. State both the numerator and denominator; for example, `4/5`, not only `80%`.
8. Report known formula defects or historical-data limitations next to affected conclusions.
9. Do not claim historical ETF coverage where the holdings date is outside the signal quarter.
10. Distinguish observations, interpretations, recommendations, and approved decisions.

## 16. Decisions Requiring User Discussion or Approval

### Approval A1 — Foundation formula and default MACD

Question: retain `Close > EMA200` plus bullish-positive MACD as the mandatory first stage, with `8/21/5` as the default?

Current implementation: yes.

Recommendation: retain provisionally while expanding to multiple regimes and industrial stocks.

### Approval A2 — Replace the single MACD-reset label

Question: approve three explicit states instead of one ambiguous reset state?

Recommended states:

```text
MACD positive pullback
MACD early recovery below zero
MACD negative weakening
```

Recommendation: approve the terminology split before the next run.

### Approval A3 — Policy for early recovery below zero

Question: should MACD below zero but above its signal remain a WAIT, or be permitted into a separately labelled early-setup analysis?

Evidence: only three observations, all positive at D+1/D+5/D+8.

Recommendation: do not promote directly to Active. Create an early-recovery research state and gather more evidence.

### Approval A4 — Freshness-score correction

Question: confirm that distance below the 20-day high should be interpreted using negative thresholds (`>= -2`, `>= -5`, `>= -10`, `>= -20`) or redefine the stored field as a positive distance.

Recommendation: approve a positive-distance definition for human clarity, correct the formula, add boundary tests, and rerun all scoring regression. This correction is required before downstream-score signoff.

### Approval A5 — Distribution cluster

Question: should eight distribution days remain an automatic Reject, become a score penalty, or become WAIT unless additional weakness is present?

Evidence: 10 Foundation-valid rejected cases; 8/10 D+1, 10/10 D+5, and 8/10 D+8 positive.

Recommendation: test three frozen alternatives. Do not immediately remove the protection based on ten observations.

### Approval A6 — Weekly trend and 126-day SPY comparison

Question: should weekly downtrend or 126-day SPY underperformance automatically Reject a Foundation-valid early recovery?

Recommendation: retain as conservative rules for established Active signals, but test a separate early-setup state using shorter relative-strength windows such as 21/63 sessions. No threshold change should be made without a new frozen comparison.

### Approval A7 — Score transparency

Question: add explicit fields for raw component total, commercially capped score, score-cap reasons, hard rejection reasons, and final confirmation blockers?

Recommendation: approve. A single displayed Score hides how the decision was produced.

Proposed fields:

```text
Raw_Score
Commercially_Capped_Score
Score_Cap_Reasons
Hard_Classification_Reasons
Final_Confirmation_Blockers
```

### Approval A8 — Historical replay limitation

Question: accept daily-only replay for development evidence, while requiring prospective/live shadow evidence for operational signoff?

Recommendation: yes.

### Approval A9 — ETF historical rule

Question: retain the rule that independently dated ETF holdings must be in the same quarter as the signal?

Recommendation: yes. Do not back-cast Q3 holdings into Q2.

### Approval A10 — Next validation population

Question: after correcting score transparency/freshness, run multiple chronological regimes with both technology and industrial cohorts?

Recommendation: yes. Freeze dates and tickers before observing results, and reserve an untouched final holdout.

### Approval A11 — Operational status

Question: approve V8 to replace V7 now?

Recommendation: no. Keep V7 operational and V8 in development until A2-A7 are resolved and the multi-regime holdout passes.

## 17. Recommended Discussion Order

For the next analysis session, discuss in this order:

1. approve plain-language terminology and split the three MACD non-confirmation states;
2. approve the intended freshness formula and score-transparency fields;
3. review the ten distribution-cluster rejects;
4. review the weekly-downtrend and SPY-underperformance recovery cases;
5. decide whether early-recovery cases get a separate research status;
6. freeze the next technology/industrial, multi-regime test design;
7. defer operational signoff until the new holdout evidence is reviewed.

## 18. Evidence and Reproduction Files

Primary interpretation documents:

```text
docs/V8_REVISED_DEVELOPMENT_CHARTER_2026-07-13.md
docs/MOMENTUM_ENGINE_FOUNDATIONAL_DESIGN_STANDARD_2026-07-13.md
docs/V8_EXPERIMENT_ANALYSIS_BRIEF_2026-07-13.md
docs/V8_FOUNDATION_VALIDATION_CONCLUSION_2026-07-12.md
docs/V8_FINAL_HANDOVER_2026-07-12.md
docs/V8_CURRENT_OUTPUT_CONTRACT_2026-07-10.md
```

Frozen result files:

```text
backtests/V8_Foundation_Validation/runs/V8FOUND_20260712T182945Z_cf0c908/outputs/execution_console.log
backtests/V8_Foundation_Validation/runs/V8FOUND_20260712T182945Z_cf0c908/outputs/execution_log.csv
backtests/V8_Foundation_Validation/runs/V8FOUND_20260712T182945Z_cf0c908/outputs/regression_comparison.csv
backtests/V8_Foundation_Validation/runs/V8FOUND_20260712T182945Z_cf0c908/outputs/etf_mapping_validation.csv
backtests/V8_Foundation_Validation/runs/V8FOUND_20260712T182945Z_cf0c908/outputs/active_etf_outcomes.csv
backtests/V8_Foundation_Validation/runs/V8FOUND_20260712T182945Z_cf0c908/outputs/aggregate_summary.json
backtests/V8_Foundation_Validation/runs/V8FOUND_20260712T182945Z_cf0c908/validation/validation_summary.json
backtests/V8_Foundation_Validation/runs/V8FOUND_20260712T182945Z_cf0c908/checksums.sha256
```

Implementation:

```text
Momentum_Detector_V8.py
Backtest_Momentum_Detector_V8_Foundation.py
Validate_Momentum_Detector_V8_Foundation.py
config/V8_Foundation_Validation_Config.json
```

Validation command:

```powershell
python Validate_Momentum_Detector_V8_Foundation.py backtests/V8_Foundation_Validation/runs/V8FOUND_20260712T182945Z_cf0c908
```

Validated boundary at handover:

```text
Foundation implementation: complete
Focused experiment: technically valid
Downstream score: requires freshness correction and rule review
ETF implementation: technically valid context; predictive/scoring role prohibited
V8 operational approval: not granted
V7 operational status: unchanged
```
