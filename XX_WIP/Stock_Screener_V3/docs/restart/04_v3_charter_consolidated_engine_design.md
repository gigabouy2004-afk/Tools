# Stock Screener V3_Charter Consolidated Engine Design

Last updated: 2026-06-16

Repo: `D:\Tools\Stock_Screener_V3`

Branch: `V3_Charter`

Document version: `V1.6`

## Revision Control

This document must maintain its own in-document revision log in addition to Git history.

Rules:

- every material change to this document must update `Last updated`
- every material change must append one row to the revision table below
- Git history is not a substitute for this in-document revision record
- future sessions must preserve this table instead of overwriting it

| Version | Date | Commit | Change |
|---|---|---|---|
| `V1.6` | 2026-06-16 | `9c11379` | Locked RSI upper-bound manifest shape, set the SETUP path to a monthly default with optional override, fixed sector and market context to zero-weight audit rows, restricted 4H and 1H MACD to CROSSOVER initially, and promoted PriceBand into a signed-off matrix row. |
| `V1.5` | 2026-06-16 | `be20679` | Locked long-boundary math definitions, established the versioned scoring-manifest schema, and declared the regression dataset/test-matrix repository layout and approval workflow. |
| `V1.4` | 2026-06-16 | `0f49e7c` | Established the D-vs-D+X engine as a permanent regression suite, added regression-gate and drift-tolerance rules, tightened deep-copy slicing and lower-timeframe truncation, clarified mixed zero-line and Setup forced-rejection handling, and added manifest-version/test-matrix requirements. |
| `V1.3` | 2026-06-16 | `075eabc` | Added in-document revision control and explicit versioning. |
| `V1.2` | 2026-06-16 | `ded6099` | Added explicit route-isolate locks, strict D-vs-D+X slicing isolation, lower-timeframe nesting rule, scoring-manifest direction, forced-rejection output rule, and long-boundary formula requirements. |
| `V1.1` | 2026-06-16 | `409bd91` | Absorbed scoring and interpretation extraction into the consolidated charter so it can serve as the single offline master document. |
| `V1.0` | 2026-06-16 | `59b9cc7` | Created the standalone consolidated charter and wired restart documents to use it. |

## Document Role

This document is the standalone consolidated charter for `V3_Charter`.

It is intended to capture, in one place:

- the business purpose of the engine;
- the allowed stage families and their meanings;
- the engine workflow and hierarchy;
- the scope boundaries and non-goals;
- the scoring and output contract;
- the data-provider rules;
- the matrix design and the current approved matrix content;
- the implementation guardrails needed to prevent path leakage and regression.

This document is comprehensive by design. A future session should be able to restart from this file alone and understand what the engine is trying to do, how it is meant to behave, and what must not be changed casually.

The original seed charter remains:

```text
docs/charter/v3_original_intent_and_handover.md
```

This consolidated document does not replace the original historical seed. It restates and integrates the approved intent in a standalone form.

## Core Purpose

`V3_Charter` is a CSV-based, user-directed equity screening engine.

Its purpose is to evaluate a user-supplied list of tickers and identify only those names that qualify for the user-selected technical stage family or families, using V2 as a reference library for technical-analysis indicator calculations and tuned threshold logic.

The engine is not meant to be:

- a broad default market scanner;
- a portfolio-management engine;
- a stop-loss engine;
- an automated trading system;
- an execution engine;
- a sector-calibration research project by default;
- a macro/regime platform by default;
- a universal pan-market screener unless the user explicitly supplies that universe.

The engine exists to answer a focused question:

```text
From the user-supplied equity universe, which tickers currently qualify for the selected technical opportunity family, and why?
```

## Business Meaning Of The Stage Families

The engine has exactly three user-facing stage families:

- `CROSSOVER`
- `DIVERGENCE`
- `SETUP`

There is no user-facing fourth family.

### CROSSOVER

`CROSSOVER` contains two critical business directions:

- `PRE_BULL_CROSSOVER`
- `PRE_BEAR_CROSSOVER`

`PRE_BULL_CROSSOVER` means:

- enter early enough to maximize the natural bull phase of the stock.

`PRE_BEAR_CROSSOVER` means:

- detect weakening early enough to support capital preservation and avoid future notional loss on an existing long-held equity.

This does not imply stop-loss trading logic. It means the engine must identify technically weakening holdings early enough to support an informed capital-preservation decision.

So `CROSSOVER` is not just a technical crossing event. It is the engine's transition-detection family for:

- early bull-phase entry;
- early bear-phase capital-preservation review.

### DIVERGENCE

`DIVERGENCE` means:

- validate whether a credible investment opportunity may be developing through meaningful disagreement between price behavior and momentum behavior.

`DIVERGENCE` is independent from `CROSSOVER` and `SETUP`. It must not be inferred just because another family fails.

### SETUP

`SETUP` means:

- a pure-play market-based entry path where technical-analysis indicators provide confidence/support for entering a new position;
- the position may be more temporary than a Pre-Bull entry because the current bull phase may later peak and rotate toward bear-side pressure.

`SETUP` is therefore not the same as `PRE_BULL_CROSSOVER`.

It is for:

- continuation;
- pullback re-entry;
- recovery within an existing bull structure;
- extension behavior where entry is still technically justified, but not at the very beginning of the natural bull phase.

## Engine Scope

The engine must:

- take a user-supplied CSV universe as the working universe;
- support stage-family selection;
- support user-selected qualifying filters;
- fetch required market data through an API/provider layer;
- process each ticker through a path-first technical engine;
- produce only qualified candidates for the selected family/families;
- rank those candidates within their family-specific scoring model;
- log rejected names with exact failure reasons;
- support D-date and D+X validation using the same logical engine.

The engine must not:

- silently expand the universe;
- infer extra stage families not chosen by the user;
- flatten all families into one undifferentiated ranking pool;
- let context rows override route logic;
- let one family's logic leak into another family's classification.

## User Workflow

The intended workflow is:

1. User supplies a CSV file containing ticker rows.
2. User selects one or more stage families.
3. User applies qualifying filters.
4. Engine loads only the data required for the selected logic.
5. Engine classifies each ticker.
6. Engine shows only qualifying candidates.
7. Engine logs non-qualifiers with exact reasons.
8. Engine can replay the same logic historically on D-date data and validate on D+X.

### Filter Contract

Filters are first-class engine inputs, not UI decoration.

Examples include:

- market cap;
- average volume;
- exchange;
- sector;
- industry;
- other metadata-based qualifying constraints.

The filter system exists before candidate display. A ticker that does not satisfy the filter contract is not a candidate, even if its technical state would otherwise be interesting.

### Candidate Display Contract

The engine is a selector, not a universal status reporter.

That means:

- qualifying tickers are shown;
- non-qualifying tickers are not shown as candidates;
- non-qualifying tickers are still logged in the processing output with reasons and relevant values.

`STATUS_QUO` is therefore not intended as a primary user-facing candidate family.

## Single-Engine Construction Rule

`V3_Charter` must be one cohesive engine.

It must not devolve into:

- separate stitched scripts;
- isolated family implementations with different design rules;
- uncontrolled indicator add-ons;
- route overrides caused by convenience code.

Everything must fit the same hierarchical engine:

```text
CSV input
-> user-selected path
-> API data retrieval required by that path
-> L0 preparation
-> L1 baseline
-> L2 route
-> L3 path-specific evidence
-> L4 classification and scoring
-> L5 output and D+X validation
```

## V2 Relationship

V2 is not the product model.

V2 is the reference library for:

- technical-analysis indicator calculations;
- tuned thresholds and parameter practice;
- diagnostic/output visibility;
- known evidence concepts.

V2 must not be copied forward blindly as finished engine behavior.

Any V2 component may be reused only if it is placed correctly in:

- the selected stage family;
- the correct hierarchy level;
- the matrix-approved row/cell meaning.

Key rule:

```text
V2 additions can refine confidence, risk, explanation, or score only inside the selected path trajectory.
They must not become base-level drivers.
```

## Engine Hierarchy

### L0: Input, Data, And Date Preparation

L0 prepares the run.

Responsibilities:

- load the CSV;
- normalize symbols;
- validate required fields;
- resolve provider symbols;
- capture the selected stage families;
- capture the selected filters;
- capture D-date and D+X settings where applicable;
- fetch data through the configured provider;
- isolate per-symbol provider/data failures.

Strict historical slicing rule:

- for historical D-date analysis, the provider wrapper must explicitly slice and truncate the active computation dataframe at index `D` before passing data into any indicator library, evidence builder, or evaluator;
- the active computation dataframe must be isolated with `.copy(deep=True)` or equivalent full-memory isolation so no forward-view references survive the slice;
- forward bars beyond `D` must be stored in a separate isolated forward-validation container;
- that forward-validation container belongs only to L5 and must not be visible to L1, L2, L3, or L4.

### L1: Baseline

L1 establishes neutral technical facts.

Responsibilities:

- current MACD state;
- current moving-average context;
- current structure context;
- current volume/liquidity context where needed;
- any neutral facts required for safe routing.

L1 is not final classification.

### L2: Route

L2 decides which family or families are legitimately eligible, based on:

- user-selected family restriction;
- baseline facts;
- hard path boundaries.

L2 is where path leakage must be prevented.

Route-isolate lock rule:

- L2 must operate with mutual-exclusion route locks;
- if only `CROSSOVER` is selected, `SETUP` and `DIVERGENCE` must be completely locked out and ignored as evaluators;
- if only `SETUP` is selected, `CROSSOVER` and `DIVERGENCE` must be completely locked out and ignored;
- if only `DIVERGENCE` is selected, `CROSSOVER` and `SETUP` must be completely locked out and ignored;
- if multiple stage families are selected, only those explicitly selected families may enter the evaluable set.

Examples of prohibited leakage:

- a continuation state classified as a fresh crossover;
- divergence inferred because crossover failed;
- setup logic used as fallback after crossover failure.
- failure to qualify for one route must never cascade into accidental fallback evaluation by another unselected route.

### L3: Evidence

L3 calculates path-specific evidence only after route context is known.

Responsibilities:

- indicator computation on demand;
- derived evidence values;
- path-specific condition logic;
- evidence packaging for L4.

L3 must not perform broad global interpretation before path selection.

Lower-timeframe synchronization rule:

- lower-timeframe layers such as `4H` and `1H` cannot act as independent entry gates;
- they are nested validation parameters within L3 evidence;
- they may be evaluated only after a valid daily (`1D`) macro route has already been established;
- they may refine timing, freshness, and confirmation quality, but they must not manufacture a route that the daily baseline did not authorize;
- their API pulls must also truncate at the final matching market minute that still belongs to trading day `D`.

Initial release scope rule:

- lower-timeframe MACD confirmation using `4H` and `1H` is approved only for the `CROSSOVER` family in the initial release;
- `SETUP` remains anchored to its higher-timeframe structural baseline and must not use `4H` or `1H` MACD as an initial route, filter, or scoring gate;
- `DIVERGENCE` does not use lower-timeframe MACD by default in the initial release unless a later charter revision signs it off explicitly.

### L4: Classification And Scoring

L4 converts routed evidence into:

- candidate class;
- confidence/priority;
- weighted score;
- reason codes;
- rejection decisions.

Scoring is post-qualification only.

### L5: Output, Audit, And Validation

L5 produces:

- candidate CSV output;
- logs and summaries;
- rejection diagnostics;
- D+X validation records;
- provider/data status;
- enough audit fields to explain every pass/fail decision.

## Data Provider Contract

The engine must be API-driven.

The current free default backend is Yahoo Finance through `yfinance`, but the logic must remain behind a swappable provider abstraction.

The provider contract is:

- fetch only the fields required by the selected family and requested evidence;
- preserve deterministic D-date slicing;
- support per-symbol failure isolation;
- support forward D+X validation retrieval;
- avoid changing engine semantics through provider-specific quirks;
- force every new feed, context row, or external evidence source to obey the same no-bleed D-date slicing contract before its values are exposed to L1-L4;
- provide a snapshot or cache interface for unstable third-party rows so historical replay can load the exact state known on day `D`.

Historical replay isolation rule:

- historical runs must expose two distinct data zones:
  - active computation data through `D`
  - isolated forward validation data after `D`
- only the active computation zone may be used for indicator calculation;
- the forward validation zone must remain inaccessible until L5 validation.

Deterministic snapshot rule:

- if a future row depends on volatile third-party web state, sentiment, or external point-in-time context that cannot be replayed reliably from a live API;
- the engine must read that row from a file-backed or cache-backed historical snapshot for the requested day `D`;
- historical replay must not rely on a live retrospective query that can drift after the fact.

The engine must not assume universal OHLCV input.

Examples:

- MACD baseline logic may require only Close series;
- OHLC fields are only requested when a chosen evidence row needs them;
- volume is only required when the selected logic uses volume participation rows.

## Output And Audit Contract

Every result must be explainable.

Minimum output expectations:

- input symbol;
- resolved provider symbol;
- selected stage family;
- D-date;
- qualification result;
- final candidate class;
- weighted score;
- reason codes;
- routed path;
- evidence used;
- rejection reason where applicable;
- provider/data status;
- D+X validation result where applicable.

The V2-style auditability standard remains in force:

- visible diagnostics;
- CSV-friendly structure;
- component-level explainability;
- no silent drops of failed logic.

## Scoring Contract

WeightedScore is:

- per ticker;
- computed only after qualification;
- family-specific in meaning;
- grouped by family in display.

This means:

- a `PRE_BULL_CROSSOVER` ticker can score `81`;
- a `SETUP` ticker can also score `81`;
- those two scores are not a universal shared ranking by default.

The scoring formula belongs to the selected family and its active matrix rows.

Score is not route.
Score is not filter qualification.
Score is not a substitute for classification.

## Comprehensive Scoring And Interpretation

This section absorbs the current V2-style computational scoring logic into the consolidated charter so this document can serve as a true standalone offline reference.

### Formal Score Object

All three stage families currently build a score with these components:

- `total_score`
- `route_score`
- `timing_score`
- `structure_score`
- `participation_score`
- `context_score`
- `risk_score`
- `labels`

The common diagnostic outputs derived from those components are:

- `WeightedScore`
- `MACDScore`
- `RSIScore`
- `ADXScore`
- `ScoreWeights`
- `ConfirmationScore`
- `QualityContextScore`

### Meaning Of Common Score Fields

`WeightedScore`

- final per-ticker family-specific score shown to the user
- total of route, timing, structure, participation, context, and risk components
- emitted only when the row is not `STATUS_QUO`

`MACDScore`

- currently interpreted as `route_score + timing_score`

`RSIScore`

- diagnostic RSI quality score derived from current helper logic

`ADXScore`

- diagnostic ADX quality score derived from current helper logic

`ConfirmationScore`

- currently:

```text
timing_score + structure_score + participation_score
```

`QualityContextScore`

- currently:

```text
context_score + risk_score
```

### External Scoring Manifest Direction

The required long-term direction is that scoring behavior be owned by an external declarative manifest instead of hidden in evaluator code.

That includes:

- component weights;
- selected/watch thresholds;
- conditional point awards;
- conditional point deductions;
- scoring bands tied to indicator states;
- route-specific or family-specific modifier rules.

Examples that should ultimately move out of hardcoded evaluator logic:

- `volume_vs_20 >= 100` yielding participation points;
- RSI band scoring;
- ADX band scoring;
- MACD near-transition distance thresholds;
- family-specific selected/watch cutoffs.

The filename `scoring_manifest.json` is a valid example, but the governing rule is declarative external ownership, not the exact filename or file extension.

Approved RSI upper-bound schema rule:

```json
"rsi_upper_bound": {
  "default": 80.0,
  "sector_overrides_enabled": false
}
```

Meaning:

- `80.0` is the current global baseline upper bound for RSI scoring;
- the threshold must live inside an object, not a raw integer or float field;
- this preserves forward compatibility for later sector-specific, market-specific, or fundamental-factor overlays such as EPS momentum without breaking the manifest shape;
- until future overrides are explicitly approved, `sector_overrides_enabled` remains `false`.

### Current Formal Stage Scoring Defaults

Current extracted defaults from implementation are:

#### Crossover

Weights:

- `route = 30`
- `timing = 20`
- `structure = 20`
- `participation = 15`
- `context = 10`
- `risk = 10`

Thresholds:

- `selected_min = 72`
- `watch_min = 58`

#### Setup

Weights:

- `route = 30`
- `timing = 20`
- `structure = 20`
- `participation = 15`
- `context = 10`
- `risk = 10`

Thresholds:

- `selected_min = 72`
- `watch_min = 58`

#### Divergence

Weights:

- `route = 30`
- `timing = 20`
- `structure = 15`
- `participation = 10`
- `context = 15`
- `risk = 10`

Thresholds:

- `selected_min = 72`
- `watch_min = 56`

### Shared Interpretation Helpers

#### Shared Risk Score

Current risk logic:

- starts from `10`
- subtract `5` for `LOW_LIQUIDITY`
- subtract `5` if direction is bullish and ticker is `BELOW_EMA200`
- minimum result is `0`

Interpretation:

- low liquidity is always negative
- `BELOW_EMA200` is currently a bullish-side risk penalty only

#### Shared RSI Diagnostic Score

Current helper behavior:

- `10` if `50 <= RSI <= 65`
- `6` if `45 <= RSI < 50` or `65 < RSI <= 72`
- `2` otherwise

#### Shared ADX Diagnostic Score

Current helper behavior:

- `10` if `ADX >= 25`
- `6` if `ADX >= 18`
- `2` otherwise

#### Shared Participation Score

Current helper behavior:

- `+8` if `volume_vs_20 >= 100`
- bullish: `+7` if `PlusDI >= MinusDI`
- bearish: `+7` if `MinusDI >= PlusDI`

#### Shared Context Score

Bullish:

- `+5` if `45 <= RSI <= 70`
- `+5` if `DailyCloseLocationPct >= 60`

Bearish:

- `+5` if `30 <= RSI <= 55`
- `+5` if `DailyCloseLocationPct <= 40`

## Crossover Computational Interpretation

### Route Logic

#### Fresh Bull Cross

Condition:

- `MACD_1D_CrossoverState == BULL_CROSS`
- `MACD value <= 0`
- `MACD signal <= 0`

Interpretation:

- real early bull transition candidate

Outputs:

- `CandidateState = PRE_BULL_CROSSOVER`
- `Direction = BULLISH`
- `RouteScore = 30`
- `Reason = DAILY_MACD_BULL_CROSS`
- `TimingProfile = fresh`

#### Bull Cross Above Zero

Condition:

- bull cross occurs but MACD pair is not fully below zero line

Interpretation:

- continuation, not early crossover transition

Outputs:

- `STATUS_QUO`
- `Reason = BULL_CROSS_ABOVE_ZERO_LINE_CONTINUATION`

Technical clarification:

- the problematic edge case is not strictly "both above zero";
- the real blind spot is any mixed zero-line bull-cross state where the MACD line and signal line are no longer both `<= 0`, but the pair is not yet cleanly treated by a signed-off rule.

Required charter rule:

- a mixed zero-line bull-cross case, such as `MACD line > 0` while `Signal line <= 0`, must not be left as an undefined fallback;
- it must be handled by an explicit matrix/config-owned rule instead of silently defaulting into generic `STATUS_QUO`;
- it is an authorized transition-context modifier, not a banned state by default.

#### Fresh Bear Cross

Condition:

- `MACD_1D_CrossoverState == BEAR_CROSS`

Interpretation:

- valid early bear transition / capital-preservation review candidate

Outputs:

- `CandidateState = PRE_BEAR_CROSSOVER`
- `Direction = BEARISH`
- `RouteScore = 30`
- `Reason = DAILY_MACD_BEAR_CROSS`
- `TimingProfile = fresh`

#### Near Bear Transition

Condition:

- above signal
- histogram deteriorating
- `MACD distance < 0.15`
- `Histogram < 0.15`
- and one of:
  - `EMA20_Below`
  - `LowerHigh_5D`
  - bearish DI support

Outputs:

- `PRE_BEAR_CROSSOVER`
- `RouteScore = 18`
- `Reason = DAILY_MACD_NEAR_BEAR_TRANSITION`
- `TimingProfile = early`

#### Bearish Below-Signal Deterioration

Condition:

- below signal
- histogram deteriorating
- and `EMA20_Below` or `LowerHigh_5D`

Outputs:

- `PRE_BEAR_CROSSOVER`
- `RouteScore = 20`
- `Reason = DAILY_MACD_BELOW_SIGNAL_DETERIORATING`
- `TimingProfile = developing`

#### Near Bull Transition

Condition:

- below signal
- histogram improving
- `MACD distance > -0.15`
- `Histogram > -0.15`
- MACD pair below zero line

Outputs:

- `PRE_BULL_CROSSOVER`
- `RouteScore = 18`
- `Reason = DAILY_MACD_NEAR_BULL_TRANSITION`
- `TimingProfile = early`

#### Otherwise

- `STATUS_QUO`

### Timing Score

Current timing logic:

- bullish fresh bull cross: `+10`
- bullish histogram improving: `+10`
- bearish fresh bear cross: `+10`
- bearish histogram deteriorating: `+10`
- capped at `20`

### Structure Score

Bullish:

- `+8` if `price >= EMA20`
- `+7` if `price >= EMA200`
- `+5` if `HigherLow_5D`

Bearish:

- `+8` if `price <= EMA20`
- `+7` if `price <= EMA200`
- `+5` if `LowerHigh_5D`

### Participation And Context

Uses shared participation and context helpers described earlier.

### Candidate-Class Logic

- invalid route -> `STATUS_QUO`
- `total >= 72` and no risk tags -> `SELECTED`
- `total >= 58` -> `WATCH`
- otherwise -> `REJECTED`

Priority:

- `A` for selected
- `B` for watch without risk tags
- `NEEDS_MANUAL_REVIEW` for watch with risk tags
- `C` for rejected

### Crossover Reason And Risk Interpretation

Extra reasons may include:

- `CONSTRUCTIVE_PRICE_STRUCTURE`
- `BEARISH_PRICE_STRUCTURE`
- `PARTICIPATION_SUPPORT`
- `SELLER_PARTICIPATION_SUPPORT`
- `ACCEPTANCE_SUPPORT`
- `BEARISH_ACCEPTANCE_SUPPORT`

Risk tags may include:

- `LOW_LIQUIDITY`
- `BELOW_EMA200` on bullish cases

## Setup Computational Interpretation

### Route Logic

#### Pullback Re-entry

Condition:

- MACD crossover state `ABOVE_SIGNAL`
- `LatestPrice >= EMA20`
- and `EMA20_Reclaim` or `HigherLow_5D`

Outputs:

- `BULL_PULLBACK_REENTRY`
- `RouteScore = 28`
- `Reason = BULL_PULLBACK_REENTRY_ROUTE`
- `TimingProfile = reentry`

#### Continuation Momentum

Condition:

- bull phase
- `PriceLadder_Passed`
- `EMA20 >= EMA50`
- bullish DI support

Outputs:

- `BULL_CONTINUATION_MOMENTUM`
- `RouteScore = 26`
- `Reason = BULL_CONTINUATION_ROUTE`
- `TimingProfile = continuation`

#### Momentum Expansion

Condition:

- bull phase
- histogram improving
- histogram positive

Outputs:

- `BULL_CONTINUATION_MOMENTUM`
- `RouteScore = 22`
- `Reason = BULL_MOMENTUM_EXPANSION_ROUTE`
- `TimingProfile = expansion`

#### Otherwise

- `STATUS_QUO`

### Timing Score

- `+8` if histogram positive
- `+7` if histogram improving
- `+5` if `EMA20_Reclaim`
- capped at `20`

### Structure Score

- `+5` if `price >= EMA20`
- `+5` if `EMA20 >= EMA50`
- `+5` if `price >= EMA200`
- `+3` if `HigherLow_5D`
- `+2` if `PriceLadder_Passed`

### Candidate-Class Logic

- invalid route -> `STATUS_QUO`
- special hard rule:
  - `BULL_PULLBACK_REENTRY` plus `BELOW_EMA200` -> forced `REJECTED`
- otherwise:
  - `total >= 72` and no risk tags -> `SELECTED`
  - `total >= 58` -> `WATCH`
  - else -> `REJECTED`

Special context outputs:

- `MomentumSetupContextRule = PULLBACK_REENTRY_BELOW_EMA200`
- `MomentumSetupContextAction = REJECT`

Forced-rejection output rule:

- the engine must still complete the normal score computation and diagnostic trail for the row;
- the row must keep its computed `WeightedScore`, component scores, reason codes, and supporting diagnostics;
- the candidate is then emitted as a priority `C` rejection rather than collapsed into an empty-scored record;
- the execution path must not short-circuit into a blank-score halt once the forced-rejection boundary is triggered.

### Setup Reason And Risk Interpretation

Reasons may include:

- `BULL_PHASE_STRUCTURE_SUPPORT`
- `PARTICIPATION_SUPPORT`
- `ACCEPTANCE_SUPPORT`
- `PULLBACK_REENTRY_BELOW_EMA200`

Risk tags may include:

- `LOW_LIQUIDITY`
- `BELOW_EMA200`

## Divergence Computational Interpretation

### Route Logic

#### Regular Bullish Divergence

- `CandidateState = BULLISH_DIVERGENCE`
- `RouteScore = 30`
- `Reason = BULLISH_REGULAR_DIVERGENCE_ROUTE`
- `TimingProfile = reversal_watch`

#### Regular Bearish Divergence

- `CandidateState = BEARISH_DIVERGENCE`
- `RouteScore = 30`
- `Reason = BEARISH_REGULAR_DIVERGENCE_ROUTE`
- `TimingProfile = exit_watch`

#### Hidden Bullish Divergence

- `CandidateState = HIDDEN_BULLISH_DIVERGENCE`
- `RouteScore = 28`
- `Reason = HIDDEN_BULLISH_DIVERGENCE_ROUTE`
- `TimingProfile = continuation`

#### Hidden Bearish Divergence

- `CandidateState = HIDDEN_BEARISH_DIVERGENCE`
- `RouteScore = 28`
- `Reason = HIDDEN_BEARISH_DIVERGENCE_ROUTE`
- `TimingProfile = failed_recovery`

#### Otherwise

- `STATUS_QUO`

### Timing Score

- `+10` if confirmation state is `CONFIRMED`
- `+4` if confirmation state is `RAW`
- `+10` if divergence bars ago `<= 5`
- `+6` if divergence bars ago `<= 12`
- capped at `20`

### Structure Score

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

- `15`

### Participation Score

- `+4` if `volume_vs_20 >= 100`
- bullish: `+6` if `PlusDI >= MinusDI`
- bearish: `+6` if `MinusDI >= PlusDI`
- capped at `10`

### Context Score

Bullish:

- `+8` if `35 <= RSI <= 60`
- `+4` if `30 <= RSI < 35` or `60 < RSI <= 68`
- `+7` if `close_location >= 45`

Bearish:

- `+8` if `45 <= RSI <= 75`
- `+4` if `38 <= RSI < 45` or `75 < RSI <= 82`
- `+7` if `close_location <= 55`

Cap:

- `15`

### Candidate-Class Logic

- invalid route -> `STATUS_QUO`
- `total >= 72`, no risk tags, and `CONFIRMED` -> `SELECTED`
- `total >= 56` and not raw-bullish-below-EMA200 -> `WATCH`
- otherwise -> `REJECTED`

Special hard rule:

- raw bullish divergence below `EMA200` is not promoted into normal watch logic

### Divergence Reason And Risk Interpretation

Reasons may include:

- `DIVERGENCE_CONFIRMED`
- `RECENT_DIVERGENCE`
- `DIVERGENCE_STRUCTURE_SUPPORT`
- `DIVERGENCE_PARTICIPATION_CONTEXT`
- `DIVERGENCE_ACCEPTANCE_CONTEXT`
- `RAW_BULLISH_DIVERGENCE_BELOW_EMA200`

Risk tags may include:

- `LOW_LIQUIDITY`
- `BELOW_EMA200` for bullish cases

## Family-Specific Diagnostic Outputs

Common score-oriented outputs include:

- `WeightedScore`
- `MACDScore`
- `RSIScore`
- `ADXScore`
- `ScoreWeights`
- `ConfirmationScore`
- `QualityContextScore`

Crossover-specific outputs include:

- `CrossoverConfidence`
- `CrossoverQualityScore`
- `CrossoverQualityComponents`
- `CrossoverTimingProfile`
- `CrossoverReason`
- `CrossoverReasonCodes`

Setup-specific outputs include:

- `MomentumSetupConfidence`
- `MomentumSetupQualityScore`
- `MomentumSetupQualityComponents`
- `MomentumSetupContextRule`
- `MomentumSetupContextAction`
- `MomentumSetupTimingProfile`
- `MomentumSetupReason`
- `MomentumSetupReasonCodes`

Divergence-specific outputs include:

- `DivergenceDirection`
- `DivergenceType`
- `DivergenceOpportunityType`
- `DivergenceConfirmationState`
- `DivergenceQualityScore`
- `DivergenceQualityComponents`
- `DivergenceTimingProfile`
- `DivergenceReason`
- `DivergenceReasonCodes`

Backtest-oriented outputs include:

- `Confidence`
- `TotalScore`
- `RouteScore`
- `TimingScore`
- `StructureScore`
- `ParticipationScore`
- `ContextScore`
- `RiskScore`
- `ReasonCodes`

## Remaining Hardcoded Interpretation

Even after the first scoring-config extraction, this consolidated charter must record that some important logic is still hardcoded in evaluator code.

Examples:

- exact route transitions and their route scores
- MACD near-zero / distance thresholds such as `0.15`
- RSI and ADX scoring bands
- divergence confirmation gating
- `BELOW_EMA200` forced-reject logic in certain bullish paths
- family-specific route details that are not yet matrix/config owned

Long-boundary math that is still not formally defined enough:

- `EMA52High`
- `EMA200High`
- associated boundary-distance percentages
- associated breach-count logic

This matters because the long-term charter direction is:

- matrix-owned meaning
- config-owned tunable values
- no hidden interpretation drift inside evaluator code

## Long-Boundary Formula Requirement

Before full implementation signoff, the following must be formally defined in math terms:

- whether `EMA52High` means an EMA applied to periodic highs;
- whether it means a smoothed trailing high-channel construct over a 52-period lookback;
- whether `EMA200High` means an EMA on highs, a trailing-extrema construct, or another bounded high-series definition;
- how each distance-to-boundary percentage is calculated;
- how each breach count is calculated;
- which lookback window, smoothing rule, and denominator are used.

These definitions must eventually resolve into explicit formulas, not descriptive labels only.

Approved long-boundary definitions:

- `EMA52High[t]` = exponential moving average applied directly to the daily `High` series using a span/lookback of `52`;
- `EMA200High[t]` = exponential moving average applied directly to the daily `High` series using a span/lookback of `200`;
- the source array for both is the provider-supplied historical `High` series truncated at `D`;
- no trailing-local-extrema substitution is allowed unless a future charter revision explicitly introduces a separate boundary family row for that purpose;
- `DistanceToEMA52HighPct[t] = ((Close[t] - EMA52High[t]) / EMA52High[t]) * 100`;
- `DistanceToEMA200HighPct[t] = ((Close[t] - EMA200High[t]) / EMA200High[t]) * 100`;
- breach logic must be evaluated on the same truncated `High`/`Close` history used for the current run;
- any breach-count field must state its exact lookback window in the field name or manifest entry.

Current baseline implementation rule:

- use the provider-truncated daily `High` series;
- use the same EMA convention as the rest of the engine's EMA family;
- do not reinterpret these fields as high-channel maxima or rolling local-peak trackers.

These rows are now approved for implementation on that basis.

## Scoring Manifest Schema

The scoring configuration must be externalized into a versioned declarative manifest.

Approved baseline filename:

```text
config/scoring_manifest.json
```

Approved required top-level schema:

```json
{
  "matrix_version": "V1.0",
  "manifest_version": "V1.0",
  "engine_version": "V3_Charter",
  "paths": {},
  "global_defaults": {},
  "indicator_rules": {},
  "classification_thresholds": {},
  "forced_rejections": {},
  "diagnostics": {},
  "metadata": {}
}
```

Approved schema intent:

- `matrix_version`: binds scoring behavior to the approved matrix revision;
- `manifest_version`: version of the manifest schema/content itself;
- `engine_version`: target charter/engine line this manifest belongs to;
- `paths`: per-path scoring blocks for `CROSSOVER`, `DIVERGENCE`, and `SETUP`;
- `global_defaults`: shared defaults such as rounding, tolerance, or generic fallback weights where explicitly approved;
- `indicator_rules`: indicator-level score rules, thresholds, bucket logic, and contextual overrides;
- `classification_thresholds`: `SELECTED`, `WATCH`, `REJECTED`, and any future signed-off class thresholds;
- `forced_rejections`: explicit path-specific hard-boundary rules such as `BULL_PULLBACK_REENTRY + BELOW_EMA200`;
- `diagnostics`: reason-code, score-component, and audit-output requirements;
- `metadata`: author/date/notes/approval state.

Approved schema rules:

- no scoring magic numbers may remain hidden in evaluator code once externalized here;
- sector/market/context overrides must appear declaratively here when approved;
- future schema changes must increment `manifest_version`;
- behaviorally material row/score changes must increment `matrix_version`;
- historical replay must load the manifest version explicitly requested by the regression run.

## Regression Dataset And Test-Matrix Repository

The permanent regression suite must use file-based, reviewable historical datasets and matching expectation maps.

Approved baseline storage root:

```text
tests/regression/
```

Approved baseline folder layout:

```text
tests/regression/
  datasets/
  manifests/
  matrices/
  snapshots/
  approvals/
```

Approved folder meanings:

- `datasets/`: historical ticker universes, date inputs, and reference run definitions;
- `manifests/`: version-pinned scoring manifests used by each regression run;
- `matrices/`: test-matrix mapping files that declare expected route/classification/score assertions;
- `snapshots/`: frozen third-party context payloads required for deterministic historical replay;
- `approvals/`: signoff notes, dataset ownership records, and approved baseline run summaries.

Approved approval workflow:

- any new regression dataset or matrix file must be added as a named artifact under `tests/regression/`;
- the artifact must declare its owner, purpose, covered paths, manifest version, and D/D+X horizon;
- changes to approved regression artifacts require explicit review before they replace an existing baseline;
- production engine changes must run against the approved regression set before merge;
- if a new dataset is exploratory only, it must not overwrite an approved baseline artifact until signed off.

## D-Date And D+X Validation

Historical replay is a mandatory correctness tool.

Definitions:

- `D` = analysis date
- `D+X` = forward validation horizon

Rules:

- classification uses only data available on or before D;
- D+X data must not influence initial classification;
- the same logical engine must run on historical D data;
- D+X validates what happened after the classified signal.

This supports:

- engine qualification;
- regression checking;
- matrix-change validation.

Backtesting is not a fourth strategy path. It is a permanent validation and regression module.

## Permanent Regression Suite

The `D` vs `D+X` engine is a permanent first-class automation suite.

It must not be treated as temporary scaffolding or a module to be decommissioned after launch.

Its job is to:

- validate new matrix rows before promotion;
- detect path drift after engine changes;
- confirm that historical classifications remain stable under approved logic;
- protect the charter from silent regression caused by score, threshold, or evidence rewiring.

## Regression Gate

No new indicator row, scoring rule, route rule, or path-selection logic may be merged into production until it passes the automated `D` vs `D+X` regression suite.

The gate condition is:

- zero unexpected drift in historical path classification on the approved regression dataset;
- zero route leakage into unselected families;
- zero lookahead contamination at `D`;
- only approved score-only tolerance drift where classification remains unchanged.

## Drift Tolerance

The regression suite must distinguish warning-level numeric drift from hard-failure behavioral drift.

Approved default interpretation:

- a small numeric `WeightedScore` deviation of `<= +/- 0.05` with no classification or priority change may be logged as a warning;
- any change that alters final classification, route, or forced-rejection status on day `D` must be treated as a hard regression failure;
- any change that introduces route leakage, D+X contamination, or different rejection reasons without signed-off intent must be treated as a hard regression failure.

## Test Matrix Mapping

The regression suite must read a separate file-based test mapping in addition to production logic.

Purpose:

- decouple regression assertions from active production code;
- allow new rows to be tested under development without rewriting live engine behavior;
- preserve stable historical expectation sets for approved engine versions.

## Manifest Version Compatibility

The scoring manifest and any future matrix-owned declarative schema must be versioned.

Requirements:

- the declarative score/matrix schema must carry a version attribute such as `matrix_version`;
- historical replay must be able to bind to the version of the manifest intended for that regression run;
- schema evolution must not silently reinterpret historical results under newer rules.

## Non-Goals

The engine is not intended for:

- automated trading;
- order execution;
- stop-loss trading logic;
- portfolio allocation;
- position sizing;
- portfolio management;
- silent universe expansion;
- default pan-USA screening;
- default sector-by-sector research;
- macro/regime expansion beyond bounded context rows;
- ad hoc threshold changes from one isolated observation.

## Regression Risks To Eliminate

The main failure mode is path leakage.

Known example:

- MACD already bullish above zero;
- stock is in continuation;
- engine incorrectly labels it `PRE_BULL_CROSSOVER`.

Other critical risks:

- divergence inferred from another family's failure;
- setup classified from crossover-style transition rules;
- context rows silently becoming route logic;
- future D+X data contaminating D classification;
- provider gaps misread as technical weakness.

## Consolidated Matrix Rules

The engine is governed by a stage-family indicator matrix.

### Matrix Shape

```text
Rows    = indicator families or evidence families
Columns = CROSSOVER, DIVERGENCE, SETUP
Cells   = exact path-specific condition logic or processing function
```

### Matrix Writing Rule

Use indicator families as rows.

Good:

- `MACD`
- `RSI`
- `EMA20`

Weak:

- `MACD(1D)` as a standalone row name

Reason:

the real meaning usually depends on a relation or condition, not on one naked value.

### Matrix Legend

- `Route`: helps decide whether a ticker belongs in that family.
- `Timing`: helps determine freshness, readiness, or staleness.
- `Quality`: strengthens or weakens confidence after route is known.
- `Context`: adds interpretation or risk context without deciding route by itself.
- `Scoring`: contributes to `WeightedScore` only after qualification.
- `Audit`: exists for explanation and visibility.
- `Validation`: belongs to D / D+X backtesting only.
- `Not used by default`: not part of default logic for that family.
- `TBD`: requires explicit signoff before implementation.

### Matrix Path Note

- `CROSSOVER` includes both `PRE_BULL_CROSSOVER` and `PRE_BEAR_CROSSOVER`.
- `PRE_BULL_CROSSOVER` is for early bull-phase entry.
- `PRE_BEAR_CROSSOVER` is for capital-preservation review on long-held equities.
- `DIVERGENCE` validates whether an opportunity may be developing.
- `SETUP` is a more tactical pure-play market-based entry path supported by TA confidence.

### SETUP Timeframe Default

`SETUP` uses a one-month candle baseline by default.

Reason:

- the `SETUP` family is intended for long-term equity accumulation and structural entry review;
- the monthly horizon reduces intra-week noise and minor corrective churn that would otherwise pollute higher-level setup interpretation.

Execution rule:

- the engine default for `SETUP` is a `1M` candle evaluation baseline;
- the pipeline may accept an explicit user override for controlled alternate validation sweeps, such as `1W`, but the default chartered behavior remains monthly.

## Consolidated Matrix

| Indicator Family / Evidence | API data required | V3 level | CROSSOVER | DIVERGENCE | SETUP | Backtesting / D+X | Primary outputs | Guardrail |
|---|---|---:|---|---|---|---|---|---|
| User CSV symbol | CSV row | L0 | Route input: supplied universe only. | Route input: supplied universe only. | Route input: supplied universe only. | Use same supplied CSV universe for historical run. | `Symbol`, `YahooSymbol`, source metadata | Supplied CSV is the universe; no hidden expansion. |
| User selected path | UI/input config | L0/L2 | Route input: only selected path can qualify candidates. | Route input: only selected path can qualify candidates. | Route input: only selected path can qualify candidates. | Execute the same selected path on D-date data. | `StageFamily`, selected family list | Only selected paths can produce final candidates. |
| D-date | UI/input config | L0/L5 | Context plus validation boundary for all D-date calculations. | Context plus validation boundary for all D-date calculations. | Context plus validation boundary for all D-date calculations. | Primary historical analysis date; API data sliced as of D. | `DDate`, data cutoff | D+X data must not enter classification. |
| D+X date / horizon | UI/input config | L5 | Validation only after D classification is complete. | Validation only after D classification is complete. | Validation only after D classification is complete. | Forward validation date/horizon after D. | `ForwardDays`, `DPlus{N}*` fields | D+X is validation only, never route evidence. |
| Provider historical pull | API provider | L0/L5 | Validation support for replaying the same provider-backed calculation stack. | Validation support for replaying the same provider-backed calculation stack. | Validation support for replaying the same provider-backed calculation stack. | Pull enough past data for D-date calculation plus forward data through D+X. | provider status, data errors | Same provider contract as live mode; provider gaps are reported. |
| D-date close price | API historical price | L0/L5 | Validation baseline price for D outcome. | Validation baseline price for D outcome. | Validation baseline price for D outcome. | Baseline price for D+X price check. | `DDateClose` | Must be price available on or before D. |
| D+X close price | API forward price | L5 | Validation-only forward close price. | Validation-only forward close price. | Validation-only forward close price. | Simple forward close comparison versus D. | `DPlus{N}ReturnPct` | Forward price is loaded after classification. |
| D+X high/low path | API forward high/low when available | L5 | Validation-only forward path extremes. | Validation-only forward path extremes. | Validation-only forward path extremes. | Optional best-high/worst-low validation. | `DPlus{N}WorstLowReturnPct`, `DPlus{N}BestHighReturnPct` | Path validation is separate from simple endpoint check. |
| Close series | API historical price | L1/L3 | Route and timing input for close-derived calculations. | Route and context input for close-derived calculations. | Route and quality input for close-derived calculations. | Use only rows <= D for indicator values. | close-derived indicators | Fetch through API per calculation; not a CSV requirement. |
| MACD | Close series for 1D baseline; lower-timeframe API data only when requested | L3/L4 | `MACD(1D) < Signal(1D)` with `Histogram(1D)` near zero for near-bull transition; `MACD(1D) > Signal(1D)` with bear-side inverse for near-bear transition; optional same-analysis-point `4H` and `1H` confirmation is approved here for the initial release only. | Price swing versus histogram swing disagreement; confirmation requires the expected histogram turn, not MACD alone; no default `4H`/`1H` layer in the initial release. | `MACD(1D) > Signal(1D)` / bull-phase continuation or re-entry logic; Setup-specific MACD baseline and historical phase behavior may refine quality; no default `4H`/`1H` layer in the initial release. | Recompute the same MACD condition stack as of D and validate against D+X movement. | `MACD_1D_*`, optional `MACD_4H_*`, `MACD_1H_*`, phase outputs | `MACD` is an indicator family row; path cells must hold exact relations, not vague labels. |
| MACD crossover distance / freshness | Close series; lower-timeframe API data only when requested | L3/L4/L5 | Distance and bars-since-cross decide near-transition readiness and freshness. | Audit/context only unless a specific divergence rule later uses freshness. | Audit/context only unless Setup maturity later uses it. | Compare fresh versus stale D conditions by D+X outcome. | `MACD_1D_CrossoverDistance`, bars-since-cross fields | Distance/freshness cannot override path boundary by itself. |
| MACD zero-line context | Close series | L3/L4/L5 | Zero-line side and nearness are context for transition quality; not the crossover itself. | Context only by default. | Context only by default. | Compare D zero-line context buckets with D+X outcome. | zero-line context outputs | Zero-line context is separate from crossover detection. |
| Historical MACD phase episodes / Setup baseline | Close series, V2-style lookback | L3/L4 | Probability/readiness aid only if explicitly approved. | Context/audit only by default. | Stock-specific bull/bear phase episodes, `MACD(8,21,5)` baseline where approved, maturity and percentile/history logic. | Validate whether D phase maturity/strength predicted D+X move. | `Momentum_Phase`, `Momentum_Strength`, maturity outputs | Use only inside SETUP unless another path explicitly signs it off. |
| RSI 1D | Close series | L3/L4 | Quality and context for recovery or weakening after crossover conditions are already known. | Route support plus quality for momentum disagreement. | Quality and scoring input for setup headroom. | Store D RSI and compare outcome buckets by D+X. | `RSI_1D`, `RSIScore` | RSI is not a global hard gate. |
| RSI upper boundary | RSI 1D plus manifest-owned threshold object | L4 | Not used by default; optional context only if specifically approved. | Context only by default. | Scoring and quality input for remaining headroom below the configured upper boundary; baseline `default = 80.0` from manifest object, with future override hooks preserved but disabled by default. | Validate headroom buckets against D+X. | `RSIHeadroom`, `RSIScore` | Distance to the upper boundary can affect confidence, not route. |
| ADX 1D | API price series as required | L3/L4 | Quality and context for trend expansion support. | Context for whether divergence has enough trend strength to matter. | Quality and scoring input for setup trend confidence. | Validate ADX bucket contribution by D+X. | `ADX_1D`, `ADX_State`, `ADXScore` | Low ADX should not automatically suppress early valid setups. |
| PlusDI / MinusDI | API price series as required | L3/L4 | Quality input for buyer versus seller participation after crossover conditions are known. | Context for directional participation around divergence. | Quality input for participation strength during continuation or re-entry. | Validate D directional participation against D+X. | `PlusDI_1D`, `MinusDI_1D` | Directional participation only after path route is known. |
| EMA20 | Close series | L3/L4 | Timing and quality input for reclaim, hold, or loss around transition. | Context for short-structure support or resistance. | Route and quality input for pullback re-entry or continuation. | Validate D EMA20 relation against D+X. | `EMA20`, `EMA20_Above`, `EMA20_Below` | EMA20 meaning is path-specific. |
| EMA20 reclaim | Close series | L3/L4 | Timing input for a possible bull transition. | Context only by default. | Route input for pullback re-entry. | Validate D reclaim setups by D+X. | `EMA20_Reclaim` | Must not relabel continuation as crossover. |
| EMA20 rejection | Close series | L3/L4 | Context and risk flag around failed reclaim. | Quality and timing signal for bear-side weakening only if divergence logic uses it. | Context and risk flag for setup weakness. | Validate rejection rows by D+X. | `EMA20_Rejection` | Use as context unless path defines it as route. |
| EMA50 | Close series | L3/L4 | Quality and context for broader trend stack support. | Context only by default. | Quality and scoring input for broader trend stack support. | Validate trend-stack buckets by D+X. | `EMA50` | Not a universal gate. |
| EMA200 | Close series | L3/L4 | Context, risk, and headroom signal; not a route trigger. | Context for major support or resistance. | Quality and context input for risk, headroom, and long-trend support. | Validate above/below EMA200 rows by D+X. | `EMA200`, `BelowEMA200` | Stage-specific evidence, not globally true gate. |
| Distance to EMA200 percent | Close series | L3/L4 | Context and scoring aid for how stretched price is versus EMA200. | Context and scoring aid only. | Quality and scoring aid for extension or headroom versus EMA200. | Validate distance buckets by D+X. | `DistanceToEMA200Pct` | Can affect score/risk only after route. |
| EMA200 slope | Close series | L3/L4 | Context and scoring aid for long-trend direction. | Context and scoring aid only. | Quality and scoring aid for long-trend direction. | Validate slope buckets by D+X. | `EMA200SlopeState` | Slope cannot create a candidate by itself. |
| Lifetime high | API long-range/lifetime history when requested | L3/L4 | Context and scoring aid only; never a base route trigger. | Context for major boundary support or resistance. | Quality and scoring input for headroom and extension risk. | Validate D boundary location by D+X. | `LifetimeHigh` | Request only when boundary analysis is selected/needed. |
| Distance to lifetime high percent | API long-range/lifetime history when requested | L4 | Context and scoring aid only. | Context and scoring aid only. | Quality and scoring aid for remaining headroom. | Validate headroom buckets by D+X. | `DistanceToLifetimeHighPct` | Bottom-level confidence aid only. |
| Lifetime high break count | API long-range/lifetime history when requested | L4/L5 | Audit plus context on prior breakout behavior. | Audit plus context on prior breakout behavior. | Quality, scoring, and audit input on prior breakout behavior. | Validate breakout history buckets by D+X. | `LifetimeHighBreakCount` | Does not override route. |
| EMA52 high / distance | API history where supported | L4 | Context and scoring aid once the exact V2 meaning is confirmed. | Context and scoring aid once the exact V2 meaning is confirmed. | Quality and scoring aid once the exact V2 meaning is confirmed. | Validate only after exact definition confirmed. | `EMA52High`, `DistanceToEMA52HighPct` | Confirm definition before coding. |
| EMA200 high / distance | API history where supported | L4 | Context and scoring aid once the exact V2 meaning is confirmed. | Context and scoring aid once the exact V2 meaning is confirmed. | Quality and scoring aid once the exact V2 meaning is confirmed. | Validate only after exact V2 meaning confirmed. | `EMA200High`, `DistanceToEMA200HighPct` | Confirm exact V2 meaning before coding. |
| One-month candle behavior | API monthly candles when requested | L3/L4 | Context and quality input from the monthly candle when explicitly requested. | Context and quality input from the monthly candle when explicitly requested. | Quality and scoring input from the monthly candle when explicitly requested. | Validate D monthly context against D+X. | monthly candle fields | Bounded context only; no broad scan. |
| Daily candle close location | API OHLC only when requested/available | L3/L4 | Quality input for candle acceptance near the close. | Context and quality input for candle acceptance. | Quality input for candle acceptance. | Validate acceptance buckets by D+X. | `DailyCloseLocationPct` | Not required for MACD baseline. |
| Daily range vs 20-day average | API OHLC only when requested/available | L3/L4 | Context and quality input for volatility versus normal range. | Context and quality input for volatility versus normal range. | Context and quality input for volatility versus normal range. | Validate volatility buckets by D+X. | `DailyRangeVs20Avg` | Quality/context only. |
| Higher low 5D | API lows only when requested/available | L3/L4 | Quality input for supportive short structure. | Route support plus quality input for bullish geometry. | Route support plus quality input for pullback structure. | Validate D structure by D+X. | `HigherLow_5D` | Geometry meaning differs by path. |
| Lower high 5D | API highs only when requested/available | L3/L4 | Context and risk flag for weaker short structure. | Route support plus quality input for bearish geometry. | Context and risk flag for weaker short structure. | Validate D structure by D+X. | `LowerHigh_5D` | Do not use as universal bearish override. |
| Range breakout up 20D | API highs/closes | L3/L4 | Quality and context input for breakout strength. | Context only by default. | Quality input for continuation strength. | Validate breakout rows by D+X. | `RangeBreakoutUp_20D` | Quality/context unless path says route. |
| Range breakdown down 20D | API lows/closes | L3/L4 | Context and risk flag for breakdown pressure. | Context plus quality input for bearish follow-through. | Context and risk flag for weakness. | Validate breakdown rows by D+X. | `RangeBreakdownDown_20D` | Do not suppress raw divergence silently. |
| Distance to 20D high | API highs/closes | L3/L4 | Context and scoring aid for nearby short-term resistance. | Context and scoring aid only. | Quality and scoring aid for headroom to recent highs. | Validate headroom buckets by D+X. | `DistanceTo20DHighPct` | Score aid only unless path contract changes. |
| Distance to 60D high | API highs/closes | L3/L4 | Context and scoring aid for nearby medium-term resistance. | Context and scoring aid only. | Quality and scoring aid for headroom to recent highs. | Validate headroom buckets by D+X. | `DistanceTo60DHighPct` | Score aid only. |
| Bollinger percent-b | API Close | L3/L4 | Quality and context input for recovery, compression, or stretch. | Context and quality input for confirmation or exhaustion. | Context and quality input for extension risk. | Validate Bollinger buckets by D+X. | `Bollinger_PctB`, `Bollinger_Position` | No global Bollinger gate. |
| Bollinger bandwidth | API Close | L3/L4 | Context and quality input for compression or expansion. | Context and quality input for compression or expansion. | Context and quality input for compression or expansion. | Validate compression/expansion buckets by D+X. | `Bollinger_BandwidthPct` | Context only unless later scoped. |
| Volume latest | API volume when requested/available | L3/L4 | Quality and context input for participation on the signal candle. | Context and quality input for participation on the signal candle. | Quality and context input for participation on the signal candle. | Validate D volume support by D+X. | `VolumeLatest` | Optional confirmation, not MACD baseline input. |
| Volume 20 average | API volume when requested/available | L3/L4 | Quality and context input for normal participation baseline. | Context and quality input for normal participation baseline. | Quality and context input for normal participation baseline. | Validate relative volume support by D+X. | `Volume20Avg` | Missing volume should be auditable, not silently fatal. |
| Relative volume / intraday volume vs 20 avg | API volume when requested/available | L3/L4 | Quality input for above-normal participation. | Context and quality input for above-normal participation. | Quality input for above-normal participation. | Validate participation buckets by D+X. | `IntradayVolumeVs20Avg` | Not a base path selector. |
| CMF | API OHLCV when requested/available | L3/L4 | Quality and context input for accumulation or distribution during pre-bull or pre-bear transition review. | Context and quality input for whether divergence is supported by money-flow behavior. | Quality and scoring input for continuation participation and accumulation support. | Validate CMF buckets by D+X. | `CMF_20` | Money-flow support only; cannot define the route by itself. |
| OBV | API close and volume when requested/available | L3/L4 | Quality and context input for whether volume flow is confirming pre-bull or pre-bear crossover direction. | Context and quality input for whether volume flow confirms or weakens the divergence reading. | Quality and scoring input for continuation or re-entry participation strength. | Validate OBV state and slope buckets by D+X. | `OBV_Slope_5`, `OBV_State` | Volume-flow support only; not a standalone stage trigger. |
| Efficiency ratio | API close series | L3/L4 | Quality and timing input for whether the transition is clean versus noisy. | Context and quality input for whether the swing structure is efficient or choppy. | Quality and scoring input for trend cleanliness during setup continuation or re-entry. | Validate efficiency buckets by D+X. | `EfficiencyRatio_10`, `DirectionalEfficiencyRatio_10`, `EfficiencyRatio_14`, `DirectionalEfficiencyRatio_14` | Trend-efficiency evidence cannot replace route logic. |
| Relative strength / benchmark relative performance | API symbol history plus benchmark history when requested/configured | L3/L4 | Context and quality input for whether the ticker is outperforming or underperforming its benchmark during transition review. | Context and quality input for whether the divergence is happening with supportive or weak relative performance. | Quality and scoring input for whether the setup is backed by relative outperformance. | Validate relative-strength buckets by D+X. | `RelativeReturn20DPct`, `RelativeReturn60DPct`, `RelativeTrendState`, `BenchmarkSymbol`, `BenchmarkReturn20DPct`, `BenchmarkReturn60DPct`, `BenchmarkRelativeReturn20DPct`, `BenchmarkRelativeReturn60DPct`, `BenchmarkRelativeTrendState` | Relative strength is supporting evidence only unless a later matrix rule explicitly promotes it. |
| Down volume pressure | API OHLCV when requested/available | L3/L4 | Context and risk flag for whether selling pressure is still heavy during bull-transition review, or supportive during bear-transition review. | Context and risk flag for whether selling pressure is contradicting or supporting the divergence case. | Context and risk flag for whether setup continuation still faces distribution pressure. | Validate down-pressure buckets by D+X. | `DownVolumePressure` | Pressure tagging should influence review quality, not silently kill valid path logic. |
| Failed high / ceiling structure | API highs, closes, and boundary history when requested/available | L3/L4 | Context and risk input for overhead resistance that may weaken a pre-bull transition, or confirm a pre-bear rollover. | Context and quality input for whether price is repeatedly failing near resistance during divergence formation. | Context, quality, and scoring input for extension risk or ceiling pressure in setup candidates. | Validate ceiling and failed-high buckets by D+X. | `FailedHighCount20D`, `CeilingPattern` | Ceiling structure is boundary evidence, not a standalone route selector. |
| Average daily volume metadata | CSV metadata/API profile cache | L0/L4 | Context input for liquidity suitability. | Context input for liquidity suitability. | Context input for liquidity suitability. | Validate liquidity risk buckets by D+X when metadata is available. | `AvgDailyVolume` | Metadata/context; do not require live profile calls in hot path. |
| Average monthly volume metadata | CSV metadata/API profile cache | L0/L4 | Context input for liquidity suitability. | Context input for liquidity suitability. | Context input for liquidity suitability. | Validate liquidity risk buckets by D+X when metadata is available. | `AvgMonthlyVolume` | Preserve if supplied. |
| Low liquidity tag | volume/profile metadata | L4/L5 | Context and risk flag for low tradability. | Context and risk flag for low tradability. | Context and risk flag for low tradability. | Validate low-liquidity rows by D+X separately. | `LowLiquidity`, risk tags | Risk/review priority, not hidden rejection unless scoped. |
| PriceBand | API price series and long-term moving-average boundary context | L3/L4 | Context and scoring aid for whether price is already too stretched for a fresh pre-bull entry or has materially broken support for a pre-bear review. | Context only by default unless a later divergence rule signs off a stronger use. | Quality and scoring aid for whether the candidate is entering too far above its long-term support bands for a prudent fresh entry. | Validate PriceBand buckets against D+X after the same long-term boundary logic is applied on D. | `PriceBandState`, band-distance fields, score deductions where approved | PriceBand is a long-term support and extension verifier, not a swing-target or sell-trigger module. |
| Market regime | API benchmark data when requested/configured | L5 | Audit/context metadata only with `Weight = 0` in the active scoring pipeline. | Audit/context metadata only with `Weight = 0` in the active scoring pipeline. | Audit/context metadata only with `Weight = 0` in the active scoring pipeline. | Validate as bounded audit metadata, not base route. | `MarketRegime` | Bounded context only; no universe expansion and no default score contribution. |
| Sector context/regime | CSV sector + API benchmark only when requested/configured | L5 | Audit/context metadata only with `Weight = 0` in the active scoring pipeline. | Audit/context metadata only with `Weight = 0` in the active scoring pipeline. | Audit/context metadata only with `Weight = 0` in the active scoring pipeline. | Validate as bounded audit metadata for supplied CSV only. | `SectorRegime` | No sector calibration project by default and no default score contribution. |
| Sector relative strength | API benchmark and symbol data | L3/L4 | TBD, with context-only use if later approved. | TBD, with context-only use if later approved. | Quality and context input when explicitly requested and defined. | No backtest until exact formula is defined. | TBD | Future bounded evidence, not broad scan. |
| AI / sentiment (`GetAI`) | External API/future provider | L3/L4 | TBD future context row only after provider, timestamp, and no-lookahead rules are defined. | TBD future context row only after provider, timestamp, and no-lookahead rules are defined. | TBD future context row only after provider, timestamp, and no-lookahead rules are defined. | No backtest until provider, timestamp, and no-lookahead rules are defined. | TBD | Future optional evidence only after core engine is stable. |
| Reason codes | evaluator output | L4/L5 | Audit output for why the ticker passed or failed Crossover. | Audit output for why the ticker passed or failed Divergence. | Audit output for why the ticker passed or failed Setup. | Required to explain D classification before D+X validation. | `ReasonCodes`, path reason fields | No failed check disappears silently. |
| WeightedScore | L4 scoring components | L4/L5 | Scoring output after the ticker already qualifies for Crossover. | Scoring output after the ticker already qualifies for Divergence. | Scoring output after the ticker already qualifies for Setup. | Validate score buckets against D+X outcome. | `WeightedScore`, component scores | Never a global promotion gate or route selector. |

## Immediate Approved Direction

From the current approved design:

- `PRE_BULL_CROSSOVER` and `PRE_BEAR_CROSSOVER` are both critical.
- `PRE_BEAR_CROSSOVER` is for capital-preservation review, not stop-loss automation.
- `DIVERGENCE` is opportunity validation.
- `SETUP` is a more tactical pure-play market-based entry path.
- `StopLoss` is out of scope and intentionally excluded.
- `AI` may exist later only as a bounded matrix-owned evidence row.

## Current Outstanding Review Items

These are still open for signoff before hardcoding behavior:

- exact future sector-override and EPS-factor expansion rules for the `rsi_upper_bound` object once overrides are enabled;

## Restart Instruction

For a new session, read this file first, then verify:

```powershell
cd D:\Tools\Stock_Screener_V3
git status --short --branch
git log --oneline --decorate -8
```

Then read:

```text
docs/handover/current_session_handover.md
```

Continue only with work that aligns to this consolidated charter unless the user explicitly changes direction.
