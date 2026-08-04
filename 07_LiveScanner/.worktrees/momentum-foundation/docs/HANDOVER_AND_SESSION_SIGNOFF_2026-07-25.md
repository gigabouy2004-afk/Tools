# V14 Enhanced Handover and Session Signoff — 2026-07-25

## 1. Handover identity

| Item | Value |
|---|---|
| Repository | `https://github.com/gigabouy2004-afk/LiveScreener` |
| Branch | `main` |
| Reference engine | `Live_Scanner_v14.py` |
| Development baseline | `Live_Scanner_v14_Enhanced.py` |
| Release date | 2026-07-25 |
| Release commit | The commit containing this signoff document |

## 2. Source integrity

The repository copies were verified byte-for-byte against the working copies in
`D:\Tools\07_LiveScanner`.

| File | SHA-256 |
|---|---|
| `Live_Scanner_v14.py` | `489A1BEA189CC050CEDB456BD0A133A83F825C848F262910F2811D58E7E69116` |
| `Live_Scanner_v14_Enhanced.py` | `2B4CFCAAD473664069AAC97BB465774BFFCF13DBA8FDE24B2F1A57AB50256230` |

The original V14 file was not modified.

## 3. Delivered scope

### 3.1 Execution

- Independent per-ticker evaluation.
- Complete concurrent polls.
- Deterministic input-order retention.
- Poll-boundary Max-Count and Max-Buys triggers.
- No task cancellation or exact output truncation.
- In-process historical-data caching.

### 3.2 Signal logic

- Daily and completed-weekly trend alignment.
- Momentum Continuation and Early Momentum paths.
- Pullback recovery paths retained.
- RSI and ADX upper caps replaced by stock-specific historical context.
- ADX relative-to-prior-maximum confidence reporting.
- Previous-positive-session stochastic relaxation after BUY detection.
- Volume participation included in momentum qualification.

### 3.3 History

- Fixed one-year context for classification.
- Adaptive MAX/5Y/1Y advisory guidance selected from the full input count.
- Current candle excluded from prior-history extrema.
- Classification invariant to guidance scope.

### 3.4 International operation

- Exchange-local session profiles.
- Listing-currency output.
- No U.S.-index or universe-relative dependency.
- No implicit USD restriction in signal calculations.

### 3.5 Documentation

- Repository README.
- Complete engine/operator guide.
- Validation and independent live-feed audit report.
- Changelog.
- Requirements and ignore rules.
- This restart and signoff document.

## 4. Validation completed

| Check | Status |
|---|---|
| Python syntax | PASS |
| CLI help | PASS |
| Guidance boundaries at 100/101 and 1000/1001 | PASS |
| Current candle excluded from historical guidance | PASS |
| MAX/5Y/1Y classification invariance | PASS |
| Poll-boundary extra-result retention | PASS |
| XLI 2026-07-22 to 2026-07-24 regression | PASS |
| 19-symbol independent fresh-data audit | PASS |
| 3,636-symbol full-U.S. scan completion | PASS |
| Original V14 preserved | PASS |

## 5. Accepted current behavior

The following behavior is deliberate and should not be changed without an owner
decision:

- the scanner is a baseline status check, not a universe-aware ranker;
- false positives are permitted because offline V&V follows;
- RSI and ADX do not have universal upper rejection limits;
- historical guidance is ticker-specific and advisory;
- polling does not affect classification; and
- final-poll extras are retained.

## 6. Open decisions

### P1 — Volume support floor

Current behavior allows one-year volume percentile to qualify participation even
when the current volume ratio is below 0.60.

Decision required: approve or reject a mandatory 0.60 current-volume floor.

### P1 — Minimum liquidity

No minimum average daily turnover is enforced.

Decision required:

- U.S. threshold, proposed starting point USD 1 million ADV20 turnover;
- international FX normalization; or
- explicit exchange/currency-specific thresholds.

### P1 — Extreme momentum labeling

Highly extended signals can remain BUY.

Decision required: approve or reject `BUY_EXTENDED_REVIEW` for candidates beyond
5 ATR from EMA50.

### P2 — Data-through summary

Run-level `AsOf` can be a weekend/holiday.

Decision required: add a prominent `DataThrough` field derived from the included
session date.

### P2 — Low-liquidity feed-quality flag

Sparse Yahoo daily data can disagree with minute/quote data.

Decision required: define the zero-volume and daily/intraday disagreement
thresholds that should create a warning.

## 7. Operator runbook

### 7.1 Environment check

```powershell
python --version
python -m pip install -r requirements.txt
python -m py_compile .\Live_Scanner_v14.py
python -m py_compile .\Live_Scanner_v14_Enhanced.py
```

### 7.2 Full watchlist

```powershell
python .\Live_Scanner_v14_Enhanced.py `
  -i "D:\path\watchlist.csv" `
  -o "D:\path\scan-output.xlsx" `
  --workers 3
```

With no Max-Count or Max-Buys, every ticker is processed.

### 7.3 Bounded continuation

```powershell
python .\Live_Scanner_v14_Enhanced.py `
  -i "D:\path\watchlist.csv" `
  -o "D:\path\scan-output.xlsx" `
  --workers 3 `
  --max-buys 20
```

The scanner completes the poll that reaches 20 BUYs and retains all extras.

### 7.4 Historical replay

```powershell
python .\Live_Scanner_v14_Enhanced.py `
  -c CAT GE RTX UNP DE `
  --as-of-dates 2026-07-22,2026-07-23,2026-07-24 `
  --live-candle-mode completed `
  -o "D:\path\historical-validation.xlsx"
```

### 7.5 Output review order

1. Confirm `session_date`, `candle_state`, and `data_note`.
2. Review `status`, `output_signal`, and `reason`.
3. Review `volume_ratio`, `volume_1y_percentile`, and
   `average_daily_turnover_20`.
4. Review `ema50_distance_atr`, RSI/stochastic percentile, and `risk_level`.
5. Review adaptive guidance scope and sessions.
6. Perform offline end-user V&V before action.

## 8. Restart instructions

On the next session:

1. Read `README.md`.
2. Read `docs/ENGINE_V14_ENHANCED.md`.
3. Read `docs/VALIDATION_2026-07-25.md`.
4. Read this signoff.
5. Confirm local `main` equals `origin/main`.
6. Resolve the P1 liquidity and extension decisions before modifying
   classification.
7. Re-run the XLI regression and the 19-symbol audit after any logic change.

## 9. Session closure statement

Development, validation, documentation, and repository handover for the
2026-07-25 V14 Enhanced session are complete.

Engineering signoff:

- code state: complete;
- reproducibility: passed;
- documentation: complete;
- repository synchronization: complete when this release commit is present on
  both local `main` and `origin/main`;
- known limitations: documented;
- production signal-quality approval: conditional on the P1 owner decisions.

This is a clean session boundary. Future work should begin from the synchronized
release commit, not from an untracked copy or an earlier scanner version.
