# V8 Development Charter

> **SUPERSEDED FOR ACTIVE DESIGN GOVERNANCE — 2026-07-13.** This document is retained as historical audit evidence. New V8 design, implementation, testing and approval must follow `docs/V8_REVISED_DEVELOPMENT_CHARTER_2026-07-13.md` and `docs/MOMENTUM_ENGINE_FOUNDATIONAL_DESIGN_STANDARD_2026-07-13.md`. Nothing in this older chronological record should be interpreted as current approval for inherited post-Foundation scoring or veto rules.

Original date: 2026-07-10

Updated: 2026-07-12

Status: EMA200 plus configurable `8/21/5` MACD is now the enforced V8 Foundation stage. The 20-stock/four-date Q2 foundation, regression, directional, and ETF validation passed independently. V8 remains development-only pending joint result review and broader multi-regime signoff.

Analysis clarification dated 2026-07-13: the required first-read analysis is `docs/V8_EXPERIMENT_ANALYSIS_BRIEF_2026-07-13.md`. It replaces unexplained shorthand, decomposes the MACD Reset population, and records the unresolved freshness-score formula defect and approval items.

## Version Boundary

Version 7 is closed and remains the operational engine. New work occurs only in V8 or V8-specific support files. `Momentum_Detector_V7.py` must not be edited by the V8 ETF track.

V8 was forked from corrected V7 commit:

```text
9a4b0ba Fix V7 score range and append-only execution log
```

Approved V8 presentation defaults remain:

```text
DEFAULT_COUNT_X = 5
DEFAULT_SCORE_Y = 75.0
```

## Beta Track Final Decision

The Beta pilot produced limited descriptive differences but did not provide sufficiently conclusive, independent evidence that Beta reliably explains or predicts forward price movement after an Active Momentum signal.

User decision on 2026-07-11:

- Stop all further Beta research and validation.
- Do not use Beta in `Score`, `Final_Decision`, ranking, allocation guidance, or `Score_Message`.
- Remove the Beta processor and its active development tooling from the V8 production path.
- Preserve the canonical Beta pilot folder and report only as historical audit evidence.

The Beta track is closed without production signoff. It is not a prerequisite for the ETF track after this decision.

## Active V8 Scope: ETF Information Extraction

V8 Phase 2 provides direct stock-to-ETF information for confirmed Active Momentum stocks.

Production trigger:

```text
Final_Decision == MOMENTUM_ACTIVE
AND
Score >= CONFIRMED_ENTRY_MIN_SCORE
```

`CONFIRMED_ENTRY_MIN_SCORE` is currently `85`. The post-processor references the programmed constant. CLI values such as `--score-y` and `--count-x` are presentation controls only and cannot enable or suppress ETF processing.

## User-Facing Contract

The user acts on one numeric field:

```text
Score
```

One string provides ETF context:

```text
Score_Message
```

The ETF processor must never modify `Score`, component scores, final decisions, or ranks.

Example:

```text
Score = 92
Score_Message = Active momentum confirmed. Verified top-10 ETF mappings: SMH 19.20%; VGT 16.77%; FTEC 16.60%.
```

## Phase 2 Requirements

- One stock-specific reverse lookup per eligible Active stock.
- No pan-ETF Yahoo/yfinance holdings loop.
- No per-ETF holdings calls in the live Momentum Detector path.
- USA-listed ETFs only, using the local US ETF master as a whitelist.
- Return at most three eligible ETFs.
- Highest stock holding weight first; ETF ticker is the deterministic tie-breaker.
- Top-ten membership must be proven, never assumed.
- Bounded timeout, persistent TTL cache, explicit failure text, and fail-open behavior.
- API/source failure must leave `Score` byte-for-byte unchanged.

## Phase 2A Source Decision

The current internal implementation uses one direct TradingView stock-to-funds page:

```text
https://www.tradingview.com/symbols/<EXCHANGE>-<STOCK>/etfs/
```

The page provides ETF ticker, listing venue, and stock weight for up to 100 funds holding the stock. It is a direct stock-specific source and does not scan an ETF universe.

TradingView does not publish this page as a stable developer API contract. Therefore:

- The parser is schema-validated and fails open if the page changes.
- Raw response hashes, latency, and source URLs are recorded in validation artifacts.
- The local US ETF master filters non-US funds.
- Leveraged/inverse funds are excluded from the mathematical top-ten proof.
- The implementation is conservative and may omit valid mappings rather than display an unproven top-ten claim.

Financial Modeling Prep was reviewed as a documented direct reverse API candidate. Its published asset-exposure schema provides weights but does not document holding rank/top-ten evidence, and no entitled API key is configured locally. It was not selected for this release.

## Conservative Top-Ten Proof

For a non-leveraged portfolio with non-negative weights summing to 100%, a holding with weight greater than:

```text
100 / 11 = 9.090909...%
```

cannot have ten larger holdings ahead of it. Such a holding is therefore mathematically guaranteed to be within the top ten.

V8 returns only locally whitelisted, non-leveraged USA ETFs passing this strict test. Valid top-ten holdings with lower weights are intentionally omitted because the direct reverse page does not provide rank.

## V8 ETF Files

```text
Momentum_Detector_V8.py
ETF_Context_V8.py
Backtest_Momentum_Detector_V8_ETF.py
config/V8_Post_Processor_Message_Map.csv
tests/test_etf_context_v8.py
```

Historical Beta evidence remains under:

```text
backtests/V8_Beta_Release1/runs/V8BETA_20260710T175207Z_27cee6f_20260710
docs/V8_BETA_RELEASE1_PILOT_2026-07-10.md
```

It is not imported or executed by the active V8 engine.

## Phase 2 Validation Result

Canonical run:

```text
V8ETF_20260711T135316Z_6fa10c6
```

Five stock-specific production requests returned 13 mappings. All 13 mappings passed separate top-ten rank validation and the 60-day freshness rule. Median production-style latency was `155.67 ms`, p95 was `212.51 ms`, and maximum was `226.16 ms`.

Full conclusion:

```text
docs/V8_ETF_PHASE2_CONCLUSION_2026-07-11.md
```

## Comprehensive Backtest Requirement

The five-stock Phase 2 run validates the ETF production path and sample mapping quality. It is not a broad historical test of V8 momentum-signal performance.

Before V8 can replace V7, execute the approved comprehensive plan:

```text
docs/V8_COMPREHENSIVE_BACKTEST_PLAN_2026-07-12.md
```

The plan requires deterministic point-in-time replay, independent Active episodes, chronological validation and final-test partitions, matched WAIT controls, frozen V7 comparison, forward return and drawdown analysis, offline reproducibility, and expanded ETF validation.

Historical ETF results are permitted only when the mapping and holdings evidence existed at the signal date. The current reverse page cannot be applied retrospectively to old signals. If a suitable historical source is unavailable, combined V8-plus-ETF outcome validation must use a prospective shadow cohort.

## 10-Stock Same-Quarter Execution Result

Canonical run:

```text
backtests/V8_Comprehensive/runs/V8FULL_20260711T192053Z_ffe1567_20260712
```

Conclusion:

```text
docs/V8_COMPREHENSIVE_BACKTEST_CONCLUSION_2026-07-12.md
```

The run replayed 620 Q2 daily rows across 10 stocks, checked one deterministic random date per stock, verified 11 same-quarter ETF mappings, preserved Score on all 620 rows, and passed independent validation with zero failures.

The four independent Active episodes returned a mean `-0.49%` over 21 sessions and a mean `-5.13%` versus SPY; only one of four was positive. This is insufficient for broad inference and unfavorable within the tested sample.

ETF mappings used a same-calendar-quarter stability assumption. All accepted holdings evidence was dated 2026-05-29 and passed top-ten validation, but the result is not strict signal-date point-in-time historical evidence.

## D+1 Direction and D+5/D+8 Persistence Result

User clarification establishes that V8 targets multi-day trades, not intraday movement. The immediate validation gate is now:

```text
D+1 Close > D Close
```

D+1 Open and Close are audited. D+5 and D+8 are persistence references.

April date selection used the maximum Active count without looking at forward outcomes. April 30 produced four Active signals: GOOGL, COST, WMT, and XOM.

Canonical run and conclusion:

```text
backtests/V8_Directional_Persistence/runs/V8DIR_20260711T193832Z_0568444
docs/V8_DIRECTIONAL_PERSISTENCE_CONCLUSION_2026-07-12.md
```

Results:

- D+1 direction passed for 1/4 Active signals.
- D+5 persistence passed for 1/4.
- D+8 persistence passed for 2/4.
- Mean Active move was `-0.33%` at D+1, `-0.79%` at D+5, and `-0.55%` at D+8 versus the signal-day Close.
- Independent validation recomputed 80 metrics with zero failures.

The primary D+1 directional hypothesis was not supported in this sample.

## Alternate-Code Result: PANW Replaces XOM

PANW replaced XOM and was independently verified as HACK's number-one holding at `9.65%`, with holdings dated 2026-06-30.

Canonical evidence:

```text
backtests/V8_Comprehensive/runs/V8FULL_20260711T194644Z_3ed85d1_20260713
backtests/V8_Directional_Persistence/runs/V8DIR_20260711T195008Z_3ed85d1
docs/V8_ALT_CODES_DIRECTIONAL_CONCLUSION_2026-07-12.md
```

On April 30, PANW was rejected at Score 16 for weekly downtrend and benchmark underperformance, then gained `0.98%` at D+1, `9.60%` at D+5, and `20.23%` at D+8.

PANW's first Active signal occurred June 9 at Score 100. From that Active date it gained `1.04%` at D+1, `7.44%` at D+5, and `9.93%` at D+8, passing all requested horizons.

The replacement case shows that V8 can identify strong PANW momentum, but only after a material confirmation delay. The common April 30 Active cohort remained below the primary gate at 1/3 D+1 passes.

## Configurable MACD Research

V8 previously had no MACD implementation. V1-V3 used standard `12/26/9`; the initial V8 audit implementation also defaulted to `12/26/9`. The enforced Foundation now defaults to configurable `8/21/5`.

```text
--macd-fast
--macd-slow
--macd-signal
```

Published audit fields:

```text
MACD_Fast_Period
MACD_Slow_Period
MACD_Signal_Period
MACD_Line
MACD_Signal_Line
MACD_Histogram
MACD_Bullish_Positive
```

Historical note: during the first comparison MACD was informational and research-only. It was subsequently promoted to the enforced Foundation stage by explicit user approval. MACD still adds no score points and ETF triggering remains Active-only, but the Foundation result now controls downstream eligibility.

Canonical evidence:

```text
backtests/V8_MACD_Research/runs/V8MACD_20260712T072722Z_1f1ac52
docs/V8_MACD_RESEARCH_CONCLUSION_2026-07-12.md
docs/V1_V8_EMA200_MACD_FOUNDATION_DISCOVERY_2026-07-12.md
```

The corrected foundation study requires both `Close > EMA200` and bullish-positive MACD. The proposed `8/21/5` setting improved D+1 pass rate from `52.63%` under standard `12/26/9` to `62.96%`, across 27 versus 19 episodes. It did not dominate D+5/D+8 persistence.

The first study identified `8/21/5` and `8/21/8` as holdout candidates. `8/21/5` is approved for the V8 development line; multi-regime and untouched-holdout testing remain prerequisites for operational signoff.

Lineage discovery confirms that EMA200 was never removed. MACD was removed in the V3-to-V4 long-term-engine rewrite without a separately versioned rationale. The intended Foundation -> Setup -> Momentum architecture is now recorded for review.

## Foundation Promotion and 20-Stock Validation

On 2026-07-12 the user approved restoring the V1-V3 foundation architecture in mainline V8. The production default is now:

```text
Close > EMA200
AND MACD_Line(8,21,5) > MACD_Signal_Line(8,21,5)
AND MACD_Line(8,21,5) > 0
```

The MACD periods remain configurable. `--foundation-policy enforce` is the production default; `audit` exists for controlled regression comparison.

The foundation executes before benchmark, Setup/Momentum scoring, intraday, external-message, and ETF work. Non-qualified states stop with score `0`:

```text
FOUNDATION_TREND_VALID_MACD_RESET -> MOMENTUM_PRESENT_WAIT_CONFIRMATION
FOUNDATION_INVALID_BELOW_EMA200   -> REJECT
FOUNDATION_INSUFFICIENT_DATA      -> REJECT
```

Canonical evidence:

```text
backtests/V8_Foundation_Validation/runs/V8FOUND_20260712T182945Z_cf0c908
docs/V8_FOUNDATION_VALIDATION_CONCLUSION_2026-07-12.md
docs/V8_FINAL_HANDOVER_2026-07-12.md
```

Across 20 technology stocks and four predeclared Q2 dates, the run produced 80 rows: 25 Foundation Valid, 28 MACD Reset, and 27 Below EMA200. Five rows were Active. Active direction was `4/5` at D+1, `5/5` at D+5, and `4/5` at D+8. All independent implementation, outcome, regression, ETF-quarter, score-invariance, and checksum checks passed.

## Operational Signoff Gates

V8 may replace V7 only after:

- Five-stock ETF validation passes. Completed 2026-07-11.
- Every returned mapping is independently confirmed within the ETF's top ten during validation.
- Exactly one reverse-source request per production stock is proven.
- No production path can call per-ETF holdings pages or a yfinance ETF-universe loop.
- US whitelist, leverage exclusions, ordering, caching, timeout, and failure tests pass.
- `Score` invariance passes.
- ETF message wording is reviewed and approved by the user.
- The 20-stock/four-date foundation backtest and independent offline validation are complete.
- Chronological validation, final-test, ticker-holdout, matched WAIT, V7 comparison, and robustness evidence are reviewed.
- Historical ETF claims use point-in-time evidence, or the prospective-only limitation is explicitly accepted.
- The comprehensive conclusion records the primary endpoint's evidence classification.
- Explicit user operational signoff is recorded.

Until then:

```text
V7 = OPERATIONAL
V8 = DEVELOPMENT / NON-OPERATIONAL
```
