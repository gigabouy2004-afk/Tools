# PMDE vNext Architecture Guardrails

PMDE exists for capital investment, capital protection, and long-term growth assessment. It is not an intraday trading engine.

## Layer Responsibilities

### Main

`main.py` is operational glue only.

It may load the symbol list, call L1, record execution output, update the baseline registry, and handle failures.

It must not calculate MACD, EMA, RSI, ADX, OBV, ATR, EPS, gross margin, or any other indicator/factor.

### L1

L1 performs the initial stock-code assessment.

It may read basic stock information needed to decide whether a baseline is missing, changed, or suspicious.

It must not calculate technical indicators or interpret indicator results.

When `ENGINE_MODE="QUICK_SETUP"`, L1 becomes mode-aware only as an entry gate. It must tag the run as `QUICK_SETUP_REQUESTED` and escalate to L2. The setup decision itself remains owned by L2.

When `ENGINE_MODE="QUICK_CROSSOVER"`, L1 tags the run as `QUICK_CROSSOVER_REVIEW` and escalates the symbol to L2. CRS produces a baseline record so `main.py` can refresh `ACTIVE_BASELINE.csv` after successful processing.

When L1 detects a missing, changed, or suspicious baseline condition, it escalates to L2.

When full validation is forced by configuration, L1 uses `FORCED_L2_REVIEW` rather than marking the regime unstable. This means L2 was run because the user asked for a full scan, not because L1 found an unstable baseline.

### L2

L2 is the key decision engine.

It decides which indicators and generic facts are required for the current assessment. It calls L3 for computation and interprets the returned values in the context of capital protection and investment growth.

In `QUICK_SETUP` mode, L2 uses a staged setup policy:

- `PRICE_LADDER_CONTEXT` is the first gate. It checks completed daily closes: `P0 > P-1`, `P0 > P-X`, and minimum advance from `P-X` to `P0`.
- MACD is the second gate and uses `8,21,5`. It is interpreted top-down only: 1D must be constructive before 4H is inspected, and 4H must be constructive before 1H is used as the current-hour trigger.
- Support filters then validate EMA200 structure, RSI, ADX/DMI, OBV, CMF, ATRP, price context, and current-session extension.
- `QUICK_SETUP` output contains only confirmed setup rows when `SETUP_OUTPUT_ONLY_CONFIRMED=True`. Rejected symbols are counted as filtered out, not written as stock-code rows.

Current tactical states are centered on crossover anticipation:

- `PRE_BEAR_CROSSOVER`: capital protection warning before a full bearish 1D crossover is confirmed.
- `BEAR_CROSSOVER_CONFIRMED`: capital protection state after higher timeframe bearish confirmation.
- `BULL_STRUCTURE_PULLBACK_RISK`: daily bull structure remains intact, but lower-timeframe or support indicators show cooling; use risk control, not capital protection.
- `PRE_BULL_CROSSOVER`: accumulation watch before a full bullish 1D crossover is confirmed, only when lower-timeframe recovery is backed by net bullish support.
- `BULL_STRUCTURE_SECURED`: bullish structure is confirmed on higher timeframes.
- `EARLY_RECOVERY_INSIDE_BEAR_STRUCTURE`: lower timeframe recovery exists, but 1D/4H structure remains bearish.
- `STATUS_QUO_NO_CROSSOVER`: mixed or unchanged structure without a confirmed crossover event.
- `INSUFFICIENT_HISTORY_FOR_BASELINE`: tactical classification is withheld because required baseline history, such as EMA200, is not valid.
- `INSUFFICIENT_TECHNICAL_DATA`: L3 could not compute required technical values, usually because ticker history is too short or incomplete.

### L3

L3 is compute-only.

L2 calls L3 methods such as `L3ComputeLayer.MACD(symbol, "1d")`, `L3ComputeLayer.MACD(symbol, "4h")`, and `L3ComputeLayer.MACD(symbol, "1h")`.

L3 returns computed values only. It must not produce tactical states, capital actions, or semantic explanations.

Current L3 technical capabilities include MACD, PPO, RSI, ADX/DMI, OBV, CMF, ATRP, EMA200 slope/distance, 52-week price context, and current-session context.

Quick setup also uses `PRICE_LADDER_CONTEXT`, which returns `P0`, `P-1`, `P-X`, advance percentage, and higher/lower close counts from completed daily closes.

Optional L3 contextual capabilities include broad-market context and related-instrument context. For example, AMD can be mapped to leveraged or inverse AMD-related instruments such as AMDL, ADMY, AMDU, and AMDS. These context hooks are disabled by default in `ACTIVE_CONTEXTS` so the core engine remains deterministic and fast.

Future L3 engines may include EPS, gross margin, earnings-date validation, analyst-call extraction, sentiment analysis, lifetime high, and time-to-EMA200 calculations.

### L4

L4 prepares semantic messages from L2 decisions and L3 computed values.

It must not select indicators, compute indicators, or change tactical decisions.

## Configuration Contract

All run-time configuration lives in `CONFIG/settings.py`.

Engine modes:

- `FULL_BASELINE`: full/deep PMDE baseline mode. Symbols are loaded from the configured input sources. New symbols are added to `ACTIVE_BASELINE.csv`; existing symbols are replaced with their latest processed state.
- `QUICK_CROSSOVER`: crossover review mode. Symbols are loaded from prior baseline rows whose `tactical_state` is in `QUICK_CROSSOVER_BASELINE_STATES`, plus any explicit input symbols provided through file, hardcoded, or fallback config. Successful symbols refresh `ACTIVE_BASELINE.csv`. The CRS report is filtered to `QUICK_CROSSOVER_STATES` when `QUICK_CROSSOVER_OUTPUT_ONLY_PROBABLES=True`.
- `QUICK_SETUP`: standalone setup mode. Symbols are loaded only from the configured input sources, evaluated through the setup policy, and only confirmed setup rows are written when `SETUP_OUTPUT_ONLY_CONFIRMED=True`. QS does not read or update the active baseline.

Path configuration:

- `PROJECT_ROOT` is resolved from the repository location.
- `BASELINE_FILE` points to `STORAGE/ACTIVE_BASELINE.csv`.
- `EXECUTION_REPORT_FILE` controls the output CSV path.
- `INPUT_FILE` controls the symbol source file.

Indicator configuration:

- MACD uses `MACD_FAST`, `MACD_SLOW`, and `MACD_SIGNAL`.
- EMA baseline uses `EMA_PERIOD` and `EMA_SLOPE_LOOKBACK`.
- RSI, ADX/DMI, CMF, ATRP use their configured periods and risk thresholds.
- `ACTIVE_INDICATORS` controls technical indicators requested by L2.
- `ACTIVE_GENERIC_FACTS` controls non-indicator facts requested by L2, currently including `EMA200`, `PRICE_CONTEXT`, and `SESSION_CONTEXT`.
- `ACTIVE_CONTEXTS` is reserved for optional broad-market and related-instrument context.

Data configuration:

- `DATA_INTERVALS` maps logical timeframes to yfinance intervals.
- `DATA_PERIODS` controls historical lookback for each timeframe.
- `USE_LIVE_PRICE_FOR_DAILY=True` overlays the latest regular-session price into the daily candle.
- `LIVE_PRICE_PREPOST=False` keeps premarket and after-hours ticks out of the main daily technical candle.
- Premarket/after-hours behavior should be added later as a separate L3 context, not mixed into EMA/MACD/ADX candle calculations.

Session context:

- `SESSION_EXTENDED_MOVE_PCT` marks a stock as extended up/down for the current session.
- `SESSION_GAP_MOVE_PCT` marks opening gap conditions.
- L2 can use this to change a constructive pre-bull setup from `ACCUMULATION_WATCH` to `WATCH_NOT_CHASE`.

## Ticker Processing Contract

Symbol processing is owned by `IO/symbol_loader.py` and orchestrated by `main.load_symbols()`.

Ticker sources are separate and then merged:

- File symbols from `INPUT_FILE`.
- Hardcoded ad-hoc symbols from `HARDCODED_SYMBOLS`.
- Fallback symbols from `FALLBACK_SYMBOLS`.

In `QUICK_CROSSOVER` mode, the run list is the union of:

- Baseline watchlist symbols from `ACTIVE_BASELINE.csv`, selected by `QUICK_CROSSOVER_BASELINE_STATES`.
- Explicit input symbols from `INPUT_FILE`, `HARDCODED_SYMBOLS`, and `FALLBACK_SYMBOLS` when provided.

This lets CRS recheck prior near-crossover symbols while also accepting new ad-hoc codes. If explicit input sources are empty, CRS still runs against the baseline watchlist. If the baseline watchlist is empty but input symbols exist, CRS runs only those input symbols and adds successful results to `ACTIVE_BASELINE.csv`.

The final run list is normalized, de-duplicated, and sorted when `SORT_UNIQUE_SYMBOLS=True`.

Input files may be CSV, XLS, or XLSX. For CSV files, the loader detects whether the first row looks like a header. If no symbol column is configured, it looks for common names such as `symbol`, `ticker`, `code`, `tradingsymbol`, and similar variants. If multiple columns exist and no symbol-like column can be inferred, the run fails with a clear input error.

Exchange handling:

- If a symbol already contains a suffix such as `.NS` or `.BO`, it is preserved.
- If an exchange column or `DEFAULT_EXCHANGE` is configured, `NSE` maps to `.NS` and `BSE` maps to `.BO`.
- Blank, malformed, header-like, or non-symbol values are ignored during normalization.

If the file source fails but hardcoded or fallback symbols exist, the run may continue with warnings. If no usable symbols exist across all configured sources, `main.py` writes an input-load failure report and exits.

## Data Loading Contract

`IO/data_loader.py` owns market data loading and caching.

Data is loaded through yfinance using the configured timeframe period and interval. A per-symbol/timeframe cache prevents repeated downloads inside one run.

Daily data:

- Uses `DATA_PERIODS["1d"]`, currently 5 years.
- Can receive a regular-session live price overlay when `USE_LIVE_PRICE_FOR_DAILY=True`.
- The live overlay uses `LIVE_PRICE_INTERVAL`, currently `1m`, and `LIVE_PRICE_PERIOD`, currently `1d`.
- The overlay updates the latest daily close, high, low, open, and volume for the current session where available.

4H data:

- Is built by loading 1H data and resampling to 4H OHLCV.

EMA200 validity:

- EMA200 is only valid when at least 200 daily closes exist.
- If fewer than 200 closes exist, L3 returns an EMA result with `is_sufficient=False`, `zone=INSUFFICIENT_HISTORY`, and a clear reason.
- L2 must withhold tactical classification and return `INSUFFICIENT_HISTORY_FOR_BASELINE` when the EMA200 baseline is required but insufficient.

## Output Report Contract

Reports are written by `OUTPUT/execution_reporter.py`.

## Active Baseline Contract

`STORAGE/ACTIVE_BASELINE.csv` is a latest-state registry, not a run-history store.

- It contains one active row per symbol.
- FB and CRS update it after successful processing.
- QS does not read from it and does not write to it.
- New symbols are appended as new active rows.
- Existing symbols are replaced case-insensitively with the latest processed row.
- Historical prices and indicator inputs remain reproducible from Yahoo Finance, so PMDE does not duplicate run history.
- Baseline rows include `timestamp` for PMDE processing time and `data_fetch_timestamp` for the market-data fetch/cache time.

The report file starts with metadata:

- Engine name, version, run timestamp, input file.
- Symbol-source counts.
- Active settings such as MACD parameters, live-price settings, data periods, and active generic facts.

The metadata section is followed by an execution summary:

- `TOTAL_SYMBOLS`
- `SUCCESS_COUNT`
- `FAILED`
- Tactical-state counts and percentages.
- `RUN_MODE`

The data table follows the summary.

Primary workflow columns:

- `Symbol`
- `Zone`
- `L1_State`
- `L1_Reason`
- `L2_Hypothesis`
- `Capital_Action`
- `L2_MACD`
- `L2_Confidence`
- `L2_Indicators_Used`
- `L3_Substantiation`
- `PMDE_Explanation`

`PMDE_Explanation` must remain immediately next to `L3_Substantiation` so the user can filter rows and then read the explanation without scrolling to the far right.

State and context column groups:

- `Final_State`, currently the same tactical state as `L2_Hypothesis`.
- Momentum and participation: `Momentum_State`, `Participation_State`, `Trend_Strength_State`, `Exhaustion_State`, `Volatility_State`.
- Session context: `Session_State`, `Session_Change_Pct`, `Opening_Gap_Pct`, `Intraday_Change_Pct`, `Gap_State`.
- EMA baseline: `EMA200`, `EMA200_Status`, `EMA200_Data_Points`, `EMA200_Reason`, `Latest_Price`, `EMA200_D_Pct`, `EMA200_Slope_Pct`, `EMA200_Slope_State`.
- MACD values: 1H, 4H, and 1D MACD, signal, and histogram.
- Support indicators: PPO, RSI, ADX/DMI, OBV, CMF, ATRP.
- Price context: 52-week high/low, distance from high/low, and `Price_Context_State`.

If the target output file is open or locked, the reporter writes a timestamped fallback file beside it rather than losing the run.

## Error Handling Contract

Input-load failure:

- If symbols cannot be loaded from any configured source, `main.py` records an `INPUT_LOAD` failure report and exits.

Per-symbol failure:

- If a symbol raises an unhandled exception, `main.py` records a row with `L1_State=FAILED`, `L2_Hypothesis=FAILED`, `Final_State=FAILED`, and the error text in `PMDE_Explanation`.

Per-indicator failure:

- L2 catches L3 computation errors per requested indicator.
- If required MACD timeframes are incomplete, L2 returns `INSUFFICIENT_TECHNICAL_DATA / REVIEW_MANUALLY`.
- The L4 explanation includes the L3 error list.

Insufficient baseline history:

- If EMA200 has fewer than 200 daily closes, L2 returns `INSUFFICIENT_HISTORY_FOR_BASELINE / REVIEW_MANUALLY`.
- This is not bullish, bearish, unstable, or a capital action. It is a data-validity block.

Forced full scans:

- With `FORCE_L2_ASSESSMENT=True`, all symbols go through L2.
- These rows must show `L1_State=FORCED_L2_REVIEW`, not `REGIME_UNSTABLE`.
- `REGIME_UNSTABLE` is reserved for real L1 baseline problems such as invalid latest price, missing baseline, invalid previous baseline price, or price-change trigger when forced mode is off.

## Current Active Scope

Active technical indicators are MACD, PPO, RSI, ADX/DMI, OBV, CMF, and ATRP.

EMA200, 52-week price context, and session context are active as generic contextual facts.

Market and related-instrument context are available in L3 but disabled by default.

Future indicators and AI-driven context should be enabled through L2 planning, not by adding calculations to `main.py` or L1.
