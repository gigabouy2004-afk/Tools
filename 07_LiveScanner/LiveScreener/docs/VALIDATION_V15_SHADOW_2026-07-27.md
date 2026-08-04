# V15 Shadow Validation — 2026-07-27

## Scope

This validation checks the first V15 requirement: add stricter momentum and
entry-quality evidence without changing the validated V14 classifications.

V15 was created from V14 Enhanced commit `20641f5` on branch
`feat/v15-momentum-quality-shadow`.

## Static and unit validation

| Check | Result |
|---|---|
| V14 reference syntax | PASS |
| V14 Enhanced syntax | PASS |
| V15 syntax | PASS |
| Existing V14 regression tests | 24/24 PASS |
| New V15 shadow tests | 15/15 PASS |
| Total test suite | 39/39 PASS |
| Patch whitespace check | PASS |

The new tests cover:

- trailing-return boundary behavior;
- `NONE`, `WEAK`, `DEVELOPING`, and `LEADER` state boundaries;
- entry-state priority;
- error handling; and
- preservation of V14 `status`, `classification`, and `output_signal`.

## Completed-session parity sample

Twenty-one symbols were replayed through V14 Enhanced and V15 as of the
completed 2026-07-24 session. The set included `GLOSTERLTD.NS` and twenty
symbols from the earlier U.S. scan review.

The following fields were compared:

- `status`;
- `classification`;
- `output_signal`; and
- `setup_type`.

Result: **21/21 exact matches; zero mismatches.**

`GLOSTERLTD.NS` remained `HOLD / NO_BUY`. V15 additionally reported
`momentum_state=NONE` and `entry_state=NO_ENTRY` because its required positive
MACD regime was absent. Its other shadow evidence cannot override that primary
gate.

## XLI three-date regression

Symbols:

```text
CAT, GE, RTX, GEV, UNP, BA, ETN, DE, UBER, PH
```

| Date | V14/V15 parity | Operational BUYs | Shadow CONFIRMED |
|---|---:|---|---|
| 2026-07-22 | 10/10 | None | None |
| 2026-07-23 | 10/10 | RTX, ETN | None |
| 2026-07-24 | 10/10 | RTX, UNP, PH | None |

Result: **30/30 exact operational matches; zero mismatches.**

The operational BUY counts reproduce the validated positive-regime baseline:
0, 2, and 3.

No BUY in this small three-date regression passes every initial V15 shadow
gate. The separating states are `WAIT_EXTENDED`, `WAIT_ADX`, or `WAIT_VOLUME`.
This is evidence that the initial V15 hypotheses are materially more selective;
it is not evidence that they improve forward outcomes.

## Interpretation

The frozen-classification implementation succeeds: V15 can expose disagreement
without altering V14 behavior.

The shadow thresholds must remain non-binding while a larger historical sample
measures:

- forward return and win rate;
- maximum favorable and adverse excursion;
- precision gained versus valid candidates discarded;
- results by listing market and liquidity group; and
- the individual contribution of each proposed gate.

Only after those measurements and owner review should a separate activation
commit be considered.

## Command-line smoke run

The V15 entry point processed `GLOSTERLTD.NS`, `RTX`, `UNP`, and `PH` as of
2026-07-24 with two workers and completed-candle mode.

| Check | Result |
|---|---|
| Codes processed | 4/4 |
| Operational statuses | 3 BUY, 1 HOLD |
| Operational BUYs | RTX, UNP, PH |
| Shadow CONFIRMED | 0 |
| Data through | 2026-07-24 |
| XLSX output | Written successfully |
| Text log | Written successfully |

The summary clearly separates operational BUYs from shadow recommendations and
states that V15 classification is inactive.
