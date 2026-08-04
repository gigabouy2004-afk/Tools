# V3 Stage-Family Indicator Working Matrix

Last updated: 2026-06-19

Purpose: core build-control table for constructing the V3 engine from the charter and V2 design intents without re-discovery. This is the editable matrix where indicator families, gates, evidence modules, inputs, outputs, inclusion/exclusion rules, guardrails, and path-specific processing functions must be added, removed, finalized, or modified before coding.

Canonical scope: `docs/charter/v3_original_intent_and_handover.md`

Reference matrix: `docs/architecture/v3_evidence_stage_matrix.md`

V2 sources:

- `docs/archive_unified_stock_scanner_engine_design.md`
- `docs/archive_unified_engine_recap_and_action_plan_2026-05-24.md`
- `docs/architecture/v2_operational_parity_contract.md`

## Usage Rule

No indicator or evidence item should be implemented directly in an evaluator unless its row exists here or in the reference evidence-stage matrix.

Each row must answer:

- what API data is required;
- which V3 level owns the calculation;
- whether the item is route, timing, quality, context, scoring, audit, or validation;
- which path can use it;
- what exact processing function or condition set it should produce inside each stage-family cell;
- what inclusion rule allows it into the engine;
- what exclusion rule prevents it from affecting the wrong path or candidate;
- what output fields prove it was evaluated;
- what it must not override.

Algorithm coding is blocked until the relevant matrix row is finalized. Rows that remain `TBD` are future/blocked rows and must not be implemented as production behavior.

## Matrix Finalization Gate

Before additional engine behavior is coded, this matrix must be reviewed row by row.

Each row must be classified as one of:

- `APPROVED_CURRENT`
- `PARTIAL_CURRENT`
- `FUTURE_TBD`
- `BLOCKED_PENDING_SIGNOFF`
- `REFERENCE_ONLY`

For every `APPROVED_CURRENT` row, the implementation plan must identify:

- input source;
- output field names;
- owning module or intended module;
- required tests;
- required validation artifact if behavior changes;
- whether scoring belongs in code config or an external manifest.

The matrix-to-code implementation assessment must be produced from this table before further algorithm changes.

## Matrix Representation Rule

Rows must be written as indicator families or evidence families, not as vague single values.

Examples:

- good row name: `MACD`
- weak row name: `MACD(1D)`

The cell under each stage family must contain the exact path-specific condition logic or processing function for that indicator family.

Examples:

- `CROSSOVER`: `MACD(1D) < Signal(1D)` and `Histogram(1D)` near zero, with optional same-analysis-point 4H/1H confirmation if requested.
- `DIVERGENCE`: price swing versus histogram swing disagreement plus confirmation turn.
- `SETUP`: `MACD(1D) > Signal(1D)` and bull-phase continuation/re-entry logic using the Setup baseline where applicable.

All indicator processing remains API/provider-driven. The matrix should describe the data needed from the provider, not assume hardcoded/static inputs inside evaluator logic.

Legend:

- `Route`: this condition can help decide whether a ticker belongs in that stage family.
- `Timing`: this condition can help decide whether the setup is early, fresh, near-trigger, or stale.
- `Quality`: this condition can improve or weaken confidence after the stage family is already known.
- `Context`: this condition adds background interpretation, risk, or review priority, but should not decide the stage by itself.
- `Scoring`: this condition affects `WeightedScore` only after the ticker has already qualified for the selected stage family.
- `Audit`: this item exists for explanation, output visibility, and failure logging.
- `Validation`: this item belongs to D / D+X backtesting only.
- `Not used by default`: this row is not part of the default logic for that stage family.
- `TBD`: exact meaning still needs user signoff before implementation.

## Core Path Matrix

Path note:

- `CROSSOVER` in this matrix includes both `PRE_BULL_CROSSOVER` and `PRE_BEAR_CROSSOVER`.
- The cell text under `CROSSOVER` should therefore describe how the row supports bull-transition review, bear-transition review, or both.
- `PRE_BULL_CROSSOVER` is for entering early enough to maximize the natural bull phase.
- `PRE_BEAR_CROSSOVER` is for capital-preservation review on existing long-held equities, not stop-loss trading logic.
- `DIVERGENCE` is for validating whether an investment opportunity may be developing.
- `SETUP` is a pure-play market-based entry path where technical-analysis indicators provide confidence for a potentially shorter-lived entry than a full Pre-Bull phase capture.

| Indicator Family / Evidence | API data required | V3 level | CROSSOVER | DIVERGENCE | SETUP | Backtesting / D+X | Primary outputs | Guardrail |
|---|---|---:|---|---|---|---|---|---|
| User CSV symbol | CSV row | L0 | Route input: supplied universe only. | Route input: supplied universe only. | Route input: supplied universe only. | Use same supplied CSV universe for historical run. | `Symbol`, `YahooSymbol`, source metadata | Supplied CSV is the universe; no hidden expansion. |
| User selected path | UI/input config | L0/L2 | Route input: only selected path can qualify candidates. | Route input: only selected path can qualify candidates. | Route input: only selected path can qualify candidates. | Execute the same selected path on D-date data. | `StageFamily`, selected family list | Only selected paths can produce final candidates. |
| D-date | UI/input config | L0/L5 | Context plus validation boundary for all D-date calculations. | Context plus validation boundary for all D-date calculations. | Context plus validation boundary for all D-date calculations. | Primary historical analysis date; API data sliced as of D. | `DDate`, data cutoff | D+X data must not enter classification. |
| D+X date / horizon | UI/input config | L5 | Validation only after D classification is complete. | Validation only after D classification is complete. | Validation only after D classification is complete. | Forward validation date/horizon after D. | `ForwardDays`, `DPlus{N}*` fields | D+X is validation only, never route evidence. |
| YFinance/provider historical pull | API provider | L0/L5 | Validation support for replaying the same provider-backed calculation stack. | Validation support for replaying the same provider-backed calculation stack. | Validation support for replaying the same provider-backed calculation stack. | Pull enough past data for D-date calculation plus forward data through D+X. | provider status, data errors | Same provider contract as live mode; provider gaps are reported. |
| D-date close price | API historical price | L0/L5 | Validation baseline price for D outcome. | Validation baseline price for D outcome. | Validation baseline price for D outcome. | Baseline price for D+X price check. | `DDateClose` TBD | Must be price available on or before D. |
| D+X close price | API forward price | L5 | Validation-only forward close price. | Validation-only forward close price. | Validation-only forward close price. | Simple forward close comparison versus D. | `DPlus{N}ReturnPct` | Forward price is loaded after classification. |
| D+X high/low path | API forward high/low when available | L5 | Validation-only forward path extremes. | Validation-only forward path extremes. | Validation-only forward path extremes. | Optional best-high/worst-low validation. | `DPlus{N}WorstLowReturnPct`, `DPlus{N}BestHighReturnPct` | Path validation is separate from simple endpoint check. |
| Close series | API historical price | L1/L3 | Route and timing input for close-derived calculations. | Route and context input for close-derived calculations. | Route and quality input for close-derived calculations. | Use only rows <= D for indicator values. | close-derived indicators | Fetch through API per calculation; not a CSV requirement. |
| MACD | Close series for 1D baseline; lower-timeframe API data only when requested | L3/L4 | `MACD(1D) < Signal(1D)` with `Histogram(1D)` near zero for near-bull transition; `MACD(1D) > Signal(1D)` with bear-side inverse for near-bear transition; optional same-analysis-point `4H` and `1H` confirmation only when requested. | Price swing versus histogram swing disagreement; confirmation requires the expected histogram turn, not MACD alone. | `MACD(1D) > Signal(1D)` / bull-phase continuation or re-entry logic; Setup-specific MACD baseline and historical phase behavior may refine quality. | Recompute the same MACD condition stack as of D and validate against D+X movement. | `MACD_1D_*`, optional `MACD_4H_*`, `MACD_1H_*`, phase outputs | `MACD` is an indicator family row; path cells must hold exact relations, not vague labels. |
| MACD crossover distance / freshness | Close series; lower-timeframe API data only when requested | L3/L4/L5 | Distance and bars-since-cross decide near-transition readiness and freshness. | Audit/context only unless a specific divergence rule later uses freshness. | Audit/context only unless Setup maturity later uses it. | Compare fresh versus stale D conditions by D+X outcome. | `MACD_1D_CrossoverDistance`, bars-since-cross fields | Distance/freshness cannot override path boundary by itself. |
| MACD zero-line context | Close series | L3/L4/L5 | Zero-line side and nearness are context for transition quality; not the crossover itself. | Context only by default. | Context only by default. | Compare D zero-line context buckets with D+X outcome. | zero-line context outputs TBD | Zero-line context is separate from crossover detection. |
| Historical MACD phase episodes / Setup baseline | Close series, V2-style lookback | L3/L4 | Probability/readiness aid only if explicitly approved. | Context/audit only by default. | Stock-specific bull/bear phase episodes, `MACD(8,21,5)` baseline where approved, maturity and percentile/history logic. | Validate whether D phase maturity/strength predicted D+X move. | `Momentum_Phase`, `Momentum_Strength`, maturity outputs TBD | Use only inside SETUP unless another path explicitly signs it off. |
| RSI 1D | Close series | L3/L4 | Quality and context for recovery or weakening after crossover conditions are already known. | Route support plus quality for momentum disagreement. | Quality and scoring input for setup headroom. | Store D RSI and compare outcome buckets by D+X. | `RSI_1D`, `RSIScore` | RSI is not a global hard gate. |
| RSI upper boundary 80 | RSI 1D | L4 | Not used by default; optional context only if specifically approved. | Context only by default. | Scoring and quality input for remaining headroom below the configured upper boundary. | Validate Momentum headroom buckets against D+X. | `RSIHeadroomTo80`, `RSIScore` TBD | Distance from current RSI to 80 can affect confidence, not route. |
| ADX 1D | API price series as required | L3/L4 | Quality and context for trend expansion support. | Context for whether divergence has enough trend strength to matter. | Quality and scoring input for setup trend confidence. | Validate ADX bucket contribution by D+X. | `ADX_1D`, `ADX_State`, `ADXScore` | Low ADX should not automatically suppress early valid setups. |
| PlusDI / MinusDI | API price series as required | L3/L4 | Quality input for buyer versus seller participation after crossover conditions are known. | Context for directional participation around divergence. | Quality input for participation strength during continuation or re-entry. | Validate D directional participation against D+X. | `PlusDI_1D`, `MinusDI_1D` TBD | Directional participation only after path route is known. |
| EMA20 | Close series | L3/L4 | Timing and quality input for reclaim, hold, or loss around transition. | Context for short-structure support or resistance. | Route and quality input for pullback re-entry or continuation. | Validate D EMA20 relation against D+X. | `EMA20`, `EMA20_Above`, `EMA20_Below` | EMA20 meaning is path-specific. |
| EMA20 reclaim | Close series | L3/L4 | Timing input for a possible bull transition. | Context only by default. | Route input for pullback re-entry. | Validate D reclaim setups by D+X. | `EMA20_Reclaim` | Must not relabel continuation as crossover. |
| EMA20 rejection | Close series | L3/L4 | Context and risk flag around failed reclaim. | Quality and timing signal for bear-side weakening only if divergence logic uses it. | Context and risk flag for setup weakness. | Validate rejection rows by D+X. | `EMA20_Rejection` | Use as context unless path defines it as route. |
| EMA50 | Close series | L3/L4 | Quality and context for broader trend stack support. | Context only by default. | Quality and scoring input for broader trend stack support. | Validate trend-stack buckets by D+X. | `EMA50` TBD | Not a universal gate. |
| EMA200 | Close series | L3/L4 | Context, risk, and headroom signal; not a route trigger. | Context for major support or resistance. | Quality and context input for risk, headroom, and long-trend support. | Validate above/below EMA200 rows by D+X. | `EMA200`, `BelowEMA200` | Stage-specific evidence, not globally true gate. |
| Distance to EMA200 percent | Close series | L3/L4 | Context and scoring aid for how stretched price is versus EMA200. | Context and scoring aid only. | Quality and scoring aid for extension or headroom versus EMA200. | Validate distance buckets by D+X. | `DistanceToEMA200Pct` | Can affect score/risk only after route. |
| EMA200 slope | Close series | L3/L4 | Context and scoring aid for long-trend direction. | Context and scoring aid only. | Quality and scoring aid for long-trend direction. | Validate slope buckets by D+X. | `EMA200SlopeState` | Slope cannot create a candidate by itself. |
| Lifetime high | API long-range/lifetime history when requested | L3/L4 | Context and scoring aid only; never a base route trigger. | Context for major boundary support or resistance. | Quality and scoring input for headroom and extension risk. | Validate D boundary location by D+X. | `LifetimeHigh` | Request only when boundary analysis is selected/needed. |
| Distance to lifetime high percent | API long-range/lifetime history when requested | L4 | Context and scoring aid only. | Context and scoring aid only. | Quality and scoring aid for remaining headroom. | Validate headroom buckets by D+X. | `DistanceToLifetimeHighPct` | Bottom-level confidence aid only. |
| Lifetime high break count | API long-range/lifetime history when requested | L4/L5 | Audit plus context on prior breakout behavior. | Audit plus context on prior breakout behavior. | Quality, scoring, and audit input on prior breakout behavior. | Validate breakout history buckets by D+X. | `LifetimeHighBreakCount` | Does not override route. |
| EMA52 high / distance | API history where supported | L4 | Context and scoring aid once the exact V2 meaning is confirmed. | Context and scoring aid once the exact V2 meaning is confirmed. | Quality and scoring aid once the exact V2 meaning is confirmed. | Validate only after exact definition confirmed. | `EMA52High`, `DistanceToEMA52HighPct` | Confirm definition before coding. |
| EMA200 high / distance | API history where supported | L4 | Context and scoring aid once the exact V2 meaning is confirmed. | Context and scoring aid once the exact V2 meaning is confirmed. | Quality and scoring aid once the exact V2 meaning is confirmed. | Validate only after exact V2 meaning confirmed. | `EMA200High`, `DistanceToEMA200HighPct` | Confirm exact V2 meaning before coding. |
| One-month candle behavior | API monthly candles when requested | L3/L4 | Context and quality input from the monthly candle when explicitly requested. | Context and quality input from the monthly candle when explicitly requested. | Quality and scoring input from the monthly candle when explicitly requested. | Validate D monthly context against D+X. | TBD monthly candle fields | Bounded context only; no broad scan. |
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
| PriceBand module | API price series | L3/L4 | TBD pending exact path-specific meaning. | TBD pending exact path-specific meaning. | TBD pending exact path-specific meaning. | No backtest until row/cell meaning is defined. | TBD | V2 listed module; define row/cell before use. |
| Market regime | API benchmark data when requested/configured | L3/L4 | Context only as bounded market background. | Context only as bounded market background. | Context only as bounded market background. | Validate as bounded context split, not base route. | `MarketRegime` | Bounded context only; no universe expansion. |
| Sector context/regime | CSV sector + API benchmark only when requested/configured | L3/L4 | Context only as bounded sector background. | Context only as bounded sector background. | Context only as bounded sector background. | Validate as bounded context split for supplied CSV only. | `SectorRegime` | No sector calibration project by default. |
| Sector relative strength | API benchmark and symbol data | L3/L4 | TBD, with context-only use if later approved. | TBD, with context-only use if later approved. | Quality and context input when explicitly requested and defined. | No backtest until exact formula is defined. | TBD | Future bounded evidence, not broad scan. |
| AI / sentiment (`GetAI`) | External API/future provider | L3/L4 | TBD future context row only after provider and timestamp rules are defined. | TBD future context row only after provider and timestamp rules are defined. | TBD future context row only after provider and timestamp rules are defined. | No backtest until provider, timestamp, and no-lookahead rules are defined. | TBD | Future optional evidence only after core engine is stable. |
| Reason codes | evaluator output | L4/L5 | Audit output for why the ticker passed or failed Crossover. | Audit output for why the ticker passed or failed Divergence. | Audit output for why the ticker passed or failed Setup. | Required to explain D classification before D+X validation. | `ReasonCodes`, path reason fields | No failed check disappears silently. |
| WeightedScore | L4 scoring components | L4/L5 | Scoring output after the ticker already qualifies for Crossover. | Scoring output after the ticker already qualifies for Divergence. | Scoring output after the ticker already qualifies for Setup. | Validate score buckets against D+X outcome. | `WeightedScore`, component scores | Never a global promotion gate or route selector. |

## Backtesting Workflow

Backtesting is a fourth validation column in the matrix, not a fourth signal path.

Required flow:

```text
CSV symbols
-> user-selected path: CROSSOVER / DIVERGENCE / MOMENTUM_SETUP
-> user-supplied historical D-date
-> API/provider fetches historical data needed for the selected path
-> engine slices data as of D
-> engine runs the same path logic used for live analysis
-> engine records D classification, reason codes, score, and evidence
-> user-supplied D+X horizon/date is loaded after classification
-> simple D close versus D+X close price check validates direction
-> optional D+X best-high/worst-low path metrics are recorded
```

Backtesting inputs:

- CSV universe.
- selected path or paths.
- D-date in the past.
- D+X horizon or explicit D+X date.
- provider/API configuration, currently yfinance-style in the existing implementation.

Backtesting outputs:

- D-date classification result.
- D-date evidence and reason codes.
- D-date price used for validation baseline.
- D+X close price.
- D+X return percentage.
- optional D+X worst-low and best-high returns.
- pass/fail/insufficient-data outcome.

No-lookahead rule:

```text
D+X data must be unavailable to L1/L2/L3/L4.
D+X data belongs only to L5 validation.
```

## Immediate Review Items

These rows need user review before coding:

- RSI upper boundary 80 and exact scoring formula for Momentum headroom.
- Exact meaning of `EMA52High`, `EMA200High`, and EMA lifetime-high percentage.
- Whether one-month candle behavior is a default Momentum aid or only user-requested.
- Whether sector/market context is shown as a score component or only as audit/context.
- Whether 4H/1H MACD belongs only to Crossover initially.
- Whether `PriceBand` and `GetAI` remain future placeholders.

## Update Discipline

When a row is changed:

1. Update this matrix first.
2. Update `docs/charter/v3_original_intent_and_handover.md` only if the top-level contract changes.
3. Add or update tests before implementing behavior.
4. Keep output fields auditable.
5. Commit and push documentation and code at the end of the step.
