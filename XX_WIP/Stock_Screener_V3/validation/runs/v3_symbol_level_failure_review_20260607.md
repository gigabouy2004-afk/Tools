# V3 Symbol-Level Failure Review - 2026-06-07

This review follows the cross-sector calibration finding that Basic Materials Crossover and Misc Divergence were weak D+20 slices.

Candidate definition: `SELECTED` plus `WATCH`.

Reviewed detail sets:

- `v3_sector_basic_materials_pack_20260607`
- `v3_sector_misc_pack_20260607`
- `v3_sector_basic_materials_regime_alias_check_20260607`

## Basic Materials Crossover

Baseline D+20 outcome:

| Slice | Candidates | Hit Rate | Average Return | Median Return |
|---|---:|---:|---:|---:|
| Basic Materials Crossover | 94 | 21.28% | -7.79% | -8.20% |
| PRE_BEAR_CROSSOVER | 50 | 18.00% | -10.14% | -10.86% |
| PRE_BULL_CROSSOVER | 44 | 25.00% | -5.13% | -5.37% |

Date split:

| D Date | Candidates | Hit Rate | Average Return | Median Return |
|---|---:|---:|---:|---:|
| 2026-02-11 | 40 | 20.00% | -8.32% | -6.75% |
| 2026-03-11 | 42 | 16.67% | -9.44% | -11.92% |
| 2026-04-11 | 12 | 41.67% | -0.29% | -0.72% |

Worst D+20 rows:

| D Date | Symbol | Candidate State | Class | Priority | D+20 Return | Regimes | Reason Codes |
|---|---|---|---|---|---:|---|---|
| 2026-02-11 | NAK | PRE_BULL_CROSSOVER | SELECTED | A | -39.55% | market=BULLISH, sector=UNKNOWN, stock=BULLISH | DAILY_MACD_NEAR_BULL_TRANSITION, CONSTRUCTIVE_PRICE_STRUCTURE, ACCEPTANCE_SUPPORT |
| 2026-02-11 | AMWD | PRE_BEAR_CROSSOVER | SELECTED | A | -34.52% | market=MIXED, sector=UNKNOWN, stock=BEARISH | DAILY_MACD_NEAR_BEAR_TRANSITION, BEARISH_PRICE_STRUCTURE, SELLER_PARTICIPATION_SUPPORT |
| 2026-03-11 | JELD | PRE_BEAR_CROSSOVER | SELECTED | A | -29.87% | market=MIXED, sector=UNKNOWN, stock=BEARISH | DAILY_MACD_BELOW_SIGNAL_DETERIORATING, BEARISH_PRICE_STRUCTURE |
| 2026-02-11 | CLF | PRE_BEAR_CROSSOVER | SELECTED | A | -28.53% | market=BULLISH, sector=UNKNOWN, stock=BEARISH | DAILY_MACD_BELOW_SIGNAL_DETERIORATING, SELLER_PARTICIPATION_SUPPORT, BEARISH_ACCEPTANCE_SUPPORT |
| 2026-04-11 | NAMM | PRE_BEAR_CROSSOVER | WATCH | B | -27.06% | market=BULLISH, sector=UNKNOWN, stock=MIXED | DAILY_MACD_NEAR_BEAR_TRANSITION, BEARISH_PRICE_STRUCTURE |

Repeated weak symbols:

| Symbol | Rows | Average D+20 | Worst D+20 | Best D+20 | Dates |
|---|---:|---:|---:|---:|---|
| NAMM | 3 | -14.94% | -27.06% | 7.09% | 2026-02-11, 2026-03-11, 2026-04-11 |
| AUST | 2 | -12.51% | -23.59% | -1.44% | 2026-02-11, 2026-04-11 |
| GLDG | 2 | -11.33% | -18.18% | -4.49% | 2026-02-11, 2026-03-11 |
| MTA | 2 | -8.55% | -20.50% | 3.40% | 2026-02-11, 2026-03-11 |
| GROY | 3 | -7.93% | -13.54% | -1.10% | 2026-02-11, 2026-03-11, 2026-04-11 |

### Regime Alias Finding

The Basic Materials sector file uses `Basic Materials`, while the default regime config only mapped `MATERIALS` to `XLB`. That made all Basic Materials rows emit `SectorRegime=UNKNOWN`.

Fix added:

- `BASIC MATERIALS -> XLB`

Regression test added:

- `test_default_config_maps_basic_materials_alias`

Alias-check rerun:

- run label: `v3_sector_basic_materials_regime_alias_check_20260607`
- processed rows: 361
- candidates: 285
- candidate density: 0.7895
- sector regimes after alias: 241 `BULLISH`, 120 `MIXED`

Outcome impact:

| Slice | Before Alias | After Alias |
|---|---|---|
| All Basic Materials candidates | 32.98% hit, -3.23% avg, -4.49% median | 32.98% hit, -3.23% avg, -4.49% median |
| Basic Materials Crossover | 21.28% hit, -7.79% avg, -8.20% median | 21.28% hit, -7.79% avg, -8.20% median |

Interpretation:

- Missing sector context was a real diagnostics/config issue.
- The Basic Materials Crossover weakness did not disappear after sector context was restored.
- Weakness is concentrated in February and March and especially in `PRE_BEAR_CROSSOVER`, which is expected to function as exit/capital-preservation visibility rather than a bullish-entry shortlist.

## Misc Divergence

Baseline D+20 outcome:

| Slice | Candidates | Hit Rate | Average Return | Median Return |
|---|---:|---:|---:|---:|
| Misc Divergence | 52 | 34.62% | -1.24% | -4.05% |
| Hidden Divergence | 30 | 30.00% | -1.74% | -5.32% |
| Regular Divergence | 22 | 40.91% | -0.55% | -0.67% |
| Bullish Divergence Direction | 24 | 33.33% | -2.63% | -5.68% |
| Bearish Divergence Direction | 28 | 35.71% | -0.04% | -3.55% |

Date split:

| D Date | Candidates | Hit Rate | Average Return | Median Return |
|---|---:|---:|---:|---:|
| 2026-02-11 | 8 | 0.00% | -8.46% | -6.02% |
| 2026-03-11 | 27 | 40.74% | -4.64% | -0.86% |
| 2026-04-11 | 17 | 41.18% | 7.56% | -3.79% |

Worst D+20 rows:

| D Date | Symbol | Candidate State | Class | Priority | D+20 Return | Risk Tags | Regimes |
|---|---|---|---|---|---:|---|---|
| 2026-03-11 | MVST | BULLISH_DIVERGENCE | WATCH | NEEDS_MANUAL_REVIEW | -30.22% | BELOW_EMA200 | market=BULLISH, sector=UNKNOWN, stock=MIXED |
| 2026-03-11 | PAR | BULLISH_DIVERGENCE | WATCH | NEEDS_MANUAL_REVIEW | -28.47% | BELOW_EMA200 | market=MIXED, sector=UNKNOWN, stock=BEARISH |
| 2026-03-11 | BTQ | HIDDEN_BULLISH_DIVERGENCE | WATCH | NEEDS_MANUAL_REVIEW | -25.94% | BELOW_EMA200 | market=BULLISH, sector=UNKNOWN, stock=MIXED |
| 2026-03-11 | SES | HIDDEN_BEARISH_DIVERGENCE | SELECTED | A | -25.58% | none | market=MIXED, sector=UNKNOWN, stock=BEARISH |
| 2026-03-11 | SUPX | HIDDEN_BEARISH_DIVERGENCE | SELECTED | A | -24.95% | none | market=BULLISH, sector=UNKNOWN, stock=BEARISH |

Repeated weak symbols:

| Symbol | Rows | Average D+20 | Worst D+20 | Best D+20 | Dates |
|---|---:|---:|---:|---:|---|
| SES | 2 | -16.34% | -25.58% | -7.10% | 2026-03-11, 2026-04-11 |
| PAR | 2 | -3.32% | -28.47% | 21.83% | 2026-03-11, 2026-04-11 |
| SLDP | 2 | -2.48% | -9.20% | 4.24% | 2026-03-11, 2026-04-11 |
| OTF | 2 | -2.33% | -3.79% | -0.86% | 2026-03-11, 2026-04-11 |
| AAUC | 2 | -0.43% | -0.48% | -0.38% | 2026-02-11, 2026-03-11 |

Interpretation:

- Misc Divergence weakness is not a single route issue. Hidden and bullish variants are weaker, but regular and bearish variants are also not strong enough to justify threshold changes.
- February Misc Divergence was uniformly poor, but sample size was only 8.
- Several worst rows are already tagged `BELOW_EMA200` and downgraded to `NEEDS_MANUAL_REVIEW`, so the current output is exposing risk rather than hiding it.
- `SectorRegime=UNKNOWN` is expected for `Misc` until a defensible benchmark mapping exists. Do not map Misc to a sector ETF casually.

## Calibration Decision

No scoring threshold changes should be made from this review alone.

Accepted implementation fix:

- Add `BASIC MATERIALS -> XLB` to default regime benchmark mapping.

Carry-forward analysis items:

1. Keep `PRE_BEAR_CROSSOVER` visible for exit/capital-preservation review, but separate it more clearly from bullish-entry interpretation in UI/report review.
2. Compare Basic Materials `PRE_BEAR_CROSSOVER` against forward drawdown avoidance, not only positive-return hit rate.
3. For Misc Divergence, require more dates before changing Divergence scoring.
4. Add a generated symbol-level failure review command once the manual review format stabilizes.
