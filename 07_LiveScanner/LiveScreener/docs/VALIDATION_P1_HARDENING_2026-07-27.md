# V14 Enhanced P1 Hardening Validation — 2026-07-27

## 1. Approved decisions

The owner approved all three P1 recommendations from the 2026-07-25 handover:

1. require a minimum current volume ratio of `0.60`;
2. require USD 1 million prior-20-session average daily turnover for U.S. BUY
   candidates; and
3. retain BUY recall beyond 5 ATR from EMA50 but label the result
   `BUY_EXTENDED_REVIEW`.

The P2 `DataThrough` summary improvement was implemented in the same change set.

## 2. Implemented semantics

### 2.1 Current volume

Historical absolute-volume percentile cannot override a current volume ratio
below `0.60`. At or above the floor, the existing immediate-ratio and
one-year-percentile support paths remain available.

### 2.2 U.S. liquidity

A U.S. BUY candidate below USD 1 million ADV20 turnover becomes HOLD with:

```text
Hold_Buy_Liquidity_Below_Minimum
```

International listings do not receive an absolute turnover gate.

### 2.3 Extreme extension

A BUY candidate more than 5 ATR above EMA50 remains status `BUY`, retains its
underlying signal name, and receives the user-facing classification:

```text
BUY_EXTENDED_REVIEW
```

Exactly 5 ATR does not trigger the review label.

## 3. Automated verification

| Check | Result |
|---|---|
| Original and enhanced Python syntax | PASS |
| CLI help | PASS |
| Unit tests | 14/14 PASS |
| Volume floor boundary at 0.60 | PASS |
| U.S. turnover boundary at USD 1 million | PASS |
| International turnover exemption | PASS |
| Extension boundary at 5 ATR | PASS |
| Weekend `DataThrough` behavior | PASS |
| Original V14 SHA-256 unchanged | PASS |

The original V14 SHA-256 remains:

```text
489A1BEA189CC050CEDB456BD0A133A83F825C848F262910F2811D58E7E69116
```

## 4. XLI regression

The documented XLI top-ten regression was rerun for 2026-07-22 through
2026-07-24.

| Date | Baseline BUY | Hardened BUY | Result |
|---|---:|---:|---|
| 2026-07-22 | 2 | 2 | Unchanged |
| 2026-07-23 | 5 | 5 | Unchanged |
| 2026-07-24 | 3 | 3 | Unchanged |

The ten retained BUY observations still comprise six Momentum Extension and four
Early Momentum signals.

## 5. Nineteen-symbol audit

The documented 19-symbol audit set was rerun through 2026-07-24.

| Status | Baseline | Hardened |
|---|---:|---:|
| BUY | 12 | 7 |
| HOLD | 2 | 7 |
| IGNORE | 2 | 2 |
| ERROR | 3 | 3 |

Expected hardening changes:

| Ticker | Baseline | Hardened | Policy |
|---|---|---|---|
| ACU | BUY#3 | NO_BUY/HOLD | ADV20 turnover below USD 1 million |
| NOEM | BUY#3 | NO_BUY/HOLD | ADV20 turnover below USD 1 million |
| LCUT | BUY#3 | NO_BUY/HOLD | Current volume ratio below 0.60 |
| NNBR | BUY#4 | NO_BUY/HOLD | Current volume ratio below 0.60 |
| WBX | BUY#4 | NO_BUY/HOLD | Current volume ratio below 0.60 |
| OII | BUY#3 | BUY_EXTENDED_REVIEW | More than 5 ATR above EMA50 |

The remaining seven BUYs were AME, OII, FTV, BRK-B, SNA, PKG, and GD.

## 6. Data-through verification

A historical request for Saturday 2026-07-25 correctly reports:

```text
As-of label  : 2026-07-25
Data through : 2026-07-24
```

Detail rows report the actual last included daily session. Mixed-market runs
report the earliest and latest included session dates plus the number of
distinct sessions.

## 7. Conclusion

The approved P1 hardening is implemented without changing the XLI regression.
The independent audit shows the intended reduction in low-participation and
low-turnover BUYs, while extreme extension remains visible for human review
instead of being silently rejected.
