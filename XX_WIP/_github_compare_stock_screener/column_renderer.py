from __future__ import annotations

import html
from typing import Any


MAIN_RESULT_COLUMNS = [
    ("Symbol", "Symbol"),
    ("CompanyName", "CompanyName"),
    ("LatestPrice", "LatestPrice"),
    ("CandidateState", "CandidateState"),
    ("Exchange", "Exchange"),
    ("Sector", "Sector"),
    ("Industry", "Industry"),
    ("MarketCap", "MarketCap"),
    ("AvgDailyVolume", "AvgDailyVolume"),
    ("AvgMonthlyVolume", "AvgMonthlyVolume"),
    ("WeightedScore", "WeightedScore"),
]

DIAGNOSTIC_COLUMNS = [
    "RSI_1D",
    "MACDScore",
    "RSIScore",
    "ADXScore",
    "ScoreWeights",
    "LifetimeHigh",
    "DistanceToLifetimeHighPct",
    "LifetimeHighBreakCount",
    "EMA20",
    "EMA52High",
    "DistanceToEMA52HighPct",
    "EMA52HighBreachCount",
    "EMA200High",
    "DistanceToEMA200HighPct",
    "EMA200HighBreachCount",
    "CeilingPattern",
    "CandidateReason",
    "L0_MACD_Alignment",
    "L0_MACD_1D_Direction",
    "L0_MACD_4H_Direction",
    "L0_MACD_1H_Direction",
    "L0_MACD_ZeroLinePassed",
    "L0_MACD_BullishPassed",
    "L0_MACD_Reason",
    "MACD_1D_State",
    "MACD_1D_Value",
    "MACD_1D_Histogram",
    "MACD_4H_State",
    "MACD_4H_Value",
    "MACD_4H_Crossover",
    "MACD_4H_BarsSinceBullishCrossover",
    "MACD_1H_State",
    "MACD_1H_Value",
    "MACD_1H_Crossover",
    "MACD_1H_ClearBullishCrossover",
    "MACD_1H_ClearBearishCrossover",
    "MACD_1H_BarsSinceBullishCrossover",
    "MACD_1H_BarsSinceBearishCrossover",
    "MACD_1H_BarsSinceBullishZeroLineCross",
    "MACD_1H_BarsSinceBearishZeroLineCross",
    "MACD_1D_BarsSinceBullishZeroLineCross",
    "MACD_4H_BarsSinceBullishZeroLineCross",
    "PreBullFreshness",
    "PreBullConfidence",
    "PreBullQualityReason",
    "RelativeVolume20",
    "VPTTrend",
    "VPTScore",
    "CompressionState",
    "CompressionScore",
    "MACD_Fast_1D_State",
    "MACD_Fast_4H_State",
    "MACD_Fast_1H_State",
    "MACD_Baseline_1D_State",
    "MACD_Baseline_1D_Regime",
    "MACD_Baseline_1D_Histogram",
    "MACD_Baseline_1D_Value",
    "MACD_Baseline_4H_State",
    "MACD_Baseline_4H_Value",
    "MACD_Baseline_4H_Crossover",
    "MACD_Baseline_4H_BarsSinceBullishCrossover",
    "MACD_Baseline_1H_State",
    "MACD_Baseline_1H_Value",
    "MACD_Flow_State",
    "MACD_Flow_Reason",
    "ConfirmedDivergence",
    "BaselineDivergence",
    "ADX_1D",
    "ADX_State",
    "Bollinger_PctB",
    "Bollinger_Position",
    "PriceLadder_Passed",
    "SetupPassed",
    "SetupScore",
    "AppliedFilters",
]

EXPORT_COLUMNS = [key for key, _ in MAIN_RESULT_COLUMNS] + DIAGNOSTIC_COLUMNS

REPORT_COLUMNS = MAIN_RESULT_COLUMNS + [(key, key) for key in DIAGNOSTIC_COLUMNS]


def display_decimal(value: object, digits: int = 2) -> str:
    if value in [None, ""]:
        return ""
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


def display_compact_number(value: object) -> str:
    if value in [None, ""]:
        return ""
    try:
        number = float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return str(value)
    sign = "-" if number < 0 else ""
    number = abs(number)
    if number >= 1_000_000_000_000:
        return f"{sign}{number / 1_000_000_000_000:.2f}T"
    if number >= 1_000_000_000:
        return f"{sign}{number / 1_000_000_000:.2f}B"
    if number >= 1_000_000:
        return f"{sign}{number / 1_000_000:.2f}M"
    if number >= 1_000:
        return f"{sign}{number / 1_000:.1f}K"
    return f"{sign}{number:.0f}"


def display_cell(key: str, value: object) -> str:
    if key in ["LatestPrice", "LifetimeHigh", "EMA20", "EMA52High", "EMA200High"]:
        return display_decimal(value, 2)
    if key in ["MarketCap", "AvgDailyVolume", "AvgMonthlyVolume"]:
        return display_compact_number(value)
    if key in [
        "WeightedScore",
        "MACDScore",
        "RSIScore",
        "ADXScore",
        "RSI_1D",
        "ADX_1D",
        "MACD_1D_Value",
        "MACD_1D_Histogram",
        "MACD_4H_Value",
        "MACD_1H_Value",
        "MACD_Baseline_1D_Histogram",
        "Bollinger_PctB",
        "PreBullConfidence",
        "RelativeVolume20",
        "VPTScore",
        "CompressionScore",
    ]:
        return display_decimal(value, 2)
    if key.startswith("DistanceTo"):
        formatted = display_decimal(value, 2)
        return f"{formatted}%" if formatted else ""
    if key.endswith("BreakCount") or key.endswith("BreachCount") or key == "SetupScore":
        return display_decimal(value, 0)
    return "" if value is None else str(value)


def render_headers(columns: list[tuple[str, str]]) -> str:
    return "".join(f'<th class="col-{html.escape(key)}">{html.escape(label)}</th>' for key, label in columns)


def render_row(row: dict[str, Any], columns: list[tuple[str, str]], use_display_format: bool = True) -> str:
    cells = []
    for key, _ in columns:
        value = display_cell(key, row.get(key, "")) if use_display_format else row.get(key, "")
        cells.append(f'<td class="col-{html.escape(key)}">{html.escape("" if value is None else str(value))}</td>')
    return "<tr>" + "".join(cells) + "</tr>"
