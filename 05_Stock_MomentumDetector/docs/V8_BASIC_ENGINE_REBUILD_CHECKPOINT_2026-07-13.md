# V8 Basic Engine Rebuild Checkpoint

Date: 2026-07-13

Status: development workflow approved by the user. The basic Foundation-only engine and the strictly Foundation-gated, calculation-only V1-V3 indicator layer were implemented and independently validated on 2026-07-13. Reports: `docs/V8_BASIC_FOUNDATION_IMPLEMENTATION_2026-07-13.md` and `docs/V8_CALCULATION_ONLY_INDICATORS_IMPLEMENTATION_2026-07-13.md`.

RSI base-layer update, 2026-07-13: standard RSI(14) now uses configurable inclusive limits 30-65, actual-value messages and a continuation Boolean. It operates only after Foundation eligibility. Ten-symbol functional evidence and the 80-row independent replay are documented in `docs/V8_RSI_BASE_LAYER_IMPLEMENTATION_2026-07-13.md`. This approves mechanics, not performance optimality.

Placeholder clarification: 30 and 65 were deliberately supplied to exercise both sides of the configurable cutoff. They carry `PLACEHOLDER_FUNCTIONAL_TEST_ONLY` status and cannot claim operational approval. The same configuration/status contract is mandatory for every later indicator.

## 1. User Direction Recorded

V8 will restart from a basic engine. Indicators will then be introduced individually.

For every indicator:

1. define the exact formula and candidate values;
2. define every proposed score, threshold, WAIT rule or hard gate;
3. functionally test the calculation;
4. backtest the indicator independently against the basic baseline;
5. measure what it improves and what valid opportunities it excludes;
6. present the results in plain language;
7. obtain explicit user approval; and only then
8. incorporate the approved formula and authority into the main V8 engine.

No indicator, value, score, threshold or gate may enter main V8 merely because it existed in an older version or is commonly used by traders.

## 2. What Is Approved Now

Approved development process:

```text
Basic V8 engine
    -> one research indicator
    -> formula tests
    -> isolated frozen backtest
    -> score/gate alternatives
    -> result review
    -> explicit user approval
    -> main V8 integration
    -> full regression
```

Approved design boundaries:

- V7 remains operational during the rebuild.
- V8 remains development-only.
- ETF mapping is informational after the stock decision and never affects scoring.
- Universal SPY veto authority is rejected.
- Current post-Foundation V8 scoring remains a historical comparator, not an approved design.
- Formula correctness and no-look-ahead validation precede predictive backtesting.
- Only one conceptual indicator change is tested at a time.

## 3. What Is Not Approved Yet

This workflow approval does not approve:

- any post-Foundation indicator;
- any component score;
- any composite-score formula;
- any Active threshold;
- any distribution count or accumulation gate;
- any weekly-trend gate;
- any broad-market, sector or industry benchmark rule;
- any ATR or volatility threshold;
- any breakout or recent-high threshold;
- any volume, close-location or liquidity gate;
- any extension threshold;
- any intraday or extended-hours gate;
- any MACD non-confirmation re-entry rule;
- promotion of V8 over V7.

Each item remains research-only until its own approval is recorded.

## 4. Basic V8 Engine Target for the Next Session

The implementation target is deliberately minimal:

### Required core

- ticker and market-data loading;
- deterministic date/index handling;
- sufficient-history validation;
- point-in-time/no-look-ahead calculations;
- configurable EMA200/MACD Foundation research baseline;
- explicit Foundation and insufficient-data states;
- raw indicator values and plain-language reasons;
- append-only execution log;
- versioned configuration;
- reproducible backtest interface;
- independent validation hooks.

### Excluded from the basic decision path

- legacy composite Score;
- legacy commercial score caps;
- universal SPY rejection;
- weekly-trend rejection;
- distribution-cluster rejection;
- breakout scoring;
- freshness scoring;
- ATR scoring or veto;
- relative-volume and close-location gates;
- intraday/extended-hours gates;
- ETF or external-message influence.

These excluded calculations may exist in historical comparator code, but they do not belong in the new basic engine until separately tested and approved.

### Basic output

The basic engine must expose facts rather than hide them in a score:

```text
Ticker
Signal timestamp/date
Data status
Close
EMA200
MACD periods
MACD line
MACD signal line
MACD histogram
Exact Foundation state
Exact Foundation reason
Configuration version
```

The exact trade-eligibility label for each MACD substate will be finalized through the approved test process.

## 5. Indicator Onboarding Contract

Every indicator receives its own research package containing:

```text
Indicator specification
Formula unit tests
Boundary tests
No-look-ahead test
Frozen configuration
Baseline results
Indicator-variant results
Excluded-opportunity report
D+1/D+5/D+8 outcomes
Risk/drawdown evidence where available
Independent validation
Plain-language conclusion
Approval decision
```

An indicator cannot borrow evidence from another indicator. Combined-indicator tests occur only after each component has independently qualified.

## 6. Score and Gate Approval Contract

Testing an indicator value does not automatically approve a score or gate.

Authority is approved separately:

```text
Raw display
Warning/message
Ranking input
Score input
WAIT condition
Hard rejection
```

A hard rejection requires stronger evidence than a display field or ranking input. The rejected cohort must be reported so that false negatives are visible.

Any proposed Score must disclose:

- raw indicator values;
- points awarded;
- raw total;
- caps and cap reasons;
- blockers;
- final displayed score;
- decision before and after the new indicator.

## 7. Required Comparison for Every Indicator

Each experiment must contain at least:

```text
A. Basic V8 baseline
B. Indicator calculated but information-only
C. Candidate scoring/ranking variant
D. Candidate WAIT or gate variant, if proposed
E. Existing legacy V8 comparator where relevant
```

The experiment must answer:

1. Did the indicator improve D+1 direction?
2. Did it improve or damage D+5/D+8 persistence?
3. How many additional signals did it admit?
4. How many valid opportunities did it exclude?
5. Did it reduce adverse movement or only reduce participation?
6. Did the result hold across dates, sectors and an untouched holdout?
7. What authority, if any, is justified by the evidence?

## 8. Main V8 Integration Gate

Integration into main V8 requires all of:

- exact approved formula;
- approved configuration values;
- approved authority level;
- passing functional tests;
- passing frozen calibration backtest;
- passing untouched holdout;
- passing regression against previously approved behaviour;
- updated output contract and documentation;
- explicit user approval recorded in a scoped commit.

If any condition is absent, the indicator remains outside main V8.

## 9. Repository Checkpoint

Current controlling documents:

```text
docs/V8_REVISED_DEVELOPMENT_CHARTER_2026-07-13.md
docs/MOMENTUM_ENGINE_FOUNDATIONAL_DESIGN_STANDARD_2026-07-13.md
docs/V8_BASIC_ENGINE_REBUILD_CHECKPOINT_2026-07-13.md
docs/V8_EXPERIMENT_ANALYSIS_BRIEF_2026-07-13.md
```

Current comparator implementation:

```text
Momentum_Detector_V8.py
```

The comparator is preserved for regression evidence. It is not the target design for the basic rebuild.

Canonical frozen evidence:

```text
backtests/V8_Foundation_Validation/runs/V8FOUND_20260712T182945Z_cf0c908
```

Source audit at this checkpoint:

```text
Active V8 TODO/FIXME/stub/NotImplemented paths: none
Empty custom exception classes: intentional
Temporary runtime outputs: not source and not canonical evidence
Frozen canonical evidence: tracked and checksum-valid
```

## 10. Next-Session Start Instruction

The next V8 session must begin by:

1. reading the controlling charter, design standard and this checkpoint;
2. checking Git status and remote synchronization;
3. preserving the current comparator and frozen evidence;
4. specifying the basic-engine file/config/output boundary before editing code;
5. implementing only the approved minimal core;
6. validating the basic core before selecting the first research indicator.

No indicator onboarding begins until the basic engine itself is reviewed.

Implementation checkpoint:

```text
Basic engine: Momentum_Detector_V8_Basic.py
Foundation-only frozen replay: V8BASICFOUND_20260712T204114Z_36c2e24
Rows independently recomputed: 80/80
Validation failures: 0
Score/benchmark/ETF fields: absent
Next gate: user review before selecting the first post-Foundation indicator
```

Calculation-only update:

```text
Indicator set: RSI, ADX/+DI/-DI, True Range/ATR/ATR%, OBV/OBV EMA, Aroon
Authority: CALCULATION_ONLY
Mandatory entry gate: Foundation_Eligible = True
Frozen rows independently recomputed: 80/80
Foundation rows changed: 0/80
Indicator module executed: 25/25 eligible rows
Indicator module skipped: 55/55 ineligible rows
Ineligible rows with indicator values: 0
Scores or gates added: none
Next gate: choose one indicator for isolated value/rule backtesting
```

RSI base-layer functional update:

```text
RSI definition: standard RSI(14)
Configured range: inclusive 30-65
Authority: configurable functional-test continuation gate after Foundation
Limit status: PLACEHOLDER_FUNCTIONAL_TEST_ONLY
Operational use approved: False
Ten-symbol sample: 2 within range, 8 above range
Frozen eligible observations: 12 allowed, 13 stopped above 65
Foundation-ineligible RSI evaluations: 0/55
Foundation rows changed: 0/80
Scores or trade statuses added: none
Next gate: isolated RSI performance testing before operational approval
```
