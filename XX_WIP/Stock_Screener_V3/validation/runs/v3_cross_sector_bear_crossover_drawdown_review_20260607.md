# V3 Cross-Sector Bear Crossover Drawdown Review - 2026-06-07

Purpose: compare `PRE_BEAR_CROSSOVER` drawdown behavior across the requested sectors before changing review priority or UI treatment.

Execution order requested and completed:

1. Technology
2. Industrial
3. Energy
4. Telecom
5. Utilities

Run labels:

- `v3_bear_crossover_path_technology_20260607`
- `v3_bear_crossover_path_industrial_20260607`
- `v3_bear_crossover_path_energy_20260607`
- `v3_bear_crossover_path_telecom_20260607`
- `v3_bear_crossover_path_telecom_alias_check_20260607`
- `v3_bear_crossover_path_utilities_20260607`

The Telecom sector file uses `Telecom`. The default regime mapping previously had `COMMUNICATION SERVICES -> XLC` but not `TELECOM -> XLC`. Added aliases:

- `TELECOM -> XLC`
- `TELECOMMUNICATIONS -> XLC`

The corrected Telecom alias-check run had the same processed and candidate counts as the original Telecom run, but sector regime diagnostics were populated.

## Aggregate PRE_BEAR_CROSSOVER D+20 Path Outcomes

| Sector | Candidates | Endpoint Hit Rate | Endpoint Avg | Endpoint Median | Avg Worst Low | Median Worst Low | Worst Low <= -10% | Worst Low <= -20% | Avg Best High | Median Best High |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Technology | 360 | 58.33% | 8.69% | 3.59% | -9.61% | -7.00% | 39.72% | 12.50% | 21.46% | 15.47% |
| Industrial | 203 | 61.58% | 3.80% | 3.52% | -11.29% | -8.89% | 44.83% | 13.79% | 14.11% | 9.82% |
| Energy | 69 | 46.38% | 1.14% | -0.64% | -9.86% | -8.63% | 39.13% | 8.70% | 17.66% | 10.44% |
| Telecom | 40 | 57.50% | 8.29% | 1.73% | -8.32% | -6.29% | 30.00% | 10.00% | 17.89% | 7.83% |
| Utilities | 53 | 60.38% | 1.13% | 1.61% | -6.21% | -5.26% | 16.98% | 1.89% | 6.30% | 5.92% |

## Date Split

| Sector | D Date | Candidates | Endpoint Avg | Avg Worst Low | Median Worst Low | Worst Low <= -10% | Avg Best High |
|---|---|---:|---:|---:|---:|---:|---:|
| Technology | 2026-02-11 | 127 | -0.83% | -13.23% | -11.72% | 59.06% | 14.76% |
| Technology | 2026-03-11 | 83 | -4.44% | -15.77% | -14.60% | 66.27% | 8.31% |
| Technology | 2026-04-11 | 150 | 24.01% | -3.13% | -1.19% | 8.67% | 34.42% |
| Industrial | 2026-02-11 | 47 | -1.49% | -12.79% | -11.18% | 59.57% | 16.47% |
| Industrial | 2026-03-11 | 115 | 4.61% | -11.68% | -8.89% | 44.35% | 10.60% |
| Industrial | 2026-04-11 | 41 | 7.59% | -8.48% | -5.33% | 29.27% | 21.25% |
| Energy | 2026-02-11 | 11 | 0.46% | -13.27% | -11.70% | 54.55% | 14.56% |
| Energy | 2026-03-11 | 15 | 7.78% | -8.69% | -8.75% | 40.00% | 31.08% |
| Energy | 2026-04-11 | 43 | -1.00% | -9.40% | -8.44% | 34.88% | 13.77% |
| Telecom | 2026-02-11 | 9 | 14.54% | -9.70% | -6.28% | 22.22% | 27.61% |
| Telecom | 2026-03-11 | 16 | 4.26% | -8.77% | -6.71% | 31.25% | 10.27% |
| Telecom | 2026-04-11 | 15 | 8.84% | -7.01% | -3.84% | 33.33% | 20.18% |
| Utilities | 2026-02-11 | 9 | -0.85% | -5.16% | -2.93% | 22.22% | 7.74% |
| Utilities | 2026-03-11 | 36 | 2.83% | -6.23% | -4.87% | 16.67% | 6.39% |
| Utilities | 2026-04-11 | 8 | -4.29% | -7.34% | -7.54% | 12.50% | 4.25% |

## Opportunity Type Split

| Sector | Opportunity Type | Candidates | Endpoint Avg | Avg Worst Low | Median Worst Low | Worst Low <= -10% |
|---|---|---:|---:|---:|---:|---:|
| Technology | BEARISH_BELOW_SIGNAL_DETERIORATING | 210 | 7.42% | -9.61% | -7.54% | 39.52% |
| Technology | BEARISH_NEAR_TRANSITION | 105 | 8.64% | -10.73% | -8.21% | 42.86% |
| Technology | BEARISH_TRANSITION_CROSSOVER | 45 | 14.68% | -6.99% | -3.98% | 33.33% |
| Industrial | BEARISH_BELOW_SIGNAL_DETERIORATING | 159 | 3.01% | -11.54% | -9.64% | 48.43% |
| Industrial | BEARISH_NEAR_TRANSITION | 32 | 7.60% | -12.36% | -7.67% | 37.50% |
| Industrial | BEARISH_TRANSITION_CROSSOVER | 12 | 4.10% | -5.18% | -4.37% | 16.67% |
| Energy | BEARISH_BELOW_SIGNAL_DETERIORATING | 53 | -0.96% | -10.62% | -8.99% | 43.40% |
| Energy | BEARISH_TRANSITION_CROSSOVER | 9 | 9.35% | -3.61% | -3.89% | 0.00% |
| Energy | BEARISH_NEAR_TRANSITION | 7 | 6.50% | -12.17% | -10.63% | 57.14% |
| Telecom | BEARISH_BELOW_SIGNAL_DETERIORATING | 25 | 9.18% | -7.61% | -6.28% | 24.00% |
| Telecom | BEARISH_NEAR_TRANSITION | 12 | 8.04% | -9.75% | -8.32% | 41.67% |
| Telecom | BEARISH_TRANSITION_CROSSOVER | 3 | 1.90% | -8.52% | -5.61% | 33.33% |
| Utilities | BEARISH_BELOW_SIGNAL_DETERIORATING | 43 | 1.12% | -6.43% | -5.26% | 18.60% |
| Utilities | BEARISH_TRANSITION_CROSSOVER | 8 | 1.27% | -5.61% | -4.96% | 12.50% |
| Utilities | BEARISH_NEAR_TRANSITION | 2 | 0.80% | -4.04% | -4.04% | 0.00% |

## Worst Rows By Sector

| Sector | D Date | Symbol | Opportunity Type | Class | Priority | D+20 Endpoint | D+20 Worst Low | D+20 Best High | Regimes | Risk Tags |
|---|---|---|---|---|---|---:|---:|---:|---|---|
| Technology | 2026-03-11 | NXTT | BEARISH_NEAR_TRANSITION | WATCH | NEEDS_MANUAL_REVIEW | -39.26% | -83.30% | 4.07% | market=BULLISH, sector=BULLISH, stock=MIXED | LOW_LIQUIDITY |
| Technology | 2026-03-11 | LAES | BEARISH_NEAR_TRANSITION | SELECTED | A | -47.49% | -49.25% | 1.76% | market=BULLISH, sector=BULLISH, stock=BEARISH | none |
| Technology | 2026-02-11 | SMWB | BEARISH_BELOW_SIGNAL_DETERIORATING | SELECTED | A | -37.56% | -46.89% | 2.99% | market=BULLISH, sector=MIXED, stock=BEARISH | none |
| Industrial | 2026-03-11 | AIIO | BEARISH_NEAR_TRANSITION | WATCH | B | -70.68% | -70.68% | 2.26% | market=BULLISH, sector=MIXED, stock=MIXED | none |
| Industrial | 2026-04-11 | ATLN | BEARISH_BELOW_SIGNAL_DETERIORATING | WATCH | NEEDS_MANUAL_REVIEW | -46.04% | -57.55% | 6.83% | market=BULLISH, sector=BULLISH, stock=BEARISH | LOW_LIQUIDITY |
| Industrial | 2026-02-11 | FFAI | BEARISH_BELOW_SIGNAL_DETERIORATING | SELECTED | A | -46.77% | -48.46% | 1.69% | market=MIXED, sector=BULLISH, stock=BEARISH | none |
| Energy | 2026-04-11 | ANNA | BEARISH_BELOW_SIGNAL_DETERIORATING | WATCH | B | -35.47% | -40.68% | 19.24% | market=BULLISH, sector=MIXED, stock=MIXED | none |
| Energy | 2026-02-11 | EAF | BEARISH_BELOW_SIGNAL_DETERIORATING | SELECTED | A | -31.00% | -35.09% | 2.24% | market=BULLISH, sector=BULLISH, stock=BEARISH | none |
| Energy | 2026-02-11 | TTI | BEARISH_BELOW_SIGNAL_DETERIORATING | WATCH | B | -26.05% | -29.62% | 2.50% | market=BULLISH, sector=BULLISH, stock=MIXED | none |
| Telecom | 2026-04-11 | LBRDK | BEARISH_NEAR_TRANSITION | WATCH | B | -29.40% | -29.43% | 15.83% | market=BULLISH, sector=BULLISH, stock=MIXED | none |
| Telecom | 2026-02-11 | ZD | BEARISH_BELOW_SIGNAL_DETERIORATING | SELECTED | A | 25.46% | -28.64% | 60.68% | market=MIXED, sector=MIXED, stock=BEARISH | none |
| Telecom | 2026-02-11 | AIOT | BEARISH_BELOW_SIGNAL_DETERIORATING | SELECTED | A | -23.57% | -24.07% | 1.49% | market=MIXED, sector=MIXED, stock=BEARISH | none |
| Utilities | 2026-03-11 | MNTK | BEARISH_BELOW_SIGNAL_DETERIORATING | SELECTED | A | -13.55% | -21.61% | 8.42% | market=BULLISH, sector=MIXED, stock=BEARISH | none |
| Utilities | 2026-03-11 | CLFD | BEARISH_BELOW_SIGNAL_DETERIORATING | WATCH | NEEDS_MANUAL_REVIEW | -8.23% | -19.21% | 3.06% | market=BULLISH, sector=MIXED, stock=BEARISH | LOW_LIQUIDITY |
| Utilities | 2026-03-11 | CWST | BEARISH_BELOW_SIGNAL_DETERIORATING | SELECTED | A | -1.65% | -16.07% | 5.33% | market=BULLISH, sector=MIXED, stock=BEARISH | none |

## Calibration Read

- Technology and Industrial have the strongest broad evidence that `PRE_BEAR_CROSSOVER` can mark meaningful forward drawdown risk.
- Technology is highly date-sensitive: February and March had substantial worst-low risk, while April had strong endpoint gains and much milder worst-low behavior.
- Industrial is more consistently drawdown-heavy than Technology on aggregate, with the highest D+20 worst-low <= -10% frequency among the five sectors.
- Energy is mixed. The `BEARISH_BELOW_SIGNAL_DETERIORATING` subtype remains useful, but `BEARISH_TRANSITION_CROSSOVER` is too small and mild in this sample.
- Telecom is moderate after adding the sector alias. `BEARISH_NEAR_TRANSITION` had more drawdown than `BEARISH_BELOW_SIGNAL_DETERIORATING`, but sample size is small.
- Utilities is materially milder than the other sectors. It should not receive the same urgency treatment as Technology, Industrial, or Basic Materials from this validation alone.
- Best-high metrics confirm that many bear-crossover rows can still rebound. This supports review/tighten/exit-planning language rather than a mechanical immediate-sell rule.

## Calibration Decision

No review-priority threshold change is promoted from this pass.

Accepted implementation/config update:

- Added Telecom sector aliases to the default benchmark configuration.

Carry-forward items:

1. In live UI/reporting, visually separate `PRE_BEAR_CROSSOVER` as exit/capital-preservation review.
2. Consider a future sector-aware urgency layer:
   - stronger for Basic Materials, Technology, and Industrial;
   - moderate for Energy and Telecom;
   - lighter for Utilities.
3. Add generated calibration report commands for these manual reviews once the format stabilizes.
