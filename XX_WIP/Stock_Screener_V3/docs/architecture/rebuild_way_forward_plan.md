# Rebuild Way Forward Plan

Date: 2026-06-01

This plan translates the fresh charter into implementation phases.

## Phase 1: Repository Baseline

Goal: create a clean, Git-tracked reset workspace.

Deliverables:

- Fresh charter.
- Current engine gap analysis.
- Archived reference documents.
- Repository structure.
- Initial commit.

## Phase 2: Metadata Baseline

Goal: stop depending on live profile calls for basic scanner metadata.

Deliverables:

- `UniverseRecord` schema.
- Enriched US universe file.
- Enriched NSE universe file.
- Loader that returns symbol plus metadata.
- Metadata preservation in historical replay.

Required fields:

- Symbol.
- YahooSymbol.
- CompanyName.
- Exchange.
- Sector.
- Industry.
- InstrumentType.
- MarketCap.
- AvgDailyVolume.
- SourceFile.
- LastProfileRefreshDate.

Parallel WIP track: enriched US master universe.

Purpose:

- Build and maintain a master NYSE/NASDAQ universe CSV with enough profile and financial fields to support pre-scan universe filters.
- Allow execution on narrower symbol sets, such as `TrailingPE < 25`, instead of always scanning `ALL_CODES`.
- Keep scanner/runtime hot paths focused on price/evidence loading, not repeated company-profile lookups.
- Preserve metadata in output rows so UI detail panes can render directly from the loaded universe and scan result as a secondary benefit.

Target universe:

- NYSE.
- NASDAQ.
- Later extension: AMEX and India-specific enriched universes if needed.

Required enrichment fields:

- Symbol.
- YahooSymbol.
- CompanyName.
- Exchange.
- Sector.
- Industry.
- InstrumentType.
- MarketCap.
- AvgDailyVolume.
- LastProfileRefreshDate.

Planned additional universe filter/cache fields:

- LongName or DisplayName.
- Website.
- Country.
- Currency.
- MarketCapCategory.
- SharesOutstanding.
- FloatShares.
- TrailingPE.
- ForwardPE.
- PriceToBook.
- PriceToSales.
- DividendRate.
- DividendYield.
- ExDividendDate.
- DividendDate.
- EarningsDate.
- Beta.
- FiftyTwoWeekHigh.
- FiftyTwoWeekLow.
- AverageVolume10D.
- AverageVolume3M.

Freshness and audit rules:

- Profile/financial fields are universe filter metadata, not stage-evaluation evidence unless explicitly moved into `EvidencePack`.
- Every enrichment run must stamp `LastProfileRefreshDate` and source/provider fields where practical.
- Historical backtests may use cached metadata for filtering and display, but must not treat current profile facts as historical truth without tagging them.
- Missing enrichment fields should not skip symbols. Leave blanks and preserve the symbol.
- The UI should prefer enriched universe fields before making new live profile calls.

Planned filter behavior:

- Add universe-filter predicates that run before price loading and stage evaluation.
- Support numeric comparisons for fields such as `TrailingPE`, `ForwardPE`, `MarketCap`, `DividendYield`, `Beta`, and average volume.
- Support categorical filters for fields such as exchange, sector, industry, country, currency, instrument type, and market-cap category.
- Missing values should use explicit include/exclude semantics chosen by the user or config.
- Filter diagnostics should report the original universe size, filtered universe size, and per-filter exclusion counts.

Implementation tasks:

1. Define the enriched US master CSV schema.
2. Add or update a metadata enrichment script for NYSE/NASDAQ symbols.
3. Add universe pre-filter support for enriched metadata predicates.
4. Extend `UniverseRecord` only for fields needed by engine/report contracts; keep extra filter/display fields in preserved row metadata or a separate profile cache until needed.
5. Update the universe loader to preserve additional CSV columns where practical.
6. Add tests proving required metadata survives loading, filtering, and scan output.
7. Add a refresh workflow that can update stale profile fields without changing signal-engine logic.

## Phase 3: Backtesting Engine V1

Goal: make historical validation a first-class subsystem.

Deliverables:

- Single-date replay.
- Random-lot replay.
- Sector-filtered replay.
- Full-universe ranked replay.
- D+1, D+2, and D+5 validation.
- Candidate-density reporting.
- Score-bucket reporting.
- Baseline comparison output.

Rules:

- No look-ahead bias.
- Same production engine as live scan.
- Preserve as-of metadata.
- Record all skipped symbols and reasons.

## Phase 4: Evidence Pack

Goal: separate calculations from decisions.

Deliverables:

- `EvidencePack` object.
- Market context section.
- Sector context section.
- Stock baseline section.
- Stage-specific evidence sections.
- Risk/context evidence section.

No classification should happen inside raw indicator calculation.

## Phase 5: Stage Evaluators

Goal: rebuild the decision layer around route, timing, quality, and context.

Deliverables:

- `CrossoverEvaluator`.
- `DivergenceEvaluator`.
- `MomentumEvaluator`.
- `StageEvaluation` output model.

Each evaluator should return:

- CandidateState.
- CandidateClass.
- ReviewPriority.
- Confidence.
- Score components.
- Reason codes.

## Phase 6: Crossover V2

Goal: avoid overloading Crossover with every bullish opportunity.

Crossover transition types:

- Below-zero bullish reversal crossover.
- Above-zero bearish reversal crossover.

The engine should not hide valid technical signals merely because they carry context risk.

Momentum Setup types:

- Bullish pullback re-entry.
- Bullish continuation momentum.

These belong in the Momentum evaluator because the stock is already in bull phase rather than transitioning into it.

## Phase 7: Validation Pack

Goal: promote changes only after broad validation.

Minimum pack:

- At least 5 D dates.
- Multiple market regimes.
- Sector-restricted samples.
- Random samples.
- Large or full-universe ranked test.
- Baseline comparison.

Promotion criteria:

- Candidate density is useful.
- Score buckets separate outcomes better than baseline.
- Failure causes are explainable.
- Improvement is not isolated to one date or one ticker.
