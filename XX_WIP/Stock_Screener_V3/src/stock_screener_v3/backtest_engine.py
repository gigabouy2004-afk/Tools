from __future__ import annotations

from collections import Counter
from datetime import datetime
from statistics import mean, median
from typing import Protocol

import pandas as pd

from stock_screener_v3.backtesting import forward_best_high_return, forward_return, forward_worst_low_return, slice_as_of
from stock_screener_v3.data_provider import PriceProvider
from stock_screener_v3.models import (
    BacktestResult,
    BacktestRunConfig,
    CandidateClass,
    PriceDataBundle,
    StageEvaluation,
    UniverseRecord,
)
from stock_screener_v3.regime_config import RegimeBenchmarkConfig
from stock_screener_v3.universe import deterministic_sample, filter_records


class StageEvaluator(Protocol):
    def evaluate(self, record: UniverseRecord, prices: PriceDataBundle) -> StageEvaluation:
        """Evaluate one symbol using as-of price data only."""


class InMemoryPriceProvider:
    def __init__(self, frames: dict[str, pd.DataFrame]):
        self.frames = frames

    def daily(self, symbol: str) -> pd.DataFrame:
        try:
            return self.frames[symbol]
        except KeyError as exc:
            raise ValueError(f"No daily data for {symbol}.") from exc


class BacktestEngine:
    def __init__(
        self,
        price_provider: PriceProvider,
        evaluator: StageEvaluator,
        regime_config: RegimeBenchmarkConfig | None = None,
    ):
        self.price_provider = price_provider
        self.evaluator = evaluator
        self.regime_config = regime_config or RegimeBenchmarkConfig.default()
        self._daily_cache: dict[str, pd.DataFrame] = {}

    def run(self, records: list[UniverseRecord], config: BacktestRunConfig) -> BacktestResult:
        selected_records = filter_records(
            records,
            sectors=config.sector_filters,
            exchanges=config.exchange_filters,
        )
        selected_records = deterministic_sample(
            selected_records,
            sample_size=config.sample_size,
            random_seed=config.random_seed,
        )
        detail_rows: list[dict[str, object]] = []
        skip_reasons: Counter[str] = Counter()
        processed = 0
        candidates = 0
        cutoff = pd.Timestamp(config.d_date) + pd.Timedelta(hours=23, minutes=59, seconds=59)

        for record in selected_records:
            try:
                full_daily = self.price_provider.daily(record.yahoo_symbol)
                historical = slice_as_of(full_daily, cutoff)
                bundle = PriceDataBundle(
                    symbol=record.yahoo_symbol,
                    daily=historical.frame,
                    benchmarks=self._benchmarks(record, cutoff),
                    as_of=historical.as_of,
                    provider=type(self.price_provider).__name__,
                )
                evaluation = self.evaluator.evaluate(record, bundle)
                processed += 1
                is_candidate = evaluation.candidate_class in {CandidateClass.SELECTED, CandidateClass.WATCH}
                if is_candidate:
                    candidates += 1
                row = self._detail_row(record, evaluation, full_daily, cutoff, config.forward_days)
                detail_rows.append(row)
            except Exception as exc:
                skip_reasons[str(exc)] += 1

        return BacktestResult(
            config=config,
            generated_at=datetime.now(),
            symbols_attempted=len(selected_records),
            symbols_processed=processed,
            symbols_skipped=sum(skip_reasons.values()),
            candidates_found=candidates,
            detail_rows=tuple(detail_rows),
            skip_reasons=dict(skip_reasons),
        )

    def _benchmarks(self, record: UniverseRecord, cutoff: pd.Timestamp) -> dict[str, pd.DataFrame]:
        benchmarks: dict[str, pd.DataFrame] = {}
        market_symbol = self.regime_config.market_symbol_for(record)
        market_frame = self._benchmark_as_of(market_symbol, cutoff)
        if market_frame is not None:
            benchmarks["market"] = market_frame
        sector_symbol = self.regime_config.sector_symbol_for(record)
        if sector_symbol:
            sector_frame = self._benchmark_as_of(sector_symbol, cutoff)
            if sector_frame is not None:
                benchmarks["sector"] = sector_frame
        return benchmarks

    def _benchmark_as_of(self, symbol: str, cutoff: pd.Timestamp) -> pd.DataFrame | None:
        try:
            return slice_as_of(self._daily(symbol), cutoff).frame
        except Exception:
            return None

    def _daily(self, symbol: str) -> pd.DataFrame:
        if symbol not in self._daily_cache:
            self._daily_cache[symbol] = self.price_provider.daily(symbol)
        return self._daily_cache[symbol]

    @staticmethod
    def _detail_row(
        record: UniverseRecord,
        evaluation: StageEvaluation,
        full_daily: pd.DataFrame,
        cutoff: pd.Timestamp,
        forward_days: tuple[int, ...],
    ) -> dict[str, object]:
        row: dict[str, object] = {
            "Symbol": record.symbol,
            "YahooSymbol": record.yahoo_symbol,
            "CompanyName": record.company_name,
            "Exchange": record.exchange,
            "Sector": record.sector,
            "Industry": record.industry,
            "CandidateState": evaluation.candidate_state,
            "CandidateClass": evaluation.candidate_class.value,
            "ReviewPriority": evaluation.review_priority.value,
            "Confidence": evaluation.confidence,
            "TotalScore": evaluation.score.total_score,
            "RouteScore": evaluation.score.route_score,
            "TimingScore": evaluation.score.timing_score,
            "StructureScore": evaluation.score.structure_score,
            "ParticipationScore": evaluation.score.participation_score,
            "ContextScore": evaluation.score.context_score,
            "RiskScore": evaluation.score.risk_score,
            "ReasonCodes": ",".join(evaluation.reason_codes),
            "RiskTags": ",".join(evaluation.risk_tags),
        }
        row.update(evaluation.diagnostics)
        for days in forward_days:
            row[f"DPlus{days}ReturnPct"] = forward_return(full_daily, cutoff, days)
            row[f"DPlus{days}WorstLowReturnPct"] = forward_worst_low_return(full_daily, cutoff, days)
            row[f"DPlus{days}BestHighReturnPct"] = forward_best_high_return(full_daily, cutoff, days)
        row["OutcomeCategory"] = outcome_category(row, forward_days)
        row["FailureCategory"] = failure_category(row, forward_days)
        return row


def summarize_result(result: BacktestResult) -> dict[str, object]:
    detail_rows = [
        row
        for row in result.detail_rows
        if row.get("CandidateClass") in {CandidateClass.SELECTED.value, CandidateClass.WATCH.value}
    ]
    summary = result.summary_dict()
    for days in result.config.forward_days:
        key = f"DPlus{days}ReturnPct"
        values = [_number(row.get(key)) for row in detail_rows if row.get(key) is not None]
        numeric_values = [value for value in values if value is not None]
        positive = [value for value in numeric_values if value > 0]
        summary[f"d_plus_{days}_evaluated"] = len(numeric_values)
        summary[f"d_plus_{days}_positive"] = len(positive)
        summary[f"d_plus_{days}_hit_rate"] = len(positive) / len(numeric_values) if numeric_values else 0.0
        summary[f"d_plus_{days}_average_return_pct"] = round(mean(numeric_values), 4) if numeric_values else None
        summary[f"d_plus_{days}_median_return_pct"] = round(median(numeric_values), 4) if numeric_values else None
    summary["failure_categories"] = dict(_counter_for_key(detail_rows, "FailureCategory"))
    summary["score_buckets"] = dict(_score_buckets(detail_rows))
    summary["score_bucket_outcomes"] = _group_outcomes(detail_rows, "ScoreBucket", result.config.forward_days)
    summary["stage_family_outcomes"] = _group_outcomes(detail_rows, "StageFamily", result.config.forward_days)
    summary["stage_family_path_outcomes"] = _group_path_outcomes(detail_rows, "StageFamily", result.config.forward_days)
    summary["candidate_state_path_outcomes"] = _group_path_outcomes(detail_rows, "CandidateStateRaw", result.config.forward_days)
    summary["sector_outcomes"] = _group_outcomes(detail_rows, "Sector", result.config.forward_days)
    summary["review_priority_outcomes"] = _group_outcomes(detail_rows, "ReviewPriority", result.config.forward_days)
    summary["risk_tag_outcomes"] = _risk_tag_outcomes(detail_rows, result.config.forward_days)
    summary["ranking_collision_buckets"] = dict(_ranking_collision_buckets(list(result.detail_rows)))
    return summary


def outcome_category(row: dict[str, object], forward_days: tuple[int, ...]) -> str:
    if row.get("CandidateClass") not in {CandidateClass.SELECTED.value, CandidateClass.WATCH.value}:
        return "NOT_CANDIDATE"
    values = [_number(row.get(f"DPlus{days}ReturnPct")) for days in forward_days]
    evaluated = [value for value in values if value is not None]
    if not evaluated:
        return "UNEVALUATED"
    if any(value > 0 for value in evaluated):
        return "POSITIVE_FOLLOW_THROUGH"
    return "FAILED_FOLLOW_THROUGH"


def failure_category(row: dict[str, object], forward_days: tuple[int, ...]) -> str:
    if outcome_category(row, forward_days) != "FAILED_FOLLOW_THROUGH":
        return ""

    risk_tags = {
        tag.strip()
        for tag in str(row.get("RiskTags") or "").split(",")
        if tag.strip()
    }
    if "LOW_LIQUIDITY" in risk_tags:
        return "LIQUIDITY_RISK"
    if "BELOW_EMA200" in risk_tags or _number(row.get("StructureScore"), 0.0) < 10:
        return "STRUCTURE_FAILURE"
    if _number(row.get("ParticipationScore"), 0.0) < 10:
        return "PARTICIPATION_FAILURE"
    if _number(row.get("ContextScore"), 0.0) < 8:
        return "ACCEPTANCE_CONTEXT_FAILURE"
    return "FOLLOW_THROUGH_FAILURE"


def _counter_for_key(rows: list[dict[str, object]], key: str) -> Counter[str]:
    values = [str(row.get(key)) for row in rows if row.get(key)]
    return Counter(values)


def _score_buckets(rows: list[dict[str, object]]) -> Counter[str]:
    buckets: Counter[str] = Counter()
    for row in rows:
        score = _number(row.get("TotalScore"))
        if score is None:
            continue
        if score >= 80:
            buckets["80+"] += 1
        elif score >= 70:
            buckets["70-79"] += 1
        elif score >= 60:
            buckets["60-69"] += 1
        elif score >= 50:
            buckets["50-59"] += 1
        else:
            buckets["<50"] += 1
    return buckets


def _ranking_collision_buckets(rows: list[dict[str, object]]) -> Counter[str]:
    buckets: Counter[str] = Counter()
    for row in rows:
        states = str(row.get("RankingCandidateStates") or "")
        active_families = []
        for part in states.split("|"):
            family, separator, state = part.partition(":")
            if separator and family and state and state != "STATUS_QUO":
                active_families.append(family)
        bucket = "+".join(sorted(active_families)) if active_families else "NONE"
        buckets[bucket] += 1
    return buckets


def _group_outcomes(rows: list[dict[str, object]], group_key: str, forward_days: tuple[int, ...]) -> dict[str, dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        group = _group_value(row, group_key)
        grouped.setdefault(group, []).append(row)
    return {group: _outcome_metrics(group_rows, forward_days) for group, group_rows in sorted(grouped.items())}


def _risk_tag_outcomes(rows: list[dict[str, object]], forward_days: tuple[int, ...]) -> dict[str, dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        tags = [tag.strip() for tag in str(row.get("RiskTags") or "").split(",") if tag.strip()]
        if not tags:
            tags = ["NO_RISK_TAG"]
        for tag in tags:
            grouped.setdefault(tag, []).append(row)
    return {tag: _outcome_metrics(tag_rows, forward_days) for tag, tag_rows in sorted(grouped.items())}


def _group_path_outcomes(rows: list[dict[str, object]], group_key: str, forward_days: tuple[int, ...]) -> dict[str, dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        group = _group_value(row, group_key)
        grouped.setdefault(group, []).append(row)
    return {group: _path_metrics(group_rows, forward_days) for group, group_rows in sorted(grouped.items())}


def _group_value(row: dict[str, object], group_key: str) -> str:
    if group_key == "ScoreBucket":
        score = _number(row.get("TotalScore"))
        if score is None:
            return "UNKNOWN"
        if score >= 80:
            return "80+"
        if score >= 70:
            return "70-79"
        if score >= 60:
            return "60-69"
        if score >= 50:
            return "50-59"
        return "<50"
    value = row.get(group_key)
    return str(value) if value not in {None, ""} else "UNKNOWN"


def _outcome_metrics(rows: list[dict[str, object]], forward_days: tuple[int, ...]) -> dict[str, object]:
    metrics: dict[str, object] = {"candidates": len(rows)}
    for days in forward_days:
        key = f"DPlus{days}ReturnPct"
        values = [_number(row.get(key)) for row in rows if row.get(key) is not None]
        numeric_values = [value for value in values if value is not None]
        positives = [value for value in numeric_values if value > 0]
        metrics[f"d_plus_{days}_evaluated"] = len(numeric_values)
        metrics[f"d_plus_{days}_positive"] = len(positives)
        metrics[f"d_plus_{days}_hit_rate"] = len(positives) / len(numeric_values) if numeric_values else 0.0
        metrics[f"d_plus_{days}_average_return_pct"] = round(mean(numeric_values), 4) if numeric_values else None
        metrics[f"d_plus_{days}_median_return_pct"] = round(median(numeric_values), 4) if numeric_values else None
    return metrics


def _path_metrics(rows: list[dict[str, object]], forward_days: tuple[int, ...]) -> dict[str, object]:
    metrics: dict[str, object] = {"candidates": len(rows)}
    for days in forward_days:
        worst_key = f"DPlus{days}WorstLowReturnPct"
        best_key = f"DPlus{days}BestHighReturnPct"
        worst_values = [_number(row.get(worst_key)) for row in rows if row.get(worst_key) is not None]
        best_values = [_number(row.get(best_key)) for row in rows if row.get(best_key) is not None]
        numeric_worst_values = [value for value in worst_values if value is not None]
        numeric_best_values = [value for value in best_values if value is not None]
        metrics[f"d_plus_{days}_path_evaluated"] = min(len(numeric_worst_values), len(numeric_best_values))
        metrics[f"d_plus_{days}_average_worst_low_return_pct"] = round(mean(numeric_worst_values), 4) if numeric_worst_values else None
        metrics[f"d_plus_{days}_median_worst_low_return_pct"] = round(median(numeric_worst_values), 4) if numeric_worst_values else None
        metrics[f"d_plus_{days}_average_best_high_return_pct"] = round(mean(numeric_best_values), 4) if numeric_best_values else None
        metrics[f"d_plus_{days}_median_best_high_return_pct"] = round(median(numeric_best_values), 4) if numeric_best_values else None
    return metrics


def _number(value: object, default: float | None = None) -> float | None:
    try:
        return default if value is None else float(value)
    except (TypeError, ValueError):
        return default
