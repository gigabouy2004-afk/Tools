# V8 Beta Release-1 Pilot Report

Date: 2026-07-10

Status: Canonical historical pilot completed; Beta track closed and dropped on 2026-07-11 without production signoff.

> **Final user decision:** Results were not sufficiently conclusive to correlate Beta confidently with forward price movement. No further Beta work will be performed. Beta has been removed from the active V8 production path and from `Score_Message`. This report and its frozen run remain audit evidence only.

## Reproducible Run

Implementation commit:

```text
27cee6f Harden V8 offline artifact validation
```

Canonical run:

```text
V8BETA_20260710T175207Z_27cee6f_20260710
```

Stored run folder:

```text
backtests/V8_Beta_Release1/runs/V8BETA_20260710T175207Z_27cee6f_20260710
```

Invocation:

```text
python Backtest_Momentum_Detector_V8_Beta.py
```

Scope:

- Tickers: `NET`, `CSX`, `ILMN`, `ICHR`, `PL`, `CVV`, `ETN`, `ACA`, `MATX`.
- Requested history: 10 years.
- Completed tickers: 9 of 9.
- Failed downloads: 0.
- Replayed daily decisions: 17,236.
- New Active Momentum episode starts: 784.
- Programmed Active trigger: `Final_Decision == MOMENTUM_ACTIVE` and `Score >= 85`.
- CLI summary filters did not participate.
- Beta window: latest 252 aligned completed-session returns, with at least 200 observations.
- Hypothetical outcome convention: signal at day-D close, entry at D+1 open, exit at D+N close.

The run stores all stock/benchmark input prices, the master-library metadata subset, exact source snapshots, the daily decision audit, the Active-episode signal audit, interaction summaries, a deterministic random sample, expected replay values, a manifest, and SHA-256 checksums.

## Offline Validation Result

Command:

```text
python Validate_V8_Beta_Backtest.py backtests/V8_Beta_Release1/runs/V8BETA_20260710T175207Z_27cee6f_20260710
```

Result:

```text
PASS: 50 sampled signals replayed exactly; all stored checksums are valid.
```

The replay independently recomputed the sampled final decision, Score, Beta, R-squared, and Beta band from the frozen prices and source snapshot. This completes the first deterministic random-validation round for the pilot; it does not replace the planned broader holdout validation.

## Preliminary Beta-Band Results

| Beta band | Signals | Unique tickers | Median Beta | Median R-squared | Median 21D return | 21D positive | Median 63D return | 63D positive | Median 126D return | 126D positive |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Defensive (`<0.75`) | 49 | 3 | 0.67 | 0.10 | -1.90% | 45.45% | -5.62% | 47.37% | 19.52% | 62.96% |
| Balanced (`0.75..1.25`) | 426 | 7 | 1.06 | 0.32 | 1.03% | 57.62% | 2.27% | 56.86% | 7.78% | 65.72% |
| High sensitivity (`>1.25..1.75`) | 231 | 7 | 1.43 | 0.32 | 3.26% | 64.71% | 7.61% | 63.41% | 8.32% | 59.41% |
| Very high sensitivity (`>1.75`) | 78 | 4 | 2.09 | 0.31 | 1.18% | 52.56% | -3.99% | 47.83% | -9.06% | 33.33% |

Observed Beta-to-forward-return Spearman correlations were small: `0.043` at 1D, `0.049` at 5D, `0.083` at 10D, `0.134` at 21D, `0.118` at 63D, and `-0.121` at 126D.

This pilot does not support a simple rule that higher Beta should increase Momentum Score confidence. The middle high-sensitivity band performed better descriptively at 21D and 63D, while the very-high-sensitivity band had worse median 63D/126D outcomes and materially larger adverse paths. The small, ticker-clustered sample was not sufficiently conclusive for a production relationship, including informational Beta messaging.

## Market-Regime Linkage

| Market regime | Signals | Unique tickers | Median 21D return | 21D positive | Median 63D return | 63D positive |
|---|---:|---:|---:|---:|---:|---:|
| Bull | 725 | 9 | 1.65% | 59.09% | 3.37% | 57.79% |
| Bear | 24 | 2 | -1.18% | 41.67% | -2.75% | 33.33% |
| Transition | 35 | 7 | 1.08% | 57.14% | 4.93% | 65.71% |

The bear-regime direction is weaker, but its sample contains only 24 episode starts from two tickers. It is an investigation lead, not a validated production rule.

## Sector and Industry Linkage Limits

The run produced both sector and industry interaction files, but this nine-ticker pilot cannot isolate an industry effect:

- The 784 observations are repeated episodes clustered within only nine securities.
- Several sector/industry cells contain one ticker, so ticker behavior and industry behavior are confounded.
- Labels come from the current stored master-library snapshot, not point-in-time historical classifications.
- The current common-stock library introduces survivorship and universe-selection risk for a historical study.
- One high-growth ticker can materially influence long-horizon averages, especially in the very-high-Beta group.

Industry/sector conclusions therefore remain open. The broader study must increase the number of independent tickers per industry, preserve chronological development/validation/holdout partitions, and report ticker-cluster-aware uncertainty.

## Quality Findings

- All 784 pilot Beta calculations returned status `OK`.
- Median R-squared was `0.315`; 85 signals had R-squared below `0.10` and are explicitly messaged as weak-fit/descriptive Beta.
- The Beta processor writes only `Score_Message`; the explicit score-invariance unit test passed.
- All six Beta unit tests passed.
- V8 `pct_change` calls now specify `fill_method=None`; deprecated implicit NA padding is not used.
- V7 remains unchanged and operational. V8 remains a development engine.

## Terminal Decision

- No broader Beta universe expansion.
- No additional Beta holdout or random-validation rounds.
- No Beta production message or Score relationship.
- No active Beta module in the V8 engine.
- Proceed directly to V8 ETF information-extraction Phases 2A-2C under the 2026-07-11 user authorization.
