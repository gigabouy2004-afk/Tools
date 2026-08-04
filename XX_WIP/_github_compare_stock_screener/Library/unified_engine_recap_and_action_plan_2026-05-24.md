# Unified Engine Recap And Action Plan

Date: 2026-05-24

Branch / worktree: `feature/unified-engine-v2-worktree`

Primary worktree: `D:\Stock_Screener_2026_Unified`

Fallback reference app: `D:\Stock_Screener_2026`

## 1. Executive Summary

The new scanner is a web-based, ad-hoc Technical Analysis scanner. The user provides stock symbols through CSV upload, manual comma-separated input, or both. The scanner must quickly baseline each stock, determine the correct stage path, calculate only the indicators needed for that path, classify the result, and show clear reasons.

The core design decision is:

```text
Baseline first -> route the path -> calculate only required evidence -> classify stage
```

The engine must not become indicator-first. It should not calculate all MACD timeframes, RSI, ADX, Bollinger, Momentum History, and future modules for every stock before knowing why those values are needed.

## 2. Current Objective

Build a clean v2 engine and web shell while preserving the original app as fallback/reference.

The new engine must keep the original purpose:

- Fast market-review scanner.
- User-driven execution.
- Clear stage classification.
- Explainable results.
- Functional logging and error handling.
- Configurable defaults outside decision code.
- Future extensibility without breaking the core baseline/stage-processing model.

The scanner is not intended to be:

- Automated trading.
- Order execution.
- Capital allocation.
- Position sizing engine.
- Final stop-loss/trade-management system at this stage.

## 3. Source Systems And Roles

The old systems are references, not final architecture.

`Version 11` is the business-logic reference:

- TA scoring ideas.
- Daily/hourly calculations.
- Quality scoring.
- Promotion/degradation/status-quo concepts.
- MACD early-detection logic where useful.

`PMDE` is the architecture reference:

- Compute calculates only.
- Decision layer classifies.
- Explanation/audit explains.
- Output contracts stay structured.

`Current web_app.py` is the runtime/UI reference:

- Web UI.
- CSV/manual symbols.
- Filters.
- Async progress.
- Results table.
- Logging/audit.

## 4. Agreed Stage Families

The scanner has four first-class stage families:

- `Crossover`
- `Divergence`
- `Momentum Trading`
- `Status Quo`

The old `Setup` name is retired. The correct name is now `Momentum Trading`.

## 5. Path-First Engine Model

The current engine model is L1/L2/L3.

### L1 Baseline

L1 establishes the current technical state before stage classification.

Primary question:

```text
Is the stock currently Bull, Bear, Neutral/Mixed, or Insufficient?
```

Baseline is not the final stage. It only determines the path.

The working baseline should be configurable. Daily classical MACD-style baseline is the current working assumption, but exact values must remain in config.

### L2 Stage Router

L2 is a practical hardcoded router for now. It is not a full matrix/schema engine yet.

Current routing:

```text
If baseline is Bear:
  check Pre-Bull Crossover
  check Bearish Divergence
  check Momentum Trading only if selected and relevant
  otherwise Status Quo

If baseline is Bull:
  check Bullish Divergence
  check Pre-Bear Crossover
  check Momentum Trading only if selected and relevant
  otherwise Status Quo

If baseline is Neutral/Mixed/Insufficient:
  classify Status Quo unless selected rules provide enough evidence
```

L2 must respect the stage families selected by the user.

### L3 Indicator Functions

L3 contains independent function modules. L2 calls them only when needed.

Current and future examples:

- `MACD`
- `RSI`
- `ADX`
- `Bollinger`
- `Volume`
- `PriceBand`
- `StopLoss`
- `MomentumHistory`
- `GetAI`

Important rule:

```text
L3 calculates values. L2 decides when to calculate. Stage rules decide meaning.
```

## 6. Crossover Understanding

Crossover means transition, not already-established regime.

It should detect:

- Bullish MACD/signal crossover.
- Bearish MACD/signal crossover.
- Pre-bull crossover possibility.
- Pre-bear crossover possibility.
- Fresh vs stale crossover.
- Zero-line context separately.

The old histogram confusion must not return:

```text
Do not require histogram > 0.5 for generic Crossover.
Do not require MACD > 0.5 for Pre-Bull Crossover.
Use histogram only to confirm the cross is real/non-flat.
Record zero-line context separately.
```

Lower timeframes such as 4H and 1H can be used for timing/confirmation, but they should be calculated only after the Crossover path needs them.

## 7. Divergence Understanding

Divergence means price/momentum disagreement.

It should detect:

- Raw bullish divergence.
- Raw bearish divergence.
- Confirmed bullish divergence.
- Confirmed bearish divergence.

Raw divergence is evidence, not automatically a final candidate.

The histogram rule:

```text
Use histogram swing comparison.
Do not apply a universal histogram > 0.5 gate.
Do not suppress raw divergence because of a generic strength threshold.
Promotion requires confirmation.
```

## 8. Momentum Trading Understanding

Momentum Trading is a separate stage family. It replaces `Setup`.

The Momentum Trading document applies only to Momentum Trading. It must not change Crossover or Divergence rules.

Momentum Trading uses stock-specific historical MACD behavior:

- Data source: YFinance historical dataframe.
- Required input: Close price.
- Default lookback: one year.
- Default interval: daily.
- Default MACD: `8,21,5`.
- Volume is optional confirmation, not part of baseline MACD calculation.
- OHLC fields are not required for the MACD baseline from the document.

Momentum Trading calculates:

- Bull/bear histogram phases.
- Consecutive phase episodes.
- Magnitude.
- Frequency.
- Duration.
- Maturity.
- Current phase strength compared to the stock's own history.

Open Momentum Trading decisions for later:

- Exact pass/fail gates.
- Long-only initial scope.
- RSI headroom impact.
- ADX confidence impact.
- Volume/liquidity validation.
- Price structure confirmation.
- Extension/chase-risk penalty.
- Ranking early strong momentum vs mature strong momentum.

## 9. Status Quo Understanding

Status Quo is a valid stage family, not just a failure.

It applies when baseline exists but selected stage evidence is not enough for Crossover, Divergence, or Momentum Trading.

Examples:

- Bull but no actionable bullish divergence or pre-bear crossover.
- Bear but no actionable pre-bull crossover or bearish divergence.
- Neutral/mixed with no strong selected-stage evidence.
- Insufficient data.
- Stale signal.

Status Quo should still explain the result.

## 10. Configuration And Text Externalization

Defaults must live outside decision code.

Configurable parameters include:

- MACD values.
- Baseline MACD values.
- RSI period/limits.
- ADX period/limits.
- Bollinger settings.
- Crossover freshness.
- Crossover minimum histogram/spread.
- Divergence lookback/recent window.
- Momentum Trading lookback/MACD/maturity values.
- Volume thresholds.
- Worker/batch sizes.

UI text should also live outside code. The current `ui_text.json` is the first i18n-style catalog.

## 11. Performance And Operations

Speed matters because scans may run in live-market conditions.

Required behavior:

- Process only selected stage families.
- Fetch baseline data first.
- Fetch 4H/1H data only when needed.
- Avoid unnecessary metadata/profile calls.
- Keep symbol failures isolated.
- Use controlled concurrency.
- Stream progress to UI.
- Preserve auditability.

Adaptive batch loading is required:

- Start with a smaller first batch.
- Increase later batch sizes.
- Stop at configured max batch size.
- Stop at lower of `Max Symbols` or total input symbols.
- Log batch number, size, processed count, and remaining count.

## 12. Current Implementation State

Current v2 artifacts:

- `web_app_v2.py`: new web shell.
- `ui_text.json`: first UI text catalog.
- `engine_v2/config.py`: engine defaults.
- `engine_v2/data_provider.py`: YFinance provider and 4H resampling.
- `engine_v2/indicators.py`: compute-only indicator functions.
- `engine_v2/compute.py`: current early compute wrapper.
- `Library/unified_stock_scanner_engine_design.md`: full design document.
- `Library/unified_engine_recap_and_action_plan_2026-05-24.md`: this recap/action plan.

Known implementation correction needed:

```text
engine_v2/compute.py currently calculates too many indicators up front.
It must be refactored into L1 baseline first, then L2-routed, L3-on-demand calculation.
```

## 13. Tomorrow Action Plan

### Step 1: Freeze Current Direction

- Review this recap and the full design document.
- Confirm the four stage families.
- Confirm the L1/L2/L3 model.
- Confirm that full matrix/schema mapping is future scope, not tomorrow's implementation.

### Step 2: Refactor Engine Entry Point

- Replace the current all-indicator `compute_symbol_indicators` flow.
- Create explicit L1 baseline function.
- Return baseline state, reason, and only baseline values.
- Keep baseline config externalized.

Target modules:

- `engine_v2/baseline.py`
- `engine_v2/compute.py`
- `engine_v2/config.py`

### Step 3: Add L2 Stage Router

- Create an explicit stage router.
- Route by baseline and selected stage families.
- Return selected path, skipped paths, and reason.

Target module:

- `engine_v2/stage_router.py`

### Step 4: Add L3 On-Demand Indicator Calls

- Keep `indicators.py` compute-only.
- Add small helper functions for only the indicators needed by a routed path.
- Stop calculating 1D/4H/1H MACD globally.

Initial L3 paths:

- Crossover path: MACD detail and lower timeframe confirmation only when needed.
- Divergence path: swing/histogram evidence only when needed.
- Momentum Trading path: placeholder call only until rules are finalized.
- Status Quo path: baseline + minimal explanatory values only.

### Step 5: Implement Basic Stage Outputs

- Produce real stage labels instead of `UNCLASSIFIED`.
- Use conservative classification first.
- Avoid over-promoting weak evidence.

Initial labels:

- `PRE_BULL_CROSSOVER`
- `PRE_BEAR_CROSSOVER`
- `BULLISH_CROSSOVER`
- `BEARISH_CROSSOVER`
- `RAW_BULLISH_DIVERGENCE`
- `RAW_BEARISH_DIVERGENCE`
- `BULL_STATUS_QUO`
- `BEAR_STATUS_QUO`
- `NEUTRAL_STATUS_QUO`
- `INSUFFICIENT_DATA`

### Step 6: Preserve Logging And Error Handling

- Log L1 baseline decision.
- Log L2 path decision.
- Log L3 functions called.
- Log provider and calculation errors per symbol.
- Ensure one bad symbol does not fail the whole run.

### Step 7: UI Verification

- Keep UI simple.
- Keep `Run Scan` as the main operation.
- Ensure stage-family checkboxes pass into the engine.
- Ensure results show baseline, detected stage, reason, and key values.

### Step 8: Smoke Test

Run a small manual-symbol test:

```text
MSFT,AAPL,NVDA,TSLA
```

Verify:

- Symbols load correctly.
- Batch logic runs.
- Baseline appears.
- Stage is not `UNCLASSIFIED`.
- L3 calls match the routed path.
- No generic `histogram > 0.5` gate is used for Crossover/Divergence.

## 14. Tomorrow Success Criteria

Tomorrow's work is successful if:

- v2 still runs from the clean worktree.
- The fallback app remains untouched.
- The engine starts with L1 baseline.
- L2 route is visible in result/audit.
- L3 functions are called on demand.
- Results classify into at least Crossover/Divergence/Status Quo placeholders without abusing Momentum Trading rules.
- Momentum Trading remains isolated as a placeholder until its separate rule discussion.

