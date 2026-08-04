# V8 Basic Composite Health Score Implementation

Date: 2026-07-13

Status: user-approved research implementation complete. The rebuilt V8 Basic engine now enforces Foundation first, DMI eligibility second, and then calculates the combined V1 RSI/ADX/OBV Health Score out of 30. Research qualification begins at 20. This is not operational trade approval and the Score is not described as a calibrated probability.

## 1. Implemented sequence

```text
Close > EMA200
AND MACD 12/26/9 line > signal and line > 0
    -> calculate raw post-Foundation indicators
    -> require +DI14 > -DI14
    -> RSI14 Score + ADX14 Score + OBV/EMA20 Score
    -> Raw Health Score out of 30
    -> Research qualified when Raw Health Score >=20
```

Execution order is enforced in code:

- Foundation-ineligible rows do not call the indicator module.
- Foundation-eligible rows publish raw indicator values and DMI eligibility.
- DMI-ineligible rows do not calculate component points or a raw Health Score.
- Only DMI-eligible rows receive RSI, ADX and OBV component points.

## 2. Why the default MACD is 12/26/9

The approved composite evidence was generated from the exact V1-V3 historical configuration, which used MACD 12/26/9. The integrated default therefore uses 12/26/9 so the implementation is evidence-equivalent.

MACD remains configurable. An 8/21/5 override is supported and is written into the Configuration ID, but it cannot inherit the 12/26/9 composite-score evidence without its own integrated replay.

## 3. Configured Health Score

### RSI14

```text
<55       = 0
55-<56    = +5
56-68     = +10
>68-75    = +5
>75       = -10
```

### ADX14

```text
<20       = 0
20-<26    = +5
26-40     = +10
>40-60    = +5
>60       = -5
```

### OBV with EMA20

```text
Fresh cross above EMA within latest three checks = +10
Price rising while OBV falls                    = -5
Otherwise                                       = 0
```

### Total

```text
Raw Health Score = RSI Score + ADX Score + OBV Score
Maximum positive Score = 30
Research qualification threshold = 20
```

ATR14 and Aroon14 remain visible calculations. They contribute no points to this V1 Score. Opening structure is not part of the engine.

## 4. Configuration authority

Machine-readable configuration:

```text
config/V8_Basic_Foundation_Config.json
```

Despite the historical filename, this is now schema `V8_BASIC_HEALTH_SCORE_1` and configuration `V8_BASIC_V1_HEALTH_SCORE_RESEARCH_20260713`.

Every period, boundary, point value and total threshold is a configuration variable. Research rules publish:

```text
Limit_Status = USER_APPROVED_RESEARCH_NOT_OPERATIONAL
Operational_Use_Approved = false
Probability_Calibrated = false
```

This records the user's approval to place the combined configuration in the rebuilt research engine. It does not claim production or trade authority.

## 5. Output contract

Every evaluated row now exposes:

```text
Foundation_Eligible / Foundation_State / Foundation_Reason
DMI_Positive / DMI_Negative
DMI_Eligible / DMI_Status / DMI_Message
RSI / RSI_Score / RSI_Score_Status / RSI_Score_Message
ADX / ADX_Score / ADX_Score_Status / ADX_Score_Message
OBV / OBV_EMA / OBV_Fresh_Cross / OBV_Score / status / message
Raw_Health_Score
Maximum_Health_Score
Health_Score_Pct_Of_Maximum          # display only
Health_Score_Threshold
Health_Qualified
Health_Qualification_State
Health_Qualification_Message
```

The component values and points remain visible; the total is never an unexplained opaque number.

The field is intentionally named `Raw_Health_Score`, not the inherited generic `Score`. This prevents confusion with the unapproved V4-V7-style nominal 0-100 Score and its status caps in `Momentum_Detector_V8.py`.

## 6. Integrated parity replay

Canonical run:

```text
backtests/V8_Basic_Health_Score/runs/V8HEALTH_20260712T232546Z_9a1689f
```

Scope:

```text
50 technology stocks
50 industrial stocks
12 signal dates from 2023 through 2026
1,200 integrated engine rows
D+1, D+5 and D+8 outcomes
```

The replay reused the frozen inputs and independently validated V1 reference from the expanded composite-score experiment.

Validation:

```text
Rows expected / checked: 1,200 / 1,200
Foundation parity: PASS
DMI parity: PASS
RSI/ADX/OBV value and point parity: PASS
Raw Health Score parity: PASS
Qualification parity: PASS
D+1/D+5/D+8 parity: PASS
Checksum entries: 117
Failures: 0
```

## 7. Reproduced result

| Sector | Rows | Foundation | DMI eligible | Health qualified |
|---|---:|---:|---:|---:|
| All | 1,200 | 301 | 292 | 87 |
| Technology | 600 | 146 | 142 | 42 |
| Industrials | 600 | 155 | 150 | 45 |

| Sector | D+1 positive / mean | D+5 positive / mean | D+8 positive / mean |
|---|---:|---:|---:|
| All qualified | 60.92% / +0.55% | 68.97% / +1.58% | 64.37% / +1.62% |
| Technology qualified | 71.43% / +1.07% | 76.19% / +1.93% | 69.05% / +2.09% |
| Industrial qualified | 51.11% / +0.06% | 62.22% / +1.24% | 60.00% / +1.18% |

These results are identical to the validated V1 reference by design; the purpose of this replay was implementation correctness, not a new performance claim.

## 8. Functional and regression validation

Focused tests cover:

- exact approved configuration and lifecycle;
- Foundation formula and execution boundary;
- DMI pass/fail execution boundary;
- exact RSI and ADX score boundaries;
- OBV cross and negative-divergence scoring;
- component sum and threshold qualification;
- raw component/total output contract;
- no operational or probability claim;
- configurable MACD and Health Score threshold;
- prefix-only historical evaluation;
- insufficient history, invalid periods, duplicate dates and log-schema rotation.

The full test suite passed after integration.

## 9. Current V8 boundary

```text
Rebuilt V8 Basic:
    Foundation + DMI + V1 composite Health Score implemented
    User-approved research qualification
    Not operationally promoted

Legacy Momentum_Detector_V8.py:
    Preserved as comparator
    Inherited V4-V7 0-100 Score remains unapproved
```

The next decision is not whether the Score exists—it now does. The next decision is how to address date instability, whether technology becomes the initial supported research sector, and what further untouched holdout is required before operational promotion.
