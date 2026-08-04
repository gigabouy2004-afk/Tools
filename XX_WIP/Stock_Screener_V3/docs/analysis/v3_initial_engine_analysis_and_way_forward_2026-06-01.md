# V3 Initial Engine Analysis And Way Forward

Date: 2026-06-01

Repository: `Stock_Screener_V3`

Status: Program execution plan.

## 1. Starting Position

V3 is a clean repository created to avoid further complexity inside V2.

The fresh charter and current-engine gap analysis agree on one core point:

```text
The current V2 engine has useful parts, but its decision layer became too restrictive and reactive because route validity, quality scoring, context risk, and output suppression were mixed together.
```

The V3 effort should therefore not begin by copying all V2 code.

It should begin by building the foundation that V2 lacked:

1. Stable universe metadata.
2. A first-class backtesting engine.
3. A neutral evidence pack.
4. Stage evaluators that separate signal validity from confidence and review priority.

## 2. What V3 Should Preserve From V2

V2 should remain the reference engine, not the base architecture.

Preserve these ideas:

- User-driven scanning.
- Web app workflow.
- CSV/manual universe input.
- Stage families:
  - Crossover.
  - Divergence.
  - Momentum Trading.
- Indicator calculation knowledge.
- Reason-code habit.
- Fixed-date historical replay idea.
- Lessons from low candidate density and weak score ranking.

Do not preserve these as-is:

- Monolithic `StockScreener.screen()` workflow.
- Crossover decision function as the central authority.
- Hard-gate accumulation pattern.
- Current `WeightedScore` as promotion logic.
- Historical replay without metadata preservation.

## 3. Key Design Correction

The V3 output model must separate four concepts:

| Concept | Meaning |
|---|---|
| CandidateState | What technical state exists |
| CandidateClass | Whether it is selected, watch, rejected, or status quo |
| ReviewPriority | How urgently the user should review it |
| RiskTags | Why the candidate may fail despite a valid signal |

This is the most important correction.

In V2, many risky but technically valid rows were demoted to `STATUS_QUO`. In V3, they should remain visible as valid but lower-priority or risk-tagged rows.

## 4. Recommended Build Sequence

### Phase 0: Baseline Documentation

Status: Complete.

Deliverables already present:

- Fresh program charter.
- V2 gap analysis.
- Backtesting requirements.
- Rebuild way-forward plan.

### Phase 1: Project Skeleton And Contracts

Goal:

Define the V3 module boundaries before implementing signal logic.

Deliverables:

- Python package skeleton.
- Core domain models:
  - `UniverseRecord`.
  - `PriceDataBundle`.
  - `EvidencePack`.
  - `StageEvaluation`.
  - `ScoreResult`.
  - `BacktestRunConfig`.
  - `BacktestResult`.
- Initial tests for model creation and serialization.

Acceptance criteria:

- Models can be imported.
- Tests pass.
- No signal logic yet.

### Phase 2: Universe Metadata Baseline

Goal:

Stop treating a universe as only a list of symbols.

Deliverables:

- CSV loader that returns `UniverseRecord` objects.
- US master file mapper.
- NSE master file mapper.
- Metadata normalization:
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
- Small test fixture CSVs under `data/samples`.

Acceptance criteria:

- Loader preserves sector and industry.
- Loader normalizes NSE symbols with `.NS`.
- Duplicate symbols are removed deterministically.
- Tests prove metadata survives through loading.

### Phase 3: Backtesting Engine V1

Goal:

Create the validation foundation before rebuilding signal logic.

Deliverables:

- Historical D-date runner.
- Deterministic random sample runner.
- Sector-filtered runner.
- Forward validation:
  - D+1.
  - D+2.
  - D+5.
- Candidate-density reporting.
- Detail CSV writer.
- Summary markdown writer.

Acceptance criteria:

- Backtester can run against a mock stage engine.
- No-lookahead slicing is tested.
- Summary reports include symbols processed, candidates found, density, and forward returns.

Important:

This phase can use a mock evaluator first. It does not need the final Crossover logic.

### Phase 4: Data Provider Layer

Goal:

Separate data fetching from signal logic.

Deliverables:

- Data provider interface.
- Yahoo provider implementation.
- Local cache policy.
- Daily and intraday OHLCV loader.
- Benchmark loader.

Acceptance criteria:

- Data provider can fetch daily and intraday data.
- Historical slicing happens outside evaluator logic.
- Missing data returns structured skip reasons.

### Phase 5: Evidence Pack V1

Goal:

Calculate facts without making stage decisions.

Deliverables:

- MACD evidence.
- RSI evidence.
- ADX/DMI evidence.
- Bollinger evidence.
- EMA evidence.
- Candle evidence.
- Volume/money-flow evidence.
- Price-structure evidence.
- Market/sector relative strength evidence.

Acceptance criteria:

- Evidence pack is serializable.
- Evidence pack contains no final candidate classification.
- Tests prove indicator functions do not need candidate state.

### Phase 6: Stage Evaluator V1

Goal:

Implement clean stage evaluation contracts.

Deliverables:

- `CrossoverEvaluator`.
- `DivergenceEvaluator`.
- `MomentumEvaluator`.
- Reason-code categories.
- Candidate class and review priority.

Acceptance criteria:

- Each evaluator returns `StageEvaluation`.
- Evaluators do not fetch data.
- Evaluators do not write output files.
- Risk/context tags do not automatically erase valid signals.

### Phase 7: Crossover V2

Goal:

Fix the overloaded Pre-Bull design.

Suggested opportunity types:

- `PRE_BULL_REVERSAL_CROSSOVER`.
- `BULL_PULLBACK_REENTRY`.
- `BULL_CONTINUATION_MOMENTUM`.
- `PRE_BEAR_REVERSAL_CROSSOVER`.

Acceptance criteria:

- Below-zero reversal and above-zero re-entry are separate states.
- Valid signal, low confidence, and event risk can all coexist.
- Candidate density improves versus V2 without hiding risk.

### Phase 8: Standard Validation Pack

Goal:

Make model promotion evidence-based.

Minimum pack:

- At least 5 D dates.
- At least 3 sector-restricted tests.
- Random-lot tests.
- Large or full-universe ranked test.
- D+1, D+2, D+5 metrics.
- Score-bucket behavior.
- Failure category distribution.

Acceptance criteria:

- V3 shows candidate density high enough for practical review.
- Higher priority groups outperform lower priority groups.
- Failure categories are explainable.
- Improvements hold across more than one date.

## 5. Recommended Immediate Sprint

The first sprint should not implement Crossover logic.

It should establish contracts and validation infrastructure.

Sprint 1 scope:

1. Create Python package skeleton.
2. Define core dataclasses.
3. Add universe loader for sample CSVs.
4. Add backtest run config and summary structures.
5. Add unit tests for metadata preservation and historical slicing.

Sprint 1 implementation status:

- Package skeleton created under `src/stock_screener_v3`.
- Core model contracts created in `models.py`.
- Universe CSV loader created in `universe.py`.
- Universe sector/exchange filtering and deterministic sampling added.
- Historical slicing and forward-return helpers created in `backtesting.py`.
- BacktestEngine v1 created in `backtest_engine.py`.
- BacktestEngine v1 supports pluggable price providers and stage evaluators.
- BacktestEngine v1 reports symbols attempted, processed, skipped, candidates found, candidate density, and candidate-only forward hit rates.
- Yahoo data provider wrapper created in `data_provider.py`.
- Backtest detail CSV and summary markdown writers created in `reports.py`.
- Sample US and NSE universe fixtures added under `data/samples`.
- Unit tests added under `tests`.
- Initial test command passed:

```powershell
$env:PYTHONPATH='D:\Tools\Stock_Screener_V3\src'
python -m unittest discover -s tests -v
```

Current test count:

```text
Ran 15 tests
OK
```

Why this first:

- It prevents V3 from repeating V2's monolithic pattern.
- It lets us validate future engine logic immediately.
- It makes sector-filtered testing reliable.

## 6. Implementation Backlog

Priority 1:

- Core model contracts.
- Universe loader.
- Metadata fixtures.
- Backtest config/result models.

Priority 2:

- Data provider interface.
- Historical slicing utility.
- Backtest runner using a mock evaluator.
- Summary reporting.

Priority 3:

- Evidence pack builder.
- Indicator functions migrated from V2 only after contracts exist.

Priority 4:

- Crossover V2 evaluator.
- Divergence evaluator.
- Momentum evaluator.

Priority 5:

- Web UI or CLI integration.

## 7. Go / No-Go Decision

Proceed with V3 refactor/rebuild.

Do not port V2 wholesale.

Use V2 only as:

- indicator reference.
- validation lesson source.
- UI behavior reference.
- historical replay reference.

The first implementation milestone is not a working scanner. It is a reliable foundation that makes a working scanner testable.
