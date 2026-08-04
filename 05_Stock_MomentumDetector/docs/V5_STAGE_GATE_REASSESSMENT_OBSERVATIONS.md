# V5 Stage Gate Reassessment Observations

Purpose: capture observations that might require future code changes. No code change should be made from this document unless explicitly authorized/requested.

## Observation 1 - TENB Early Momentum Blocked By Weekly Stage Gate

Date captured: 2026-06-29

Ticker reviewed: `TENB`

Observed live behavior:

- `Return_5D_Pct`: about `+24.97%`
- `Return_10D_Pct`: about `+22.83%`
- `Daily_Change_Pct`: about `+8.93%`
- `Return_63D_Pct`: about `+99.02%`
- `Entry_Timing_Status`: `Clean`
- `Last_3H_Return_Pct`: positive
- `Bearish_1H_Candles_Last3`: `0`
- `Last_1H_Bearish`: `False`

Current engine output:

- `Action_Status`: `Avoid`
- `Long_Term_Status`: `Avoid`
- `Classification_Reason`: `weekly Transition`
- `Score`: `66`
- `Weekly_Stage`: `Transition`

Why the engine avoided it:

- `Weekly_Close` is above `Weekly_SMA_30`.
- But `Weekly_SMA_30_Slope_Pct_10W` is still negative, around `-4.76%`.
- Current stage gate requires confirmed `Stage 2`; `Transition` becomes `Avoid`.

Assessment:

The calculation appears correct under current rules, but the translation may be incomplete. TENB is not a confirmed Stage 2 momentum stock, but it is showing strong short-term price momentum and clean timing.

Potential future enhancement:

- Consider adding an explicit bucket such as `Emerging Momentum Watch` or `Early Momentum / Transition Breakout`.
- This bucket would not replace confirmed `Actionable Momentum Candidate`.
- It would prevent strong early transition names from being buried as plain `Avoid`.

Important constraint:

- No code change should be made for this observation without explicit authorization.
- Any future change should be validated with backtest/comparison against the existing Stage 2 gate.
