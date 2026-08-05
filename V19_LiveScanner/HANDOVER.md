# V19 Momentum Engine — Technical and Analytical Handover

**Handover date:** 2026-08-06

**Project location:** `D:\Tools\V19_LiveScanner`

**Repository:** `https://github.com/gigabouy2004-afk/Tools`

**Release state:** V19.1 validated and ready for controlled extension

**Prepared by:** Codex (OpenAI)

## 1. Executive summary

V19 is a standalone deterministic momentum-classification engine. It uses
completed daily market data through D-1 and does not use any part of the D
candle when deciding whether a security qualifies.

The engine has two supported operating paths:

1. `Live_Scanner_v19.py` performs a live or single-date historical scan and
   writes the established five-sheet Excel review workbook.
2. `V19_Backtest_Matrix.py` performs scalable code/date matrix testing and
   writes one flat CSV containing the qualification calculations and the D
   opening outcome for every code/date combination.

The expanded 2,000-combination study established that V19 is a selective
**Full Blown Bull** classifier, but is not by itself a predictor that D will
open above D-1 Close. V19 should therefore remain frozen as the foundation
classification layer. A future entry-timing layer must be developed and
validated separately.

## 2. Frozen V19 qualification contract

A code qualifies only when all three compulsory groups pass using adjusted
daily data through D-1:

### 2.1 Bull zone

- D-1 Close > EMA50.
- D-1 Close > EMA200.
- EMA20 is deliberately excluded from the V19 foundation.

### 2.2 MACD buyer zone

- MACD uses 12/26/9 exponential moving averages.
- MACD line > 0.
- MACD signal > 0.
- MACD line > MACD signal.

### 2.3 Multi-period price movement

- Short window: 21 completed sessions.
- Medium window: 63 completed sessions.
- Long window: 126 completed sessions.
- Tier 1: all three returns are at least 20%.
- Tier 2: all three returns are at least 10%.
- A security below the Tier 2 requirement in any window is rejected.

### 2.4 Stochastic interpretation

- Standard slow stochastic 14/3/3.
- Calculated only after the three compulsory groups qualify.
- Fresh bullish crossover: K was at or below D on D-2 and is above D on D-1.
- Preferred midpoint zone: 45 to 55.
- Recent oversold reference: slow K reached 20 or below within 14 sessions.
- Stochastic remains descriptive in V19 and does not alter the tier.

### 2.5 Invalid data policy

Missing, malformed, insufficient or non-finite price data produces
`INVALID_DATA` for that code/date. The error is recorded and processing
continues for all remaining work.

## 3. Backtesting convention

The qualification boundary and outcome boundary are intentionally separate:

- Indicators and qualification use completed candles strictly before D.
- D-1 is the latest available trading session before D; it is not assumed to
  be the previous calendar day.
- D-2 and earlier candles are used wherever the calculation requires them.
- The D candle cannot affect EMA, MACD, returns, stochastic or tier.
- The backtest outcome is the adjusted opening price on D.
- Positive D opening is defined as `D Open > D-1 Close`.
- `D_Open_Gap_Return = (D Open / D-1 Close) - 1`.
- D Open and D-1 Close use the same auto-adjusted price basis.
- External events are not separate model inputs, although their market effect
  is naturally reflected in the observed D opening price.

This isolation is covered by deterministic tests that materially change the D
candle and confirm that the V19 qualification remains unchanged.

## 4. Delivered files

| File | Purpose |
|---|---|
| `Live_Scanner_v19.py` | Single-date live/backtest engine and Excel output |
| `V19_Backtest_Matrix.py` | Scalable code × date CSV backtest runner |
| `tests/test_v19_engine.py` | Core V19 qualification, retry, input and workbook tests |
| `tests/test_v19_backtest_matrix.py` | Matrix, no-D-leakage, date-range and one-download tests |
| `README.md` | Installation, CLI usage and operating examples |
| `requirements.txt` | Minimum Python package requirements |
| `.gitignore` | Excludes generated output and Python caches |

## 5. Scalable matrix runner

`V19_Backtest_Matrix.py` evaluates the Cartesian product of the supplied codes
and dates. Each symbol's required Yahoo history is downloaded once across the
complete requested date span, then sliced independently for each D using the
same 1,100-calendar-day history window as the base engine.

Supported inputs:

- Codes supplied directly with `--codes`.
- Codes read from the first column of CSV, TXT or XLSX with `--input-file`.
- Explicit dates supplied with `--dates`.
- Dates read from the first column of CSV, TXT or XLSX with `--dates-file`.
- An inclusive trading-date range supplied with `--date-range START END`.
- Range dates are resolved from SPY by default; `--calendar-symbol` overrides
  the calendar proxy.

The output is an atomic UTF-8 CSV with one row per code/date combination. It
contains identifiers, D-1 baseline, D opening outcome, all EMA/MACD/return
calculations, qualification tier, rejection reasons, stochastic values,
integrity state, retry details and error information.

### Example: one code over a long trading-date range

```powershell
python .\V19_Backtest_Matrix.py `
  -c NVDA `
  --date-range 2022-01-01 2026-07-31 `
  -o D:\TMP\NVDA_Backtest.csv
```

### Example: a complete code library for one historical date

```powershell
python .\V19_Backtest_Matrix.py `
  -i D:\path\NASDAQ_Codes.csv `
  -d 2025-07-15 `
  -o D:\TMP\NASDAQ_Backtest.csv
```

### Example: separate code and date files

```powershell
python .\V19_Backtest_Matrix.py `
  -i D:\path\Stock_Codes.csv `
  --dates-file D:\path\Backtest_Dates.csv `
  -o D:\TMP\V19_Matrix.csv
```

## 6. Validation record

### 6.1 Automated verification

- 21 deterministic tests passed on 2026-08-06.
- Both Python entry points compile successfully.
- The test suite covers input validation, retries, multithreading, terminal
  states, tier thresholds, completed-candle exclusion, stochastic handling,
  workbook structure, matrix date resolution and atomic CSV output.
- The D-candle isolation test confirms that D Open/High/Low/Close can change
  the outcome without changing any D-1 qualification calculation.
- The matrix download test confirms one history request per symbol even when
  multiple dates are evaluated.

Run the complete verification suite with:

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
python -m py_compile .\Live_Scanner_v19.py
python -m py_compile .\V19_Backtest_Matrix.py
```

### 6.2 Live-data smoke validation

- 3 symbols × 3 dates = 9 CSV rows.
- Three Yahoo history requests, not nine.
- Zero retries, provider failures or invalid rows.
- Every D-opening outcome was present and valid.

### 6.3 Expanded foundation study

Test design:

- 100 liquid US-listed stocks.
- 11 broad sector groups.
- 20 trading dates from 2024-01-16 through 2026-06-15.
- 2,000 unique code/date combinations.
- Fixed stock universe across all dates.
- Adjusted D Open compared with adjusted D-1 Close.

Processing result:

| Status | Count |
|---|---:|
| Tier 1 | 14 |
| Tier 2 | 115 |
| Total qualified | 129 |
| Rejected | 1,871 |
| Invalid | 0 |

D-opening result:

| Population | Positive / Total | Positive rate |
|---|---:|---:|
| All combinations | 1,147 / 2,000 | 57.35% |
| V19 qualified | 74 / 129 | 57.36% |
| V19 rejected | 1,073 / 1,871 | 57.35% |

After matching qualified rows to the market opening rate on each specific D,
73.79 positive qualified openings were expected and 74 were observed. The
foundation therefore produced no measurable directional lift for D Open.

Tier breakdown:

| Tier | Positive / Total | Rate | Median D opening gap |
|---|---:|---:|---:|
| Tier 1 | 6 / 14 | 42.86% | -0.56% |
| Tier 2 | 68 / 115 | 59.13% | +0.13% |

Stochastic breakdown:

| State | Positive / Total | Rate |
|---|---:|---:|
| Fresh bullish crossover above midline | 6 / 8 | 75.00% |
| Bullish above 50 without fresh crossover | 25 / 46 | 54.35% |
| No bullish crossover | 43 / 75 | 57.33% |

The fresh-crossover result is potentially useful for the next layer but is
not statistically established from eight observations. No qualified case
crossed within the preferred 45–55 midpoint zone, so that condition remains
untested.

## 7. Analytical decision

V19 should be treated as a **market-state and momentum classifier**, not as a
next-opening direction predictor.

The correct architecture is:

1. Keep V19 frozen as the Full Blown Bull foundation.
2. Build a separate entry-timing layer that consumes V19-qualified rows.
3. Give the timing layer its own version, tests and acceptance criteria.
4. Evaluate the timing layer against the matched same-date baseline rather
   than a pooled unconditional rate.
5. Preserve every attempted rule and result to control backtest overfitting.

Initial timing-layer candidates for investigation include fresh stochastic
crossover, sector-relative regime, broad-market opening regime, volume
confirmation, pullback/reclaim structure and ATR-based overextension. These
are research candidates, not approved production rules.

## 8. Known limitations

- Yahoo supplies its currently available adjusted history; historical values
  may be revised.
- The 100-stock study uses a current liquid-stock universe and is not free of
  survivorship bias.
- Twenty dates improve on the earlier sample but still represent only twenty
  independent market mornings; stocks on the same D are correlated.
- The study does not model transaction costs, liquidity at the opening print,
  spreads, slippage or order execution.
- Earnings, news, macro events, futures, pre-market trading and other external
  inputs are intentionally absent.
- The preferred stochastic 45–55 crossover condition had no observations in
  the qualified expanded sample.
- Generated `output/` files are intentionally excluded from Git. The primary
  expanded result remains local at
  `output\foundation_matrix_2000_20260806\V19_PanMarket_2000.csv`.

## 9. Operational safeguards

- Keep Yahoo concurrency bounded; the default is four workers.
- Preserve the global request interval and retry/backoff controls.
- Do not use D candle values as V19 feature inputs.
- Do not overwrite existing output unless `--overwrite` is explicitly used.
- Review `INVALID_DATA`, provider failures and missing D outcomes before
  accepting aggregate statistics.
- Use a fixed code universe when comparing filters across dates.
- Use matched same-date baselines when measuring directional lift.
- Do not alter V19 thresholds while developing the timing layer; fork the new
  behavior into a separately versioned engine.

## 10. Handover acceptance checklist

- [x] V19 qualification contract implemented.
- [x] D-1 candle boundary verified.
- [x] D opening outcome definition agreed and implemented.
- [x] Single-date Excel workflow retained.
- [x] Scalable CSV matrix workflow implemented.
- [x] File I/O and preflight validation implemented.
- [x] Multithreading, pacing and retries implemented.
- [x] Automated tests passing.
- [x] Historical smoke tests completed.
- [x] Expanded 2,000-combination study completed.
- [x] Analytical limitations and next-stage boundary documented.

## 11. Sign-off

V19.1 is handed over as a validated Full Blown Bull classification foundation
with a scalable CSV backtesting facility. No evidence currently supports using
V19 alone to predict that D will open above D-1 Close. Further predictive work
belongs in a separately versioned entry-timing layer.

**Prepared and signed off by:** Codex (OpenAI)

**Date:** 2026-08-06

**Status:** Handover complete; ready for repository synchronization
