# V7/V8 reviewed session baseline

Baseline date: 2026-07-29

Branch: `baseline/v7-v8-session-history`

Parent: `94dc7b5` (`Add V6 and V7 live scanner scripts with buy cap and summary output`)

## Scope and baseline decision

This baseline preserves the V7/V8 session history without silently changing
the trading rules.

- `Live_Scanner_v7.py` is the final V7 snapshot recovered from `Retired`.
- `Live_Scanner_v8.py` is the canonical final V8 snapshot.
- `archive/v8_session_variants/Live_Scanner_v8_1_auto_session.py` preserves the
  earlier exchange-calendar experiment.
- `archive/v8_session_variants/Live_Scanner_v8-tmp.py` preserves the alternate
  manual-mode work file. It is not the canonical V8.
- The original V7 Git snapshot remains recoverable from parent commit
  `94dc7b5`.

The final V8 file is canonical because it has the stable version filename,
removes the undeclared `exchange_calendars` dependency, filters minute bars to
the current Eastern date, supports automatic/completed/intraday candle modes,
and separates ticker-count and BUY-count limits.

## Captured source checksums

These SHA-256 values identify the source files as recovered before Git line
ending normalization:

| Session artifact | SHA-256 |
| --- | --- |
| V7 initial Git snapshot | `91F745A47AD0E00B73DFE98E4C589702F106CB2D49D5CE81DCB8ED45FA718077` |
| V7 final snapshot | `8339884595B32B9DCD60E19293F51CCB8596CB9DD2EE96331D26C9DC9E94914A` |
| V8 exchange-calendar experiment | `3D319D0A6ED320B4F07F2D8E972F2DBF9759F4325D6234333EA6B6074702D7A9` |
| V8 canonical final snapshot | `6183E16C353D57421101E3EA78FC98D7E1A57005489492E7DE9A1BE4614EB339` |
| V8 alternate temporary snapshot | `E90B0EF79300069E65D370B7EF6C027864BCD39683EA4131F72BF2611640A7A2` |

## Review findings

### High: V7 constructs an incoherent live candle

V7 replaces only the last daily `close` with a pre/post-market or minute quote.
It leaves that row's open, high, low, and volume unchanged. The substituted
close can therefore fall outside the stored high/low and ATR, ADX, Stochastic,
and volume can describe a different candle. V8 is the first coherent-OHLCV
implementation and should be preferred for live-session evaluation.

### High: V7 count-limit flags are ambiguous

V7 maps `--countmax`, `--countMax`, and `--max-buys` to one BUY-count limit and
defaults it to five. `--countmax` therefore does not cap tickers and a normal
run can stop after five BUYs. Canonical V8 resolves this by separating
`--countmax` from `--max-buys` and defaulting both limits to disabled.

### High: V7 and V8 backtest drawdown is not chronological

The backtest sorts trades by return before calculating the summary. Drawdown is
therefore calculated on best-to-worst returns rather than entry-date order.
The equity curve also starts after the first return instead of at initial
equity, so an initial losing trade can report zero drawdown. Treat
`max_drawdown_pct` as invalid in both snapshots.

### Medium: V8 can include a partial Friday weekly candle

V8 drops the current resampled week when the latest daily date is before the
Friday label. On Friday, the dates are equal, so an intraday Friday candle is
retained even though the code promises completed weeks. The weekly gate can
therefore move during Friday's live session.

### Medium: empty backtests can leave stale output

Both versions write a backtest CSV only when at least one trade exists. A
zero-trade rerun does not create or truncate the requested output even though
the CLI reports that results were written.

### Medium: report-write failures return success

Both command-line programs catch output/report exceptions, print an error, and
then finish without a nonzero exit status. Schedulers cannot reliably detect a
failed artifact write.

### Medium: multi-date final totals mix scopes

For multi-date validation, the post-execution counts come from the final date
while BUY symbols and signal breakups are selected from all accumulated dates.
The resulting final report combines last-run and all-run scopes.

### Variant disposition

The exchange-calendar V8 experiment imports `exchange_calendars`, which is not
part of the project dependency set and is not installed in the reviewed
environment. It is archived for lineage only. The `v8-tmp` file retains the V7
combined count-limit behavior and lacks automatic session selection; it is also
archived rather than promoted.

## Validation

The deterministic baseline suite covers:

- import and syntax viability for canonical V7 and V8;
- preset-copy isolation and date-list normalization;
- V8 Eastern-time market phase boundaries;
- V8 Eastern-date minute filtering;
- coherent V8 intraday OHLCV aggregation;
- completed-week exclusion before Friday;
- executable expected-failure coverage for the two confirmed calculation
  defects (initial-loss drawdown and live-Friday weekly inclusion).

Run it with:

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

This is a reviewed historical baseline, not an operational approval of the
known-defect paths above.
