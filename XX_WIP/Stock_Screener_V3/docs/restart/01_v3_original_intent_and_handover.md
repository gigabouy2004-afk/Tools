# Stock Screener V3_Charter Original Intent And Handover

Last updated: 2026-06-13

Repo: `D:\Tools\Stock_Screener_V3`

Branch: `V3_Charter`

## Document Authority

This document is the canonical seed and source of truth for `V3_Charter`.

The top-level purpose, user workflow, allowed analysis paths, V2 level architecture, data method, backtesting requirement, and non-goals in this document must not be changed by a future session without explicit user approval.

Future sessions may add implementation status, UI details, test status, and granular next steps, but they must not change the original direction recorded here.

Every new session must read this document before reading validation notes, calibration runs, handover summaries, or recent commits.

## Original Intent

`V3_Charter` is a CSV-based, user-directed stock analysis engine.

The purpose of `V3_Charter` is to use V2 as a reference library for technical-analysis indicator processing while rebuilding selection, routing, scoring, and validation into a single cohesive structure that avoids the logical regressions that appeared when separate paths were merged.

`V3_Charter` is not a new broad market research project. It is not a pan-USA screening engine unless the user supplies a pan-USA CSV and explicitly asks for that processing. It is not a sector, regime, or macro calibration project by default.

The engine must process stocks from a user-provided CSV and produce analysis only for the user-selected processing path or paths.

Only processing logic explicitly confirmed by the user should be carried forward. That includes V2 indicator calculations, reusable utilities, and confirmed evidence concepts, not every artifact produced during prior drift.

## Single Engine Construction Contract

`V3_Charter` must be constructed as one cohesive engine, not as separate stitched scripts and not as independent strategy modules that override each other.

The engine's base flow is:

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

Every addition from V2 must enter the engine at the correct level. V2 is a reference library for indicator calculation and tuned variable/threshold processing. No V2 detail may bypass the user-selected path, change the base route, or override another signal path.

The key construction rule is:

```text
V2 additions can refine confidence, risk, explanation, or score only inside the selected path trajectory.
They must not become base-level drivers.
```

Examples:

- EMA200 can aid Momentum confidence/risk for `BULL_PULLBACK_REENTRY`; it must not globally suppress all Momentum or force Crossover.
- Lifetime high or EMA lifetime-high percentage can aid Momentum headroom/extension scoring; it must not become a base route selector.
- RSI and current price context can support WeightedScore; they must not relabel a continuation as `PRE_BULL_CROSSOVER`.
- Sector context can aid confidence when requested; it must not trigger a sector scan or cross-sector calibration run.
- Market regime can provide bounded context; it must not expand the supplied CSV universe or become a fourth path.

If a calculation is added, the implementer must answer these before coding:

1. Which user-selected path does it support?
2. Which level owns it: L1 fact, L2 route, L3 evidence, L4 score, or L5 validation?
3. Can it change the path, or only refine score/risk/explanation?
4. What data does it request from the API?
5. What test proves it cannot override another path?

## Stage-Family Indicator Matrix Requirement

The engine must be designed from a stage-family indicator matrix.

The V2 design described a two-axis route/indicator model. The current repository still contains the active equivalent:

```text
docs/architecture/v3_evidence_stage_matrix.md
```

The editable working matrix for engine construction is:

```text
docs/architecture/v3_stage_family_indicator_working_matrix.md
```

These documents are grounded in the V2 route/indicator hierarchy and must be reused, not rediscovered.

The required matrix shape for construction is:

```text
Rows    = Indicator families or evidence families
Columns = selected stage families / stage gates / candidate trajectories
Cells   = the exact processing condition/function used by that indicator family inside that path
```

Allowed stage-family columns:

- `CROSSOVER`
- `DIVERGENCE`
- `SETUP`

Each matrix row must define:

- indicator/evidence name
- API data required
- calculation level: L1, L2, L3, L4, or L5
- input fields
- output fields
- path-specific processing function or condition set
- whether it can affect route, timing, quality, confidence score, risk, audit, or backtest only
- anti-leakage rule proving it cannot override another path

Examples:

| Indicator / evidence | Crossover | Divergence | Setup |
|---|---|---|---|
| MACD | Example: `MACD(1D) < Signal(1D)` and `Histogram(1D)` near zero for near-bull transition, with 4H/1H alignment only if the path requests it. | Example: price swing versus MACD/histogram swing disagreement plus confirmation turn. | Example: MACD already positive / above signal, using Setup-specific baseline and bull-phase continuation logic. |
| RSI | Quality/readiness condition only after route is known. | Disagreement/exhaustion support condition. | Headroom / pullback-quality / continuation-strength condition. |
| EMA stack | Reclaim / break / transition context. | Support / resistance context. | Pullback / re-entry / continuation / extension context. |
| Volume | Participation confirmation after route is known. | Participation confirmation after route is known. | Pullback / continuation participation and abnormal-risk checks. |
| Market / sector context | Bounded context only when requested. | Bounded context only when requested. | Bounded context only when requested. |

This matrix is the main mechanism that prevents isolated implementation from breaking the engine. No indicator should be added directly to code until its row/cell meaning is documented.

Important precision rule:

```text
Do not write loose matrix rows such as "MACD(1D)" when the real logic depends on a relation or condition.
Use the indicator family as the row name, such as "MACD", and write the exact condition or processing function inside each stage-family cell.
```

The working matrix also contains a `Backtesting / D+X` column. That column records how each item is validated when the user supplies a historical D-date and a D+X horizon/date. Backtesting runs the same selected path logic on D-date data first, then loads D+X price data only for validation.

The matrix can be refined over time, but the rule is fixed:

```text
An indicator belongs to a path only through an explicit matrix cell.
No indicator is globally meaningful across all paths by default.
```

## User Workflow Contract

The user workflow is fixed:

1. User provides a CSV file containing stock symbols or stock rows.
2. User selects the required analysis path or paths.
3. User provides the analysis date context where required.
4. Engine processes each stock through the structured engine pipeline.
5. Engine produces candidate output, reason codes, diagnostics, rejection logging, and backtest/self-validation where applicable.

The only allowed user-facing analysis options are:

- `CROSSOVER`
- `DIVERGENCE`
- `SETUP`

No hidden fourth path should be added. No sector, market-regime, ETF, or universe-expansion path should be treated as part of the core engine unless the user explicitly requests that as a separate feature.

Market regime, EMA200, future-price processing, backtesting utilities, and future AI/sentiment analysis may be incorporated only as supporting evidence or validation components inside the CSV-driven engine. They must not replace the three-path workflow or create broad sector/universe calibration work.

Filter qualification is a first-class engine input. The engine must support user-selected ticker universes, user-selected stage families, and user-selected qualifying filters such as market cap, average volume, or similar metadata-based constraints. Only tickers that satisfy the selected stage or stage combination and the selected filters should be shown as candidates.

Tickers that do not satisfy the selected stage or filters are not user-facing candidates. They must be discarded from the visible candidate list and logged in the processing output with the exact reason for failure and the relevant indicator/value that caused rejection.

`STATUS_QUO` is not part of the intended user-facing engine output for this selection engine.

## Three Analysis Paths

### Crossover

Crossover is for phase-transition analysis. It identifies setup conditions around bullish or bearish crossover events.

Functional meaning:

- `PRE_BULL_CROSSOVER`: identify an entry early enough to maximize the natural bull phase of the stock.
- `PRE_BEAR_CROSSOVER`: identify weakening early enough to support capital preservation and avoid future notional loss on an existing long-held equity.

Valid examples:

- `PRE_BULL_CROSSOVER`
- `PRE_BEAR_CROSSOVER`
- confirmed bullish crossover
- confirmed bearish crossover

Crossover must not classify an already-extended bull continuation as `PRE_BULL_CROSSOVER`.

If MACD is already above the zero line and the evidence describes continuation or re-entry, the engine must route the stock to Setup logic, not Crossover transition logic.

Crossover may use bounded MACD-history aids from V2:

- MACD line, signal line, and histogram.
- MACD/signal crossover state.
- histogram improvement or deterioration near crossover.
- minimum histogram/spread only to confirm the cross is real and non-flat.
- bars since MACD/signal crossover.
- bars since MACD zero-line cross.
- historical histogram phase/episode behavior as a probability or confidence aid for near-crossover readiness.

These aids can support Crossover confidence or readiness. They must not become a universal histogram threshold and must not relabel Momentum continuation as Crossover.

### Divergence

Divergence is for price-versus-indicator disagreement.

Functional meaning:

- validate whether a credible investment opportunity may be developing through technical disagreement between price behavior and momentum behavior.

It must remain independent from Crossover and Setup logic. A divergence candidate must be identified through divergence-specific evidence, not through side effects of crossover or setup rules.

The divergence path must preserve the V2 intent of finding meaningful bullish or bearish disagreement and then validating whether the signal had forward price behavior.

### Setup

Setup is for bull-phase continuation, re-entry, pullback recovery, and extension behavior.

Functional meaning:

- a pure-play market-based entry path where technical-analysis indicators provide the confidence/support for entering a new position;
- the resulting position may be more temporary than a Pre-Bull entry because the current bull phase may later peak and rotate toward bear-side pressure.

This path handles stocks where the trend or MACD structure is already in a bullish continuation state. It is not the same as a fresh bullish crossover transition.

Examples of this path include:

- pullback re-entry
- bull extension
- continuation after MACD is already positive
- setups where price movement is expected after an already-established bullish structure

Setup may use bounded context checks when the user asks for them. Examples:

- sector information for the supplied stock or supplied CSV universe
- stock behavior in one-month candles
- lifetime high and lifetime low checks
- boundary analysis against prior major highs/lows
- market-regime context as supporting evidence

These checks are valid only as supporting context for the selected Setup analysis. They must not trigger a broad sector scan, cross-sector calibration project, or extra analysis path.

## V2 Level Architecture To Preserve

`V3_Charter` must retain the path-first V2 architecture and make it stricter.

The V2 artifacts describe the core model as:

```text
L1 baseline -> L2 stage router -> L3 indicator functions
```

`V3_Charter` should extend this into a complete implementation pipeline without changing that core meaning:

### L0 Input, Data, And Date Preparation

L0 prepares the run before analysis starts.

Responsibilities:

- load user CSV
- normalize symbols
- validate required columns
- resolve exchange/provider symbol format
- prepare D-date analysis context
- fetch required historical data through the configured API/provider
- enforce no-lookahead data slicing for production classification
- record provider/data failures per symbol

### L1 Baseline

L1 establishes the stock's current technical state before any final stage classification.

Responsibilities:

- determine current trend state
- determine current MACD state
- determine moving-average context
- determine price structure and volume context where needed
- produce neutral baseline facts

L1 is not the final stage. It only establishes the current technical condition and gives L2 enough information to route safely.

L1 may include neutral facts such as MACD state, RSI, price versus selected moving averages, and other facts needed by the selected run. L1 must not use detail aids such as lifetime high distance or EMA lifetime-high percentage as route decisions unless the canonical path contract is explicitly updated by the user.

### L2 Stage Router

L2 chooses the eligible path based on:

- user-selected analysis option
- L1 baseline state
- hard path boundaries

L2 must prevent path leakage.

Examples:

- a continuation state must not be routed as a fresh crossover transition
- divergence logic must not run because crossover logic failed
- setup continuation must not be mixed with pre-crossover classification

### L3 Indicator And Evidence Functions

L3 calculates detailed evidence only for the path requested by L2.

Responsibilities:

- calculate indicators on demand
- return raw values and derived evidence
- avoid global indicator interpretation before the path is chosen
- keep Crossover, Divergence, and Setup evidence independent

V2 additions such as EMA200, lifetime high, EMA lifetime-high percentage, one-month candles, volume confirmation, and sector context belong here when they are evidence for a selected path. They do not belong at the base level as universal gates.

### L4 Classification And Scoring

L4 converts routed evidence into the final candidate class.

Responsibilities:

- apply path-specific thresholds
- assign candidate class
- assign confidence or priority
- produce reason codes
- reject logically inconsistent candidates

WeightedScore belongs in L4 as a confidence/detailing layer after route and path eligibility are known. It must not be used as a global promotion gate or as a substitute for path-specific classification.

For example, in Setup:

- current RSI may contribute to quality/headroom
- current price distance versus lifetime high may contribute to headroom
- price distance versus EMA200 or EMA lifetime-high style datapoints may contribute to risk/headroom
- these values can improve or reduce confidence score
- these values must not change the path into Crossover or Divergence

WeightedScore applies only after stage qualification. It is an individual candidate score derived from multiple values inside the selected stage and its active matrix rows. It must not be used before stage qualification and must not be used as a substitute for stage selection.

WeightedScore is computed per ticker, not once per stage family. The selected stage family determines the scoring formula, active matrix rows, and interpretation rules for that ticker.

This means two tickers can both score `81` while still belonging to different qualified stage families. For example:

- ticker `T1` may qualify as `PRE_BULL_CROSSOVER` with score `81`
- ticker `T2` may qualify as `SETUP` with score `81`

Those scores are valid inside their own category logic. They must be displayed under their respective stage-family groups rather than treated as a single flat ranking pool by default.

### L5 Output, Audit, And Backtest

L5 writes user-facing and developer-facing evidence.

Responsibilities:

- output CSV results
- output summary markdown/logs where required
- include L0/L1/L2/L3/L4 diagnostics
- perform D+X forward validation where requested or required
- preserve enough audit detail to debug why a symbol was classified or rejected

## API And Data Provider Method

The engine must use a provider abstraction rather than letting provider behavior leak into strategy logic.

Current implementation work has used a Yahoo/yfinance-style provider wrapper in the repository. That is an implementation detail, not the product identity of `V3_Charter`.

The current default free backend is Yahoo Finance through `yfinance`, but the engine must keep a swappable provider abstraction so another free backend can replace it later without changing matrix logic, evaluator meaning, or output contracts.

The required method is API-based. For any calculation, the engine must request the required data from the configured market-data API/provider for the supplied CSV symbols.

The provider contract is calculation-specific:

- fetch enough historical data for the selected path and requested supporting evidence
- preserve the V2-style default historical window where applicable, including the current two-year style provider pull used by the implementation
- fetch Close series for V2-style MACD/Momentum baseline calculations
- fetch High/Low/Open/Volume only when a selected evidence calculation requires those fields
- fetch lifetime or long-range history only when lifetime high/low, EMA lifetime-high percentage, or major-boundary analysis is requested
- fetch forward price data for D+X self-backtesting
- deterministic slicing so classification uses only data available as of D
- per-symbol failure handling
- clear handling for missing dates, holidays, suspended symbols, provider gaps, and insufficient bars
- cache or reuse behavior that does not change analysis semantics
- rate-limit and provider-error reporting

`V3_Charter` must not assume OHLCV as the universal input contract. V2's MACD/Setup baseline required a Close price series; Volume was optional confirmation, and OHLC fields were not required for that baseline. `V3_Charter` should request only the fields needed by the selected path and requested evidence modules.

If a future TradingView API or another market-data API is used, it must be integrated behind this provider contract. The analysis engine should not be rewritten around the provider.

Live mode and historical/backtest mode must use the same logical data contract. The only difference should be the date window and whether forward D+X bars are available for validation.

## Confirmed Processing Components To Carry Forward

The following items may be carried forward because they are processing capabilities or evidence concepts aligned with the original engine intent:

- CSV input handling and symbol normalization.
- D-date processing.
- D+X future-price processing.
- backtesting/self-validation utility.
- no-lookahead historical slicing.
- API-based data retrieval for each required calculation.
- V2-style two-year historical pull where applicable.
- EMA200 as a risk/evidence component where it supports the selected analysis path.
- market regime as bounded contextual evidence, not as a separate screening project.
- sector information as bounded context for the supplied stock/CSV when the user asks for it.
- one-month candle behavior as bounded path evidence.
- lifetime high/low, EMA lifetime-high percentage, and major-boundary checks as bounded path evidence.
- future AI/sentiment analysis as an optional evidence module, only as another matrix-owned row after the core three-path engine is stable.

These components must stay subordinate to the core workflow:

```text
CSV input -> selected path -> L0/L1/L2/L3/L4/L5 processing -> D+X validation
```

They must not introduce additional user-facing analysis paths.

## V2 Reuse Map

The following V2 design and analysis artifacts are to be reused directly as references. They should prevent a new rediscovery phase.

### Core Engine Model

Source:

- `docs/archive_unified_stock_scanner_engine_design.md`
- `docs/archive_unified_engine_recap_and_action_plan_2026-05-24.md`
- `docs/architecture/v3_evidence_stage_matrix.md`
- `docs/architecture/v3_stage_family_indicator_working_matrix.md`

Reuse:

- path-first engine model
- L1 baseline before route
- L2 stage router honoring user-selected families
- L3 on-demand indicator/evidence functions
- no global calculation of every indicator/timeframe before route
- audit fields showing baseline, route, and functions called
- stage-family indicator/evidence matrix with rows as evidence and columns as stage-family meanings
- editable working matrix for adding, subtracting, and modifying individual V2/V3 indicator rows before coding

### Setup / MACD Baseline

Source:

- `docs/archive_unified_stock_scanner_engine_design.md`
- `docs/archive_unified_engine_recap_and_action_plan_2026-05-24.md`

Reuse:

- Setup-specific MACD baseline is based on Close series
- default Setup MACD reference: `MACD(8,21,5)`
- compare current MACD phase against stock-specific history where applicable
- Volume is optional confirmation, not part of the baseline MACD calculation
- OHLC fields are not required for the MACD baseline
- Setup methodology applies only to Setup; it must not change Crossover or Divergence rules

### Crossover Boundaries

Source:

- `docs/archive_unified_stock_scanner_engine_design.md`
- `docs/architecture/v3_evidence_stage_matrix.md`
- `docs/analysis/current_engine_gap_analysis_against_fresh_charter_2026-06-01.md`

Reuse:

- Crossover is a transition event or near-transition state
- already bullish or already bearish continuation must not be classified as Crossover
- MACD zero-line context is confirmation/context, not a reason to relabel continuation
- `PRE_BULL_CROSSOVER` must not be produced for an already above-zero bull continuation
- historical MACD histogram behavior may support crossover probability/readiness scoring
- histogram should confirm that a cross is real/non-flat, not act as a universal `> 0.5` gate

### Divergence Boundaries

Source:

- `docs/architecture/v3_divergence_contract.md`
- `docs/archive_unified_stock_scanner_engine_design.md`

Reuse:

- Divergence is price versus indicator disagreement
- Divergence must not be inferred from Crossover failure or Momentum continuation
- EMA200, RSI, volume, and candle acceptance are context/quality unless explicitly defined inside Divergence rules

### Output And UI Parity

Source:

- `docs/architecture/v2_operational_parity_contract.md`

Reuse:

- V2-style explainability
- CSV-friendly fields
- reason codes
- visible route/state diagnostics
- user-facing controls that map to actual engine capability

### Do Not Reuse As Direction

The following should not drive engine construction:

- broad sector-folder validation as product direction
- cross-sector calibration reports as base rules
- current market/sector/regime calibration artifacts as accepted scope
- old WeightedScore as a promotion gate
- any rule that was created from one isolated slice without path-specific validation

These artifacts may be read only to understand mistakes, candidate failure modes, or potential bottom-level evidence ideas.

## V2 Design Intent Validation Matrix

This matrix consolidates the individual V2 intents that must be preserved in V3. Each intent is valid only at its proper hierarchy level. The past failure mode was implementing these ideas in isolation, causing path leakage, global gates, or incorrect overrides.

### Input And User Control

| V2 intent | Source pointer | V3 level | Carry-forward rule | Anti-regression guardrail |
|---|---|---|---|---|
| User supplies the universe through CSV/manual symbols. | `archive_unified_stock_scanner_engine_design.md` lines 7, 63-71; `archive_unified_engine_recap_and_action_plan_2026-05-24.md` lines 13, 27 | L0 | CSV/manual input defines the universe. | Do not expand to pan-USA, sector folders, or broad markets unless user supplied that universe. |
| User selects stage families. | design lines 65, 108-116, 232; recap lines 77-85, 128 | L0/L2 | Only selected paths are eligible. | If user selects Crossover, Divergence or Momentum must not produce final candidates. |
| Rejected/non-qualifying rows are processing outputs, not user-facing candidate classes. | design lines 116, 727-745; recap lines 237-249 | L5 | Non-qualifying selected-path rows should be logged with rejection reasons and relevant values. | Do not expose a non-candidate state as a user-facing analysis option or score it as a candidate family. |
| Defaults and thresholds live outside decision code. | design lines 120-157; recap lines 253-269 | Config/L0 | Parameters are configurable per run/profile. | Do not bury market/sector/stock-sensitive thresholds inside evaluator code. |

### Hierarchical Engine Flow

| V2 intent | Source pointer | V3 level | Carry-forward rule | Anti-regression guardrail |
|---|---|---|---|---|
| Engine must be path-first, not indicator-first. | design lines 7-9; recap lines 18-21 | Whole engine | Baseline, route, then evidence. | Do not calculate every indicator/timeframe globally before path selection. |
| Stage-family indicator matrix governs usage. | design lines 253-263; recap lines 130-149; `v3_evidence_stage_matrix.md` sections 4-5 | L2/L3/L4 | Every indicator/evidence item must have a path-specific matrix meaning. | Do not add an indicator directly into an evaluator without documenting its matrix row/cell. |
| L1 baseline establishes current technical state. | design lines 185-207; recap lines 89-103 | L1 | Determine where the stock is now. | Baseline sets route context; it is not final classification. |
| L2 router chooses the relevant path. | design lines 209-232; recap lines 105-128 | L2 | Router respects baseline and user-selected families. | Router must prevent Crossover/Divergence/Momentum leakage. |
| L3 functions calculate only evidence required by L2. | design lines 234-277; recap lines 130-149, 346-356 | L3 | Indicator functions are compute-only and on-demand. | No classification inside raw indicator calculation. |
| Baseline must not erase transition versus established regime. | design lines 302-318; evidence matrix lines 47, 152 | L1/L2 | Separate transition, continuation, divergence, and fallback. | Above-zero bull continuation must not become `PRE_BULL_CROSSOVER`. |
| Stage-family scores are not equivalent across paths. | design line 347 | L4/L5 | Score inside each path and compare only through an explicit ranking contract. | Do not treat Crossover 80 as equivalent to Divergence 80 without ranking rules. |
| WeightedScore is per ticker inside the selected family, then grouped for display by family. | V2-compatible UI/export contract plus clarified scoring intent | L4/L5/UI | Compute each ticker's score from its own indicator/evidence values under the selected family formula, then display results grouped by stage family. | Do not collapse all qualified rows into one flat score pool by default. |

### Data And API Method

| V2 intent | Source pointer | V3 level | Carry-forward rule | Anti-regression guardrail |
|---|---|---|---|---|
| Use provider abstraction. | design line 183 | L0 | API/provider retrieves data required by selected calculation. | Provider behavior must not leak into strategy rules. |
| Fetch daily baseline data first. | design line 175 | L0/L1 | Daily data supports baseline. | Do not fetch lower timeframes unless path evidence needs them. |
| Fetch 4H/1H only when route needs it. | design lines 176, 298-299; recap lines 174, 277-279, 350-354 | L3 | Lower timeframe is timing/confirmation only. | Lower timeframe must not override base route blindly. |
| Momentum MACD baseline needs Close series. | design lines 582-587; recap lines 207-212 | L3 Momentum | Close series is enough for MACD baseline. | Do not impose OHLCV as universal input. |
| Volume is optional confirmation for Momentum baseline. | design lines 586, 716; recap lines 211, 230 | L3/L4 | Use volume only as quality/context when requested or configured. | Volume must not become a hidden base gate. |

### Crossover Intent

| V2 intent | Source pointer | V3 level | Carry-forward rule | Anti-regression guardrail |
|---|---|---|---|---|
| Crossover means transition, not established regime. | design lines 401-405; recap lines 152-156 | L2/L4 | Classify only transition or near-transition states. | Do not classify already bullish continuation as Crossover. |
| Detect bullish and bearish MACD/signal crosses. | design lines 409-412; recap lines 156-159 | L3/L4 | MACD line/signal cross is core Crossover evidence. | Directional Crossover states remain separate. |
| Freshness must be recorded. | design lines 437-444 | L3/L4/L5 | Include bars since MACD/signal and zero-line crosses. | Stale crosses must be classified/audited separately. |
| Zero-line context is separate from crossover detection. | design lines 448-465; recap lines 165-170 | L3/L4 | Zero-line improves context/quality. | Do not require `histogram > 0.5` or `MACD > 0.5` for generic `PRE_BULL_CROSSOVER`. |
| Histogram confirms real/non-flat crossover. | design lines 424-433, 750-758; recap lines 165-170 | L3/L4 | Use histogram/spread as readiness or quality evidence. | No universal histogram strength gate across paths. |
| Historical MACD/histogram behavior can aid readiness. | design lines 28, 245, 283-287; recap lines 55, 263 | L3/L4 | Use as probability/confidence aid for near-crossover. | It cannot relabel Momentum continuation as Crossover. |

### Divergence Intent

| V2 intent | Source pointer | V3 level | Carry-forward rule | Anti-regression guardrail |
|---|---|---|---|---|
| Divergence means price/momentum disagreement. | design lines 484-488; recap lines 176-180 | L2/L4 | Keep as independent stage family. | Do not infer Divergence from Crossover failure or Momentum continuation. |
| Raw divergence is evidence, not final candidate. | design lines 506-520; recap lines 187-194 | L3/L4 | Raw geometry remains auditable. | Do not promote raw divergence without confirmation/context. |
| Confirmed divergence waits for histogram momentum to turn. | design lines 520-524 | L3/L4 | Bullish: histogram below zero but improving. Bearish: above zero but deteriorating. | Developing evidence must not be promoted as confirmed. |
| Divergence uses swing/histogram comparison. | design lines 506-537; recap lines 189-194 | L3 | Compare price swing and histogram swing. | Do not apply generic `histogram > 0.5` strength gate. |
| Divergence scoring stays separate. | design lines 498, 543-557; divergence contract lines 7, 217-219 | L4/L5 | Emit direction/type/confirmation/reason fields. | Do not import Crossover hard gates or Momentum continuation gates. |

### Setup Intent

| V2 intent | Source pointer | V3 level | Carry-forward rule | Anti-regression guardrail |
|---|---|---|---|---|
| Setup replaces the old generic `Setup` label and is the selected path for continuation, re-entry, and extension behavior. | design lines 559-567; recap lines 198-202 | L2/L4 | Setup is its own selected path. | It must not modify Crossover or Divergence rules. |
| Setup uses stock-specific historical MACD behavior. | design lines 571-599; recap lines 204-222 | L3/L4 | Compare current setup momentum with the stock's own history. | Do not use universal histogram strength as primary definition. |
| Default Setup MACD reference is `MACD(8,21,5)`. | design lines 582-585; recap lines 207-210 | L3 | Use configurable Setup MACD parameters. | Keep parameters in config, not buried in code. |
| Setup phases are histogram episodes. | design lines 593-617; recap lines 214-222 | L3 | Split bull/bear phases and consecutive episodes. | Positive bars alone are not equivalent to phase episodes. |
| Setup strength is percentile/history based. | design lines 619-665 | L3/L4 | Compare current histogram to stock-specific averages/percentiles. | Do not use a global `0.5` threshold as primary strength. |
| Phase maturity is confidence context. | design lines 671-687; recap lines 224-233 | L4 | Early/developing/mature/extended affects confidence and chase risk. | Maturity must not override path routing. |
| RSI, ADX, volume, liquidity, extension risk need scoped decisions. | design lines 712-720; recap lines 224-230 | L3/L4 | Use as bounded quality/confidence inputs after route. | Do not let them become global gates. |

### Scoring, Ranking, And Output

| V2 intent | Source pointer | V3 level | Carry-forward rule | Anti-regression guardrail |
|---|---|---|---|---|
| WeightedScore was unreliable as promotion logic. | gap analysis lines 227-241, 390-391 | L4/L5 | Rebuild as component confidence/detail score. | Do not use old WeightedScore as promotion gate. |
| Distinguish route validity, quality, context risk, and output priority. | gap analysis lines 15-24, 145-176, 195-209 | L2/L4/L5 | Keep separate fields for each decision layer. | Do not mix invalidating evidence with probability evidence. |
| Ranking is reporting/prioritization. | `docs/architecture/v3_ranking_contract.md` lines 9, 61-68 | L5 | Ranking chooses display winner after family logic. | Ranking must not mutate family signal logic or suppress evidence. |
| Failed checks remain auditable. | evidence matrix lines 51-60, 338-342 | L5 | Emit reason codes, risk tags, diagnostics. | Do not silently hide weak/failed route evidence. |
| V2-compatible output visibility should remain. | `docs/architecture/v2_operational_parity_contract.md` lines 5-59 | L5/UI | Keep CSV/log/summary auditability and leading V2 columns where useful. | UI must not hide why a symbol was selected/skipped. |

### Backtesting, Metadata, And Operations

| V2 intent | Source pointer | V3 level | Carry-forward rule | Anti-regression guardrail |
|---|---|---|---|---|
| Historical replay/backtesting is required for validation. | gap analysis lines 296-302, 451-485; design lines 907-908 | L5 | Same production engine should run against D-date slices. | No stage is complete until historical D and D+X validation proves the engine is correctly identifying genuine candidates. |
| D-date processing must avoid lookahead. | canonical rule plus backtesting utility intent | L0/L5 | Classify with data through D, validate later with D+X. | D+X data must never enter initial classification. |
| Backtesting uses same selected path as live analysis. | working matrix Backtesting column | L5 | User supplies D-date, provider fetches historical data, engine runs selected Crossover/Divergence/Setup path as of D, then D+X validates price movement. | Backtesting must not introduce a fourth path or alternate evaluator. |
| Preserve input metadata for audit. | design lines 87, 835-862; gap analysis lines 268-284, 412 | L0/L5 | Keep source metadata like sector/industry/volume when supplied. | Do not use current profile facts as historical truth without tagging. |
| One symbol failure must not fail the run. | design lines 818-831; recap lines 377-381 | L0/L5 | Record per-symbol provider/data errors. | Only input/output layer failures should stop the whole run. |
| Performance cannot break trading logic. | design lines 792-813, 922 | Whole engine | Batch and optimize after correctness. | A faster path is unacceptable if classification correctness is reduced. |

## V3_Charter Validation Requirement From The Matrix

Before implementing or carrying forward any V2 item, create or identify a validation check for:

1. correct `V3_Charter` hierarchy placement;
2. selected-path restriction;
3. no override of the other two paths;
4. no global gate unless explicitly defined as a base gate;
5. D-date no-lookahead behavior where dates are involved;
6. output diagnostics proving why the item affected score, risk, or classification.

This matrix is the start point for engine construction. Future implementation should not re-discover these V2 points from scratch.

## Date Processing And D+X Self-Backtesting

Date processing is part of the core engine, not an optional later feature.

Definitions:

- `D`: the analysis date.
- `D+X`: the forward validation horizon after D.

Rules:

- production classification must use only data available on or before D
- forward D+X data must be loaded only after classification
- D+X validation must check whether the engine's classified setup was followed by actual price movement
- forward validation must report pass/fail/insufficient-data rather than silently assuming success
- D+X horizons should be configurable, with practical defaults such as D+1, D+2, D+5, D+10, and D+20 where supported by data

Self-backtesting is a quality gate for the signal engine. It is not permission to add unrelated strategies.

## Output And Audit Contract

Every result must be explainable.

Minimum required output fields:

- input symbol
- resolved provider symbol
- selected user path
- D-date
- final candidate class
- acceptance/rejection status
- reason codes
- L1 baseline state
- L2 routed path
- L3 evidence used
- D+X validation result where applicable
- provider/data status

The output should preserve V2-compatible visibility where useful, including reason-code discipline and CSV-friendly diagnostics.

## Explicit Non-Goals

The following are not part of the core `V3_Charter` intent:

- default pan-USA market scanning
- default sector-by-sector calibration
- market regime or sector analysis as a separate screening/calibration project
- treating market regime as a reason to expand beyond the supplied CSV
- ETF portfolio mapping
- automated trading
- order execution
- stop-loss trading logic
- position sizing
- portfolio allocation
- hidden strategy expansion beyond the three allowed paths
- changing path rules based on one isolated validation slice
- broad token-expensive recalibration unless explicitly approved by the user

These may be separate future projects or optional features only if the user explicitly requests them.

## Regression Risks To Eliminate

The central `V3_Charter` risk is logical regression from mixed path behavior.

Known failure pattern:

- MACD is above the zero line
- stock is already in bullish continuation
- engine incorrectly labels it as `PRE_BULL_CROSSOVER`

`V3_Charter` must prevent this class of error through L1 baseline facts, L2 path routing, path-specific L3 evidence, and rejection rules in L4.

Other risks:

- divergence being inferred from momentum rules
- crossover being used as a fallback when momentum logic fails
- D+X validation using future data during initial classification
- provider gaps being mistaken for signal weakness
- UI allowing selections that the engine cannot process consistently

## Referenced V2 Analysis Artifacts

The V2 analysis work and design artifacts are not absent; they are scattered. Future sessions should read these as supporting references, not as replacements for this canonical document.

Primary references:

- `docs/archive_unified_stock_scanner_engine_design.md`
- `docs/archive_unified_engine_recap_and_action_plan_2026-05-24.md`
- `docs/archive_technical_signal_processing_engine.md`
- `docs/analysis/current_engine_gap_analysis_against_fresh_charter_2026-06-01.md`
- `docs/analysis/v3_initial_engine_analysis_and_way_forward_2026-06-01.md`
- `docs/architecture/v2_operational_parity_contract.md`
- `validation/baselines/v3_baseline_acceptance_pack.md`

Key V2 model references:

- `docs/archive_unified_stock_scanner_engine_design.md`: path-first L1/L2/L3 model and baseline/router/evidence separation
- `docs/archive_unified_engine_recap_and_action_plan_2026-05-24.md`: V2 recap, L1/L2/L3 implementation action plan, and audit expectations
- `docs/architecture/v2_operational_parity_contract.md`: V2-style output visibility and operational parity expectations

## Development Rules For Future Sessions

Every future session must follow these rules:

1. Read this document first.
2. Check local and remote git state before editing.
3. State the exact code or documentation step before making changes.
4. Keep work scoped to the CSV-driven `V3_Charter` engine unless the user explicitly asks for a separate feature.
5. Update documentation at the end of each completed step.
6. Commit locally at the end of each completed step when changes are valid.
7. Push to GitHub at the end of each completed step when network/authentication permits.
8. Update `docs/handover/current_session_handover.md` with current status and next steps.
9. If a requested or inferred task conflicts with this document, stop and ask the user before proceeding.

## Current Drift To Treat Carefully

Recent repository history includes sector, regime, and broad calibration work. Those artifacts should not be treated as `V3_Charter` core product direction.

Do not delete or revert that history without explicit user approval. Treat it as historical context only.

Do not carry forward the current drift version of market-regime, sector, and cross-sector calibration work as accepted product direction. Only extract confirmed processing pieces that fit the canonical CSV-driven engine, such as bounded market-regime context, EMA200 evidence, backtesting utility, and D/D+X date handling.

The forward direction is this canonical intent:

```text
User CSV + user-selected path + V2 path-first levels + D-date processing + D+X self-backtesting
```

## Forward Implementation Plan

### Phase 1: Intent Lock And Audit

- add this canonical document
- update README and handover pointers
- audit `web_app_v3.py` and `src/stock_screener_v3` against this document
- list logic that belongs to `V3_Charter` core versus drift artifacts

### Phase 2: Input And UI Contract

- enforce CSV upload/input as the primary universe source
- expose only the three allowed analysis options
- expose D-date and D+X controls
- prevent unsupported combinations in the UI

### Phase 3: L0/L1/L2/L3/L4/L5 Engine Structure

- formalize L0 input/data/date preparation
- formalize L1 baseline object
- formalize L2 router object
- split L3 evidence by path
- centralize L4 classification/rejection rules
- centralize L5 output/audit/backtesting

### Phase 4: V2 Logic Preservation

- recover and map V2 Crossover rules
- recover and map V2 Divergence rules
- recover and map V2 Setup rules
- write path-specific parity tests before changing behavior

### Phase 5: Self-Backtesting

- implement D+X validation for accepted candidates
- keep classification no-lookahead clean
- report validation outcome per symbol
- add tests for D-date slicing and D+X horizons

### Phase 6: Web App Integration

- wire UI inputs to the engine contract
- keep output CSV/audit visible
- show provider/data failures cleanly
- preserve V2-style user diagnostics where useful

## Handover Instruction

For a new session:

1. Read this file.
2. Run:

```powershell
cd D:\Tools\Stock_Screener_V3
git status --short --branch
git log --oneline --decorate -8
```

3. Read `docs/handover/current_session_handover.md`.
4. Continue only on tasks that align with this document unless the user explicitly changes direction.
