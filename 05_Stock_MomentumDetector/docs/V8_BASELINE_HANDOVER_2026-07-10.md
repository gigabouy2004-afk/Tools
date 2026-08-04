# V8 Development Handover

Original date: 2026-07-10

Updated: 2026-07-12

Status: Superseded by `docs/V8_FINAL_HANDOVER_2026-07-12.md`. EMA200 plus configurable `8/21/5` MACD is now enforced as the V8 Foundation; the 20-stock/four-date validation passed. V8 remains development-only pending joint analysis and broader signoff.

## Baseline

V8 was forked from corrected V7 commit:

```text
9a4b0ba Fix V7 score range and append-only execution log
```

Intentional V8 differences:

```text
Engine identity: V8
Default top count: 5
Default final-summary threshold: 75
Execution log: Processed_Data/V8_Momentum_Execution_Log.csv
Final summary: Processed_Data/V8_Momentum_Execution_Dump.csv
Run ID prefix: V8_
Post-processing: ETF information only
```

## Inherited Correctness Rules

- Score remains within `0..100`.
- REJECT remains capped at `49`, independently of `--score-y`.
- CLI filters affect only the final summary.
- Every processed ticker reaches the append-only execution log before filtering.
- V7 remains untouched and operational.

## Beta Retirement

The Beta pilot was completed and preserved for audit, but its relationship with forward price performance was not sufficiently conclusive for production use. On 2026-07-11 the user closed and dropped the Beta track.

Consequences:

- No active V8 import of `Beta_Context_V8.py`.
- No Beta calculation or message in the production scan.
- No further Beta backtesting or signoff work.
- Frozen historical Beta artifacts remain immutable evidence only.

## ETF Phase 2 Implementation

Active files:

```text
Momentum_Detector_V8.py
ETF_Context_V8.py
Backtest_Momentum_Detector_V8_ETF.py
config/V8_Post_Processor_Message_Map.csv
tests/test_etf_context_v8.py
```

Trigger:

```text
Final_Decision == MOMENTUM_ACTIVE
AND Score >= CONFIRMED_ENTRY_MIN_SCORE
```

The ETF processor writes only `Score_Message` and never changes `Score`.

The live lookup makes one stock-specific request, filters against the local US ETF master, excludes leveraged/inverse funds, applies the strict `weight > 100/11` top-ten proof, returns at most three mappings, caches successes, and fails open.

The separate backtest may call returned ETFs' holdings pages solely to validate rank. That validation path is not imported by the production engine.

## Remaining Transition Gate

Completed in the 10-stock technical run:

1. Comprehensive design and same-quarter execution rule recorded.
2. Deterministic daily replay runner, independent validator, configuration, and tests implemented.
3. Ten-stock Q2 technical sample, random-date outcomes, ETF rank validation, Score invariance, frozen inputs, and checksums completed.
4. Technical conclusion prepared.

Still required before V8 becomes operational:

1. Execute the broader chronological development, validation, final-test, ticker-holdout, matched WAIT, V7 comparison, and robustness stages.
2. Obtain strict point-in-time ETF evidence or complete the prospective shadow cohort; alternatively record explicit acceptance of the assumption-limited scope.
3. Review the unfavorable sample result, completed conclusion, ETF message wording, and all data limitations.
4. Record explicit V8 operational signoff only if the expanded evidence supports it.

Canonical evidence:

```text
backtests/V8_ETF_Phase2/runs/V8ETF_20260711T135316Z_6fa10c6
docs/V8_ETF_PHASE2_CONCLUSION_2026-07-11.md
```

Comprehensive execution specification:

```text
docs/V8_COMPREHENSIVE_BACKTEST_PLAN_2026-07-12.md
```

Executed technical sample and conclusion:

```text
backtests/V8_Comprehensive/runs/V8FULL_20260711T192053Z_ffe1567_20260712
docs/V8_COMPREHENSIVE_BACKTEST_CONCLUSION_2026-07-12.md
```

Execution summary:

- 10 stocks and 620 Q2 daily EOD replays.
- 10 deterministic random test dates with 5/10/21-session exits inside Q2.
- 11 same-quarter ETF mappings; 11/11 independently validated in the top ten.
- 620/620 Score-invariance checks passed.
- Independent validator recomputed 30 forward returns and reported zero failures.
- Four independent Active episodes: mean 21D return `-0.49%`, mean SPY-adjusted return `-5.13%`, positive rate `25%`.
- Evidence classification: `TECHNICAL_SAMPLE_COMPLETE_INSUFFICIENT_FOR_BROAD_OPERATIONAL_SIGNOFF`.

Directional persistence run and conclusion:

```text
backtests/V8_Directional_Persistence/runs/V8DIR_20260711T193832Z_0568444
docs/V8_DIRECTIONAL_PERSISTENCE_CONCLUSION_2026-07-12.md
```

The April 30 date was chosen because it had the most April Active signals without using forward outcomes. GOOGL, COST, WMT, and XOM were Active. D+1 direction passed for 1/4, D+5 persistence passed for 1/4, and D+8 persistence passed for 2/4. All 80 independently recomputed metrics matched.

Alternate-code evidence:

```text
backtests/V8_Comprehensive/runs/V8FULL_20260711T194644Z_3ed85d1_20260713
backtests/V8_Directional_Persistence/runs/V8DIR_20260711T195008Z_3ed85d1
docs/V8_ALT_CODES_DIRECTIONAL_CONCLUSION_2026-07-12.md
```

Alternate result:

- XOM removed; PANW added.
- PANW -> HACK 9.65%, independently validated rank 1, holdings dated 2026-06-30.
- April 30 Active cohort: GOOGL, COST, WMT.
- Common-date pass rates: D+1 `1/3`, D+5 `1/3`, D+8 `2/3`.
- PANW was rejected on April 30 but rose `20.23%` by D+8.
- PANW first became Active June 9 and then passed D+1 `1.04%`, D+5 `7.44%`, and D+8 `9.93%`.
- Alternate validators reported zero failures across 620 execution rows, 30 random returns, and 88 directional metrics.

Important boundary:

- The existing five-stock ETF run is a production-path and mapping-quality validation, not a comprehensive V8 momentum backtest.
- The retired Beta pilot is historical audit evidence and is not part of the active V8 test scope.
- Current ETF mappings cannot be assigned to historical signals without dated point-in-time holdings evidence.
- The completed 10-stock technical run does not meet the broad sample targets in the comprehensive plan.
- The user-defined primary D+1 directional gate did not pass on the April signal-rich date.
- PANW is a documented confirmation-lag case: strong post-activation behavior, but late recognition of the April move.

MACD research evidence:

```text
backtests/V8_MACD_Research/runs/V8MACD_20260712T072722Z_1f1ac52
docs/V8_MACD_RESEARCH_CONCLUSION_2026-07-12.md
docs/V1_V8_EMA200_MACD_FOUNDATION_DISCOVERY_2026-07-12.md
```

MACD handover summary:

- V8 previously had no MACD; V1-V3 used `12/26/9`.
- V8 MACD is now configurable through CLI and stored in output audit fields.
- Defaults are now `8/21/5` following explicit user approval.
- MACD does not add score points, but Foundation enforcement changes downstream eligibility and can change Final Decision.
- Five predeclared settings produced 122 independent combined EMA200+MACD foundation episodes.
- `8/21/5`: D+1 `62.96%`, D+5 `62.96%`, D+8 `62.96%`.
- `12/26/9`: D+1 `52.63%`, D+5 `73.68%`, D+8 `73.68%`.
- `8/21/8` provided the strongest balanced fast-setting profile.
- Independent validator recomputed 1,586 metrics with zero failures.
- Discovery: EMA200 remained present; MACD was removed in V4's long-term rewrite with no documented evidence-based justification.
- The first 20-stock/four-date enforced run passed; the next evidence gate is multi-regime and untouched-holdout comparison.

Until signoff:

```text
V7 = operational baseline
V8 = development only; D+1 directional gate and operational signoff not passed
```
