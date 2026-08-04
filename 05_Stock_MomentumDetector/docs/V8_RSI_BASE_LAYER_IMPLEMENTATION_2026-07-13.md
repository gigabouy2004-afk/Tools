# V8 RSI Base-Layer Implementation

Date: 2026-07-13

Status: first configurable post-Foundation indicator cutoff implemented and functionally validated. The values 30 and 65 are explicit placeholders used only to prove variable-driven boundaries, cutoff behavior and messages. They are not recommended RSI limits, professional-trading defaults or operationally approved values.

## 1. Required Execution Sequence

```text
Daily OHLCV data
    -> EMA200 and MACD Foundation
    -> stop if Foundation_Eligible = False
    -> calculate the post-Foundation indicator values
    -> evaluate RSI against configured limits
    -> allow or stop later indicator-rule processing
```

RSI never overrides or manufactures Foundation eligibility.

## 2. RSI Definition and Configuration

The calculation uses the same standard 14-session RSI definition from the Python `ta` library used by the original V1-V3 engine.

Configuration:

```text
RSI period: 14
Lower limit: 30
Upper limit: 65
Boundary mode: inclusive
Authority: CONFIGURABLE_CONTINUATION_GATE
Limit status: PLACEHOLDER_FUNCTIONAL_TEST_ONLY
Operational use approved: False
```

Therefore:

```text
RSI < 30       -> stop further indicator-rule processing
30 <= RSI <= 65 -> allow further indicator-rule processing
RSI > 65       -> stop further indicator-rule processing
```

The limits are script variables in `config/V8_Basic_Foundation_Config.json` and can be overridden with:

```text
--rsi-lower-limit
--rsi-upper-limit
```

The engine rejects a lower limit that is equal to or greater than the upper limit.

## 3. Output Contract

The output exposes:

```text
RSI
RSI_Period
RSI_Authority
RSI_Rule_Type
RSI_Limit_Status
RSI_Operational_Use_Approved
RSI_Lower_Limit
RSI_Upper_Limit
RSI_Range_Status
RSI_Allows_Further_Processing
RSI_Message
```

Example requested behavior for RSI 45:

```text
RSI: 45
RSI_Range_Status: RSI_WITHIN_CONFIGURED_RANGE
RSI_Allows_Further_Processing: True
RSI_Message: RSI 45.00 is within inclusive limits 30 to 65; further indicator rule processing is allowed
```

Other messages follow the same pattern and always contain the actual RSI value and the limit that caused the result.

## 4. Authority Boundary

RSI currently has `CONFIGURABLE_CONTINUATION_GATE` behavior inside the development engine. Its `Limit_Status` is `PLACEHOLDER_FUNCTIONAL_TEST_ONLY` and `Operational_Use_Approved` is false. It proves that the configured cutoff can allow or stop future post-RSI indicator rules; it does not approve 30 or 65 as trading values.

It does not currently:

- alter `Foundation_Eligible`;
- create an Active, Wait or Reject trade status;
- award or subtract points;
- rank stocks;
- create a trade recommendation.

ADX/DMI, True Range/ATR, OBV/OBV EMA and Aroon remain calculation-only. No limits or interpretations have been invented for them.

## 5. Functional Tests

The focused basic-engine module contains 19 tests and the complete repository suite contains 41 tests.

RSI-specific coverage includes:

- RSI 29.99 is below range and stops;
- RSI 30 is inside the inclusive range and allows;
- RSI 45 is inside the range, displays 45.00 and allows;
- RSI 65 is inside the inclusive range and allows;
- RSI 65.01 is above range and stops;
- unavailable RSI stops safely;
- invalid lower/upper configuration is rejected;
- CLI/config overrides are embedded in the Configuration ID;
- Foundation-ineligible stocks never calculate or evaluate RSI;
- independently generated messages and Boolean results match engine output.
- placeholder limits cannot claim operational approval;
- every output row publishes placeholder/approval metadata.

## 6. Ten-Symbol Execution Sample

Common evaluation date: 2026-05-07.

Symbols:

```text
AAPL, GOOGL, AMD, ORCL, PANW, CRWD, MU, QCOM, AMAT, LRCX
```

All ten were deliberately selected from the Foundation-eligible cohort on that date so the RSI value/message contract could be observed.

| Ticker | RSI | Result | Continue? |
|---|---:|---|---|
| AAPL | 69.31 | Above 65 | No |
| GOOGL | 83.41 | Above 65 | No |
| AMD | 76.14 | Above 65 | No |
| ORCL | 68.75 | Above 65 | No |
| PANW | 70.77 | Above 65 | No |
| CRWD | 70.43 | Above 65 | No |
| MU | 77.49 | Above 65 | No |
| QCOM | 82.61 | Above 65 | No |
| AMAT | 57.85 | Within 30-65 | Yes |
| LRCX | 63.50 | Within 30-65 | Yes |

Captured evidence:

```text
backtests/V8_RSI_Base/samples/V8RSI10_20260507_PLACEHOLDER
```

## 7. Frozen 20-Stock/Four-Date Replay

Canonical run:

```text
backtests/V8_Basic_Foundation/runs/V8BASICFOUND_20260712T213957Z_f16019c
```

Result:

```text
Total rows: 80
Foundation eligible: 25
Foundation ineligible: 55
RSI evaluated: 25/25 eligible rows
RSI not evaluated: 55/55 ineligible rows
RSI within 30-65: 12
RSI above 65: 13
RSI below 30: 0
RSI limit status: PLACEHOLDER_FUNCTIONAL_TEST_ONLY
Operational use approved: False
Foundation regression changes: 0/80
Independent validation failures: 0
Checksums: PASS
```

## 8. Interpretation

The mechanics work as specified: configuration, inclusive limits, actual-value messages, continuation Boolean, Foundation ordering and audit output all passed.

The sample also shows why functional validation and performance approval are separate. An upper limit of 65 stops many stocks precisely when the Foundation identifies strong positive momentum. Whether those exclusions improve or damage D+1, D+5 and D+8 outcomes must be tested during the individual RSI research phase.

Preliminary cohort observation from this same replay:

| RSI cohort | Rows | D+1 positive | D+1 mean | D+5 positive | D+5 mean | D+8 positive | D+8 mean |
|---|---:|---:|---:|---:|---:|---:|---:|
| Within 30-65; allowed | 12 | 7/12 | +0.44% | 11/12 | +6.63% | 9/12 | +9.67% |
| Above 65; stopped | 13 | 12/13 | +3.85% | 12/13 | +9.57% | 9/13 | +10.77% |

This is not a final backtest because the sample is small and was not reserved as a holdout. It is nevertheless a material warning about the placeholder's observed behavior: in this cohort, the test upper limit of 65 removed the group with the stronger D+1 hit rate and mean return. The RSI drill-down must independently research suitable interpretations and values before any RSI cutoff is proposed for operational use.

No change to the 30-65 limits should be made from this small functional sample alone.

## 9. Next Indicator Workflow

For each later indicator:

1. confirm its standard formula and period;
2. specify the exact lower, upper, crossover or comparison rule;
3. add configurable variables;
4. expose the actual value, status, continuation Boolean and plain-language message;
5. test exact boundaries;
6. execute the common 10-symbol sample;
7. only then begin individual performance backtesting and approval.
