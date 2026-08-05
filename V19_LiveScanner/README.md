# V19 Live Scanner

V19 is a standalone, deterministic D-1 momentum qualification engine. It does
not import classifications or signal rules from V16, V17 or V18.

## Qualification

A security is qualified only when all three compulsory points pass:

1. D-1 adjusted close is above EMA50 and EMA200.
2. MACD 12/26/9 line and signal are above zero, and MACD is above signal.
3. All 21/63/126-session adjusted-close returns are at least 20% for Tier 1,
   or at least 10% for Tier 2.

Standard slow stochastic 14/3/3 is calculated only for qualified securities.
It is descriptive and does not change the qualification tier.

The execution date is D. Every daily candle dated D is excluded, so the latest
available trading session strictly before D becomes D-1. This policy is the
same in current-date and backtest runs.

Historical runs reproduce the V19 calculations at the selected decision date,
but Yahoo supplies its currently available adjusted history. They are useful
for scanner replay and comparison, not a point-in-time delisting/survivorship-
free market study.

## Installation

```powershell
python -m pip install -r requirements.txt
```

## CLI examples

Current-date D-1 run with direct stock codes:

```powershell
python .\Live_Scanner_v19.py -c AAPL MSFT NVDA
```

Current-date run from the first column of a CSV or Excel file:

```powershell
python .\Live_Scanner_v19.py `
  -i D:\path\Stock_Codes.xlsx `
  -o D:\path\V19_Result.xlsx
```

Historical decision-date/backtest run:

```powershell
python .\Live_Scanner_v19.py `
  -c AAPL MSFT NVDA `
  --backtest-date 2026-07-31 `
  -o D:\path\V19_Backtest_2026-07-31.xlsx
```

Replace an existing output and adjust bounded Yahoo concurrency:

```powershell
python .\Live_Scanner_v19.py `
  -i D:\path\Stock_Codes.csv `
  --workers 4 `
  --max-attempts 3 `
  --request-timeout 15 `
  --overwrite `
  -o D:\path\V19_Result.xlsx
```

Run `python .\Live_Scanner_v19.py --help` for every option.

## Output workbook

The workbook retains the five-sheet baseline contract:

- `Summary`
- `Review`
- `Baseline Info`
- `Technical Data`
- `Scoring`

Every input code receives a terminal state. `Scoring` contains qualified Tier
1 and Tier 2 rows only. Rejected calculations remain visible in `Technical
Data`; invalid extraction rows remain visible in `Review` with an error code.

## Tests

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
python -m py_compile .\Live_Scanner_v19.py
```
