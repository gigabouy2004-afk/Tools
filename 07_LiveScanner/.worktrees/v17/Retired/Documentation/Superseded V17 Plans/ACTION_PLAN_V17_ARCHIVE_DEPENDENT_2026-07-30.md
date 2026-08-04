# V17 Continuation Action Plan

Date: 2026-07-30

Branch: `V17`

Baseline commit: `3586f24cb4e8390e66476e30f895e1a3ce3ff430`

Baseline tag: `baseline-v17-momentum-foundation-2026-07-30`

Document role: active execution plan supporting the master blueprint

Status: active; first blocking dependency is the promotion-quality daily
archive

## Governing decision

V17 is approved research infrastructure. It is not an approved
genuine-momentum classifier, production BUY rule or operational override.

The inherited daily rules are a comparison baseline only. Their five-year
reference replay had a -0.0627% gross mean return and failed the daily-rule
stability gate. Current-session 4-hour/1-hour evidence remains descriptive
until a timestamp-correct multi-year 30-minute archive supports a separate
incremental-value test.

All work must preserve the authoritative time contract:

- the previous completed session supplies the daily foundation;
- today remains the current session, including after the close;
- only completed current-session 4-hour/1-hour observations describe today;
- historical intraday observations are indicator warm-up only; and
- future outcomes are joined only after the feature record is frozen.

## Active documentation boundary

`MOMENTUM_ENGINE_MASTER_BLUEPRINT.md` is the primary standalone authority.
The following V17 documents form the active supporting set:

- `MOMENTUM_ENGINE_MASTER_BLUEPRINT.md`;
- `HANDOVER_V17_MOMENTUM_FOUNDATION_2026-07-30.md`;
- `ENGINE_V17_SHADOW.md`;
- `MOMENTUM_RESEARCH_PROTOCOL.md`;
- `MOMENTUM_RESEARCH_FIELD_GUIDE.md`;
- `VALIDATION_V17_D1_MTF_2026-07-29.md`;
- `VALIDATION_MOMENTUM_RESEARCH_FOUNDATION_2026-07-30.md`; and
- this action plan.

Material under any `Retired` directory is historical or invalid and must not
be used for current requirements, calculations, thresholds, conclusions or
plans unless the owner explicitly reactivates it.

If this plan changes a contract, gate or goal, update the master blueprint and
changelog in the same commit.

## Starting position

| Item | Status | Decision |
|---|---|---|
| Baseline code and documentation | Ready | Continue from the tagged V17 baseline |
| Deterministic mechanics | Passed at handover | Retain as regression gate |
| Daily inherited-rule efficacy | Failed | Use only as a benchmark |
| Compliant point-in-time daily archive | Not present in the workspace | First blocking dependency |
| Multi-year 30-minute archive | Not present in the workspace | Required after the daily model is frozen |
| Transparent daily classifier | Not started | Do not start before archive and split freeze |
| Production activation | Not approved | Remain research-only |

Existing Yahoo daily replay files and the recent intraday smoke panel are
mechanical evidence only. They are not substitutes for a promotion-quality
archive because they do not remove survivor, identity, delisting and
point-in-time membership bias.

## Prioritized execution plan

### P0 — Acquire and version the daily archive

Obtain an immutable long-form daily archive containing active, inactive and
delisted NYSE/Nasdaq equities. The accepted package must include:

- a stable security identifier across ticker changes;
- point-in-time ticker, listing exchange and equity/ETF identity;
- adjusted daily open, high, low, close and volume;
- listing and delisting dates;
- delisting return or documented terminal-value treatment;
- point-in-time sector and industry where available;
- corporate-action adjustment provenance; and
- immutable source/version metadata.

Create a dataset manifest containing the source, extract/version date, covered
period, row and security counts, file hashes, adjustment method, timezone,
calendar convention and known limitations.

**Exit gate G1:** no missing stable identifiers; point-in-time scope is
auditable; inactive/delisted coverage and terminal-value treatment are
documented; corporate-action checks pass; source files and hashes are frozen.

### P0 — Audit the archive before measuring momentum

Run an acceptance audit before building or viewing efficacy results:

1. Verify required columns and types.
2. Check duplicate `security_id`/session rows and ticker-history continuity.
3. Reconcile listing/delisting dates with observed price coverage.
4. Verify NYSE/Nasdaq equity scope without using today's membership as history.
5. Sample splits, distributions, symbol changes and delistings.
6. Check non-positive OHLC, impossible high/low relationships, missing volume,
   stale prices, extreme returns and calendar gaps.
7. Report coverage by year, exchange, active status, history group and sector.
8. Quarantine rejected rows with explicit reasons; never silently repair them.

**Deliverables:** archive manifest, field mapping, quality report, exclusion
ledger and a frozen accepted archive.

**Exit gate G2:** archive quality is sufficient for point-in-time daily
research and all material exclusions are quantified.

### P0 — Freeze the research contract and chronological periods

Before examining final results:

- retain the provisional next-session-open entry and 5/10/20-session return,
  MFE and MAE outcomes unless a documented pre-analysis decision changes them;
- retain the provisional 10-session +2 ATR/-1 ATR path label as a research
  label, not a trading threshold;
- define liquidity and broad-market-regime fields using point-in-time data;
- select fixed training, calibration and untouched holdout boundaries from the
  accepted archive's coverage;
- purge rows whose outcome crosses a period boundary;
- define transaction-cost and slippage sensitivity assumptions; and
- write the feature, model-family and promotion gates into a frozen research
  configuration.

**Exit gate G3:** outcome definitions, periods, feature availability rules,
cost assumptions and promotion gates are committed before holdout inspection.

### P1 — Build and validate the completed-daily panel

Use `build_momentum_research_panel.py` on the accepted archive. Confirm:

- one point-in-time row per valid security/session;
- every history group is retained;
- unavailable long-history features remain blank and explicitly unavailable;
- later prices cannot alter earlier features;
- future windows and same-session barrier ambiguity are handled explicitly;
- corporate actions and ticker changes remain linked by `security_id`; and
- panel, coverage and summary outputs reconcile to the accepted archive.

Use `validate_momentum_research_panel.py` with the frozen boundaries.

**Deliverables:** versioned panel, build manifest, reconciliation report and
chronological eligibility summary.

**Exit gate G4:** deterministic checks pass and all row-count or coverage
differences are explained.

### P1 — Establish unconditional and inherited-rule benchmarks

Measure unconditional 5/10/20-session outcomes by:

- calendar year and broad market regime;
- history group and listing age;
- liquidity and turnover;
- sector and industry where point-in-time fields are available;
- exchange; and
- active versus subsequently delisted status.

Then measure the inherited scanner conditions against the same base rates and
identical eligible rows. Report sample size, missingness, mean/median outcome,
win rate, MFE, MAE, barrier outcome and cost sensitivity. Treat the inherited
rules as benchmarks, not defaults to optimize.

**Exit gate G5:** the base-rate report is reproducible and exposes regime,
survivorship, liquidity and young-listing behavior.

### P2 — Research stable daily features without creating a BUY rule

Within training and calibration only:

1. Test individual features for monotonicity, missingness behavior and
   stability across years and history groups.
2. Test a small, predeclared set of economically interpretable interactions.
3. Build transparent probability baselines with calibrated probabilities.
4. Compare one nonlinear challenger only after the transparent baseline is
   stable.
5. Evaluate calibration, ranking, outcome distributions, turnover and cost
   sensitivity rather than a single accuracy statistic.
6. Reject features whose apparent value depends on one regime, sparse cohorts
   or unstable thresholds.

The untouched holdout must remain unopened during this phase.

**Exit gate G6:** feature set, model family, probability calibration method and
promotion thresholds are locked.

### P2 — Run the untouched holdout and make the daily decision

Execute the locked daily pipeline once on the untouched holdout. Compare:

- unconditional base rates;
- inherited scanner conditions;
- the transparent probability baseline; and
- the predeclared challenger.

Report results by regime, history group, liquidity, sector and delisting
status, including costs and uncertainty. A failed gate ends promotion work; it
does not trigger holdout threshold tuning.

**Exit gate G7:** either approve a frozen daily research candidate for
intraday-increment testing or document a no-promotion decision.

### P3 — Acquire and validate multi-year 30-minute data

Only after the daily candidate is frozen, acquire several years of
split-adjusted, regular-session 30-minute OHLCV with:

- exchange-timezone timestamps and immutable source provenance;
- point-in-time NYSE/Nasdaq identity aligned to the daily archive;
- inactive and delisted names;
- enough pre-period history for 4-hour EMA200 and other indicator warm-up; and
- documented corporate-action alignment with the daily archive.

Replay fixed execution cutoffs through `v17_mtf_replay.py`. Compare identical
daily candidates with and without completed current-session 4-hour/1-hour
evidence. Do not compare against prior-session intraday opinions.

**Exit gate G8:** multi-timeframe evidence adds stable out-of-sample value
after costs across regimes without violating timestamp or candle-completion
contracts.

### P3 — Live research-only observation and activation review

Run the frozen candidate in shadow mode. Monitor data quality, coverage,
probability calibration, drift, turnover and operational failures. Keep all
classification/confirmation activation flags false.

Production activation requires a separate owner-approved change after the
daily, intraday and live-shadow gates pass.

## Immediate execution checklist

1. Place or identify the candidate point-in-time daily archive.
2. Record its immutable version and file hashes.
3. Map its fields to the V17 long-form schema.
4. Run the P0 acceptance audit and issue the quality report.
5. Freeze chronological boundaries and the research configuration.
6. Build the daily panel only after gates G1-G3 pass.

Until step 1 is satisfied, productive work is limited to archive procurement,
schema mapping and audit tooling. Model or threshold changes would be
premature.

## Regression commands

```powershell
python -m unittest discover -s tests -p "test_*.py"
python -m py_compile `
  Live_Scanner_v17.py v17_mtf.py v17_mtf_replay.py `
  momentum_research.py plain_language_output.py `
  build_momentum_research_panel.py `
  validate_momentum_research_panel.py
git diff --check
```

These checks protect implementation integrity. They do not replace archive
acceptance or efficacy validation.
