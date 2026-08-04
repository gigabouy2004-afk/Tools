# V3 Baseline Decision Tree

Date: 2026-06-02

Purpose: define the top-down baseline filter that runs before stage-family evaluation.

This is intended to prevent V2-style over-complex stage matrices. The engine should first understand the broad condition, then positively eliminate stage paths that do not make sense.

Implementation status:

```text
V1 complete for engine traversal.
```

The current implementation supports configurable benchmark symbols, market/sector benchmark loading, stock-regime classification, positive elimination, and audit output. Future work should improve configuration ergonomics and mapping coverage, not change the baseline-first architecture.

## 1. Design Principle

The engine must not start by asking every indicator every possible question.

It should ask:

```text
1. What is the market doing?
2. What is the sector doing?
3. What is this stock doing?
4. Which stage families are even applicable?
5. Which lower-level evaluator should inspect the stock?
```

This creates controlled routing before detailed scoring.

## 2. Baseline Levels

### Market Regime

Broad index context:

- US default: `SPY` or `QQQ`.
- India default: `NIFTY 50`.
- Custom geography/theme mappings are supported through `RegimeBenchmarkConfig`.

Initial V3 regime states:

- `BULLISH`
- `BEARISH`
- `MIXED`
- `UNKNOWN`

### Sector Regime

Sector benchmark context:

- US sector ETF or configured sector index.
- India sector index where available.

Same regime states:

- `BULLISH`
- `BEARISH`
- `MIXED`
- `UNKNOWN`

### Stock Regime

Stock baseline context from current evidence:

- price vs EMA20/EMA50/EMA200.
- MACD state and histogram direction.
- DMI buyer/seller participation.
- short-term structure.

Same regime states:

- `BULLISH`
- `BEARISH`
- `MIXED`
- `UNKNOWN`

## 3. Positive Elimination Rules

Positive elimination means the engine removes paths that do not fit the baseline before detailed evaluation.

| Market | Sector | Stock | Bull Entry Paths | Bear Exit Paths | Momentum Setup |
|---|---|---|---|---|---|
| `BEARISH` | `BEARISH` | `BEARISH` | Block | Allow | Block |
| `BEARISH` | `BEARISH` | `MIXED` | Watch only | Allow | Block |
| `BEARISH` | `MIXED` | `BULLISH` | Allow with risk | Allow | Watch only |
| `MIXED` | `BULLISH` | `BULLISH` | Allow | Allow | Allow |
| `BULLISH` | `BULLISH` | `BULLISH` | Allow | Allow | Allow |
| `BULLISH` | `BULLISH` | `BEARISH` | Watch only | Allow | Block |
| `UNKNOWN` | any | any | Allow with unknown-context tag | Allow with unknown-context tag | Allow with unknown-context tag |

The purpose is not to hide all bearish-market opportunities. It is to stop bullish entry families from being promoted when market, sector, and stock all disagree.

## 4. Stage Family Implications

### Crossover

`CROSSOVER` remains bidirectional:

- `PRE_BULL_CROSSOVER`: new capital entry.
- `PRE_BEAR_CROSSOVER`: exit or capital preservation.

Baseline routing can block bullish Crossover promotion, but it should not block bearish Crossover warnings when the user is using the engine to manage existing capital.

### Momentum Setup

`MOMENTUM_SETUP` is a bull-phase family.

It is blocked when:

- market is bearish,
- sector is bearish,
- stock is bearish.

It can be downgraded to watch/manual review when:

- broad market is bearish but stock is outperforming,
- sector is mixed or weak,
- stock is bullish but context is not supportive.

### Divergence

Divergence V1 is implemented and participates in the default holistic stage-family set after V1 ranking diagnostics. Its route contract is defined in:

```text
docs/architecture/v3_divergence_contract.md
```

Current routing guardrails:

- Bullish divergence can be relevant in bearish or mixed stock regimes.
- Bearish divergence can be relevant in bullish or extended stock regimes.
- Hidden bullish divergence is continuation-oriented and should be downgraded or risk-tagged when broad context is clearly hostile.
- Hidden bearish divergence can remain relevant in bearish or weakening stock regimes as failed-recovery evidence.
- Divergence must not inherit Crossover or Momentum Setup hard gates.
- In the all-bearish market/sector/stock positive-elimination case, bullish Divergence routes are blocked as bullish entry routes while bearish review remains available.

## 5. V3 Implementation Plan

Current target:

```text
EvidencePack
-> BaselineDecision
-> applicable stage families/directions
-> StageFamilyEvaluator
-> output diagnostics
```

Minimum output diagnostics:

- `MarketRegime`
- `SectorRegime`
- `StockRegime`
- `AllowedBullishStages`
- `AllowedBearishStages`
- `BlockedStageFamilies`
- `BaselineRouteReason`

## 6. Regime Benchmark Configuration

Regime benchmark selection must be configurable rather than embedded inside evaluator rules.

Current code-level config:

```text
RegimeBenchmarkConfig
```

Supported mappings:

- `market_benchmarks_by_exchange`
- `market_benchmarks_by_geography`
- `sector_benchmarks`
- `theme_benchmarks`
- `default_market_benchmark`

Initial defaults:

| Context | Benchmark |
|---|---|
| NASDAQ | `QQQ` |
| Q exchange code | `QQQ` |
| NYSE / AMEX | `SPY` |
| N / A exchange codes | `SPY` |
| NSE | `^NSEI` |
| BSE | `^BSESN` |
| Technology | `XLK` |
| Energy | `XLE` |
| Industrials | `XLI` |
| Financials | `XLF` |
| Health Care | `XLV` |
| Consumer Discretionary | `XLY` |
| Consumer Staples | `XLP` |
| Communication Services | `XLC` |
| Materials | `XLB` |
| Real Estate | `XLRE` |
| Utilities | `XLU` |

Benchmark loading is non-fatal. If a configured benchmark cannot be loaded, the corresponding regime remains `UNKNOWN` and the stock is still evaluated.

## 7. Guardrail

This tree is a routing layer, not a scoring layer.

It should only eliminate paths when the high-level baseline is clearly incompatible. Borderline cases should remain eligible but carry lower confidence, risk tags, or manual review priority.
