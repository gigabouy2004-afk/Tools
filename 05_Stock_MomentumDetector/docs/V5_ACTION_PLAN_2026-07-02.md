# V5 Action Plan After July 2 Backtest Initiation

Date: 2026-07-02

## Repository State

- Local branch: `main`
- GitHub remote: `origin/main`
- Current synced commit: `c93ea0f Add V5 D+2 status validation audit`
- GitHub and local HEAD are aligned.
- Local generated CSV/XLSX artifacts remain uncommitted.

## Last Confirmed Update

The latest committed update added the D/D+1/D+2 validation audit and documentation:

- `Validate_V5_Status_DD2.py`
- `docs/V5_STATUS_VALIDATION_CONTRACT_2026-07-02.md`
- `docs/V5_STATUS_DD2_VALIDATION_RUN_2026-07-02.md`

The July 2 validation confirmed status/reason strings are traceable, but it also showed calibration risk:

- Some actionable rows failed to continue by D+2.
- Many `Avoid` rows still continued by D+2.
- Historical replay remains daily-only and cannot validate old intraday or extended-hours states.

## Backtest Initiated

Input set:

- Portfolio/watchlist tickers from `PorfolioHolding.txt`
- Tickers: `ASTS BLZE FCEL PLTR OUST BB PANW TOST TENB ZD FROG HLIT NNE PDYN QBTS EXTR MXL QNT`

Command:

```powershell
python .\Backtest_Momentum_Detector_V5.py --tickers ASTS BLZE FCEL PLTR OUST BB PANW TOST TENB ZD FROG HLIT NNE PDYN QBTS EXTR MXL QNT --period 8y --signal-step-days 21
```

Generated root outputs:

- `V5_Backtest_Signal_Audit.csv`
- `V5_Backtest_Summary.csv`

Archived outputs:

- `backtests/20260702_125445_PortfolioWatchlist_V5_Backtest_Signal_Audit.csv`
- `backtests/20260702_125445_PortfolioWatchlist_V5_Backtest_Summary.csv`

Pre-run root-output snapshots:

- `backtests/20260702_125445_pre_run_V5_Backtest_Signal_Audit.csv`
- `backtests/20260702_125445_pre_run_V5_Backtest_Summary.csv`

## Backtest Result Snapshot

- Tickers tested: 18
- Historical signals: 285
- Momentum Candidate signals: 146
- Watchlist Candidate signals: 139
- Average D+1/D+2 confirmation rate by ticker: 23.82%

Status bucket performance:

| Long Term Status | Signals | D+1/D+2 Confirm |
|---|---:|---:|
| Momentum Candidate | 146 | 20.55% |
| Watchlist Candidate | 139 | 28.06% |

## Interpretation

The portfolio/watchlist backtest output contains forward-return columns, but those columns do not validate the immediate D decision.

Key issue:

- The required validation is D status replay and D+2 revalidation.
- The current historical validator uses daily bars only.
- The unresolved blocker is historical intraday reconstruction: 1H candles for the D session, and 4H candles derived from historical intraday data or supplied by a provider.

## Action Plan

1. Preserve the current portfolio/watchlist backtest outputs as the working baseline.
2. Stop treating 21D/63D/126D/252D forward returns as validation for the immediate action call.
3. Add a historical intraday data path for D-day 1H candles.
4. Derive D-day 4H candles from 1H data when the provider does not expose a native 4H interval.
5. Re-run D status using the exact D daily slice plus D-session intraday candles.
6. Revalidate D result against D+1 and D+2 daily bars.
7. Mark rows as `INTRADAY_UNAVAILABLE` instead of assuming `Clean` when historical 1H/4H candles cannot be fetched.
8. Only after D/D+2 validation is reliable, review scoring or stage-gate changes.
