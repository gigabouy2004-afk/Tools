# V8 MACD Foundation Comparison: 12/26/9 vs 8/21/5

Date: 2026-07-13

Status: expanded dual-MACD replay complete and independently validated. MACD 12/26/9 remains the approved V1 Health Score research default. MACD 8/21/5 is not promoted because it increased false-positive rates overall and materially weakened the technology result. Neither MACD configuration solved the industrial D+1 problem.

## 1. Plain-language deduction

MACD 8/21/5 did not provide a safer earlier signal.

For technology Health-qualified observations:

```text
12/26/9: 42 signals, 28.57% D+1 false positives, 28.57% D+3 false positives
8/21/5:  34 signals, 38.24% D+1 false positives, 35.29% D+3 false positives
```

The faster configuration produced fewer signals and a higher proportion of wrong-direction signals. It also missed a strong group selected only by 12/26/9.

For industrials, D+1 false-positive rates were effectively identical and close to 49% under both settings. Changing MACD periods is therefore not the missing industrial pivot.

Decision:

1. Retain MACD 12/26/9 in the integrated V1 Health Score research baseline.
2. Do not replace it with 8/21/5.
3. Do not add both MACD variants together or award extra points for agreement.
4. Proceed to the proposed industrial sector-context experiment using the unchanged 12/26/9 baseline.

## 2. Frozen experiment

| Item | Value |
|---|---|
| Technology stocks | 50 |
| Industrial stocks | 50 |
| Signal dates | 12 |
| Stock-date observations | 1,200 |
| MACD variants | 2 |
| Result rows | 2,400 |
| Forward horizons | D+1 and D+3 |
| EMA | 200 |
| MACD Foundation rule | Line above signal and line above zero |
| Post-Foundation sequence | DMI eligibility, unchanged V1 Health Score >=20/30 |
| Score or indicator tuning | None |

Compared variants:

```text
STANDARD_12_26_9
FIBONACCI_8_21_5
```

The same frozen stock prices, dates, DMI rule, RSI/ADX/OBV values, component points and threshold were used for both variants.

## 3. Error definitions

The user's priority is avoiding false positives, even if the engine produces more false negatives.

For this experiment:

```text
False positive = selected by the stated stage
                 AND return from D+1 open to horizon close <= 0

False negative = not selected by the stated stage
                 AND return from D+1 open to horizon close > 0
```

“Selected” is reported twice:

- Foundation selected: EMA200 and the stated MACD configuration passed.
- Health qualified: Foundation, DMI and Raw Health Score >=20 passed.

This is a directional definition, not a complete trade simulation with costs, stops or sizing.

## 4. Overall comparison

### Foundation stage

| MACD | Selected | D+1 positive | D+1 false-positive rate | D+3 positive | D+3 false-positive rate |
|---|---:|---:|---:|---:|---:|
| 12/26/9 | 301 | 56.48% | 43.52% | 56.81% | 43.19% |
| 8/21/5 | 274 | 53.65% | 46.35% | 53.65% | 46.35% |

### Complete Health qualification

| MACD | Selected | D+1 positive | D+1 false-positive rate | D+3 positive | D+3 false-positive rate |
|---|---:|---:|---:|---:|---:|
| 12/26/9 | 87 | 60.92% | 39.08% | 63.22% | 36.78% |
| 8/21/5 | 77 | 55.84% | 44.16% | 61.04% | 38.96% |

At complete qualification, 12/26/9 reduced the false-positive rate relative to 8/21/5 by:

```text
D+1: 5.08 percentage points
D+3: 2.18 percentage points
```

It also produced ten more qualified observations and fewer false negatives.

## 5. Technology result

### Foundation

| MACD | Selected | D+1 positive / FP | D+3 positive / FP |
|---|---:|---:|---:|
| 12/26/9 | 146 | 64.38% / 35.62% | 57.53% / 42.47% |
| 8/21/5 | 125 | 60.80% / 39.20% | 52.80% / 47.20% |

### Health qualified

| MACD | Selected | D+1 positive / FP | D+1 mean | D+3 positive / FP | D+3 mean |
|---|---:|---:|---:|---:|---:|
| 12/26/9 | 42 | 71.43% / 28.57% | +1.07% | 71.43% / 28.57% | +1.18% |
| 8/21/5 | 34 | 61.76% / 38.24% | +1.03% | 64.71% / 35.29% | +1.05% |

For technology, 12/26/9 is clearly better on the user's false-positive priority:

```text
D+1 false-positive reduction: 9.66 percentage points
D+3 false-positive reduction: 6.72 percentage points
```

## 6. Industrial result

### Foundation

| MACD | Selected | D+1 positive / FP | D+3 positive / FP |
|---|---:|---:|---:|
| 12/26/9 | 155 | 49.03% / 50.97% | 56.13% / 43.87% |
| 8/21/5 | 149 | 47.65% / 52.35% | 54.36% / 45.64% |

### Health qualified

| MACD | Selected | D+1 positive / FP | D+1 mean | D+3 positive / FP | D+3 mean |
|---|---:|---:|---:|---:|---:|
| 12/26/9 | 45 | 51.11% / 48.89% | +0.06% | 55.56% / 44.44% | +0.77% |
| 8/21/5 | 43 | 51.16% / 48.84% | +0.09% | 58.14% / 41.86% | +1.07% |

The industrial D+1 difference is 0.05 percentage points—statistically and practically negligible. The 8/21/5 D+3 rate is modestly better, but D+1 remains essentially random under both settings.

Deduction: MACD period selection is not the industrial solution. The industrial branch still needs a separate contextual feature such as broad-market or XLI sector state.

## 7. What happened when the variants disagreed

### Technology Health qualification

| Transition | Rows | D+1 positive | D+3 positive |
|---|---:|---:|---:|
| Both qualify | 25 | 64.00% | 64.00% |
| 12/26/9 only | 17 | 82.35% | 82.35% |
| 8/21/5 only | 9 | 55.56% | 66.67% |

This is the most important comparison. The 17 technology observations uniquely retained by 12/26/9 were exceptionally strong, while the nine added only by 8/21/5 were materially weaker.

The faster MACD did not merely reduce lag. At the sampled endpoints it reset more quickly, removed profitable standard-MACD signals, and admitted a smaller weaker set at other dates.

### Industrial Health qualification

| Transition | Rows | D+1 positive | D+3 positive |
|---|---:|---:|---:|
| Both qualify | 40 | 47.50% | 55.00% |
| 12/26/9 only | 5 | 80.00% | 60.00% |
| 8/21/5 only | 3 | 100.00% | 100.00% |

The unique industrial cohorts are too small—five and three observations—to establish a reliable period preference. The full industrial cohorts remain the controlling result.

## 8. False negatives

The experiment deliberately tolerates false negatives, but records them:

| MACD | Health D+1 false negatives | Health D+3 false negatives |
|---|---:|---:|
| 12/26/9 | 652 | 716 |
| 8/21/5 | 662 | 724 |

The strict engine rejects many observations that subsequently rise. That is expected under a precision-first design. Nevertheless, 8/21/5 did not trade more false negatives for fewer false positives—it produced both more false negatives and a higher false-positive rate overall.

## 9. Date dependence

The configurations did not behave uniformly across dates. For example:

- On 2024-01-31, technology 12/26/9 qualified 13 observations, all D+1 positive; 8/21/5 qualified only three, also positive. The faster variant missed ten successful signals.
- On 2023-06-15, both configurations performed badly for technology.
- Industrial D+1 remained strongly date-dependent under both variants.

This confirms that changing MACD periods does not eliminate market-regime dependence.

## 10. Charts

Generated chart evidence:

```text
charts/false_positive_rate_comparison.png
charts/selection_count_comparison.png
charts/macd_line_signal_disagreement_examples.png
charts/chart_manifest.json
```

The MACD line/signal examples were selected mechanically as the first chronological disagreement in each sector and direction. Forward outcomes were not used to choose examples.

## 11. Independent validation

```text
Expected rows: 2,400
Independently checked rows: 2,400
Both MACD formula/state calculations: PASS
DMI and RSI/ADX/OBV point calculations: PASS
Raw Health Score and qualification: PASS
D+1 and D+3 outcomes: PASS
Chart evidence: PASS
Checksum entries: 127
Failures: 0
```

Canonical run:

```text
backtests/V8_MACD_Foundation_Comparison_Expanded/runs/V8MACDCMP_20260712T235809Z_ffd4372
```

## 12. Final decision before sector branching

```text
Integrated Foundation MACD: retain 12/26/9
MACD 8/21/5: rejected as replacement under current evidence
Technology: 12/26/9 supported
Industrials: neither MACD configuration provides acceptable D+1 precision
Next research increment: industrial market/sector context using unchanged 12/26/9 base
```

No sector benchmark has been added to the engine or Score by this experiment.
