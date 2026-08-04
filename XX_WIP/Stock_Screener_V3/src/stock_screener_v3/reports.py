from __future__ import annotations

import csv
from pathlib import Path
import re
from typing import Any

from stock_screener_v3.backtest_engine import summarize_result
from stock_screener_v3.models import BacktestResult
from stock_screener_v3.output_contracts import DEFAULT_DETAIL_CSV_COLUMNS


def write_detail_csv(result: BacktestResult, path: str | Path, columns: list[str] | None = None) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    rows = list(result.detail_rows)
    base_columns = list(columns or DEFAULT_DETAIL_CSV_COLUMNS)
    fieldnames = list(dict.fromkeys(base_columns + [key for row in rows for key in row.keys()]))
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def render_summary_markdown(result: BacktestResult) -> str:
    summary = summarize_result(result)
    lines: list[str] = [
        "# V3 Backtest Summary",
        "",
        f"- D date: {summary['d_date']}",
        f"- Universe file: {result.config.universe_file}",
        f"- Stage families: {', '.join(result.config.stage_families)}",
        f"- Sample mode: {result.config.sample_mode}",
        f"- Symbols attempted: {summary['symbols_attempted']}",
        f"- Symbols processed: {summary['symbols_processed']}",
        f"- Symbols skipped: {summary['symbols_skipped']}",
        f"- Candidates found: {summary['candidates_found']}",
        f"- Candidate density: {float(summary['candidate_density']):.4f}",
        "",
        "## Forward Outcomes",
        "",
        "| Horizon | Evaluated | Positive | Hit Rate | Average Return | Median Return |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for days in result.config.forward_days:
        evaluated = int(summary.get(f"d_plus_{days}_evaluated", 0))
        positive = int(summary.get(f"d_plus_{days}_positive", 0))
        hit_rate = float(summary.get(f"d_plus_{days}_hit_rate", 0.0))
        average_return = _format_pct_value(summary.get(f"d_plus_{days}_average_return_pct"))
        median_return = _format_pct_value(summary.get(f"d_plus_{days}_median_return_pct"))
        lines.append(f"| D+{days} | {evaluated} | {positive} | {hit_rate:.2%} | {average_return} | {median_return} |")
    score_buckets = summary.get("score_buckets", {})
    if score_buckets:
        lines.extend(["", "## Score Buckets", "", "| Bucket | Candidates |", "|---|---:|"])
        for bucket in ["80+", "70-79", "60-69", "50-59", "<50"]:
            count = int(score_buckets.get(bucket, 0))  # type: ignore[union-attr]
            if count:
                lines.append(f"| {bucket} | {count} |")
    _append_group_outcomes(
        lines,
        "Score Bucket Outcomes",
        summary.get("score_bucket_outcomes", {}),
        result.config.forward_days,
        group_order=("80+", "70-79", "60-69", "50-59", "<50"),
    )
    _append_group_outcomes(lines, "Stage Family Outcomes", summary.get("stage_family_outcomes", {}), result.config.forward_days)
    _append_group_path_outcomes(lines, "Stage Family Path Outcomes", summary.get("stage_family_path_outcomes", {}), result.config.forward_days)
    _append_group_path_outcomes(lines, "Candidate State Path Outcomes", summary.get("candidate_state_path_outcomes", {}), result.config.forward_days)
    _append_group_outcomes(lines, "Sector Outcomes", summary.get("sector_outcomes", {}), result.config.forward_days)
    _append_group_outcomes(lines, "Review Priority Outcomes", summary.get("review_priority_outcomes", {}), result.config.forward_days)
    _append_group_outcomes(lines, "Risk Tag Outcomes", summary.get("risk_tag_outcomes", {}), result.config.forward_days)
    _append_ranking_collision_buckets(lines, summary.get("ranking_collision_buckets", {}))
    failure_categories = summary.get("failure_categories", {})
    if failure_categories:
        lines.extend(["", "## Failure Categories", ""])
        for category, count in sorted(failure_categories.items(), key=lambda item: (-item[1], item[0])):  # type: ignore[union-attr]
            lines.append(f"- {category}: {count}")
    if result.skip_reasons:
        lines.extend(["", "## Skip Reasons", ""])
        for reason, count in sorted(result.skip_reasons.items(), key=lambda item: (-item[1], item[0])):
            lines.append(f"- {reason}: {count}")
    return "\n".join(lines) + "\n"


def write_summary_markdown(result: BacktestResult, path: str | Path) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_summary_markdown(result), encoding="utf-8")


def write_cross_sector_calibration_report(
    detail_paths: tuple[str | Path, ...],
    output_path: str | Path,
    *,
    horizon_days: int = 20,
    candidate_state: str = "PRE_BEAR_CROSSOVER",
) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        render_cross_sector_calibration_markdown(
            detail_paths,
            horizon_days=horizon_days,
            candidate_state=candidate_state,
        ),
        encoding="utf-8",
    )


def render_cross_sector_calibration_markdown(
    detail_paths: tuple[str | Path, ...],
    *,
    horizon_days: int = 20,
    candidate_state: str = "PRE_BEAR_CROSSOVER",
) -> str:
    rows = _candidate_rows_from_csvs(detail_paths)
    rows = [row for row in rows if row_value(row, "CandidateStateRaw") == candidate_state or row_value(row, "CandidateState") == candidate_state]
    lines: list[str] = [
        f"# V3 Cross-Sector {candidate_state} Calibration Report",
        "",
        f"- Horizon: D+{horizon_days}",
        f"- Detail files: {len(detail_paths)}",
        f"- Candidate rows: {len(rows)}",
        "",
        "## Sector Path Outcomes",
        "",
        "| Sector | Candidates | Endpoint Hit Rate | Endpoint Avg | Endpoint Median | Avg Worst Low | Median Worst Low | Worst Low <= -10% | Worst Low <= -20% | Avg Best High | Median Best High |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for sector, sector_rows in _group_rows(rows, "Sector").items():
        metrics = _calibration_metrics(sector_rows, horizon_days)
        lines.append(
            f"| {sector} | {len(sector_rows)} | {metrics['hit_rate']} | {metrics['endpoint_avg']} | "
            f"{metrics['endpoint_median']} | {metrics['worst_avg']} | {metrics['worst_median']} | "
            f"{metrics['worst_lte_10']} | {metrics['worst_lte_20']} | {metrics['best_avg']} | {metrics['best_median']} |"
        )
    _append_calibration_split(lines, "Date Split", rows, "DDate", horizon_days)
    _append_calibration_split(lines, "Opportunity Type Split", rows, "CrossoverOpportunityType", horizon_days)
    lines.extend(["", "## Worst Rows", "", "| Sector | D Date | Symbol | Opportunity Type | Class | Priority | Endpoint | Worst Low | Best High | Risk Tags |", "|---|---|---|---|---|---|---:|---:|---:|---|"])
    for row in _worst_rows(rows, horizon_days, limit=15):
        lines.append(
            f"| {row_value(row, 'Sector') or 'UNKNOWN'} | {row_value(row, 'DDate') or _date_from_source(row)} | "
            f"{row_value(row, 'Symbol')} | {row_value(row, 'CrossoverOpportunityType') or 'UNKNOWN'} | "
            f"{row_value(row, 'CandidateClass')} | {row_value(row, 'ReviewPriority')} | "
            f"{_format_pct_value(row.get(f'DPlus{horizon_days}ReturnPct'))} | "
            f"{_format_pct_value(row.get(f'DPlus{horizon_days}WorstLowReturnPct'))} | "
            f"{_format_pct_value(row.get(f'DPlus{horizon_days}BestHighReturnPct'))} | "
            f"{row_value(row, 'RiskTags') or 'none'} |"
        )
    return "\n".join(lines) + "\n"


def write_symbol_failure_report(
    detail_paths: tuple[str | Path, ...],
    output_path: str | Path,
    *,
    horizon_days: int = 20,
    limit: int = 15,
    stage_family: str = "",
    candidate_state: str = "",
    sector: str = "",
) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        render_symbol_failure_markdown(
            detail_paths,
            horizon_days=horizon_days,
            limit=limit,
            stage_family=stage_family,
            candidate_state=candidate_state,
            sector=sector,
        ),
        encoding="utf-8",
    )


def render_symbol_failure_markdown(
    detail_paths: tuple[str | Path, ...],
    *,
    horizon_days: int = 20,
    limit: int = 15,
    stage_family: str = "",
    candidate_state: str = "",
    sector: str = "",
) -> str:
    rows = _candidate_rows_from_csvs(detail_paths)
    rows = _filter_rows(rows, stage_family=stage_family, candidate_state=candidate_state, sector=sector)
    endpoint_key = f"DPlus{horizon_days}ReturnPct"
    failed_rows = [row for row in rows if (_number(row.get(endpoint_key)) is not None and _number(row.get(endpoint_key), 0.0) < 0)]
    lines: list[str] = [
        "# V3 Symbol-Level Failure Report",
        "",
        f"- Horizon: D+{horizon_days}",
        f"- Detail files: {len(detail_paths)}",
        f"- Stage family filter: {stage_family or 'ALL'}",
        f"- Candidate state filter: {candidate_state or 'ALL'}",
        f"- Sector filter: {sector or 'ALL'}",
        f"- Candidate rows: {len(rows)}",
        f"- Negative endpoint rows: {len(failed_rows)}",
        "",
        "## Worst Endpoint Rows",
        "",
        "| D Date | Symbol | Sector | Candidate State | Class | Priority | Endpoint | Worst Low | Best High | Reason Codes |",
        "|---|---|---|---|---|---|---:|---:|---:|---|",
    ]
    for row in sorted(failed_rows, key=lambda item: _number(item.get(endpoint_key), 0.0) or 0.0)[:limit]:
        lines.append(
            f"| {row_value(row, 'DDate') or _date_from_source(row)} | {row_value(row, 'Symbol')} | "
            f"{row_value(row, 'Sector') or 'UNKNOWN'} | {row_value(row, 'CandidateStateRaw') or row_value(row, 'CandidateState')} | "
            f"{row_value(row, 'CandidateClass')} | {row_value(row, 'ReviewPriority')} | "
            f"{_format_pct_value(row.get(endpoint_key))} | "
            f"{_format_pct_value(row.get(f'DPlus{horizon_days}WorstLowReturnPct'))} | "
            f"{_format_pct_value(row.get(f'DPlus{horizon_days}BestHighReturnPct'))} | "
            f"{row_value(row, 'ReasonCodes')} |"
        )
    repeated = _repeated_symbol_failures(failed_rows, horizon_days)
    if repeated:
        lines.extend(["", "## Repeated Weak Symbols", "", "| Symbol | Rows | Average Endpoint | Worst Endpoint | Best Endpoint | Dates |", "|---|---:|---:|---:|---:|---|"])
        for symbol, metrics in repeated[:limit]:
            dates = ", ".join(metrics["dates"])
            lines.append(
                f"| {symbol} | {metrics['rows']} | {_format_pct_value(metrics['average'])} | "
                f"{_format_pct_value(metrics['worst'])} | {_format_pct_value(metrics['best'])} | {dates} |"
            )
    return "\n".join(lines) + "\n"


def write_stage_family_calibration_report(
    detail_paths: tuple[str | Path, ...],
    output_path: str | Path,
    *,
    stage_family: str,
    horizon_days: int = 20,
) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        render_stage_family_calibration_markdown(detail_paths, stage_family=stage_family, horizon_days=horizon_days),
        encoding="utf-8",
    )


def render_stage_family_calibration_markdown(
    detail_paths: tuple[str | Path, ...],
    *,
    stage_family: str,
    horizon_days: int = 20,
) -> str:
    family = stage_family.upper()
    rows = [row for row in _candidate_rows_from_csvs(detail_paths) if row_value(row, "StageFamily").upper() == family]
    lines: list[str] = [
        f"# V3 {family} Calibration Report",
        "",
        f"- Horizon: D+{horizon_days}",
        f"- Detail files: {len(detail_paths)}",
        f"- Candidate rows: {len(rows)}",
    ]
    _append_stage_family_split(lines, "Candidate State Outcomes", rows, "CandidateStateRaw", horizon_days)
    _append_stage_family_split(lines, "Sector Outcomes", rows, "Sector", horizon_days)
    _append_stage_family_split(lines, "Date Outcomes", rows, "DDate", horizon_days)
    if family == "DIVERGENCE":
        _append_stage_family_split(lines, "Divergence Direction Outcomes", rows, "DivergenceDirection", horizon_days)
        _append_stage_family_split(lines, "Divergence Type Outcomes", rows, "DivergenceType", horizon_days)
        _append_stage_family_split(lines, "Divergence Opportunity Outcomes", rows, "DivergenceOpportunityType", horizon_days)
    if family == "MOMENTUM_SETUP":
        _append_stage_family_split(lines, "Momentum Opportunity Outcomes", rows, "MomentumSetupOpportunityType", horizon_days)
    lines.extend(
        [
            "",
            "## Worst Endpoint Rows",
            "",
            "| D Date | Symbol | Sector | Candidate State | Class | Priority | Endpoint | Worst Low | Best High | Reason Codes |",
            "|---|---|---|---|---|---|---:|---:|---:|---|",
        ]
    )
    endpoint_key = f"DPlus{horizon_days}ReturnPct"
    rows_with_endpoint = [row for row in rows if _number(row.get(endpoint_key)) is not None]
    for row in sorted(rows_with_endpoint, key=lambda item: _number(item.get(endpoint_key), 0.0) or 0.0)[:15]:
        lines.append(
            f"| {row_value(row, 'DDate') or _date_from_source(row)} | {row_value(row, 'Symbol')} | "
            f"{row_value(row, 'Sector') or 'UNKNOWN'} | {row_value(row, 'CandidateStateRaw') or row_value(row, 'CandidateState')} | "
            f"{row_value(row, 'CandidateClass')} | {row_value(row, 'ReviewPriority')} | "
            f"{_format_pct_value(row.get(endpoint_key))} | "
            f"{_format_pct_value(row.get(f'DPlus{horizon_days}WorstLowReturnPct'))} | "
            f"{_format_pct_value(row.get(f'DPlus{horizon_days}BestHighReturnPct'))} | "
            f"{row_value(row, 'ReasonCodes')} |"
        )
    return "\n".join(lines) + "\n"


def write_integrated_calibration_report(
    detail_paths: tuple[str | Path, ...],
    output_path: str | Path,
    *,
    horizon_days: int = 20,
) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        render_integrated_calibration_markdown(detail_paths, horizon_days=horizon_days),
        encoding="utf-8",
    )


def render_integrated_calibration_markdown(
    detail_paths: tuple[str | Path, ...],
    *,
    horizon_days: int = 20,
) -> str:
    rows = _candidate_rows_from_csvs(detail_paths)
    lines: list[str] = [
        "# V3 Integrated Holistic Calibration Report",
        "",
        f"- Horizon: D+{horizon_days}",
        f"- Detail files: {len(detail_paths)}",
        f"- Candidate rows: {len(rows)}",
    ]
    _append_stage_family_split(lines, "Stage Family Outcomes", rows, "StageFamily", horizon_days)
    _append_stage_family_split(lines, "Candidate State Outcomes", rows, "CandidateStateRaw", horizon_days)
    _append_stage_family_split(lines, "Review Priority Outcomes", rows, "ReviewPriority", horizon_days)
    _append_stage_family_split(lines, "Risk Tag Outcomes", _rows_by_exploded_risk_tag(rows), "_RiskTag", horizon_days)
    _append_stage_family_split(lines, "Ranking Collision Outcomes", _rows_by_ranking_collision_bucket(rows), "_RankingCollisionBucket", horizon_days)
    _append_winner_family_collision_split(lines, rows, horizon_days)
    _append_integrated_worst_rows(lines, rows, horizon_days, limit=20)
    return "\n".join(lines) + "\n"


def render_multi_date_summary_markdown(results: tuple[BacktestResult, ...]) -> str:
    lines: list[str] = [
        "# V3 Multi-Date Backtest Summary",
        "",
        f"- Runs: {len(results)}",
    ]
    if not results:
        return "\n".join(lines) + "\n"

    forward_days = results[0].config.forward_days
    summaries = [summarize_result(result) for result in results]
    total_attempted = sum(int(summary["symbols_attempted"]) for summary in summaries)
    total_processed = sum(int(summary["symbols_processed"]) for summary in summaries)
    total_skipped = sum(int(summary["symbols_skipped"]) for summary in summaries)
    total_candidates = sum(int(summary["candidates_found"]) for summary in summaries)
    aggregate_density = total_candidates / total_processed if total_processed else 0.0
    lines.extend(
        [
            f"- Stage families: {', '.join(results[0].config.stage_families)}",
            f"- Universe file: {results[0].config.universe_file}",
            f"- Symbols attempted: {total_attempted}",
            f"- Symbols processed: {total_processed}",
            f"- Symbols skipped: {total_skipped}",
            f"- Candidates found: {total_candidates}",
            f"- Candidate density: {aggregate_density:.4f}",
            "",
            "## Runs",
            "",
            "| D Date | Processed | Skipped | Candidates | Density |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for summary in summaries:
        lines.append(
            f"| {summary['d_date']} | {summary['symbols_processed']} | {summary['symbols_skipped']} | "
            f"{summary['candidates_found']} | {float(summary['candidate_density']):.4f} |"
        )

    lines.extend(["", "## Aggregate Forward Outcomes", "", "| Horizon | Evaluated | Positive | Hit Rate | Average Return | Median Return |", "|---|---:|---:|---:|---:|---:|"])
    candidate_rows = [
        row
        for result in results
        for row in result.detail_rows
        if row.get("CandidateClass") in {"SELECTED", "WATCH"}
    ]
    for days in forward_days:
        values = [_number(row.get(f"DPlus{days}ReturnPct")) for row in candidate_rows if row.get(f"DPlus{days}ReturnPct") is not None]
        numeric_values = [value for value in values if value is not None]
        positives = [value for value in numeric_values if value > 0]
        hit_rate = len(positives) / len(numeric_values) if numeric_values else 0.0
        average_return = _mean(numeric_values)
        median_return = _median(numeric_values)
        lines.append(
            f"| D+{days} | {len(numeric_values)} | {len(positives)} | {hit_rate:.2%} | "
            f"{_format_pct_value(average_return)} | {_format_pct_value(median_return)} |"
        )
    _append_aggregate_path_outcomes(lines, candidate_rows, forward_days)
    _append_group_path_outcomes(lines, "Stage Family Path Outcomes", _group_path_outcomes(candidate_rows, "StageFamily", forward_days), forward_days)
    _append_group_path_outcomes(lines, "Candidate State Path Outcomes", _group_path_outcomes(candidate_rows, "CandidateStateRaw", forward_days), forward_days)
    _append_ranking_collision_buckets(lines, _ranking_collision_buckets([row for result in results for row in result.detail_rows]))
    return "\n".join(lines) + "\n"


def row_value(row: dict[str, Any], key: str) -> str:
    value = row.get(key)
    return "" if value is None else str(value)


def _append_group_outcomes(
    lines: list[str],
    title: str,
    outcomes: object,
    forward_days: tuple[int, ...],
    *,
    group_order: tuple[str, ...] = (),
) -> None:
    if not isinstance(outcomes, dict) or not outcomes:
        return
    for days in forward_days:
        ordered_groups = _ordered_groups(outcomes, group_order)
        rows: list[str] = []
        for group in ordered_groups:
            metrics = outcomes.get(group)
            if not isinstance(metrics, dict):
                continue
            evaluated = int(metrics.get(f"d_plus_{days}_evaluated", 0))
            if evaluated == 0:
                continue
            candidates = int(metrics.get("candidates", 0))
            positive = int(metrics.get(f"d_plus_{days}_positive", 0))
            hit_rate = float(metrics.get(f"d_plus_{days}_hit_rate", 0.0))
            average_return = _format_pct_value(metrics.get(f"d_plus_{days}_average_return_pct"))
            median_return = _format_pct_value(metrics.get(f"d_plus_{days}_median_return_pct"))
            rows.append(
                f"| {group} | {candidates} | {evaluated} | {positive} | {hit_rate:.2%} | {average_return} | {median_return} |"
            )
        if rows:
            lines.extend(
                [
                    "",
                    f"## {title} D+{days}",
                    "",
                    "| Group | Candidates | Evaluated | Positive | Hit Rate | Average Return | Median Return |",
                    "|---|---:|---:|---:|---:|---:|---:|",
                ]
            )
            lines.extend(rows)


def _append_group_path_outcomes(
    lines: list[str],
    title: str,
    outcomes: object,
    forward_days: tuple[int, ...],
) -> None:
    if not isinstance(outcomes, dict) or not outcomes:
        return
    for days in forward_days:
        rows: list[str] = []
        for group in _ordered_groups(outcomes, ()):
            metrics = outcomes.get(group)
            if not isinstance(metrics, dict):
                continue
            evaluated = int(metrics.get(f"d_plus_{days}_path_evaluated", 0))
            if evaluated == 0:
                continue
            candidates = int(metrics.get("candidates", 0))
            average_worst = _format_pct_value(metrics.get(f"d_plus_{days}_average_worst_low_return_pct"))
            median_worst = _format_pct_value(metrics.get(f"d_plus_{days}_median_worst_low_return_pct"))
            average_best = _format_pct_value(metrics.get(f"d_plus_{days}_average_best_high_return_pct"))
            median_best = _format_pct_value(metrics.get(f"d_plus_{days}_median_best_high_return_pct"))
            rows.append(
                f"| {group} | {candidates} | {evaluated} | {average_worst} | {median_worst} | {average_best} | {median_best} |"
            )
        if rows:
            lines.extend(
                [
                    "",
                    f"## {title} D+{days}",
                    "",
                    "| Group | Candidates | Evaluated | Avg Worst Low | Median Worst Low | Avg Best High | Median Best High |",
                    "|---|---:|---:|---:|---:|---:|---:|",
                ]
            )
            lines.extend(rows)


def _append_aggregate_path_outcomes(lines: list[str], rows: list[dict[str, Any]], forward_days: tuple[int, ...]) -> None:
    path_metrics = _path_metrics(rows, forward_days)
    table_rows: list[str] = []
    for days in forward_days:
        evaluated = int(path_metrics.get(f"d_plus_{days}_path_evaluated", 0))
        if evaluated == 0:
            continue
        table_rows.append(
            f"| D+{days} | {evaluated} | "
            f"{_format_pct_value(path_metrics.get(f'd_plus_{days}_average_worst_low_return_pct'))} | "
            f"{_format_pct_value(path_metrics.get(f'd_plus_{days}_median_worst_low_return_pct'))} | "
            f"{_format_pct_value(path_metrics.get(f'd_plus_{days}_average_best_high_return_pct'))} | "
            f"{_format_pct_value(path_metrics.get(f'd_plus_{days}_median_best_high_return_pct'))} |"
        )
    if table_rows:
        lines.extend(
            [
                "",
                "## Aggregate Forward Path Outcomes",
                "",
                "| Horizon | Evaluated | Avg Worst Low | Median Worst Low | Avg Best High | Median Best High |",
                "|---|---:|---:|---:|---:|---:|",
            ]
        )
        lines.extend(table_rows)


def _append_ranking_collision_buckets(lines: list[str], buckets: object) -> None:
    if not isinstance(buckets, dict) or not buckets:
        return
    lines.extend(["", "## Ranking Collision Buckets", "", "| Active Families Before Ranking | Rows |", "|---|---:|"])
    for bucket, count in sorted(buckets.items(), key=lambda item: (-int(item[1]), str(item[0]))):
        if int(count):
            lines.append(f"| {bucket} | {count} |")


def _ordered_groups(outcomes: dict[object, object], group_order: tuple[str, ...]) -> list[str]:
    keys = [str(key) for key in outcomes.keys()]
    ordered = [group for group in group_order if group in keys]
    ordered.extend(sorted(group for group in keys if group not in set(ordered)))
    return ordered


def _format_pct_value(value: object) -> str:
    try:
        return "" if value is None else f"{float(value):.2f}%"
    except (TypeError, ValueError):
        return ""


def _number(value: object, default: float | None = None) -> float | None:
    try:
        return default if value is None else float(value)
    except (TypeError, ValueError):
        return default


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 4)


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    midpoint = len(ordered) // 2
    if len(ordered) % 2:
        return round(ordered[midpoint], 4)
    return round((ordered[midpoint - 1] + ordered[midpoint]) / 2, 4)


def _group_path_outcomes(rows: list[dict[str, Any]], group_key: str, forward_days: tuple[int, ...]) -> dict[str, dict[str, object]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        value = row.get(group_key)
        group = str(value) if value not in {None, ""} else "UNKNOWN"
        grouped.setdefault(group, []).append(row)
    return {group: _path_metrics(group_rows, forward_days) for group, group_rows in sorted(grouped.items())}


def _path_metrics(rows: list[dict[str, Any]], forward_days: tuple[int, ...]) -> dict[str, object]:
    metrics: dict[str, object] = {"candidates": len(rows)}
    for days in forward_days:
        worst_values = [
            value
            for value in (_number(row.get(f"DPlus{days}WorstLowReturnPct")) for row in rows if row.get(f"DPlus{days}WorstLowReturnPct") is not None)
            if value is not None
        ]
        best_values = [
            value
            for value in (_number(row.get(f"DPlus{days}BestHighReturnPct")) for row in rows if row.get(f"DPlus{days}BestHighReturnPct") is not None)
            if value is not None
        ]
        metrics[f"d_plus_{days}_path_evaluated"] = min(len(worst_values), len(best_values))
        metrics[f"d_plus_{days}_average_worst_low_return_pct"] = _mean(worst_values)
        metrics[f"d_plus_{days}_median_worst_low_return_pct"] = _median(worst_values)
        metrics[f"d_plus_{days}_average_best_high_return_pct"] = _mean(best_values)
        metrics[f"d_plus_{days}_median_best_high_return_pct"] = _median(best_values)
    return metrics


def _ranking_collision_buckets(rows: list[dict[str, Any]]) -> dict[str, int]:
    buckets: dict[str, int] = {}
    for row in rows:
        bucket = _ranking_collision_bucket(row)
        buckets[bucket] = buckets.get(bucket, 0) + 1
    return buckets


def _ranking_collision_bucket(row: dict[str, Any]) -> str:
    active_families = []
    for part in str(row.get("RankingCandidateStates") or "").split("|"):
        family, separator, state = part.partition(":")
        if separator and family and state and state != "STATUS_QUO":
            active_families.append(family)
    return "+".join(sorted(active_families)) if active_families else "NONE"


def _candidate_rows_from_csvs(detail_paths: tuple[str | Path, ...]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for detail_path in detail_paths:
        path = Path(detail_path)
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                if row.get("CandidateClass") not in {"SELECTED", "WATCH"}:
                    continue
                enriched = dict(row)
                enriched["_SourceFile"] = str(path)
                if not enriched.get("DDate"):
                    enriched["DDate"] = _date_from_filename(path)
                rows.append(enriched)
    return rows


def _group_rows(rows: list[dict[str, Any]], key: str) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        group = row_value(row, key) or "UNKNOWN"
        grouped.setdefault(group, []).append(row)
    return dict(sorted(grouped.items()))


def _rows_by_exploded_risk_tag(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    exploded: list[dict[str, Any]] = []
    for row in rows:
        tags = [tag.strip() for tag in row_value(row, "RiskTags").split(",") if tag.strip()]
        if not tags:
            tags = ["NO_RISK_TAG"]
        for tag in tags:
            tagged = dict(row)
            tagged["_RiskTag"] = tag
            exploded.append(tagged)
    return exploded


def _rows_by_ranking_collision_bucket(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    bucketed: list[dict[str, Any]] = []
    for row in rows:
        bucketed_row = dict(row)
        bucketed_row["_RankingCollisionBucket"] = _ranking_collision_bucket(row)
        bucketed.append(bucketed_row)
    return bucketed


def _filter_rows(
    rows: list[dict[str, Any]],
    *,
    stage_family: str = "",
    candidate_state: str = "",
    sector: str = "",
) -> list[dict[str, Any]]:
    filtered = rows
    if stage_family:
        expected = stage_family.upper()
        filtered = [row for row in filtered if row_value(row, "StageFamily").upper() == expected]
    if candidate_state:
        expected = candidate_state.upper()
        filtered = [
            row
            for row in filtered
            if row_value(row, "CandidateStateRaw").upper() == expected or row_value(row, "CandidateState").upper() == expected
        ]
    if sector:
        expected = sector.upper()
        filtered = [row for row in filtered if row_value(row, "Sector").upper() == expected]
    return filtered


def _append_calibration_split(lines: list[str], title: str, rows: list[dict[str, Any]], key: str, horizon_days: int) -> None:
    grouped = _group_rows(rows, key)
    if not grouped:
        return
    lines.extend(["", f"## {title}", "", f"| {key} | Candidates | Endpoint Avg | Avg Worst Low | Median Worst Low | Worst Low <= -10% | Avg Best High |", "|---|---:|---:|---:|---:|---:|---:|"])
    for group, group_rows in grouped.items():
        metrics = _calibration_metrics(group_rows, horizon_days)
        lines.append(
            f"| {group} | {len(group_rows)} | {metrics['endpoint_avg']} | {metrics['worst_avg']} | "
            f"{metrics['worst_median']} | {metrics['worst_lte_10']} | {metrics['best_avg']} |"
        )


def _append_stage_family_split(lines: list[str], title: str, rows: list[dict[str, Any]], key: str, horizon_days: int) -> None:
    grouped = _group_rows(rows, key)
    if not grouped:
        return
    lines.extend(
        [
            "",
            f"## {title}",
            "",
            "| Group | Candidates | Endpoint Hit Rate | Endpoint Avg | Endpoint Median | Avg Worst Low | Median Worst Low | Avg Best High | Median Best High |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for group, group_rows in grouped.items():
        metrics = _calibration_metrics(group_rows, horizon_days)
        lines.append(
            f"| {group} | {len(group_rows)} | {metrics['hit_rate']} | {metrics['endpoint_avg']} | "
            f"{metrics['endpoint_median']} | {metrics['worst_avg']} | {metrics['worst_median']} | "
            f"{metrics['best_avg']} | {metrics['best_median']} |"
        )


def _append_winner_family_collision_split(lines: list[str], rows: list[dict[str, Any]], horizon_days: int) -> None:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        bucket = _ranking_collision_bucket(row)
        family = row_value(row, "StageFamily") or row_value(row, "RankingWinnerFamily") or "UNKNOWN"
        grouped.setdefault((bucket, family), []).append(row)
    if not grouped:
        return
    lines.extend(
        [
            "",
            "## Winner Family vs Ranking Collision",
            "",
            "| Ranking Bucket | Winner Family | Candidates | Endpoint Hit Rate | Endpoint Avg | Endpoint Median | Avg Worst Low | Median Worst Low | Avg Best High | Median Best High |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for bucket, family in sorted(grouped):
        group_rows = grouped[(bucket, family)]
        metrics = _calibration_metrics(group_rows, horizon_days)
        lines.append(
            f"| {bucket} | {family} | {len(group_rows)} | {metrics['hit_rate']} | {metrics['endpoint_avg']} | "
            f"{metrics['endpoint_median']} | {metrics['worst_avg']} | {metrics['worst_median']} | "
            f"{metrics['best_avg']} | {metrics['best_median']} |"
        )


def _append_integrated_worst_rows(lines: list[str], rows: list[dict[str, Any]], horizon_days: int, *, limit: int) -> None:
    endpoint_key = f"DPlus{horizon_days}ReturnPct"
    rows_with_endpoint = [row for row in rows if _number(row.get(endpoint_key)) is not None]
    lines.extend(
        [
            "",
            "## Worst Endpoint Rows",
            "",
            "| D Date | Symbol | Sector | Stage Family | Candidate State | Class | Priority | Ranking Bucket | Endpoint | Worst Low | Best High | Risk Tags |",
            "|---|---|---|---|---|---|---|---|---:|---:|---:|---|",
        ]
    )
    for row in sorted(rows_with_endpoint, key=lambda item: _number(item.get(endpoint_key), 0.0) or 0.0)[:limit]:
        lines.append(
            f"| {row_value(row, 'DDate') or _date_from_source(row)} | {row_value(row, 'Symbol')} | "
            f"{row_value(row, 'Sector') or 'UNKNOWN'} | {row_value(row, 'StageFamily') or 'UNKNOWN'} | "
            f"{row_value(row, 'CandidateStateRaw') or row_value(row, 'CandidateState')} | "
            f"{row_value(row, 'CandidateClass')} | {row_value(row, 'ReviewPriority')} | "
            f"{_ranking_collision_bucket(row)} | {_format_pct_value(row.get(endpoint_key))} | "
            f"{_format_pct_value(row.get(f'DPlus{horizon_days}WorstLowReturnPct'))} | "
            f"{_format_pct_value(row.get(f'DPlus{horizon_days}BestHighReturnPct'))} | "
            f"{row_value(row, 'RiskTags') or 'none'} |"
        )


def _calibration_metrics(rows: list[dict[str, Any]], horizon_days: int) -> dict[str, str]:
    endpoint_values = _numeric_column(rows, f"DPlus{horizon_days}ReturnPct")
    worst_values = _numeric_column(rows, f"DPlus{horizon_days}WorstLowReturnPct")
    best_values = _numeric_column(rows, f"DPlus{horizon_days}BestHighReturnPct")
    positives = [value for value in endpoint_values if value > 0]
    worst_lte_10 = [value for value in worst_values if value <= -10.0]
    worst_lte_20 = [value for value in worst_values if value <= -20.0]
    return {
        "hit_rate": _format_ratio(len(positives), len(endpoint_values)),
        "endpoint_avg": _format_pct_value(_mean(endpoint_values)),
        "endpoint_median": _format_pct_value(_median(endpoint_values)),
        "worst_avg": _format_pct_value(_mean(worst_values)),
        "worst_median": _format_pct_value(_median(worst_values)),
        "worst_lte_10": _format_ratio(len(worst_lte_10), len(worst_values)),
        "worst_lte_20": _format_ratio(len(worst_lte_20), len(worst_values)),
        "best_avg": _format_pct_value(_mean(best_values)),
        "best_median": _format_pct_value(_median(best_values)),
    }


def _numeric_column(rows: list[dict[str, Any]], key: str) -> list[float]:
    return [value for value in (_number(row.get(key)) for row in rows) if value is not None]


def _worst_rows(rows: list[dict[str, Any]], horizon_days: int, *, limit: int) -> list[dict[str, Any]]:
    key = f"DPlus{horizon_days}WorstLowReturnPct"
    with_values = [row for row in rows if _number(row.get(key)) is not None]
    return sorted(with_values, key=lambda row: _number(row.get(key), 0.0) or 0.0)[:limit]


def _repeated_symbol_failures(rows: list[dict[str, Any]], horizon_days: int) -> list[tuple[str, dict[str, Any]]]:
    grouped = _group_rows(rows, "Symbol")
    repeated: list[tuple[str, dict[str, Any]]] = []
    for symbol, symbol_rows in grouped.items():
        if len(symbol_rows) < 2:
            continue
        values = _numeric_column(symbol_rows, f"DPlus{horizon_days}ReturnPct")
        if not values:
            continue
        dates = sorted({row_value(row, "DDate") or _date_from_source(row) for row in symbol_rows})
        repeated.append(
            (
                symbol,
                {
                    "rows": len(symbol_rows),
                    "average": _mean(values),
                    "worst": min(values),
                    "best": max(values),
                    "dates": dates,
                },
            )
        )
    return sorted(repeated, key=lambda item: (item[1]["average"], item[0]))


def _format_ratio(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return ""
    return f"{numerator / denominator:.2%}"


def _date_from_source(row: dict[str, Any]) -> str:
    source = row.get("_SourceFile")
    return _date_from_filename(Path(str(source))) if source else "UNKNOWN"


def _date_from_filename(path: Path) -> str:
    matches = re.findall(r"(20\d{2})(\d{2})(\d{2})", path.stem)
    if not matches:
        return ""
    year, month, day = matches[-1]
    return f"{year}-{month}-{day}"
