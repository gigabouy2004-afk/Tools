# V15 Beta and Alpha Validation - 2026-07-28

## Scope

This validation covers the V15-only addition of:

- Beta for live equity and ETF rows;
- three-year Alpha for live ETF rows;
- intentionally blank Alpha for equity rows;
- placement directly after Price and Currency; and
- a worksheet freeze boundary after Alpha.

The V14 reference and V14 Enhanced files are outside this change and remain
unchanged. V15 remains a non-binding shadow engine.

## Build identity

| Item | Value |
|---|---|
| Repository | `https://github.com/gigabouy2004-afk/LiveScreener` |
| Branch | `feat/v15-momentum-quality-shadow` |
| Starting branch commit | `119364ce5ba5d37986797d18f81399545fbc5766` |
| Repository V15 SHA-256 | `0EF1AA99BA7C2801CA47A92F99FC2085F177F14388B7A17C6DC0CD13F262A4D2` |
| Parent-folder V15 SHA-256 | `0EF1AA99BA7C2801CA47A92F99FC2085F177F14388B7A17C6DC0CD13F262A4D2` |

The parent-folder execution copy and the Git repository copy are byte-identical.

## Data contract

| Instrument/run | Beta | Alpha |
|---|---|---|
| Live equity | Provider Beta | Blank |
| Live ETF | Provider three-year Beta | Provider three-year Alpha |
| Historical/as-of equity or ETF | Blank | Blank |
| Unsupported instrument or unavailable provider value | Blank | Blank |

Provider lookup errors are non-fatal. Beta and Alpha are descriptive fields and
do not affect `status`, `classification`, `output_signal`, momentum score,
entry state, or shadow recommendation.

## Automated validation

Commands:

```powershell
python -m py_compile .\Live_Scanner_v15.py
python -m unittest discover -s tests -p 'test_*.py' -v
git diff --check
```

Results:

| Check | Result |
|---|---|
| V15 syntax compilation | PASS |
| Complete regression suite | 49/49 PASS |
| New Beta/Alpha tests | 5/5 PASS |
| Patch whitespace check | PASS |
| V14 file diff | No changes |

The focused tests cover:

- exact selection and rounding of the ETF three-year statistics row;
- equity Beta with intentionally blank Alpha;
- ETF Beta and Alpha;
- safe blank values when provider values are unavailable; and
- `Details` worksheet freeze, formats, and column widths.

## Live provider smoke validation

Command:

```powershell
python .\Live_Scanner_v15.py `
  -c AAPL SPY `
  --live-candle-mode completed `
  -o .\output\v15_beta_alpha_signoff.xlsx
```

The run completed on 2026-07-28 with data through 2026-07-27 and no ticker
errors.

| Ticker | Instrument | Price | Currency | Beta | Alpha |
|---|---|---:|---|---:|---:|
| AAPL | Equity | 336.91 | USD | 1.10 | Blank |
| SPY | ETF | 739.09 | USD | 1.00 | -0.09 |

These are time-specific provider observations used only to verify the output
contract; they are not permanent reference values.

## Historical look-ahead check

The same symbols were run with `--as-of-dates 2026-07-24`. Both Beta and Alpha
were blank for both rows, confirming that current provider statistics are not
inserted into historical/as-of output.

## Workbook validation

The live and historical workbooks both produced this leading `Details` schema:

| Column | Header |
|---|---|
| A | Ticker |
| B | engine_version |
| C | v15_shadow_mode |
| D | v15_classification_active |
| E | Message |
| F | Reason |
| G | Company Name |
| H | Price |
| I | Currency |
| J | Beta |
| K | Alpha |

Checks:

- freeze pane: `L2`;
- frozen area: header row and columns A through K;
- Price, Beta, and Alpha numeric format: `0.00`;
- no formula-error strings in either workbook; and
- Excel visual preview confirmed readable leading columns without clipping.

Temporary smoke workbooks, logs, and preview files were removed after evidence
was recorded.

## Sign-off conclusion

The V15 Beta/Alpha addition satisfies the requested stock/ETF behavior,
position, and freeze-pane contract. The change is ready for owner sign-off on
the V15 feature branch. It does not authorize a merge to `main` or production
activation.
