# V14 to V15 Handover, Controls, and Owner Approval

Document date: 2026-07-27

Document status: **SUBMITTED FOR OWNER APPROVAL**

Implementation status: V15 shadow baseline complete; Phase 2 not started

Activation status: V15 classifications are not active

## 1. Handover identity

| Item | Value |
|---|---|
| Repository | `https://github.com/gigabouy2004-afk/LiveScreener` |
| Authoritative local Git repository | `D:\Tools\07_LiveScanner\LiveScreener` |
| V15 feature branch | `feat/v15-momentum-quality-shadow` |
| V15 implementation baseline | `ae1ce80` |
| Validated V14 positive-regime baseline | `20641f5` |
| Parent execution folder | `D:\Tools\07_LiveScanner` |
| V14 reference engine | `Live_Scanner_v14.py` |
| V14 validated operational engine | `Live_Scanner_v14_Enhanced.py` in the Git repository |
| V15 shadow engine | `Live_Scanner_v15.py` |
| V15 classification mode | V14 operational fields frozen; V15 fields non-binding |
| Owner approval | Pending |
| Merge to `main` | Not requested and not performed |
| Production activation | Not approved |

This document is the approval boundary between the corrected V14 intent, the
current V15 shadow implementation, and any later V15 Phase 2 work.

## 2. Executive summary

V14 is an independent per-ticker scanner for established positive setup, trend,
and momentum. It is not a pre-bull or pre-bear crossover detector, a
universe-relative ranker, a benchmark forecaster, or an order-execution engine.

The corrected V14 mandate requires a positive daily and weekly trend plus a
confirmed positive MACD regime before secondary indicators may qualify or
strengthen a candidate. Negative MACD histogram improvement cannot be described
as positive momentum and cannot produce a BUY.

V15 does not replace that mandate. V15 Phase 1 preserves every V14 operational
classification and adds two separate audit layers:

1. `momentum_state` describes the measured quality of the positive momentum
   condition.
2. `entry_state` describes whether additional ADX, volume, extension, and
   leadership evidence supports immediate confirmation.

The first full V15 run proved that this separation works without regression,
but also showed that the initial shadow thresholds are too restrictive for
activation. Only one of 41 operational BUYs was shadow-confirmed. Therefore,
V15 must remain in shadow mode while Phase 2 is designed, calibrated, and
separately approved.

## 3. V14 original intent

### 3.1 Business purpose

V14 reduces a large international stock-code universe to a smaller list of
codes with established positive technical conditions. The expected human
workflow is:

1. run the scanner;
2. retain technically valid candidates;
3. perform additional offline validation, such as Performance Comparator and
   ETF Mapping;
4. decide whether the setup is confirmed or still awaiting confirmation; and
5. make any investment decision outside the scanner.

The engine is a screening and classification tool. It is not an investment
recommendation and does not place trades.

### 3.2 Independent ticker contract

Every ticker is evaluated from its own market data and listing metadata.
Classification must not depend on:

- another code in the input list;
- input order;
- thread completion order;
- the number of BUYs already found;
- a U.S. benchmark applied to a non-U.S. listing; or
- the composition or performance of the scanned universe.

Concurrency is operational only. Worker count may change elapsed time but must
not change a ticker's result.

### 3.3 Mandatory positive-regime gates

Every BUY path is contained inside these mandatory conditions:

```text
daily close > EMA50 > EMA200
completed weekly close > weekly EMA20 > weekly EMA50
MACD > signal
MACD > 0
signal > 0
MACD histogram > 0
```

Additional setup-specific conditions are evaluated only after the primary
regime is established.

The consequences are deliberate:

- price above EMA50/EMA200 cannot compensate for bearish MACD;
- ADX, stochastic, RSI, volume, or price response cannot rescue failed primary
  gates;
- MACD and signal below zero are outside the positive-momentum mandate;
- an improving but negative histogram is not positive momentum;
- BUY#4 is a fresh bullish MACD signal-line crossover above zero with a
  positive histogram; and
- momentum continuation requires a sustained configured expansion window with
  its latest two histogram bars positive.

### 3.4 GLOSTERLTD.NS control case

The historical 2026-07-24 `GLOSTERLTD.NS` case is the permanent negative
control for this mandate:

- price trend was positive;
- MACD was below its signal;
- histogram was negative;
- status was `HOLD`;
- classification was `NO_BUY`; and
- secondary evidence received no authority to override MACD.

Any future engine that classifies that condition as confirmed positive momentum
has violated the approved scope.

## 4. V14 operational classification and messaging contract

### 4.1 Operational statuses

| Status | Meaning |
|---|---|
| `BUY` | The V14 positive regime and setup-specific confirmation rules pass |
| `HOLD` | Trend/setup may exist, but confirmation or an approved quality policy is pending |
| `IGNORE` | Required daily or weekly trend alignment is absent |
| `REJECT` | A defined rejection/exhaustion path applies |
| `ERROR` | Data or indicator evaluation could not complete reliably |

### 4.2 User classifications

| Classification | V14 meaning |
|---|---|
| `BUY#1` | Positive-regime pullback oversold recovery |
| `BUY#2` | Positive-regime EMA20 midrange recovery |
| `BUY#3` | Confirmed momentum continuation |
| `BUY#4` | Fresh positive-phase MACD crossover |
| `BUY_EXTENDED_REVIEW` | V14 BUY retained, but more than 5 ATR above EMA50 |
| `NO_BUY` | Any non-BUY operational outcome |

### 4.3 Message fields

The following fields have distinct responsibilities and must not be
interchanged:

| Field | Responsibility |
|---|---|
| `status` | Stable operational category used for counts and sorting |
| `classification` | Concise end-user result such as `BUY#3` or `NO_BUY` |
| `OUT_MESSAGE` / workbook `Message` | Prominent display classification |
| `output_signal` | Exact machine-readable rule path |
| `reason` | Short human-readable reason |
| `setup_type` | Technical setup family and policy suffixes |
| `message_details` | Auditable rule and policy details |
| `risk_level` | Extension, liquidity, or setup-risk description |
| `confidence` | Existing V14 setup-score label |

External validation tools should use `ticker`, `status`, `classification`, and
`output_signal` as structured inputs. They should not parse prose from
`message_details` when a dedicated field exists.

## 5. Approved V14 hardening controls

The current validated V14 Enhanced baseline includes:

- a mandatory current-volume ratio floor of 0.60 before other volume-support
  paths can qualify a BUY;
- a USD 1 million prior-20-session average daily turnover minimum for U.S. BUY
  candidates;
- `BUY_EXTENDED_REVIEW` beyond 5 ATR above EMA50;
- a base BUY stochastic K/D limit of 80, with approved prior-positive-session
  relaxation for the applicable positive setup;
- prominent actual `DataThrough` reporting;
- live/as-of policy parity;
- complete poll-boundary retention; and
- strict positive MACD/histogram scope.

International absolute turnover gates remain disabled until currency-aware or
exchange-specific policy is approved.

## 6. Why V15 is required

V14 correctly identifies the positive technical regime, but an operational BUY
does not by itself answer all of the following:

- Is the medium- and long-term trend still accelerating?
- Is price performance positive across several horizons?
- Is directional movement bullish?
- Is ADX strong or developing?
- Is current volume confirming participation?
- Is the stock behaving near its prior 52-week high?
- Is a valid momentum condition already too extended for a normal entry?
- Is the setup a leader, developing, weak, or merely awaiting a V14 trigger?

V15 addresses this information gap without allowing new evidence to rewrite
V14 before historical proof and owner approval exist.

## 7. V15 Phase 1 implementation

### 7.1 Frozen operational contract

V15 Phase 1 records:

```text
v15_classification_active = False
```

The following fields remain governed by V14:

- `status`;
- `classification`;
- `output_signal`;
- `setup_type`;
- all BUY/HOLD/IGNORE/ERROR counts; and
- all approved V14 quality policies.

V15 disagreement is reported through separate shadow fields only.

### 7.2 Ten shadow quality checks

| Check | Phase 1 hypothesis |
|---|---|
| EMA50 slope | 20-session percentage change is positive |
| EMA200 slope | 60-session percentage change is non-negative |
| 20-session return | Positive |
| 60-session return | Positive |
| 120-session return | Positive |
| Directional movement | `+DI > -DI` |
| ADX | At least 20 |
| Prior 52-week high proximity | Price is at least 85% of the high |
| Volume participation | Current/prior-20-session average is at least 1.0 |
| Normal entry extension | Price is no more than 3 ATR above EMA50 |

Each check currently contributes one point. Equal weighting is an auditable
starting hypothesis, not an approved statement of predictive value.

### 7.3 Momentum states

| Momentum state | Rule |
|---|---|
| `NONE` | Mandatory primary regime fails, regardless of quality score |
| `LEADER` | Primary regime passes and quality score is 8-10 |
| `DEVELOPING` | Primary regime passes and quality score is 6-7 |
| `WEAK` | Primary regime passes and quality score is 0-5 |

### 7.4 Entry states

Entry states are evaluated in this priority:

1. `NOT_APPLICABLE` - engine error.
2. `NO_ENTRY` - mandatory primary regime failed.
3. `WAIT_EXTENDED` - more than 3 ATR above EMA50.
4. `WAIT_ADX` - ADX below 20 or `+DI <= -DI`.
5. `WAIT_VOLUME` - current volume below its prior-20-session average.
6. `WAIT_LEADERSHIP` - positive regime exists but state is not `LEADER`.
7. `CONFIRMED` - shadow gates pass and V14 status is BUY.
8. `WAIT_TRIGGER` - shadow quality passes but V14 has not produced a BUY.

`shadow_recommended_status` expresses the shadow interpretation. It does not
change operational `status`.

## 8. V15 full-run evidence

Source run:

```text
D:\TMP\Live_Screener\27-07-2026-Validated-USA-Result-withengineV15.xlsx
D:\TMP\Live_Screener\27-07-2026-Validated-USA-Result-withengineV15.log
```

Run configuration:

| Item | Result |
|---|---|
| Requested mode | `completed` |
| Input codes | 3,636 |
| Processed | 3,636 |
| Workers | 3 |
| Historical guidance | 1Y |
| Operational BUY | 41 |
| HOLD | 793 |
| IGNORE | 2,510 |
| ERROR | 292 |
| Operational BUY breakup | 33 continuation, 8 early momentum |
| Shadow CONFIRMED | 1 (`BMY`) |
| Current automated test suite | 44/44 passed |

Global entry-state distribution:

| Entry state | Count |
|---|---:|
| `NO_ENTRY` | 3,069 |
| `NOT_APPLICABLE` | 292 |
| `WAIT_ADX` | 108 |
| `WAIT_EXTENDED` | 88 |
| `WAIT_VOLUME` | 67 |
| `WAIT_TRIGGER` | 11 |
| `CONFIRMED` | 1 |

Independent replay of the 41 operational BUY symbols produced:

| Result | Count |
|---|---:|
| Operational BUY reproduced | 41/41 |
| Daily EMA invariant failures | 0 |
| Weekly EMA invariant failures | 0 |
| Positive MACD invariant failures | 0 |
| Completed session other than 2026-07-24 | 0 |
| `LEADER` | 36 |
| `DEVELOPING` | 5 |
| `WAIT_EXTENDED` | 17 |
| `WAIT_ADX` | 17 |
| `WAIT_VOLUME` | 6 |
| `CONFIRMED` | 1 |

The evidence supports two conclusions:

1. The V14/V15 separation and primary positive-regime controls work.
2. The initial V15 entry thresholds are too selective for activation without
   further calibration.

## 9. V15 Phase 2 proposal - not yet implemented

Phase 2 must improve discrimination without weakening the primary V14 mandate.

### 9.1 Graduated ADX confirmation

Candidate hypothesis for testing:

- ADX below 15: weak confirmation / `WAIT_ADX`;
- ADX 15-20 with rising ADX and bullish DI: developing confirmation;
- ADX at least 20 with bullish DI: confirmed direction; and
- `+DI <= -DI`: directional confirmation fails irrespective of ADX.

These bands are proposed test cases, not approved production thresholds.

### 9.2 Graduated volume confirmation

Candidate hypothesis for testing:

- ratio at least 1.0: strong current confirmation;
- ratio 0.8-1.0: acceptable/developing participation;
- ratio 0.60-0.80: weak but above the existing V14 safety floor; and
- ratio below 0.60: fails the approved V14 floor.

Historical volume percentile may remain context, but it must not hide
materially weak current participation.

### 9.3 Extension separation

Candidate hypothesis for testing:

- up to 3 ATR above EMA50: normal entry zone;
- more than 3 and up to 5 ATR: valid momentum with extended-entry warning;
- more than 5 ATR: extreme review or strict entry wait.

Extension must describe entry risk separately from whether positive momentum
exists.

### 9.4 Data freshness

Phase 2 should expose an explicit stale-session control based on the listing's
native exchange calendar and market state. A stale candle must not be presented
as current momentum merely because indicator calculations succeeded.

### 9.5 Performance Comparator and ETF Mapping

The user's comma-separated code string must remain available for downstream
Performance Comparator and ETF Mapping workflows.

Any future benchmark-relative or ETF-relative field inside V15 must:

- remain ticker-specific and auditable;
- use a suitable native-market benchmark;
- never apply one U.S. benchmark to all international listings;
- expose benchmark identity and data-through date;
- begin as non-binding output; and
- require a separate engine-contract approval before classification use.

### 9.6 Calibration evidence required

Before any Phase 2 gate can activate, historical testing must measure:

- forward returns over agreed holding periods;
- maximum favorable excursion;
- maximum adverse excursion;
- win rate and candidate count;
- false positives removed;
- valid candidates lost;
- performance by exchange, liquidity group, and setup type; and
- incremental effect of each proposed gate in isolation.

## 10. Input contract

### 10.1 Direct code input

`-c` / `--codes` accepts the reusable comma-separated format.

All of these are valid:

```powershell
-c ETN,VRT,PWR,GEV,CAT,PH
-c "ETN, VRT, PWR, GEV, CAT, PH"
-c ETN VRT PWR GEV CAT PH
```

The parser:

- splits every argument segment on commas;
- trims leading and trailing spaces;
- normalizes to uppercase;
- removes duplicates while retaining first occurrence order; and
- stores the normalized comma-separated list in the Summary sheet.

The comma-separated form is the preferred operator contract because the same
string is used in downstream validation.

Focused regression tests cover compact commas, comma-plus-leading-space,
space-segmented arguments, mixed segments, duplicate removal, empty segments,
and exchange-code normalization.

### 10.2 CSV input

`-i` / `--input` accepts a CSV containing one of these case-insensitive header
names:

- `Ticker`;
- `Tickers`; or
- `Symbol`.

Optional company-name headers include:

- `Security Name`;
- `Company Name`;
- `company_name`;
- `Company`; or
- `Name`.

Blank/null-like codes are ignored. Duplicate codes are removed in first-seen
order. Direct `-c` input takes precedence over `-i`.

If the requested CSV is missing or invalid, the present engine falls back to
the default `MU` watchlist and prints a warning. This fallback must be visible
to the operator; a future strict-input option may be considered separately.

### 10.3 Symbol normalization

Examples of supported normalization:

- whitespace is trimmed;
- codes are converted to uppercase;
- `XNSE:` codes become Yahoo `.NS` listings;
- `XBOM:` / `XBSE:` codes become `.BO` listings; and
- preferred-share `$` notation is converted to Yahoo `-P` form.

### 10.4 Historical and candle controls

| Option | Meaning |
|---|---|
| `--as-of-date YYYY-MM-DD` | One historical evaluation date |
| `--as-of-dates date1,date2` | Multi-date historical validation |
| `--live-candle-mode auto` | Resolve completed/provisional behavior from native listing session |
| `--live-candle-mode completed` | Use completed-session data |
| `--live-candle-mode intraday` | Attempt a provisional current-session candle |
| `--live-history-years` | Core technical-calculation history |
| `--workers` | Independent concurrent ticker workers |
| `--countmax` | Poll-boundary processed-count continuation trigger |
| `--max-buys` | Poll-boundary BUY-count continuation trigger |

`Max-Count` and `Max-Buys` do not cancel work already submitted and do not
create exact output caps. Complete final-poll results are retained.

## 11. Output contract

### 11.1 Files

For output target `result.xlsx`, V15 creates:

```text
result.xlsx
result.log
```

Built-in historical signal replay writes CSV to `--backtest-output`.

### 11.2 Workbook sheets

| Sheet | Content |
|---|---|
| `Summary` | Execution identity, code counts, operational results, shadow results, configuration, paths, and normalized direct-code string |
| `Details` | One structured ticker/date result per row, sorted by operational status, date, score, and ticker |

The Details sheet freezes panes at `E2`.

### 11.3 Important Details field groups

Operational identity and messages:

- `Ticker`, `engine_version`, `status`, `Message`, `output_signal`, `reason`,
  `setup_type`, `confidence`, and `risk_level`.

V15 shadow controls:

- `v15_shadow_mode`, `v15_classification_active`,
  `v15_primary_regime_passed`, `momentum_state`, `entry_state`,
  `shadow_recommended_status`, `momentum_quality_score`, and check fields.

Session and listing context:

- exchange, currency, market phase, data mode, market-local time,
  `session_date`, `candle_state`, and `data_note`.

Trend and performance:

- price, EMA20/50/200, weekly EMA20/50, EMA slopes, 20/60/120-session returns,
  prior 52-week context, and ATR extension.

Momentum and confirmation:

- MACD, signal, histogram and histogram history; ADX, `+DI`, `-DI`, ADX change;
  RSI; stochastic; volume ratio; historical volume context; and liquidity
  policy fields.

Advisory history:

- requested/actual guidance scope, sessions, price/RSI/ADX/stochastic/volume
  extrema, percentiles, and confidence context.

### 11.4 Terminal and log messages

The scanner reports:

- startup identity and configuration;
- initial `DataThrough=PENDING`;
- poll submission and per-ticker completion;
- poll totals and any poll-boundary stop reason;
- final actual data-through date/range;
- operational BUY/HOLD/IGNORE/REJECT/ERROR counts;
- operational BUY symbols and signal breakup;
- shadow BUY count and symbols;
- shadow entry-state breakup;
- explicit `V14 frozen; V15 shadow fields are non-binding`;
- requested candle mode; and
- exact XLSX and log paths.

An output without the explicit classification-mode message must not be treated
as the approved V15 Phase 1 build.

## 12. Checks and balances

### 12.1 Source control

- V14 files are not edited as part of V15.
- V15 work occurs on `feat/v15-momentum-quality-shadow`.
- `main` is not changed without owner approval.
- Phase 2 must use separate commits from the Phase 1 baseline.
- Production activation must be a separate, reviewable commit.

### 12.2 Logic invariants

Every operational or future activated BUY must satisfy:

- daily EMA ordering;
- completed weekly EMA ordering;
- MACD above signal;
- both MACD lines above zero; and
- positive histogram.

Secondary indicators cannot rescue a failed primary invariant.

### 12.3 Regression controls

Required after any signal or policy change:

- syntax compilation of V14 reference, V14 Enhanced, and V15;
- full unit suite;
- GLOSTER negative control;
- XLI three-date regression;
- V14/V15 operational-field parity while shadow mode remains active;
- BUY primary-gate invariant scan;
- data-through validation;
- input-format tests, including comma plus leading spaces; and
- representative U.S. and international runs.

### 12.4 Deployment controls

The Git repository is the source of truth. The parent folder is an execution
deployment location, not a second development repository.

Before a run:

```powershell
Get-FileHash `
  "D:\Tools\07_LiveScanner\Live_Scanner_v15.py", `
  "D:\Tools\07_LiveScanner\LiveScreener\Live_Scanner_v15.py" `
  -Algorithm SHA256
```

Both V15 hashes must match.

### 12.5 Data and operational controls

- Review `Data through`, not only `As-of label`.
- Review row-level `session_date` and `candle_state`.
- Treat provisional intraday BUY conditions as HOLD until completion.
- Review all ERROR rows and do not silently exclude them from denominators.
- Verify the normalized direct-code string before downstream comparison.
- Do not infer international liquidity from USD thresholds.

## 13. Source and deployment manifest

### 13.1 Authoritative Git files

| File | SHA-256 |
|---|---|
| `Live_Scanner_v14.py` | `489A1BEA189CC050CEDB456BD0A133A83F825C848F262910F2811D58E7E69116` |
| `Live_Scanner_v14_Enhanced.py` | `6FFF0F8ED1DB00B6991DD808B4BC2B082B6E039068A0AE4AB173144230AE35FE` |
| `Live_Scanner_v15.py` | `976430111C26885732F36D5FFEC5DB27968B539D4D16229ADA8BE0B7125C54DF` |

### 13.2 Parent execution folder

| File | SHA-256 | State |
|---|---|---|
| `Live_Scanner_v14.py` | `489A1BEA189CC050CEDB456BD0A133A83F825C848F262910F2811D58E7E69116` | Matches Git |
| `Live_Scanner_v14_Enhanced.py` | `2B4CFCAAD473664069AAC97BB465774BFFCF13DBA8FDE24B2F1A57AB50256230` | **Legacy copy; does not match validated Git V14 Enhanced** |
| `Live_Scanner_v15.py` | `976430111C26885732F36D5FFEC5DB27968B539D4D16229ADA8BE0B7125C54DF` | Matches Git |

No automatic overwrite of the legacy parent-folder V14 Enhanced file has been
performed. Until the owner chooses a resolution, the authoritative validated
V14 Enhanced file is:

```text
D:\Tools\07_LiveScanner\LiveScreener\Live_Scanner_v14_Enhanced.py
```

## 14. Operator runbook

### 14.1 Confirm V15 source

```powershell
cd D:\Tools\07_LiveScanner\LiveScreener
git switch feat/v15-momentum-quality-shadow
git pull --ff-only
git branch --show-current
git rev-parse --short HEAD
```

### 14.2 Environment and tests

```powershell
python -m pip install -r requirements.txt
python -m py_compile .\Live_Scanner_v14.py
python -m py_compile .\Live_Scanner_v14_Enhanced.py
python -m py_compile .\Live_Scanner_v15.py
python -m unittest discover -s tests -v
```

### 14.3 Direct comma-separated run

```powershell
python "D:\Tools\07_LiveScanner\Live_Scanner_v15.py" `
  -c "ETN, VRT, PWR, GEV, CAT, PH" `
  --live-candle-mode auto `
  -o "D:\TMP\27-7-2026\27-7-2026-ETN_VRT_PWR_GEV_CAT_PH.xlsx"
```

### 14.4 Completed-candle validation

```powershell
python "D:\Tools\07_LiveScanner\Live_Scanner_v15.py" `
  -c "GLOSTERLTD.NS, RTX, UNP, PH" `
  --as-of-date 2026-07-24 `
  --live-candle-mode completed `
  -o "D:\TMP\Live_Screener\V15_completed_validation.xlsx"
```

### 14.5 Full-universe run

```powershell
python "D:\Tools\07_LiveScanner\Live_Scanner_v15.py" `
  -i "D:\Tools\00_StockCodeMaster\02_Stock\22-07-US_Common_Stocks_Master_Library.csv" `
  --workers 3 `
  --live-candle-mode completed `
  -o "D:\TMP\Live_Screener\V15_full_USA_shadow.xlsx"
```

### 14.6 Review order

1. Confirm branch, commit, and file hash.
2. Confirm requested candle mode.
3. Confirm `Data through` and row-level session dates.
4. Confirm input count and normalized direct-code string.
5. Review operational status/classification and signal path.
6. Review primary EMA/MACD invariants.
7. Review V15 momentum state and quality score.
8. Review shadow entry state and exact wait reason.
9. Review liquidity, extension, stochastic, and data warnings.
10. Export the normalized code string to Performance Comparator and ETF Mapping.

## 15. Known limitations and non-approved items

- V15 Phase 1 shadow gates have not demonstrated improved forward outcomes.
- Only one of 41 operational BUYs was shadow-confirmed in the first full run.
- Benchmark-relative and ETF-relative strength are not implemented.
- Data freshness needs an explicit future control beyond current session
  reporting.
- Yahoo may return missing or sparse history; the full run contained 292 ERROR
  rows.
- The artifact spreadsheet-analysis runtime is unavailable in the current
  Codex session. This affects automated workbook inspection by Codex, not
  scanner generation of XLSX files.
- The parent-folder V14 Enhanced deployment copy is not the validated
  positive-regime version.
- Phase 2 thresholds described in this document are hypotheses only.
- No V15 shadow rule is approved to modify operational classification.

## 16. Approval decisions requested

### Decision A - Accept V14 mandate and controls

- [ ] Approve the positive-regime gates as the locked engine foundation.
- [ ] Approve GLOSTERLTD.NS as a permanent negative regression control.
- [ ] Confirm that secondary indicators can never rescue failed EMA/MACD gates.

### Decision B - Accept V15 Phase 1 handover

- [ ] Approve the V15 shadow architecture and frozen V14 classification
  contract.
- [ ] Approve the documented input, output, and messaging contracts.
- [ ] Accept the recorded validation evidence and known limitations.

### Decision C - Authorize V15 Phase 2 development

- [ ] Authorize development and backtesting of graduated ADX confirmation.
- [ ] Authorize development and backtesting of graduated volume confirmation.
- [ ] Authorize development and backtesting of refined extension states.
- [ ] Authorize development of data-freshness audit fields.
- [ ] Authorize design of non-binding, exchange-aware comparator/ETF fields.

Authorization to develop Phase 2 does **not** authorize activation.

### Decision D - Resolve the parent V14 Enhanced copy

Select one:

- [ ] Replace the legacy parent copy with the validated Git V14 Enhanced file.
- [ ] Rename/archive the legacy parent copy, then deploy the validated file.
- [ ] Retain the legacy parent copy with an explicit warning suffix.
- [ ] Other owner instruction: __________________________________________

### Decision E - Git disposition

Select one:

- [ ] Keep V15 on the feature branch during Phase 2.
- [ ] Open a pull request for documentation review only.
- [ ] Merge the Phase 1 shadow baseline to `main` while keeping activation off.
- [ ] Other owner instruction: __________________________________________

## 17. Signoff record

Engineering preparation:

| Item | Status |
|---|---|
| V14 intent reconstructed and documented | Complete |
| V14 positive-regime correction | Complete and validated |
| V15 Phase 1 implementation | Complete |
| V14/V15 operational parity | Passed for documented samples |
| V15 full-run audit | Complete |
| Current automated test suite | 44/44 passed |
| Input/output/message contracts | Documented |
| Git/source manifest | Documented |
| Local execution manifest | Documented |
| Phase 2 implementation | Not started |
| V15 classification activation | Not approved |
| Owner approval | Pending |

Owner decision:

```text
[ ] APPROVED AS WRITTEN
[ ] APPROVED WITH CONDITIONS
[ ] RETURNED FOR REVISION
[ ] REJECTED

Owner:
Decision date:
Conditions or comments:
```

## 18. Closure statement

This handover is ready for owner review. Approval of this document accepts the
recorded source state, contracts, controls, and development boundary. It does
not activate V15 classification rules, merge the branch, overwrite the legacy
V14 execution copy, or authorize investment decisions.

Any Phase 2 activation requires a later package containing historical evidence,
regression results, a reviewed classification diff, updated hashes, and a
separate owner signoff.
