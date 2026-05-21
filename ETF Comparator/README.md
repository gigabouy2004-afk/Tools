# ETF Comparator

Python scripts for comparing ETF performance and fundamentals using yfinance.

## Current Version

Use `ETF_ComparatorTool_v7.py` for the latest working version.

Older file-name-based versions are kept in `Archive/` for reference.

## Usage

Run with tickers from the configured input file:

```powershell
python ETF_ComparatorTool_v7.py
```

Run with additional comma-separated terminal tickers:

```powershell
python ETF_ComparatorTool_v7.py --tickers SMH,SOXX,XLK
```

If the configured input file is missing but `--tickers` is supplied, the script will continue with the terminal tickers.

Build or refresh the classification mapping file with the standalone mapper:

```powershell
python ETF_ClassificationMapper.py
```

For other ETF master files, pass the file and column names:

```powershell
python ETF_ClassificationMapper.py --input-file "D:\path\to\NSE_ETF_Master.csv" --output-file "D:\Tools\ETF_Comparator\INPUT\NSE_ETF_Classification_Mapping.csv" --ticker-column Symbol --name-column "Security Name" --default-geography India
```

Run by classification instead of changing input/output filenames:

```powershell
python ETF_ComparatorTool_v7.py --classification Semiconductor
python ETF_ComparatorTool_v7.py --classification Bitcoin
python ETF_ComparatorTool_v7.py --classification "South Korea"
python ETF_ComparatorTool_v7.py --classification "Dividend/Income"
```

Classification filters match the generated mapping columns: `Asset Class`, `Strategy`, `Theme`, `Geography`, `Category Flags`, and `Security Name`.

## Dependencies

- pandas
- yfinance
- openpyxl
