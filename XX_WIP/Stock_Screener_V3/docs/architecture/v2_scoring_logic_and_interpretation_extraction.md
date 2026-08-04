# V2 Scoring Logic And Interpretation Extraction

Last updated: 2026-06-16

Repo: `D:\Tools\Stock_Screener_V3`

Branch: `V3_Charter`

## Purpose

This document extracts the current V2-style scoring, interpretation, and output logic from the engine code into one human-readable reference.

It answers:

- what score fields exist;
- how `WeightedScore` is assembled;
- which indicator-derived components contribute to the score;
- how each stage family interprets those components;
- how score thresholds map to `SELECTED`, `WATCH`, `REJECTED`, and `STATUS_QUO`;
- which interpretation rules are still hardcoded in evaluator logic.

This is a code-grounded extraction, not a new design proposal.

## Source Files Used

Primary implementation sources:

- [evaluators.py](/D:/Tools/Stock_Screener_V3/src/stock_screener_v3/evaluators.py)
- [scoring_config.py](/D:/Tools/Stock_Screener_V3/src/stock_screener_v3/scoring_config.py)
- [output_contracts.py](/D:/Tools/Stock_Screener_V3/src/stock_screener_v3/output_contracts.py)
- [models.py](/D:/Tools/Stock_Screener_V3/src/stock_screener_v3/models.py)
- [backtest_engine.py](/D:/Tools/Stock_Screener_V3/src/stock_screener_v3/backtest_engine.py)

## Important Scope Note

This document reflects the current V2-compatible scoring logic as implemented in the present engine codebase.

That means:

- it is the best available extraction of the V2-style scoring behavior in code;
- it is not automatically the final signed-off scoring model for `V3_Charter`;
- some parts are already externalized into `scoring_config.py`;
- many interpretation thresholds and path-specific conditions are still hardcoded in `evaluators.py`.

So this file should be treated as:

- an extraction of current computational logic;
- a baseline for future matrix/config migration;
- a reference for understanding how score was actually derived in the current engine.

## High-Level Scoring Model

All three stage families produce a `ScoreResult` object with these components:

- `total_score`
- `route_score`
- `timing_score`
- `structure_score`
- `participation_score`
- `context_score`
- `risk_score`
- `labels`

The output diagnostics then expose:

- `WeightedScore`
- `MACDScore`
- `RSIScore`
- `ADXScore`
- `ScoreWeights`
- `ConfirmationScore`
- `QualityContextScore`

### Meaning Of The Main Score Fields

`WeightedScore`

- the final per-ticker family-specific score shown to the user;
- equals the total of route, timing, structure, participation, context, and risk components;
- emitted only when the candidate is not `STATUS_QUO`.

`MACDScore`

- currently defined as `route_score + timing_score`;
- effectively the family's momentum/route stack rather than a pure raw MACD value.

`RSIScore`

- derived from helper logic `_rsi_score(rsi)`;
- emitted as a separate diagnostic score.

`ADXScore`

- derived from helper logic `_adx_score(adx_value)`;
- emitted as a separate diagnostic score.

`ConfirmationScore`

- currently defined as:

```text
timing_score + structure_score + participation_score
```

`QualityContextScore`

- currently defined as:

```text
context_score + risk_score
```

## Formal Stage Scoring Config

The first extracted defaults now live in [scoring_config.py](/D:/Tools/Stock_Screener_V3/src/stock_screener_v3/scoring_config.py).

### Crossover Default Weights

- `route = 30`
- `timing = 20`
- `structure = 20`
- `participation = 15`
- `context = 10`
- `risk = 10`

Thresholds:

- `selected_min = 72`
- `watch_min = 58`

### Setup Default Weights

- `route = 30`
- `timing = 20`
- `structure = 20`
- `participation = 15`
- `context = 10`
- `risk = 10`

Thresholds:

- `selected_min = 72`
- `watch_min = 58`

### Divergence Default Weights

- `route = 30`
- `timing = 20`
- `structure = 15`
- `participation = 10`
- `context = 15`
- `risk = 10`

Thresholds:

- `selected_min = 72`
- `watch_min = 56`

## Common Helper Interpretations

The current code relies on several shared helper functions.

### Shared Risk Score

`_risk_score(direction, low_liquidity, below_ema200)`

Starts at `10`.

Adjustments:

- `-5` if `LOW_LIQUIDITY`
- `-5` if direction is `BULLISH` and ticker is `BELOW_EMA200`

Lower bound:

- minimum `0`

Interpretation:

- low liquidity always hurts risk score;
- being below `EMA200` only penalizes bullish candidates, not bearish ones.

### Shared RSI Diagnostic Score

`_rsi_score(rsi)`

- `10` if `50 <= RSI <= 65`
- `6` if `45 <= RSI < 50` or `65 < RSI <= 72`
- `2` otherwise

Interpretation:

- this is a separate diagnostic score, not the only place RSI influences final family scoring.

### Shared ADX Diagnostic Score

`_adx_score(adx)`

- `10` if `ADX >= 25`
- `6` if `ADX >= 18`
- `2` otherwise

Interpretation:

- stronger ADX gets a better diagnostic value;
- again, this is separate from family component scoring.

### Shared Participation Score

`_participation_score(direction, volume_vs_20, plus_di, minus_di)`

Base contributions:

- `+8` if `volume_vs_20 >= 100`

Directional contributions:

- bullish: `+7` if `PlusDI >= MinusDI`
- bearish: `+7` if `MinusDI >= PlusDI`

Interpretation:

- above-normal volume and DI alignment together provide participation support.

### Shared Context Score

`_context_score(direction, rsi, close_location)`

Bullish:

- `+5` if `45 <= RSI <= 70`
- `+5` if `DailyCloseLocationPct >= 60`

Bearish:

- `+5` if `30 <= RSI <= 55`
- `+5` if `DailyCloseLocationPct <= 40`

Interpretation:

- the same raw indicator can be interpreted differently by direction.

## Crossover Scoring Extraction

### Crossover Route Classification

The Crossover route is built by `_classify_crossover_route(...)`.

#### Route 1: Fresh Bull Cross

Condition:

- `MACD_1D_CrossoverState == BULL_CROSS`
- and both `MACD value <= 0` and `MACD signal <= 0`

Output:

- `CandidateState = PRE_BULL_CROSSOVER`
- `OpportunityType = BULLISH_TRANSITION_CROSSOVER`
- `Direction = BULLISH`
- `RouteScore = 30`
- `Reason = DAILY_MACD_BULL_CROSS`
- `TimingProfile = fresh`

Important interpretation:

- a bull cross above the zero line is explicitly rejected as continuation, not transition.

#### Route 2: Bull Cross Above Zero Line

Condition:

- `MACD_1D_CrossoverState == BULL_CROSS`
- but MACD pair is not fully below zero line

Output:

- `STATUS_QUO`
- reason: `BULL_CROSS_ABOVE_ZERO_LINE_CONTINUATION`

Interpretation:

- this is a major anti-leakage rule;
- already-bullish continuation must not become `PRE_BULL_CROSSOVER`.

#### Route 3: Fresh Bear Cross

Condition:

- `MACD_1D_CrossoverState == BEAR_CROSS`

Output:

- `CandidateState = PRE_BEAR_CROSSOVER`
- `OpportunityType = BEARISH_TRANSITION_CROSSOVER`
- `Direction = BEARISH`
- `RouteScore = 30`
- `Reason = DAILY_MACD_BEAR_CROSS`
- `TimingProfile = fresh`

#### Route 4: Near Bear Transition Above Signal

Condition:

- `CrossoverState == ABOVE_SIGNAL`
- histogram deteriorating
- `MACD distance < 0.15`
- `Histogram < 0.15`
- and one of:
  - `EMA20_Below`
  - `LowerHigh_5D`
  - bearish DI support

Output:

- `PRE_BEAR_CROSSOVER`
- `RouteScore = 18`
- `Reason = DAILY_MACD_NEAR_BEAR_TRANSITION`
- `TimingProfile = early`

#### Route 5: Bearish Below-Signal Deterioration

Condition:

- `CrossoverState == BELOW_SIGNAL`
- histogram deteriorating
- and `EMA20_Below` or `LowerHigh_5D`

Output:

- `PRE_BEAR_CROSSOVER`
- `RouteScore = 20`
- `Reason = DAILY_MACD_BELOW_SIGNAL_DETERIORATING`
- `TimingProfile = developing`

#### Route 6: Near Bull Transition Below Signal

Condition:

- `CrossoverState == BELOW_SIGNAL`
- histogram improving
- `MACD distance > -0.15`
- `Histogram > -0.15`
- MACD pair below zero line

Output:

- `PRE_BULL_CROSSOVER`
- `RouteScore = 18`
- `Reason = DAILY_MACD_NEAR_BULL_TRANSITION`
- `TimingProfile = early`

#### Otherwise

- `STATUS_QUO`
- `Reason = NO_CROSSOVER_ROUTE`

### Crossover Timing Score

`_timing_score(direction, crossover_state, improving, deteriorating)`

Bullish:

- `+10` for fresh `BULL_CROSS`
- `+10` if histogram improving

Bearish:

- `+10` for fresh `BEAR_CROSS`
- `+10` if histogram deteriorating

Cap:

- maximum `20`

### Crossover Structure Score

`_structure_score(...)`

Bullish:

- `+8` if `price >= EMA20`
- `+7` if `price >= EMA200`
- `+5` if `HigherLow_5D`

Bearish:

- `+8` if `price <= EMA20`
- `+7` if `price <= EMA200`
- `+5` if `LowerHigh_5D`

### Crossover Participation Score

Uses shared participation logic:

- volume support;
- DI directional support.

### Crossover Context Score

Uses shared context logic:

- bullish RSI band and strong close location;
- bearish RSI band and weak close location.

### Crossover Candidate-Class Interpretation

If route is invalid:

- `STATUS_QUO`

Else if `total >= 72` and no risk tags:

- `SELECTED`
- priority `A`
- confidence `HIGH`

Else if `total >= 58`:

- `WATCH`
- priority `B` or `NEEDS_MANUAL_REVIEW` if risk tags exist
- confidence `MEDIUM`

Else:

- `REJECTED`
- priority `C`
- confidence `LOW`

### Crossover Reason/Tag Interpretation

Additional reasons:

- `CONSTRUCTIVE_PRICE_STRUCTURE` / `BEARISH_PRICE_STRUCTURE` if structure score is high
- `PARTICIPATION_SUPPORT` / `SELLER_PARTICIPATION_SUPPORT` if participation is high
- `ACCEPTANCE_SUPPORT` / `BEARISH_ACCEPTANCE_SUPPORT` if context is high

Risk tags:

- `LOW_LIQUIDITY`
- `BELOW_EMA200` for bullish cases only

## Setup Scoring Extraction

### Setup Route Classification

The Setup route is built by `_classify_momentum_route(...)`.

#### Route 1: Pullback Re-entry

Bull-phase requirement:

- `MACD crossover state == ABOVE_SIGNAL`
- and `LatestPrice >= EMA20`

Additional trigger:

- `EMA20_Reclaim` or `HigherLow_5D`

Output:

- `CandidateState = BULL_PULLBACK_REENTRY`
- `OpportunityType = BULLISH_PULLBACK_REENTRY`
- `Direction = BULLISH`
- `RouteScore = 28`
- `Reason = BULL_PULLBACK_REENTRY_ROUTE`
- `TimingProfile = reentry`

#### Route 2: Continuation Momentum

Bull-phase requirement:

- `ABOVE_SIGNAL`
- `LatestPrice >= EMA20`

Additional trigger:

- `PriceLadder_Passed`
- `EMA20 >= EMA50`
- bullish DI support

Output:

- `CandidateState = BULL_CONTINUATION_MOMENTUM`
- `OpportunityType = BULLISH_CONTINUATION_MOMENTUM`
- `RouteScore = 26`
- `Reason = BULL_CONTINUATION_ROUTE`
- `TimingProfile = continuation`

#### Route 3: Momentum Expansion

Bull-phase requirement:

- `ABOVE_SIGNAL`
- `LatestPrice >= EMA20`

Additional trigger:

- histogram improving
- histogram positive

Output:

- `CandidateState = BULL_CONTINUATION_MOMENTUM`
- `OpportunityType = BULLISH_MOMENTUM_EXPANSION`
- `RouteScore = 22`
- `Reason = BULL_MOMENTUM_EXPANSION_ROUTE`
- `TimingProfile = expansion`

#### Otherwise

- `STATUS_QUO`
- `Reason = NO_MOMENTUM_SETUP_ROUTE`

### Setup Timing Score

`_momentum_timing_score(histogram, improving, ema20_reclaim)`

- `+8` if histogram positive
- `+7` if histogram improving
- `+5` if `EMA20_Reclaim`

Cap:

- maximum `20`

### Setup Structure Score

`_momentum_structure_score(...)`

- `+5` if `price >= EMA20`
- `+5` if `EMA20 >= EMA50`
- `+5` if `price >= EMA200`
- `+3` if `HigherLow_5D`
- `+2` if `PriceLadder_Passed`

### Setup Participation Score

Uses shared bullish participation logic.

### Setup Context Score

Uses shared bullish context logic.

### Setup Candidate-Class Interpretation

If route invalid:

- `STATUS_QUO`

Special hard rule:

- if route is `BULL_PULLBACK_REENTRY`
- and ticker is `BELOW_EMA200`
- then force `REJECTED`

This creates:

- `MomentumSetupContextRule = PULLBACK_REENTRY_BELOW_EMA200`
- `MomentumSetupContextAction = REJECT`

Normal thresholds:

- `SELECTED` if `total >= 72` and no risk tags
- `WATCH` if `total >= 58`
- `REJECTED` otherwise

### Setup Reason/Tag Interpretation

Reasons added when scores are strong:

- `BULL_PHASE_STRUCTURE_SUPPORT`
- `PARTICIPATION_SUPPORT`
- `ACCEPTANCE_SUPPORT`

Risk tags:

- `LOW_LIQUIDITY`
- `BELOW_EMA200`

Special reason:

- `PULLBACK_REENTRY_BELOW_EMA200`

## Divergence Scoring Extraction

### Divergence Route Classification

The Divergence route is built by `_classify_divergence_route(candidate)`.

#### Regular Bullish Divergence

- `CandidateState = BULLISH_DIVERGENCE`
- `OpportunityType = BULLISH_REGULAR_DIVERGENCE`
- `Direction = BULLISH`
- `DivergenceType = REGULAR`
- `RouteScore = 30`
- `Reason = BULLISH_REGULAR_DIVERGENCE_ROUTE`
- `TimingProfile = reversal_watch`

#### Regular Bearish Divergence

- `CandidateState = BEARISH_DIVERGENCE`
- `OpportunityType = BEARISH_REGULAR_DIVERGENCE`
- `Direction = BEARISH`
- `DivergenceType = REGULAR`
- `RouteScore = 30`
- `Reason = BEARISH_REGULAR_DIVERGENCE_ROUTE`
- `TimingProfile = exit_watch`

#### Hidden Bullish Divergence

- `CandidateState = HIDDEN_BULLISH_DIVERGENCE`
- `OpportunityType = HIDDEN_BULLISH_CONTINUATION`
- `Direction = BULLISH`
- `DivergenceType = HIDDEN`
- `RouteScore = 28`
- `Reason = HIDDEN_BULLISH_DIVERGENCE_ROUTE`
- `TimingProfile = continuation`

#### Hidden Bearish Divergence

- `CandidateState = HIDDEN_BEARISH_DIVERGENCE`
- `OpportunityType = HIDDEN_BEARISH_CONTINUATION`
- `Direction = BEARISH`
- `DivergenceType = HIDDEN`
- `RouteScore = 28`
- `Reason = HIDDEN_BEARISH_DIVERGENCE_ROUTE`
- `TimingProfile = failed_recovery`

#### Otherwise

- `STATUS_QUO`
- `Reason = NO_DIVERGENCE_ROUTE`

### Divergence Timing Score

`_divergence_timing_score(bars_ago, confirmation_state)`

- `+10` if `CONFIRMED`
- `+4` if `RAW`
- `+10` if `bars_ago <= 5`
- `+6` if `bars_ago <= 12`

Cap:

- maximum `20`

### Divergence Structure Score

`_divergence_structure_score(...)`

Bullish:

- `+5` if hidden bullish and `HigherLow_5D`
- `+4` if `EMA20_Reclaim`
- `+4` if `price >= EMA200`
- `+3` if `price >= EMA20`

Bearish:

- `+5` if hidden bearish and `LowerHigh_5D`
- `+4` if `EMA20_Below`
- `+4` if `price <= EMA20`
- `+3` if `price <= EMA200`

Cap:

- maximum `15`

### Divergence Participation Score

`_divergence_participation_score(...)`

- `+4` if `volume_vs_20 >= 100`
- bullish: `+6` if `PlusDI >= MinusDI`
- bearish: `+6` if `MinusDI >= PlusDI`

Cap:

- maximum `10`

### Divergence Context Score

`_divergence_context_score(direction, rsi, close_location)`

Bullish RSI:

- `+8` if `35 <= RSI <= 60`
- `+4` if `30 <= RSI < 35` or `60 < RSI <= 68`

Bearish RSI:

- `+8` if `45 <= RSI <= 75`
- `+4` if `38 <= RSI < 45` or `75 < RSI <= 82`

Bullish close location:

- `+7` if `close_location >= 45`

Bearish close location:

- `+7` if `close_location <= 55`

Cap:

- maximum `15`

### Divergence Candidate-Class Interpretation

If route invalid:

- `STATUS_QUO`

If `total >= 72`, no risk tags, and `confirmation_state == CONFIRMED`:

- `SELECTED`

Else if `total >= 56` and not `raw_bullish_below_ema200`:

- `WATCH`

Else:

- `REJECTED`

Special hard rule:

- bullish divergence below `EMA200`
- and not confirmed
- becomes a restricted case through `RAW_BULLISH_DIVERGENCE_BELOW_EMA200`

This prevents raw/unconfirmed bullish divergence below `EMA200` from being promoted into normal `WATCH`.

### Divergence Reason/Tag Interpretation

Reasons added:

- `DIVERGENCE_CONFIRMED`
- `RECENT_DIVERGENCE`
- `DIVERGENCE_STRUCTURE_SUPPORT`
- `DIVERGENCE_PARTICIPATION_CONTEXT`
- `DIVERGENCE_ACCEPTANCE_CONTEXT`
- `RAW_BULLISH_DIVERGENCE_BELOW_EMA200`

Risk tags:

- `LOW_LIQUIDITY`
- `BELOW_EMA200` for bullish cases

## Family-Specific Outputs Exposed To V2-Compatible Surfaces

The V2-compatible output contract still exposes a large number of score and interpretation fields.

Core user-facing/common fields:

- `WeightedScore`
- `MACDScore`
- `RSIScore`
- `ADXScore`
- `ScoreWeights`
- `ConfirmationScore`
- `QualityContextScore`
- `CandidateState`
- `CandidateStateRaw`

Crossover-specific interpretation fields:

- `CrossoverConfidence`
- `CrossoverQualityScore`
- `CrossoverQualityComponents`
- `CrossoverTimingProfile`
- `CrossoverReason`
- `CrossoverReasonCodes`

Setup-specific interpretation fields:

- `MomentumSetupConfidence`
- `MomentumSetupQualityScore`
- `MomentumSetupQualityComponents`
- `MomentumSetupContextRule`
- `MomentumSetupContextAction`
- `MomentumSetupTimingProfile`
- `MomentumSetupReason`
- `MomentumSetupReasonCodes`

Divergence-specific interpretation fields:

- `DivergenceDirection`
- `DivergenceType`
- `DivergenceOpportunityType`
- `DivergenceConfirmationState`
- `DivergenceQualityScore`
- `DivergenceQualityComponents`
- `DivergenceTimingProfile`
- `DivergenceReason`
- `DivergenceReasonCodes`

Backtest-oriented score outputs:

- `Confidence`
- `TotalScore`
- `RouteScore`
- `TimingScore`
- `StructureScore`
- `ParticipationScore`
- `ContextScore`
- `RiskScore`
- `ReasonCodes`

## Hardcoded Interpretation Still Present

This extraction makes clear that some important interpretation logic is still hardcoded in evaluator functions.

Examples:

- exact route transitions and their route scores;
- MACD distance and histogram near-zero thresholds such as `0.15`;
- RSI scoring bands;
- ADX scoring bands;
- divergence confirmation gating;
- `BELOW_EMA200` rejection logic for certain bullish families;
- family-specific selected/watch thresholds already partly externalized, but not all path logic is config-owned.

This is important because the matrix/charter direction requires:

- no hidden thresholds inside evaluator code over the long run;
- matrix-owned meaning;
- config-owned tunable values where appropriate.

## Practical Use Of This Document

This file should be used for:

- understanding how current V2-style scoring actually works in code;
- comparing future matrix-owned logic against current behavior;
- deciding what should move from evaluator hardcoding into config or matrix;
- explaining why two families can score similarly while still meaning different things.

It should not be used to justify silent scoring changes.

Any future change to these computational rules should be reflected in:

- the matrix;
- the charter if top-level meaning changes;
- this extraction file if scoring behavior changes materially.
