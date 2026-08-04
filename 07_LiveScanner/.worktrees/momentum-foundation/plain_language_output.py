"""Plain-language presentation for the momentum research engine.

Internal version names, shadow flags and calculation fields remain available to
the implementation and technical audit.  This module produces the compact view
intended for an offline human review.
"""

from __future__ import annotations

from typing import Any

import pandas as pd


def _text(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def _int(value: Any) -> int:
    number = pd.to_numeric(value, errors="coerce")
    return int(number) if pd.notna(number) else 0


def _daily_view(row: pd.Series) -> str:
    if _text(row.get("status")) == "ERROR":
        return "Daily foundation unavailable"
    if not bool(row.get("v16_primary_regime_passed")):
        return "Existing daily rules do not show an upward momentum foundation"
    state = _text(row.get("momentum_state"))
    return {
        "LEADER": "Existing daily rules show a strong upward structure",
        "DEVELOPING": "Existing daily rules show a developing upward structure",
        "WEAK": "Upward structure exists, but supporting evidence is weak",
    }.get(state, "Daily foundation is mixed")


def _timeframe_view(row: pd.Series, prefix: str, label: str) -> str:
    current_bars = _int(row.get(f"{prefix}_bars"))
    if current_bars <= 0:
        return f"No completed {label} bar is available for the current session"
    relation = _text(row.get(f"{prefix}_relation_to_daily"))
    progression = _text(row.get(f"{prefix}_progression_state"))
    relation_text = {
        "SUPPORTIVE": "supports",
        "REGRESSING": "weakens",
        "MIXED": "is mixed against",
    }.get(relation, "cannot yet assess")
    if progression == "CURRENT_SESSION_START":
        return (
            f"The first completed {label} observation {relation_text} the "
            "previous-session daily view"
        )
    progression_text = {
        "PROGRESSED": " and has improved during the current session",
        "REGRESSED": " and has deteriorated during the current session",
        "MIXED": ", with mixed changes during the current session",
        "STABLE": " and is broadly unchanged during the current session",
    }.get(progression, "")
    return (
        f"Completed {label} evidence {relation_text} the previous-session "
        f"daily view{progression_text}"
    )


def _today_conclusion(row: pd.Series) -> str:
    state = _text(row.get("v17_current_development_state"))
    return {
        "TRUE_MOMENTUM_CANDIDATE": (
            "Both completed current-session timeframes support the "
            "previous-session view; research confirmation only"
        ),
        "DAILY_MOMENTUM_PARTIALLY_SUPPORTED": (
            "Only one completed current-session timeframe supports the "
            "previous-session view"
        ),
        "DAILY_MOMENTUM_REGRESSING": (
            "Current-session evidence is weakening the previous-session view"
        ),
        "DAILY_MOMENTUM_MIXED": (
            "Current-session evidence is mixed; no conclusion should be drawn"
        ),
        "DAILY_MOMENTUM_INTRADAY_UNAVAILABLE": (
            "No completed current-session timeframe is available yet"
        ),
        "INTRADAY_IGNITION_DAILY_UNQUALIFIED": (
            "Current-session strength is visible, but the previous-session "
            "daily foundation is absent"
        ),
        "DAILY_UNQUALIFIED": (
            "The previous-session daily foundation is absent"
        ),
    }.get(state, "Current-session conclusion is unavailable")


def build_plain_review_frame(details: pd.DataFrame) -> pd.DataFrame:
    """Return one compact, layman-readable row per evaluated security."""
    if details is None or details.empty:
        return pd.DataFrame(
            columns=[
                "Ticker",
                "Company",
                "Previous completed session",
                "Daily foundation",
                "Current session",
                "Completed 4-hour bars today",
                "Current 4-hour evidence",
                "Completed 1-hour bars today",
                "Current 1-hour evidence",
                "Today's conclusion",
                "Existing scanner result",
                "Reason",
                "Data note",
            ]
        )

    rows = []
    for _, row in details.iterrows():
        rows.append({
            "Ticker": _text(row.get("ticker")),
            "Company": _text(row.get("company_name")),
            "Previous completed session": _text(
                row.get("v17_daily_baseline_session_date")
                or row.get("session_date")
            ),
            "Daily foundation": _daily_view(row),
            "Current session": _text(
                row.get("v17_execution_session_date")
                or row.get("as_of_date")
            ),
            "Completed 4-hour bars today": _int(row.get("mtf_4h_bars")),
            "Current 4-hour evidence": _timeframe_view(
                row,
                "mtf_4h",
                "4-hour",
            ),
            "Completed 1-hour bars today": _int(row.get("mtf_1h_bars")),
            "Current 1-hour evidence": _timeframe_view(
                row,
                "mtf_1h",
                "1-hour",
            ),
            "Today's conclusion": _today_conclusion(row),
            "Existing scanner result": _text(
                row.get("classification")
                or row.get("OUT_MESSAGE")
                or row.get("status")
            ),
            "Reason": _text(row.get("reason")),
            "Data note": _text(
                row.get("v17_mtf_unavailable_reason")
                or row.get("data_note")
            ),
        })
    return pd.DataFrame(rows)


def format_plain_review_worksheet(worksheet) -> None:
    """Apply readable widths and keep the identifying columns visible."""
    worksheet.freeze_panes = "D2"
    widths = {
        "A": 16,
        "B": 28,
        "C": 24,
        "D": 52,
        "E": 20,
        "F": 26,
        "G": 68,
        "H": 26,
        "I": 68,
        "J": 72,
        "K": 28,
        "L": 52,
        "M": 72,
    }
    for column, width in widths.items():
        worksheet.column_dimensions[column].width = width
    worksheet.auto_filter.ref = worksheet.dimensions
