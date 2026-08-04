# V17 Runtime-Only Execution Plan

Date: 2026-07-30

Branch: `V17`

Baseline commit: `3586f24cb4e8390e66476e30f895e1a3ce3ff430`

Baseline tag: `baseline-v17-momentum-foundation-2026-07-30`

Document role: active implementation plan supporting the master blueprint

Status: approved planning baseline; implementation not yet started

## Continuity and restart state

The master blueprint is the standalone authority. This plan may sequence work
but may not introduce an assumption, decision, gate or status that is absent
from the master.

Every implementation-progress commit must update together:

- `docs/MOMENTUM_ENGINE_MASTER_BLUEPRINT.md`, including its living checkpoint;
- this action plan;
- `CHANGELOG.md`; and
- any other supporting document affected by the change.

The continuity regression test requires the master, this plan and changelog to
share the same latest commit and prevents implementation progress from being
committed ahead of the master.

Current synchronized restart state:

| Item | State |
|---|---|
| Product work | Runtime architecture approved; implementation not started |
| Current runtime gate | R1 - pending |
| Current scientific gate | G1 blocked; G2-G8 blocked or not started |
| Next action | Add/retain tests for legacy local-input and persistent-cache behavior, then implement R1 |
| Prohibited scope | No signal, threshold, classifier, BUY or activation change |
| Handoff authority | Section 25 of the master blueprint |
| Last validation | 82 unit tests, syntax compilation, diff checks and root master-link verification passed |

## Governing constraints

The implementation must satisfy all of the following:

1. Use only sources that can be accessed without a paid subscription or API
   key.
2. Discover the requested market universe at runtime.
3. Download all required market history at runtime.
4. Never require a local universe master, historical database, historical-data
   folder, persistent market-data cache or resume checkpoint.
5. Accept either a small explicit list of stock codes or the complete
   Nasdaq/NYSE listed-equity universe.
6. Keep the normal end-user path limited to choosing the input scope and,
   optionally, an output location.
7. Avoid serial per-ticker work across the complete market wherever a bulk
   request or vectorized calculation can produce the same result.
8. Preserve the V17 completed-session, instrument-scope and per-stock
   independence contracts.
9. Expose missing, rejected or provider-failed symbols instead of silently
   dropping them.
10. Keep all genuine-momentum and production-activation flags false.

The prohibition applies to historical inputs and reusable data stores. A final
workbook and execution log are permitted outputs; they must never be read as
historical inputs by a later run.

## Feasibility boundary

The constrained runtime product and promotion-quality momentum research are
different deliverables.

The runtime product can:

- discover today's Nasdaq and NYSE listings;
- download currently available adjusted daily history in bulk;
- calculate the inherited completed-daily foundation;
- add recent completed current-session 1-hour/4-hour diagnostics;
- run a current-survivor daily reference replay; and
- produce a plain-language review without a local data installation.

The same free, runtime-only design cannot establish:

- point-in-time historical exchange membership;
- inactive and delisted-security coverage;
- stable identity through every historical ticker change;
- immutable source versions and adjustment provenance;
- several years of 30-minute history; or
- reproducible promotion evidence after the remote source changes.

Therefore a runtime backtest is explicitly a biased reference diagnostic. It
cannot pass scientific gates G1-G8 in the master blueprint and cannot support
`TRUE_MOMENTUM_CONFIRMED`. This is a data constraint, not a calculation
shortcut.

## Runtime source contract

### Universe discovery

Use the official Nasdaq Trader symbol-directory files at run start:

- `nasdaqlisted.txt` for Nasdaq-listed securities; and
- `otherlisted.txt` for other U.S. listings.

For the supported scope:

- reject rows marked as test issues;
- reject ETFs;
- use Nasdaq-listed rows for the Nasdaq scope;
- retain only exchange code `N` from `otherlisted.txt` for NYSE;
- reject NYSE American, NYSE Arca, OTC and other venues; and
- normalize provider-specific symbols only after the original symbol is
  retained for reporting.

The SEC `company_tickers_exchange.json` file may be downloaded once per run to
corroborate ticker, company and exchange identity. It is not the sole universe
authority and must not cause a valid symbol to disappear silently.

Because the symbol-directory files contain listed securities beyond common
equities, use paginated `yfinance.EquityQuery` exchange screens (`NMS`, `NGM`,
`NCM` and `NYQ`) as a batch equity-type corroboration layer. Only unresolved
symbols may fall back to bounded per-symbol history metadata. A symbol that
cannot be verified as an in-scope equity receives an explicit
`UNVERIFIED_INSTRUMENT` or rejection result; it is never silently included.

### Market history

The first implementation adapter uses `yfinance` multi-ticker download for
adjusted daily OHLCV and recent 30-minute regular-session data.

Required request behavior:

- daily data uses a multi-symbol bulk request with threading enabled;
- `auto_adjust=True`;
- `prepost=False`;
- only the minimum daily history required by the frozen calculations is
  requested;
- raw downloads exist in memory only for the duration of the run;
- any provider-library cookie/timezone cache is redirected to an isolated
  per-run operating-system temporary directory and removed on exit; it never
  contains reusable OHLCV history;
- retries use bounded exponential backoff with jitter;
- failed batches are split to isolate bad symbols;
- failed symbols receive explicit output rows and reason codes; and
- no retry loop is unbounded.

`yfinance` is a free-access research interface to Yahoo data, not a contracted
market-data service. Its own documentation states that intraday history cannot
extend beyond the most recent 60 days. Provider availability, throttling and
terms remain external constraints.

Primary references:

- [Nasdaq Trader symbol-directory definitions](https://www.nasdaqtrader.com/trader.aspx?id=symboldirdefs)
- [SEC EDGAR data-access guidance](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data)
- [SEC ticker and exchange JSON](https://www.sec.gov/files/company_tickers_exchange.json)
- [yfinance multi-ticker download reference](https://ranaroussi.github.io/yfinance/reference/api/yfinance.download.html)
- [yfinance equity screener reference](https://ranaroussi.github.io/yfinance/reference/yfinance.screener.html)
- [yfinance project and usage notice](https://ranaroussi.github.io/yfinance/index.html)

All endpoints must be isolated behind adapters so a later free source can be
substituted without changing engine calculations.

## Target end-user interface

The delivered command surface is:

```powershell
# A few stock codes
python .\Live_Scanner_v17.py -c AAPL MSFT NVDA

# Every supported Nasdaq-listed equity
python .\Live_Scanner_v17.py --universe nasdaq

# Every supported NYSE-listed equity
python .\Live_Scanner_v17.py --universe nyse

# The combined supported universe
python .\Live_Scanner_v17.py --universe all
```

The user may optionally set the output path. Provider retries, history length,
batch sizing, worker count, time budgets and enrichment routing must have safe
automatic defaults. Advanced diagnostic switches may exist but must not be
required for normal use.

The legacy default local input CSV, persistent daily cache, cache directory,
cache TTL and resume/checkpoint workflow must not be part of the normal runtime
path.

## Two execution lanes

The input size changes data-access strategy only. It must never change a
stock's completed-daily calculation or classification.

### Small-list lane

For an explicit list at or below the internally tested small-list threshold:

1. normalize and deduplicate the supplied codes;
2. verify supported exchange/instrument identity at runtime;
3. bulk-download daily history for the list;
4. calculate the completed-daily foundation for every valid code;
5. fetch recent 30-minute data and construct completed current-session 1-hour
   and 4-hour evidence for every valid code;
6. produce the final workbook and text log.

The provisional threshold is 25 symbols. It becomes a frozen internal default
only after benchmark testing.

### Large/all-market lane

For a larger explicit list or discovered exchange universe:

1. download and parse the runtime universe;
2. normalize and deduplicate symbols while retaining original identities;
3. divide the universe into adaptive daily-data batches;
4. bulk-download adjusted daily OHLCV;
5. calculate the daily foundation vectorially or batch-wise in memory;
6. immediately reduce raw history to compact result records;
7. discard completed raw batches from memory;
8. identify daily-qualified candidates using the unchanged V17 conditions;
9. fetch metadata and recent 30-minute data only for those candidates;
10. calculate completed current-session 1-hour/4-hour evidence for every
    candidate that can be reached within the bounded run;
11. automatically retry transient failures once through the isolation path;
12. write one final workbook and one text log.

No arbitrary top-N cap may be applied to daily-qualified candidates. If a
provider or time budget prevents enrichment, the daily result remains present
and the missing intraday evidence is marked `NOT_AVAILABLE`, with its reason.

## Performance and responsiveness contract

Free endpoints cannot support an honest fixed all-market completion guarantee.
V17 must instead meet measurable software gates and report external-provider
limitations plainly.

The implementation is accepted only when:

- progress or a source-status message appears within 10 seconds;
- progress is refreshed at least once per completed batch and never remains
  silent for more than 30 seconds during active work;
- status includes completed/total symbols, failures, elapsed time and current
  phase;
- daily data for a large universe is not fetched through one
  `Ticker.history()` call per symbol;
- non-critical metadata is not requested for the whole large universe;
- memory contains at most the current raw-data batches plus compact results;
- measured peak memory remains at or below 1 GiB in the full-universe
  acceptance run;
- calculation output for the same symbol/date is identical in small and large
  lanes;
- retries and backoff terminate within a documented budget;
- an interrupted or provider-degraded run still writes an explicit partial
  result when at least one symbol was evaluated; and
- the final summary never describes partial coverage as a complete market
  scan.

Benchmark 2, 25, 100, 1,000 and the full runtime universe on the same machine
and connection. Record source time, calculation time, enrichment time, output
time, peak memory, success rate and retry count. Freeze a realistic service
target only after those measurements exist. Until then, elapsed-time targets
are goals, not promises:

- 2-symbol run: target under 30 seconds;
- 25-symbol run: target under 90 seconds; and
- daily foundation for the full supported universe: target under 15 minutes.

Provider throttling may invalidate these targets. The run must fail or finish
partially and clearly; it must not appear to hang.

## Output contract

The workbook remains intentionally simple:

- `Summary` gives scope, source timestamps, counts, duration and data-quality
  status;
- `Review` gives one plain-language row for every requested/discovered symbol;
  and
- hidden `Technical Data` retains the diagnostic vector and reason codes.

The summary must include:

- input mode and requested exchanges;
- discovered, accepted, rejected and duplicate counts;
- daily download, daily evaluation and daily failure counts;
- candidate and intraday-enrichment counts;
- unavailable/incomplete evidence counts;
- source names and retrieval timestamps;
- total elapsed time;
- whether coverage is complete or partial; and
- a statement that free runtime data is not promotion-quality historical
  evidence.

For a non-candidate in the large lane, the visible explanation should say that
current-session enrichment was not required because the completed-daily
foundation did not qualify. It must not imply that missing intraday work is a
bearish result.

## Implementation gates

Runtime delivery gates R1-R8 do not replace scientific promotion gates G1-G8.

### R1 - Freeze interfaces and remove local-input dependencies

Implement and test:

- `--universe nasdaq|nyse|all`;
- mutual-exclusion and validation rules for `--codes` and `--universe`;
- no default local input file;
- no persistent historical cache in the runtime path;
- no persistent provider-library cookie/timezone cache;
- no cache/checkpoint/resume requirement;
- a runtime-only default output location under the current working directory;
  and
- a run manifest embedded in the final output.

Exit when a clean machine can reach argument validation without any local data
installation.

### R2 - Implement runtime universe discovery

Create a universe adapter that:

- downloads and parses the Nasdaq Trader files;
- applies exchange, ETF and test-issue filters;
- handles footer rows and malformed lines;
- corroborates instrument type through paginated equity screens;
- optionally corroborates through the SEC file;
- records rejection reasons; and
- returns a deterministic first-seen symbol list.

Exit when fixture tests and a live smoke confirm scope and counts.

### R3 - Implement the bulk daily engine

Refactor daily acquisition so:

- one bulk call serves a batch;
- multi-index provider output is normalized safely;
- one symbol's malformed data cannot discard a successful batch;
- calendar and completed-session filters are applied consistently;
- calculations match the current direct-ticker engine;
- raw batch frames are released after reduction; and
- results are independent of batch size and order.

Exit when daily output is identical across direct, batched and reordered runs.

### R4 - Implement lane routing and candidate enrichment

Add automatic small/large routing. In the large lane:

- calculate daily results for all accepted symbols first;
- queue every daily-qualified candidate;
- fetch only necessary metadata;
- download recent 30-minute bars in bounded groups where supported;
- construct only full-duration completed 1-hour/4-hour observations; and
- retain explicit unavailable reasons.

Exit when changing input population, batch size or concurrency cannot change a
shared symbol's daily or intraday result.

### R5 - Make failures bounded and visible

Add:

- request timeout;
- bounded retries with backoff and jitter;
- batch splitting;
- automatic rate-limit detection;
- per-symbol failure reasons;
- run-level coverage classification; and
- graceful final-output generation after partial provider failure.

Exit when injected timeout, empty-response, malformed-symbol and rate-limit
tests terminate and report correctly.

### R6 - Simplify progress and output

Provide phase-based progress without requiring configuration. Update the
workbook and log to meet the output contract and keep internal activation flags
out of the visible review.

Exit when a first-time user can run either input form and understand complete,
partial and unavailable states from `Summary` and `Review`.

### R7 - Add runtime-only reference backtesting

Refactor the existing daily reference replay so it can:

- discover today's exchange universe at runtime;
- bulk-download daily history at runtime;
- calculate without a local universe master;
- avoid checkpoints and resume inputs; and
- label every result `CURRENT_SURVIVOR_REFERENCE_ONLY`.

Do not implement a runtime 1-hour/4-hour promotion backtest. The free recent
intraday window is a smoke/operational diagnostic only.

Exit when the backtest runs without local historical inputs and its output
cannot be confused with point-in-time promotion evidence.

### R8 - Benchmark, regression-test and release

Run:

1. deterministic unit and syntax validation;
2. no-local-input filesystem tests;
3. 2-, 25-, 100-, 1,000- and full-universe benchmarks;
4. parity checks for shared symbols across both lanes;
5. repeated runs with different batch sizes and worker ordering;
6. injected provider degradation;
7. workbook review for complete and partial coverage; and
8. a clean-worktree release audit.

Exit only after the benchmark record freezes the production defaults and
documents any free-provider limitations.

## Required test inventory

At minimum, add tests for:

- Nasdaq and NYSE directory parsing;
- ETF, test-issue and wrong-exchange rejection;
- SEC corroboration conflict handling;
- equity-screen pagination and unresolved-instrument handling;
- ticker normalization and duplicate handling;
- CLI input exclusivity;
- proof that no historical input path is read;
- proof that no persistent market-data cache is written;
- proof that provider technical cache is temporary and cleaned;
- bulk multi-index daily normalization;
- completed-session filtering;
- bad-symbol batch isolation;
- calculation parity across lane, batch size and order;
- candidate-only enrichment;
- completed 1-hour/4-hour construction;
- bounded retries and timeout behavior;
- partial-run output generation;
- coverage-state summary;
- memory release between batches; and
- explicit runtime-backtest limitation labels.

## Ordered implementation checklist

1. Add tests that fail on the current local-input and persistent-cache
   behavior.
2. Implement R1 and R2.
3. Implement R3 and prove parity before changing candidate enrichment.
4. Implement R4 and R5.
5. Implement R6.
6. Benchmark 2, 25 and 100 symbols; adjust internal defaults only from
   measurements.
7. Benchmark 1,000 symbols, then the full universe.
8. Implement R7 only after the live runtime path is stable.
9. Execute R8 and issue a new validation record.
10. Keep G1-G8 blocked/not started and all confirmation flags false.

## Regression commands

```powershell
python -m unittest discover -s tests -p "test_*.py"
python -m py_compile `
  Live_Scanner_v17.py v17_mtf.py v17_mtf_replay.py `
  momentum_research.py plain_language_output.py `
  build_momentum_research_panel.py `
  validate_momentum_research_panel.py
git diff --check
```

These checks protect implementation integrity. The full-universe benchmark and
provider-degradation tests are additional release gates, not substitutes for
unit tests.
