# V15 Beta and Alpha Handover and Owner Sign-off

Document date: 2026-07-28

Document status: **READY FOR OWNER SIGN-OFF**

Activation status: V15 remains a non-binding shadow engine

## 1. Handover identity

| Item | Value |
|---|---|
| Repository | `https://github.com/gigabouy2004-afk/LiveScreener` |
| Authoritative local Git repository | `D:\Tools\07_LiveScanner\LiveScreener` |
| Parent execution folder | `D:\Tools\07_LiveScanner` |
| Branch | `feat/v15-momentum-quality-shadow` |
| Implementation commit | `d79ba6abc8412a7bcc01c55d852c89c5833b8fef` |
| V15 engine | `Live_Scanner_v15.py` |
| Repository V15 SHA-256 | `0EF1AA99BA7C2801CA47A92F99FC2085F177F14388B7A17C6DC0CD13F262A4D2` |
| Parent-folder V15 SHA-256 | `0EF1AA99BA7C2801CA47A92F99FC2085F177F14388B7A17C6DC0CD13F262A4D2` |
| Implementation commit on GitHub | Confirmed |
| V14 files changed | No |
| Merge to `main` | Not requested and not performed |
| Production activation | Not requested and not performed |

The repository V15 file and the parent-folder execution copy are
byte-identical.

## 2. Delivered scope

The accepted implementation boundary is V15 only:

1. live equity rows report Beta;
2. live ETF rows report Beta and three-year Alpha;
3. equity Alpha is intentionally blank;
4. Beta and Alpha appear together directly after Price and Currency;
5. the `Details` worksheet freezes after Alpha; and
6. historical/as-of rows leave both fields blank to avoid current-data
   look-ahead.

No V14 source file, V14 rule, status, classification, signal, or workbook
contract was changed.

## 3. Output contract

The leading `Details` worksheet schema is:

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

The freeze pane is `L2`. This retains the header row and columns A through K
while scrolling. Price, Beta, and Alpha use the `0.00` numeric display format.

## 4. Data and safety behavior

- ETF values are selected from the provider's three-year risk statistics.
- Equity Beta uses the provider's default key statistic.
- Provider info fields are a fallback when the preferred statistic is absent.
- Unsupported instruments, malformed values, and provider failures return
  blanks without failing the ticker scan.
- ETF Alpha is a provider-supplied percentage-point value; the scanner does not
  calculate it.
- Beta and Alpha are descriptive only. They do not affect operational or shadow
  classification.
- Current provider risk values are never added to historical/as-of rows.

## 5. Validation evidence

Detailed evidence is recorded in
`docs/VALIDATION_V15_BETA_ALPHA_2026-07-28.md`.

| Check | Result |
|---|---|
| V15 syntax compilation | PASS |
| Complete automated suite | 49/49 PASS |
| New focused tests | 5/5 PASS |
| Patch whitespace check | PASS |
| Live AAPL equity contract | Beta populated; Alpha blank |
| Live SPY ETF contract | Beta and Alpha populated |
| Historical AAPL/SPY contract | Beta and Alpha blank |
| Workbook schema | Price H, Currency I, Beta J, Alpha K |
| Freeze pane | `L2` |
| Workbook formula-error scan | No errors |
| Excel visual inspection | PASS |
| Repository/parent copy hash match | PASS |
| GitHub implementation sync | PASS |

The live values recorded during validation are time-specific provider
observations and are not fixed expected market values.

## 6. Documentation set

- `README.md` - operator-facing V15 behavior and workbook navigation.
- `CHANGELOG.md` - delivered feature and safety boundary.
- `docs/ENGINE_V15_SHADOW.md` - engine contract, data behavior, and activation
  safeguards.
- `docs/VALIDATION_V15_BETA_ALPHA_2026-07-28.md` - repeatable test and smoke
  evidence.
- `docs/HANDOVER_V14_TO_V15_AND_APPROVAL_2026-07-27.md` - preceding V14-to-V15
  shadow baseline and approval boundary.
- this document - final Beta/Alpha sign-off checklist, risks, and runbook.

## 7. Known limitations and operational risks

1. Beta and Alpha are provider fields. Coverage and calculation methodology can
   vary by listing and provider.
2. The preferred lookup uses the provider endpoint through yfinance's data
   client. A future yfinance or provider schema change may cause blank fields
   until the adapter is updated.
3. The additional live lookup adds provider requests per supported listing.
   Large runs should be monitored for rate limiting and runtime impact.
4. Missing values are deliberately blank; they are not replaced with zero.
5. No scanner-owned benchmark mapping or Alpha calculation has been added.
6. V15 thresholds remain experimental and non-binding. This handover does not
   approve classification activation.

## 8. Operator runbook

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Run a live V15 scan:

```powershell
python .\Live_Scanner_v15.py `
  -i "D:\path\watchlist.csv" `
  --live-candle-mode completed `
  -o "D:\path\v15-shadow-output.xlsx"
```

Repeat the local regression:

```powershell
python -m py_compile .\Live_Scanner_v15.py
python -m unittest discover -s tests -p 'test_*.py' -v
git diff --check
```

Verify synchronization:

```powershell
git fetch origin
git status --short --branch
git rev-parse HEAD
git ls-remote --heads origin feat/v15-momentum-quality-shadow
Get-FileHash -Algorithm SHA256 .\Live_Scanner_v15.py
Get-FileHash -Algorithm SHA256 ..\Live_Scanner_v15.py
```

## 9. Rollback boundary

If the owner rejects this addition before any later V15 work is applied, create
a normal Git revert of implementation commit
`d79ba6abc8412a7bcc01c55d852c89c5833b8fef`, validate the suite, and then
replace the parent-folder V15 execution copy with the reverted repository copy.

Do not roll back V14 files: they were not part of this change.

## 10. Sign-off checklist

- [x] Change is confined to V15.
- [x] Equity Beta behavior is implemented and tested.
- [x] ETF Beta and Alpha behavior is implemented and tested.
- [x] Equity Alpha remains blank.
- [x] Column position and freeze-pane behavior match the request.
- [x] Historical look-ahead is prevented.
- [x] Full regression and workbook checks pass.
- [x] Root and repository V15 files match.
- [x] Implementation commit is synchronized to GitHub.
- [x] Temporary validation artifacts are removed.
- [ ] Owner accepts the V15 Beta/Alpha handover.
- [ ] Any future merge to `main` is separately authorized.
- [ ] Any future V15 classification activation is separately authorized.

Owner decision: ____________________________________

Owner/name: _______________________________________

Date: _____________________________________________

Comments or conditions: ___________________________

## 11. Handover conclusion

The V15 Beta/Alpha addition is implemented, validated, documented, locally
synchronized, and present on the GitHub feature branch. It is ready for owner
sign-off. The engine remains in shadow mode, and no merge or production
activation is implied by acceptance of this handover.
