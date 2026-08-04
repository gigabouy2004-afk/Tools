# V5 Final Handover And Sync

Date: 2026-07-02

Current output contract reference:

- `docs/V5_CURRENT_OUTPUT_CONTRACT_2026-07-04.md`

Future sessions must treat `Final_Decision` as the only primary user-facing output. `Score`, `Action_Status`, ranks, trend scores, timing statuses, and other technical fields are internal/audit details, not a formula the end user must combine.

## Current Git State

Latest code commit before this handover:

- `5c21007 Improve NSE ticker handling and no-data messages`

Repository:

- `https://github.com/gigabouy2004-afk/Stock_MomentumDetector.git`

## Current Engine

Primary script:

- `Momentum_Detector_V5.py`

Primary user-facing output column:

- `Final_Decision`

Allowed values:

- `MOMENTUM_ACTIVE`
- `MOMENTUM_PRESENT_WAIT_CONFIRMATION`
- `REJECT`

The CLI prints every processed ticker with:

- ticker
- final decision
- score
- close
- plain-language reason

Default output files are now unique per run.

## Input Handling

Default ticker input:

- `D:/Tools/StockCodeMaster/02_Stock/01-07-US_Common_Stocks_Master_Library-Filtered_Technology.csv`

Supported CLI examples:

```powershell
python .\Momentum_Detector_V5.py AAPL MSFT
python .\Momentum_Detector_V5.py --tickers AAPL,MSFT
python .\Momentum_Detector_V5.py --market nse RELIANCE TCS
python .\Momentum_Detector_V5.py --ticker-csv D:\path\to\tickers.csv
```

NSE handling:

- `--market nse` appends `.NS` to plain symbols.
- Already suffixed symbols like `ZENTEC.NS` are accepted as-is.
- Bad symbols now show `Score N/A`, `Close N/A`, and `Reason: no market data - check symbol`.

## Validation Position

Historical D/D+1/D+2 validation uses:

- `Validate_V5_Status_DD2.py`

Latest consolidated validation file:

- `backtests/V5_FinalDecision_Validation_Consolidated_20260702.csv`

Known validation result from the existing sample:

- `KLIC` was the only `MOMENTUM_ACTIVE` row.
- It passed D+1 open confirmation and D+2 continuation.

## Important Artifacts

Key docs:

- `docs/V5_CURRENT_OUTPUT_CONTRACT_2026-07-04.md`
- `docs/V5_HANDOVER_SINGLE_COLUMN_REQUIREMENT_2026-07-02.md`
- `docs/V5_FINAL_DECISION_IMPLEMENTATION_2026-07-02.md`
- `docs/V5_INDICATOR_REVALIDATION_DIAGNOSIS_2026-07-02.md`
- `docs/V5_RANDOM20_MAY06_MAY19_MULTIROUND_VALIDATION_2026-07-02.md`

Key validation/backtest files:

- `backtests/V5_FinalDecision_D1_D2_PrimarySecondary_Assessment_20260702.csv`
- `backtests/V5_FinalDecision_Validation_Consolidated_20260702.csv`
- `backtests/V5_Backtest_Iteration_Log.csv`

## Sync Note

This handover is being committed with remaining local runtime/output artifacts so GitHub and local workspace have the same audit trail at the end of the session.
