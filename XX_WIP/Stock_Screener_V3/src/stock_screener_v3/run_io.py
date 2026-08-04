from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from stock_screener_v3.models import BacktestResult
from stock_screener_v3.reports import write_detail_csv, write_summary_markdown


RUNS_DIR = Path("validation") / "runs"
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s - %(message)s"


@dataclass(frozen=True)
class RunPaths:
    workspace_root: Path
    input_path: Path
    details_output: Path
    summary_output: Path
    log_file: Path

    @classmethod
    def for_backtest(
        cls,
        workspace_root: str | Path,
        universe_file: str | Path,
        d_date: date,
        *,
        run_label: str = "v3_backtest",
        details_output: str | Path | None = None,
        summary_output: str | Path | None = None,
        log_file: str | Path | None = None,
    ) -> "RunPaths":
        root = resolve_workspace_root(workspace_root)
        date_token = d_date.strftime("%Y%m%d")
        paths = cls(
            workspace_root=root,
            input_path=resolve_workspace_path(root, universe_file, must_exist=True),
            details_output=resolve_workspace_path(
                root,
                details_output or RUNS_DIR / f"{run_label}_{date_token}_details.csv",
            ),
            summary_output=resolve_workspace_path(
                root,
                summary_output or RUNS_DIR / f"{run_label}_{date_token}_summary.md",
            ),
            log_file=resolve_workspace_path(
                root,
                log_file or RUNS_DIR / f"{run_label}_{date_token}.log",
            ),
        )
        validate_distinct_run_artifacts(paths)
        return paths


def resolve_workspace_root(workspace_root: str | Path) -> Path:
    root = Path(workspace_root).resolve()
    if not root.exists():
        raise FileNotFoundError(f"Workspace root does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Workspace root is not a directory: {root}")
    return root


def resolve_workspace_path(root: str | Path, value: str | Path, *, must_exist: bool = False) -> Path:
    workspace_root = resolve_workspace_root(root)
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = workspace_root / candidate
    resolved = candidate.resolve()
    try:
        resolved.relative_to(workspace_root)
    except ValueError as exc:
        raise ValueError(f"Path escapes workspace root: {resolved}") from exc
    if must_exist and not resolved.exists():
        raise FileNotFoundError(f"Required input file does not exist: {resolved}")
    return resolved


def configure_run_logger(log_file: str | Path, *, name: str = "stock_screener_v3.run") -> logging.Logger:
    output = Path(log_file)
    output.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.handlers.clear()

    formatter = logging.Formatter(LOG_FORMAT)
    file_handler = logging.FileHandler(output, encoding="utf-8")
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    return logger


def validate_distinct_run_artifacts(paths: RunPaths) -> None:
    artifacts = {
        "details_output": paths.details_output.resolve(),
        "summary_output": paths.summary_output.resolve(),
        "log_file": paths.log_file.resolve(),
    }
    seen: dict[Path, str] = {}
    for label, path in artifacts.items():
        if path in seen:
            raise ValueError(f"Run artifact paths must be distinct: {seen[path]} and {label} both use {path}")
        seen[path] = label


def close_run_logger(logger: logging.Logger) -> None:
    for handler in list(logger.handlers):
        handler.flush()
        handler.close()
        logger.removeHandler(handler)


def write_run_artifacts(result: BacktestResult, paths: RunPaths) -> None:
    write_detail_csv(result, paths.details_output)
    write_summary_markdown(result, paths.summary_output)
