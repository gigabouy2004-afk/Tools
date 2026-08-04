# V8 V1-V3 Indicator Baseline and Backtest

Date: 2026-07-13

Status: historical V1-V3 indicator values consolidated, made configurable, functionally tested and replayed. The values are frozen as the V8 research baseline only. They are not approved operational gates or scores.

## 1. Plain-language conclusion

The V1-V3 formulas now run correctly after Foundation eligibility, and the 240-row replay passed an independent formula recalculation with no failures.

The backtest does **not** justify copying the complete V1, V2 or V3 scoring model into operational V8:

- V1 and V2 are technically identical. There is no reason to test them as separate indicator models in future work.
- The EMA200/MACD Foundation produced 27 eligible stock-date observations from 80.
- All 27 also passed the historical `+DI > -DI` rule in this sample, so DMI removed nothing here.
- V1/V2 qualified 7 of the 27 Foundation-eligible observations. Their D+1 positive rate was 71.43%, almost unchanged from the Foundation cohort's 70.37%. At D+5 and D+8, the excluded observations performed better than the qualified observations.
- V3 qualified 11 observations. It improved the D+8 positive rate in this small sample, but reduced the primary D+1 positive rate to 54.55%.
- Aroon and opening structure awarded positive points very broadly. That increased the number of V3 qualifications but did not establish that those additions improve immediate direction.

Decision: retain these exact values as configurable research defaults for controlled, indicator-by-indicator testing. Do not incorporate their scores, minimum totals or gates into the operational V8 path without further evidence and explicit approval.

## 2. Finalized historical baseline

“Finalized” here means that the source values have been captured exactly and frozen in configuration. It does not mean that their predictive usefulness has been approved.

### Foundation and strict eligibility

| Element | V1 | V2 | V3 | Frozen research value |
|---|---:|---:|---:|---|
| Long-term trend | EMA200 | EMA200 | EMA200 | `Close > EMA200` |
| MACD | 12/26/9 | 12/26/9 | 12/26/9 | Line above signal and line above zero |
| Directional movement | DMI14 | DMI14 | DMI14 | `+DI > -DI` |
| Minimum history | 260-day API request | 260-day API request | 260-day API request, at least 250 rows | 300 trading bars for replay integrity |

The 300-bar replay minimum is an integrity correction, not a new trading threshold. A 260-calendar-day API request does not reliably provide 200 completed trading sessions for EMA200.

### Post-Foundation calculations and values

| Indicator | Period/value | Historical rule | V1 | V2 | V3 |
|---|---|---|---:|---:|---:|
| RSI | 14 | `<55: 0`; `55-<56: +5`; `56-68: +10`; `>68-75: +5`; `>75: -10` | Yes | Yes | Yes |
| ADX | 14 | `<20: 0`; `20-<26: +5`; `26-40: +10`; `>40-60: +5`; `>60: -5` | Yes | Yes | Yes |
| OBV | Standard OBV, EMA20 | Cross above EMA in latest three checks: `+10`; price up and OBV down: `-5`; otherwise `0` | Yes | Yes | Yes |
| ATR | 14, `ta` Wilder-style calculation | Calculation/output only; no points and no qualification threshold | Yes | Yes | Yes |
| Opening structure | Current open versus prior open | Current open greater than prior open: `+5`; otherwise `0` | No | No | Yes |
| Aroon | 14 | Up>70 and Down<30: `+10`; Up>50 and Down<50: `+5`; Up<30 and Down>70: `-5`; otherwise `0` | No | No | Yes |

### Total qualification

| Profile | Maximum positive score | Historical minimum | Components |
|---|---:|---:|---|
| V1 | 30 | 20 | RSI + ADX + OBV |
| V2 | 30 | 20 | RSI + ADX + OBV |
| V3 | 45 | 25 | RSI + ADX + OBV + opening structure + Aroon |

V2 changed data handling by applying a live daily override; it did not change indicator periods, values, points or total threshold. Under a completed-daily-bar historical replay, V1 and V2 must therefore produce the same result.

The machine-readable authority is `config/V8_V1_V3_Indicator_Baseline_Config.json`. Every period, boundary, point value and total threshold is a variable. The configuration carries:

```text
Limit_Status = RESEARCH_CANDIDATE_NOT_OPERATIONAL
Operational_Use_Approved = false
```

## 3. Implementation

The research package is deliberately separate from the operational V8 path:

```text
V8_V1_V3_Indicator_Baseline.py
Backtest_V8_V1_V3_Indicator_Baseline.py
Validate_V8_V1_V3_Indicator_Baseline.py
config/V8_V1_V3_Indicator_Baseline_Config.json
tests/test_v8_v1_v3_indicator_baseline.py
```

Execution order is enforced:

```text
Sufficient point-in-time history
    -> EMA200 and MACD12/26/9 Foundation
    -> only if Foundation eligible: calculate RSI/ADX/DMI/OBV/ATR/Aroon
    -> historical DMI dominance check
    -> historical component points
    -> profile minimum score
```

If Foundation eligibility is false, the post-Foundation indicator module is not called and its values remain blank.

## 4. Functional validation

Seven focused tests passed:

1. Exact source periods, thresholds, points and research-only lifecycle.
2. Every RSI boundary.
3. Every ADX boundary.
4. OBV fresh-cross and divergence behavior.
5. Aroon and opening-structure behavior.
6. V1/V2 technical identity.
7. Foundation-ineligible rows cannot execute the indicator module.

Command:

```powershell
python -m unittest tests.test_v8_v1_v3_indicator_baseline -v
```

## 5. Backtest design

The replay used the existing frozen technology-stock price set, so results do not depend on a new provider download.

| Item | Value |
|---|---|
| Symbols | 20 technology stocks |
| Stock-date observations | 80 |
| Profiles | V1, V2 and V3 |
| Result rows | 240 |
| Signal dates | 2026-04-08, 2026-04-30, 2026-05-07, 2026-06-09 |
| Price evidence | Unadjusted daily OHLCV, frozen locally |
| Point-in-time rule | Only rows on or before the signal date enter indicator calculations |
| D+1 | Next session open to next session close |
| D+5 | Next session open to fifth-session close |
| D+8 | Next session open to eighth-session close |
| Costs/stops/sizing | Not modeled |

Symbols: NVDA, AAPL, MSFT, GOOGL, META, AMD, AVGO, ORCL, CRM, NOW, PANW, CRWD, ANET, MU, QCOM, AMAT, LRCX, KLAC, PLTR and APP.

Canonical run:

```text
backtests/V8_V1_V3_Indicator_Baseline/runs/V8V1V3_20260712T222737Z_931c0cf
```

## 6. Backtest results

### Qualification results

| Profile | Total observations | Foundation eligible | DMI pass | Qualified |
|---|---:|---:|---:|---:|
| V1 | 80 | 27 | 27 | 7 |
| V2 | 80 | 27 | 27 | 7 |
| V3 | 80 | 27 | 27 | 11 |

V1/V2 technical differences: **0**.

### Qualified observations

| Profile | Horizon | Positive | Positive rate | Mean return | Median return |
|---|---|---:|---:|---:|---:|
| V1 | D+1 | 5/7 | 71.43% | +2.09% | +1.49% |
| V1 | D+5 | 5/7 | 71.43% | +3.00% | +2.34% |
| V1 | D+8 | 5/7 | 71.43% | +5.57% | +1.65% |
| V2 | D+1 | 5/7 | 71.43% | +2.09% | +1.49% |
| V2 | D+5 | 5/7 | 71.43% | +3.00% | +2.34% |
| V2 | D+8 | 5/7 | 71.43% | +5.57% | +1.65% |
| V3 | D+1 | 6/11 | 54.55% | +1.19% | +0.46% |
| V3 | D+5 | 9/11 | 81.82% | +5.67% | +6.78% |
| V3 | D+8 | 9/11 | 81.82% | +11.55% | +5.97% |

### Comparison with Foundation alone

The correct comparison is not just whether qualified observations rose. It is whether the historical indicator rules selected a better subset than the already eligible Foundation cohort.

| Cohort | N | D+1 positive / mean | D+5 positive / mean | D+8 positive / mean |
|---|---:|---:|---:|---:|
| Foundation eligible | 27 | 70.37% / +1.99% | 85.19% / +6.63% | 70.37% / +8.88% |
| V1/V2 qualified | 7 | 71.43% / +2.09% | 71.43% / +3.00% | 71.43% / +5.57% |
| V1/V2 excluded after Foundation | 20 | 70.00% / +1.95% | 90.00% / +7.90% | 70.00% / +10.04% |
| V3 qualified | 11 | 54.55% / +1.19% | 81.82% / +5.67% | 81.82% / +11.55% |
| V3 excluded after Foundation | 16 | 81.25% / +2.54% | 87.50% / +7.29% | 62.50% / +7.05% |

Interpretation:

- V1/V2 did not materially improve D+1 selection and selected a worse D+5/D+8 subset in this sample.
- V3's qualified group was worse at D+1, the primary validation endpoint.
- V3's D+8 positive rate and mean were better than Foundation alone, but this is only 11 observations and the mean is influenced by large individual moves. The median improvement was small: +5.97% versus +5.72% for all 27 Foundation observations.
- These are descriptive sample results, not proof that a rule works or fails universally.

### How often components affected the 27 eligible observations

| Component result | Count |
|---|---:|
| RSI +10 | 15 |
| RSI +5 | 4 |
| RSI 0 | 1 |
| RSI -10 | 7 |
| ADX +10 | 8 |
| ADX +5 | 5 |
| ADX 0 | 14 |
| OBV +10 fresh cross | 4 |
| OBV -5 divergence | 0 |
| OBV 0 | 23 |
| Aroon +10, V3 | 17 |
| Aroon +5, V3 | 3 |
| Aroon 0, V3 | 7 |
| Opening structure +5, V3 | 22 |
| Opening structure 0, V3 | 5 |

The V3 additions were generous in this sample: 17/27 received maximum Aroon points and 22/27 received opening-structure points. This explains much of the increase from seven to eleven qualified observations and must be tested as two separate hypotheses.

ATR has no points or gate in V1-V3. It was calculated and recorded correctly but cannot explain qualification or performance differences.

## 7. Independent validation and evidence

The validator independently recalculated EMA, MACD, RSI, ADX/DMI, OBV/EMA, ATR, Aroon, every historical point rule, every profile total and every D+1/D+5/D+8 return. It did not import the baseline evaluator.

```text
Rows expected: 240
Rows checked: 240
Formula comparison failures: 0
V1/V2 identity failures: 0
Checksum entries checked: 36
Validation status: PASS
```

Primary evidence files:

```text
outputs/profile_results.csv
outputs/profile_summary.csv
outputs/aggregate_summary.json
outputs/execution.log
validation/independently_recomputed_rows.csv
validation/validation_summary.json
checksums.sha256
```

Revalidate the sealed run:

```powershell
python Validate_V8_V1_V3_Indicator_Baseline.py backtests/V8_V1_V3_Indicator_Baseline/runs/V8V1V3_20260712T222737Z_931c0cf
```

## 8. Approved way forward

The next research sequence should use the 27-observation Foundation cohort as the comparator and test one decision change at a time:

1. Foundation only.
2. Add DMI dominance by itself.
3. Test RSI14 bands by themselves, including alternative configurable ranges.
4. Test ADX14 bands by themselves.
5. Test OBV/EMA20 events by themselves.
6. Test Aroon14 by itself.
7. Test opening structure by itself.
8. Only after individual evidence, test combinations and total-score thresholds.

Each test must report both the selected and excluded Foundation-eligible cohorts. A value may enter the mainstream V8 decision path only after broader multi-regime dates, an untouched holdout, technology and industrial coverage, and explicit user approval.

## 9. Matters requiring user approval

No approval is assumed by this report. Future approval is required for:

- whether DMI remains a strict eligibility rule or becomes information-only;
- any RSI, ADX, OBV or Aroon boundary and its authority level;
- whether opening structure should affect a multi-session signal;
- whether any point system is retained at all;
- any minimum combined score;
- promotion from research candidate to operational V8.
