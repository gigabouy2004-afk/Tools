# V7 Beta Release 1 Execution and Backtesting Plan

> **Retired on 2026-07-11.** The canonical V8 pilot did not provide sufficiently conclusive evidence that Beta reliably correlates with forward price performance after Active Momentum. The user closed and dropped this track. Do not execute the remaining stages, do not integrate Beta into production, and retain this document only as historical research design.

Date: 2026-07-10

Status: Execution plan for review. This document does not authorize Beta production deployment.

Versioning note: V7 is now closed. Release 1 implementation, backtesting code, artifacts, and signoff will be versioned as V8 work. References to historical V7 replay mean regression against the frozen V7 baseline, not modification of V7.

Parent plan:

- `docs/V7_BETA_ETF_ACTIVE_POSTPROCESSOR_PLAN_2026-07-10.md`

## Release 1 Objective

Determine whether Beta adds useful explanatory context after the V7 engine has already produced an active momentum score.

The study must answer:

1. Do stocks with different Beta values behave differently after the engine identifies `MOMENTUM_ACTIVE` under its programmed confirmation threshold?
2. Is Beta linked to actual subsequent price variation, continuation, drawdown, and realized volatility?
3. Does that relationship change by sector, industry, market-cap group, or broad-market regime?
4. Is the observed momentum primarily benchmark-driven or stock-specific residual momentum?
5. Is there enough repeatable evidence to support different `Score_Message` wording or qualitative risk-budget context?

The study will not award or remove momentum points. `Score` remains unchanged throughout Release 1 research.

## Research Contract

### Primary population

Historical signals whose finalized replay decision is:

```text
Final_Decision == MOMENTUM_ACTIVE
AND
Score >= CONFIRMED_ENTRY_MIN_SCORE
```

This is the production post-processor population.

### Diagnostic control population

A matched sample of historical rows with:

```text
75 <= Score <= 84
```

The control population is used only to understand whether Beta relationships are unique to active signals. It does not expand the production Beta trigger.

### Primary unit of analysis

Use a momentum episode rather than every qualifying day.

An episode begins when:

```text
Today's Final_Decision == MOMENTUM_ACTIVE
AND
the prior eligible trading day's Final_Decision != MOMENTUM_ACTIVE
```

If a stock remains continuously active, do not count every day as a new independent signal. Secondary snapshots may be taken every 21 trading days and must be labeled separately.

This avoids allowing a long-running trend in one stock to dominate the sample.

### Score invariance

The Beta module is forbidden from changing:

```text
Score
Final_Decision
Final_Decision_Reason
any component score
```

Every backtest run must compare baseline and Beta-enriched scoring fields byte-for-byte.

## Known Existing Backtest Gaps

`Backtest_Momentum_Detector_V6.py` is a useful reference but is not sufficient as the Release 1 runner because it:

- Imports V6 rather than V7.
- Selects long-term candidate labels instead of the finalized semantic `MOMENTUM_ACTIVE` contract.
- Assumes clean historical timing without a sufficiently explicit limitation field.
- Skips forward by 21 days after any candidate rather than defining an episode transition.
- Writes two fixed CSV files and overwrites prior runs.
- Fetches mutable online data during each replay.
- Does not store the exact ticker universe, price inputs, random seed, engine hash, or dependency versions.
- Does not calculate Beta, R-squared, residual momentum, sector/industry interactions, MAE, MFE, or realized volatility.

Release 1 therefore requires a new isolated research runner while reusing verified V7 calculations.

## Execution Components

Planned research modules:

```text
Beta_Context.py
Backtest_Momentum_Detector_V7_Beta.py
Replay_V7_Beta_Run.py
Validate_V7_Beta_Random.py
config/Beta_Release1_Config.json
tests/test_beta_context.py
tests/test_beta_backtest_contract.py
```

`Beta_Context.py` must remain independent of base score calculation.

## Phase 0: Freeze the Baseline

Before calculating Beta:

1. Review and commit the intended V7 engine baseline separately.
2. Enforce the existing 300-bar minimum-history intent.
3. Resolve the pandas `pct_change` FutureWarnings using explicit missing-value semantics.
4. Add a deterministic historical replay mode.
5. Freeze the score threshold and confirmation-gate configuration.
6. Add the invariant:

```text
Score >= 85 => Final_Decision == MOMENTUM_ACTIVE
```

The current working tree contains uncommitted engine changes. A run manifest must never rely only on the Git commit ID when the tree is dirty.

Every run records:

- Git commit ID.
- Git branch.
- Dirty/clean state.
- SHA-256 of every engine/config source file used.
- A Git diff patch when the tree is dirty.
- A source snapshot or reconstructable commit-plus-patch reference.

## Historical Replay Contract

### Daily data boundary

At signal date `D`, all indicators, Beta values, score fields, sector/market regimes, and message-rule inputs must use data dated `<= D`.

Forward outcome columns are calculated only after the signal row has been frozen.

### Live and intraday limitation

V7 uses live quote and hourly timing inputs that cannot always be reconstructed historically. Release 1 uses a deterministic daily replay mode and records:

```text
Historical_Replay_Mode = DAILY_EOD
Intraday_Replay_Status = UNAVAILABLE | AVAILABLE
Live_Quote_Replay_Status = UNAVAILABLE
```

The primary Beta linkage analysis is based on daily end-of-day active episodes. Any available historical intraday validation is reported separately and cannot be silently mixed into daily-only results.

### Benchmark handling

Use the same broad benchmark selection rule as V7:

- US default: `SPY`.
- US growth override when explicitly configured: `QQQ`.
- NSE: `^NSEI`.

The benchmark ticker used for each signal is stored in every audit row.

### Corporate actions and input revisions

Historical price data is frozen at acquisition time. Vendor revisions, splits, symbol changes, and delistings are not re-fetched during offline validation.

The initial study uses the current StockCodeMaster universe and therefore has survivorship/universe-history limitations. Those limitations must appear in the final signoff and prevent unsupported market-wide claims.

## Frozen Input Dataset

### Initial US universe source

```text
D:\Tools\StockCodeMaster\02_Stock\01-07-US_Common_Stocks_Master_Library.csv
```

Current reviewed snapshot SHA-256:

```text
DB2C286456885E3D0BBBC3210FF633B0C21B3EB36F36B9E2949D58496E2C9070
```

The execution run copies the actual universe file into the immutable run folder and recalculates the hash. The hash above documents the planning-time snapshot only.

Universe metadata retained:

```text
Ticker
Security Name
Listing Exchange
MarketCap
Sector
Industry
```

### Eligibility

Primary research eligibility:

- Common-stock row in the frozen universe.
- Supported market/exchange.
- At least 300 daily price bars before any signal date.
- Valid benchmark history.
- Valid sector value or explicit `UNKNOWN` label.
- No blank-check/SPAC classification in the primary cohort.
- Base V7 liquidity gates remain authoritative.

Exclusions and reasons are written to `universe_exclusions.csv`; they are never silently dropped.

### Price storage

Download once during the online acquisition phase and store locally:

```text
inputs/prices/<ticker>.parquet
inputs/benchmarks/<benchmark>.parquet
```

Required columns:

```text
Date
Open
High
Low
Close
Adj_Close, when available
Volume
Dividends, when available
Stock_Splits, when available
```

Parquet is available in the current Python environment and provides compact typed offline snapshots. CSV manifests remain the human-readable index.

No network call is permitted when `Replay_V7_Beta_Run.py --offline` is used.

## Beta and Residual-Momentum Specification

### Primary market Beta

For each signal date, align stock and benchmark daily returns on common dates and fit:

```text
Stock_Return_t = Alpha + Beta * Benchmark_Return_t + Residual_t
```

Primary specification:

```text
Lookback: 252 aligned daily returns
Minimum valid observations: 200
Return type: simple daily percentage return
Missing values: no implicit forward-fill before return calculation
```

Stored fields:

```text
Beta_252D
Beta_Alpha_Daily
Beta_R2_252D
Beta_Observations
Beta_Window_Start
Beta_Window_End
Beta_Status
```

### Stability diagnostics

Calculate, but do not initially use for production messaging:

```text
Beta_63D
Beta_126D
Beta_252D
Beta_252D_StdErr
Beta_252D_Confidence_Low
Beta_252D_Confidence_High
Beta_Up_Market
Beta_Down_Market
```

This establishes whether the Beta estimate is stable or regime/asymmetry dependent.

### Residual momentum

Calculate regression residual returns using information available through `D` and compound:

```text
Residual_Momentum_63D_Pct
Residual_Momentum_126D_Pct
```

Also retain the simpler interpretation field:

```text
Beta_Adjusted_RS_126D_Pct =
    Stock_Return_126D_Pct
    - Beta_252D * Benchmark_Return_126D_Pct
```

The compounded regression residual is the primary feature. The subtraction formula is an audit approximation.

### Provisional Beta bands

```text
DEFENSIVE:              Beta < 0.75
BALANCED:               0.75 <= Beta <= 1.25
HIGH_SENSITIVITY:       1.25 < Beta <= 1.75
VERY_HIGH_SENSITIVITY:  Beta > 1.75
UNRELIABLE:             insufficient observations or weak/invalid fit
```

Band boundaries are hypotheses. They may not be changed after final holdout results are opened without starting a new versioned research round.

## Industry and Market Linkage

### Sector and industry

Attach frozen StockCodeMaster `Sector` and `Industry` to every signal.

Sector is the primary grouping because industry groups may be sparse. Industry analysis is reported only when the group has an adequate sample; otherwise it is aggregated under an explicit `OTHER_SPARSE` group.

Store:

```text
Sector
Industry
MarketCap
MarketCap_Band
```

### Market regime at signal date

Define regime from benchmark data available at `D`:

```text
BULL:
  Benchmark_Close > Benchmark_EMA_200
  AND Benchmark_EMA_200_Slope > 0
  AND Benchmark_Weekly_Trend == Uptrend

BEAR:
  Benchmark_Close < Benchmark_EMA_200
  AND Benchmark_EMA_200_Slope < 0

TRANSITIONAL:
  all other valid combinations
```

Also record continuous market features:

```text
Benchmark_Return_21D_Pct
Benchmark_Return_63D_Pct
Benchmark_Realized_Vol_21D
Benchmark_Realized_Vol_63D
Benchmark_ATR_Pct
```

Volatility-regime thresholds must be rolling/point-in-time or fixed before holdout review. They may not use full-sample future quantiles.

### Linkage questions

The analysis must explicitly test:

- Beta versus subsequent absolute price variation.
- Beta versus positive/negative forward return.
- Beta versus MAE, MFE, and realized volatility.
- Beta versus D+1/D+2 continuation.
- Beta versus market-adjusted/residual forward return.
- Beta by market regime.
- Beta by sector and sufficiently populated industry.
- Beta by ATR and market-cap band.
- Residual momentum by Beta band.
- Whether high Beta merely explains amplitude or also predicts continuation quality.

## Forward Outcome Contract

Entry reference:

```text
Primary entry = next trading day's Open after signal date D
```

Store raw price points and derived outcomes:

```text
D_Close
D1_Open
D1_Close
D2_Open
D2_Close
Forward_5D_Return_Pct
Forward_10D_Return_Pct
Forward_21D_Return_Pct
Forward_63D_Return_Pct
Forward_126D_Return_Pct
Forward_5D_Realized_Vol
Forward_21D_Realized_Vol
Forward_63D_Realized_Vol
MAE_5D_Pct
MAE_21D_Pct
MAE_63D_Pct
MFE_5D_Pct
MFE_21D_Pct
MFE_63D_Pct
Max_Drawdown_21D_Pct
Max_Drawdown_63D_Pct
```

Continuation fields:

```text
D1_Open_Above_D_Close
D1_Close_Above_D_Close
D2_Close_Above_D_Close
Continuation_By_D2
Positive_5D
Positive_21D
Positive_63D
```

Market-adjusted outcomes:

```text
Benchmark_Forward_21D_Return_Pct
Benchmark_Forward_63D_Return_Pct
Beta_Adjusted_Forward_21D_Return_Pct
Beta_Adjusted_Forward_63D_Return_Pct
```

If a horizon is unavailable near the dataset cutoff, keep the signal and mark the horizon unavailable. Do not impute the outcome.

## Statistical Analysis Plan

### Descriptive analysis

For each Beta band and interaction group, report:

```text
Signals
Unique_Tickers
Mean
Median
Standard_Deviation
25th/75th_Percentile
Positive_Rate
D1_D2_Continuation_Rate
Median_MAE
Median_MFE
Median_Realized_Volatility
Bootstrap_Confidence_Interval
```

### Correlation analysis

Calculate Pearson and Spearman relationships between Beta and:

- Forward return.
- Absolute forward return.
- Realized volatility.
- MAE/MFE.
- Residual forward return.

Spearman is primary for monotonic relationships and robustness to extreme values.

### Multivariable models

Initial models:

```text
Forward_Return ~
    Beta + Beta_R2 + Residual_Momentum + Score + ATR_Pct
    + Market_Regime + Sector + MarketCap_Band
    + Beta:Market_Regime
    + Beta:Sector

Forward_Realized_Volatility ~
    Beta + ATR_Pct + Market_Regime + Sector + MarketCap_Band

Continuation_By_D2 ~
    Beta + Beta_R2 + Residual_Momentum + Score + ATR_Pct
    + Market_Regime + Sector
```

Use ticker-clustered uncertainty where supported. Report coefficients, confidence intervals, effect sizes, sample size, and out-of-sample performance—not p-values alone.

Industry interaction models run only for sufficiently populated industries. Multiple industry comparisons require false-discovery-rate control.

Raw observations are never deleted to improve a model. Winsorized/model-specific fields may be added alongside untouched raw outcomes.

## Chronological and Random Validation Design

### Chronological partitions

Use fixed calendar partitions after confirming data availability:

```text
Development:  earliest eligible date through 2022-12-31
Validation:   2023-01-01 through 2024-12-31
Final test:   2025-01-01 through the last frozen complete trading date
```

Warm-up data before the first eligible signal date is retained for indicators and Beta.

The final-test summary is not opened until calculation rules, Beta bands, and message-rule candidates are frozen in the manifest.

### Ticker-level holdout

Within chronological partitions, split at ticker level so the same company does not appear in both development and random holdout groups.

Default deterministic seed:

```text
20260710
```

Proposed split:

```text
Development tickers: 70%
Validation tickers:  15%
Holdout tickers:     15%
```

Stratify where feasible by sector and market-cap band before outcomes are examined.

### Offline random validation rounds

After the main backtest is frozen, create three deterministic offline validation rounds:

```text
Round 1 seed: 20260710
Round 2 seed: 20260711
Round 3 seed: 20260712
```

Target each round:

```text
50 active momentum episodes
```

Sample by ticker, then episode, with stratification across available Beta bands, market regimes, and sectors. Selection may use Beta/sector/regime but must never use forward outcomes.

If a stratum lacks enough rows, include all available rows and record the shortfall. Do not substitute favorable examples.

Every random sample is stored before its outcomes are summarized.

### Matched controls

For each sampled active episode, optionally select one `Score 75-84` control matched as closely as possible on:

```text
Signal date window
Sector
Market-cap band
ATR band
```

Controls are diagnostic and do not alter the active-only production rule.

## Immutable Run Folder and Offline Traceability

Each run receives a unique ID:

```text
V7BETA_<UTC timestamp>_<short commit>_<seed>
```

Folder layout:

```text
backtests/V7_Beta_Release1/runs/<RUN_ID>/
  README.md
  run_manifest.json
  command.txt
  environment.txt
  checksums.sha256
  source/
    engine_files_manifest.csv
    working_tree.patch
  config/
    Beta_Release1_Config.json
    Post_Processor_Message_Map.csv
  inputs/
    universe_snapshot.csv
    universe_exclusions.csv
    ticker_split.csv
    prices/
      <ticker>.parquet
    benchmarks/
      <benchmark>.parquet
  outputs/
    signal_audit.csv
    beta_band_summary.csv
    beta_market_interactions.csv
    beta_sector_interactions.csv
    beta_industry_interactions.csv
    regression_summary.csv
    message_policy_preview.csv
  validation/
    random_round_01_sample.csv
    random_round_01_results.csv
    random_round_02_sample.csv
    random_round_02_results.csv
    random_round_03_sample.csv
    random_round_03_results.csv
    validation_summary.csv
```

### Run manifest

`run_manifest.json` records:

```text
Run_ID
Created_UTC
Research_Version
Engine_Version
Git_Commit
Git_Branch
Git_Dirty
Engine_File_SHA256
Config_SHA256
Universe_SHA256
Random_Seeds
Date_Cutoff
Chronological_Partitions
Benchmark_Rules
Beta_Specification
Signal_Episode_Definition
Forward_Outcome_Definition
Input_Row_Counts
Exclusion_Counts_By_Reason
Dependency_Versions
Command_Line
Known_Limitations
```

### Checksums

Generate SHA-256 for every input, configuration, source snapshot/patch, sample, and output artifact.

Offline replay starts by verifying `checksums.sha256`. Any mismatch aborts the replay and records the mismatch.

### Git policy for artifacts

Commit to GitHub:

- Execution/backtest code.
- Configuration and message-map files.
- Run manifest.
- Ticker/sample manifests.
- Summary CSVs.
- Final signoff document.

Do not automatically commit large raw price Parquet files or very large signal-level outputs. Keep those in the immutable local run archive and record their hashes. If off-machine reproducibility is required, copy the full run folder to a versioned external/archive location and retain the same checksum manifest.

## Primary Signal Audit Columns

Every `signal_audit.csv` row must contain enough data to evaluate the signal without another live query:

```text
Run_ID
Signal_ID
Ticker
Signal_Date
Episode_Type
Score
Final_Decision
Final_Decision_Reason
Sector
Industry
MarketCap
MarketCap_Band
Benchmark_Ticker
Market_Regime
all V7 component scores
all V7 confirmed-entry gate values
Beta fields
Residual-momentum fields
raw D/D1/D2 prices
all forward outcomes
availability/status flags
source-data hashes
```

This prevents later offline validation from depending on current Yahoo values.

## Test Plan

### Beta unit tests

Synthetic return series:

```text
Stock = 0.5 * Market + small noise  -> estimated Beta near 0.5
Stock = 1.0 * Market + small noise  -> estimated Beta near 1.0
Stock = 2.0 * Market + small noise  -> estimated Beta near 2.0
Independent Stock and Market        -> low R-squared
Constant Market return              -> invalid variance status
Missing/interior observations       -> aligned/no-fill behavior
Fewer than 200 observations         -> insufficient-history status
```

### No-look-ahead tests

- Changing prices after `D` cannot change Score/Beta at `D`.
- Changing forward outcomes cannot change sample membership.
- Random samples are identical for the same input hash and seed.
- Chronological holdout dates cannot enter estimation windows.

### Engine contract tests

- Baseline and Beta-enriched scores are identical.
- Score 84 does not enter the production Beta cohort.
- Score 85 enters the cohort.
- Score 85 with non-active final decision is a contract error.
- An unavailable Beta produces a rule/status, not a score change.

### Offline replay tests

- Replay succeeds with network disabled.
- Replay fails on a modified input hash.
- Replay reproduces signal IDs, sample membership, Beta values, and summary row counts.
- Repeated replay does not overwrite the original run.

## Review Outputs

The Release 1 review package must answer in plain language:

1. Does high Beta increase actual future price amplitude after active momentum?
2. Does high Beta improve continuation, or only increase both upside and downside variation?
3. Do defensive/low-Beta active signals show stronger residual momentum?
4. Which market regimes materially change Beta outcomes?
5. Which sectors/industries show stable or unstable relationships?
6. Does Beta add information after controlling for Score, ATR, relative strength, and residual momentum?
7. What message-rule codes are supported, unsupported, or inconclusive?

Required review files:

```text
V7_Beta_Release1_Research_Summary.md
V7_Beta_Release1_Signoff.md
beta_band_summary.csv
beta_market_interactions.csv
beta_sector_interactions.csv
beta_industry_interactions.csv
validation_summary.csv
message_policy_preview.csv
```

## Signoff Gates

### Calculation signoff

- Unit tests and no-look-ahead tests pass.
- All inputs and outputs are hashed.
- Offline replay succeeds from frozen inputs.
- Score invariance is exact.

### Research signoff

- Adequate unique tickers and episodes exist in each claimed Beta band.
- Results are not driven by one stock, industry, or market period.
- Development, validation, final-test, and random-round directions are compared explicitly.
- Downside variation and drawdown are evaluated alongside returns.
- Known survivorship, live-timing, and vendor-history limitations are documented.

### Production-message signoff

The first Beta production release may proceed only after the user approves:

- Supported Beta rule codes.
- Initial lookup-table message text.
- Whether any qualitative allocation-context wording is justified.
- Behavior for weak R-squared or unavailable Beta.

If linkage is weak or inconsistent, production Beta remains factual:

```text
Beta value + R-squared + market-sensitivity description
```

No unvalidated allocation implication will be added.

## Execution Order

1. Commit/freeze the approved V7 baseline.
2. Implement minimum-history and explicit `pct_change` prerequisites.
3. Implement/test `Beta_Context.py` without production integration.
4. Implement immutable input acquisition and run manifests.
5. Implement V7 daily episode replay.
6. Run a small technical pilot across known processed tickers.
7. Inspect pilot only for data/calculation errors, not policy selection.
8. Freeze research configuration and random seeds.
9. Run the full development/validation backtest.
10. Freeze candidate message rules.
11. Run final chronological holdout and three offline random rounds.
12. Produce the research summary and signoff package.
13. Stop for user review.
14. Only after signoff, integrate Beta into `Score_Message` for live `MOMENTUM_ACTIVE` rows meeting the programmed threshold.

## Pilot Scope

Initial pipeline candidates from existing V5/V6/V7 artifacts include:

```text
NET
CSX
ILMN
ICHR
PL
CVV
ETN
ACA
MATX
```

These are candidates, not guaranteed research rows. A ticker/date enters the active cohort only when the frozen replay produces `MOMENTUM_ACTIVE`, meets `CONFIRMED_ENTRY_MIN_SCORE`, and has all required history.

The pilot should include:

- Previously processed active-momentum examples from V6/V7 validation artifacts.
- At least one stock from each provisional Beta band when available.
- Multiple sectors/industries.
- Bull, transitional, and bear market dates.
- A high-Beta stock with weak R-squared.
- A low-Beta stock with positive residual momentum.

Pilot results cannot be used as production evidence. They validate the pipeline and audit fields only.

After the pilot passes, execution expands to a sector/market-cap-stratified sample and then the full eligible frozen universe so rare Beta-band and market-regime combinations are not inferred from a handful of examples.

## Current Environment Recorded During Planning

```text
Python:       3.14.4
pandas:       2.3.3
numpy:        2.4.4
scipy:        1.18.0
statsmodels:  0.14.6
pyarrow:      available
pytest:       not currently installed
```

The execution manifest records actual versions again at run time. Testing may use the standard library `unittest` unless a reviewed dependency change adds pytest.

## Research Basis

- Residual momentum and common-factor exposure: https://repub.eur.nl/pub/22252
- Beta and risk-adjusted return evidence: https://www.nber.org/papers/w16601
- Market-regime dependence and momentum crashes: https://www.kentdaniel.net/papers/published/jfe_16.pdf
