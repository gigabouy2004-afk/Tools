# V15 Shadow Momentum Quality Engine

## Purpose

V15 starts from the validated V14 Enhanced positive-regime engine at commit
`20641f5`. Its first job is measurement, not reclassification.

The scanner continues to identify positive setup, trend, and momentum only
after these primary conditions are present:

- price above EMA50 above EMA200;
- completed weekly price above weekly EMA20 above weekly EMA50; and
- MACD above signal, both MACD lines above zero, and histogram above zero.

V15 then asks a separate question: is the qualifying condition strong,
directional, current, and safe enough to resemble a genuine momentum leader?

## Frozen-classification contract

During the shadow phase, the following V14 fields are frozen:

- `status`;
- `classification`;
- `output_signal`; and
- all existing BUY/HOLD/IGNORE/ERROR rules and policy decisions.

The V15 fields are additional diagnostics only. The output explicitly records
`v15_classification_active=False`. A V15 recommendation can disagree with V14
without altering the V14 result.

Auto mode evaluates two V14-compatible views during the ticker's regular
session: the last completed regular-session candle and the current regular
partial candle. `.NS`/`.BO` codes use India regular hours; every other code uses
U.S. regular hours. If the completed view is BUY, that confirmed result remains
the primary action; otherwise the live view can expose a non-executable
provisional candidate. This is view selection and disclosure, not a new
classification rule.

This contract provides a direct regression check and permits the owner to run
V14 and V15 in parallel on the same dates and universes.

## Shadow quality evidence

The first shadow score contains ten one-point checks.

| Check | Initial hypothesis |
|---|---|
| EMA50 slope | 20-session change is positive |
| EMA200 slope | 60-session change is non-negative |
| Price return | 20-session return is positive |
| Price return | 60-session return is positive |
| Price return | 120-session return is positive |
| Direction | ADX +DI is greater than -DI |
| Trend strength | ADX is at least 20 |
| Leadership proximity | price is at least 85% of the prior 52-week high |
| Participation | current volume is at least its prior 20-session average |
| Entry extension | price is no more than 3 ATR above EMA50 |

The score is not intended to prove that every condition has equal predictive
value. Equal weighting is deliberately simple for the initial evidence-
collection phase.

## Momentum states

The positive primary regime is mandatory before a momentum state can be
assigned.

| State | Rule |
|---|---|
| `NONE` | primary regime fails, irrespective of score |
| `LEADER` | primary regime passes and score is 8–10 |
| `DEVELOPING` | primary regime passes and score is 6–7 |
| `WEAK` | primary regime passes and score is 0–5 |

The raw score remains visible when the primary regime fails so that historical
analysis can distinguish an otherwise strong stock from an in-scope positive
momentum candidate.

## Entry states

Entry states are evaluated in this safety-first priority order:

1. `NOT_APPLICABLE` for engine errors.
2. `NO_ENTRY` when the primary positive regime fails.
3. `WAIT_EXTENDED` when price is more than 3 ATR above EMA50.
4. `WAIT_ADX` when +DI does not exceed -DI or ADX is below 20.
5. `WAIT_VOLUME` when current volume is below its prior 20-session average.
6. `WAIT_LEADERSHIP` when the momentum state is not `LEADER`.
7. `PROVISIONAL_CONFIRMED` when all shadow gates pass but the qualifying V14
   BUY is based on a regular-session partial candle.
8. `CONFIRMED` when all shadow gates pass and a completed candle classifies
   BUY.
9. `WAIT_TRIGGER` when shadow quality passes but V14 has not classified BUY.

`shadow_recommended_status` expresses the implied shadow result, but it is not
the operational `status`.

## Output fields

Important V15 fields include:

- `engine_version`, `v15_shadow_mode`, and
  `v15_classification_active`;
- `beta` for live equity and ETF rows, and `alpha` for live ETF rows;
- `v15_primary_regime_passed`;
- `momentum_state`, `momentum_quality_score`,
  `momentum_quality_max_score`, and `momentum_quality_checks`;
- `entry_state` and `shadow_recommended_status`;
- `auto_action_source`, `auto_combined_state`, and `auto_dual_state`;
- completed-baseline fields prefixed with `confirmed_`;
- regular-session live fields prefixed with `live_overlay_`;
- `market_phase`, requested/effective mode, candle state, and fallback state;
- `ema50_slope_20_pct`, `ema200_slope_60_pct`;
- `return_20d_pct`, `return_60d_pct`, `return_120d_pct`;
- `adx_plus_di`, `adx_minus_di`, `adx_change_5`, and `adx_rising_5`; and
- boolean audit fields for every scored check.

The terminal and log summary show primary BUYs, completed-baseline BUYs,
provisional BUYs, exchange phases, Auto combined states, live-overlay states,
and shadow-confirmed BUYs.

## Simplified U.S./India Auto contract

Every ticker resolves its market independently from its code:

- `.NS` and `.BO` use `Asia/Kolkata`, 09:15-15:30;
- every other code uses `America/New_York`, 09:30-16:00; and
- provider exchange metadata, premarket data, and postmarket data do not alter
  this routing.

Auto then applies the relevant view:

| Phase | Confirmed view | Live overlay |
|---|---|---|
| Regular | prior completed regular candle | current regular partial candle, elapsed-volume adjusted |
| Closed | latest completed daily candle | none |

If fresh regular-session minute bars are unavailable, the completed baseline
remains authoritative and the fallback is disclosed.

## Live Beta and Alpha context

V15 adds provider-supplied Beta and Alpha as descriptive listing context:

- equities report Beta and intentionally leave Alpha blank;
- ETFs report three-year Beta and three-year Alpha when available;
- the fields are fetched only for live runs;
- historical/as-of rows leave both fields blank to avoid present-data
  look-ahead; and
- unavailable or malformed provider values remain blank without failing the
  ticker scan.

These fields do not contribute to the momentum score, entry state, operational
classification, or shadow recommendation. ETF Alpha is the provider's
three-year percentage-point value; it is not calculated by the scanner.

In the `Details` worksheet, the leading columns are:

| Column | Field |
|---|---|
| H | `Price` |
| I | `Currency` |
| J | `Beta` |
| K | `Alpha` |

The worksheet freezes at `L2`, keeping the header row and columns A through K
visible while the user scrolls through the remaining V15 diagnostics.

## Running the shadow engine

For automatic U.S./India regular-session confirmation plus live overlays:

```powershell
python .\Live_Scanner_v15.py `
  -i "D:\path\watchlist.csv" `
  --live-candle-mode auto `
  -o "D:\path\v15-auto-output.xlsx"
```

For a completed-candle parallel validation:

```powershell
python .\Live_Scanner_v15.py `
  -i "D:\path\watchlist.csv" `
  --live-candle-mode completed `
  -o "D:\path\v15-shadow-output.xlsx"
```

For historical dates:

```powershell
python .\Live_Scanner_v15.py `
  -c CAT GE RTX UNP DE `
  --as-of-dates 2026-07-22,2026-07-23,2026-07-24 `
  --live-candle-mode completed `
  -o "D:\path\v15-shadow-history.xlsx"
```

## Activation safeguards

No shadow condition should become a production classification rule until:

1. V14/V15 operational classifications have demonstrated exact parity during
   the shadow phase.
2. Historical tests measure precision, recall, forward return, adverse
   excursion, and candidate loss caused by each proposed gate.
3. Complete U.S. and India runs confirm that thresholds behave as intended.
4. The owner reviews named false-positive and false-negative examples.
5. Any activation is made in a separate commit with boundary and regression
   tests.

## Deferred custom relative-strength work

Absolute 20/60/120-session performance is measured in this first V15 version.
Provider-supplied Beta and ETF Alpha are displayed as descriptive risk context,
but custom benchmark-relative ranking is not scored.
