# V6 Current Output Contract

Date: 2026-07-05

## Purpose

V6 starts from the stable V5 final-decision engine and adds a post-decision analyst text message.

V5 must remain the stable baseline. Analyst-message extraction belongs to V6 and must not be backported into `Momentum_Detector_V5.py`.

## User-Facing Rule

The primary user-facing decision remains:

- `Final_Decision`

Allowed values remain:

- `MOMENTUM_ACTIVE`
- `MOMENTUM_PRESENT_WAIT_CONFIRMATION`
- `REJECT`

The analyst message is additional text context only. It is not part of the technical calculation.

## Analyst Message

V6 adds:

- `External_Message`
- `Analyst_Message`
- `EPS_Message`
- `Event_Message`

Current behavior:

- Populated only for `MOMENTUM_ACTIVE` rows.
- Extracted from yfinance after `Final_Decision` is already calculated.
- Does not affect score, gates, ranks, blocker reasons, or `Final_Decision`.
- Includes analyst rating counts, mean analyst target where available, recent upgrade/downgrade counts, EPS revision text, and earnings/event date text where Yahoo data is available.
- Missing analyst/EPS/event data must not penalize a stock and must not change the engine decision.

## Exchange And Benchmark Handling

V6 selects relative-strength benchmark by exchange:

- US tickers use `SPY` by default.
- US scans can use `--us-benchmark QQQ` for Nasdaq/growth-heavy universes.
- NSE tickers, including `.NS`, use `^NSEI`.

The selected benchmark is written to `Benchmark_Ticker`.

## Liquidity Filter

V6 adds liquidity fields:

- `Avg_Dollar_Volume_50D`
- `Min_Avg_Dollar_Volume_50D`
- `Liquidity_Status`

Low liquidity is a confirmation blocker. It can downgrade a technically strong row from `MOMENTUM_ACTIVE` to `MOMENTUM_PRESENT_WAIT_CONFIRMATION`, but it does not rewrite technical score components.

## Implementation Boundary

Do not convert the analyst message into a score component without a separate validation task.

Any future external data source, including EPS revisions or earnings-date warnings, should first be added as post-decision text/audit output in V6 or later.

## Freshness Scoring Note (2026-07-06)

Implementation summary:

- `Freshness_Score` field added to the CSV output and exposed in the `scores` dictionary.
- The component is intentionally bounded (`-10` to `+15`) and is summed into the `raw` score before the existing 0-100 clamp.
- The overall score capping behavior remains unchanged; no score can exceed `100` after the change.

Note: Because `Freshness_Score` is summed into `scores["raw"]`, it therefore contributes to the final reported `Score` (after the existing 0..100 clamp). In short, `Freshness_Score` is part of the numeric `Score` reported in the CSV output.

Operational note: if you want freshness to be advisory only (not part of the numeric `Score`), I can flip it to a non-summed label and add a separate `Freshness_Label` (e.g. `Fresh`, `Moderate`, `Stale`) to the output.
