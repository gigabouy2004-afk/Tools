# CLI Reference

## Usage

```text
python Stock_Code_ETF_Mapping_v5.py [-h] [-e ETF_MASTER]
                                    [-etf_codes ETF_CODES] [-f SEED_FILE]
                                    [-c SEED_CODES]
                                    [--stock_master STOCK_MASTER]
                                    [--name_lookup {local,yfinance}]
                                    [-w MIN_WEIGHT] [-o OUTPUT]
```

## Arguments

`-h`, `-?`, `--help`

Shows the built-in engine documentation and exits.

`-e`, `--etf_master`, `-etf_master ETF_MASTER`

CSV path for the ETF universe. The first column is read as ETF code. If this explicit CLI file is invalid or empty, the engine fails instead of falling back to the default ETF path.

`-etf_codes`, `--etf_codes ETF_CODES`

Comma-separated ETF list, for example `SPY,QQQ`. Takes precedence over `--etf_master`.

`-f`, `--seed_file`, `-seed_file SEED_FILE`

CSV path for seed stocks. The first column is read as stock code. If this explicit CLI file is invalid or empty, the engine fails instead of falling back to the default seed path.

`-c`, `--seed_codes`, `-seed_codes SEED_CODES`

Comma-separated seed stock list, for example `MU,TSLA,XNSE:TCS`. Takes precedence over `--seed_file`.

`--stock_master`, `-stock_master STOCK_MASTER`

Optional local stock master CSV used to enrich seed company names. This file should contain a code column in the first column and a recognized name column such as `Security Name` or `Company Name`.

`--name_lookup {local,yfinance}`

Controls display-name fallback behavior.

- `local`: default. Uses only local CSV sources for names.
- `yfinance`: fills missing names with yfinance lookups.

`-w`, `--min_weight`, `-min_weight MIN_WEIGHT`

Minimum holding allocation threshold. Default is `0.0`.

`-o`, `--output`, `-output OUTPUT`

Output CSV path. Parent directories are created when needed.

## Engine Behavior

The engine resolves seed stocks and ETFs independently. Explicit CLI inputs take precedence. Defaults are used only when the corresponding CLI input is absent. Invalid explicit CLI input fails the engine and prints an execution snapshot.

The output summary records selected sources, source status, source counts, locally resolved name counts, total seed codes read, total ETFs processed, matched seed count, matched ETF count, and output filename.

