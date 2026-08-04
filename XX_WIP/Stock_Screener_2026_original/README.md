# Stock Screener

A MACD-based stock screener for Pre-Bull, Pre-Bear, Bull Extended, and setup candidates.

## Setup

1. Create a Python environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Universe file

Provide a CSV file with symbols in column A. The first cell can be `Symbol`, or the file can be a simple no-header ticker list. Optional columns are `Exchange`, `Sector`, and `Industry`.

Example:

```csv
Symbol,Exchange,Sector,Industry
AAPL,NASDAQ,Technology,Consumer Electronics
AMD,NASDAQ,Technology,Semiconductors
MSFT,NASDAQ,Technology,Software
NVDA,NASDAQ,Technology,Semiconductors
```

## Run

Browser form:

```bash
python web_app.py
```

On Windows you can also double-click `start_web_app.bat`.

Open `http://127.0.0.1:8000` and choose a local symbols CSV or use the default `clean_universe.csv` USA universe. Exchange, Sector, and Industry are multi-select filters. Price, Market Cap, Average Volume, RSI, ADX, and Bollinger %b filters are optional; blank values are ignored. `Max Symbols` defaults to `50` so test runs return quickly; clear it to run the full universe. The results table appears on the page, and the app also writes `screener_output.csv` plus a standalone `screener_report.html` report file.

Command-line run:

```bash
python stock_screener.py --symbols-file symbols.csv --output-file screener_output.csv --exchange NASDAQ --sector Technology --price-min 5 --price-max 200 --rsi-max 75 --adx-min 20 --states PRE_BULL_CROSSOVER,BULL_EXTENDED
```

## Supported filters

- Exchange
- Sector
- Industry
- Price range
- Market cap
- Average daily volume
- RSI value
- ADX value
- Bollinger %b
- Candidate states

## Output

The script writes a CSV containing only symbols that pass the configured filters and match an engine candidate state. Key columns:

- `CandidateState`
- `AppliedFilters`
- `MarketCap`, `AvgDailyVolume`, `AvgMonthlyVolume`
- `RSI_1D`
- `WeightedScore`, `MACDScore`, `RSIScore`, `ADXScore`
- `MACD_1D_State`, `MACD_4H_State`, `MACD_1H_State`
- `MACD_1H_Crossover`, `MACD_Flow_State`, `MACD_Flow_Reason`
- `RawDivergence_1H`, `RawDivergence_4H`, `RawDivergence_1D`, `ConfirmedDivergence`
- `ADX_1D`
- `Bollinger_PctB`
- `PriceLadder_Passed`
- `SetupPassed`

## Notes

This screener is built from the PMDE architecture and focuses on:

- MACD crossover and state assessment
- Weighted scoring from MACD, RSI, and ADX
- MACD setup progression
- Bottom-up MACD crossover and divergence flow from 1H to 4H to 1D
- Pre-bull and pre-bear candidate identification
- Flexible filter criteria
