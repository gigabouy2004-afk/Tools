# Momentum Research Panel — Plain Field Guide

Document role: supporting dictionary for research-panel fields

Primary authority: `MOMENTUM_ENGINE_MASTER_BLUEPRINT.md`

Status: current for the implemented panel foundation

The research panel is deliberately detailed, but its column names describe
their contents without requiring internal version knowledge.

## Identity and timing

| Column | Meaning |
|---|---|
| `ticker` | Exchange symbol being studied |
| `security_id` | Stable identity used when a company changes ticker |
| `previous_completed_session` | Completed daily observation used as the foundation |
| `hypothetical_entry_session` | Trading session immediately after the daily foundation |
| `hypothetical_entry_open` | Opening price of that hypothetical entry session |
| `available_completed_sessions` | Number of stock observations available up to the foundation |
| `history_tier` | Observation-only, young, developing or established history |
| `eligible_research_track` | Research path allowed by the available stock history |

## Daily evidence

`ema_*`, `macd*`, `adx*`, `plus_di*`, `minus_di*`, `rsi*`, `stochastic*` and
`atr*` contain the named daily indicator calculated only through the previous
completed session.

Columns ending in `_available` say whether enough stock history genuinely
exists. Blank values are not failures.

Historical returns and slopes include their exact session lookback in the
column name. Volume comparisons use the previous 20 completed sessions and do
not include the current row in their average.

## Plain descriptions

| Column | Meaning |
|---|---|
| `daily_structure_description` | Plain description of the stock's available trend structure |
| `participation_description` | Whether completed daily volume is below, near or above its prior average |
| `extension_description` | ATR-normalized distance from the available medium-term trend |

These descriptions are not recommendations.

## Outcomes

For each 5-, 10- or 20-session horizon:

| Pattern | Meaning |
|---|---|
| `outcome_*_sessions_complete` | Whether the complete future window exists |
| `outcome_*_end_date` | Last trading session in the future window |
| `forward_*_session_return_pct` | Return from hypothetical entry open to horizon close |
| `forward_*_session_mfe_pct` | Best intraperiod high relative to entry |
| `forward_*_session_mae_pct` | Worst intraperiod low relative to entry |

`barrier_outcome_10_sessions` reports whether the provisional upward or
downside ATR threshold was reached first. It explicitly reports same-session
ambiguity and incomplete windows.

The entry session counts as session 1 of each 5-, 10- or 20-session outcome
window.

## Chronological validation

| Column | Meaning |
|---|---|
| `research_split` | Training, calibration or untouched holdout |
| `split_eligible` | Whether the future outcome stays inside that period |
| `split_exclusion_reason` | Plain reason the row cannot be used |

No column in the current panel is an approved genuine-momentum classification.
