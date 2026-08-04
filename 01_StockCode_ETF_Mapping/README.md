# Stock Code ETF Mapping

`Stock_Code_ETF_Mapping_v5.py` builds a stock-to-ETF coverage matrix. It accepts a seed stock universe and an ETF universe, scans ETF holdings through Yahoo Finance/yfinance paths, and writes a CSV showing which ETFs hold each seed stock and at what allocation weight.

## What It Produces

The output CSV starts with an execution summary, followed by the mapping matrix:

```text
Stock Code, Company Name, LTP, Total ETF Count, <ETF columns...>
Stock# in this ETF, , , , <count per ETF>
ETF Full Name, , , , <ETF full names>
<seed stock>, <company name>, <last price>, <ETF count>, <holding weights...>
```

Stock rows are sorted by `Total ETF Count`, so the most widely covered seed stocks appear first.

## Input Precedence

Seed stock inputs and ETF inputs are resolved independently.

Seed stocks:

1. `--seed_codes` / `-c`: explicit comma-separated stock codes.
2. `--seed_file` / `-f`: CSV file where the first column contains stock codes.
3. `DEFAULT_SEED_FILE_PATH`: used only when no seed CLI input is supplied.
4. Failure: invalid explicit CLI seed input fails the engine.

ETF universe:

1. `--etf_codes`: explicit comma-separated ETF codes.
2. `--etf_master` / `-e`: CSV file where the first column contains ETF codes.
3. `DEFAULT_ETF_MASTER_PATH`: used only when no ETF CLI input is supplied.
4. Failure: invalid explicit CLI ETF input fails the engine.

## CSV Handling

- Only the first column is used for code extraction.
- CSV files may have a header row or no header row.
- Codes are normalized, deduplicated, and validated.
- `XNSE:` symbols are converted to Yahoo Finance `.NS` symbols.
- Name enrichment is header-aware. Recognized name columns include `Security Name`, `Company Name`, `Name`, `Fund Name`, and `ETF Name`.
- Large mixed-type files are read as strings on only the required columns to avoid pandas `DtypeWarning` noise.

## Name Enrichment

Seed company names are loaded from `--stock_master` or `DEFAULT_STOCK_MASTER_PATH`, then overridden by names in `--seed_file` if the seed file has a recognized name column.

ETF full names are loaded from the selected ETF master file when it has a recognized name column such as `Security Name`.

Yahoo name lookup is disabled by default to avoid extra network calls for large universes. Use `--name_lookup yfinance` to fill missing local names through yfinance.

## Examples

```powershell
python .\Stock_Code_ETF_Mapping_v5.py -f D:\Tools\StockCodeMaster\02_Stock\Momentum\4-7-2026.csv --output D:\TMP\MomentumStock_ETFMapping_4-7-2026.csv
```

```powershell
python .\Stock_Code_ETF_Mapping_v5.py -c MU,TSLA --etf_codes SPY,QQQ --output D:\TMP\quick-map.csv
```

```powershell
python .\Stock_Code_ETF_Mapping_v5.py -f seeds.csv -e etfs.csv --stock_master stocks.csv --name_lookup local
```

Run the built-in reference:

```powershell
python .\Stock_Code_ETF_Mapping_v5.py -?
```

## Dependencies

Install dependencies with:

```powershell
pip install -r requirements.txt
```

