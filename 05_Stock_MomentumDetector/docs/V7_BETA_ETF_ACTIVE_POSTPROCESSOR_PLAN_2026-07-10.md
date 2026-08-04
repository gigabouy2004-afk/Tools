# V7 Post-Processor Implementation Track: Beta First, ETF Mapping Second

> **Updated decision — 2026-07-11:** Beta is closed and dropped without production signoff because the pilot evidence was not conclusive. All Beta sections below are historical only. The direct ETF mapping requirements remain active for V8 and proceed independently as Phases 2A, 2B, and 2C.

Date: 2026-07-10

Status: Beta portion retired; ETF Phases 2A-2C authorized for V8 implementation and five-stock validation.

Versioning note: V7 is now closed. This document preserves the approved feature design, but all implementation described here targets V8. References to V7 calculations mean the frozen baseline behavior that V8 must inherit and regression-test.

## Final User-Facing Contract

The user should need only two columns:

```text
Score
Score_Message
```

`Score` is the single action value.

`Score_Message` is one user-facing string that explains the score using post-processor context. Its wording will be driven by a configurable lookup table so it can be refined without changing indicator or beta calculations.

The post-processors do not create another action score and do not bias, add to, subtract from, or replace `Score` in their first releases.

Detailed beta and API fields may be written to backtest/audit outputs, but the only new production column required for the user is `Score_Message`.

## Production Trigger

Post-processing starts only after the engine has finalized the semantic Active Momentum decision:

```text
if (
    Final_Decision == MOMENTUM_ACTIVE
    and Score >= CONFIRMED_ENTRY_MIN_SCORE
):
    run approved post-processors
```

The current programmed Active baseline is `85`. Post-processors reference `CONFIRMED_ENTRY_MIN_SCORE`; they do not maintain an independent hard-coded threshold.

This trigger uses `Score` alone because `Score` is the user's authoritative action column. Under the V7 output contract:

```text
MOMENTUM_PRESENT_WAIT_CONFIRMATION <= 84
REJECT < the normal output threshold
```

`Final_Decision` is the internal semantic trigger because it confirms that the score and every other Active Momentum gate passed. It remains an audit field rather than a second user action value.

Required invariant test:

```text
Score >= 85  =>  Final_Decision == MOMENTUM_ACTIVE
```

If that invariant fails, the row is logged as a contract error and post-processing is skipped until the core result is reconciled.

The CLI display controls `--score-y` and `--count-x` do not control post-processing. They may hide or show rows in the final summary, but they cannot enable or suppress Beta/ETF processing.

## Approved Release Order

### Release 1: Beta post-processor — retired

The Beta pilot is preserved for audit, but no further Beta calculation, validation, messaging, or production work is permitted.

### Release 2: Mapped ETF extraction

ETF mapping proceeds by explicit user authorization dated 2026-07-11. Beta signoff is no longer a prerequisite.

There will be no pan-ETF holdings scan in the live momentum workflow.

## Shared Post-Processor Boundary

Create one coordinator outside the base indicator/scoring functions:

```text
Momentum_Active_PostProcessor.py
```

Conceptual interface:

```python
post_process_score_context(
    score,
    ticker,
    stock_daily_df,
    benchmark_daily_df,
    engine_output,
    enabled_processors,
    config,
) -> str
```

The returned string becomes `Score_Message`.

Current enabled processor sequence:

```text
1. ETFMappingProcessor
```

Each processor returns structured rule codes and template parameters internally. The message builder converts those codes into one user-facing string.

Failure rules:

- Preserve `Score` unchanged.
- Return an explicit context-unavailable message when appropriate.
- Never turn a post-processor API/calculation failure into a core momentum rejection.
- Log technical details separately from the user-facing message.

## Message Lookup Table

Create a versioned mapping file:

```text
config/Post_Processor_Message_Map.csv
```

Proposed columns:

```text
Processor
Rule_Code
Priority
Template
Enabled
Version
```

Example initial beta rules:

```text
BETA_UNAVAILABLE
BETA_DEFENSIVE_STOCK_SPECIFIC
BETA_BALANCED_CONFIRMED
BETA_HIGH_CONFIRMED
BETA_HIGH_MARKET_DEPENDENT
BETA_VERY_HIGH_SENSITIVITY
BETA_WEAK_FIT
```

Example future ETF rules:

```text
ETF_TOP10_MAPPED
ETF_NO_TOP10_MAPPING
ETF_MAPPING_PARTIAL
ETF_API_UNAVAILABLE
ETF_RESPONSE_STALE
```

The templates can reference calculated values:

```text
{ticker}
{score}
{beta}
{beta_r2}
{beta_band}
{residual_momentum_126d}
{benchmark}
{allocation_context}
{mapped_etf_codes}
```

Illustrative Release 1 message:

```text
Active momentum confirmed at Score 92. Beta 1.38 vs SPY with moderate benchmark fit; momentum is market-sensitive but residual momentum remains positive. Use the configured reduced/standard risk-budget guidance and confirm broad-market strength.
```

Illustrative Release 2 message extension:

```text
Top-10 ETF mappings: SMH 17.75%, SOXX 8.40%, QQQ 7.58%.
```

The exact wording is not locked by this plan. Calculation outputs and stable rule codes are locked first; user-facing language can then be tuned in the lookup table.

## Release 1: Beta Post-Processor

### Purpose

Beta explains how the already-active momentum should be interpreted and used. It does not make the core momentum score larger merely because the stock is high beta.

Initial context includes:

- Broad-market sensitivity.
- Strength of the beta relationship through R-squared.
- Stock-specific versus benchmark-driven momentum.
- Broad/sector regime confirmation where data is available.
- Qualitative risk-budget wording inside `Score_Message`.

### Combined Beta Inputs

| Input | Source | Purpose |
|---|---|---|
| Final `Score` | V7 output | Trigger at `>= 85` |
| Ticker | V7 | Audit/message parameter |
| Stock daily OHLCV | Existing V7 in-memory data | Return and beta calculation |
| Broad benchmark OHLCV | Existing V7 benchmark cache | Market beta and residual return |
| Exchange profile | V7 | Select US/NSE benchmark behavior |
| Sector/industry | StockCodeMaster | Optional sector benchmark selection |
| Existing indicator values | V7 output row | Initial message-rule inputs |
| Message map | Versioned config | Convert rule codes into text |

No additional network request is needed for the broad beta calculation because the stock and benchmark histories are already present in the scan.

### Calculation Specification

Use aligned daily percentage returns:

```text
stock_return = alpha + beta * benchmark_return + residual
```

Initial specification:

```text
Estimation window: 252 aligned daily returns
Target observations: 252
Minimum observations: 200
Outputs: Beta, Alpha, R-squared, observations, residual returns
```

The separately diagnosed `MIN_HISTORY_BARS = 300` check must be enforced before Beta Release 1 is enabled.

### Residual momentum

Preferred implementation:

1. Fit the regression using only data available through the signal date.
2. Calculate daily residual returns.
3. Compound residual returns over 63 and 126 trading days.

Audit approximation:

```text
Beta_Adjusted_RS_126D = Stock_Return_126D - Beta_252D * Benchmark_Return_126D
```

The compounded regression residual is the preferred research feature; the approximation is retained only for interpretation and auditing.

### Provisional beta bands

These bands are backtest hypotheses, not approved behavior:

| Beta | Rule family | Initial interpretation |
|---:|---|---|
| `< 0.75` | `DEFENSIVE` | Low market sensitivity; strong residual momentum may be high-quality stock-specific momentum |
| `0.75-1.25` | `BALANCED` | Normal market sensitivity |
| `1.25-1.75` | `HIGH_SENSITIVITY` | More market-dependent; risk-budget wording requires validation |
| `> 1.75` | `VERY_HIGH_SENSITIVITY` | High reversal exposure; conservative wording unless evidence supports otherwise |

`Beta_R2_252D` must accompany beta. A large beta with weak R-squared is not reliable evidence of consistent market amplification.

### Beta audit/backtest fields

These fields are for validation and diagnostics. They do not all need to become production user columns:

```text
Beta_Status
Beta_Benchmark
Beta_252D
Beta_R2_252D
Beta_Observations
Beta_As_Of_Date
Beta_Risk_Band
Residual_Momentum_63D_Pct
Residual_Momentum_126D_Pct
Beta_Adjusted_RS_126D_Pct
Broad_Market_Trend_Status
Sector_Benchmark
Sector_Beta_252D
Sector_Trend_Status
Allocation_Context_Code
Beta_Message_Rule_Code
```

### Full Beta backtest

#### Baseline freeze

1. Freeze the V7 scoring/output configuration.
2. Reproduce the existing active-signal baseline.
3. Enforce the 300-bar history rule as a separately reviewed prerequisite.
4. Confirm Beta informational mode never changes `Score`.

#### Point-in-time calculation

For every historical row whose finalized V7 score is `>= 85`:

1. Use data available only through the signal date.
2. Calculate beta, R-squared, residual momentum, beta band, and market regime.
3. Record forward returns at D+1, D+2, 5, 10, 21, 63, and 126 trading days.
4. Record maximum adverse/favorable excursion and drawdown.
5. Stratify by beta band, R-squared, sector, ATR, market cap, and market regime.

Use chronological walk-forward validation, not a random train/test split.

Candidate message/allocation policies:

```text
P0: Baseline V7; no beta context
P1: Beta information only
P2: Beta plus residual-momentum context
P3: Beta-sensitive qualitative risk-budget wording
P4: High-beta context conditioned on broad/sector market regime
```

#### Signoff requirements

Release 1 cannot be enabled until:

- Formula/unit tests pass.
- No-look-ahead audit passes.
- The score-invariance test passes.
- Target sample size is at least 50 signals per proposed beta band, or the band is marked inconclusive.
- Results are stable across multiple chronological windows and major sectors.
- Any allocation wording is supported by downside/risk-adjusted results and not only average return.
- Sample messages are reviewed and approved.

If predictive evidence is weak, Beta Release 1 remains factual/informational in `Score_Message`.

## Release 2: Direct Stock-to-ETF Mapping

### Required behavior

ETF mapping is called only for a finalized `MOMENTUM_ACTIVE` stock meeting `CONFIRMED_ENTRY_MIN_SCORE`.

Required user-facing function:

```python
getETFMappedCodes(stock_code) -> str
```

Example return value:

```text
SMH 17.75%; SOXX 8.40%; QQQ 7.58%
```

Only USA-listed ETF codes are eligible.

Only ETFs where the identified stock is within that ETF's top ten holdings are eligible.

Return at most the top three eligible ETFs. If weight is unavailable, return ETF codes without fabricated percentages and state that weights are unavailable.

### Explicitly prohibited live workflow

The production workflow must not:

- Download a pan-US ETF list and loop over it.
- Call Yahoo/yfinance once per ETF.
- Inspect every ETF's holdings to reverse-map one stock.
- Add a multi-minute ETF discovery stage after finding an active stock.

This prohibition applies even if calls are parallelized. The design requirement is a direct reverse lookup, not a faster universe scan.

### Direct API candidate

Financial Modeling Prep currently documents a direct reverse endpoint:

```text
GET https://financialmodelingprep.com/stable/etf/asset-exposure?symbol=AAPL
```

Official documentation:

```text
https://site.financialmodelingprep.com/developer/docs/stable/etf-asset-exposure
```

The documentation says the response identifies ETFs holding a stock and includes weight percentage, shares, and market value. This matches the required single-stock reverse-lookup direction.

FMP is a candidate, not yet an approved dependency. A proof-of-concept must verify:

- API plan/entitlement and cost.
- Authentication and rate limits.
- Response schema stability.
- US ETF listing/exchange metadata.
- Holdings freshness/as-of date.
- Whether the stock's rank within each ETF is returned.
- Whether a top-ten flag/rank can be established without per-ETF follow-up calls.
- Response completeness and accuracy against a manual sample.
- Response time under realistic active-stock usage.

If the endpoint cannot directly prove that the stock is a top-ten holding inside each returned ETF, it does not satisfy Release 2 by itself. The engine will not fall back to a pan-ETF scan.

### ETF combined inputs

| Input | Source | Purpose |
|---|---|---|
| Final `Score` | V7 | Trigger at `>= 85` |
| Stock code | V7 | Direct reverse API parameter |
| US ETF ticker set | Local StockCodeMaster reference | Filter response to USA-listed ETFs without network loops |
| Direct exposure response | Approved API | ETF code, weight, rank/top-ten evidence, freshness |
| Message map | Versioned config | Convert results into `Score_Message` text |

### Sorting interpretation

The highest stock weight in an ETF is the strongest exposure and should appear first.

Implementation order:

```text
Holding_Weight_Pct DESC
Exposure_Rank ASC (1, 2, 3)
ETF_Ticker ASC as deterministic tie-breaker
```

This interprets the requested ascending sort as ascending exposure rank while preserving the earlier requirement that the highest-percentage ETF appears first.

### Speed and freshness contract

- One direct reverse-lookup request per active stock is the target.
- No request is made below Score 85.
- Cache successful results by stock code with an as-of timestamp and configurable TTL.
- Use a short bounded timeout and fail open into `Score_Message`.
- API errors must not change `Score`.
- Record request start/end time and provider data date.
- The proof-of-concept must report median and 95th-percentile latency.
- Any provider requiring per-ETF follow-up calls is rejected for the initial release.

Because the call is direct and bounded, ETF extraction should add seconds at most rather than a multi-minute universe scan. Exact latency limits will be approved after the provider proof-of-concept.

### ETF validation and signoff

Release 2 requires:

- API contract tests using several large, mid-cap, and less widely held US stocks.
- Manual comparison of returned top-ten membership and weights against issuer/TradingView views.
- Confirmation that non-US ETFs are removed.
- Confirmation that top-three order is correct.
- Missing-weight and stale-data behavior tests.
- Cache and timeout tests.
- Proof that no yfinance ETF-universe loop is reachable.
- Sample `Score_Message` strings approved by the user.

ETF trend verification is not part of the first mapping deliverable. It may be added after the direct mapping API is stable and its runtime is known.

## Combined Production Message Evolution

### After Beta Release 1

```text
Score = 92
Score_Message = <Beta-derived explanation from lookup table>
```

### After ETF Release 2

```text
Score = 92
Score_Message = <Beta explanation> | Top-10 ETF mappings: SMH 17.75%; SOXX 8.40%; QQQ 7.58%.
```

The user still acts on one numeric field: `Score`.

## Integration Tests

```text
WAIT/REJECT at any Score -> no post-processor call
MOMENTUM_ACTIVE at programmed threshold -> Beta called once
Score at/above threshold with Final_Decision not active -> no Beta call; contract audit if the score cap invariant is violated
Changing --score-y/--count-x -> no change to post-processor calls
Beta failure -> Score unchanged; context-unavailable string
Message template changed -> calculation output unchanged
ETF Release disabled -> no ETF API request
ETF Release enabled, Score 84 -> no ETF API request
ETF Release enabled, Score 85 -> one direct stock exposure request
ETF result includes non-US fund -> filtered locally
ETF result cannot prove top-ten rank -> excluded/unsupported, no universe scan fallback
Weight available -> top three ordered by weight descending
Weight unavailable -> codes returned without fabricated weights
Any post-processor failure -> Score byte-for-byte unchanged
```

## Revised Implementation Phases

### Phase 0: Core prerequisites

- Enforce the existing 300-bar minimum-history intent.
- Resolve the pandas `pct_change` warnings with explicit missing-value semantics.
- Freeze V7 score contract fixtures.
- Add the programmed-threshold/active-decision invariant test.
- Create the message-template schema.

### Phase 1A: Beta research implementation

- Implement beta, R-squared, and residual-momentum calculations outside core scoring.
- Add unit and no-look-ahead tests.
- Produce historical signal-level audit output.

### Phase 1B: Beta backtest and review

- Run the full chronological backtest.
- Compare the proposed message/allocation-context policies.
- Deliver backtest summary, downside analysis, and sample messages.
- Stop for user review and Beta signoff.

### Phase 1C: Beta production release

- Enable Beta only for finalized Score `>= 85`.
- Populate the single `Score_Message` column.
- Keep Beta behind a feature flag.

### Phase 2A: ETF API identification

- Test the FMP direct reverse endpoint and any other direct candidates.
- Reject any design requiring an ETF-universe scan.
- Select a provider only after top-ten membership, US listing, latency, freshness, and licensing are verified.

### Phase 2B: ETF mapping implementation

- Implement `getETFMappedCodes(stock_code)`.
- Add local US ETF filtering, caching, timeouts, sorting, and message rules.
- Run API contract and data-quality tests.
- Stop for user review and ETF signoff.

### Phase 2C: Combined production release

- Append the approved ETF string to `Score_Message` for Score `>= 85` only.
- Preserve Score and Beta behavior unchanged.
- Monitor API latency and failures.

## Planned Deliverables

### Beta track

```text
Momentum_Active_PostProcessor.py
Beta_Context.py
config/Post_Processor_Message_Map.csv
tests/test_beta_context.py
tests/test_active_postprocessor.py
backtests/V7_Beta_Active_Signal_Audit_<timestamp>.csv
backtests/V7_Beta_Policy_Summary_<timestamp>.csv
docs/V7_BETA_BACKTEST_SIGNOFF_<date>.md
```

### ETF track after Beta signoff

```text
ETF_Context.py
tests/test_etf_context.py
backtests/V7_ETF_API_QUALITY_<timestamp>.csv
docs/V7_ETF_API_SELECTION_AND_SIGNOFF_<date>.md
```

Only this revised plan document is part of the current task.

## Decisions Recorded From User Review

1. `Score` is the single action column.
2. Post-processing begins only for finalized `MOMENTUM_ACTIVE` rows meeting the programmed `CONFIRMED_ENTRY_MIN_SCORE`; CLI filters are unrelated.
3. One additional user-facing string column, `Score_Message`, explains the score.
4. Message wording comes from a configurable lookup table.
5. Beta is Release 1 and requires full backtesting and signoff.
6. ETF mapping is Release 2 after direct API identification.
7. No pan-ETF Yahoo/yfinance holdings scan is permitted.
8. ETF output is restricted to USA-listed ETFs where the stock is a top-ten holding.
9. Return at most three ETF codes, ordered by highest available holding weight first.
10. Post-processors do not change the core Score in their initial releases.

## Research Basis

- Residual momentum separates stock-specific momentum from common factor exposures: https://repub.eur.nl/pub/22252
- High beta is not automatically higher risk-adjusted confidence: https://www.nber.org/papers/w16601
- Momentum risk is regime-dependent and can reverse sharply in stressed/rebound states: https://www.kentdaniel.net/papers/published/jfe_16.pdf
