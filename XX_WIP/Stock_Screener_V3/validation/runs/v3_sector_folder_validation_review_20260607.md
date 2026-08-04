# V3 Sector Folder Validation Review - 2026-06-07

Input source: `D:\Tools\StockCodeMaster\USA`

Workspace samples copied into `data/samples`:

- `00-NYSE_NASDAQ_Common_Stocks_Sector-BasicMaterials.csv`
- `00-NYSE_NASDAQ_Common_Stocks_Sector-Energy.csv`
- `00-NYSE_NASDAQ_Common_Stocks_Sector-Industrial.csv`
- `00-NYSE_NASDAQ_Common_Stocks_Sector-Misc.csv`
- `00-NYSE_NASDAQ_Common_Stocks_Sector-Telecom.csv`
- `00-NYSE_NASDAQ_Common_Stocks_Sector-Utilities.csv`
- `00-NYSE_NASDAQ_Common_Stocks_Sector-Technology-Semiconductor.csv`

Run parameters:

- D dates: `2026-02-11`, `2026-03-11`, `2026-04-11`
- Stage families: `CROSSOVER,MOMENTUM_SETUP,DIVERGENCE`
- Forward horizons: D+1, D+2, D+5, D+10, D+20
- Sample mode: full sector files

Aggregate summaries:

- `validation/runs/v3_sector_basic_materials_pack_20260607_multi_date_summary.md`
- `validation/runs/v3_sector_energy_pack_20260607_multi_date_summary.md`
- `validation/runs/v3_sector_industrial_pack_20260607_multi_date_summary.md`
- `validation/runs/v3_sector_misc_pack_20260607_multi_date_summary.md`
- `validation/runs/v3_sector_telecom_pack_20260607_multi_date_summary.md`
- `validation/runs/v3_sector_utilities_pack_20260607_multi_date_summary.md`
- `validation/runs/v3_sector_technology_semiconductor_pack_20260607_multi_date_summary.md`

## Aggregate Candidate Outcomes

Candidates here mean `SELECTED` plus `WATCH`, matching the pack-level `Candidates found` count.

| Sector | Processed | Candidates | Density | D+20 Hit Rate | D+20 Avg Return | D+20 Median Return |
|---|---:|---:|---:|---:|---:|---:|
| Basic Materials | 361 | 285 | 0.7895 | 32.98% | -3.23% | -4.49% |
| Energy | 402 | 358 | 0.8905 | 60.89% | 4.10% | 2.53% |
| Industrial | 1370 | 1140 | 0.8321 | 48.51% | 0.74% | -0.43% |
| Misc | 194 | 146 | 0.7526 | 41.10% | -1.83% | -3.08% |
| Telecom | 191 | 161 | 0.8429 | 50.31% | 3.64% | 0.01% |
| Utilities | 366 | 331 | 0.9044 | 52.87% | 0.66% | 0.49% |
| Technology Semiconductor | 255 | 189 | 0.7412 | 58.20% | 18.11% | 8.69% |

## D+20 Family Slices

| Sector | CROSSOVER | MOMENTUM_SETUP | DIVERGENCE |
|---|---|---|---|
| Basic Materials | 21.28%, -7.79% avg | 40.00%, -0.59% avg | 37.36%, -1.40% avg |
| Energy | 48.54%, 1.50% avg | 71.81%, 5.67% avg | 57.55%, 4.42% avg |
| Industrial | 57.81%, 2.76% avg | 39.72%, -1.59% avg | 56.83%, 3.33% avg |
| Misc | 40.54%, -3.33% avg | 47.37%, -1.40% avg | 34.62%, -1.24% avg |
| Telecom | 52.00%, 5.34% avg | 50.00%, 2.48% avg | 48.65%, 3.69% avg |
| Utilities | 56.41%, 2.01% avg | 43.62%, -1.11% avg | 63.46%, 2.17% avg |
| Technology Semiconductor | 35.48%, -1.86% avg | 64.76%, 26.16% avg | 58.49%, 13.85% avg |

## Review Notes

- Candidate density remains high across all sector files, from 0.7412 to 0.9044. This reinforces that current classification is still broad and should not be treated as a narrow actionable signal list.
- Basic Materials is the weakest sector in this pack, with negative average and median returns at every aggregate horizon and especially weak Crossover D+20 behavior.
- Misc is also weak at D+20, though less consistently negative than Basic Materials.
- Energy has strong D+10 and D+20 outcomes, led by Momentum Setup and Divergence.
- Technology Semiconductor is strongly positive at D+10 and D+20, but the pack is heavily lifted by the April 2026 date.
- Industrial is date-sensitive: February is weak while March and April improve sharply at D+20.
- Utilities has acceptable aggregate D+20 numbers, but April deteriorates sharply versus February and March.
- `WATCH + BELOW_EMA200` did not reproduce as a generic weak filter in these sector-folder runs. It was mixed by sector and often positive at D+20.
- Do not change scoring thresholds from this pack alone. The evidence supports sector/date calibration review, not an immediate rule change.

## Next Calibration Work

1. Add a cross-sector aggregate report that combines these sector-folder packs with the existing Technology full-universe baseline.
2. Compare family outcomes by date to identify date-regime sensitivity before tuning stage-family priority.
3. Investigate Basic Materials Crossover weakness and Misc Divergence weakness with symbol-level examples.
4. Keep bearish `CROSSOVER` exit/capital-preservation review intact while calibration continues.
