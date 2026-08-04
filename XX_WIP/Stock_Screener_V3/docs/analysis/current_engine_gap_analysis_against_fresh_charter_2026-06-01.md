# Current Engine Gap Analysis Against Fresh Charter

Date: 2026-06-01

Branch observed: `scoring/prebull-quality-context`

Reference charter: `Library/engine_program_charter_fresh_2026-06-01.md`

Purpose: analyze the current engine against the fresh program intent, without assuming that the current implementation is the correct architecture.

## 1. Executive Assessment

The current engine contains several useful building blocks, but it is no longer a clean expression of the program charter.

The main issue is not that the engine has no intelligence. The issue is that too many concepts are mixed inside one monolithic flow:

```text
route eligibility + technical validity + score quality + context risk + output suppression
```

This creates two practical failures:

1. Candidate density becomes too low because borderline but valid technical signals are converted to `STATUS_QUO`.
2. Candidate ranking remains unreliable because score factors were added reactively and are not calibrated through a standard backtesting pack.

The current code should not be discarded blindly. It has valuable indicator calculations, reason codes, historical replay capability, and partial route separation. But the decision layer should be refactored or rebuilt around the fresh charter before more signal rules are added.

## 2. High-Level Alignment

| Charter Requirement | Current Engine Status | Assessment |
|---|---|---|
| User-driven tactical scanner | Present | Keep |
| Stage families: Crossover, Divergence, Momentum | Present | Keep, but separate better |
| Path-first design | Partially present | Refactor |
| Evidence pack before classification | Partial | Refactor |
| Hard gates rare | Not aligned | Refactor |
| Quality and context scoring separate | Not aligned | Refactor |
| Review priority separate from state | Missing | Add |
| Stable metadata baseline | Missing | Add |
| Market/sector context | Partial | Refactor |
| Event risk | Missing | Add |
| First-class backtesting engine | Partial script exists | Promote to subsystem |
| Candidate density reporting | Manual | Add |
| Score calibration | Not proven | Rebuild validation process |

## 3. What To Keep

### 3.1 Indicator Calculations

The current `StockScreener` already calculates many useful technical facts:

- MACD fast and baseline variants.
- RSI.
- ADX and DMI.
- Bollinger position.
- EMA200 context.
- Candle profile.
- Intraday close profile.
- Volume profile.
- Money flow.
- Price structure.
- Efficiency ratio.
- Overhead supply proxy.
- Benchmark-relative strength.

These are valuable as raw evidence functions.

Recommendation:

```text
Keep the calculations, but move them toward a neutral evidence-pack layer.
```

### 3.2 Reason Codes

Reason codes are a strong feature. They make failures auditable and make backtesting interpretable.

Recommendation:

```text
Keep reason codes, but classify them into categories:
Route, Timing, Structure, Participation, Context, Risk, Data.
```

### 3.3 Fixed-Date Replay Concept

`HistoricalScreener` and `backtest_strategy_family.py` prove that same-engine historical replay is possible.

Recommendation:

```text
Keep the concept, but promote it into a first-class backtesting engine.
```

### 3.4 Directional Crossover Routes

Splitting Pre-Bull and Pre-Bear route selection is directionally correct.

Recommendation:

```text
Keep route separation, but simplify what belongs to route validity versus score/context.
```

## 4. What To Refactor

### 4.1 Monolithic `screen()` Flow

Current behavior:

`screen()` loads data, fetches profile, calculates many indicators, builds shared state, evaluates crossover, classifies candidate, scores, filters, and emits output rows.

Problem:

This violates the charter's clean architecture:

```text
Universe -> Data -> Baseline -> Route -> Evidence -> Classify -> Score -> Rank -> Audit
```

Current `screen()` is doing most of that at once.

Impact:

- Hard to reason about stage-family leakage.
- Hard to preserve metadata through historical replay.
- Hard to test one layer independently.
- Hard to know whether a rejected row was invalid, low quality, risky, or simply filtered.

Recommendation:

Split into:

- `UniverseRecord`
- `PriceDataBundle`
- `EvidencePack`
- `StageEvaluation`
- `ScoreResult`
- `OutputRow`

### 4.2 Crossover Evaluation

Current behavior:

`evaluate_crossover_path()` handles route selection, daily eligibility, zero-line rules, EMA200 requirements, lower-timeframe bridge, quality blocks, and selected/watch demotion.

Problem:

The function mixes four separate questions:

1. Is this technically a Crossover route?
2. Is the timing active?
3. Is the quality strong?
4. Should the row be hidden from selected output?

Impact:

This is the largest cause of low candidate density. Valid but risky or incomplete technical signals are often collapsed into `STATUS_QUO`.

Recommendation:

Refactor Crossover into:

```text
evaluate_crossover_route()
evaluate_crossover_timing()
evaluate_crossover_quality()
evaluate_crossover_context_risk()
assign_crossover_review_priority()
```

Output should allow:

- Valid route + weak quality.
- Valid route + event risk.
- Valid route + low confidence.
- Watch state with explicit output policy.

### 4.3 Hard Gates Versus Score Factors

Current hard/blocking behavior includes:

- 1D MACD zero-line side.
- EMA200 below/near requirement.
- Daily MACD and signal below zero for Pre-Bull.
- Histogram momentum.
- Lower-timeframe bridge.
- Latest 1H close confirmation.
- Selected-output quality blocks such as negative confirmation, severe distribution, falling EMA with lag, and weak daily acceptance.

Some of these may be stage-defining. Others are clearly quality/context factors.

Problem:

The current engine does not consistently distinguish invalidating evidence from probability evidence.

Impact:

- Candidate density drops.
- The engine becomes reactive to past failures.
- Good but messy early signals are hidden instead of classified as lower priority.

Recommendation:

Hard gate only:

- Missing data.
- Wrong direction.
- No route/timing evidence.
- User filter exclusion.

Score or risk-tag:

- ADX/ER.
- CMF/OBV.
- EMA200 slope.
- Volume.
- Candle quality.
- Relative strength.
- Headroom.
- Event risk.

### 4.4 Scoring

Current behavior:

WeightedScore starts from MACD/RSI/ADX weights and then applies many additive/subtractive adjustments.

Problem:

The score is not calibrated. Recent tests showed low scores can pass and higher scores can fail.

Observed examples:

- May 5: `LCNB` passed both days with low score.
- May 5: `EXPO` failed both days despite being a valid technical signal.
- Feb 11: sector-restricted test had `PNR` as the only pass, while several other selected rows failed.

Recommendation:

Do not rely on current `WeightedScore` for promotion decisions.

Rebuild score as stage-specific components:

| Component | Purpose |
|---|---|
| Route/timing | Technical validity |
| Structure | Price behavior |
| Participation | DMI, CMF, OBV, volume |
| Acceptance | Candle/intraday close |
| Market/sector context | Relative strength |
| Risk/headroom | Resistance, event risk, liquidity |

Then validate score bucket separation through backtesting.

### 4.5 Metadata Handling

Current behavior:

The live engine can fetch Yahoo profile metadata. Historical replay uses fast profile behavior and often loses sector metadata.

Problem:

This breaks sector-aware validation.

Example:

The sector-restricted Feb 11 test selected symbols from Industrials, but the historical output `Sector` field was blank because replay did not preserve the master CSV sector metadata.

Recommendation:

Implement enriched universe records before more sector-relative tuning.

Required minimum:

- Symbol.
- YahooSymbol.
- CompanyName.
- Exchange.
- Sector.
- Industry.
- InstrumentType.
- MarketCap.
- AvgDailyVolume.
- SourceFile.
- LastProfileRefreshDate.

### 4.6 Backtesting Engine

Current behavior:

`backtest_strategy_family.py` can run fixed-date replay, sample-file replay, and universe mode. It writes detail and summary outputs.

Problems:

- It is still a script, not a program subsystem.
- It loads one symbol at a time in universe mode, which is slow.
- Candidate-density reporting is not first-class.
- Metadata is not preserved consistently.
- It does not produce multi-date aggregate scorecards.
- It does not compare baseline versus branch changes.
- It does not classify failure categories systematically.

Recommendation:

Promote it into a backtesting subsystem before further signal redesign.

## 5. What To Discard Or Stop Doing

### 5.1 Stop Adding One-Off Hard Gates

The current path has accumulated tactical gates to solve individual observed failures.

This should stop.

New rule:

```text
No new hard gate unless it defines stage validity and passes a multi-date validation pack.
```

### 5.2 Stop Treating D+1/D+2 Failure As Technical Invalidity

The engine should distinguish:

- Technical signal valid, follow-through failed.
- Technical signal invalid.
- Event-risk failure.
- Choppy-market failure.
- Liquidity/volatility failure.
- Ranking failure.

### 5.3 Stop Using Current Candidate Density As Acceptable

Recent random tests showed low density:

- May 5 full random: 4 selected from 625.
- Feb 11 full random: 4 selected from 625.
- Feb 11 sector-restricted: 4 selected from 625.

This is too sparse for a tactical scanner unless the user explicitly wants extremely rare signals.

## 6. Root Causes Of Low Candidate Density

Likely causes:

1. Pre-Bull definition is too narrow:
   - Requires daily MACD and signal below zero.
   - Requires price below/near EMA200.
   - Requires histogram improvement.
   - Requires lower-timeframe bridge/timing.

2. Quality concerns sometimes become output suppression:
   - Negative confirmation.
   - Severe distribution.
   - Weak daily acceptance.
   - Falling EMA with 20D lag.

3. Watch states are hidden:
   - Potentially useful early candidates become `STATUS_QUO`.

4. Current Crossover route only captures one subtype:
   - It mostly catches early reversal/reclaim behavior.
   - It may miss pullback-continuation, above-zero re-entry, and momentum resumption setups.

5. The engine is overloaded by a single `PRE_BULL_CROSSOVER` label:
   - Different market behaviors are being forced into one state.

## 7. Proposed State Model Correction

Instead of one overloaded Pre-Bull route, split technical opportunity types.

Suggested Crossover-related states:

| State | Meaning |
|---|---|
| `PRE_BULL_REVERSAL_CROSSOVER` | Below-zero recovery / early reversal |
| `BULL_PULLBACK_REENTRY` | Above-zero pullback resumes trend |
| `BULL_CONTINUATION_MOMENTUM` | Existing trend continuation |
| `PRE_BEAR_REVERSAL_CROSSOVER` | Above-zero deterioration / early bearish transition |

The current engine tries to force too much into `PRE_BULL_CROSSOVER`, then blocks cases that do not fit the narrow definition.

## 8. Fresh-Charter Gap Table

| Area | Keep | Refactor | Discard |
|---|---|---|---|
| Indicator calculations | Yes | Move into EvidencePack | No |
| Reason codes | Yes | Categorize | No |
| Current Crossover function | Some logic | Split into route/timing/quality/context | Monolithic form |
| Current WeightedScore | As diagnostic history | Rebuild as component score | Do not use as promotion gate |
| Current backtest script | Concept | Promote to subsystem | No |
| Yahoo profile lookup | As fallback | Replace hot-path dependence | Runtime metadata dependency |
| Watch states | Yes | Expose or rank separately | Do not silently hide all |
| Event handling | Missing | Add | N/A |
| One-off hard gates | No | Convert to score factors | Stop pattern |

## 9. Recommended Remediation Plan

### Step 1: Freeze Current Signal Tuning

Do not add more Crossover gates until architecture is corrected.

### Step 2: Build Enriched Universe Metadata

This is foundational for sector tests, profile filters, and historical replay.

Deliverable:

- `enriched_universe_us.csv`
- `enriched_universe_nse.csv`
- Loader that returns records, not just symbols.

### Step 3: Promote Backtesting Engine

Deliverable:

- Single-date replay.
- Multi-date replay.
- Random-lot replay.
- Sector-filtered replay.
- Full-universe ranked replay.
- Candidate density report.
- Score-bucket report.
- Failure-category report.

### Step 4: Refactor Evidence Pack

Current indicator functions should write into an explicit evidence object.

No classification inside evidence calculation.

### Step 5: Rebuild Crossover Around Multiple Opportunity Types

Separate:

- Below-zero reversal.
- Above-zero pullback re-entry.
- Momentum continuation.
- Bearish reversal.

### Step 6: Recalibrate Scoring

Use the backtesting engine to test score buckets across multiple dates before promoting scoring rules.

## 10. Decision: Refactor Or Restart?

Recommended decision:

```text
Do not throw everything away.
Do not keep tuning the current monolith.
Refactor by extracting reusable evidence functions and rebuilding the decision layer around the fresh charter.
```

Rationale:

- Indicator and output infrastructure are useful.
- UI and async scan shell are useful.
- Reason-code practice is useful.
- Fixed-date replay concept is useful.
- The current Crossover decision layer is the part most in need of redesign.

If the refactor becomes harder than expected, the fallback should be:

```text
Keep UI, data loading, indicator functions, and backtest harness ideas.
Rebuild StageEvaluator and Scoring modules from scratch.
```

## 11. Immediate Next Work

Recommended next task:

Create a module-level implementation plan:

```text
1. UniverseRecord and metadata loader.
2. EvidencePack object.
3. BacktestingEngine v1.
4. CrossoverEvaluator v2 with separate route/timing/quality/context outputs.
5. Output model with CandidateClass and ReviewPriority.
```

Only after those exist should the engine be tuned again.

