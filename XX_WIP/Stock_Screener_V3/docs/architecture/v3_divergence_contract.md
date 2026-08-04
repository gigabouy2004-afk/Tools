# V3 Divergence Contract

Date: 2026-06-02

Purpose: define the V3 Divergence stage-family contract and implementation guardrails.

Divergence is a separate stage family. It must not inherit Crossover hard gates or Momentum Setup continuation gates.

## 1. Stage Family Scope

`DIVERGENCE` identifies price and momentum disagreement.

Implementation status:

```text
V1 complete and tested for the current engine scope as of 2026-06-11.
```

Completion means the route contract, diagnostics, ranking participation, and generated calibration reporting are in place. Future changes should be limited to evidence-backed scoring, review-priority, or swing-geometry calibration and must not import Crossover or Momentum Setup hard gates.

It covers four candidate states:

| Candidate state | Primary meaning | Typical use |
|---|---|---|
| `BULLISH_DIVERGENCE` | Price makes a lower low or weak retest while momentum makes a higher low or improves. | Bearish exhaustion / reversal watch. |
| `BEARISH_DIVERGENCE` | Price makes a higher high or failed breakout while momentum makes a lower high or weakens. | Bullish exhaustion / exit or preservation watch. |
| `HIDDEN_BULLISH_DIVERGENCE` | Price makes a higher low while momentum makes a lower low. | Bull trend continuation / pullback absorption. |
| `HIDDEN_BEARISH_DIVERGENCE` | Price makes a lower high while momentum makes a higher high. | Bear trend continuation / failed recovery. |

## 2. Family Boundary

Divergence answers a different question than Crossover or Momentum Setup.

| Family | Question |
|---|---|
| `CROSSOVER` | Is MACD transitioning between seller and buyer control? |
| `MOMENTUM_SETUP` | Is an existing bull phase offering pullback re-entry or continuation? |
| `DIVERGENCE` | Is price behavior disagreeing with momentum behavior? |

Divergence can coexist with other families, but it must be scored and ranked as its own candidate family.

## 3. Regular Divergence Contract

### `BULLISH_DIVERGENCE`

Route evidence:

- Price makes a lower low, equal-low retest, or weak marginal breakdown.
- Momentum makes a higher low, improves materially, or refuses to confirm the price weakness.
- Candidate is recent enough to matter.

Quality/context evidence:

- Price is near support, prior demand, EMA200, Bollinger lower-band area, or another meaningful risk-defined location.
- MACD histogram improves from negative or deeply weak territory.
- RSI forms a higher low or improves from a weak zone.
- Volume and candle acceptance do not show uncontrolled distribution.

Output contract:

- `CandidateState = BULLISH_DIVERGENCE`.
- `DivergenceDirection = BULLISH`.
- `DivergenceType = REGULAR`.
- `DivergenceOpportunityType = BULLISH_REGULAR_DIVERGENCE`.

### `BEARISH_DIVERGENCE`

Route evidence:

- Price makes a higher high, equal-high retest, or weak marginal breakout.
- Momentum makes a lower high, weakens materially, or refuses to confirm the price strength.
- Candidate is recent enough to matter.

Quality/context evidence:

- Price is near resistance, prior supply, Bollinger upper-band area, distance extension, or another meaningful risk-defined location.
- MACD histogram weakens from positive or extended territory.
- RSI forms a lower high or rolls down from a strong/overheated zone.
- Volume and candle acceptance show fading participation or rejection.

Output contract:

- `CandidateState = BEARISH_DIVERGENCE`.
- `DivergenceDirection = BEARISH`.
- `DivergenceType = REGULAR`.
- `DivergenceOpportunityType = BEARISH_REGULAR_DIVERGENCE`.

## 4. Hidden Divergence Contract

### `HIDDEN_BULLISH_DIVERGENCE`

Route evidence:

- Price makes a higher low during a constructive or recovering structure.
- Momentum makes a lower low or deeper pullback than price structure implies.
- Candidate is recent enough to matter.

Quality/context evidence:

- Market, sector, or stock context is not clearly hostile to bullish continuation.
- Price holds above or reclaims short/intermediate trend support.
- EMA20/EMA50 structure, higher-low behavior, or price ladder evidence supports trend continuation.
- Momentum recovers after the hidden-divergence low.

Output contract:

- `CandidateState = HIDDEN_BULLISH_DIVERGENCE`.
- `DivergenceDirection = BULLISH`.
- `DivergenceType = HIDDEN`.
- `DivergenceOpportunityType = HIDDEN_BULLISH_CONTINUATION`.

### `HIDDEN_BEARISH_DIVERGENCE`

Route evidence:

- Price makes a lower high during weak or deteriorating structure.
- Momentum makes a higher high or stronger bounce than price structure confirms.
- Candidate is recent enough to matter.

Quality/context evidence:

- Stock structure remains below short/intermediate resistance or fails reclaim attempts.
- Lower-high behavior, EMA20 rejection, or weak close-location supports failed recovery.
- Momentum rolls down after the hidden-divergence high.
- Bearish Crossover or bearish baseline context can improve confidence, but must not be mandatory.

Output contract:

- `CandidateState = HIDDEN_BEARISH_DIVERGENCE`.
- `DivergenceDirection = BEARISH`.
- `DivergenceType = HIDDEN`.
- `DivergenceOpportunityType = HIDDEN_BEARISH_CONTINUATION`.

## 5. Route Outcome Contract

Every selected Divergence evaluation must return one of:

| Outcome | Meaning |
|---|---|
| `SELECTED` | Divergence is recent, structurally relevant, and high enough quality for current review. |
| `WATCH` | Divergence evidence exists, but confirmation or context needs manual review. |
| `REJECTED` | Divergence geometry exists, but recency, quality, or context is currently weak. |
| `STATUS_QUO` | No divergence route exists for the selected family. |

Raw geometry should not disappear. If price/momentum disagreement exists but is not actionable, emit it as `WATCH` or `REJECTED` with reason codes.

## 6. Evidence Requirements

Current V3 evidence has a first-pass daily swing/MACD-histogram geometry detector. It is sufficient for V1 route evaluation, but it is not yet a calibrated production-grade divergence detector.

Future evidence improvements:

- Recent swing high/low points for price.
- Recent swing high/low points for MACD histogram.
- Recent swing high/low points for RSI or another momentum confirmation input.
- Bar age for each detected divergence.
- Divergence recency window.
- Divergence confirmation flag.
- Support/resistance or location context sufficient for risk tagging.

Do not infer full Divergence from only current-day MACD histogram direction.

## 7. Baseline Routing

Divergence routing must be less restrictive than Momentum Setup.

Baseline implications:

- Regular bullish divergence can be relevant in bearish, mixed, or weak stock regimes.
- Regular bearish divergence can be relevant in bullish, mixed, extended, or weakening stock regimes.
- Hidden bullish divergence is more continuation-oriented and should be risk-tagged or downgraded when market, sector, and stock are all bearish.
- Hidden bearish divergence can remain relevant in bearish or weakening stock regimes as continuation or failed-recovery evidence.

Hard guardrail:

- Do not block all Divergence only because market/sector/stock baseline is bearish.
- Do not use Momentum Setup bull-phase gates to suppress regular bullish divergence.
- Do not use Crossover transition gates to suppress hidden divergence.

## 8. Ranking Implication

Divergence can be selected explicitly through `StageFamilyEvaluator` and now participates in the default holistic dispatch because ranking diagnostics are explicit.

The ranking layer must be able to explain why one of these won:

- `PRE_BULL_CROSSOVER`
- `PRE_BEAR_CROSSOVER`
- `BULL_PULLBACK_REENTRY`
- `BULL_CONTINUATION_MOMENTUM`
- `BULLISH_DIVERGENCE`
- `BEARISH_DIVERGENCE`
- `HIDDEN_BULLISH_DIVERGENCE`
- `HIDDEN_BEARISH_DIVERGENCE`

The V1 ranking contract now makes this choice auditable, so Divergence can participate in the default holistic stage-family set while calibration remains a separate validation track.

## 9. Diagnostics Contract

Planned V3 output diagnostics:

- `DivergenceDirection`
- `DivergenceType`
- `DivergenceOpportunityType`
- `DivergenceConfirmationState`
- `DivergencePriceSwing`
- `DivergenceMomentumSwing`
- `DivergenceBarsAgo`
- `DivergenceQualityScore`
- `DivergenceQualityComponents`
- `DivergenceReason`
- `DivergenceReasonCodes`

These fields should be appended after existing V2-compatible columns and current V3 diagnostics.

## 10. Implementation Guardrails

- Keep swing/geometry calculation in evidence or a neutral helper, not inside unrelated stage evaluators.
- Keep Divergence scoring independent from Crossover and Momentum Setup scoring.
- Treat EMA200, RSI, ADX, volume, and candle acceptance as context/quality, not universal hard gates.
- Separate regular and hidden divergence in reason codes and diagnostics.
- Do not tune from a single ticker or single historical event.

## 11. Validation Closure

V1 validation artifacts:

- `validation/runs/v3_divergence_smoke_20260211_summary.md`
- `validation/runs/v3_divergence_stage_family_calibration_20260611.md`
- `validation/runs/v3_divergence_path_enabled_calibration_20260611.md`
- `validation/runs/v3_divergence_family_v1_completion_20260611.md`

Path-enabled calibration baseline:

- Detail files: 15.
- Candidate rows: 962.
- D+20 endpoint and path metrics are split by candidate state, sector, date, direction, type, and opportunity.
- Regular bullish divergence is the weakest current slice:
  - `BULLISH_DIVERGENCE`: 211 candidates, 44.08% endpoint hit rate, -1.45% median endpoint, -11.13% median worst low.

## 12. Path-Forward Calibration Rule

Implemented on 2026-06-11 after the Technology weak-watch review and the cross-sector path-enabled calibration both confirmed weakness in bullish Divergence below EMA200.

Rule:

- Raw or unconfirmed bullish Divergence below EMA200 remains auditable as `BULLISH_DIVERGENCE` or `HIDDEN_BULLISH_DIVERGENCE`.
- It is not promoted into the normal `WATCH` path.
- It is emitted as `REJECTED` with:
  - `BELOW_EMA200`
  - `RAW_BULLISH_DIVERGENCE_BELOW_EMA200`
- Confirmed bullish Divergence below EMA200 can still be `WATCH` with `NEEDS_MANUAL_REVIEW`.

Guardrail:

- This does not suppress Divergence geometry.
- This does not apply Crossover zero-line rules or Momentum Setup continuation rules to Divergence.
- Bearish Divergence and confirmed bullish Divergence behavior is unchanged.

Regression coverage:

- `test_divergence_rejects_raw_bullish_divergence_below_ema200`
- `test_divergence_keeps_confirmed_bullish_below_ema200_as_manual_watch`

## 13. Post-Rule Backtest Result

Backtested on 2026-06-11:

```text
validation/runs/v3_divergence_rule_backtest_review_20260611.md
validation/runs/v3_divergence_rule_stage_family_calibration_20260611.md
validation/runs/v3_divergence_rule_integrated_calibration_20260611.md
```

Scope:

- 15 fresh post-rule runs.
- Sectors: Technology, Industrial, Energy, Telecom, Utilities.
- Dates: 2026-02-11, 2026-03-11, 2026-04-11.
- Horizons: D+1, D+2, D+5, D+10, D+20.

Result:

- Selected/watch candidates changed from 3,144 before-rule baseline rows to 3,056 post-rule rows.
- The new rule directly rejected 33 rows with `RAW_BULLISH_DIVERGENCE_BELOW_EMA200`.
- Those 33 rows were mixed overall:
  - 54.55% D+20 hit rate;
  - 0.25% median D+20 endpoint;
  - -7.55% median D+20 worst low.
- Weakness was concentrated in:
  - Technology, 2026-03-11: 7 rows, 14.29% hit rate, -2.92% median endpoint.
  - Telecom, 2026-03-11: 3 rows, 0.00% hit rate, -0.23% median endpoint.

Calibration read:

- The rule is safe as a conservative audit/risk separation rule, but it is not a broad performance improvement across all sectors and dates.
- Do not add more Divergence tightening from this evidence alone.
- The next implementation focus should move to the analogous Momentum Setup weakness: `BULL_PULLBACK_REENTRY` below EMA200, especially weak February-March Industrial slices.
