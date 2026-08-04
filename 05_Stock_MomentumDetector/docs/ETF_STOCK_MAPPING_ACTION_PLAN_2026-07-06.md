# ETF-Stock Mapping Engine Action Plan

> **V8 live-workflow status — 2026-07-11:** This older plan remains background for offline StockCodeMaster and ETF Comparator mapping. Its pan-ETF Yahoo/yfinance extraction approach is explicitly prohibited inside the live V8 Momentum Detector. V8 uses the separate direct stock-specific design documented in `V8_DEVELOPMENT_CHARTER_2026-07-10.md` and `V8_CURRENT_OUTPUT_CONTRACT_2026-07-10.md`.

Date: 2026-07-06

## Objective

Enhance `D:\Tools\StockCodeMaster` from a ticker and ETF information extractor into a local ETF-stock mapping database.

The final intent is to connect three workflows:

1. `StockCodeMaster` creates and refreshes master ticker, ETF, and ETF-holding reference data.
2. `Momentum_Detector_V5.py` / `Momentum_Detector_V6.py` use that reference data to show which ETFs may be impacted by a momentum stock.
3. `D:\Tools\ETF_Comparator` identifies outperforming ETFs, then maps those ETFs back to their holdings so the underlying stocks can be checked by Momentum Detector for fresh or continuing momentum.

The target workflow must support both directions:

- Stock to ETF: if a stock/ticker is showing momentum, identify ETFs where that stock has meaningful weight.
- ETF to Stock: if an ETF is surging, identify which holdings may be driving the ETF move and run those stock tickers through Momentum Detector.

## Existing Folder Roles

### `D:\Tools\StockCodeMaster`

Current role:

- Extracts NYSE/NASDAQ/NSE tickers.
- Separates common stocks from ETFs.
- Builds US/NSE stock master files.
- Builds US/NSE ETF master and classification files.
- Has partial ETF top-holdings enrichment logic in the latest master extraction script.

Important current script:

```text
D:\Tools\StockCodeMaster\00_Script\001_GetNYSE_NASDAQ_Code_v6.py
```

Important current files:

```text
D:\Tools\StockCodeMaster\01_MASTER\01-07-NYSE_NASDAQ_NSE_Master_Library.csv
D:\Tools\StockCodeMaster\01_MASTER\01-07-Master_Ticker_List_Base.csv
D:\Tools\StockCodeMaster\02_Stock\01-07-US_Common_Stocks_Master_Library.csv
D:\Tools\StockCodeMaster\02_Stock\01-07-US_Common_Stocks_Master_Library-Filtered_Technology.csv
D:\Tools\StockCodeMaster\02_Stock\01-07-NSE_Common_Stocks_Master_Library.csv
D:\Tools\StockCodeMaster\03_ETF\01-07-US_ETF_Master_Library.csv
D:\Tools\StockCodeMaster\03_ETF\01-07-US_ETF_Classification_Mapping.csv
D:\Tools\StockCodeMaster\03_ETF\01-07-NSE_ETF_Master_Library.csv
D:\Tools\StockCodeMaster\03_ETF\01-07-NSE_ETF_Classification_Mapping.csv
```

Existing momentum mapping artifacts:

```text
D:\Tools\StockCodeMaster\02_Stock\Momentum\04-07-2026\MomentumStock_ETFMapping_4-7-2026.csv
D:\Tools\StockCodeMaster\02_Stock\Momentum\04-07-2026\MomentumStock_ETFMapping_4-7-2026-ETF-Filtered.csv
```

### `D:\Tools\Stock_MomentumDetector`

Current role:

- Runs momentum classification for stock tickers.
- Produces V5/V6 CSV outputs.
- V6 includes additional analyst/external-message fields.

Future role:

- Read ETF-stock mapping outputs as reference data.
- Add ETF impact context to stock momentum output.
- Accept ETF-derived holding ticker lists produced by ETF Comparator workflows.

Important scripts:

```text
D:\Tools\Stock_MomentumDetector\Momentum_Detector_V5.py
D:\Tools\Stock_MomentumDetector\Momentum_Detector_V6.py
```

### `D:\Tools\ETF_Comparator`

Current role:

- Compares performance of multiple ETFs and generates Excel reports.
- Has input ETF code lists and output comparison reports.

Important current script:

```text
D:\Tools\ETF_Comparator\ETF_ComparatorTool_v9.py
```

Important folders:

```text
D:\Tools\ETF_Comparator\INPUT
D:\Tools\ETF_Comparator\OUTPUT
```

Future role:

- Identify outperforming ETFs from comparison reports.
- Use ETF-stock mapping to extract holdings for selected outperforming ETFs.
- Create a stock ticker list from those holdings.
- Feed that stock list into Momentum Detector to check whether any holdings still have fresh momentum potential.

## Proposed New Mapping Folder

Create a dedicated local output area:

```text
D:\Tools\StockCodeMaster\04_ETF_Stock_Mapping
```

This keeps the ETF-stock mapping database separate from raw stock/ETF master extraction outputs.

Suggested subfolders:

```text
D:\Tools\StockCodeMaster\04_ETF_Stock_Mapping\CURRENT
D:\Tools\StockCodeMaster\04_ETF_Stock_Mapping\ARCHIVE
D:\Tools\StockCodeMaster\04_ETF_Stock_Mapping\LOGS
```

`CURRENT` should contain stable filenames consumed by Momentum Detector and ETF Comparator.

`ARCHIVE` should contain dated snapshots for audit/history.

## Proposed Database Tables

### `ETF_Master.csv`

Purpose:

- Clean ETF reference table.
- Built from US/NSE ETF master and classification files.

Suggested columns:

```text
ETF_Ticker
ETF_Name
Listing_Exchange
Market_Region
ETF_Asset_Class
ETF_Category
ETF_Theme
ETF_Geography
ETF_Sector
ETF_Industry
ETF_Is_Excluded
ETF_Exclusion_Reason
Data_Source
As_Of_Date
```

### `Stock_Master.csv`

Purpose:

- Clean stock reference table.
- Built from US/NSE common stock master files.

Suggested columns:

```text
Stock_Ticker
Stock_Name
Listing_Exchange
Market_Region
Sector
Industry
MarketCap
ETF_Flag
Data_Source
As_Of_Date
```

### `ETF_Holdings_Detail.csv`

Purpose:

- Core many-to-many table.
- One row per ETF-holding pair.

Suggested columns:

```text
ETF_Ticker
ETF_Name
Holding_Ticker
Holding_Name
Holding_Weight_Pct
Holding_Sector
Holding_Industry
Holding_Market_Region
Holding_MarketCap
Holding_Metadata_Source
Holdings_Source
As_Of_Date
Run_Timestamp
```

This is the key table for both stock-to-ETF and ETF-to-stock analysis.

### `Stock_To_ETF_Map.csv`

Purpose:

- Reverse lookup table.
- Answers: if stock `NVDA` is moving, which ETFs may be impacted?

Suggested columns:

```text
Holding_Ticker
Holding_Name
ETF_Ticker
ETF_Name
Holding_Weight_Pct
ETF_Asset_Class
ETF_Category
ETF_Theme
ETF_Sector
ETF_Geography
Impact_Rank
As_Of_Date
```

Initial ranking logic:

```text
Impact_Rank = rank ETFs per Holding_Ticker by Holding_Weight_Pct descending
```

### `ETF_To_Stock_Map.csv`

Purpose:

- ETF driver table.
- Answers: if ETF `SMH` is surging, which holdings may be driving the move?

Suggested columns:

```text
ETF_Ticker
ETF_Name
Holding_Ticker
Holding_Name
Holding_Weight_Pct
Holding_Sector
Holding_Industry
Driver_Rank
As_Of_Date
```

Initial ranking logic:

```text
Driver_Rank = rank holdings per ETF_Ticker by Holding_Weight_Pct descending
```

### `ETF_Impact_Summary.csv`

Purpose:

- Compact summary for fast joins into Momentum Detector output.

Suggested columns:

```text
Holding_Ticker
Mapped_ETF_Count
Top_Mapped_ETFs
Highest_ETF_Weight_Pct
Total_Known_ETF_Weight_Pct
ETF_Impact_Notes
As_Of_Date
```

Example note:

```text
NVDA maps to SMH 20.50%; SOXX 8.20%; QQQ 7.10%
```

## Phase 1: Formalize StockCodeMaster Outputs

Tasks:

1. Add `04_ETF_Stock_Mapping` folder structure.
2. Keep stable `CURRENT` output filenames for downstream tools.
3. Archive every run with timestamped filenames.
4. Add a small run manifest with source files, row counts, and run timestamp.

Expected outputs:

```text
CURRENT\ETF_Master.csv
CURRENT\Stock_Master.csv
CURRENT\ETF_Holdings_Detail.csv
CURRENT\Stock_To_ETF_Map.csv
CURRENT\ETF_To_Stock_Map.csv
CURRENT\ETF_Impact_Summary.csv
CURRENT\run_manifest.json
```

## Phase 2: Improve ETF Holdings Extraction

Starting script:

```text
D:\Tools\StockCodeMaster\00_Script\001_GetNYSE_NASDAQ_Code_v6.py
```

Existing function areas:

- `fetch_etf_top_holdings(etf_ticker)`
- `build_stock_metadata(master_df)`
- `lookup_external_holding_metadata(ticker, external_metadata_cache)`
- `complete_holding_metadata(...)`
- `enrich_etfs_with_holdings(...)`

Enhancements:

1. Keep the existing Yahoo/yfinance path.
2. Write a normalized holdings detail table even when some metadata is missing.
3. Add `As_Of_Date` and `Run_Timestamp`.
4. Track holding source and metadata source separately.
5. Mark missing holdings as `HOLDINGS_UNAVAILABLE`; do not silently drop ETFs.
6. Make the holdings extraction independently runnable without regenerating all master files when possible.

## Phase 3: Generate Reverse Mapping

From `ETF_Holdings_Detail.csv`, generate:

```text
Stock_To_ETF_Map.csv
```

Use case:

1. Momentum Detector finds a stock with momentum.
2. Lookup the stock in `Stock_To_ETF_Map.csv`.
3. Identify ETFs where the stock has meaningful weight.
4. Add ETF impact context to the stock momentum output.

Example:

```text
Stock: NVDA
Mapped ETFs: SMH, SOXX, QQQ
Interpretation: NVDA movement can materially affect semiconductor and growth ETFs where it has high weight.
```

## Phase 4: Generate ETF Driver View

From `ETF_Holdings_Detail.csv`, generate:

```text
ETF_To_Stock_Map.csv
```

Use case:

1. ETF Comparator identifies a surging ETF.
2. Lookup the ETF in `ETF_To_Stock_Map.csv`.
3. Extract top holdings by weight.
4. Run those stock tickers through Momentum Detector.
5. Determine which holdings still have fresh momentum, continuation potential, or exhaustion risk.

Example:

```text
ETF: SMH
Top holdings: NVDA, AVGO, AMD, ASML
Next step: run those holdings through Momentum_Detector_V6.py.
```

## Phase 5: Link With Momentum Detector

Initial approach:

- Keep Momentum Detector as a consumer of mapping outputs.
- Do not embed ETF holdings extraction directly into V5/V6.
- Add optional read-only enrichment from `ETF_Impact_Summary.csv` and/or `Stock_To_ETF_Map.csv`.

Potential V6 output additions for stock scans:

```text
Mapped_ETF_Count
Top_Mapped_ETFs
Highest_ETF_Weight_Pct
ETF_Impact_Notes
```

Potential V6 output additions for ETF-derived scans:

```text
ETF_Source_Ticker
ETF_Source_Name
ETF_Holding_Weight_Pct
ETF_Driver_Rank
```

Suggested CLI additions later:

```powershell
python Momentum_Detector_V6.py --tickers NVDA AMD AVGO --etf-map D:\Tools\StockCodeMaster\04_ETF_Stock_Mapping\CURRENT\Stock_To_ETF_Map.csv
```

or:

```powershell
python Momentum_Detector_V6.py --from-etf SMH --etf-holdings-map D:\Tools\StockCodeMaster\04_ETF_Stock_Mapping\CURRENT\ETF_To_Stock_Map.csv
```

## Phase 6: Link With ETF Comparator

Starting script:

```text
D:\Tools\ETF_Comparator\ETF_ComparatorTool_v9.py
```

Current ETF Comparator output:

- Produces Excel performance comparison reports for multiple ETFs.
- Outputs are under `D:\Tools\ETF_Comparator\OUTPUT`.

Future enhancement:

1. ETF Comparator ranks ETFs by performance.
2. User selects one or more ETFs from the report.
3. ETF Comparator or a helper script reads `ETF_To_Stock_Map.csv`.
4. It creates a top-holdings ticker list for those ETFs.
5. That stock ticker list is passed to Momentum Detector.
6. Momentum Detector reports whether any underlying holdings still have fresh momentum potential.

Possible helper output:

```text
D:\Tools\ETF_Comparator\OUTPUT\Selected_ETF_Holdings_For_Momentum.csv
```

Suggested columns:

```text
ETF_Ticker
ETF_Name
ETF_Performance_Rank
Holding_Ticker
Holding_Name
Holding_Weight_Pct
Driver_Rank
Include_For_Momentum_Check
```

Possible command chain:

```powershell
python D:\Tools\ETF_Comparator\ETF_ComparatorTool_v9.py --input <ETF_LIST> --output <COMPARISON_REPORT>
python D:\Tools\ETF_Comparator\Extract_ETF_Holdings_For_Momentum.py --comparison-report <COMPARISON_REPORT> --etf-map D:\Tools\StockCodeMaster\04_ETF_Stock_Mapping\CURRENT\ETF_To_Stock_Map.csv
python D:\Tools\Stock_MomentumDetector\Momentum_Detector_V6.py --ticker-csv D:\Tools\ETF_Comparator\OUTPUT\Selected_ETF_Holdings_For_Momentum.csv
```

The exact CLI should be finalized after reviewing `ETF_ComparatorTool_v9.py`.

## Phase 7: Scoring and Analysis Logic

Initial ETF-stock mapping should remain factual, not predictive.

Basic impact logic:

- Higher holding weight means higher likely ETF sensitivity to that stock.
- Multiple ETFs holding the same stock increases market relevance.
- Sector/theme overlap can explain why several ETFs move together.

Potential later metrics:

```text
ETF_Impact_Score = Holding_Weight_Pct * Stock_Momentum_Score
ETF_Driver_Score = Holding_Weight_Pct * Stock_Return_Recent
Theme_Confirmation_Count = count of mapped ETFs also showing strength
```

These should be added only after the base mapping is reliable.

## Phase 8: Data Quality Rules

Required handling:

1. Normalize tickers consistently between tools.
2. Preserve `.NS` for NSE tickers.
3. Track unmapped holdings as `External / Unmapped`.
4. Do not delete ETFs simply because holdings are unavailable.
5. Separate ETF metadata source from holding metadata source.
6. Store run date and source path in each output.
7. Keep stable `CURRENT` files and dated `ARCHIVE` snapshots.

Known limitations:

- Yahoo/yfinance holdings data may be missing or incomplete for some ETFs.
- Some ETF holdings may be non-US or non-NSE securities.
- Some holdings may be cash, futures, swaps, bonds, or index instruments.
- Holding weights may not be current intraday; they are usually latest published portfolio weights.
- ETF price movement can be affected by flows, premiums/discounts, currency, and futures, not only holdings.

## Recommended Implementation Order

1. Create the `04_ETF_Stock_Mapping` folder and stable output contract.
2. Refactor `001_GetNYSE_NASDAQ_Code_v6.py` to produce clean current/archive ETF holdings detail outputs.
3. Generate `Stock_To_ETF_Map.csv`.
4. Generate `ETF_To_Stock_Map.csv`.
5. Generate `ETF_Impact_Summary.csv`.
6. Add a lightweight validation script for row counts, missing tickers, duplicate keys, and empty holdings.
7. Add V6 read-only enrichment from `ETF_Impact_Summary.csv`.
8. Add an ETF Comparator helper to export ETF top holdings selected for momentum analysis.
9. Wire ETF Comparator output into Momentum Detector ticker input.

## First New-Session Task

Start with:

```text
D:\Tools\StockCodeMaster\00_Script\001_GetNYSE_NASDAQ_Code_v6.py
```

Target first deliverable:

```text
D:\Tools\StockCodeMaster\04_ETF_Stock_Mapping\CURRENT\ETF_Holdings_Detail.csv
D:\Tools\StockCodeMaster\04_ETF_Stock_Mapping\CURRENT\Stock_To_ETF_Map.csv
D:\Tools\StockCodeMaster\04_ETF_Stock_Mapping\CURRENT\ETF_To_Stock_Map.csv
```

After that is stable, connect the outputs to:

```text
D:\Tools\Stock_MomentumDetector\Momentum_Detector_V6.py
D:\Tools\ETF_Comparator\ETF_ComparatorTool_v9.py
```
