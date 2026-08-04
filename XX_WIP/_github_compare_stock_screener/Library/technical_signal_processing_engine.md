# Rule-Based Technical Analysis Signal Processing Engine

## 1. Purpose

This document defines a **Signal Processing Engine** for stock screening using classical technical analysis principles.

The engine generates:

- `BUY`
- `WATCHLIST`
- `NO_TRADE`

The current version is **signal-only**. It does **not** calculate:

- stop-loss
- position size
- quantity
- trade capital allocation
- risk-reward ratio
- portfolio exposure
- final trade execution

The engine should be treated as a **technical candidate discovery module**, not a complete trading system.

---

## 2. Strategy Philosophy

The engine follows a top-down technical analysis sequence:

```text
Market Regime → Sector Strength → Stock Trend → Price Structure → Setup Detection → Momentum Confirmation → Volume Confirmation → Signal Score → Final Signal
```

This approach is preferred over a single-indicator system because no indicator is reliable in isolation.

The core idea:

```text
Only consider buying stocks when:
1. The broad market is supportive
2. The sector is strong
3. The stock is already in an uptrend
4. Price action shows a valid setup
5. Momentum confirms the move
6. Volume supports the signal
```

---

## 3. Engine Scope

### In Scope

| Area | Included |
|---|---|
| Market trend filter | Yes |
| Sector trend filter | Yes |
| Sector relative strength | Yes |
| Stock trend filter | Yes |
| Support/resistance calculation | Yes |
| Breakout detection | Yes |
| Pullback detection | Yes |
| Retest detection | Yes |
| RSI confirmation | Yes |
| MACD confirmation | Yes |
| Volume confirmation | Yes |
| Signal scoring | Yes |
| BUY / WATCHLIST / NO_TRADE output | Yes |

### Out of Scope

| Area | Included |
|---|---|
| Stop-loss | No |
| Position sizing | No |
| Trade quantity | No |
| Capital allocation | No |
| Portfolio risk | No |
| Automated order placement | No |
| Intraday scalping | No |

---

## 4. Input Data

The system requires OHLCV data.

### Required Data Per Stock

```json
{
  "date": "YYYY-MM-DD",
  "symbol": "RELIANCE",
  "sector": "NIFTY_ENERGY",
  "open": 2500.00,
  "high": 2550.00,
  "low": 2480.00,
  "close": 2535.00,
  "volume": 12000000
}
```

### Required Data Per Index

```json
{
  "date": "YYYY-MM-DD",
  "index_symbol": "NIFTY_50",
  "open": 22500.00,
  "high": 22650.00,
  "low": 22420.00,
  "close": 22610.00,
  "volume": null
}
```

### Required Universe

The engine should support:

```text
Broad Market Index: NIFTY_50
Sector Indices: NIFTY_BANK, NIFTY_IT, NIFTY_AUTO, NIFTY_PHARMA, etc.
Stock Universe: NIFTY_500 / F&O Universe / Custom Watchlist
```

---

## 5. Indicators to Calculate

| Indicator | Period | Type | Purpose |
|---|---:|---|---|
| EMA | 20 | Trend | Short-term trend |
| SMA | 50 | Trend | Medium-term trend |
| SMA | 200 | Trend | Long-term trend |
| RSI | 14 | Momentum | Strength confirmation |
| MACD | 12, 26, 9 | Momentum | Daily trend/momentum confirmation |
| MACD | 12, 26, 9 on 4H | Momentum | Intermediate timeframe alignment |
| MACD | 12, 26, 9 on 1H | Momentum | Short-term timeframe alignment and crossover/divergence detection |
| Average Volume | 20 | Volume | Participation confirmation |
| Relative Strength | 20 | Comparative | Sector/stock outperformance |
| 52-week high distance | 252 sessions | Strength filter | Avoid structurally weak stocks |

---

## 6. Rule Execution Sequence

```text
1. Load market, sector, and stock OHLCV data
2. Calculate indicators
3. Determine market regime
4. Determine sector strength
5. Determine sector relative strength
6. Determine stock trend
7. Calculate support and resistance
8. Detect valid setup
9. Confirm momentum
10. Confirm volume
11. Apply liquidity filter
12. Apply signal scoring
13. Generate BUY / WATCHLIST / NO_TRADE output
```

---

## 7. Configuration

All thresholds must be configurable.

```json
{
  "market_filter": {
    "enabled": true,
    "required_status_for_buy": "BULLISH"
  },
  "sector_filter": {
    "enabled": true,
    "required_status_for_buy": "BULLISH",
    "relative_strength_lookback": 20
  },
  "stock_trend_filter": {
    "ema_short": 20,
    "sma_medium": 50,
    "sma_long": 200
  },
  "liquidity_filter": {
    "enabled": true,
    "min_avg_daily_value_traded": 50000000,
    "avg_volume_period": 20
  },
  "breakout_setup": {
    "enabled": true,
    "lookback_days": 20,
    "breakout_buffer_percent": 0.5,
    "volume_multiplier": 1.5,
    "rsi_min": 55,
    "rsi_max": 75,
    "require_macd_bullish": true,
    "require_macd_above_zero_buffer": true
  },
  "quick_setup": {
    "enabled": true,
    "require_macd_above_zero_buffer": true,
    "require_1h_alignment": true,
    "require_4h_alignment": true,
    "require_1d_alignment": true
  },
  "pullback_setup": {
    "enabled": true,
    "ema_period": 20,
    "ema_tolerance_percent": 1.0,
    "rsi_min": 40,
    "rsi_max": 60,
    "require_rsi_rising": true
  },
  "retest_setup": {
    "enabled": true,
    "lookback_days": 10,
    "retest_tolerance_percent": 1.0,
    "rsi_min": 50
  },
  "macd_filter": {
    "enabled": true,
    "periods": {
      "1d": [12, 26, 9],
      "4h": [12, 26, 9],
      "1h": [12, 26, 9]
    },
    "bull_zero_line_min": 0.5,
    "apply_bull_zero_line_min_to": [
      "BULL_CROSSOVER",
      "BREAKOUT",
      "QUICK_SETUP",
      "SETUP_CANDIDATE"
    ],
    "require_all_timeframes_aligned": true,
    "bearish_timeframe_blocks_bull_signal": true,
    "clear_crossover_min_histogram": 0.0,
    "clear_crossover_min_macd_signal_spread": 0.0,
    "divergence_lookback": 20,
    "divergence_recent_window": 5
  },
  "signal_score": {
    "buy_threshold": 80,
    "watchlist_threshold": 65
  }
}
```

---

## 8. Market Regime Filter

### Purpose

Avoid long-side signals when the broad market is technically weak.

### Function

```python
def get_market_status(index):
    if (
        index.close > index.sma_50 and
        index.close > index.sma_200 and
        index.sma_50 > index.sma_200
    ):
        return "BULLISH"

    if (
        index.close < index.sma_50 and
        index.close < index.sma_200 and
        index.sma_50 < index.sma_200
    ):
        return "BEARISH"

    return "NEUTRAL"
```

### Rule

```python
market_status == "BULLISH"
```

If false, no fresh `BUY` signal should be generated.

---

## 9. Sector Strength Filter

### Purpose

Select stocks from sectors that are already technically strong.

### Function

```python
def get_sector_status(sector_index):
    if (
        sector_index.close > sector_index.sma_50 and
        sector_index.close > sector_index.sma_200 and
        sector_index.sma_50 > sector_index.sma_200
    ):
        return "BULLISH"

    if (
        sector_index.close < sector_index.sma_50 and
        sector_index.close < sector_index.sma_200 and
        sector_index.sma_50 < sector_index.sma_200
    ):
        return "BEARISH"

    return "NEUTRAL"
```

### Rule

```python
sector_status == "BULLISH"
```

---

## 10. Sector Relative Strength Filter

### Purpose

Prefer sectors outperforming the broad market.

### Formula

```python
sector_rs_today = sector_index.close / market_index.close
sector_rs_past = sector_index.close_n_days_ago / market_index.close_n_days_ago

sector_rs_positive = sector_rs_today > sector_rs_past
```

### Rule

```python
sector_rs_positive == True
```

Recommended default:

```text
Lookback = 20 trading days
```

---

## 11. Stock Trend Filter

### Purpose

Only consider stocks in established uptrends.

### Function

```python
def is_stock_bullish(stock):
    return (
        stock.close > stock.ema_20 and
        stock.close > stock.sma_50 and
        stock.close > stock.sma_200 and
        stock.ema_20 > stock.sma_50 and
        stock.sma_50 > stock.sma_200
    )
```

### Rule

```python
is_stock_bullish(stock) == True
```

---

## 12. Liquidity Filter

### Purpose

Avoid illiquid stocks where signals may not be executable.

### Formula

```python
avg_daily_value_traded = average(close * volume, 20)
```

### Rule

```python
avg_daily_value_traded >= min_avg_daily_value_traded
```

Recommended configurable value for Indian equities:

```text
Minimum average traded value = ₹5 crore per day
```

---

## 13. Support and Resistance

### Resistance

```python
resistance_20d = max(stock.high[-21:-1])
```

Meaning:

```text
Highest high of the previous 20 sessions, excluding today.
```

### Support

```python
support_20d = min(stock.low[-21:-1])
```

Meaning:

```text
Lowest low of the previous 20 sessions, excluding today.
```

---

## 14. Setup Detection

The engine should initially support three setup types:

```text
1. BREAKOUT
2. PULLBACK
3. RETEST
```

Complex chart patterns such as head-and-shoulders, triangles, double tops, and double bottoms should be excluded from Version 1 because they require subjective geometric interpretation.

---

# 15. Setup 1: Breakout

## Definition

A breakout occurs when price closes above recent resistance with stronger-than-normal volume and positive momentum.

## Function

```python
def is_breakout(stock):
    resistance = max(stock.high[-21:-1])

    return (
        stock.close > resistance * 1.005 and
        stock.volume > 1.5 * stock.avg_volume_20 and
        stock.rsi_14 >= 55 and
        stock.rsi_14 <= 75 and
        stock.macd_line > stock.macd_signal and
        stock.macd_histogram > 0
    )
```

## Interpretation

```text
BUY candidate when price closes at least 0.5% above 20-day resistance, volume is at least 1.5x average, RSI confirms strength, and MACD is bullish.
```

---

# 16. Setup 2: Pullback

## Definition

A pullback occurs when a strong stock temporarily returns near its short-term moving average and then shows recovery.

## Function

```python
def is_pullback(stock):
    return (
        stock.low <= stock.ema_20 * 1.01 and
        stock.close > stock.open and
        stock.close > stock.previous_close and
        stock.rsi_14 >= 40 and
        stock.rsi_14 <= 60 and
        stock.rsi_14 > stock.previous_rsi_14 and
        stock.volume <= 1.2 * stock.avg_volume_20
    )
```

## Interpretation

```text
BUY candidate when an uptrending stock pulls back near 20-EMA, recovers with a positive candle, RSI turns up, and pullback volume is not abnormally high.
```

---

# 17. Setup 3: Retest

## Definition

A retest occurs after a breakout. Price returns to the breakout level and holds above it.

## Prior Breakout Detection

```python
def has_prior_breakout(stock, lookback=10):
    for day in last_n_days(stock, lookback):
        resistance = max(day.high_history[-21:-1])

        if (
            day.close > resistance * 1.005 and
            day.volume > 1.5 * day.avg_volume_20
        ):
            return True, resistance

    return False, None
```

## Retest Function

```python
def is_retest(stock):
    prior_breakout, breakout_level = has_prior_breakout(stock, lookback=10)

    if not prior_breakout:
        return False

    return (
        stock.low <= breakout_level * 1.01 and
        stock.close > breakout_level and
        stock.rsi_14 > 50
    )
```

## Interpretation

```text
BUY candidate when price breaks out, pulls back to the breakout zone, holds it, and momentum remains positive.
```

---

## 18. Momentum Confirmation

### RSI Status

```python
def get_rsi_status(stock):
    if stock.rsi_14 >= 55 and stock.rsi_14 <= 75:
        return "BULLISH"

    if stock.rsi_14 > 75:
        return "OVEREXTENDED"

    if stock.rsi_14 >= 40 and stock.rsi_14 < 55:
        return "NEUTRAL_TO_POSITIVE"

    return "WEAK"
```

### MACD Status

```python
def get_macd_status(stock):
    if stock.macd_line > stock.macd_signal and stock.macd_histogram > 0:
        return "BULLISH"

    if stock.macd_line < stock.macd_signal and stock.macd_histogram < 0:
        return "BEARISH"

    return "NEUTRAL"
```

### Multi-Timeframe MACD

The engine must calculate MACD independently on these timeframes:

| Timeframe | Default MACD | Role |
|---|---|---|
| 1D | 12, 26, 9 | Primary trend confirmation |
| 4H | 12, 26, 9 | Intermediate timeframe alignment |
| 1H | 12, 26, 9 | Short-term timeframe alignment and crossover/divergence detection |

The default signal rule is strict multi-timeframe alignment:

```text
1D signal == 4H signal == 1H signal
```

For bullish strength, all three timeframes must be bullish or constructive. There must be no bearish deviation in any one timeframe.

Example:

```text
1D = BULLISH
4H = BULLISH
1H = BEARISH
Result = NOT_BULLISH / NO_TRADE
```

Reason:

```text
The 1H bearish reading means active sellers are still present. The MACD histogram may remain in, or return to, the red zone, so the setup does not have clean strength across timeframes.
```

The periods must remain configurable per timeframe. The default can be `12, 26, 9`, but the implementation must not hard-code one period set across all timeframes.

### Strict MACD Alignment Rule

A bullish signal is valid only when all selected MACD timeframes agree.

Recommended classification:

```python
def classify_macd_direction(macd):
    if macd["macd"] > macd["signal"] and macd["histogram"] > 0:
        return "BULLISH"

    if macd["macd"] < macd["signal"] and macd["histogram"] < 0:
        return "BEARISH"

    return "NEUTRAL"
```

Bullish alignment:

```python
macd_1d_direction == "BULLISH"
macd_4h_direction == "BULLISH"
macd_1h_direction == "BULLISH"
```

Bearish alignment:

```python
macd_1d_direction == "BEARISH"
macd_4h_direction == "BEARISH"
macd_1h_direction == "BEARISH"
```

Mixed alignment:

```python
len({macd_1d_direction, macd_4h_direction, macd_1h_direction}) > 1
```

Any mixed alignment must block a clean bullish signal.

Recommended implementation:

```python
def get_macd_alignment(macd_1d, macd_4h, macd_1h):
    directions = [
        classify_macd_direction(macd_1d),
        classify_macd_direction(macd_4h),
        classify_macd_direction(macd_1h),
    ]

    if all(direction == "BULLISH" for direction in directions):
        return "BULLISH_ALIGNED"

    if all(direction == "BEARISH" for direction in directions):
        return "BEARISH_ALIGNED"

    return "MIXED_OR_WEAK"
```

Rule:

```python
macd_alignment == "BULLISH_ALIGNED"
```

If false, the engine must not emit `BUY`, `BULL_CROSSOVER`, `PRE_BULL_CROSSOVER`, `BREAKOUT`, or `QUICK_SETUP`.

This is a state-specific qualifier, not a global rejection rule. If a symbol fails the bullish alignment gate, the engine must continue evaluating the remaining state rules such as bearish crossover, bearish extension, bearish divergence, bullish divergence, and finally status quo.

### State Classification Fallthrough

Every analyzed symbol must resolve to one final state before the UI-selected state filter is applied.

Supported states:

```text
PRE_BULL_CROSSOVER
PRE_BEAR_CROSSOVER
BULL_EXTENDED
BEAR_EXTENDED
SETUP_CANDIDATE
BULLISH_DIVERGENCE
BEARISH_DIVERGENCE
STATUS_QUO
```

Rule:

```text
If a symbol fails the qualifier for one state, continue checking the next state.
Only use STATUS_QUO after no defined state rule qualifies.
```

Example:

```text
Candidate is tested for PRE_BULL_CROSSOVER
1D = BULLISH
4H = BULLISH
1H = BEARISH
Result: not PRE_BULL_CROSSOVER
Next: continue checking bearish states, divergence states, extension states, then STATUS_QUO
```

### MACD Zero-Line Buffer Filter

For bullish breakout and quick setup candidates, MACD must be meaningfully above the zero line.

Default rule:

```python
macd_line >= 0.5
```

This rule applies to position-quality bullish setup states:

```text
BULL_CROSSOVER
BREAKOUT
QUICK_SETUP
SETUP_CANDIDATE
```

Interpretation:

- A bullish MACD/signal cross below zero is only an early recovery condition, not a breakout-quality bullish signal.
- A `PRE_BULL_CROSSOVER` is an early warning state around the MACD zero-line transition and must not require the `0.5` buffer.
- A quick setup or position-quality setup should not qualify unless the confirming MACD line is at least `0.5` above the zero line.
- The `0.5` threshold must be configurable because absolute MACD values vary by stock price scale and timeframe.

Recommended implementation:

```python
def passes_macd_zero_line_buffer(macd, threshold=0.5):
    return macd["macd"] is not None and macd["macd"] >= threshold
```

For strict alignment, the preferred confirmation point is all three MACD timeframes. If any timeframe fails the zero-line or direction rule, the bullish setup must be downgraded to `WATCHLIST` or `NO_TRADE`.

### Clear Bullish Crossover Definition

A clear bullish MACD crossover occurs when all required conditions are true:

```python
previous_macd <= previous_signal
latest_macd > latest_signal
latest_histogram > clear_crossover_min_histogram
latest_macd - latest_signal >= clear_crossover_min_macd_signal_spread
```

Optional stronger filter for breakout/quick setup candidates, not for `PRE_BULL_CROSSOVER`:

```python
latest_macd >= bull_zero_line_min
```

Default interpretation:

- `previous_macd <= previous_signal` proves the crossover happened on the latest candle.
- `latest_macd > latest_signal` confirms the bullish side of the crossover.
- `latest_histogram > 0` avoids flat or weak crosses.
- `latest_macd - latest_signal` can be used as a configurable spread filter when small noisy crosses need to be ignored.

### Clear Bearish Crossover Definition

A clear bearish MACD crossover occurs when:

```python
previous_macd >= previous_signal
latest_macd < latest_signal
latest_histogram < 0
previous_histogram >= latest_histogram
```

The bearish crossover rule is used for `PRE_BEAR_CROSSOVER`, deterioration warnings, and avoiding fresh long entries.

### Divergence Definition

MACD divergence compares price structure against MACD histogram structure over a configurable lookback.

Default windows:

```text
Lookback window: 20 candles
Recent window: 5 candles
```

Bullish divergence:

```python
recent_price_low < prior_price_low
recent_histogram_low > prior_histogram_low
```

Meaning:

```text
Price makes a lower low, but MACD histogram makes a higher low.
```

Bearish divergence:

```python
recent_price_high > prior_price_high
recent_histogram_high < prior_histogram_high
```

Meaning:

```text
Price makes a higher high, but MACD histogram makes a lower high.
```

Recommended implementation:

```python
def detect_macd_divergence(close, histogram, lookback=20, recent_window=5):
    if len(close) < lookback or len(histogram) < lookback:
        return "NONE"

    prior_close = close.iloc[-lookback:-recent_window]
    recent_close = close.iloc[-recent_window:]
    prior_hist = histogram.iloc[-lookback:-recent_window]
    recent_hist = histogram.iloc[-recent_window:]

    if recent_close.min() < prior_close.min() and recent_hist.min() > prior_hist.min():
        return "BULLISH_DIVERGENCE"

    if recent_close.max() > prior_close.max() and recent_hist.max() < prior_hist.max():
        return "BEARISH_DIVERGENCE"

    return "NONE"
```

### Divergence Confirmation Rules

A raw divergence on one timeframe is not enough for a final `BUY`.

Recommended rules:

| Raw Event | Required Confirmation |
|---|---|
| 1H bullish divergence | 1D, 4H, and 1H MACD must not be bearish; strict bullish alignment is preferred for `BUY` |
| 4H bullish divergence | 1D, 4H, and 1H MACD must not be bearish; strict bullish alignment is preferred for `BUY` |
| 1D bullish divergence | 1D, 4H, and 1H MACD must not be bearish; stock trend and volume confirmation required |
| Any 1H bearish signal while 1D/4H are bullish | Block `BUY`; active sellers are still present |
| 4H/1D bearish divergence | Downgrade signal to `WATCHLIST` or `NO_TRADE` |

Constructive MACD means:

```python
macd_line > macd_signal or histogram_is_rising
```

For `BUY`, bullish divergence should also pass the broader filters:

```text
Market bullish
Sector bullish
Stock trend bullish
Liquidity passed
Volume acceptable
Score >= buy threshold
```

---

## 19. Volume Confirmation

### Volume Status

```python
def get_volume_status(stock):
    if stock.volume >= 1.5 * stock.avg_volume_20:
        return "HIGH_VOLUME"

    if stock.volume >= stock.avg_volume_20:
        return "ABOVE_AVERAGE"

    if stock.volume >= 0.7 * stock.avg_volume_20:
        return "NORMAL"

    return "LOW_VOLUME"
```

### Usage

| Setup | Desired Volume |
|---|---|
| Breakout | HIGH_VOLUME |
| Pullback | NORMAL or LOW_VOLUME |
| Retest | NORMAL or ABOVE_AVERAGE |

---

## 20. Signal Score

Instead of producing signals from a single condition, the engine should generate a score.

### Scorecard

| Condition | Points |
|---|---:|
| Market bullish | 10 |
| Sector bullish | 10 |
| Sector relative strength positive | 10 |
| Stock above 20-EMA | 10 |
| Stock above 50-SMA | 10 |
| Stock above 200-SMA | 10 |
| 20-EMA > 50-SMA > 200-SMA | 10 |
| Valid setup detected | 15 |
| RSI confirms momentum | 10 |
| MACD bullish | 10 |
| Volume confirms setup | 10 |
| Liquidity filter passed | 5 |

Maximum score:

```text
120
```

### Normalized Score

```python
normalized_score = round((raw_score / 120) * 100, 2)
```

### Signal Classification

```python
if normalized_score >= 80 and valid_setup_detected:
    signal = "BUY"
elif normalized_score >= 65:
    signal = "WATCHLIST"
else:
    signal = "NO_TRADE"
```

### Category-Specific Scoring

The score is relative to the candidate's final bucket. A score of `80` in `BULL_EXTENDED` is not the same as a score of `80` in `PRE_BULL_CROSSOVER`.

Each state must have scoring logic that reflects the purpose of that state:

| State | Primary Score Meaning |
|---|---|
| `PRE_BULL_CROSSOVER` | Quality of clean bullish alignment and early crossover readiness |
| `PRE_BEAR_CROSSOVER` | Quality of bearish trigger and deterioration confirmation |
| `BULL_EXTENDED` | Degree of bullish extension, overbought pressure, and lower-timeframe rollover risk |
| `BEAR_EXTENDED` | Degree of bearish extension, oversold pressure, and downside trend persistence |
| `SETUP_CANDIDATE` | Setup quality, trend alignment, momentum headroom, and support conditions |
| `BULLISH_DIVERGENCE` | Strength and location of bullish divergence evidence |
| `BEARISH_DIVERGENCE` | Strength and location of bearish divergence evidence |
| `STATUS_QUO` | Degree of non-action/mixed signal balance |

Recommended score components:

| State Family | MACD Weight | RSI / Bollinger Weight | ADX / Trend Weight |
|---|---:|---:|---:|
| Crossover | 50 | 25 | 25 |
| Extended | 35 | 40 | 25 |
| Divergence | 50 | 30 | 20 |
| Status Quo | 40 mixed-signal balance | 30 RSI balance + 30 Bollinger balance | informational only |

The output must expose the score components and the score formula label so the user can understand why a candidate ranked high inside its own bucket.

---

## 21. Master Signal Function

```python
def generate_signal(stock, market_index, sector_index, config):

    market_status = get_market_status(market_index)
    sector_status = get_sector_status(sector_index)
    sector_rs_positive = is_sector_relative_strength_positive(
        sector_index,
        market_index,
        config["sector_filter"]["relative_strength_lookback"]
    )
    stock_bullish = is_stock_bullish(stock)
    liquidity_ok = passes_liquidity_filter(stock, config)

    breakout = is_breakout(stock)
    pullback = is_pullback(stock)
    retest = is_retest(stock)

    valid_setup = breakout or pullback or retest

    if breakout:
        setup_type = "BREAKOUT"
    elif pullback:
        setup_type = "PULLBACK"
    elif retest:
        setup_type = "RETEST"
    else:
        setup_type = null

    score = calculate_signal_score(
        market_status=market_status,
        sector_status=sector_status,
        sector_rs_positive=sector_rs_positive,
        stock=stock,
        valid_setup=valid_setup,
        liquidity_ok=liquidity_ok
    )

    if (
        market_status == "BULLISH" and
        sector_status == "BULLISH" and
        sector_rs_positive and
        stock_bullish and
        liquidity_ok and
        valid_setup and
        score >= 80
    ):
        signal = "BUY"

    elif score >= 65:
        signal = "WATCHLIST"

    else:
        signal = "NO_TRADE"

    return {
        "date": stock.date,
        "symbol": stock.symbol,
        "signal": signal,
        "setup_type": setup_type,
        "score": score,
        "market_status": market_status,
        "sector_status": sector_status,
        "sector_relative_strength_positive": sector_rs_positive,
        "stock_trend_status": "BULLISH" if stock_bullish else "NOT_BULLISH",
        "liquidity_status": "PASS" if liquidity_ok else "FAIL",
        "rsi_14": stock.rsi_14,
        "rsi_status": get_rsi_status(stock),
        "macd_status": get_macd_status(stock),
        "volume_status": get_volume_status(stock),
        "reference_price": stock.close,
        "support_20d": min(stock.low[-21:-1]),
        "resistance_20d": max(stock.high[-21:-1]),
        "remarks": generate_remarks()
    }
```

---

## 22. Output Format

### BUY Output

```json
{
  "date": "2026-05-20",
  "symbol": "RELIANCE",
  "signal": "BUY",
  "setup_type": "BREAKOUT",
  "score": 86.67,
  "market_status": "BULLISH",
  "sector_status": "BULLISH",
  "sector_relative_strength_positive": true,
  "stock_trend_status": "BULLISH",
  "liquidity_status": "PASS",
  "reference_price": 2535.00,
  "support_20d": 2410.00,
  "resistance_20d": 2520.00,
  "rsi_14": 62.40,
  "rsi_status": "BULLISH",
  "macd_status": "BULLISH",
  "volume_status": "HIGH_VOLUME",
  "remarks": [
    "Market is bullish",
    "Sector is bullish",
    "Sector relative strength is positive",
    "Stock is above 20EMA, 50SMA, and 200SMA",
    "Price closed above 20-day resistance",
    "Volume is above 1.5x 20-day average",
    "RSI confirms bullish momentum",
    "MACD confirms bullish momentum"
  ]
}
```

### WATCHLIST Output

```json
{
  "date": "2026-05-20",
  "symbol": "TCS",
  "signal": "WATCHLIST",
  "setup_type": null,
  "score": 72.50,
  "market_status": "BULLISH",
  "sector_status": "BULLISH",
  "sector_relative_strength_positive": true,
  "stock_trend_status": "BULLISH",
  "reason": "Trend and sector are bullish, but no valid setup has triggered yet"
}
```

### NO_TRADE Output

```json
{
  "date": "2026-05-20",
  "symbol": "INFY",
  "signal": "NO_TRADE",
  "setup_type": null,
  "score": 48.33,
  "market_status": "BULLISH",
  "sector_status": "NEUTRAL",
  "sector_relative_strength_positive": false,
  "stock_trend_status": "NOT_BULLISH",
  "reason": "Sector relative strength is negative and stock trend is not bullish"
}
```

---

## 23. Recommended Version 1 Build

### Must Build

```text
1. Market trend filter
2. Sector trend filter
3. Sector relative strength filter
4. Stock trend filter
5. Liquidity filter
6. Breakout setup
7. Pullback setup
8. Retest setup
9. RSI confirmation
10. MACD confirmation
11. Volume confirmation
12. Signal score
13. BUY / WATCHLIST / NO_TRADE output
```

### Should Not Build in Version 1

```text
1. Head-and-shoulders pattern detection
2. Triangle detection
3. Cup-and-handle detection
4. Double-top/double-bottom detection
5. Automated trade execution
6. Stop-loss
7. Position sizing
8. Portfolio management
```

---

## 24. Better Strategy Additions for Future Versions

The current engine is aligned with classical technical analysis. However, stronger future versions can add the following:

### 24.1 Relative Strength Ranking

Instead of checking only whether sector relative strength is positive, rank all sectors and stocks.

Example:

```text
Only consider stocks in the top 30% of relative strength.
```

This improves selectivity.

---

### 24.2 Multi-Timeframe Confirmation

Use weekly charts to confirm the larger trend.

Example:

```text
Daily BUY signal is valid only if weekly close > weekly 30-SMA.
```

---

### 24.3 Market Breadth Filter

Add breadth indicators such as:

```text
Percentage of stocks above 50-SMA
Percentage of stocks above 200-SMA
Advance/decline ratio
New highs vs new lows
```

This prevents buying when only a few index-heavy stocks are supporting the market.

---

### 24.4 Volatility Regime Filter

Avoid signals during unstable volatility spikes.

Example:

```text
Skip BUY signals if index volatility is above defined threshold.
```

---

### 24.5 Earnings/Event Filter

Avoid signals immediately before major uncertain events.

Example:

```text
No fresh BUY signal within X days before earnings announcement.
```

---

## 25. Validation Requirements

Before using live:

```text
1. Backtest across at least 5 years of data
2. Include bull, bear, and sideways markets
3. Test sector-wise performance
4. Track false breakout rate
5. Track average return after signal over 5, 10, 20, and 60 sessions
6. Compare BUY signals against random stock selection
7. Validate transaction cost impact separately
```

Since this engine does not include stop-loss or position sizing, validation should focus on signal quality, not full trading profitability.

Recommended metrics:

```text
Forward return after signal
Hit rate after 5/10/20/60 sessions
Average return
Median return
Maximum adverse excursion
Maximum favorable excursion
Signal frequency
False breakout percentage
Sector-wise success rate
```

---

## 26. Final System Description

```text
The Signal Processing Engine is a rule-based technical analysis scanner that identifies technically strong stock candidates using top-down market filtering, sector strength confirmation, relative strength, moving-average trend alignment, support/resistance breakout logic, pullback/retest detection, RSI and MACD momentum confirmation, volume validation, liquidity screening, and signal scoring.

The system outputs BUY, WATCHLIST, or NO_TRADE signals. It does not perform stop-loss calculation, position sizing, portfolio allocation, or trade execution in the current version.
```

---

## 27. Important Disclaimer

This engine does not guarantee profitable trading outcomes. Technical analysis produces probabilistic signals, not certainty. The engine must be backtested, forward-tested, and reviewed before any real-money use.
