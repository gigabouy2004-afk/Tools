# V14 Enhanced Engine Documentation

## 1. Purpose and scope

V14 Enhanced is a fast, independent, per-ticker baseline status scanner. Its
purpose is to reduce the time required to screen a large code list while
preserving the broad recall needed for a separate end-user verification stage.

Its signal mandate is limited to established positive setup, trend, and momentum
conditions. It does not identify or classify anticipated pre-bull or pre-bear
crossovers.

It is not:

- a universe-relative ranker;
- a sector or index forecasting engine;
- an order execution engine;
- a guarantee that every BUY is immediately actionable; or
- a system that may change a ticker's status because of adjacent input codes.

False positives are tolerated by design because the end user performs a separate
offline review. The output must therefore expose enough context to distinguish a
clean candidate from a risky or low-quality candidate.

## 2. Engine invariants

### 2.1 Stateless ticker evaluation

Each ticker is evaluated from its own price and volume history. It has no
knowledge of:

- the ticker processed before or after it;
- thread completion order;
- the performance of SPY, NASDAQ, XLI, or another benchmark;
- the composition or behavior of the input universe; or
- the number of BUYs already found.

### 2.2 Concurrency is operational only

`ThreadPoolExecutor` processes independent ticker jobs in complete polls. The
worker count controls the number of tickers submitted in each poll.

For Poll X:

1. submit up to `--workers` tickers;
2. allow every submitted task to finish;
3. retain every result, including final-poll extras;
4. restore input order;
5. update cumulative counts; and
6. decide whether Poll X+1 should begin.

Classification cannot depend on completion order.

### 2.3 Limit semantics

`--countmax` and `--max-buys` are optional poll-boundary continuation triggers.

- They do not size a poll.
- They do not cancel submitted work.
- They do not impose an exact output cap.
- They do not affect classification.
- If neither is supplied, all input codes are processed.
- When either limit is met after Poll X completes, Poll X+1 is not started.

## 3. Data lifecycle

### 3.1 Daily data

The engine requests adjusted daily OHLCV data from Yahoo Finance. The default
core calculation history is five years and can be changed with
`--live-history-years`.

The core window must remain long enough for:

- EMA 200 on daily data;
- EMA 50 on completed weekly data; and
- stable MACD, RSI, ADX, ATR, and stochastic calculations.

### 3.2 Market sessions

The scanner resolves the exchange and timezone from Yahoo metadata, with
fallback profiles for U.S., NSE, BSE, Japan, Korea, and Taiwan listings.

`--live-candle-mode` supports:

- `auto` — use the appropriate completed or provisional mode for the exchange;
- `completed` — prefer the latest completed session candle; and
- `intraday` — rebuild a current session candle from minute data when available.

Provisional intraday BUYs are downgraded to HOLD until the candle is completed.

The output fields `session_date`, `candle_state`, `market_phase`, `data_mode`,
and `data_note` are authoritative for the included market session. A run-level
`as_of_date` can be a weekend or holiday. Run summaries therefore display
`DataThrough`, derived from successful rows' actual final included daily
sessions. A mixed-market run displays the earliest and latest included session
dates and the number of distinct session dates.

### 3.3 International listings and currency

The scanner retains the Yahoo listing currency and exchange. It does not assume
that every ticker is denominated in USD. Any future absolute price, turnover, or
market-cap threshold must be currency-aware or exchange-specific.

## 4. Technical calculations

### 4.1 Default indicators

| Indicator | Parameters |
|---|---|
| EMA | 20, 50, 200 daily |
| Weekly EMA | 20, 50 completed weekly |
| MACD | 12, 26, 9 |
| RSI | 14 |
| ADX | 14 |
| ATR | 14 |
| Stochastic | K 9, D smoothing 6 |
| Volume ratio | current volume / prior 20-session average |
| Historical context | prior 252 completed sessions |

The current observation is excluded from prior-history extrema and percentiles.

### 4.2 Trend alignment

Daily trend is aligned when:

```text
close > EMA50 > EMA200
```

Weekly trend is aligned when:

```text
weekly close > weekly EMA20 > weekly EMA50
```

Daily misalignment produces `Ignore_Daily_Trend`. Weekly misalignment produces
`Ignore_Weekly_Trend`.

### 4.3 Momentum continuation

`Buy_Momentum_Extension` requires:

- daily and weekly trend alignment;
- MACD above its signal;
- MACD and signal both above zero;
- positive histogram;
- every histogram bar in the configured window expanding, with the latest two
  bars both positive;
- a positive current session; and
- supportive volume.

RSI and ADX do not have universal upper rejection limits.

A qualified BUY more than 5 ATR above EMA50 retains BUY status but is presented
as `BUY_EXTENDED_REVIEW`. This preserves recall while preventing extreme
momentum from appearing equivalent to an ordinary BUY.

### 4.4 Early momentum

`Buy_Early_Momentum` requires:

- daily and weekly trend alignment;
- MACD and signal both above zero;
- MACD crossing from at or below its signal to above the signal;
- a positive MACD histogram;
- stochastic K above D;
- a positive current session; and
- supportive volume.

An improving negative histogram is not a signal in this engine. It cannot
qualify a BUY, increase confidence, or produce a pre-crossover classification.
When price trends remain aligned but MACD momentum is not confirmed, the ticker
is retained as a strict HOLD or ignored under the applicable trend rule.

ADX, volume, price response, and stochastic/EMA recovery contribute to setup
confidence only after daily trend, weekly trend, and the established positive
MACD regime have passed. Secondary indicators cannot compensate for a failed
primary momentum gate.

### 4.5 Pullback paths

Established positive trends may also produce:

- `Buy_Pullback_Oversold_Recovery`; or
- `Buy_EMA20_Midrange_Recovery`.

These require the relevant stochastic/EMA recovery and the stronger preset
volume confirmation. They also require the established positive MACD regime:
MACD above signal, MACD and signal above zero, and a positive histogram.

## 5. Historical context

### 5.1 Fixed one-year signal context

The classification path uses a fixed prior 252-session context for:

- RSI percentile and prior maximum;
- ADX percentile and prior maximum;
- stochastic K percentile and prior maximum;
- volume percentile and prior maximum; and
- prior 52-week price high and low.

ADX current/prior-maximum is confidence context only. It is not a hard gate.

### 5.2 Adaptive advisory guidance

The full input-code count selects the advisory history depth:

| Input ticker count | Guidance scope |
|---:|---|
| 1–100 | Maximum available history |
| 101–1,000 | Five years |
| More than 1,000 | One year |

This scope affects output guidance fields only. It cannot affect status,
`output_signal`, classification, confidence score, or polling.

The output discloses:

- requested and actual guidance scope;
- prior-session count;
- price high and low;
- current price versus guidance high;
- RSI, ADX, stochastic, and volume extrema;
- percentiles; and
- current value as a percentage of the prior maximum.

Daily-history downloads are cached within a process so multi-date validation
does not refetch the same ticker/period repeatedly.

Built-in historical signal replay applies the same post-classification BUY
quality policies as live and as-of evaluation, including the U.S. ADV20
liquidity floor and extreme-extension review label.

## 6. Volume semantics

The balanced preset defines supportive volume as:

```text
volume_ratio >= 0.60
AND
(
    volume_ratio >= 0.80
    OR
    one_year_absolute_volume_percentile >= 60
)
```

The design recognizes two forms of participation:

- current volume relative to the ticker's immediate 20-session baseline; and
- current absolute volume relative to the ticker's own one-year distribution.

The mandatory `0.60` floor prevents historical participation from overriding
materially weak current participation. Preset-specific immediate-ratio
thresholds still apply inside the parenthesized support paths.

`average_daily_turnover_20` is reported as:

```text
prior 20-session average volume * current listing-currency price
```

For U.S. listings, a BUY candidate must have at least USD 1 million ADV20
turnover. A candidate below that floor becomes HOLD with
`Hold_Buy_Liquidity_Below_Minimum`. No absolute turnover gate is applied to
international listings until currency-aware or exchange-specific policies are
defined.

## 7. Stochastic handling

The base post-detection stochastic K/D limit is 80.

After a BUY path is detected:

- a positive previous session can relax Early Momentum to 90;
- a positive previous session can relax Momentum Continuation to 100; and
- `--buy-stoch-max 0` disables the post-detection limit.

If the effective limit is exceeded, the candidate becomes
`Hold_Buy_Stochastic_Above_Limit`. The previous-positive session is contextual
relaxation, not a standalone predictor.

## 8. Output and interpretation

The XLSX contains:

- `Summary` — execution settings and aggregate counts;
- `Details` — one row per processed ticker.

The principal end-user classifications are:

- `BUY#1` — oversold pullback recovery;
- `BUY#2` — EMA20 midrange recovery;
- `BUY#3` — momentum continuation;
- `BUY#4` — early momentum; and
- `BUY_EXTENDED_REVIEW` — a retained BUY more than 5 ATR above EMA50; and
- `NO_BUY` — HOLD, IGNORE, REJECT, or ERROR.

The 113-column detail output includes trend, momentum, volume, historical,
session, currency, risk, and guidance fields. `message_details` is the concise
human-readable trace of why the row received its signal.

## 9. Operator controls

```text
--workers N
--countmax N
--max-buys N
--buy-stoch-max VALUE
--live-history-years N
--live-candle-mode auto|completed|intraday
--as-of-date YYYY-MM-DD
--as-of-dates YYYY-MM-DD,YYYY-MM-DD
--preset conservative|balanced|aggressive
```

Always use quoted paths in PowerShell when a path can contain spaces.

## 10. Current safeguards and remaining limitations

### 10.1 Current participation floor

The approved minimum is implemented as:

```text
require volume_ratio >= 0.60
and then allow:
volume_ratio >= 0.80 OR one_year_volume_percentile >= 60
```

### 10.2 U.S. minimum liquidity

U.S. BUY candidates now require USD 1 million prior-20-session average daily
turnover. International use remains ungated because it requires currency
conversion or explicit exchange/currency policies.

### 10.3 Extreme momentum review

The engine retains BUY recall beyond 5 ATR from EMA50 but labels those candidates
`BUY_EXTENDED_REVIEW` and assigns an Extreme Extension Review risk level.

### 10.4 Market-data quality

Sparse and low-liquidity Yahoo daily candles can disagree with intraday quote
data. The closing price may match while high, low, and volume differ. This can
affect ATR, stochastic, ADX, and volume ratio.

Low-liquidity filtering and explicit data-quality flags are preferred to
reintroducing universal RSI/ADX caps.

### 10.5 Displayed run date

The summary `AsOf` value can show the wall-clock or requested historical date,
while `session_date` shows the actual last included exchange session.
`DataThrough` makes that distinction prominent in per-run messages, terminal
and text-log output, and the workbook Summary sheet.

## 11. Verification commands

```powershell
python -m py_compile .\Live_Scanner_v14.py
python -m py_compile .\Live_Scanner_v14_Enhanced.py
python .\Live_Scanner_v14_Enhanced.py --help
```

Focused historical regression:

```powershell
python .\Live_Scanner_v14_Enhanced.py `
  -c CAT GE RTX GEV UNP BA ETN DE UBER PH `
  --as-of-dates 2026-07-22,2026-07-23,2026-07-24 `
  --live-candle-mode completed `
  --workers 3 `
  -o "D:\TMP\Live_Screener\XLI_Top10_2026-07-22_to_24.xlsx"
```
