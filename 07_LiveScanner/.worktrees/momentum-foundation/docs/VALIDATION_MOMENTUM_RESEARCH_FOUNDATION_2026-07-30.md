# Momentum Research Foundation Validation — 2026-07-30

## Decision

The research foundation is ready for point-in-time archive ingestion.

This decision covers temporal integrity, age-aware feature availability,
future-outcome construction, chronological split purging and plain-language
presentation. It does not approve a momentum classifier or any new BUY rule.

## Temporal contract

The implementation now enforces:

- the traded session before today is the completed daily foundation;
- today remains the current session even after its official close;
- today's daily row is excluded from the foundation;
- only completed 4-hour/1-hour observations from today are exposed;
- no previous-session lower-timeframe state is displayed or used as today's
  progression comparison;
- the first completed current-session bar is reported as the starting
  observation; and
- historical lower-timeframe records are limited to mathematical indicator
  warm-up.

Tests cover regular-hours, post-close, holiday, early-close and first-current-
bar behavior.

## Young and newly listed equities

Every completed daily observation is retained. The implementation does not
require EMA200 or weekly EMA50 before a row can enter the research panel.

The provisional history groups are:

- fewer than 20 sessions: observation only;
- 20–119 sessions: young listing;
- 120–251 sessions: developing history; and
- at least 252 sessions: established history.

Unavailable long-history indicators remain blank with explicit availability
fields. Sector and industry metadata are carried as point-in-time context but
never replace missing stock history.

## Outcome integrity

For each completed daily foundation:

- hypothetical entry is the open of the trading session immediately after the
  daily foundation;
- forward return, MFE and MAE are recorded over 5, 10 and 20 sessions;
- incomplete future windows are marked incomplete;
- the provisional ten-session barrier path distinguishes upward-first,
  downside-first, neither and same-session ambiguity; and
- future outcomes are attached only after daily features have been calculated.

A deterministic test changes all later prices and confirms that an earlier
feature record remains unchanged.

## Chronological validation

Training, calibration and holdout assignment is date ordered. A row is excluded
when its forward outcome crosses the training or calibration boundary.
Incomplete holdout outcomes are also excluded.

No random split is available.

## Plain-language presentation

The visible workbook contract is:

- `Summary` — execution and data-quality totals;
- `Review` — one readable row per security; and
- hidden `Technical Data` — reproducibility fields.

The visible review and text log contain no version names, shadow-state names or
internal flag columns. Current-session replay exports replace internal prefixes
with previous-session/current-session wording.

## Bounded cached-data smoke

The smoke used one previously cached daily frame only to exercise mechanics:

| Measure | Result |
|---|---:|
| Daily rows | 1,255 |
| Panel rows retained | 1,255 |
| First session | 2021-07-29 |
| Last session | 2026-07-29 |
| Observation-only rows | 19 |
| Young-listing rows | 100 |
| Developing-history rows | 132 |
| Established-history rows | 1,004 |
| Complete 20-session outcomes | 1,235 |

Chronological assignment produced:

| Period | Eligible | Boundary/incomplete exclusions |
|---|---:|---:|
| Training | 590 | 20 |
| Calibration | 482 | 20 |
| Holdout | 123 | 20 |

The panel exposed zero columns containing internal version or shadow names.

Barrier counts were recorded only as a mechanics check:

- downside threshold first: 675;
- upward target first: 419;
- neither threshold: 138;
- ATR unavailable: 13; and
- future window incomplete: 10.

These counts describe one surviving cached security and have no predictive or
economic interpretation.

## Automated validation

- 78 deterministic/regression tests passed.
- All changed Python modules compiled.
- `git diff --check` passed.

## Remaining requirements

Before classifier research:

1. acquire a versioned point-in-time NYSE/Nasdaq daily archive;
2. require equity/ETF identification, listing dates, delisting dates and
   terminal-value treatment;
3. include inactive and delisted securities;
4. audit corporate-action adjustments;
5. freeze training, calibration and holdout dates;
6. measure unconditional outcomes by year, history group, sector, liquidity
   and market regime; and
7. freeze the outcome definition before inspecting final holdout performance.

Only after that work should transparent probability models be compared with
the inherited rules. The current code intentionally emits no genuine-momentum
classification.
