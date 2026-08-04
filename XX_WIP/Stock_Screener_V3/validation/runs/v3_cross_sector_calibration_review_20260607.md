# V3 Cross-Sector Calibration Review - 2026-06-07

This review combines the 2026-06-05 full Technology baseline with the 2026-06-07 USA sector-folder validation packs.

Included runs:

- `v3_tech_full_pack_20260605`
- `v3_sector_basic_materials_pack_20260607`
- `v3_sector_energy_pack_20260607`
- `v3_sector_industrial_pack_20260607`
- `v3_sector_misc_pack_20260607`
- `v3_sector_telecom_pack_20260607`
- `v3_sector_utilities_pack_20260607`
- `v3_sector_technology_semiconductor_pack_20260607`

Candidate definition: `SELECTED` plus `WATCH`.

## Aggregate D+20 Outcomes

| Sector | Processed | Candidates | Density | D+20 Hit Rate | D+20 Avg Return | D+20 Median Return |
|---|---:|---:|---:|---:|---:|---:|
| Technology Full | 1540 | 1158 | 0.7519 | 53.45% | 8.86% | 1.56% |
| Basic Materials | 361 | 285 | 0.7895 | 32.98% | -3.23% | -4.49% |
| Energy | 402 | 358 | 0.8905 | 60.89% | 4.10% | 2.53% |
| Industrial | 1370 | 1140 | 0.8321 | 48.51% | 0.74% | -0.43% |
| Misc | 194 | 146 | 0.7526 | 41.10% | -1.83% | -3.08% |
| Telecom | 191 | 161 | 0.8429 | 50.31% | 3.64% | 0.01% |
| Utilities | 366 | 331 | 0.9044 | 52.87% | 0.66% | 0.49% |
| Technology Semiconductor | 255 | 189 | 0.7412 | 58.20% | 18.11% | 8.69% |

## D+20 Date Sensitivity

Each cell is hit rate, average return.

| Sector | 2026-02-11 | 2026-03-11 | 2026-04-11 |
|---|---:|---:|---:|
| Technology Full | 35.31%, -1.80% | 35.03%, -1.61% | 82.22%, 25.48% |
| Basic Materials | 19.75%, -8.80% | 18.48%, -8.04% | 54.46%, 4.77% |
| Energy | 72.50%, 7.39% | 63.03%, 2.11% | 47.06%, 2.77% |
| Industrial | 22.60%, -7.00% | 62.61%, 3.15% | 61.00%, 5.94% |
| Misc | 23.26%, -6.29% | 40.82%, -5.89% | 55.56%, 5.41% |
| Telecom | 35.19%, -0.82% | 58.00%, 4.35% | 57.89%, 7.26% |
| Utilities | 56.76%, 0.68% | 76.64%, 3.96% | 26.55%, -2.50% |
| Technology Semiconductor | 18.75%, -3.60% | 60.87%, 3.91% | 88.61%, 43.97% |

## D+20 Stage-Family Outcomes

Each cell is hit rate, average return, candidate count.

| Sector | CROSSOVER | MOMENTUM_SETUP | DIVERGENCE |
|---|---:|---:|---:|
| Technology Full | 55.85%, 8.62%, n=419 | 57.82%, 14.00%, n=339 | 47.25%, 4.74%, n=400 |
| Basic Materials | 21.28%, -7.79%, n=94 | 40.00%, -0.59%, n=100 | 37.36%, -1.40%, n=91 |
| Energy | 48.54%, 1.50%, n=103 | 71.81%, 5.67%, n=149 | 57.55%, 4.42%, n=106 |
| Industrial | 57.81%, 2.76%, n=256 | 39.72%, -1.59%, n=569 | 56.83%, 3.33%, n=315 |
| Misc | 40.54%, -3.33%, n=37 | 47.37%, -1.40%, n=57 | 34.62%, -1.24%, n=52 |
| Telecom | 52.00%, 5.34%, n=50 | 50.00%, 2.48%, n=74 | 48.65%, 3.69%, n=37 |
| Utilities | 56.41%, 2.01%, n=78 | 43.62%, -1.11%, n=149 | 63.46%, 2.17%, n=104 |
| Technology Semiconductor | 35.48%, -1.86%, n=31 | 64.76%, 26.16%, n=105 | 58.49%, 13.85%, n=53 |

## Calibration Read

- Candidate density is still too broad for a final production shortlist. It is acceptable for calibration visibility, but not for final ranking precision.
- Date regime dominates several sectors. Technology Full, Industrial, Misc, and Technology Semiconductor are weak or poor in February but improve sharply by April.
- Basic Materials is the most repeatably weak sector in this pack. Its Crossover candidates are especially poor at D+20.
- Energy is the most stable positive sector across the three dates, with Momentum Setup performing best.
- Utilities is not uniformly defensive. February and March were constructive, while April was weak.
- Momentum Setup is not globally superior. It works well in Energy and Semiconductor but is weak in Industrial and Utilities.
- Divergence is useful in Energy, Industrial, Utilities, and Semiconductor, but weak in Misc and Basic Materials.
- No threshold changes should be promoted yet. The next useful change is analytical: compare regime labels, stage family, and sector/date slices before tuning scoring.

## Next Work

1. Build symbol-level failure reviews for Basic Materials Crossover and Misc Divergence.
2. Compare market, sector, and stock regime labels by date for sectors with sharp date reversals.
3. Add a generated cross-sector calibration report command once the manual review format stabilizes.
4. Keep `PRE_BEAR_CROSSOVER` exit/capital-preservation visibility separate from bullish-entry calibration.
