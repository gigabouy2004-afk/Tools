# Engine Backlog

## Offline Universe Preparation

- Prepare separate NYSE, NASDAQ, and NSE universe CSV files outside market hours.
- Include stable metadata columns where available: `Symbol`, `Exchange`, `Sector`, `Industry`, `InstrumentType`, and any reliable volume/market-cap fields.
- Use these prepared files as the primary scanner input so the live engine can avoid slow profile metadata calls where possible.
- Refresh cadence should be decided per market, but the job should not run during active market sessions.

## Data Provider Evaluation

- Evaluate whether a mixed API model is worth adding after the Yahoo-backed engine behavior is stable.
- Compare candidate providers on: intraday coverage, adjusted historical data, rate limits, cost, uptime, symbol mapping for NYSE/NASDAQ/NSE, and legal/data-use terms.
- If adopted, introduce a `DataProvider` abstraction so Yahoo remains one provider and another API can be plugged in without changing signal logic.

## Price Fetch Optimization

- Evaluate batched historical downloads for daily data first, then intraday data if Yahoo reliability is acceptable.
- Keep per-run auditability intact: every result row must still be attributable to the run timestamp, job id, filter set, and provider used.
