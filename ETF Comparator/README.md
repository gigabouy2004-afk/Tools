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

## Dependencies

- pandas
- yfinance
- openpyxl
