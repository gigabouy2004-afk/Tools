from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
import tempfile
import unittest

from stock_screener_v3.models import BacktestResult, BacktestRunConfig
from stock_screener_v3.run_io import (
    RunPaths,
    close_run_logger,
    configure_run_logger,
    resolve_workspace_path,
    write_run_artifacts,
)


class RunIoTests(unittest.TestCase):
    def test_run_paths_create_v2_style_default_artifact_names(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            universe = root / "data" / "sample.csv"
            universe.parent.mkdir()
            universe.write_text("Symbol\nAAA\n", encoding="utf-8")

            paths = RunPaths.for_backtest(root, "data/sample.csv", date(2026, 2, 11))

            self.assertEqual(universe.resolve(), paths.input_path)
            self.assertEqual(root.resolve() / "validation" / "runs" / "v3_backtest_20260211_details.csv", paths.details_output)
            self.assertEqual(root.resolve() / "validation" / "runs" / "v3_backtest_20260211_summary.md", paths.summary_output)
            self.assertEqual(root.resolve() / "validation" / "runs" / "v3_backtest_20260211.log", paths.log_file)

    def test_workspace_path_rejects_traversal_outside_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaises(ValueError):
                resolve_workspace_path(tmpdir, "../outside.csv")

    def test_workspace_path_requires_existing_input_when_requested(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaises(FileNotFoundError):
                resolve_workspace_path(tmpdir, "missing.csv", must_exist=True)

    def test_run_artifact_paths_must_be_distinct(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            universe = root / "universe.csv"
            universe.write_text("Symbol\nAAA\n", encoding="utf-8")

            with self.assertRaises(ValueError):
                RunPaths.for_backtest(
                    root,
                    universe,
                    date(2026, 2, 11),
                    details_output="validation/runs/shared.csv",
                    log_file="validation/runs/shared.csv",
                )

    def test_write_run_artifacts_creates_csv_and_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            universe = root / "universe.csv"
            universe.write_text("Symbol\nAAA\n", encoding="utf-8")
            paths = RunPaths.for_backtest(root, universe, date(2026, 2, 11))
            result = BacktestResult(
                config=BacktestRunConfig(
                    universe_file=str(paths.input_path),
                    d_date=date(2026, 2, 11),
                    stage_families=("MOCK",),
                    forward_days=(1, 2),
                ),
                generated_at=datetime(2026, 6, 2),
                symbols_attempted=1,
                symbols_processed=1,
                symbols_skipped=0,
                candidates_found=1,
                detail_rows=({"Symbol": "AAA", "CandidateClass": "SELECTED", "DPlus1ReturnPct": 1.2},),
            )

            write_run_artifacts(result, paths)

            self.assertIn("Symbol", paths.details_output.read_text(encoding="utf-8"))
            self.assertIn("V3 Backtest Summary", paths.summary_output.read_text(encoding="utf-8"))

    def test_configure_run_logger_writes_to_log_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "validation" / "runs" / "test.log"

            logger = configure_run_logger(log_file, name="stock_screener_v3.tests.run_io")
            logger.info("Queued v3 job with parameters: %s", {"d_date": "2026-02-11"})
            logger.info("V3 job completed. message=%s", "ok")
            close_run_logger(logger)

            log_text = log_file.read_text(encoding="utf-8")
            self.assertIn("Queued v3 job", log_text)
            self.assertIn("V3 job completed", log_text)


if __name__ == "__main__":
    unittest.main()
