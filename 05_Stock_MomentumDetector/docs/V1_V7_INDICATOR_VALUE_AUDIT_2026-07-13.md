# Momentum Detector V1-V7 Indicator Value Audit

Date: 2026-07-13

Status: source-code audit complete. This records what the code calculated and how each value affected the engine. It does not endorse any historical value as correct, professional, optimal or suitable for V8.

## 1. Scope and Method

The audit started from `Momentum_Detector_V7.py`. When an indicator was absent from V7, the search moved backward through V6, V5, V4, V3, V2 and V1.

For every indicator or rule family, the audit separates formula/period, numerical values, decision effect, version changes and final outcome by V7.

V5 and V6 currently have unrelated local edits. A Git diff confirmed those edits change CLI/output behavior only; the indicator formulas and values below match committed `main`.

## 2. V7 Values First

V7 does **not** calculate RSI, MACD, ADX/DMI, OBV or Aroon. Those values cannot be extracted from V7 and are traced backward later.

| V7 family | Calculation or period | V7 values | V7 effect |
|---|---|---|---|
| Price trend | EMA 20, 50, 150 and 200; EMA200 percentage change over 50 sessions | Full stack `Close > EMA50 > EMA150 > EMA200`: +20. Partial `Close > EMA200` and `EMA50 > EMA200`: +12. EMA200 slope >2%: +10; >0%: +5. | `Close <= EMA200` creates Avoid and caps final technical score at 20. |
| Weekly trend | Friday weekly close; 30-week SMA; SMA percentage change over 10 weeks | Uptrend: close>SMA and slope>0, +15. Downtrend: close<SMA and slope<0, -10. Absolute slope <=1%: Flat. Other: Mixed; Mixed +5. | Any state other than Uptrend prevents Momentum Candidate; Downtrend cap 25, other non-Uptrend cap 45. |
| Returns | Close changes over 5, 10, 63, 126 and 252 sessions | Active confirmation requires 5D <=18% and 10D <=30%. | Higher values are entry blockers. V7 relaxed V5/V6 limits of 12% and 20%. |
| Benchmark relative strength | Stock 126D return minus benchmark 126D return; price/benchmark ratio; 50/200-session ratio averages; 50-session ratio slope | Excess >20%: +12; >5%: +8; >0%: +4. `RS_Ratio > RS_SMA50 > RS_SMA200` and slope>0: +13. | Excess <=0 creates Avoid/cap35. Active requires excess >=5%. US default SPY, optional QQQ; NSE `^NSEI`. |
| Breakout/proximity | Rolling highs over 20, 55, 100 and 252 sessions | Close >=98% of 55D high: +6. Close >=97% of 100D high: +6. Distance below 52W high <=10%: +8; <=20%: +4. | Adds Breakout Score. Distance<=5% with ATR>10% can classify Extended/Exhaustion Risk. |
| Freshness | `Distance_From_20D_High_Pct = (Close / High20 - 1) * 100` | <=2: +12; <=5: +8; <=10: +5; <=20: +2. 5D>15 and distance>10: -4. 10D>20 and distance>15: -5. Clamped -10..15. | Added V6. Because stored distance is normally zero/negative, `<=2` normally awards +12; later positive bands and penalties are effectively unreachable. Known sign/threshold mismatch, not a validated rule. |
| ATR/volatility | Raw True Range followed by simple 14-session rolling mean; `ATR_Pct=ATR14/Close*100` | <=4: +10; <=7: +7; <=10: +3; 10-15: 0; >15: -5. | Active requires <=10%. >15 creates Avoid and caps score at 30. |
| Volume | 20D/50D averages; relative volume = current volume / 20D average | Active requires Relative Volume >=0.75. | V7 relaxed V5/V6 minimum 1.0 to 0.75. |
| Close location | `(Close-Low)/(High-Low)*100`; zero-range day=50 | Active requires >=50%. | Entry blocker only. |
| Accumulation/distribution | Accumulation: daily change >=+1% and volume>50D average. Distribution: <=-1% and volume>50D average. Counts over 50 sessions. | Net>=3: +10; >0: +6. Distribution<=5: +5; >=10: -5. Latest distribution: -8. | Distribution>=8 creates Avoid and caps score at 40. |
| Liquidity | 50D average of Close*Volume | US minimum $5,000,000; NSE minimum 100,000,000 local currency units | Low liquidity blocks Active without changing component score. Added V6. |
| Daily timing | EMA20, signed 20D-high distance, 5D return, lower-high/lower-low and volume | Deep distance<=-8%; early<=-5%; 5D<=-3%; daily distribution<=-3%; high-volume pullback allows gain<=+0.5%. | Can create Wait or Failed Distribution Risk. |
| Intraday/extended hours | Live quote and last three hourly candles | Extended wait<=-2%; reject<=-5%; last-3H selling<=-1%; bearish confirmation 2 of 3. | Can Wait/cap/Reject. V7 uses PRE/REGULAR/POST/POSTPOST price for scoring. |
| Overall status | Component sum clamped 0..100; minimum momentum score70; candidate85 | Candidate requires raw>=85 and clean timing. Watchlist raw>=70. Active requires final score>=85 and all blockers clear. | Published caps: Active100, Wait84, Reject49. |

Source anchors: `Momentum_Detector_V7.py:22-49`, `688-823`, `837-1077`, plus `docs/V7_CURRENT_OUTPUT_CONTRACT_2026-07-10.md`.

## 3. Legacy Core Indicator Matrix, V1 Through V7

`—` means absent from that version's calculation and decision path.

| Indicator | V1 | V2 | V3 | V4 | V5 | V6 | V7 | Final outcome by V7 |
|---|---|---|---|---|---|---|---|---|
| EMA200 | Hard gate `Close>EMA200`. | Same. | Same. | EMA50/150/200. Hard gates: Close>EMA200, EMA50>EMA200, EMA200 50D slope>0. | Adds EMA20. Close<=EMA200 becomes Avoid/cap20 rather than early gate. | Same. | Same. | Present in all versions; authority changed from first-stage gate to later Avoid/cap. |
| MACD | Standard 12/26/9. Hard gate: line>signal and line>0. | Same. | Same. | — | — | — | — | Removed V4; absent V7. |
| RSI | RSI14. 56-68 +10; 55-<56 +5; >68-75 +5; >75 -10; <55 0. | Same. | Same. | — | — | — | — | Last present V3; historical bands absent V7. |
| ADX | ADX14. 26-40 +10; 20-<26 or >40-60 +5; >60 -5; <20 0. | Same. | Same. | ADX14, minimum18. 20-40 +10; 18-<20 or >40-60 +5; >60 +2. | — | — | — | Last present V4; removed V5. |
| +DI/-DI | DMI14 hard gate `+DI>-DI`. | Same. | Same. | Calculated but not used in gate, score or CSV. | — | — | — | Authority ended V4; calculation removed V5. |
| OBV | OBV and EMA20. Cross above EMA in last 1-3 checks +10; price up/OBV down -5. | Same. | Same. | OBV and EMA50; OBV>EMA50 +5. | — | — | — | Smoothing/logic changed V4; removed V5. |
| ATR | `ta` ATR14; published only. | Same. | Same. | `ta` ATR14; ATR% <=4/+10, <=7/+7, <=10/+4, <=15/+1, >15/-5; >15 gate; 3x ATR stop. | Changes to simple rolling TR mean14. ATR% <=4/+10, <=7/+7, <=10/+3, >15/-5; Active max10; >15 Avoid/cap30. | Same. | Same. | Survived, but formula and authority changed materially V5. |
| Aroon | — | — | Aroon14: Up>70 & Down<30 +10; Up>50 & Down<50 +5; Up<30 & Down>70 -5. | — | — | — | — | V3 only; removed V4. |
| Opening structure | — | — | Current open>prior open +5. | — | — | — | — | V3-only; removed V4. |
| OTR | — | — | — | — | — | — | — | No OTR indicator exists V1-V7. V5-V7 use internal raw True Range for ATR. |

Source anchors: V1 `43-158`; V2 `84-190`; V3 `72-211`; V4 `155-309`; V5 `345-421`, `593-709`; V6 `593-975`; V7 `688-1077`.

## 4. Score and Qualification Evolution

| Version | History/score | Qualification model | Outcome |
|---|---|---|---|
| V1 | 260-day request; 20/30 | EMA200+DMI+MACD first; RSI+ADX+OBV score >=20. | Original Foundation-plus-three-indicator model. |
| V2 | Same | Same technical rules; live daily OHLCV override. | No indicator-value change. |
| V3 | 260-day request; 25/45 | Same Foundation/RSI/ADX/OBV; adds opening structure +5 and Aroon up to +10. | Expanded V1 model. |
| V4 | 3 years; >=260 bars; >=65/100 | Replaces MACD/RSI/Aroon with long-term gates and trend/return/high/volume/ADX/ATR score. Intraday risk subtracts25 and can veto. | First wholesale redesign. |
| V5 | 5 years; >=300 bars; raw70, candidate85 | Removes ADX/OBV. Adds benchmark RS, breakout, accumulation/distribution, weekly trend, timing, caps and Active/Wait/Reject. | Second wholesale redesign. |
| V6 | Same core | V5 plus Freshness Score, exchange benchmark/liquidity and post-decision messages. | Freshness gains score authority and has sign/threshold mismatch. |
| V7 | Same core | Same V6 component score. Relaxes 5D/10D/relative-volume blockers, adds phase-aware price and published decision caps. | Actionability/display changes; core family unchanged. |

## 5. V4-V7 Replacement Indicator Matrix

| Family | V4 | V5 | V6 | V7 outcome |
|---|---|---|---|---|
| Trend stack | EMA50/150/200 and slope50D; max30. | Adds EMA20; full +20, partial +12, slope +10/+5. | Same. | Same. |
| Returns | 63/126/252 score; positive126 hard gate. | 5/10 extension and 63/126/252 stored; score uses benchmark excess. | Same. | Same formulas; Active extension limits 18/30. |
| Highs | 252D distance 10/20/30 ->15/10/5. | 55D/100D proximity plus 52W 10/20; 20D signed distance for timing. | Adds freshness. | Same as V6 including mismatch. |
| Volume | Ratio20/50>1 +5; OBV>EMA50 +5. | OBV removed; relative volume/close location blockers. | Adds liquidity. | Relative volume relaxed 1.0 to0.75. |
| ADX | ADX14 points, minimum18. | Removed. | Removed. | Removed. |
| ATR | `ta` ATR14 gate/score/stop. | Simple rolling TR mean14 and multiple rules. | Same. | Same. |
| Benchmark RS | None. | Fixed SPY. | US SPY/optional QQQ; NSE `^NSEI`. | Same. |
| Accumulation/distribution | Intraday veto only. | Daily +/-1% with volume>50D; 50D counts. | Same. | Same. |
| Weekly | None. | SMA30 and 10-week slope. | Same. | Same. |
| Freshness | None. | None. | Added, -10..15, summed. | Retained. |
| Liquidity | None. | None. | 50D dollar-volume blocker. | Retained. |

## 6. Exact Values Missing From V7

### RSI — last present V3

```text
Period 14
<55: 0
55 to <56: +5
56 to 68 inclusive: +10
>68 to 75 inclusive: +5
>75: -10
```

### ADX/DMI — last present V4

```text
V1-V3: period14; +DI>-DI hard gate; ADX <20/0, 20-<26/+5, 26-40/+10, >40-60/+5, >60/-5
V4: period14; no DMI gate; ADX <18/0, 18-<20/+5, 20-40/+10, >40-60/+5, >60/+2
```

### OBV — last present V4

```text
V1-V3: EMA20; fresh cross in latest three checks +10; price up/OBV down -5
V4: EMA50; OBV>EMA50 +5
```

### MACD — last present V3

```text
12/26/9
MACD line > signal AND MACD line >0
Hard first-stage gate
```

### Aroon — last present V3

```text
Period14
Up>70 and Down<30: +10
Up>50 and Down<50: +5
Up<30 and Down>70: -5
```

## 7. Final Outcome Register

| Concept | V7 state | Historical result |
|---|---|---|
| EMA200 | Present | Only legacy indicator present every version; authority changed. |
| MACD12/26/9 | Absent | V1-V3 hard gate; dropped V4. |
| RSI14/bands | Absent | V1-V3 score; dropped V4. |
| ADX14/DMI | Absent | V1-V3 gate+score; altered V4; dropped V5. |
| OBV/EMA | Absent | EMA20/cross V1-V3; EMA50/level V4; dropped V5. |
| ATR14 | Present | Formula changed from `ta` ATR to simple rolling TR mean V5; several V7 thresholds. |
| Aroon14 | Absent | V3 only. |
| Trend/RS/breakout/accumulation/weekly | Present | Introduced V4-V5; became V7 core. |
| Freshness | Present | Added V6, unchanged V7, but current sign/threshold behavior is defective. |

The historical result is not that V7 contains final or correct values. Several early indicators disappeared without a documented per-indicator validation trail, while V4-V7 accumulated replacement thresholds. Under the current V8 charter, every value remains historical evidence until it is configurable, functionally tested, backtested and explicitly approved.

## 8. Sources Audited

```text
Momentum_Detector_V1.py
Momentum_Detector_V2.py
Momentum_Detector_V3.py
Momentum_Detector_V4.py
Momentum_Detector_V5.py
Momentum_Detector_V6.py
Momentum_Detector_V7.py
docs/V5_CURRENT_OUTPUT_CONTRACT_2026-07-04.md
docs/V6_CURRENT_OUTPUT_CONTRACT_2026-07-05.md
docs/V7_CURRENT_OUTPUT_CONTRACT_2026-07-10.md
```

No generic trading convention was used to fill missing values. An absent value is reported as absent rather than inferred.
