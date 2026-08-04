# V8 ETF Information Extraction — Phase 2 Conclusion

Date: 2026-07-11

Status: Phases 2A, 2B, and 2C implemented and five-stock validation completed. Awaiting user review before V8 operational activation.

## Scope Decision

The Beta track is closed and dropped. Its pilot evidence was not sufficiently conclusive to establish a dependable relationship with forward price movement. Beta is not calculated or messaged by the active V8 engine.

Phase 2 is now the only V8 post-processing feature:

```text
Confirmed Active Momentum stock -> direct ETF extraction -> ETF-only Score_Message
```

`Score` remains the sole action value and is never modified by ETF processing.

## Phase 2A — Direct Source Selection

### Existing scanner rejected for the live path

`D:/Tools/StockCode_ETF_Mapping/Stock_Code_ETF_Mapping_v5.py` loops across an ETF universe and calls Yahoo/yfinance holdings sources. That architecture is suitable only as a separate offline utility and is prohibited inside V8.

### FMP candidate not selected

Financial Modeling Prep documents a direct asset-exposure endpoint:

```text
https://financialmodelingprep.com/stable/etf/asset-exposure?symbol=AAPL
```

Its public documentation describes ETF ticker exposure, shares, market value, and holding weight. It does not document an ETF holding-rank/top-ten field. No entitled FMP key is configured locally. It therefore could not satisfy the strict top-ten proof requirement for this release.

### Selected direct internal source

The implementation uses one stock-specific TradingView page:

```text
https://www.tradingview.com/symbols/<EXCHANGE>-<STOCK>/etfs/
```

The response provides a direct list of funds holding the stock, including fund ticker, exchange, and stock weight. It returns up to 100 rendered rows without scanning a local or remote ETF universe.

This is a public TradingView page, not a documented developer API contract. The implementation therefore validates the response schema, records the page hash, uses a bounded timeout, caches successful results, and fails open if the page changes.

### Strict top-ten proof

For a non-leveraged portfolio with non-negative weights summing to 100%, a holding above:

```text
100 / 11 = 9.090909...%
```

cannot have ten holdings with larger weights ahead of it. V8 therefore accepts only mappings that:

1. Exist in the local USA ETF master.
2. Are not identified as leveraged or inverse.
3. Have stock holding weight strictly greater than `100/11` percent.

This is conservative. Valid top-ten holdings at lower weights are intentionally omitted rather than guessed.

## Phase 2B — ETF Mapping Module

Implemented files:

```text
ETF_Context_V8.py
config/V8_Post_Processor_Message_Map.csv
tests/test_etf_context_v8.py
```

Implemented behavior:

- `getETFMappedCodes(stock_code) -> str`.
- One direct stock page request per uncached lookup.
- Local US ETF whitelist.
- Leveraged/inverse exclusion.
- Conservative top-ten proof.
- Maximum three ETFs ordered by weight descending.
- 24-hour persistent cache by default.
- Eight-second bounded request timeout by default.
- Response hash, URL, HTTP status, latency, counts, and retrieval time in audit context.
- Explicit no-mapping, partial/schema-error, and unavailable message rules.
- No Score or decision mutation.

Five ETF unit tests passed:

- Direct-page parser.
- US/non-leveraged/top-ten filter.
- One-request cache behavior.
- Active trigger and Score invariance.
- Top-three descending sort and overflow audit reason.

## Phase 2C — V8 Integration

`Momentum_Detector_V8.py` imports only the ETF post-processor. Root-level Beta implementation and Beta test/backtest utilities were removed; the historical frozen Beta run remains audit evidence.

Production trigger:

```text
Final_Decision == MOMENTUM_ACTIVE
AND Score >= CONFIRMED_ENTRY_MIN_SCORE
```

Current threshold:

```text
CONFIRMED_ENTRY_MIN_SCORE = 85
```

CLI presentation values do not affect this trigger.

Example output:

```text
Score = 92
Score_Message = Active momentum confirmed. Verified top-10 ETF mappings: SMH 19.20%; VGT 16.77%; FTEC 16.60%.
```

## Canonical Five-Stock Validation

Implementation commit used by the run:

```text
6fa10c6 Tighten V8 ETF audit counts and freshness checks
```

Run ID:

```text
V8ETF_20260711T135316Z_6fa10c6
```

Run folder:

```text
backtests/V8_ETF_Phase2/runs/V8ETF_20260711T135316Z_6fa10c6
```

### Results

| Stock | Eligible before top-3 limit | Returned message mappings | Independent top-10 validation |
|---|---:|---|---|
| NVDA | 19 | `SMH 19.20%; VGT 16.77%; FTEC 16.60%` | 3/3 pass; ranks 1, 1, 1 |
| AAPL | 11 | `FTEC 15.94%; VGT 15.25%; IYW 12.78%` | 3/3 pass; ranks 2, 2, 2 |
| MSFT | 2 | `VGT 9.87%; VOOG 9.28%` | 2/2 pass; ranks 3, 2 |
| TSLA | 3 | `XLY 19.05%; VCR 17.67%; ARKK 10.37%` | 3/3 pass; ranks 2, 2, 1 |
| AMZN | 2 | `XLY 23.11%; VCR 22.14%` | 2/2 pass; ranks 1, 1 |

Aggregate result:

```text
Production-style stock requests: 5
Production requests per stock: 1.0
Returned mappings: 13
Top-ten rank validations passed: 13/13
Validation failures: 0
Mappings within 60-day freshness limit: 13/13
Oldest validation holdings date: 43 days
```

Production-style reverse-request latency:

```text
Median: 155.67 ms
P95: 212.51 ms
Maximum: 226.16 ms
```

The 13 separate ETF holdings-page requests were performed only by the backtest to validate actual top-ten ranks and freshness. They are not imported or reachable from the production V8 engine.

## Traceability

The canonical run stores:

- Exact ETF, V8, backtest, message-map, and test source snapshots.
- Frozen stock and US ETF master snapshots.
- Per-stock API quality summary.
- Per-mapping direct weights, validation ranks, validation weights, as-of dates, freshness ages, latencies, URLs, and response hashes.
- Run manifest and SHA-256 checksum inventory.

## Known Limitations

- TradingView's public page is not a versioned developer API contract and may change structure.
- The direct page exposes only its first 100 rendered funds.
- Conservative proof omits valid lower-weight top-ten holdings.
- The direct reverse page does not expose a holdings as-of date. Freshness was confirmed through test-only ETF holdings pages.
- A future licensed direct API that returns explicit rank and as-of date could replace the adapter without changing the V8 trigger or Score contract.

## Phase 2 Conclusion

Phases 2A, 2B, and 2C are technically complete for the approved conservative internal design. The five-stock sample passed request-count, US-listing, top-ten rank, freshness, sorting, latency, and Score-invariance checks.

V7 remains operational and unchanged. V8 remains a development engine until the user reviews this conclusion and explicitly authorizes the operational version switch.
