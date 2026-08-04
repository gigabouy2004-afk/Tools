# V5 Final Decision Implementation

Date: 2026-07-02

Current output contract reference:

- `docs/V5_CURRENT_OUTPUT_CONTRACT_2026-07-04.md`

The contract is explicit: `Final_Decision` is the only primary user-facing decision. Internal score/status/rank fields may remain in CSV output for audit, but they must not be described as a formula or multi-column ranking method the end user must interpret.

## Objective

Replace reliance on the old user-facing `Actionable Momentum Candidate` status with one primary execution column:

- `Final_Decision`

The internal score/status fields remain in the CSV for audit, but the field to read is now `Final_Decision`.

## Final Decisions

| Final_Decision | Meaning |
|---|---|
| `MOMENTUM_ACTIVE` | Momentum is active now. This is the only actionable decision. |
| `MOMENTUM_PRESENT_WAIT_CONFIRMATION` | Momentum structure is present, but immediate-entry confirmation is not strong enough. |
| `REJECT` | Not qualified for action. |

## Confirmation Gates Added

The engine now downgrades a raw momentum setup unless all of these are satisfied:

- Score at least `85`.
- Weekly trend is `Uptrend`.
- Entry timing is `Clean`.
- `RS_126D_Excess_Pct >= 5`.
- `ATR_Pct <= 10`.
- `Return_5D_Pct <= 12`.
- `Return_10D_Pct <= 20`.
- `Relative_Volume_20 >= 1.0`.
- `Close_Location_Pct >= 50`.

These are internal gates. The output remains one decision column.

## New Internal Fields

Added to engine output for audit:

- `Final_Decision`
- `Final_Decision_Rank`
- `Final_Decision_Reason`
- `Volume_Avg_20`
- `Relative_Volume_20`
- `Close_Location_Pct`
- `Extension_Risk`

## Validation Result

Replayed the six existing random-20 rounds:

- May 6, 2026: 3 rounds.
- May 19, 2026: 3 rounds.
- Total rows validated: 114.

Consolidated output:

- `backtests/V5_FinalDecision_Validation_Consolidated_20260702.csv`

Result by `D_Final_Decision`:

| D_Final_Decision | PASS | FLAG_REVIEW | OBSERVE_CONTINUED | PASS_WAIT | PASS_REJECT | PASS_WATCHLIST_NO_CONFIRMATION |
|---|---:|---:|---:|---:|---:|---:|
| `MOMENTUM_ACTIVE` | 1 | 0 | 0 | 0 | 0 | 0 |
| `MOMENTUM_PRESENT_WAIT_CONFIRMATION` | 0 | 0 | 11 | 3 | 0 | 2 |
| `REJECT` | 0 | 68 | 0 | 0 | 29 | 0 |

The previous failed actionable rows are no longer confirmed entries:

| Ticker | Old Problem | New Final_Decision | Internal Blocker |
|---|---|---|---|
| `PL` | Failed D+1 and D+2 after old actionable label | `MOMENTUM_PRESENT_WAIT_CONFIRMATION` | 5D extension above 12%; relative volume below 1.0x |
| `CVV` | Failed D+1 and D+2 after old actionable label | `MOMENTUM_PRESENT_WAIT_CONFIRMATION` | ATR above 10%; 5D extension above 12%; 10D extension above 20% |
| `ETN` | Failed D+1 and D+2 after old actionable label | `MOMENTUM_PRESENT_WAIT_CONFIRMATION` | RS excess below 5% |

## Remaining Risk

This revision is intentionally conservative.

It reduced false confirmed entries in the tested sample, but it also downgrades some rows that did continue. That is acceptable for now because the immediate requirement is that the single confirmed-entry column should not be overconfident.

The next validation should expand the sample size and evaluate only `MOMENTUM_ACTIVE` as the actionable output.
