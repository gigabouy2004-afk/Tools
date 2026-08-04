# V8 Composite Score Expanded Backtest

Date: 2026-07-13

Status: expanded V1-V3 composite Score replay complete and independently validated. This establishes the historical V1 Score as a serious V8 research candidate, especially for technology. It does not yet authorize operational promotion or a claim that the Score is a probability.

## 1. Corrected design interpretation

Momentum identification is intended to be the combined interpretation of several health signals. RSI, ADX, OBV and the other components are not competing stock selectors. Their individual values contribute to a composite view of the stock's current technical health.

Component-level analysis remains useful for explaining why the combined Score behaves as it does, but the principal backtest question is:

> Does the complete configured Score select a higher-probability group from stocks that already passed Foundation eligibility?

This report answers that question using unchanged V1-V3 periods, values, points and qualification totals.

## 2. Where Score currently exists

V8 presently has three different code paths:

| Path | Score position | Authority |
|---|---|---|
| `Momentum_Detector_V8_Basic.py` | No combined Score. It contains Foundation and base calculation mechanics. | Development base only. |
| `V8_V1_V3_Indicator_Baseline.py` | Historical combined Score: V1/V2 maximum 30 and V3 maximum 45. | Configurable research candidate. |
| `Momentum_Detector_V8.py` | Inherited V4-V7-style nominal 0-100 Score, commercial caps and status thresholds. | Frozen legacy comparator; not the rebuilt V8 Score. |

Therefore Score was not absent from every V8 file. It was missing from the rebuilt Basic engine because no composite model had yet passed a sufficiently broad replay.

The present experiment tests whether the V1-V3 combined Score deserves to become the starting Score architecture for the rebuilt engine.

## 3. Unchanged configurations tested

### Shared Foundation and strict gate

```text
Close > EMA200
MACD 12/26/9 line > signal and line > 0
+DI14 > -DI14
```

### V1 and V2 Score

```text
RSI14 points + ADX14 points + OBV/EMA20 points
Maximum positive Score = 30
Historical qualification = Score >= 20
```

### V3 Score

```text
V1 Score + Aroon14 points + opening-structure points
Maximum positive Score = 45
Historical qualification = Score >= 25
```

V1 and V2 have identical technical Score rules. V2 historically changed live-data handling, not weights or thresholds. Their completed-daily-bar replay results must therefore match.

No period, boundary, weight or qualification threshold was tuned during this experiment.

## 4. Expanded experiment

| Item | Value |
|---|---|
| Technology stocks | 50 |
| Industrial stocks | 50 |
| Total stocks | 100 |
| Signal dates | 12 |
| Date span | March 2023 through May 2026 |
| Stock-date observations | 1,200 |
| Profiles | V1, V2 and V3 |
| Total result rows | 3,600 |
| Horizons | D+1, D+5 and D+8 |
| Data failures | 0 |
| Price policy | Frozen unadjusted daily OHLCV |
| Look-ahead protection | Every indicator uses only data on or before the signal date |

Signal dates:

```text
2023-03-15  2023-06-15  2023-10-27
2024-01-31  2024-04-19  2024-08-05  2024-11-06
2025-03-10  2025-04-09  2025-08-01
2026-02-05  2026-05-07
```

Universe selection is purposeful and based on the current stock master. Historical index or sector membership was not reconstructed, so survivorship and universe-selection limitations remain.

Canonical run:

```text
backtests/V8_V1_V3_Composite_Score_Expanded/runs/V8SCORE_20260712T230552Z_2fcd424
```

## 5. Eligibility and signal counts

| Profile | Stock-date rows | Foundation eligible | DMI pass | Score qualified |
|---|---:|---:|---:|---:|
| V1 | 1,200 | 301 | 292 | 87 |
| V2 | 1,200 | 301 | 292 | 87 |
| V3 | 1,200 | 301 | 292 | 157 |

V1 and V2 again produced identical results.

The historical DMI rule removed only 9 of 301 Foundation observations. Its effect was small and slightly adverse in this sample, but DMI remained part of the unchanged combined configuration for this test.

## 6. Main combined-Score result

The fairest control is the 292 observations that passed Foundation and DMI and therefore received a complete Score.

### All sectors combined

| Cohort | N | D+1 positive / mean | D+5 positive / mean | D+8 positive / mean |
|---|---:|---:|---:|---:|
| Foundation + DMI | 292 | 55.82% / +0.46% | 57.19% / +1.15% | 53.42% / +1.26% |
| V1/V2 Score >=20 | 87 | 60.92% / +0.55% | 68.97% / +1.58% | 64.37% / +1.62% |
| V1/V2 below 20 | 205 | 53.66% / +0.43% | 52.20% / +0.97% | 48.78% / +1.10% |
| V3 Score >=25 | 157 | 57.32% / +0.46% | 61.78% / +1.31% | 56.69% / +1.11% |
| V3 below 25 | 135 | 54.07% / +0.47% | 51.85% / +0.97% | 49.63% / +1.42% |

The combined V1 threshold improved positive rates by:

```text
D+1: +5.10 percentage points
D+5: +11.78 percentage points
D+8: +10.95 percentage points
```

This is materially stronger evidence for the combined V1 configuration than the earlier 20-stock/four-date replay provided.

## 7. Sector result

### Technology

| Cohort | N | D+1 positive / mean | D+5 positive / mean | D+8 positive / mean |
|---|---:|---:|---:|---:|
| Foundation + DMI | 142 | 63.38% / +0.84% | 59.86% / +1.37% | 52.11% / +1.40% |
| V1/V2 Score >=20 | 42 | 71.43% / +1.07% | 76.19% / +1.93% | 69.05% / +2.09% |
| V1/V2 below 20 | 100 | 60.00% / +0.74% | 53.00% / +1.13% | 45.00% / +1.12% |
| V3 Score >=25 | 74 | 67.57% / +0.96% | 64.86% / +1.74% | 55.41% / +1.41% |

For the user's primary technology use case, the V1 combined configuration is the strongest tested version. It provides clear separation at all three horizons.

### Industrials

| Cohort | N | D+1 positive / mean | D+5 positive / mean | D+8 positive / mean |
|---|---:|---:|---:|---:|
| Foundation + DMI | 150 | 48.67% / +0.11% | 54.67% / +0.95% | 54.67% / +1.12% |
| V1/V2 Score >=20 | 45 | 51.11% / +0.06% | 62.22% / +1.24% | 60.00% / +1.18% |
| V1/V2 below 20 | 105 | 47.62% / +0.13% | 51.43% / +0.83% | 52.38% / +1.09% |
| V3 Score >=25 | 83 | 48.19% / +0.01% | 59.04% / +0.92% | 57.83% / +0.85% |

The industrial result is weaker. V1 improves D+5/D+8 persistence, but D+1 remains close to a coin flip. Technology and industrials should therefore not automatically share one operational interpretation merely because they use the same calculation.

## 8. What V3 added

V1 and V3 both qualified 82 observations. V1 qualified five observations that V3 did not, while V3 added 75 observations that V1 did not.

| Cohort | N | D+1 positive | D+5 positive | D+8 positive |
|---|---:|---:|---:|---:|
| Qualified by both | 82 | 59.76% | 69.51% | 64.63% |
| V1 only | 5 | 80.00% | 60.00% | 60.00% |
| Added by V3 only | 75 | 54.67% | 53.33% | 48.00% |

The V3 additions diluted the V1 selection. Under the unchanged historical values, Aroon and opening structure should not be added to the main Score merely because they raise the numerical total.

## 9. Is a higher Score always better?

No. The Score has useful threshold behavior, but weak continuous ordering.

Spearman rank correlation between raw Score and forward return among the 292 fully scored observations:

| Profile | D+1 | D+5 | D+8 |
|---|---:|---:|---:|
| V1/V2 | 0.083 | 0.089 | 0.076 |
| V3 | 0.066 | 0.082 | 0.069 |

These are weak positive relationships. The exact-score results are not monotonic. For example, V1 observations scoring 20 had a higher D+1 positive rate than the much smaller groups scoring 25 or 30.

Therefore the current historical Score should be interpreted as:

```text
A configured technical-health qualification total
```

It must not yet be described as:

```text
A probability of success
or
A linear ranking where 30 is necessarily better than 20
```

This distinction is important for the rebuilt V8 output. The engine should expose the raw components and raw total, and use an evidence-supported health band or threshold. It should not claim that a one-point increase has a calibrated probabilistic meaning.

## 10. Date stability

Results varied substantially by date. Examples for V1-qualified technology stocks:

```text
2023-06-15: 0/8 positive at D+1
2024-01-31: 13/13 positive at D+1
```

Industrials showed the same regime dependence:

```text
2023-06-15: 1/10 positive at D+1
2024-01-31: 9/10 positive at D+1
```

This is not a reason to add SPY or ETF points. It demonstrates that the current technical-health Score is not regime-neutral and that aggregate percentages must not conceal date-level instability.

## 11. Recommended Score position in rebuilt V8

The evidence supports the following research direction:

```text
Foundation eligibility
    -> calculate the complete approved health-signal set
    -> publish every component value and component point
    -> publish Raw Health Score
    -> publish configured Health Band / qualification state
    -> D+1/D+5/D+8 validation
```

The V1 architecture should be the next candidate, not the inherited V4-V7 0-100 model and not V3's expanded 45-point model.

Proposed research fields:

```text
RSI_Score
ADX_Score
OBV_Score
Raw_Health_Score
Maximum_Configured_Score
Health_Score_Percent_Of_Maximum   # display only
Health_Qualification_Threshold
Health_Qualification_State
```

The raw V1 total remains the decision evidence. A percentage-of-maximum representation may improve readability but must not change the decision or imply calibrated probability.

## 12. Validation

The independent validator recalculated all formulas, component points, total Scores, qualification states and D+1/D+5/D+8 outcomes from the frozen price files.

```text
Expected rows: 3,600
Checked rows: 3,600
Formula/Score/outcome failures: 0
Checksum entries checked: 122
Validation: PASS
```

The evidence pipeline writes and reloads frozen CSV prices before calculation. This prevents recursive indicators such as ADX from being calculated from a provider's transient in-memory float representation while validation uses a serialized representation.

## 13. Decision and approvals required

Evidence-supported findings:

1. Composite validation is the correct primary evaluation model.
2. The V1/V2 Score >=20 configuration provides useful selection separation in this expanded sample.
3. The technology result is materially stronger than the industrial result.
4. V3's Aroon/opening additions dilute the V1 result under existing values.
5. The raw Score is not a calibrated continuous probability or reliable linear rank.

User approval is still required before:

- adding the V1 composite Score to `Momentum_Detector_V8_Basic.py` as a decision-changing research stage;
- accepting 20/30 as the continuing V8 research qualification threshold;
- treating DMI as part of Foundation, a post-Foundation gate, or only a scored health signal;
- rejecting the V3 Aroon/opening additions from further research;
- defining separate technology and industrial qualification policies;
- promoting any Score to operational V8.
