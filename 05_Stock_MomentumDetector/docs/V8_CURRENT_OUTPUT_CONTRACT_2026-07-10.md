# V8 Current Output Contract

> **CURRENT-CODE DESCRIPTION, NOT FUTURE-DESIGN APPROVAL.** The controlling development documents are `docs/V8_REVISED_DEVELOPMENT_CHARTER_2026-07-13.md` and `docs/MOMENTUM_ENGINE_FOUNDATIONAL_DESIGN_STANDARD_2026-07-13.md`. This file describes what the existing V8 comparator publishes; inherited post-Foundation score and veto behaviour remains subject to research and approval.

Original date: 2026-07-10

Updated: 2026-07-12

Status: V8 development contract with an enforced EMA200 plus configurable MACD Foundation stage. Production defaults are MACD `8/21/5` and `--foundation-policy enforce`. ETF context remains informational and V8 remains non-operational pending signoff.

Known review item: `FOUNDATION_TREND_VALID_MACD_RESET` currently combines three distinct MACD states. The existing freshness score also uses a negative distance-from-high field with positive comparison thresholds. Neither terminology splitting nor the freshness correction is implemented yet; both require user approval as documented in `docs/V8_EXPERIMENT_ANALYSIS_BRIEF_2026-07-13.md`.

## Defaults and Active Trigger

```text
DEFAULT_COUNT_X = 5
DEFAULT_SCORE_Y = 75.0
CONFIRMED_ENTRY_MIN_SCORE = 85
```

ETF post-processing is eligible only when:

```text
Final_Decision == MOMENTUM_ACTIVE
AND
Score >= CONFIRMED_ENTRY_MIN_SCORE
```

`--score-y` and `--count-x` control only final-summary presentation. They do not participate in the ETF trigger.

## Score Contract

Published `Score` remains constrained to `0..100`.

| Final decision | Maximum published Score |
|---|---:|
| `MOMENTUM_ACTIVE` | 100 |
| `MOMENTUM_PRESENT_WAIT_CONFIRMATION` | 84 |
| `REJECT` | 49 |

The ETF post-processor cannot modify `Score`, component scores, decisions, or ranks. Beta is not calculated and cannot modify any output.

## Score_Message Contract

For an eligible Active row, `Score_Message` contains ETF context only.

Mapped example:

```text
Active momentum confirmed. Verified top-10 ETF mappings: SMH 19.20%; VGT 16.77%; FTEC 16.60%.
```

No verified mapping:

```text
Active momentum confirmed. No USA-listed ETF mapping could be conservatively verified as a top-ten holding.
```

Failure example:

```text
Active momentum confirmed. ETF mapping is unavailable (<reason>); Score is unchanged.
```

WAIT and REJECT rows do not call the ETF source and retain a blank `Score_Message`.

## ETF Eligibility and Ordering

A mapping is displayed only when all conditions pass:

- ETF ticker exists in the local US ETF master.
- ETF is not identified as leveraged or inverse.
- Stock holding weight is strictly greater than `100/11` percent, conservatively proving top-ten membership.

At most three mappings are displayed, sorted by:

```text
Holding_Weight_Pct DESC
ETF_Ticker ASC
```

Lower-weight exposures are omitted because the reverse source does not publish holding rank. No percentage is fabricated.

## Network, Cache, and Failure Contract

- One stock-specific TradingView funds-page request is permitted per uncached Active stock.
- Successful results are cached by stock code for 24 hours by default.
- No per-ETF holdings request exists in `Momentum_Detector_V8.py` or `ETF_Context_V8.py` production lookup.
- No ETF-universe Yahoo/yfinance scan is allowed.
- Timeout, HTTP error, empty response, or schema change fails open into `Score_Message`.
- Provider response hash, retrieval time, latency, URL, and filter counts are available in the mapping context/audit result.

## Append-Only Execution Log

Default path:

```text
D:/Tools/Stock_MomentumDetector/Processed_Data/V8_Momentum_Execution_Log.csv
```

Every processed ticker is appended before final-summary filtering. A reader may inspect completed rows while the scan continues when it uses non-exclusive file access.

## Final Summary

Default path:

```text
D:/Tools/Stock_MomentumDetector/Processed_Data/V8_Momentum_Execution_Dump.csv
```

It is written after the scan and contains the sorted top `--count-x` rows satisfying `Score >= --score-y`.

## Feature State

Implemented in development:

- Semantic Active-only ETF trigger.
- Direct stock-specific ETF exposure lookup.
- Local US ETF whitelist.
- Conservative top-ten proof and leverage exclusion.
- Top-three sorting.
- Persistent TTL cache and bounded timeout.
- ETF-only `Score_Message` rules.
- Fail-open Score invariance.
- Five-stock API/data-quality validation runner.

Dropped:

- Beta calculation.
- Beta messaging.
- Any Beta influence on Score or action context.

V8 remains non-operational pending broader backtest execution, review of the unfavorable 10-stock sample, and explicit user signoff supported by expanded evidence.

Canonical validation evidence:

```text
backtests/V8_ETF_Phase2/runs/V8ETF_20260711T135316Z_6fa10c6
docs/V8_ETF_PHASE2_CONCLUSION_2026-07-11.md
```

Comprehensive backtest specification:

```text
docs/V8_COMPREHENSIVE_BACKTEST_PLAN_2026-07-12.md
```

The existing ETF validation proves sample mapping quality and production-path behavior. ETF mapping is not a momentum-performance feature and has no predictive or scoring mandate. Historical ETF rows, where retained, are audit context only and require appropriately dated holdings evidence.

Completed 10-stock technical evidence:

```text
backtests/V8_Comprehensive/runs/V8FULL_20260711T192053Z_ffe1567_20260712
docs/V8_COMPREHENSIVE_BACKTEST_CONCLUSION_2026-07-12.md
```

The execution did not change this output contract. Score invariance passed on all 620 replayed rows. The same-quarter ETF analysis is assumption-limited and the momentum results do not support V8 operational activation.

Directional validation evidence:

```text
backtests/V8_Directional_Persistence/runs/V8DIR_20260711T193832Z_0568444
docs/V8_DIRECTIONAL_PERSISTENCE_CONCLUSION_2026-07-12.md
```

The directional test does not change `Score`, decisions, ETF triggering, or output fields. It defines the research gate as D+1 Close above D Close, with D+5 and D+8 used as persistence references.

Alternate-code evidence:

```text
docs/V8_ALT_CODES_DIRECTIONAL_CONCLUSION_2026-07-12.md
```

PANW replaced XOM without changing this output contract. The alternate run identified a possible confirmation-lag issue but made no scoring or gate change.

## Enforced Foundation Contract

Default periods:

```text
8/21/5
```

Configurable CLI fields:

```text
--macd-fast
--macd-slow
--macd-signal
```

Output fields:

```text
MACD_Fast_Period
MACD_Slow_Period
MACD_Signal_Period
MACD_Line
MACD_Signal_Line
MACD_Histogram
MACD_Bullish_Positive
Foundation_Status
Foundation_Qualified
Foundation_Reason
Foundation_Policy
```

The first-stage qualification rule is:

```text
Close > EMA200
AND MACD_Line > MACD_Signal_Line
AND MACD_Line > 0
```

Only `FOUNDATION_VALID` proceeds to benchmark, Setup/Momentum scoring, intraday confirmation, external messages, and ETF context. A price-above-EMA200 MACD reset publishes `MOMENTUM_PRESENT_WAIT_CONFIRMATION` with Score `0`; below EMA200 or insufficient data publishes `REJECT` with Score `0`.

Changing the configurable periods can therefore change `Foundation_Status` and downstream eligibility. It does not directly add score points. `--foundation-policy audit` is reserved for regression analysis and calculates legacy downstream decisions without enforcing the first-stage stop.

Research evidence:

```text
docs/V8_MACD_RESEARCH_CONCLUSION_2026-07-12.md
docs/V1_V8_EMA200_MACD_FOUNDATION_DISCOVERY_2026-07-12.md
docs/V8_FOUNDATION_VALIDATION_CONCLUSION_2026-07-12.md
```

The lineage review confirms that V1-V3 required EMA200 and MACD before Phase-2 scoring, while V4 removed MACD during the long-term-engine rewrite. The restored `Foundation_Status` is now part of the mainline V8 contract. Evidence is recorded in `docs/V8_FOUNDATION_VALIDATION_CONCLUSION_2026-07-12.md`.

If an existing append-only execution log has the pre-foundation header, V8 preserves it and opens a timestamped log with the current schema.
