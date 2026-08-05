import csv
import sys
import tempfile
import unittest
from collections import Counter
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import Live_Scanner_v19 as v19
import V19_Backtest_Matrix as matrix


def make_history(periods: int = 700, daily_growth: float = 0.006) -> pd.DataFrame:
    index = pd.bdate_range("2021-01-04", periods=periods)
    close = 20.0 * np.power(1.0 + daily_growth, np.arange(periods))
    return pd.DataFrame(
        {
            "Open": close * 0.999,
            "High": close * 1.01,
            "Low": close * 0.99,
            "Close": close,
            "Volume": np.full(periods, 1_000_000.0),
        },
        index=index,
    )


def make_config(output_path: Path, **overrides) -> matrix.MatrixConfig:
    values = {
        "input_source": "test codes",
        "date_source": "test dates",
        "raw_code_count": 1,
        "duplicate_code_count": 0,
        "raw_date_count": 1,
        "duplicate_date_count": 0,
        "output_path": output_path,
        "overwrite": True,
        "workers": 2,
        "max_attempts": 3,
        "request_timeout": 5.0,
        "request_interval": 0.0,
        "retry_base_seconds": 0.0,
        "history_lookback_days": 1100,
        "progress_every": 25,
        "stoch_zone_low": 45.0,
        "stoch_zone_high": 55.0,
        "calendar_symbol": "SPY",
        "date_range_start": None,
        "date_range_end": None,
    }
    values.update(overrides)
    return matrix.MatrixConfig(**values)


class MatrixOutcomeTests(unittest.TestCase):
    def test_d_candle_is_outcome_only_and_never_changes_qualification(self):
        history = make_history()
        d_timestamp = history.index[550]
        execution_date = d_timestamp.date()
        d1_close = float(history.loc[history.index[549], "Close"])

        positive = history.copy()
        positive.loc[d_timestamp, ["Open", "High", "Low", "Close"]] = [
            d1_close * 1.02,
            d1_close * 2.10,
            d1_close * 0.30,
            d1_close * 0.40,
        ]
        negative = history.copy()
        negative.loc[d_timestamp, ["Open", "High", "Low", "Close"]] = [
            d1_close * 0.98,
            d1_close * 4.00,
            d1_close * 0.10,
            d1_close * 3.00,
        ]

        with tempfile.TemporaryDirectory() as directory:
            config = make_config(Path(directory) / "matrix.csv")
            positive_row = matrix.evaluate_dates_from_history(
                0, "TEST", [execution_date], positive, config, 1
            )[0]
            negative_row = matrix.evaluate_dates_from_history(
                0, "TEST", [execution_date], negative, config, 1
            )[0]

        self.assertTrue(positive_row["D_Open_Positive"])
        self.assertFalse(negative_row["D_Open_Positive"])
        self.assertEqual(positive_row["Qualification_Status"], negative_row["Qualification_Status"])
        for field in (
            "D1_Close",
            "EMA_50",
            "EMA_200",
            "MACD_Line",
            "MACD_Signal",
            "Return_Short",
            "Return_Medium",
            "Return_Long",
        ):
            self.assertAlmostEqual(float(positive_row[field]), float(negative_row[field]), places=12)

    def test_weekend_has_qualification_but_no_d_open_outcome(self):
        history = make_history()
        friday = history.index[549]
        saturday = friday.date() + pd.Timedelta(days=1)
        with tempfile.TemporaryDirectory() as directory:
            config = make_config(Path(directory) / "matrix.csv")
            row = matrix.evaluate_dates_from_history(0, "TEST", [saturday], history, config, 1)[0]
        self.assertNotEqual(row["Qualification_Status"], v19.STATUS_INVALID)
        self.assertEqual(row["Outcome_Status"], "D_CANDLE_UNAVAILABLE")
        self.assertIsNone(row["D_Open_Positive"])


class MatrixScaleAndInputTests(unittest.TestCase):
    def test_one_download_per_symbol_for_multiple_dates(self):
        histories = {"AAA": make_history(), "BBB": make_history(daily_growth=0.0055)}
        dates = [histories["AAA"].index[520].date(), histories["AAA"].index[560].date()]
        calls = Counter()

        def fetcher(symbol, start_date, end_date, timeout):
            calls[symbol] += 1
            return histories[symbol]

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "matrix.csv"
            config = make_config(
                output,
                raw_code_count=2,
                raw_date_count=2,
                progress_every=1,
            )
            summary, stats = matrix.run_matrix(["AAA", "BBB"], dates, config, fetcher=fetcher)
            with output.open("r", encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))

        self.assertEqual(calls, Counter({"AAA": 1, "BBB": 1}))
        self.assertEqual(stats.request_attempts, 2)
        self.assertEqual(summary["rows_written"], 4)
        self.assertEqual(len(rows), 4)
        self.assertEqual([int(row["Pair_Index"]) for row in rows], [0, 1, 2, 3])

    def test_preflight_deduplicates_codes_and_dates(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "matrix.csv"
            config, symbols, dates = matrix.preflight(
                [
                    "--codes",
                    "AAPL,MSFT",
                    "AAPL",
                    "--dates",
                    "2024-05-01,2024-05-02",
                    "2024-05-01",
                    "--output",
                    str(output),
                ]
            )
        self.assertEqual(symbols, ["AAPL", "MSFT"])
        self.assertEqual(dates, [date(2024, 5, 1), date(2024, 5, 2)])
        self.assertEqual(config.duplicate_code_count, 1)
        self.assertEqual(config.duplicate_date_count, 1)

    def test_date_range_uses_calendar_candles_only(self):
        calendar = make_history(periods=30)
        range_start = calendar.index[5].date()
        range_end = calendar.index[12].date()
        expected = [stamp.date() for stamp in calendar.loc[str(range_start) : str(range_end)].index]

        def fetcher(symbol, start_date, end_date, timeout):
            self.assertEqual(symbol, "SPY")
            return calendar

        with tempfile.TemporaryDirectory() as directory:
            config = make_config(
                Path(directory) / "matrix.csv",
                date_range_start=range_start,
                date_range_end=range_end,
            )
            dates = matrix.resolve_range_dates(
                config,
                fetcher,
                v19.ProviderGuard(0.0),
                v19.RetryStatistics(),
            )
        self.assertEqual(dates, expected)


if __name__ == "__main__":
    unittest.main()
