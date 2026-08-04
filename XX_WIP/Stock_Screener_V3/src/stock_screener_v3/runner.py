from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path

from stock_screener_v3.backtest_engine import BacktestEngine, PriceProvider, StageEvaluator
from stock_screener_v3.data_provider import YahooFinancePriceProvider
from stock_screener_v3.evaluators import StageFamilyEvaluator
from stock_screener_v3.models import BacktestResult, BacktestRunConfig
from stock_screener_v3.regime_config import RegimeBenchmarkConfig
from stock_screener_v3.reports import render_multi_date_summary_markdown
from stock_screener_v3.run_io import RUNS_DIR, RunPaths, close_run_logger, configure_run_logger, resolve_workspace_path, resolve_workspace_root, write_run_artifacts
from stock_screener_v3.universe import load_universe_records


@dataclass(frozen=True)
class EngineRunResult:
    result: BacktestResult
    paths: RunPaths


@dataclass(frozen=True)
class EngineRunPackResult:
    runs: tuple[EngineRunResult, ...]
    summary_output: Path


def run_backtest(
    *,
    workspace_root: str | Path,
    universe_file: str | Path,
    d_date: date,
    sectors: tuple[str, ...] = (),
    exchanges: tuple[str, ...] = (),
    sample_size: int | None = None,
    random_seed: int | None = None,
    forward_days: tuple[int, ...] = (1, 2, 5),
    stage_families: tuple[str, ...] = ("CROSSOVER", "MOMENTUM_SETUP", "DIVERGENCE"),
    run_label: str = "v3_backtest",
    details_output: str | Path | None = None,
    summary_output: str | Path | None = None,
    log_file: str | Path | None = None,
    price_provider: PriceProvider | None = None,
    evaluator: StageEvaluator | None = None,
    regime_config: RegimeBenchmarkConfig | None = None,
) -> EngineRunResult:
    paths = RunPaths.for_backtest(
        workspace_root,
        universe_file,
        d_date,
        run_label=run_label,
        details_output=details_output,
        summary_output=summary_output,
        log_file=log_file,
    )
    logger = configure_run_logger(paths.log_file)
    run_parameters = {
        "workspace_root": str(paths.workspace_root),
        "universe_file": str(paths.input_path),
        "d_date": d_date.isoformat(),
        "sectors": sectors,
        "exchanges": exchanges,
        "sample_size": sample_size,
        "random_seed": random_seed,
        "forward_days": forward_days,
        "stage_families": stage_families,
        "details_output": str(paths.details_output),
        "summary_output": str(paths.summary_output),
        "log_file": str(paths.log_file),
    }
    logger.info("V3 run queued with parameters: %s", json.dumps(run_parameters, sort_keys=True))
    try:
        logger.info("V3 run started.")
        records = load_universe_records(paths.input_path)
        logger.info("Loaded universe records: %s", len(records))
        config = BacktestRunConfig(
            universe_file=str(paths.input_path),
            d_date=d_date,
            stage_families=stage_families,
            forward_days=forward_days,
            sector_filters=sectors,
            exchange_filters=exchanges,
            sample_mode="sample" if sample_size is not None else "full",
            sample_size=sample_size,
            random_seed=random_seed,
        )
        engine = BacktestEngine(
            price_provider=price_provider or YahooFinancePriceProvider(period="5y"),
            evaluator=evaluator or StageFamilyEvaluator(stage_families=stage_families),
            regime_config=regime_config,
        )
        result = engine.run(records, config)
        write_run_artifacts(result, paths)
        logger.info(
            "V3 run completed. attempted=%s processed=%s skipped=%s candidates=%s details=%s summary=%s",
            result.symbols_attempted,
            result.symbols_processed,
            result.symbols_skipped,
            result.candidates_found,
            paths.details_output,
            paths.summary_output,
        )
        if result.skip_reasons:
            logger.info("Skip reasons: %s", json.dumps(result.skip_reasons, sort_keys=True))
        return EngineRunResult(result=result, paths=paths)
    except Exception:
        logger.exception("V3 run failed.")
        raise
    finally:
        close_run_logger(logger)


def run_backtest_pack(
    *,
    workspace_root: str | Path,
    universe_file: str | Path,
    d_dates: tuple[date, ...],
    sectors: tuple[str, ...] = (),
    exchanges: tuple[str, ...] = (),
    sample_size: int | None = None,
    random_seed: int | None = None,
    forward_days: tuple[int, ...] = (1, 2, 5),
    stage_families: tuple[str, ...] = ("CROSSOVER", "MOMENTUM_SETUP", "DIVERGENCE"),
    run_label: str = "v3_backtest_pack",
    aggregate_summary_output: str | Path | None = None,
    price_provider: PriceProvider | None = None,
    evaluator: StageEvaluator | None = None,
    regime_config: RegimeBenchmarkConfig | None = None,
) -> EngineRunPackResult:
    if not d_dates:
        raise ValueError("At least one D date is required for a backtest pack.")
    root = resolve_workspace_root(workspace_root)
    shared_provider = price_provider or YahooFinancePriceProvider(period="5y")
    runs: list[EngineRunResult] = []
    for d_date in d_dates:
        runs.append(
            run_backtest(
                workspace_root=root,
                universe_file=universe_file,
                d_date=d_date,
                sectors=sectors,
                exchanges=exchanges,
                sample_size=sample_size,
                random_seed=random_seed,
                forward_days=forward_days,
                stage_families=stage_families,
                run_label=run_label,
                price_provider=shared_provider,
                evaluator=evaluator,
                regime_config=regime_config,
            )
        )
    summary_output = resolve_workspace_path(
        root,
        aggregate_summary_output or RUNS_DIR / f"{run_label}_multi_date_summary.md",
    )
    summary_output.parent.mkdir(parents=True, exist_ok=True)
    summary_output.write_text(render_multi_date_summary_markdown(tuple(run.result for run in runs)), encoding="utf-8")
    return EngineRunPackResult(runs=tuple(runs), summary_output=summary_output)
