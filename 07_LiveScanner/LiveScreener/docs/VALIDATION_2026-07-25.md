# V14 Enhanced Validation Report — 2026-07-25

## 1. Validation objective

This report records the evidence used to assess whether V14 Enhanced:

- reproduces its own workbook classifications from a fresh data pull;
- detects known positive industrial-sector momentum;
- preserves classification independently of thread order and history-guidance
  scope;
- retains complete final-poll results; and
- exposes signal-quality limitations honestly.

The tests validate repeatability and implementation behavior. They do not prove
future profitability.

## 2. Poll-boundary validation

Synthetic worker tests confirmed:

| Scenario | Expected | Observed |
|---|---|---|
| Unlimited, 7 inputs | Process all 7 | 7 retained |
| Max-Count 4, workers 3 | Finish Poll 2 | 6 retained |
| Max-Buys 2, workers 3 | Finish current poll | 3 retained |
| Real smoke, Max-Count 2, workers 3 | Finish Poll 1 | 3 retained |

No submitted final-poll result was cancelled or discarded.

## 3. XLI top-ten regression

The following XLI holdings were evaluated for 2026-07-22 through 2026-07-24:

```text
CAT, GE, RTX, GEV, UNP, BA, ETN, DE, UBER, PH
```

Results:

| Date | BUY count | BUY symbols |
|---|---:|---|
| 2026-07-22 | 2 | RTX, DE |
| 2026-07-23 | 5 | GE, RTX, UNP, ETN, DE |
| 2026-07-24 | 3 | RTX, UNP, PH |

Signal breakup across the 30 ticker-date observations:

- 6 Momentum Extension;
- 4 Early Momentum.

For the seven signals on 2026-07-22 and 2026-07-23 that had a next completed
session available:

- 6 were positive on the following session;
- next-session win rate was 85.7%; and
- average next-session return was approximately 1.736%.

ETN was the negative exception and illustrates why contextual risk fields and
end-user review remain necessary.

## 4. High-indicator regression

DE as of 2026-02-10 remained a BUY with:

- RSI 81.79;
- prior one-year RSI maximum 80.37;
- ADX 45.11;
- prior one-year ADX maximum 43.08;
- stochastic K/D 99.53/95.50;
- positive previous session;
- effective continuation stochastic limit 100; and
- supportive volume.

This confirms that universal RSI and ADX upper caps are not silently rejecting
strong stock-specific momentum.

The same DE status, output signal, score, confidence, risk level, and stochastic
override were reproduced with MAX and 1Y advisory guidance. Only guidance
values changed.

## 5. Full-U.S. run

Source input:

```text
D:\Tools\00_StockCodeMaster\02_Stock\22-07-US_Common_Stocks_Master_Library.csv
```

Source result retained outside the repository:

```text
D:\TMP\Live_Screener\25-7-2026-ALL-USA-Codes.xlsx
```

Execution:

| Metric | Result |
|---|---:|
| Codes processed | 3,636 |
| Elapsed time | 19m 14s |
| BUY | 74 |
| HOLD | 760 |
| IGNORE | 2,513 |
| ERROR | 289 |
| Guidance scope | 1Y |
| Workers | 3 |

The market was closed during the audit. The run-level date was 2026-07-25; the
latest completed U.S. data session was 2026-07-24.

## 6. Independent fresh-data audit

Nineteen symbols were selected to include:

- high RSI/stochastic BUYs;
- low-volume-ratio BUYs;
- liquid large-cap BUYs;
- HOLD and IGNORE controls; and
- each major ERROR type.

Fresh Yahoo daily history was pulled and the indicators were independently
recomputed. The current enhanced engine was then rerun on the same fresh data.

| Ticker | Workbook | Fresh result | Price | RSI | ADX | Stoch K/D | Volume ratio |
|---|---|---|---:|---:|---:|---:|---:|
| ACU | BUY#3 | BUY#3 | 53.94 | 75.20 | 15.16 | 85.28/46.33 | 3.199 |
| AME | BUY#3 | BUY#3 | 241.97 | 61.04 | 11.23 | 87.79/83.23 | 0.836 |
| NOEM | BUY#3 | BUY#3 | 11.02 | 95.14 | 42.26 | 100.00/100.00 | 2.472 |
| OII | BUY#3 | BUY#3 | 52.73 | 83.52 | 26.30 | 96.92/77.34 | 3.164 |
| LCUT | BUY#3 | BUY#3 | 8.69 | 53.20 | 16.05 | 68.31/67.82 | 0.268 |
| NNBR | BUY#4 | BUY#4 | 3.53 | 57.05 | 33.90 | 73.17/63.12 | 0.300 |
| WBX | BUY#4 | BUY#4 | 3.95 | 46.92 | 30.30 | 20.77/7.03 | 0.358 |
| FTV | BUY#4 | BUY#4 | 62.31 | 55.37 | 12.98 | 84.34/39.23 | 0.824 |
| BRK-B | BUY#4 | BUY#4 | 494.93 | 53.43 | 15.68 | 52.39/27.60 | 0.888 |
| SNA | BUY#4 | BUY#4 | 404.12 | 53.81 | 17.99 | 40.49/35.17 | 1.120 |
| PKG | BUY#3 | BUY#3 | 254.39 | 72.18 | 13.51 | 99.84/58.77 | 1.935 |
| GD | BUY#3 | BUY#3 | 386.75 | 70.27 | 24.39 | 94.92/60.30 | 1.319 |
| CIX | HOLD | HOLD | 26.70 | 55.88 | 14.21 | 80.19/46.99 | 0.614 |
| BKHA | HOLD | HOLD | 12.10 | 50.85 | 70.25 | 12.28/74.42 | 0.029 |
| BMRN | IGNORE | IGNORE | 59.33 | 56.47 | 23.58 | 59.32/47.57 | 0.809 |
| ORIC | IGNORE | IGNORE | 12.10 | 69.87 | 39.93 | 82.57/47.33 | 2.182 |
| AACO | ERROR | ERROR | n/a | n/a | n/a | n/a | n/a |
| AEXA | ERROR | ERROR | 11.70 | 54.44 | 24.59 | 58.21/42.31 | 0.242 |
| AKO-A | ERROR | ERROR | 22.60 | 49.51 | 25.25 | null | 0.000 |

Audit result:

- 19/19 statuses matched;
- 19/19 signal names matched;
- 19/19 available prices and indicators matched;
- 12/12 audited BUYs reproduced; and
- all control failures reproduced for their documented reason.

## 7. Signal-quality findings

The result is mechanically reproducible, but not every BUY is equally
actionable.

Across all 74 BUYs:

| Quality condition | Count |
|---|---:|
| Price below USD 5 | 6 |
| Price below USD 10 | 15 |
| Prior-20-session average volume below 100,000 shares | 10 |
| Prior-20-session average turnover below USD 1 million | 9 |
| Current volume ratio below 0.60 | 11 |
| Current volume ratio below 0.80 | 15 |
| ADX below 15 | 12 |
| RSI at least 80 | 2 |
| Stochastic K at least 90 | 19 |
| More than 3 ATR above EMA50 | 26 |
| More than 5 ATR above EMA50 | 4 |

### 7.1 Low-participation examples

| Ticker | Volume ratio | One-year volume percentile |
|---|---:|---:|
| LCUT | 0.268 | 63.89 |
| NNBR | 0.300 | 94.84 |
| WBX | 0.358 | 78.97 |
| MSLE | 0.374 | 69.05 |
| FRD | 0.380 | 75.79 |

These pass because the historical percentile branch overrides weak immediate
participation.

### 7.2 Extreme examples

NOEM:

- average daily turnover approximately USD 14,326;
- RSI 95.14;
- stochastic 100/100;
- 11.556 ATR above EMA50; and
- sparse daily trading, including multiple zero-volume sessions.

OII:

- RSI 83.52;
- stochastic K 96.92;
- 5.587 ATR above EMA50; and
- current volume ratio 3.164.

Both are mathematically valid momentum-continuation results. They should not be
presented as having the same operational quality.

## 8. Daily versus intraday feed sensitivity

For 11 of 12 audited BUYs, replacing the final daily candle with an aggregation
of available five-minute bars preserved the BUY classification.

BRK-B changed from Early Momentum BUY to a pre-bull HOLD because the intraday
feed reported less consolidated volume than the completed daily feed. The
completed daily feed is the appropriate source after market close, but this test
shows that candidates close to the volume floor are feed-sensitive.

NOEM had a completed daily candle but no same-date regular-session minute bars
available from Yahoo. This is an additional low-liquidity data-quality warning.

## 9. Recommended hardening decisions

These are recommendations only and were not implemented during documentation
handover:

1. Add a non-negotiable current volume-ratio floor of 0.60.
2. For U.S. scans, add an average daily turnover floor such as USD 1 million.
3. Preserve high recall but relabel candidates beyond 5 ATR as
   `BUY_EXTENDED_REVIEW`.
4. Add a low-liquidity/data-quality flag when zero-volume sessions or daily
   versus intraday OHLC disagreements are detected.
5. Add `DataThrough=<session_date>` to run-level summaries.
6. Define currency-aware or exchange-specific liquidity rules before applying
   absolute thresholds internationally.

Applying only the proposed 0.60 volume-ratio and USD 1 million turnover screens
to the full-U.S. result would reduce 74 BUYs to approximately 55. Adding a USD 5
price screen would reduce the set to approximately 54.

## 10. Validation conclusion

The engine's output is trustworthy as a reproducible per-ticker baseline state
check. It is not yet trustworthy as an undifferentiated actionable BUY list.

Development signoff therefore covers:

- deterministic execution;
- correct poll-boundary behavior;
- repeatable indicators and classifications;
- adaptive guidance isolation;
- multi-market/currency metadata; and
- documented limitations.

Production signal-quality signoff remains conditional on an owner decision for
liquidity and extreme-extension handling.
