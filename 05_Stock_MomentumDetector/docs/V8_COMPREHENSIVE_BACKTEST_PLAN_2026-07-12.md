# V8 Comprehensive Momentum and ETF Backtesting Plan

> **HISTORICAL TEST PLAN.** New V8 design and validation are governed by `docs/V8_REVISED_DEVELOPMENT_CHARTER_2026-07-13.md` and `docs/MOMENTUM_ENGINE_FOUNDATIONAL_DESIGN_STANDARD_2026-07-13.md`. Any ETF return-comparison work in this older plan is not an active signal-design requirement; ETF mapping is informational and non-scoring.

Date: 2026-07-12

Status: The original 10-stock Q2 run and the subsequent enforced-Foundation 20-stock/four-date Q2 run are complete. Both passed integrity validation. The later run improved D+1 Active evidence but remains a single-quarter technology sample; multi-regime execution and operational signoff remain pending.

Executed technical sample:

```text
backtests/V8_Comprehensive/runs/V8FULL_20260711T192053Z_ffe1567_20260712
docs/V8_COMPREHENSIVE_BACKTEST_CONCLUSION_2026-07-12.md
```

The executed sample does not satisfy this plan's broad evidence targets and does not authorize V8 operational activation.

Directional persistence addendum executed after user clarification:

```text
Primary: D+1 Close > D Close
Reference: D+5 and D+8 Close versus D Close
Run: backtests/V8_Directional_Persistence/runs/V8DIR_20260711T193832Z_0568444
Conclusion: docs/V8_DIRECTIONAL_PERSISTENCE_CONCLUSION_2026-07-12.md
```

This D+1 primary contract supersedes the earlier use of 21-day benchmark-adjusted return as the immediate validation gate. Longer horizons remain secondary stability and research references.

Alternate-code execution:

```text
XOM replaced by PANW
Comprehensive run: backtests/V8_Comprehensive/runs/V8FULL_20260711T194644Z_3ed85d1_20260713
Directional run: backtests/V8_Directional_Persistence/runs/V8DIR_20260711T195008Z_3ed85d1
Conclusion: docs/V8_ALT_CODES_DIRECTIONAL_CONCLUSION_2026-07-12.md
```

PANW passed D+1/D+5/D+8 after its first Active signal but exposed a potential confirmation lag that requires a separate false-negative study before gate changes.

MACD configuration study:

```text
Run: backtests/V8_MACD_Research/runs/V8MACD_20260712T072722Z_1f1ac52
Conclusion: docs/V8_MACD_RESEARCH_CONCLUSION_2026-07-12.md
Lineage: docs/V1_V8_EMA200_MACD_FOUNDATION_DISCOVERY_2026-07-12.md
```

The first comparison tested standard `12/26/9` and four Fibonacci variants. `8/21/5` improved D+1 detection but did not dominate longer persistence. Following explicit user approval, `8/21/5` is now the enforced development-line Foundation default. It adds no score points; multi-regime and holdout validation remain required for operational signoff.

## 20-Stock Foundation Execution Update

The approved follow-on execution is frozen at:

```text
backtests/V8_Foundation_Validation/runs/V8FOUND_20260712T182945Z_cf0c908
```

It covers 20 technology stocks, four predeclared dates (`2026-04-08`, `2026-04-30`, `2026-05-07`, `2026-06-09`), MACD `8/21/5`, D+1/D+5/D+8 outcomes, audit-versus-enforce regression, and strict same-quarter acceptance of independently dated ETF holdings. The independent validator recomputed all 80 rows and passed checksums.

This execution satisfies a focused implementation and directional validation phase. It does not satisfy the plan's multi-regime, final-test, ticker-holdout, delisted-universe, or prospective ETF requirements.

## Objective

Determine whether the complete V8 Stock Momentum Detector is reproducible, free of look-ahead bias, operationally reliable, and supported by out-of-sample evidence before it replaces V7.

The study must validate two distinct contracts:

1. The V8 momentum engine identifies useful, actionable `MOMENTUM_ACTIVE` episodes.
2. The ETF post-processor provides accurate, timely, informational ETF context without changing the stock signal, `Score`, or decision.

V7 remains the operational baseline throughout this work.

## Existing Evidence and Remaining Gap

Completed evidence:

- V8 was forked from corrected V7 commit `9a4b0ba`.
- Five ETF unit tests passed.
- The canonical five-stock ETF run returned 13 mappings; all 13 passed separate top-ten rank and freshness validation.
- ETF processing preserved `Score` and used one stock-specific production request per eligible stock.
- The Beta pilot was completed, found inconclusive, closed, and removed from the active V8 path.

This is not yet a comprehensive backtest. The missing evidence is:

- Deterministic point-in-time replay of finalized V8 decisions over a broad stock universe.
- Chronological development, validation, and untouched final-test results.
- Independent momentum episodes rather than repeated daily observations from the same trend.
- Forward return, excess return, drawdown, continuation, and robustness analysis.
- Comparison with V7, matched WAIT controls, benchmarks, sectors, regimes, and cost scenarios.
- Reproducible offline artifacts and an independent validator.
- Point-in-time or prospective evidence for ETF mappings attached to V8 signals.

## Non-Negotiable Contracts

The backtest cannot change the active V8 production contract:

```text
0 <= Score <= 100
MOMENTUM_PRESENT_WAIT_CONFIRMATION Score <= 84
REJECT Score <= 49
ETF processing never changes Score, component scores, decisions, or ranks
--score-y and --count-x affect only final-summary presentation
Beta remains absent from active V8
```

The production ETF trigger remains:

```text
Final_Decision == MOMENTUM_ACTIVE
AND
Score >= CONFIRMED_ENTRY_MIN_SCORE
```

The current programmed threshold is `85`.

## Study Boundaries

### Primary study

The primary study evaluates signal quality. V8 does not currently define a complete portfolio-sizing and exit policy, so the backtest must not present an invented trading policy as the production strategy.

Primary evaluation uses fixed forward horizons from the next tradable session open. A separate research-only trade simulation may test mechanical exits, but it must be labeled `ILLUSTRATIVE_POLICY` and cannot become operational without a separate policy decision.

### Historical replay mode

The primary historical mode is:

```text
Historical_Replay_Mode = DAILY_EOD
Decision_Information_Cutoff = signal-date market close
Entry_Reference = next eligible trading session open
```

V8 also uses live quotes and hourly timing in production. Those inputs cannot be inferred from daily bars. Daily replay must use an explicit, deterministic timing policy and report:

```text
Intraday_Replay_Status = UNAVAILABLE | ARCHIVED_DATA_AVAILABLE
Live_Quote_Replay_Status = UNAVAILABLE | ARCHIVED_DATA_AVAILABLE
```

Daily-only results cannot be represented as proof of exact historical live decisions. Archived intraday/live data is not required for the D+1/D+5/D+8 outcome test because intraday movement is not the engine's intended holding horizon. It is relevant only if exact historical reproduction of live timing downgrades is separately required.

## Research Questions

The final package must answer:

1. Do independent V8 Active episodes produce positive benchmark-relative returns after the next open?
2. Does V8 outperform matched WAIT controls and the frozen V7 baseline out of sample?
3. Are results stable across time, sector, market-cap, volatility, exchange, and market regime?
4. What are the continuation rate, adverse excursion, favorable excursion, and drawdown after a signal?
5. Are results concentrated in a few tickers or episodes?
6. How sensitive are conclusions to costs, signal spacing, and the D+5/D+8 persistence horizon?
7. Does the ETF feature consistently return valid current mappings for eligible signals without affecting the stock result?
8. Where point-in-time ETF evidence exists, what happens to the mapped ETFs after the stock signal?
9. What limitations prevent stronger claims or operational activation?

## Populations and Units of Analysis

### Active population

```text
Final_Decision == MOMENTUM_ACTIVE
AND Score >= 85
```

### WAIT control population

```text
Final_Decision == MOMENTUM_PRESENT_WAIT_CONFIRMATION
AND 75 <= Score <= 84
```

Controls must be matched without using forward outcomes. Matching variables should include signal month, sector, market-cap band, ATR band, exchange profile, and market regime.

### V7 regression population

Replay the frozen V7 and V8 engines from identical inputs. Store decision, score, and component-level differences for every eligible date. Expected fork differences must be separated from unexplained regressions.

### Independent momentum episode

The primary unit is an episode, not every active day.

An episode begins when:

```text
today is MOMENTUM_ACTIVE
AND the prior eligible session was not MOMENTUM_ACTIVE
```

No second primary episode is counted for the same ticker until it exits Active and remains non-Active for at least 21 trading sessions. Continuous Active trends may have secondary 21-session snapshots, labeled `SECONDARY_SNAPSHOT` and excluded from primary inference.

## Point-in-Time and No-Look-Ahead Rules

At signal date `D`, every decision input must be dated `<= D`. Forward prices and outcomes are attached only after the signal record and sample membership are frozen.

Mandatory rules:

- Indicator windows are sliced at `D`; the runner cannot calculate on the full frame and accidentally expose future rows to a decision helper.
- Missing returns use explicit no-fill semantics.
- Adjusted and unadjusted prices are stored with the chosen corporate-action policy documented.
- The universe, classifications, benchmark data, and configuration are frozen per run.
- Samples and matched controls are selected without forward outcome fields.
- Near-cutoff signals remain in the audit with unavailable horizons; outcomes are never imputed.
- Delisted, acquired, renamed, and failed-download securities are retained or reported as explicit exclusions.
- Full-period quantiles cannot define a point-in-time regime or threshold.

Changing any data after `D` must not change the signal at `D`.

## Universe and Input Data

### Universe hierarchy

Preferred evidence uses a survivorship-aware, point-in-time US common-stock universe that includes delisted securities. If that dataset is unavailable, use the frozen current StockCodeMaster universe but label the entire run:

```text
Survivorship_Bias_Status = CURRENT_UNIVERSE_LIMITATION
```

No broad market-wide claim may be made from a current-universe-only run without this limitation.

Primary eligibility:

- Supported US common stock and exchange profile.
- At least `MIN_HISTORY_BARS` before the candidate date.
- Valid daily OHLCV and benchmark history.
- Liquidity eligibility according to the frozen V8 engine.
- Sector and industry from the point-in-time source when available; otherwise `UNKNOWN`.

All exclusions go to `universe_exclusions.csv` with a reason and source row.

### Frozen market data

Acquire inputs once, then run all replay and validation offline.

Required stock and benchmark fields:

```text
Date
Open
High
Low
Close
Adjusted_Close
Volume
Dividends
Stock_Splits
Source
Retrieved_UTC
```

The cutoff is the last fully completed trading session before acquisition. Partial current-day bars are prohibited.

Benchmarks:

- Primary US benchmark: `SPY`.
- Growth sensitivity: `QQQ`.
- Sector sensitivity: the applicable liquid sector ETF when the mapping is frozen before holdout review.
- Cash reference: a frozen risk-free series when available; otherwise report that risk-adjusted cash comparisons are unavailable.

## Chronological Design

Use the following default partitions, subject only to documented data availability:

```text
Development: earliest eligible signal through 2022-12-31
Validation:  2023-01-01 through 2024-12-31
Final test:  2025-01-01 through the frozen data cutoff
```

Warm-up history may precede the development start. Configuration, endpoints, matching policy, and reporting code must be frozen before final-test results are opened.

Also create a deterministic ticker holdout so the same company does not appear in development and ticker-holdout evidence:

```text
Development tickers: 70%
Validation tickers:  15%
Holdout tickers:     15%
Seed:                20260712
```

Stratify where feasible by sector and market-cap band. Store the split before computing outcomes.

## Momentum Outcome Contract

### Primary endpoint

```text
Primary_Endpoint = D1_Close_Above_D_Close
D1_Audit_Prices = D_Close, D1_Open, D1_Close
Primary_Pass = D1_Close > D_Close
```

D+1 Open-to-Close movement is diagnostic only. It does not replace comparison with the signal-day Close.

Primary persistence references:

```text
D5_Close_Above_D_Close
D8_Close_Above_D_Close
```

The 21-day benchmark-adjusted outcome remains a secondary longer-horizon research measure.

### Secondary endpoints

```text
Forward_1D_Return_Pct
Forward_2D_Return_Pct
Forward_5D_Return_Pct
Forward_10D_Return_Pct
Forward_21D_Return_Pct
Forward_63D_Return_Pct
Forward_126D_Return_Pct
Benchmark_Adjusted_5D/21D/63D/126D_Return_Pct
Sector_Adjusted_21D/63D_Return_Pct, when available
Positive_5D/21D/63D
D1_Close_Above_D_Close
D2_Close_Above_D_Close
Continuation_By_D2
MAE_5D/21D/63D_Pct
MFE_5D/21D/63D_Pct
Max_Drawdown_21D/63D_Pct
Realized_Volatility_21D/63D
```

Store the raw signal close, next open, horizon closes, interval highs/lows, and benchmark prices used to calculate every outcome.

### Cost and execution sensitivity

Report fixed-horizon results under round-trip cost assumptions of:

```text
0 bps
20 bps
50 bps
100 bps
```

Costs combine slippage and fees and are sensitivity scenarios, not claims about a particular broker. Flag next-open gaps and test volume participation only if position sizing is later introduced.

### Optional illustrative policy

Any stop, trailing-stop, or maximum-hold simulation must be configured separately and labeled `ILLUSTRATIVE_POLICY`. Its rules, same-bar stop ordering, gap fills, cooldown, and position overlap policy must be fixed before validation. It is secondary to fixed-horizon signal-quality results.

## Regime and Robustness Analysis

Report primary and secondary outcomes by:

- Development, validation, final-test, and ticker-holdout partitions.
- Calendar year and rolling 12-month cohort.
- Bull, bear, and transitional SPY regime defined only from information available at `D`.
- Low, medium, and high point-in-time market volatility.
- Sector, sufficiently populated industry, market-cap band, and exchange profile.
- Score bands `85-89`, `90-94`, and `95-100`.
- ATR, relative-volume, and gap-at-entry bands.
- First Active episode versus secondary snapshots.
- Data-vendor availability and replay-quality status.

Sensitivity runs must include:

- Episode reset windows of 10, 21, and 42 sessions.
- SPY and QQQ benchmark alternatives.
- Adjusted-price policy checks.
- Daily-EOD replay results with the historical live-timing limitation labeled explicitly but not treated as the outcome target.
- Equal-weight ticker aggregation so prolific tickers cannot dominate.
- Leave-one-sector-out, leave-one-year-out, and leave-top-five-tickers-out summaries.

## Statistical Reporting

For each primary group report:

```text
Episodes
Unique_Tickers
Mean
Median
Standard_Deviation
25th/75th_Percentile
Positive_Rate
Bootstrap_95_Pct_Confidence_Interval
Median_MAE
Median_MFE
Median_Max_Drawdown
```

Use both episode-level and ticker-clustered bootstrap intervals. Report effect sizes and uncertainty, not p-values alone. Correct exploratory sector/industry comparisons for multiple testing or label them descriptive.

Required comparisons:

- V8 Active versus SPY and QQQ.
- V8 Active versus matched V8 WAIT controls.
- V8 versus frozen V7 on identical dates and inputs.
- V8 score-band monotonicity.
- Final test versus development and validation direction.

## Predeclared Evidence Classification

Integrity gates are mandatory and independent of profitability.

Classify the primary 21-day final-test result as:

- `SUPPORTED`: median benchmark-adjusted return is positive, its ticker-clustered bootstrap interval is above zero, the net result remains positive at 50 bps round trip, and the result is not reversed by leave-one-year/sector/top-five-tickers-out checks.
- `PROMISING_BUT_INCONCLUSIVE`: the final-test point estimate is positive but its interval includes zero or a robustness check is mixed.
- `NOT_SUPPORTED`: the final-test point estimate is non-positive, Active materially underperforms matched WAIT, or results depend on a small concentration of observations.
- `INSUFFICIENT_SAMPLE`: the evidence cannot support a conclusion because episode or ticker coverage is inadequate.

This classification validates the signal contract; it does not promise future returns.

Coverage targets for a broad claim are at least 300 independent Active episodes, 200 unique tickers, and 50 Active episodes in the final-test partition. Shortfalls must be reported and classified as limited evidence rather than filled with repeated daily observations.

## ETF Backtesting Contract

ETF context is informational and must be assessed separately from momentum signal quality.

### Track A: production-path functional validation

Expand the completed five-stock test to a frozen, sector-stratified sample of eligible current Active signals and controlled fixtures.

Measure:

- Exactly one reverse-source request per uncached eligible stock.
- Zero requests for WAIT and REJECT rows.
- Cache hit, TTL expiry, timeout, HTTP failure, malformed schema, and partial-response behavior.
- US whitelist and leveraged/inverse exclusions.
- Strict `weight > 100/11` proof.
- Top-three ordering and deterministic tie-breaking.
- Message-map behavior and `Score` byte invariance.
- Mapping coverage, omission reasons, latency, and provider error rate.
- Independent holdings-page rank and freshness confirmation for every displayed mapping.

Technical acceptance requires zero score/decision mutations and 100% independent rank confirmation for displayed mappings in the reviewed validation sample.

### Track B: point-in-time historical ETF cohort

The current TradingView reverse page does not provide historical holdings as of an old stock signal. A current ETF mapping must never be attached retrospectively to a historical signal.

A historical stock-to-ETF pair is eligible only when evidence frozen at the signal date proves:

```text
Mapping_Retrieved_UTC <= signal decision cutoff
Holdings_As_Of_Date <= Signal_Date
Freshness_Age_Days <= approved limit
Stock was independently top ten at that as-of date
ETF was US-listed and non-leveraged at that date
```

If an entitled historical source is unavailable, write:

```text
ETF_Historical_Status = NOT_POINT_IN_TIME_ELIGIBLE
```

and do not calculate a historical ETF result for that signal.

For eligible point-in-time pairs, report ETF forward returns from the next open at 5, 21, and 63 sessions, ETF excess return versus SPY, stock-minus-ETF return, ETF drawdown, tracking relationship, and mapping rank/freshness. These are descriptive because V8 does not recommend replacing the stock with an ETF or changing allocation.

### Track C: prospective ETF shadow cohort

Unless adequate historical holdings are licensed, prospective shadow collection is the authoritative combined V8+ETF test.

For every live eligible V8 signal:

1. Freeze the stock output before ETF processing.
2. Save the reverse-page response, hash, URL, retrieval time, and parsed rows.
3. Save the independent ETF holdings evidence, rank, weight, and as-of date.
4. Preserve the local stock and ETF master snapshots.
5. Track stock and displayed ETF outcomes for 5, 21, and 63 sessions.
6. Never modify the original mapping after later provider changes; append correction records instead.

The prospective cohort needs at least 50 eligible stock signals and 100 verified displayed mappings, or six months of collection, whichever occurs first, before a broad reliability conclusion. Operational functional signoff may occur earlier only if explicitly separated from forward-performance claims.

## Implementation Components

Planned files:

```text
Backtest_Momentum_Detector_V8.py
Replay_Momentum_Detector_V8.py
Validate_Momentum_Detector_V8_Backtest.py
config/V8_Comprehensive_Backtest_Config.json
tests/test_v8_historical_replay.py
tests/test_v8_backtest_contract.py
tests/test_v8_no_lookahead.py
tests/test_v8_etf_point_in_time.py
```

Reuse `ETF_Context_V8.py` and `Backtest_Momentum_Detector_V8_ETF.py` only through reviewed interfaces. Do not add research-only holdings calls to the production engine.

The historical runner should call pure V8 calculation/decision functions against date-sliced data. If safe replay requires extracting shared pure functions, preserve production behavior with regression tests before running research.

## Required Tests

### Engine and replay

- Full score range and decision caps.
- Exact Active threshold boundary at 84/85.
- All confirmed-entry gates at pass/fail boundaries.
- Deterministic output for identical frozen inputs.
- Future-price mutation cannot change a prior signal.
- Final-summary CLI filters cannot change the audit population.
- V7/V8 regression differences are fully enumerated.
- Daily replay limitation flags are always populated.

### Outcomes

- Next-open entry and each horizon use the correct trading-session index.
- Splits/dividends follow the documented price policy.
- MAE/MFE use only the post-entry window.
- Missing horizons remain missing.
- Benchmark alignment uses common valid sessions without forward fill across missing dates.

### Sampling and statistics

- Same seed and input hashes reproduce ticker splits, samples, and controls.
- Forward fields cannot affect sample membership.
- Episode deduplication prevents overlapping primary episodes.
- Cluster bootstrap resamples tickers, not individual rows only.

### ETF

- All existing ETF unit tests remain green.
- Production request count and no-call controls.
- Cache corruption, expiry, and concurrency-safe behavior.
- Timeout and schema failure leave Score unchanged.
- Historical mapping is rejected without point-in-time evidence.
- Prospective snapshots are immutable and checksum-covered.

### Offline validation

- Replay succeeds with network disabled.
- Modified source, input, configuration, or output hash is detected.
- Independent validator recomputes a deterministic random sample from raw frozen prices.
- A repeated run creates a new folder and cannot overwrite the canonical run.

## Immutable Run Package

Run ID:

```text
V8FULL_<UTC timestamp>_<short commit>_<config hash>
```

Folder layout:

```text
backtests/V8_Comprehensive/runs/<RUN_ID>/
  README.md
  command.txt
  run_manifest.json
  environment.txt
  checksums.sha256
  inputs/
    universe_snapshot.csv
    universe_exclusions.csv
    ticker_split.csv
    prices/
    benchmarks/
    etf_point_in_time/
  source_snapshot/
    Momentum_Detector_V8.py
    ETF_Context_V8.py
    backtest_and_validator_files
    config/
    tests/
    working_tree.patch
  outputs/
    signal_audit.csv
    outcome_audit.csv
    matched_wait_controls.csv
    v7_v8_regression.csv
    strategy_summary.csv
    yearly_summary.csv
    regime_summary.csv
    sector_summary.csv
    robustness_summary.csv
    etf_mapping_audit.csv
    etf_forward_outcomes.csv
    download_failures.csv
  validation/
    random_sample_manifest.csv
    independently_recomputed_rows.csv
    validation_summary.csv
```

The manifest records commit, branch, clean/dirty state, source/config/input hashes, dependency versions, data cutoff, replay mode, universe limitation, partitions, seed, episode rule, endpoints, cost assumptions, row counts, exclusions, command line, and known limitations.

Large price archives may remain outside Git, but their immutable location and hashes must be recorded. Code, configuration, manifests, checksums, compact audit samples, summaries, conclusion, and handover belong in Git.

## Execution Phases and Gates

### Phase 0: freeze and design review

- Review this plan and record approval or requested changes.
- Freeze the V8 and V7 comparison commits.
- Freeze configuration, endpoints, partitions, universe source, and price policy.
- Decide whether a point-in-time/delisted-security dataset and historical ETF holdings source are available.

Gate: no code or data acquisition begins until open decisions are recorded.

### Phase 1: runner and validator implementation

- Implement deterministic daily replay, outcomes, episode logic, matched controls, artifacts, and independent validation.
- Add the required automated tests.
- Keep research network calls outside production modules.

Gate: tests, syntax checks, and static contract review pass.

### Phase 2: technical pilot

- Run 10-20 diverse tickers across bull, bear, and transitional dates.
- Inspect calculations, exclusions, replay limitations, and artifacts only.
- Do not tune thresholds from pilot forward returns.

Gate: zero unexplained score discrepancies, no look-ahead failures, offline replay success, and checksum validation.

### Phase 3: development run

- Acquire and freeze the eligible universe and price inputs.
- Run development partitions and diagnose implementation/data defects.
- Any model or rule change requires a new config version and rerun.

Gate: configuration and reporting freeze.

### Phase 4: validation run

- Open validation results.
- Compare direction, coverage, concentration, controls, V7, and cost sensitivity.
- Select no new threshold using final-test outcomes.

Gate: final-test manifest, code, and checksum set are frozen.

### Phase 5: final test and ticker holdout

- Run once using frozen code and configuration.
- Independently recompute a deterministic sample.
- Classify the result using the predeclared evidence rules.

Gate: integrity pass and signed validation report.

### Phase 6: ETF expansion and prospective shadowing

- Complete the expanded production-path ETF validation.
- Run point-in-time historical ETF analysis only where eligible.
- Start or continue the prospective shadow cohort for combined forward evidence.

Gate: no displayed mapping fails rank validation; all limitations and coverage are reported.

### Phase 7: conclusion and operational decision

Produce:

```text
docs/V8_COMPREHENSIVE_BACKTEST_CONCLUSION_<date>.md
docs/V8_OPERATIONAL_SIGNOFF_<date>.md
updated V8 handover and output contract
canonical run manifests and summaries
```

User review must explicitly decide:

- Whether V8 momentum evidence is supported, inconclusive, or not supported.
- Whether ETF functional reliability is acceptable.
- Whether prospective ETF evidence must continue before activation.
- Whether V8 replaces V7, remains development-only, or returns for revision.

## Operational Signoff Gates

V8 cannot replace V7 until all applicable gates are recorded:

- Backtest and validator code reviewed and committed.
- All mandatory tests and no-look-ahead checks pass.
- Canonical run is immutable, hashed, and reproducible offline.
- Broad-universe exclusions and survivorship limitations are quantified.
- Validation, final-test, ticker-holdout, matched-control, V7 comparison, and robustness results are reviewed.
- The primary endpoint receives an evidence classification.
- ETF score invariance and displayed-mapping rank validation pass with zero exceptions.
- Historical ETF claims use point-in-time evidence; otherwise the prospective limitation is explicit.
- Known daily-versus-live replay limitations are accepted.
- The comprehensive conclusion and output wording are approved.
- Explicit user operational signoff is committed.

Until then:

```text
V7 = OPERATIONAL BASELINE
V8 = DEVELOPMENT / COMPREHENSIVE BACKTEST PENDING
```

## Handover Checklist

The next expansion session should begin by reading:

```text
docs/V8_COMPREHENSIVE_BACKTEST_PLAN_2026-07-12.md
docs/V8_DEVELOPMENT_CHARTER_2026-07-10.md
docs/V8_CURRENT_OUTPUT_CONTRACT_2026-07-10.md
docs/V8_FINAL_HANDOVER_2026-07-12.md
docs/V8_ETF_PHASE2_CONCLUSION_2026-07-11.md
```

Before execution, record these open decisions in the run configuration:

1. Point-in-time universe/delisted-security source availability.
2. Historical intraday/live quote availability.
3. Historical point-in-time ETF holdings entitlement; if absent, use prospective shadowing.
4. Adjusted-price and corporate-action policy.
5. Exact data cutoff and benchmark sources.
6. Whether the optional illustrative exit-policy analysis is in scope.

Do not treat the existing five-stock ETF validation or retired Beta pilot as the comprehensive V8 backtest.
