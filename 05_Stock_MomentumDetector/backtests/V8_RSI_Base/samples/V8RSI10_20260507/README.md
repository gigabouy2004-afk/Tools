# V8 RSI 10-Symbol Functional Sample

Evaluation date: 2026-05-07

Purpose: demonstrate the Foundation-first RSI base-layer contract on ten technology stocks that qualified for the EMA200/MACD Foundation on the common evaluation date.

Configuration:

```text
RSI definition: standard 14-session RSI from the Python ta library
Lower limit: 30
Upper limit: 65
Boundary mode: inclusive
Authority: continuation gate only
```

Result:

```text
Foundation eligible: 10/10
RSI within 30-65: 2/10
RSI above 65: 8/10
RSI below 30: 0/10
```

This is a functional value-and-message sample, not evidence that 30-65 is an optimal trading rule. Individual RSI outcome backtesting remains a later approval step.

`rsi_sample.csv` contains the complete engine output. `sample_summary.csv` contains the concise review view. `execution_log.csv` is the append-only engine log.
