# V5 Current Output Contract

Date: 2026-07-04

## Purpose

This document is the current source of truth for the V5 engine output contract.

Older handover and validation documents may mention `Action_Rank`, `Action_Status`, `Score`, or other diagnostic columns as user-facing outputs. Those older instructions are superseded. They are historical context only.

## Current User-Facing Rule

The end user must read one primary output field:

- `Final_Decision`

The engine may still write internal technical columns for audit, debugging, validation, sorting, and future calibration. Those columns are not the final user-facing answer and must not be presented as a formula the user has to interpret.

Do not describe the current engine as requiring the user to combine multiple columns such as score, trend, relative strength, timing, action rank, and status. That is no longer the product contract.

## Allowed Final Decisions

| Final_Decision | User Meaning |
|---|---|
| `MOMENTUM_ACTIVE` | Momentum is active now. This is the only actionable output. |
| `MOMENTUM_PRESENT_WAIT_CONFIRMATION` | Momentum/setup may be present, but immediate confirmation is missing or timing is not clean. |
| `REJECT` | Not valid for momentum action. |

## Internal Columns

Columns such as these are internal/audit fields:

- `Final_Decision_Rank`
- `Final_Decision_Reason`
- `Action_Rank`
- `Action_Status`
- `Long_Term_Status`
- `Entry_Timing_Status`
- `Score`
- `Trend_Score`
- `Relative_Strength_Score`
- `Breakout_Score`
- `Accumulation_Score`
- `Volatility_Score`
- `Weekly_Trend_Score`

They can be retained in CSV output for traceability, but they are not the end-user decision contract.

## Future Feature Rule

Any new data source must preserve the same single final user decision. It may be used internally or stored as audit data in a future version, but it must not create a multi-column interpretation burden for the end user.
