# V14 Enhanced Positive-Regime Validation — 2026-07-27

## 1. Corrected engine mandate

V14 Enhanced screens only for established positive setup, trend, and momentum.
It does not identify or classify anticipated pre-bull or pre-bear crossovers.

Every BUY path requires:

```text
close > EMA50 > EMA200
completed weekly trend aligned
MACD > signal
MACD > 0
signal > 0
histogram > 0
```

Setup-specific stochastic, volume, price-response, ATR, and other confirmation
rules are applied only inside that positive regime. Secondary indicators cannot
compensate for a failed primary MACD gate.

## 2. Histogram scope

The generic one-bar `hist_improving` shortcut was removed from:

- momentum continuation;
- shallow pullback qualification;
- confidence scoring;
- MACD state labels; and
- HOLD classification.

Momentum continuation now requires the configured histogram window to be
strictly expanding and its latest two bars to be positive. This permits a valid
continuation on the session after a confirmed positive crossover while
rejecting negative-histogram improvement and one-bar rebounds inside a
non-expanding window.

BUY#4 remains a fresh signal-line crossover with both MACD lines above zero and
a positive current histogram.

## 3. GLOSTERLTD.NS reproduction

Completed candle evaluated: 2026-07-24.

| Field | Result |
|---|---:|
| Close | INR 683.65 |
| EMA50 | INR 660.43 |
| EMA200 | INR 626.01 |
| MACD | 1.544 |
| Signal | 1.785 |
| Histogram | -0.240 |
| Histogram window | -1.720, -1.159, -0.240 |
| Status | HOLD |
| Classification | NO_BUY |
| Signal | `Hold_MACD_Momentum_Not_Confirmed` |
| MACD state | `POSITIVE_PHASE_UNCONFIRMED` |
| Setup score | 4/10, Low Setup |

The price trend is positive, but MACD remains below its signal and the histogram
remains negative. GLOSTER is therefore a strict HOLD, receives no crossover
watch label, and receives no secondary-indicator score credit.

## 4. XLI three-date regression

Symbols:

```text
CAT, GE, RTX, GEV, UNP, BA, ETN, DE, UBER, PH
```

| Date | BUY count | BUY symbols |
|---|---:|---|
| 2026-07-22 | 0 | None |
| 2026-07-23 | 2 | RTX, ETN |
| 2026-07-24 | 3 | RTX, UNP, PH |

RTX and ETN on July 23 and PH on July 24 are fresh confirmed positive-phase
crossovers. RTX and UNP on July 24 are confirmed momentum continuations.

UNP on July 23 remains HOLD because its histogram window
`1.263, 0.746, 1.073` contains only a one-bar rebound and is not yet a sustained
expansion. It becomes BUY#3 on July 24 when the full window is expanding:
`0.746, 1.073, 1.349`.

## 5. Nineteen-symbol audit

The established audit set was replayed through 2026-07-24.

| Status | Count |
|---|---:|
| BUY | 3 |
| HOLD | 11 |
| IGNORE | 2 |
| ERROR | 3 |

Retained BUYs:

- AME — BUY#3;
- OII — `BUY_EXTENDED_REVIEW`; and
- GD — BUY#3.

All retained BUYs pass the daily trend, positive MACD/signal, bullish
MACD-to-signal relation, and positive-histogram invariants. Every retained
momentum-continuation BUY also passes the scoped expansion-window rule.

NNBR, WBX, FTV, BRK-B, and SNA are strict
`Hold_MACD_Momentum_Not_Confirmed` rows with a capped 4/10 setup score.

## 6. Historical signal replay

The built-in replay was aligned with the live/as-of BUY quality-policy layer and
run against the ten XLI symbols using three years of daily history and a
five-session holding period.

| Metric | Result |
|---|---:|
| Trades | 124 |
| Win rate | 52.42% |
| Average five-session return | 0.43% |
| Sequential replay max drawdown | -33.84% |

This replay is a signal-behavior check, not a profitability claim. It excludes
fees, slippage, stops, position sizing, and realistic portfolio treatment of
overlapping signals. The reported drawdown compounds the replay rows
sequentially and is not a portfolio simulation.

## 7. Verification matrix

| Check | Result |
|---|---|
| Original and enhanced Python syntax | PASS |
| Unit tests | 24/24 PASS |
| Removed-identifier source audit | PASS |
| GLOSTER full-engine historical regression | PASS |
| XLI three-date regression | PASS |
| Nineteen-symbol audit | PASS |
| BUY primary-gate invariant scan | PASS, zero violations |
| Momentum-continuation histogram invariant | PASS, zero violations |
| Three-year historical replay | PASS |

The scanner successfully generated its XLSX output during the GLOSTER
full-engine run. The optional artifact-runtime XLSX inspection layer was not
available in this session, so workbook-object inspection was not used as
evidence; validation relied on the engine's structured result, assertions,
terminal summary, and execution log.

