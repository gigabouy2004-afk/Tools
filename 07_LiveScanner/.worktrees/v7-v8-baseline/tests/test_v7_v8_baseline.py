from __future__ import annotations

import importlib.util
import unittest
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def load_scanner(module_name: str, filename: str):
    spec = importlib.util.spec_from_file_location(module_name, ROOT / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


V7 = load_scanner("baseline_live_scanner_v7", "Live_Scanner_v7.py")
V8 = load_scanner("baseline_live_scanner_v8", "Live_Scanner_v8.py")
ET = ZoneInfo("America/New_York")


class BaselineImportAndConfigurationTests(unittest.TestCase):
    def test_canonical_modules_import(self):
        self.assertEqual(V7.EMA_SLOW_PERIOD, 200)
        self.assertEqual(V8.EMA_SLOW_PERIOD, 200)
        self.assertTrue(callable(V7.evaluate_frame))
        self.assertTrue(callable(V8.evaluate_frame))

    def test_preset_configuration_is_copied(self):
        first = V8.get_config("balanced")
        first["adx_trend_strong"] = -1
        second = V8.get_config("balanced")
        self.assertEqual(second["adx_trend_strong"], 20.0)

    def test_date_list_is_normalized_and_deduplicated(self):
        actual = V8.build_as_of_date_list(
            None,
            "2026-07-01, 2026-07-01, 2026-07-02",
        )
        self.assertEqual(actual, ["2026-07-01", "2026-07-02"])


class V8SessionTests(unittest.TestCase):
    def test_market_phase_boundaries(self):
        cases = [
            (datetime(2026, 8, 1, 12, 0, tzinfo=ET), "COMPLETED", "completed"),
            (datetime(2026, 7, 29, 8, 0, tzinfo=ET), "PREMARKET", "intraday"),
            (datetime(2026, 7, 29, 10, 0, tzinfo=ET), "REGULAR", "intraday"),
            (datetime(2026, 7, 29, 17, 0, tzinfo=ET), "POSTMARKET", "intraday"),
            (datetime(2026, 7, 29, 21, 0, tzinfo=ET), "COMPLETED", "completed"),
        ]
        for now, expected_phase, expected_mode in cases:
            with self.subTest(now=now):
                context = V8.get_us_market_phase(now)
                self.assertEqual(context["phase"], expected_phase)
                self.assertEqual(context["effective_mode"], expected_mode)

    def test_intraday_filter_converts_to_eastern_date(self):
        index = pd.DatetimeIndex(
            [
                "2026-07-29 03:59:00+00:00",
                "2026-07-29 14:00:00+00:00",
                "2026-07-30 01:00:00+00:00",
            ]
        )
        frame = pd.DataFrame({"close": [1.0, 2.0, 3.0]}, index=index)
        now = datetime(2026, 7, 29, 12, 0, tzinfo=ET)

        actual = V8.filter_intraday_to_today(frame, now)

        self.assertEqual(actual["close"].tolist(), [2.0, 3.0])
        self.assertTrue(all(item.date() == date(2026, 7, 29) for item in actual.index))

    def test_intraday_merge_builds_one_coherent_ohlcv_candle(self):
        daily_index = pd.DatetimeIndex(["2026-07-27", "2026-07-28"]).tz_localize(ET)
        daily = pd.DataFrame(
            {
                "open": [90.0, 95.0],
                "high": [100.0, 105.0],
                "low": [85.0, 92.0],
                "close": [98.0, 101.0],
                "volume": [1000.0, 1200.0],
            },
            index=daily_index,
        )
        minute_index = pd.DatetimeIndex(
            [
                "2026-07-29 09:30:00",
                "2026-07-29 09:31:00",
                "2026-07-29 09:32:00",
            ]
        ).tz_localize(ET)
        minute = pd.DataFrame(
            {
                "open": [102.0, 103.0, 101.0],
                "high": [104.0, 106.0, 105.0],
                "low": [101.0, 100.0, 99.0],
                "close": [103.0, 101.0, 104.0],
                "volume": [100.0, 200.0, 300.0],
            },
            index=minute_index,
        )

        merged = V8.merge_intraday_session_candle(daily, minute)
        candle = merged.iloc[-1]

        self.assertEqual(merged.index[-1].date(), date(2026, 7, 29))
        self.assertEqual(candle["open"], 102.0)
        self.assertEqual(candle["high"], 106.0)
        self.assertEqual(candle["low"], 99.0)
        self.assertEqual(candle["close"], 104.0)
        self.assertEqual(candle["volume"], 600.0)

    def test_completed_week_default_excludes_midweek_partial(self):
        index = pd.bdate_range(end="2026-07-30", periods=300)
        frame = pd.DataFrame(
            {
                "open": range(1, 301),
                "high": range(2, 302),
                "low": range(0, 300),
                "close": range(1, 301),
                "volume": 100.0,
            },
            index=index,
        )

        weekly = V8.build_weekly_data(frame, include_incomplete_week=False)

        self.assertEqual(weekly.index[-1].date(), date(2026, 7, 24))


class ConfirmedKnownDefectTests(unittest.TestCase):
    @unittest.expectedFailure
    def test_drawdown_includes_initial_equity_anchor(self):
        trades = pd.DataFrame(
            {
                "ticker": ["A", "B"],
                "return_pct": [-10.0, 20.0],
            }
        )

        summary = V8.summarize_backtest_results(trades)

        self.assertEqual(summary["max_drawdown_pct"], -10.0)

    @unittest.expectedFailure
    def test_live_friday_is_not_treated_as_a_completed_week(self):
        index = pd.bdate_range(end="2026-07-31", periods=300)
        frame = pd.DataFrame(
            {
                "open": range(1, 301),
                "high": range(2, 302),
                "low": range(0, 300),
                "close": range(1, 301),
                "volume": 100.0,
            },
            index=index,
        )

        weekly = V8.build_weekly_data(frame, include_incomplete_week=False)

        self.assertEqual(weekly.index[-1].date(), date(2026, 7, 24))


if __name__ == "__main__":
    unittest.main()
