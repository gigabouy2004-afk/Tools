# V3 USA Folder Non-Technology Watch Probe Review

Run label: `v3_usa_folder_nontech_watch_probe_20260605`

Source folder: `D:\Tools\StockCodeMaster\USA`

Derived universe: `data/samples/us_usa_folder_nontech_sector_universe_20260605.csv`

Purpose: use the USA sector-code folder as the source for sector-based validation, per operating preference.

## Source Files Used

- `00-NYSE_NASDAQ_Common_Stocks_Sector-BasicMaterials.csv`
- `00-NYSE_NASDAQ_Common_Stocks_Sector-Energy.csv`
- `00-NYSE_NASDAQ_Common_Stocks_Sector-Industrial.csv`
- `00-NYSE_NASDAQ_Common_Stocks_Sector-Misc.csv`
- `00-NYSE_NASDAQ_Common_Stocks_Sector-Telecom.csv`
- `00-NYSE_NASDAQ_Common_Stocks_Sector-Utilities.csv`

Technology and Technology-Semiconductor files were excluded for this non-Technology watch-risk comparison.

Derived universe size: 996 unique symbols.

## Run Setup

- Sample size: 200.
- Random seed: 20260605.
- D dates: `2026-02-11`, `2026-03-11`.
- Stage families: `CROSSOVER,MOMENTUM_SETUP,DIVERGENCE`.
- Forward horizons: D+1, D+2, D+5, D+10, D+20.

Generated artifacts:

- `validation/runs/v3_usa_folder_nontech_watch_probe_20260605_20260211_summary.md`
- `validation/runs/v3_usa_folder_nontech_watch_probe_20260605_20260311_summary.md`
- `validation/runs/v3_usa_folder_nontech_watch_probe_20260605_multi_date_summary.md`

## Run Result

| D date | Attempted | Processed | Skipped | Candidates | Candidate density |
|---|---:|---:|---:|---:|---:|
| 2026-02-11 | 200 | 191 | 9 | 163 | 0.8534 |
| 2026-03-11 | 200 | 193 | 7 | 152 | 0.7876 |

## WATCH / BELOW_EMA200 D+20

| D date | Segment | Candidates | Hit Rate | Average Return |
|---|---|---:|---:|---:|
| 2026-02-11 | SELECTED + NO_RISK_TAG | 119 | 44.54% | -1.88% |
| 2026-02-11 | WATCH + LOW_LIQUIDITY | 19 | 21.05% | -4.55% |
| 2026-02-11 | WATCH + NO_RISK_TAG | 14 | 35.71% | -5.08% |
| 2026-02-11 | WATCH + BELOW_EMA200 | 11 | 27.27% | -0.12% |
| 2026-03-11 | SELECTED + NO_RISK_TAG | 84 | 54.76% | 0.68% |
| 2026-03-11 | WATCH + NO_RISK_TAG | 35 | 51.43% | 2.59% |
| 2026-03-11 | WATCH + BELOW_EMA200 | 19 | 57.89% | 5.88% |
| 2026-03-11 | WATCH + LOW_LIQUIDITY | 19 | 73.68% | 2.85% |

## Read

The USA-folder sector sample does not confirm a generic March `WATCH + BELOW_EMA200` weakness. February was weak-to-flat for this segment, but March was positive.

This differs from the broader master-library non-Technology sample. The likely reason is coverage: the USA-folder non-Technology set is concentrated in Industrials, Energy, Utilities, Basic Materials, Telecom, and Miscellaneous. It does not include the full Finance, Health Care, Consumer Discretionary, Consumer Staples, and Real Estate coverage present in the combined master library.

Therefore:

- Use `D:\Tools\StockCodeMaster\USA` for sector-folder validation and sector-specific code lists.
- Use `D:\Tools\StockCodeMaster\Script\NYSE_NASDAQ_Master_Library.csv` when a broad all-sector NYSE/NASDAQ common-stock universe is required.
- Do not promote a broad `WATCH + BELOW_EMA200` downgrade rule from one source alone.

## Next Step

Run sector-by-sector packs from the USA folder where files exist, then compare them with broad master-library packs before changing review priority rules.

