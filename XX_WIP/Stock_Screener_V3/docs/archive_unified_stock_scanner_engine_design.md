# Unified Stock Scanner Engine Design

## 1. Purpose

This document consolidates the agreed engine direction for the web-based stock scanner.

The application is an ad-hoc, user-driven tactical Technical Analysis scanner. The user supplies the scan universe through a stock-code file, comma-separated manual symbols, or both. The user may also provide filter choices and selected Technical Analysis parameters. The engine evaluates each stock by first establishing the current technical baseline, then selecting the relevant stage path, then calculating only the indicator evidence required for that path. It assigns stage-specific confidence scores and returns ranked candidates with clear reasons.

Correct trading meaning is more important than preserving old engine boundaries or keeping code paths convenient. The engine must be path-first, not indicator-first.

The current target is not automated trading, position sizing, stop-loss generation, capital allocation, or order execution. The target is fast, explainable candidate discovery for practical market review.

## 2. Source-System Roles

The final scanner should not preserve three separate engines. The older systems are source references:

### Version 11

Business-logic reference.

Useful concepts:

- Technical Analysis scoring.
- Daily and hourly indicator calculations.
- Quality component scoring.
- Stage and gate validation.
- Promotion, degradation, hold, and status-quo reasoning where useful.
- Custom MACD early-detect logic as a reference, not as unquestioned truth.

### PMDE

Architecture reference.

Useful concepts:

- Compute layer calculates values only.
- Decision layer owns stage classification.
- Explanation and audit layer explains decisions from computed values.
- Structured output contracts.

### Current Stock Screener / Web App

Runtime and web-shell reference.

Useful components:

- Web page.
- CSV upload.
- Manual symbols.
- Filters.
- Async progress.
- CSV output.
- HTML/report output.
- Audit logging.
- Displayed result table.

The current monolithic decision engine should not be treated as the final source of truth. Its working pieces should be reused behind a cleaner staged design.

## 3. Application Workflow

```text
User opens web app
-> user provides CSV and/or manual symbols
-> user selects exchange / sector / industry / instrument filters where available
-> user selects stage families
-> user optionally adjusts TA parameters
-> engine loads only the minimum data required for baseline
-> L1 baseline layer classifies current technical state
-> L2 stage router chooses the relevant stage path from baseline and user selections
-> L3 indicator functions calculate only the evidence required by that path
-> stage-family layer evaluates Crossover, Divergence, and Momentum Trading
-> output layer marks remaining processed symbols as STATUS_QUO when All is selected
-> scoring layer assigns stage-specific confidence
-> filter/ranking layer prepares final candidates
-> UI displays compact results
-> audit layer writes full computed and decision detail
```

## 4. Inputs

### Universe Inputs

- Uploaded CSV containing stock codes.
- Manual comma-separated stock codes.
- Both CSV and manual codes in the same run.

The loader must normalize symbols, remove blanks/duplicates, and preserve enough source metadata for audit.

### Filter Inputs

Where available, the web app should support:

- Exchange.
- Sector.
- Industry.
- Instrument type.
- Price range.
- Market cap range.
- Average volume range.
- RSI range.
- ADX range.
- Bollinger percent-b range.

### Stage-Family Inputs

The required candidate stage families are:

- `Crossover`
- `Divergence`
- `Momentum Trading`

The old `Setup` name is replaced by `Momentum Trading`.

The UI may expose `All` as a convenience option. `All` means evaluate all candidate stage families and display remaining processed symbols as `STATUS_QUO`.

`Status Quo` is not a selectable stage family. It is an output classification for symbols that do not satisfy the selected candidate-stage criteria.

### TA Parameter Inputs

The user may override selected defaults per run. Defaults must live outside decision code.

Important configurable values include:

- MACD fast / slow / signal.
- Baseline MACD fast / slow / signal.
- RSI period and limits.
- ADX period and limits.
- Bollinger period and standard deviation.
- Crossover freshness limits.
- Clear crossover minimum histogram and spread.
- Zero-line buffer where applicable.
- Divergence lookback and recent window.
- Momentum Trading lookback.
- Momentum Trading MACD parameters.
- Momentum Trading phase maturity limits.
- Volume and relative-volume thresholds.
- Worker count and batch size.

## 5. Configuration Model

Configuration must support fast changes without code edits.

Initial model:

```text
global defaults
-> optional exchange override
-> optional exchange + sector override
-> optional exchange + sector + industry override
-> user UI override
```

The current `config.py` can remain the first implementation vehicle, but the target should support structured config profiles as the scanner matures.

Important rule: thresholds that are market, sector, industry, or stock-behavior sensitive must not be buried inside classification code.

UI messages, labels, headings, and other display strings should also live outside the decision code. The current `ui_text.json` file is the first i18n-style text catalog for this purpose.

## 6. Engine Layers

### 6.1 Input Layer

Responsibilities:

- Load CSV and manual symbols.
- Normalize ticker symbols.
- Apply exchange suffix handling where needed.
- Merge duplicate symbols.
- Preserve input source and run metadata.

### 6.2 Data Provider Layer

Responsibilities:

- Fetch daily data for L1 baseline.
- Fetch 4H and 1H data only when L2/stage logic requests lower-timeframe evidence.
- Avoid unnecessary profile calls during live-market review.
- Support batching where provider behavior allows.
- Return structured provider errors rather than failing the whole run.

Future direction:

- Introduce a `DataProvider` abstraction so Yahoo/YFinance remains one provider and other APIs can be plugged in without changing decision logic.

### 6.3 Path-First L1 / L2 / L3 Model

The current implementation target is not a full mapped schema engine. The design should remain simple enough to build and verify while keeping a clean path for later expansion.

Current levels:

- `L1 Baseline`: determine where the stock is now.
- `L2 Stage Router`: choose the practical stage path using hardcoded rules for the three candidate families.
- `L3 Indicator Functions`: calculate detailed indicator evidence only after L2 asks for it.

This avoids calculating every possible indicator and timeframe before knowing why they are needed.

### L1 Baseline

L1 answers the first and most important question:

```text
Is the current stock state Bull, Bear, Neutral/Mixed, or Insufficient?
```

The working baseline is configurable and should initially use a stable daily baseline definition, such as daily classical MACD settings, with supporting context where needed. The exact baseline parameters must remain in configuration, not embedded inside decision code.

Baseline is not the final stage. It only sets the route.

### L2 Stage Router

L2 is currently a small, explicit router. It is not a full strategy matrix yet.

Required routing logic:

```text
If baseline is Bear:
  check Pre-Bull Crossover possibility
  check Bearish Divergence
  check Momentum Trading only if selected and relevant
  otherwise output Status Quo

If baseline is Bull:
  check Bullish Divergence
  check Pre-Bear Crossover possibility
  check Momentum Trading only if selected and relevant
  otherwise output Status Quo

If baseline is Neutral/Mixed/Insufficient:
  output Status Quo unless selected stage rules provide enough evidence
```

The router must respect user-selected stage families. For example, if the user only selects Crossover, the engine should not perform full Divergence or Momentum Trading calculations unless they are required for baseline or audit.

### L3 Indicator Functions

L3 consists of independent calculation functions/modules. Examples:

- `MACD`
- `RSI`
- `ADX`
- `Bollinger`
- `Volume`
- `PriceBand`
- `StopLoss`
- `MomentumHistory`
- `GetAI`

The first implementation should support only the functions needed for the four current stage families. New functions can be added later as new columns in the future row/column model, but the engine should not require a full matrix schema now.

Important rule:

```text
L3 functions calculate values. L2 decides when those values are needed. Stage-family rules decide what those values mean.
```

### Future Matrix Direction

The future design may evolve into a two-axis model:

- Rows: stage or strategy paths, such as Bull Crossover, Bear Divergence, Momentum Trading, Intraday Trading.
- Columns: indicator/function modules, such as MACD, RSI, ADX, Bollinger, StopLoss, PriceBand, MomentumHistory, GetAI.

Each row would declare which columns it needs and how outputs should be interpreted. This is a future direction, not the current implementation requirement.

For now, L2 remains a hardcoded router for candidate families:

- `Crossover`
- `Divergence`
- `Momentum Trading`

When no selected candidate rule qualifies, the output layer marks the row as `STATUS_QUO`.

### 6.4 Compute Layer

Responsibilities:

- Calculate indicator values only when requested by L2 or stage-family logic.
- Avoid classifying candidate stages.
- Return structured values that decision rules can consume.

Core indicators:

- MACD line, signal line, histogram.
- MACD/signal crossover event.
- MACD zero-line context.
- Bars since MACD/signal crossover.
- Bars since MACD zero-line cross.
- RSI.
- ADX.
- Bollinger bands and percent-b.
- Volume and relative volume.
- Compression / expansion.
- Price structure and highs/lows where available.

Implementation warning:

```text
Do not globally compute daily, 4H, and 1H MACD for every symbol by default.
Compute baseline first, then calculate lower timeframe MACD only when the selected path requires it.
```

### 6.5 Baseline Layer

Responsibilities:

- Establish current stock state before stage classification.
- Distinguish bullish, bearish, recovering, weakening, extended, mixed, insufficient, or neutral state.
- Provide context for stage decisions, not automatically produce final candidates.

Baseline answers:

```text
What is this stock doing now?
Is the current state bullish, bearish, recovering, deteriorating, extended, or mixed?
Is the stock in a valid context for the selected stage family?
```

Baseline must not erase the difference between a transition event and an already-established regime.

### 6.6 Stage-Family Layer

Responsibilities:

- Evaluate selected stage families.
- Keep rules independent by family.
- Return raw checks, promoted candidate state, reason, and score inputs.

Required families:

- Crossover.
- Divergence.
- Momentum Trading.

`STATUS_QUO` is the fallback output when none of the selected families qualify.

### 6.7 Scoring Layer

Responsibilities:

- Assign stage-specific confidence.
- Keep score meanings separate across families.
- Return component scores for explanation and audit.

Important rule:

```text
A Crossover score of 80 is not equivalent to a Divergence score of 80 or a Momentum Trading score of 80.
```

### 6.8 Output Layer

Responsibilities:

- Show a compact result set by default.
- Write CSV and HTML/report output.
- Keep full details in audit rather than overloading the main table.

Default display fields:

- Symbol.
- Company name.
- Exchange.
- Sector.
- Industry.
- Latest price.
- Baseline state.
- Detected stage.
- Confidence score.
- Stage reason.
- Key TA values.
- Filter result.

Output format and presets are intentionally deferred. The current UI should stay close to the original operation: the user presses `Run Scan`, the engine executes, and results are displayed.

### 6.9 Audit And Operations Layer

Responsibilities:

- Log run lifecycle.
- Log input source and parameters.
- Log computed values.
- Log decision reasons.
- Log score components.
- Log pass/reject status.
- Log provider and calculation errors.
- Preserve enough detail to reproduce why each symbol passed or failed.

Operational logs should include:

- Run started / completed.
- Runtime duration.
- Input source.
- Symbols loaded.
- Symbols processed.
- Symbols matched.
- Symbols rejected.
- Parameters used.
- Provider/data errors.
- Classification errors.

## 7. Stage Family: Crossover

### Purpose

Crossover identifies actual MACD transition events or explicit near-transition states. It must not classify every already-bullish or already-bearish stock as a crossover.

### Current Web-App Basis

Crossover should remain aligned with the current web app's useful MACD/signal crossover behavior:

- Detect bullish MACD/signal crossover.
- Detect bearish MACD/signal crossover.
- Track crossover freshness.
- Track zero-line context separately.
- Use lower timeframe behavior as timing/confirmation, not as blind override.

### Core Crossover Rule

Bullish crossover event:

```text
previous_macd <= previous_signal
latest_macd > latest_signal
latest_histogram > clear_crossover_min_histogram
latest_macd - latest_signal >= clear_crossover_min_spread
```

Bearish crossover event:

```text
previous_macd >= previous_signal
latest_macd < latest_signal
latest_histogram < -clear_crossover_min_histogram
abs(latest_macd - latest_signal) >= clear_crossover_min_spread
```

### Crossover Freshness

Crossover must be fresh or explicitly classified as stale. Required fields:

- Bars since bullish MACD/signal crossover.
- Bars since bearish MACD/signal crossover.
- Bars since bullish zero-line cross.
- Bars since bearish zero-line cross.

### Zero-Line Context

Zero-line context must be recorded separately from crossover detection.

Examples:

- Bullish crossover below zero: early recovery / pre-bull context.
- Bullish crossover near zero: transition context.
- Bullish crossover above zero: stronger confirmation context.

### Histogram Clarification

The universal `0.5` histogram-style gate must not be used as a generic crossover requirement.

For Crossover:

```text
Histogram confirms the cross is real/non-flat.
Histogram is not a universal strength gate.
MACD zero-line buffer, when used, is context or stronger confirmation only.
```

The `0.5` style threshold belongs to position-quality or Momentum Trading confirmation, not raw crossover detection.

### Crossover Output

Possible crossover outputs:

- `BULLISH_CROSSOVER`
- `BEARISH_CROSSOVER`
- `PRE_BULL_CROSSOVER`
- `PRE_BEAR_CROSSOVER`
- `STALE_BULL_REGIME`
- `STALE_BEAR_REGIME`
- `NO_CROSSOVER`

The first implementation may retain the current web-app output names where needed, but the explanation must distinguish fresh crossover from established regime.

## 8. Stage Family: Divergence

### Purpose

Divergence identifies price/momentum disagreement. It must distinguish raw divergence evidence from confirmed, actionable divergence.

### Current Web-App Basis

Divergence remains aligned with the current web app behavior:

- Detect bullish divergence.
- Detect bearish divergence.
- Record raw divergence by timeframe.
- Require confirmation before promotion to final candidate.
- Score divergence separately from crossover and Momentum Trading.

### Raw Divergence

Bullish raw divergence:

```text
recent price low is lower than prior price low
recent MACD histogram low is higher than prior MACD histogram low
```

Bearish raw divergence:

```text
recent price high is higher than prior price high
recent MACD histogram high is lower than prior MACD histogram high
```

### Confirmation

Raw divergence is evidence, not a final candidate by itself.

Confirmed divergence must wait for MACD histogram momentum to stop making a new extreme.

- Bullish divergence is sell-momentum exhaustion. The latest histogram must still be below zero and must improve against the prior bar: `H0 > H1`.
- Bearish divergence is buy-momentum exhaustion. The latest histogram must still be above zero and must deteriorate against the prior bar: `H0 < H1`.
- Bars before this turn are developing evidence only; they must not be promoted to confirmed `BULLISH_DIVERGENCE` or `BEARISH_DIVERGENCE`.
- Until the remaining qualification criteria are finalized, confirmed divergence outputs are still provisional for V2 display/evaluation and must be marked with `*`; concrete scoring is deferred.

Confirmation may come from:

- Higher timeframe agreement.
- Constructive or deteriorating MACD bridge.
- Daily context support.
- Price structure confirmation.
- Momentum not being stale or overextended.

### Histogram Clarification

Divergence uses histogram shape and relative highs/lows. It must not apply a universal `0.5` histogram strength gate.

For Divergence:

```text
Histogram is compared against its own prior swing behavior.
Raw divergence is recorded even when it is not promoted.
Promotion requires confirmation.
```

### Divergence Output

Possible divergence outputs:

- `RAW_BULLISH_DIVERGENCE`
- `RAW_BEARISH_DIVERGENCE`
- `CONFIRMED_BULLISH_DIVERGENCE`
- `CONFIRMED_BEARISH_DIVERGENCE`
- `NO_DIVERGENCE`

The current web app may still expose `BULLISH_DIVERGENCE` and `BEARISH_DIVERGENCE`; audit fields must show whether the observation was raw or confirmed.

## 9. Stage Family: Momentum Trading

### Status

Placeholder for a separate detailed discussion and implementation plan.

Momentum Trading replaces the old generic `Setup` label. It is a long-trade candidate-quality family built around momentum-trading principles and stock-specific historical behavior.

The methodology in `MACD_Momentum_Identification_Baseline_Methodology_Consolidated_v3 (1).docx` applies only to Momentum Trading. It must not change Crossover or Divergence rules.

### Purpose

Momentum Trading is for identifying higher-quality long-trade candidates by comparing current momentum with the stock's own historical buyer/seller momentum behavior.

It is not an intraday noise detector and not a standalone trade execution system.

### Methodology Incorporated For Momentum Trading Only

The attached methodology defines a stock-specific MACD momentum baseline.

Approved scope:

- Data source: YFinance historical dataframe for the selected stock.
- Required input: Close price series.
- Default lookback: one year.
- Default interval: daily bars only.
- Default MACD: MACD(8,21,5).
- Volume: optional validation/confirmation gate only, not part of MACD baseline calculation.
- OHLC fields: not required for the MACD baseline described in the document.

### Momentum Baseline Process

```text
Load historical YFinance dataframe
-> calculate MACD(8,21,5) from Close
-> remove EMA warm-up rows
-> split histogram into bull and bear momentum phases
-> construct consecutive phase episodes
-> compute magnitude, frequency, duration, and maturity metrics
-> compare current phase against stock-specific history
-> produce Momentum Trading context and gates
```

### Bull/Bear Momentum Phase Definitions

```text
Bull momentum phase: histogram > 0
Bear momentum phase: histogram < 0
Neutral / transition: histogram near zero or changing polarity
```

Important distinction:

```text
Positive bars are not the same as bull phase episodes.
Negative bars are not the same as bear phase episodes.
```

Episodes are continuous runs of same-polarity histogram bars.

### Momentum Baseline Metrics

Required baseline metrics:

- `M_Average`
- `S_Average`
- `Current_MACD`
- `Current_Signal`
- `Current_Histogram`
- `Hist_Pos_Average`
- `Hist_Pos_Median`
- `Hist_Pos_75`
- `Hist_Pos_90`
- `Hist_Neg_Average`
- `Hist_Neg_Median`
- `Hist_Neg_25`
- `Hist_Neg_10`
- `Bull_Bar_Frequency`
- `Bear_Bar_Frequency`
- `Bull_Phase_Count`
- `Bear_Phase_Count`
- `Avg_Bull_Phase_Length`
- `Max_Bull_Phase_Length`
- `Avg_Bear_Phase_Length`
- `Max_Bear_Phase_Length`
- `Current_Phase`
- `Current_Phase_Length`
- `Current_Phase_Maturity`

### Momentum Strength Classification

Bull phase:

```text
Current histogram <= Hist_Pos_Average -> Normal / weak bull momentum
Current histogram > Hist_Pos_Average  -> Above-normal bull momentum
Current histogram >= Hist_Pos_75      -> Strong bull momentum
Current histogram >= Hist_Pos_90      -> Exceptional bull momentum
```

Bear phase:

```text
Current histogram >= Hist_Neg_Average -> Normal / weak bear momentum
Current histogram < Hist_Neg_Average  -> Above-normal bear momentum
Current histogram <= Hist_Neg_25      -> Strong bear momentum
Current histogram <= Hist_Neg_10      -> Exceptional bear momentum
```

### Phase Maturity Classification

```text
Current phase length / average phase length < 0.50 -> Early phase
0.50 to 1.00                                      -> Developing / normal phase
1.00 to 1.50                                      -> Mature phase
> 1.50                                            -> Extended phase
```

### Critical Gates For Momentum Trading

Momentum Trading must respect these gates before high-confidence promotion:

- Dataframe sufficiency.
- Correct Close-price input series.
- Warm-up removal.
- Bull/bear phase separation.
- Episode construction.
- Percentile thresholds.
- Current phase maturity.
- Price context.
- Liquidity and optional volume confirmation.
- Volatility regime control.
- Backtest / forward-test validation before production reliance.

### Momentum Trading Output Fields

Required output fields:

- `Momentum_Phase`
- `Momentum_Strength`
- `Phase_Maturity`
- `Phase_Maturity_Ratio`
- `Buyer_Behavior_Status`
- `Seller_Behavior_Status`
- `Critical_Gate_Status`
- `MomentumTrading_Confidence`
- `MomentumTrading_Reason`
- `MomentumTrading_Reject_Reason`

### Momentum Trading Placeholder

Open design items for the next discussion:

- Exact Momentum Trading pass/fail rules.
- Whether early/developing strong bull momentum is preferred over mature/extended momentum.
- How RSI headroom should interact with stock-specific momentum strength.
- How ADX should influence confidence.
- How volume/liquidity should validate setup quality.
- How price structure confirms setup readiness.
- How extension/chase risk should reduce score.
- How to rank strong but mature momentum versus moderate but early momentum.
- Whether Momentum Trading should be long-only initially.
- Whether bearish Momentum Trading should be deferred.

## 10. Output Classification: Status Quo

### Purpose

Status Quo is an output classification, not a user-facing stage family. It is used when the stock has a baseline state but does not currently satisfy the selected Crossover, Divergence, or Momentum Trading paths.

Status Quo should preserve useful context:

- Bull but no actionable Bullish Divergence or Pre-Bear Crossover.
- Bear but no actionable Pre-Bull Crossover or Bearish Divergence.
- Neutral/mixed state with no strong selected-stage evidence.
- Insufficient data for safe promotion.
- Stale crossover or stale divergence evidence.

### Status Quo Output

The current v2 UI emits `STATUS_QUO` as the fallback row state. It should still include a reason and key values, because a non-candidate result may be useful during market review.

Rules:

- Do not expose `Status Quo` as a checkbox or filter.
- Do not score `Status Quo` as a candidate family.
- Keep `WeightedScore` as `0.00`.
- Display `STATUS_QUO` rows only when the user selects `All`.

## 11. MACD Threshold Rules

This section prevents the prior histogram confusion from re-entering the engine.

### Crossover

For Crossover:

```text
Use histogram only to confirm the MACD/signal cross is real and non-flat.
Do not require histogram > 0.5.
Do not require MACD > 0.5 for PRE_BULL_CROSSOVER.
Record zero-line position separately.
```

### Divergence

For Divergence:

```text
Use histogram swing comparison.
Do not require histogram > 0.5.
Do not suppress raw divergence merely because the histogram is below a universal strength threshold.
Require confirmation before final promotion.
```

### Momentum Trading

For Momentum Trading:

```text
MACD zero-line buffer may be used as a setup-quality gate.
Histogram strength must be stock-specific, using the historical momentum baseline.
Avoid universal histogram > 0.5 as the primary strength definition.
```

If a `0.5` threshold remains in configuration, its usage must be explicitly scoped and named. It must not be reused ambiguously across Crossover, Divergence, and Momentum Trading.

## 12. Performance Requirements

Speed matters because the scanner may run during live-market review.

Required design behavior:

- Process only the selected stage families.
- Avoid unnecessary intraday fetches.
- Avoid unnecessary metadata/profile calls.
- Batch price downloads where reliable.
- Use concurrent symbol processing with controlled worker count.
- Use adaptive batch sizing for symbol processing.
- Keep per-symbol failures isolated.
- Stream progress to the web UI.
- Preserve auditability despite batching/concurrency.

Performance should not break trading logic. If a faster path reduces classification correctness, the faster path is not acceptable.

### Adaptive Batch Loading

The scanner should start with a conservative first batch and increase later batch sizes until it reaches either the configured `Max Symbols` limit or the total count of input symbols.

Required behavior:

- First batch should be small enough to produce quick initial progress.
- Later batches should increase in size to reduce total runtime.
- Batch growth should stop at the configured maximum batch size.
- Processing should stop at the lower of `Max Symbols` or total valid input count.
- Batch logs should record batch number, batch size, processed count, and remaining count.

## 13. Error Handling

Errors must be structured and auditable.

Examples:

- Missing price data.
- Insufficient history.
- Provider timeout.
- Invalid symbol.
- Missing required columns.
- Indicator calculation failure.
- Stage classification failure.
- Output write failure.

One symbol failing must not fail the whole run unless the input or output layer itself is invalid.

## 14. Result Contract

Each processed symbol should produce a structured result similar to:

```text
Identity:
  Symbol
  CompanyName
  Exchange
  Sector
  Industry

Market Data:
  LatestPrice
  MarketCap
  AvgDailyVolume
  AvgMonthlyVolume

Baseline:
  BaselineState
  BaselineReason
  Baseline values used

Stage:
  SelectedStageFamily
  DetectedStage
  StageReason
  RawStageChecks
  L2Path
  L3FunctionsCalled

Scoring:
  ConfidenceScore
  ScoreComponents
  ScoreWeights

Filtering:
  FilterPassed
  FilterReason

Audit:
  RunTimestamp
  JobId
  InputSource
  ConfigProfile
  UserOverrides
  ProviderErrors
```

## 15. Implementation Direction

Short-term:

- Keep the original `web_app.py` as fallback/reference only.
- Use the new `web_app_v2.py` as the web/runtime shell in the clean worktree.
- Keep current Crossover and Divergence behavior, but remove ambiguous histogram-threshold leakage when refactoring.
- Add clear stage-family separation in the engine contract.
- Refactor current compute behavior away from global indicator calculation and toward L1-first, L2-routed, L3-on-demand calculation.
- Keep full audit output.

Medium-term:

- Extract compute-only indicator functions.
- Add explicit L1 baseline module.
- Add explicit L2 stage router.
- Extract Crossover decision module.
- Extract Divergence decision module.
- Add Momentum Trading module after its detailed rules are agreed.
- Move config toward named profiles and explicit threshold scopes.

Long-term:

- Add provider abstraction.
- Add cached/prepared universe metadata.
- Add output formatting/presets only after engine behavior is stable.
- Add validation/backtest support for Momentum Trading methodology.

## 16. Decision Principles

- Trading meaning wins over code convenience.
- Stage families must remain semantically separate.
- Baseline comes before stage calculation.
- L2 chooses the path before L3 calculates detailed evidence.
- Crossover means transition, not established regime.
- Divergence raw evidence is not automatically a final candidate.
- Momentum Trading uses stock-specific historical behavior.
- Status Quo is a fallback output classification with an explanation, not a selectable stage family.
- Configuration owns thresholds.
- Compute calculates; decision classifies; explanation/audit explains.
- Fast results are required, but not at the cost of incorrect classification.

