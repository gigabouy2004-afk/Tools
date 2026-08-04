# V3 Divergence Rule Comprehensive Backtest

Date written: 2026-06-11

## Scope

- Rule under test: raw/unconfirmed bullish Divergence below EMA200 is emitted as `REJECTED` with `RAW_BULLISH_DIVERGENCE_BELOW_EMA200`.
- Fresh post-rule backtests: 15 runs across Technology, Industrial, Energy, Telecom, and Utilities.
- Dates: 2026-02-11, 2026-03-11, 2026-04-11.
- Horizons: D+1, D+2, D+5, D+10, D+20.

## Candidate Impact

| Dataset | Selected/Watch Candidates | D+20 Hit Rate | D+20 Avg | D+20 Median | D+20 Median Worst Low |
|---|---:|---:|---:|---:|---:|
| Before rule | 3144 | 52.29% | 4.26% | 0.72% | -7.88% |
| After rule | 3056 | 52.42% | 4.31% | 0.78% | -7.89% |

- Candidate count change: -88.
- Rows directly rejected by the new Divergence rule: 33.
- New-rule rejected rows D+20 profile: 33 rows, 54.55% hit rate, 0.25% median endpoint, -7.55% median worst low.

## Stage Family Outcomes After Rule

| Stage Family | Candidates | D+20 Hit Rate | D+20 Avg | D+20 Median | D+20 Median Worst Low |
|---|---:|---:|---:|---:|---:|
| CROSSOVER | 789 | 56.91% | 6.04% | 2.56% | -7.61% |
| DIVERGENCE | 987 | 52.89% | 3.75% | 0.90% | -8.43% |
| MOMENTUM_SETUP | 1280 | 49.30% | 3.67% | -0.39% | -7.36% |

## Divergence Candidate-State Comparison

| Candidate State | Before Count | Before Median | After Count | After Median | Count Change |
|---|---:|---:|---:|---:|---:|
| BULLISH_DIVERGENCE | 211 | -1.45% | 205 | -2.38% | -6 |
| HIDDEN_BULLISH_DIVERGENCE | 257 | 1.23% | 264 | 1.42% | 7 |
| BEARISH_DIVERGENCE | 210 | 2.69% | 228 | 2.28% | 18 |
| HIDDEN_BEARISH_DIVERGENCE | 284 | 0.95% | 290 | 1.01% | 6 |

## New Rule Rejections By Sector/Date

| Sector | D Date | Rows | D+20 Hit Rate | D+20 Median | D+20 Median Worst Low |
|---|---|---:|---:|---:|---:|
| Energy | 2026-03-11 | 1 | 100.00% | 2.23% | -5.85% |
| Energy | 2026-04-11 | 1 | 100.00% | 7.39% | -2.61% |
| Industrial | 2026-03-11 | 9 | 55.56% | 0.23% | -8.89% |
| Industrial | 2026-04-11 | 2 | 50.00% | 4.07% | -13.08% |
| Technology | 2026-02-11 | 6 | 83.33% | 6.32% | -10.56% |
| Technology | 2026-03-11 | 7 | 14.29% | -2.92% | -11.30% |
| Technology | 2026-04-11 | 3 | 100.00% | 27.78% | -0.93% |
| Telecommunications | 2026-03-11 | 3 | 0.00% | -0.23% | -7.22% |
| Telecommunications | 2026-04-11 | 1 | 100.00% | 13.75% | -0.28% |

## Fresh Backtest Artifacts

- `validation/runs/v3_divergence_rule_backtest_technology_20260611_20260211_details.csv`
- `validation/runs/v3_divergence_rule_backtest_technology_20260611_20260311_details.csv`
- `validation/runs/v3_divergence_rule_backtest_technology_20260611_20260411_details.csv`
- `validation/runs/v3_divergence_rule_backtest_industrial_20260611_20260211_details.csv`
- `validation/runs/v3_divergence_rule_backtest_industrial_20260611_20260311_details.csv`
- `validation/runs/v3_divergence_rule_backtest_industrial_20260611_20260411_details.csv`
- `validation/runs/v3_divergence_rule_backtest_energy_20260611_20260211_details.csv`
- `validation/runs/v3_divergence_rule_backtest_energy_20260611_20260311_details.csv`
- `validation/runs/v3_divergence_rule_backtest_energy_20260611_20260411_details.csv`
- `validation/runs/v3_divergence_rule_backtest_telecom_20260611_20260211_details.csv`
- `validation/runs/v3_divergence_rule_backtest_telecom_20260611_20260311_details.csv`
- `validation/runs/v3_divergence_rule_backtest_telecom_20260611_20260411_details.csv`
- `validation/runs/v3_divergence_rule_backtest_utilities_20260611_20260211_details.csv`
- `validation/runs/v3_divergence_rule_backtest_utilities_20260611_20260311_details.csv`
- `validation/runs/v3_divergence_rule_backtest_utilities_20260611_20260411_details.csv`
