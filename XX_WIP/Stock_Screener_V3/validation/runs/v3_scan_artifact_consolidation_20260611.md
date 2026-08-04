# V3 Scan Artifact Consolidation

Date written: 2026-06-11

## Purpose

Close the remaining untracked validation artifacts before moving implementation focus to the `DIVERGENCE` stage family.

The remaining untracked files were not source-code changes. They were Crossover scan summary markdown files plus local web-app upload CSVs.

## Consolidated Scan Summaries

The following summaries are preserved as validation evidence:

| Summary | D Date | Universe | Stage Family | Processed | Candidates | Density | Notes |
|---|---|---|---|---:|---:|---:|---|
| `v3_scan_20260209_summary.md` | 2026-02-09 | `data/samples/us_master_sample.csv` | `CROSSOVER` | 3 | 1 | 0.3333 | Small smoke-style run. |
| `v3_scan_20260311_summary.md` | 2026-03-11 | `data/samples/00-NYSE_NASDAQ_Common_Stocks_Sector-Technology.csv` | `CROSSOVER` | 514 | 195 | 0.3794 | Full Technology Crossover run. |
| `v3_scan_20260511_summary.md` | 2026-05-11 | `data/samples/00-NYSE_NASDAQ_Common_Stocks_Sector-Technology.csv` | `CROSSOVER` | 517 | 331 | 0.6402 | Full Technology Crossover run. |
| `v3_scan_20260609_summary.md` | 2026-06-09 | local uploaded Technology CSV | `CROSSOVER` | 100 | 22 | 0.2200 | Sample run; uploaded CSV matched tracked Technology sample by file hash. |
| `v3_scan_20260611_summary.md` | 2026-06-11 | `data/samples/00-NYSE_NASDAQ_Common_Stocks_Sector-Technology.csv` | `CROSSOVER` | 520 | 273 | 0.5250 | Full Technology Crossover run. |

## Upload Cleanup Decision

`validation/uploads/` is local web-app input/cache state and is now git-ignored.

Observed uploaded files:

- `00-NYSE_NASDAQ_Common_Stocks_Sector-Technology.csv`
- `00-NYSE_NASDAQ_Common_Stocks_Sector-Technology-Semiconductor.csv`
- `09-06-NYSE_NASDAQ_Common_Stocks_Master_Library.csv`

The first two uploaded files are duplicates of tracked files under `data/samples/`. The master-library upload remains local because broad operational input files should be promoted deliberately into a tracked input location only when they are accepted as a baseline source.

## Closure

After this consolidation:

- scan summary markdown is tracked as lightweight validation evidence;
- large detail CSV/log artifacts remain ignored under the existing validation-output policy;
- local web-app uploads are ignored;
- Crossover V1 closure remains intact;
- the next implementation path is `DIVERGENCE` validation and calibration.
