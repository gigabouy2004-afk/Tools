# Momentum Engine Foundational Design Standard

Date: 2026-07-13

Applies to: V8 and future momentum-engine designs derived from this work.

Purpose: preserve what the experiments genuinely support, prevent failed assumptions from being repeated, and require functional and historical evidence before any indicator can alter the mainstream engine.

Authority: this standard is subordinate only to explicit user instruction and the active revised charter. It is the fresh-session design and closure register.

Workflow approval recorded 2026-07-13: the user approved a basic-engine rebuild followed by one-indicator-at-a-time functional testing, backtesting, result review and explicit approval before main V8 incorporation. See `docs/V8_BASIC_ENGINE_REBUILD_CHECKPOINT_2026-07-13.md`. This approves the process, not any untested indicator or gate.

## 1. Core Design Doctrine

The engine must answer four separate questions without mixing them:

```text
1. Is the data trustworthy?
2. Does the stock have a valid Foundation?
3. What additional evidence describes the setup and entry timing?
4. What non-signal context should be shown after the decision?
```

Data integrity, signal eligibility, entry timing and context are different responsibilities. A feature must not move between them without evidence and approval.

## 2. Rules That Apply to Every New Feature

Every proposed indicator or rule must declare:

- plain-language purpose;
- exact formula and units;
- input data and minimum history;
- point-in-time/no-look-ahead behaviour;
- expected benefit;
- known overlap with existing indicators;
- expected false positives and false negatives;
- requested authority level;
- backtest variants;
- primary and secondary endpoints;
- calibration sample;
- untouched holdout;
- promotion criteria;
- rollback behaviour.

Every numerical period, lower limit, upper limit, exact comparison value, crossover rule and tolerance must live in configuration variables. No such value may be embedded as an unexplained code literal.

Every configured decision value must also declare:

```text
Rule_Type
Limit_Status
Operational_Use_Approved
Requested authority
```

Allowed lifecycle states are:

```text
PLACEHOLDER_FUNCTIONAL_TEST_ONLY
RESEARCH_CANDIDATE_NOT_OPERATIONAL
USER_APPROVED_OPERATIONAL
```

A placeholder exists only to prove that configuration, boundaries, cutoffs and messages work. It is not a market recommendation or a claimed industry standard. `Operational_Use_Approved` must remain false until the user explicitly approves the value after the required research.

If any item is missing, the feature remains information-only.

## 3. Authority Levels

| Level | Authority | Meaning | Minimum evidence |
|---:|---|---|---|
| 0 | Display only | Publish raw measurement | Formula and no-look-ahead tests |
| 1 | Warning | Add explanatory text, no decision change | Functional tests plus descriptive replay |
| 2 | Ranking/score | Change ordering or transparent component score | Frozen ablation, calibration and holdout |
| 3 | WAIT | Prevent immediate Active while preserving setup | Evidence of weaker immediate entry or excess risk |
| 4 | Hard veto | Force Reject | Strong multi-regime evidence that excluded cases are invalid or unacceptably risky |

An inherited rule does not retain its old authority automatically. It must requalify under this standard.

## 4. Carry-Forward Register

These elements are carried into the new design immediately.

### CARRY-01 — Multi-session objective

```text
Primary: D+1 open-to-close direction
Persistence: D+5 and D+8 from D+1 open
Expected use: approximately 3 sessions to 1-2 weeks
```

Reason: explicitly defined user intent.

### CARRY-02 — Point-in-time and no-look-ahead integrity

No future bar, later holding, revised classification or post-signal information may affect an earlier signal.

Reason: foundational correctness requirement.

### CARRY-03 — Foundation-first architecture

Only Foundation-eligible stocks proceed to additional analysis.

Reason: explicit user requirement and V1-V3 lineage.

### CARRY-04 — EMA200 in the Foundation

Price relative to EMA200 represents long-term structural eligibility.

Current authority: Foundation gate.

Required continuing test: below-EMA200 false negatives across recovery regimes must still be reported.

### CARRY-05 — Configurable MACD in the Foundation

MACD must remain configurable and auditable.

Current development baseline: `8/21/5`.

Carried concept: MACD participation in Foundation.

Not yet universally approved: `8/21/5` as optimal in every sector/regime and one combined policy for all non-confirming states.

### CARRY-06 — Explicit state rather than silent elimination

Every processed stock must produce a state and reason, including insufficient data and non-confirming Foundation substates.

Reason: auditability and later false-negative analysis.

### CARRY-07 — Configuration and evidence versioning

Indicator periods, thresholds, benchmark selection, weights and authority must be stored with each run.

Default values must be stored in named configuration variables, not buried in formulas. Output and frozen evidence must state whether each value is a placeholder, research candidate or explicitly approved operational value.

### CARRY-08 — Frozen evidence package

Each qualifying run must preserve config, prices, source snapshot, outputs, manifest, validator results and checksums.

### CARRY-09 — Independent validation

Critical formulas and forward outcomes must be independently recomputed from frozen inputs.

### CARRY-10 — Transparent failure and append-only logging

Data/API failures must be visible. Historical logs must not be silently overwritten when schema changes.

### CARRY-11 — ETF as post-decision information only

ETF mapping may run after Active. It cannot change any signal value or decision.

### CARRY-12 — Operational isolation

V7 remains operational until explicit V8 signoff. Experimental findings cannot silently alter V7.

## 5. Rejected Design Practices

These practices are rejected and must not be reintroduced without explicit user reversal.

### REJECT-01 — Generic “professional practice” as evidence

An indicator is not valid for this engine because professionals commonly discuss or use it.

### REJECT-02 — Universal SPY hard veto

SPY cannot automatically reject technology, industrial or other stocks based on one fixed horizon.

### REJECT-03 — ETF influence on signal quality

ETF ownership, holding weight or mapping availability cannot add points, confirm momentum, rank stocks or change a decision.

### REJECT-04 — Unvalidated hard thresholds

No distribution count, weekly trend, ATR, return, volume or benchmark threshold may become a hard veto without veto-level evidence.

### REJECT-05 — Opaque composite score

A single final number without raw components, caps and blockers is not an adequate contract.

### REJECT-06 — Automatic authority for inherited rules

V4-V7 presence does not approve a rule for the new engine.

### REJECT-07 — Indicator stacking without ablation

Several new rules may not be added together and credited collectively. Each must be tested one at a time.

### REJECT-08 — Outcome-driven sample selection

Tickers, dates, thresholds and variants may not be selected after forward outcomes are inspected.

### REJECT-09 — Percentage-only reporting

Every percentage must show its numerator and denominator.

### REJECT-10 — Ambiguous terminology

Terms such as “MACD reset,” “downstream score,” “professional confirmation” and “commercial readiness” cannot appear without exact definitions.

### REJECT-11 — Historical ETF back-casting

Current holdings cannot be assigned to an old signal unless the evidence date satisfies the approved historical rule.

### REJECT-12 — Mixing implementation validation with predictive validation

Passing checksums and formula recomputation proves technical integrity only. It does not prove that a signal predicts returns.

### REJECT-13 — Treating Reject as a bearish forecast

Reject means the engine did not authorize the setup. It does not assert that price must decline.

### REJECT-14 — Mainstream modification before approval

Research code and a successful sample do not authorize mainstream integration.

### REJECT-15 — Arbitrary defaults presented as accepted practice

No numerical value may be institutionalized because it is conventional, popular, described as professional practice, or previously suggested by the implementation agent. A value may be used as a clearly labelled functional placeholder, but it cannot be described as correct, recommended or operationally approved without the required evidence and explicit user approval.

## 6. Functional and Backtest Gate Register

Every item below is research-only at the effective date unless explicitly stated otherwise.

### TEST-01 — Freshness / distance from 20-day high

Current problem:

- field is negative below the high;
- positive comparison thresholds award 12 points to all analysed cases;
- extension penalties cannot operate as intended.

Required functional tests:

- exact definition: positive distance below high or signed return from high;
- boundary cases at 0%, 2%, 5%, 10% and 20%;
- no-look-ahead rolling high;
- handling of zero/missing highs;
- independent recomputation.

Required backtest:

- current defective comparator;
- corrected information-only measurement;
- alternative ranking/score variants;
- same frozen 80 observations first;
- later calibration and holdout.

Promotion restriction: cannot affect score until formula approval and holdout pass.

### TEST-02 — Distribution count and accumulation evidence

Current problem:

- eight distribution days force Reject;
- ten Foundation-valid rejected observations were 8/10 positive D+1, 10/10 D+5 and 8/10 D+8.

Required variants:

```text
A. Information only
B. Transparent score penalty
C. WAIT only when recent distribution is also present
D. Hard veto only with price/volume trend breakdown
E. Current eight-day hard veto comparator
```

Required analysis:

- count, recency and clustering separately;
- net accumulation context;
- sector-normalized volatility/volume behaviour;
- D+1/D+5/D+8 outcomes;
- maximum adverse excursion;
- false-negative list.

Promotion restriction: current hard veto is not approved.

### TEST-03 — Benchmark and relative strength

Current problem:

- fixed 126-session SPY underperformance can Reject every stock;
- this is inappropriate as a universal technology rule and too slow for early recovery.

Required variants:

```text
A. No benchmark decision authority
B. SPY information only
C. Sector benchmark information only
D. 21/63-session sector-relative ranking
E. 21/63/126 multi-horizon context
F. WAIT or ranking variants only after evidence
```

Required benchmark design:

- deterministic mapping by sector/industry;
- frozen before outcomes;
- fallback and missing-map behaviour;
- benchmark changes recorded historically;
- no per-stock hand selection after results.

Promotion restriction: universal SPY veto is rejected; any replacement starts at Level 0.

### TEST-04 — Weekly trend

Current problem:

- non-Uptrend weekly state can force Reject;
- slow 30-week confirmation may reject early recoveries.

Required variants:

```text
A. Information only
B. Ranking input
C. WAIT for mature-trend strategy only
D. Separate Established Momentum versus Early Recovery labels
E. Current hard-reject comparator
```

Required analysis:

- early recovery cohort;
- established trend cohort;
- weekly moving-average lengths;
- false-negative delay in trading sessions;
- D+1 and persistence trade-off.

Promotion restriction: no hard veto until multi-regime holdout evidence.

### TEST-05 — MACD periods and substates

Carried concept: configurable MACD Foundation participation.

Current issue: one `MACD_RESET` label combines different states.

Required substates:

```text
MACD positive but below signal       = positive pullback
MACD below zero but above signal     = early recovery
MACD below zero and below signal     = negative weakening
```

Required variants:

- `8/21/5` development baseline;
- standard `12/26/9` comparator;
- previously frozen Fibonacci candidates;
- substate-specific WAIT/research behaviour;
- episode-start versus arbitrary-date analysis.

Promotion restriction: no substate may become Active directly from three observations.

### TEST-06 — EMA stack and EMA200 slope

Question: after Close > EMA200 passes, do EMA50/EMA150 ordering and EMA200 slope improve entry quality or merely delay recovery detection?

Required variants:

- raw display only;
- ranking input;
- positive-slope WAIT;
- current point allocation.

Promotion restriction: no hard veto without ablation and holdout.

### TEST-07 — Breakout and high proximity

Question: does proximity to 55-, 100- or 252-session highs improve D+1 and persistence, and how should pullbacks be handled?

Required functional tests:

- signed versus positive distance convention;
- rolling-window boundaries;
- split/corporate-action behaviour;
- no-look-ahead.

Required variants:

- information only;
- individual horizons separately;
- combined ranking only after ablation.

### TEST-08 — Volatility and ATR

Question: should ATR measure opportunity, risk, position sizing, WAIT, or veto?

Required analysis:

- sector distributions;
- return versus drawdown;
- fixed versus percentile thresholds;
- technology versus industrial calibration;
- interaction with position sizing.

Promotion restriction: ATR cannot be a universal veto based only on a generic percentage.

### TEST-09 — Relative volume and close location

Question: do volume confirmation and daily close position improve next-session entry?

Required variants:

- information only;
- entry WAIT;
- ranking;
- combined and separate ablation.

Required functional tests:

- zero-range daily bar;
- missing/abnormal volume;
- split-adjusted volume policy;
- earnings-gap behaviour.

### TEST-10 — Liquidity

Liquidity is primarily an execution constraint, not momentum evidence.

Required design:

- market-specific dollar-volume units;
- intended position-size relationship;
- missing data behaviour;
- distinction between research-universe exclusion and signal veto.

Promotion restriction: threshold requires user-approved execution assumptions.

### TEST-11 — Recent return / extension

Question: when should strong recent return indicate desirable momentum versus excessive extension?

Required variants:

- information only;
- WAIT at multiple thresholds;
- interaction with close location and volatility;
- D+1 benefit versus D+5/D+8 opportunity loss.

Promotion restriction: no generic 5D/10D threshold may be assumed professional or universal.

### TEST-12 — Intraday and extended-hours timing

This engine targets multi-day trades. Intraday evidence may affect execution timing but must not redefine long-term momentum without proof.

Required evidence:

- prospective/live shadow data;
- reproducible quote timestamp and market state;
- missing-hourly-data behaviour;
- separation of signal validity from entry timing.

Promotion restriction: historical daily replay cannot validate unavailable live/hourly rules.

### TEST-13 — Composite score and thresholds

Question: is a composite Score required, or would explicit states and ranked evidence be clearer?

Required variants:

```text
A. Foundation state plus raw measurements, no composite
B. Transparent ranking score, no veto authority
C. Small evidence-supported component score
D. Current legacy score comparator
```

Required output for every scored variant:

- raw metric;
- points awarded;
- raw total;
- caps;
- cap reasons;
- blockers;
- final state.

Promotion restriction: current opaque score is not approved as the new design.

### TEST-14 — ETF context

Mandate: functional accuracy only.

Required tests:

- direct mapping correctness;
- whitelist and leverage exclusion;
- top-ten evidence;
- ordering and limit;
- timeout/cache/failure behaviour;
- date disclosure;
- Score and decision invariance.

Not required and not authorized: testing ETF mapping as a stock-return predictor unless the user separately requests a research study.

### TEST-15 — External analyst, EPS and event messages

Mandate: contextual information only unless separately approved.

Required tests:

- fail-open behaviour;
- timestamp/source disclosure;
- no Score/decision mutation;
- clear separation from engine-generated evidence.

## 7. Mandatory Backtest Sequence

### Phase A — Correctness repair

1. Approve the freshness definition.
2. Add boundary/no-look-ahead tests.
3. Expose raw score, caps and blockers.
4. Do not change decision authority in the same step.
5. Recompute the frozen 80 observations under the corrected formula.

Purpose: isolate correctness changes from strategy changes.

### Phase B — Minimal baseline

Create a Foundation-only candidate baseline:

```text
Data valid
Close > EMA200
MACD state published
No inherited post-Foundation hard veto
All later indicators information-only
```

This baseline does not mean every Foundation-valid stock is automatically trade-ready. It creates the neutral comparator needed to determine what each additional rule contributes.

### Phase C — Frozen 80-row ablation

Use the same frozen stocks, dates and prices from:

```text
V8FOUND_20260712T182945Z_cf0c908
```

Compare:

1. minimal Foundation baseline;
2. current legacy V8 comparator;
3. corrected freshness only;
4. each proposed rule variant one at a time.

Report changes in:

- eligible/Active/Wait/Reject counts;
- D+1/D+5/D+8 results;
- false positives and false negatives;
- entry delay;
- maximum adverse/favourable excursion where data permits;
- sector and date breakdown.

Purpose: diagnose, not select final thresholds from 80 rows.

### Phase D — Calibration study

Proposed minimum design, subject to user approval before execution:

- at least 40 stocks;
- technology majority plus a defined industrial cohort;
- at least 8 predeclared signal dates;
- more than one market condition;
- frozen sector/industry benchmark mapping;
- chronological partitions;
- adequate Foundation-valid and non-confirming episodes;
- one-change-at-a-time variants.

The exact stocks, dates and regimes must be frozen before outcomes are opened.

### Phase E — Untouched holdout

Proposed minimum, subject to user approval:

- at least 20 different stocks;
- at least 4 previously unused dates;
- technology and industrial representation;
- no formula, threshold or benchmark changes after opening results.

Purpose: decide promotion, not further tune rules.

### Phase F — Prospective shadow

Before operational promotion:

- run V8 without affecting V7;
- store live timestamps, quotes, hourly evidence and decisions;
- observe failures and message quality;
- validate ETF context functionally;
- compare live versus historical replay behaviour.

## 8. Promotion Test by Requested Authority

### To become a warning

The feature must be correct, understandable and non-mutating.

### To become a ranking or score input

It must improve ordering or outcome separation in calibration and holdout without relying on post-hoc thresholds.

### To become WAIT

The blocked group must show meaningfully weaker immediate entry quality or higher risk, while the output preserves the opportunity for later re-entry.

### To become a hard veto

The excluded group must consistently show invalid structure, unacceptable drawdown or materially inferior results across sectors/regimes and untouched holdout. A few negative examples or generic practice are insufficient.

### To enter mainstream

All prior tests plus explicit user approval are required.

## 9. Closure Register

| ID | Topic | Current status | Required closure | Current recommendation |
|---|---|---|---|---|
| CL-01 | Foundation architecture | Carried | Wider sector/regime validation | Retain Foundation-first design |
| CL-02 | MACD default `8/21/5` | Development baseline | Calibration plus holdout versus comparators | Keep configurable; do not declare universal optimum |
| CL-03 | MACD non-confirmation labels | Open | Approve three explicit substates | Replace ambiguous reset label |
| CL-04 | Early recovery below zero | Research | Larger episode sample | Research state, not direct Active |
| CL-05 | Freshness formula | Defect | User-approved definition, tests, rerun | Correct before score signoff |
| CL-06 | Distribution hard veto | Not approved | Ablation variants and risk analysis | Test information/penalty/WAIT before veto |
| CL-07 | Universal SPY veto | Rejected | None unless user reverses | Remove decision authority in new design |
| CL-08 | Sector benchmark design | Research | Deterministic mapping and horizon tests | Information-only initially |
| CL-09 | Weekly trend hard veto | Not approved | Early-recovery versus mature-trend study | Information or labelled setup initially |
| CL-10 | Composite score | Open | Transparent alternatives and holdout | Do not retain opaque score by default |
| CL-11 | Score caps | Not approved | Expose raw/capped values and validate need | Never hide raw score |
| CL-12 | ATR/volatility authority | Research | Sector/risk calibration | Information first |
| CL-13 | Volume/close-location authority | Research | Separate ablation | Candidate entry-timing feature only |
| CL-14 | Intraday/live confirmation | Research | Prospective shadow | Keep separate from long-term validity |
| CL-15 | ETF mapping | Functionally validated context | Maintain invariance and date accuracy | Active-only information, never scoring |
| CL-16 | Technology/industrial generalization | Open | Calibration and untouched holdout | Required before promotion |
| CL-17 | V8 operational replacement | Blocked | Close defects, tests and explicit approval | V7 remains operational |

## 10. Approval Register for the User

The following decisions should be discussed before new mainstream implementation:

1. Approve the revised charter and this design standard as controlling documents.
2. Confirm EMA200 plus configurable MACD as the carried Foundation architecture.
3. Confirm `8/21/5` as the next-test baseline rather than a universal final setting.
4. Approve the three MACD substate names.
5. Approve the freshness-distance definition.
6. Approve removal of universal SPY veto authority from the new design.
7. Approve ETF mapping as permanently informational and non-scoring.
8. Approve the minimal Foundation-only comparator.
9. Approve one-rule-at-a-time ablation order.
10. Approve the calibration and untouched-holdout sample design before dates/tickers are selected.
11. Decide whether a composite Score remains a product requirement after transparent-state alternatives are shown.

No unanswered item should be silently assumed approved by a future session.

## 11. Fresh-Session Restart Procedure

At the start of a new session:

1. Work only in `D:/Tools/Stock_MomentumDetector`, not the ETF Comparator folder.
2. Read `docs/V8_REVISED_DEVELOPMENT_CHARTER_2026-07-13.md` completely.
3. Read this document completely.
4. Read `docs/V8_BASIC_ENGINE_REBUILD_CHECKPOINT_2026-07-13.md`.
5. Read `docs/V8_EXPERIMENT_ANALYSIS_BRIEF_2026-07-13.md` for results and terminology.
6. Read the frozen validation summary and aggregate summary.
7. Check Git status and preserve unrelated user changes.
8. Treat `Momentum_Detector_V8.py` as the current experimental comparator, not the approved future blueprint.
9. Do not add or remove decision rules before checking the Closure Register.
10. Ask only for unresolved approvals that materially change the next test.
11. Freeze the test design before running outcomes.
12. Commit only scoped changes and never rewrite frozen evidence.

Key commits:

```text
1cf46a0 Enforce V8 MACD foundation and validate tech cohort
3f3102b Document V8 experiment terms and approval decisions
```

Canonical frozen evidence:

```text
backtests/V8_Foundation_Validation/runs/V8FOUND_20260712T182945Z_cf0c908
```

Required summaries:

```text
outputs/aggregate_summary.json
outputs/execution_log.csv
outputs/regression_comparison.csv
validation/validation_summary.json
checksums.sha256
```

## 12. Current Handover State

```text
Operational engine: V7
Development engine: V8
Approved architectural direction: data integrity -> EMA200/MACD Foundation -> tested evidence -> entry decision -> context
Current V8 post-Foundation rules: frozen comparator only
Universal SPY veto: rejected
ETF signal/scoring role: prohibited
Known blocking defect: freshness sign/threshold mismatch
Next work: approve documents, repair correctness transparently, build minimal baseline, run frozen ablations
```
