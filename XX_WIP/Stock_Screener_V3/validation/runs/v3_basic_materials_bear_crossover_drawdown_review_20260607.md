# V3 Basic Materials Bear Crossover Drawdown Review - 2026-06-07

Purpose: evaluate Basic Materials `PRE_BEAR_CROSSOVER` as an exit/capital-preservation signal instead of judging it only by positive-return hit rate.

Run label:

- `v3_basic_materials_path_metrics_20260607`

Input:

- `data/samples/00-NYSE_NASDAQ_Common_Stocks_Sector-BasicMaterials.csv`

Dates and horizons:

- D dates: `2026-02-11`, `2026-03-11`, `2026-04-11`
- Forward horizons: D+1, D+2, D+5, D+10, D+20

New path-aware detail columns added for each horizon:

- `DPlus{N}WorstLowReturnPct`: worst future low inside the horizon, measured from D-date close.
- `DPlus{N}BestHighReturnPct`: best future high inside the horizon, measured from D-date close.

These columns are additive. Existing `DPlus{N}ReturnPct` endpoint-close summaries are unchanged.

## Crossover Path Outcomes

| Slice | Candidates | D+20 Endpoint Avg | D+20 Endpoint Median | D+20 Worst-Low Avg | D+20 Worst-Low Median | D+20 Best-High Avg | D+20 Best-High Median |
|---|---:|---:|---:|---:|---:|---:|---:|
| Basic Materials Crossover | 94 | -7.79% | -8.20% | -19.89% | -19.60% | 10.02% | 6.93% |
| PRE_BEAR_CROSSOVER | 50 | -10.14% | -10.86% | -23.00% | -25.36% | 7.21% | 2.17% |
| PRE_BULL_CROSSOVER | 44 | -5.13% | -5.37% | -16.36% | -14.08% | 13.21% | 11.97% |

## PRE_BEAR_CROSSOVER Date Split

| D Date | Candidates | D+20 Endpoint Avg | D+20 Endpoint Median | D+20 Worst-Low Avg | D+20 Worst-Low Median | D+20 Best-High Avg | D+20 Best-High Median |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-02-11 | 10 | -17.79% | -18.88% | -23.37% | -23.19% | 11.45% | 4.30% |
| 2026-03-11 | 32 | -9.90% | -10.29% | -26.00% | -27.22% | 3.09% | 0.95% |
| 2026-04-11 | 8 | -1.54% | -0.89% | -10.53% | -8.33% | 18.42% | 16.05% |

## PRE_BEAR_CROSSOVER Downside Frequency

| Slice | D+20 Endpoint <= -5% | D+20 Endpoint <= -10% | D+20 Worst-Low <= -5% | D+20 Worst-Low <= -10% |
|---|---:|---:|---:|---:|
| PRE_BEAR_CROSSOVER | 70.00% | 52.00% | 94.00% | 86.00% |
| PRE_BULL_CROSSOVER | 52.27% | 36.36% | 93.18% | 81.82% |

## PRE_BEAR_CROSSOVER Opportunity Types

| Opportunity Type | Candidates | D+20 Endpoint Avg | D+20 Worst-Low Avg | D+20 Worst-Low Median |
|---|---:|---:|---:|---:|
| BEARISH_BELOW_SIGNAL_DETERIORATING | 38 | -9.56% | -24.18% | -25.82% |
| BEARISH_NEAR_TRANSITION | 9 | -12.41% | -18.15% | -13.43% |
| BEARISH_TRANSITION_CROSSOVER | 3 | -10.68% | -22.60% | -29.08% |

## Worst D+20 Forward Lows

| D Date | Symbol | Opportunity Type | Class | Priority | D+20 Endpoint | D+20 Worst Low | D+20 Best High | Regimes |
|---|---|---|---|---|---:|---:|---:|---|
| 2026-03-11 | JELD | BEARISH_BELOW_SIGNAL_DETERIORATING | SELECTED | A | -29.87% | -39.94% | 0.32% | market=MIXED, sector=MIXED, stock=BEARISH |
| 2026-03-11 | CTGO | BEARISH_BELOW_SIGNAL_DETERIORATING | WATCH | B | -18.51% | -38.16% | -1.32% | market=MIXED, sector=MIXED, stock=BEARISH |
| 2026-03-11 | NAMM | BEARISH_BELOW_SIGNAL_DETERIORATING | SELECTED | A | -24.83% | -36.42% | 0.33% | market=BULLISH, sector=MIXED, stock=BEARISH |
| 2026-02-11 | AMWD | BEARISH_NEAR_TRANSITION | SELECTED | A | -34.52% | -35.87% | 2.29% | market=MIXED, sector=BULLISH, stock=BEARISH |
| 2026-03-11 | ODV | BEARISH_TRANSITION_CROSSOVER | WATCH | B | -23.00% | -35.45% | 0.94% | market=MIXED, sector=MIXED, stock=MIXED |

## Interpretation

- `PRE_BEAR_CROSSOVER` should not be evaluated as a bullish-entry candidate.
- The endpoint-return result is weak, but the path result is more important: 86.00% of `PRE_BEAR_CROSSOVER` rows had a D+20 worst-low drawdown of at least 10% from the D-date close.
- March 2026 was the clearest exit-review window: 32 rows, -26.00% average D+20 worst-low, -27.22% median D+20 worst-low.
- `BEARISH_BELOW_SIGNAL_DETERIORATING` is the dominant and most actionable bear-crossover subtype in this slice.
- Best-high values show that some rows still offered brief rebounds, so this signal is better framed as risk review / tighten / exit planning rather than a mechanical immediate-sell rule.

## Calibration Decision

No threshold change is promoted from this review.

Accepted implementation improvement:

- Backtest detail CSVs now include path-aware forward high/low return columns for each configured horizon.

Carry-forward items:

1. Add summary reporting for forward worst-low and best-high metrics by stage family and candidate state.
2. Compare `PRE_BEAR_CROSSOVER` drawdown behavior across Energy, Industrial, Technology, Utilities, and Telecom before changing review priority.
3. In the live scanner UI, visually separate `PRE_BEAR_CROSSOVER` as exit/capital-preservation review from bullish-entry candidates.
