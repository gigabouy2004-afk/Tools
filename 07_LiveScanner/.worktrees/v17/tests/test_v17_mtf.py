import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pandas as pd

import Live_Scanner_v17 as scanner
import v17_mtf
import v17_mtf_replay
import v17_us_daily_backtest


NY = ZoneInfo("America/New_York")


def synthetic_source(session_count: int = 60) -> pd.DataFrame:
    calendar = v17_mtf.get_us_calendar()
    sessions = calendar.sessions_in_range("2026-03-01", "2026-07-28")
    sessions = sessions[-session_count:]
    rows = []
    index = []
    sequence = 0
    for session in sessions:
        open_at = calendar.session_open(session).tz_convert(NY)
        close_at = calendar.session_close(session).tz_convert(NY)
        cursor = open_at
        slot = 0
        while cursor < close_at:
            base = 100.0 + sequence * 0.08
            rows.append({
                "Open": base,
                "High": base + 0.55,
                "Low": base - 0.20,
                "Close": base + 0.40,
                "Volume": 100_000 + slot * 2_000,
            })
            index.append(cursor)
            cursor += pd.Timedelta(minutes=30)
            sequence += 1
            slot += 1
    return pd.DataFrame(rows, index=pd.DatetimeIndex(index))


class UsCalendarContractTests(unittest.TestCase):
    def test_holiday_uses_previous_completed_session(self):
        context = v17_mtf.us_market_context(
            datetime(2026, 7, 3, 12, 0, tzinfo=NY)
        )
        self.assertEqual(context["phase"], "HOLIDAY")
        self.assertEqual(context["latest_completed_session_date"], "2026-07-02")

    def test_early_close_uses_official_close(self):
        context = v17_mtf.us_market_context(
            datetime(2026, 11, 27, 13, 1, tzinfo=NY)
        )
        self.assertEqual(context["phase"], "POSTMARKET")
        self.assertTrue(context["session_close"].endswith("13:00:00-05:00"))
        self.assertEqual(
            context["latest_completed_session_date"],
            "2026-11-27",
        )

    def test_good_friday_thursday_closes_the_trading_week(self):
        self.assertTrue(v17_mtf.is_completed_us_trading_week("2026-04-02"))
        self.assertFalse(v17_mtf.is_completed_us_trading_week("2026-04-01"))

    def test_v17_scanner_context_is_completed_only(self):
        context = scanner.get_market_context(
            "AAPL",
            now=datetime(2026, 7, 28, 11, 0, tzinfo=NY),
        )
        self.assertEqual(context["phase"], "REGULAR")
        self.assertEqual(context["effective_mode"], "completed")
        self.assertEqual(context["candle_state"], "LAST_COMPLETED")
        self.assertEqual(
            context["_previous_traded_session_date"],
            "2026-07-27",
        )


class CompletedIntradayBarTests(unittest.TestCase):
    def test_active_source_bar_is_excluded(self):
        index = pd.DatetimeIndex([
            datetime(2026, 7, 28, 9, 30, tzinfo=NY),
            datetime(2026, 7, 28, 10, 0, tzinfo=NY),
        ])
        source = pd.DataFrame({
            "Open": [100, 101],
            "High": [102, 103],
            "Low": [99, 100],
            "Close": [101, 102],
            "Volume": [1000, 1200],
        }, index=index)
        completed = v17_mtf.filter_completed_regular_bars(
            source,
            cutoff=datetime(2026, 7, 28, 10, 12, tzinfo=NY),
        )
        self.assertEqual(len(completed), 1)
        self.assertEqual(completed.index[0].strftime("%H:%M"), "09:30")

    def test_session_anchored_aggregation_excludes_short_close_tails(self):
        source = synthetic_source(session_count=2)
        cutoff = source.index[-1] + pd.Timedelta(minutes=30)
        completed = v17_mtf.filter_completed_regular_bars(
            source,
            cutoff=cutoff,
        )
        one_hour = v17_mtf.aggregate_session_bars(
            completed,
            timeframe_minutes=60,
        )
        four_hour = v17_mtf.aggregate_session_bars(
            completed,
            timeframe_minutes=240,
        )
        self.assertEqual(len(one_hour), 12)
        self.assertEqual(len(four_hour), 2)
        self.assertTrue((one_hour["duration_minutes"] == 60).all())
        self.assertTrue((four_hour["duration_minutes"] == 240).all())
        self.assertFalse(one_hour["is_short_bar"].any())
        self.assertFalse(four_hour["is_short_bar"].any())
        self.assertEqual(one_hour.attrs["excluded_short_tail_count"], 2)
        self.assertEqual(four_hour.attrs["excluded_short_tail_count"], 2)
        self.assertTrue(
            all(
                one_hour.groupby("session_date")["session_date"].nunique()
                == 1
            )
        )


class MtfDiagnosticTests(unittest.TestCase):
    def test_all_indicator_families_are_calculated_on_both_timeframes(self):
        source = synthetic_source()
        cutoff = source.index[-1] + pd.Timedelta(minutes=30)
        daily = {
            "status": "BUY",
            "output_signal": "Buy_Momentum_Extension",
            "momentum_state": "LEADER",
            "v16_primary_regime_passed": True,
        }
        output, frames = v17_mtf.evaluate_mtf_source(
            source,
            daily_result=daily,
            cutoff=cutoff,
        )
        for prefix in ("mtf_1h", "mtf_4h"):
            self.assertTrue(output[f"{prefix}_available"])
            for suffix in (
                "ema_20",
                "ema_50",
                "macd",
                "macd_signal",
                "macd_hist",
                "adx",
                "adx_plus_di",
                "adx_minus_di",
                "rsi",
                "atr",
                "stoch_k",
                "stoch_d",
                "volume_slot_ratio",
            ):
                self.assertIsNotNone(output[f"{prefix}_{suffix}"])
        self.assertFalse(output["v17_classification_active"])
        self.assertTrue(output["v17_operational_status_unchanged"])
        self.assertIn("1h_indicators", frames)
        self.assertIn("4h_indicators", frames)

    def test_missing_ema50_is_reported_not_counted_as_bearish(self):
        source = synthetic_source(session_count=45)
        cutoff = source.index[-1] + pd.Timedelta(minutes=30)
        output, _ = v17_mtf.evaluate_mtf_source(
            source,
            daily_result={
                "status": "BUY",
                "output_signal": "Buy_Early_Momentum",
                "momentum_state": "DEVELOPING",
                "v16_primary_regime_passed": True,
            },
            cutoff=cutoff,
        )
        self.assertIsNone(output["mtf_4h_ema_50"])
        self.assertFalse(output["mtf_4h_trend_check_available"])
        self.assertIsNone(output["mtf_4h_trend_supportive"])
        self.assertEqual(output["mtf_4h_support_max"], 5)

    def test_daily_status_remains_authoritative(self):
        daily = {
            "status": "HOLD",
            "output_signal": "Hold",
            "momentum_state": "DEVELOPING",
            "v16_primary_regime_passed": True,
        }
        supportive = {
            "relation_to_daily": "SUPPORTIVE",
            "fresh_for_execution_session": True,
        }
        combined = v17_mtf.combine_daily_and_intraday(
            daily,
            supportive,
            supportive,
        )
        self.assertEqual(combined["v17_daily_baseline_status"], "HOLD")
        self.assertEqual(
            combined["v17_current_development_state"],
            "TRUE_MOMENTUM_CANDIDATE",
        )
        self.assertFalse(combined["v17_true_momentum_confirmed"])
        self.assertTrue(combined["v17_operational_status_unchanged"])

    def test_stale_four_hour_context_cannot_create_true_candidate(self):
        source = synthetic_source()
        last_session = source.index[-1].date()
        cutoff = datetime(
            last_session.year,
            last_session.month,
            last_session.day,
            12,
            0,
            tzinfo=NY,
        )
        daily = {
            "status": "BUY",
            "output_signal": "Buy_Momentum_Extension",
            "momentum_state": "LEADER",
            "v16_primary_regime_passed": True,
        }
        output, _ = v17_mtf.evaluate_mtf_source(
            source,
            daily_result=daily,
            cutoff=cutoff,
        )
        self.assertFalse(output["mtf_4h_fresh_for_execution_session"])
        self.assertTrue(output["mtf_1h_fresh_for_execution_session"])
        self.assertEqual(
            output["mtf_1h_latest_session_date"],
            last_session.isoformat(),
        )
        self.assertFalse(output["v17_true_momentum_candidate"])

    def test_india_suffix_is_out_of_scope(self):
        scope = v17_mtf.validate_us_listing("RELIANCE.NS")
        self.assertFalse(scope["in_scope"])

    def test_listing_scope_requires_nyse_or_nasdaq_metadata(self):
        self.assertTrue(
            v17_mtf.validate_us_listing(
                "AAPL",
                {"exchangeName": "NMS", "instrumentType": "EQUITY"},
            )["in_scope"]
        )
        self.assertTrue(
            v17_mtf.validate_us_listing(
                "IBM",
                {"fullExchangeName": "NYSE", "quoteType": "EQUITY"},
            )["in_scope"]
        )
        self.assertFalse(
            v17_mtf.validate_us_listing(
                "SPY",
                {"exchangeName": "PCX", "quoteType": "ETF"},
            )["in_scope"]
        )
        self.assertFalse(
            v17_mtf.validate_us_listing(
                "XYZ",
                {"exchangeName": "ASE", "quoteType": "EQUITY"},
            )["in_scope"]
        )
        self.assertFalse(v17_mtf.validate_us_listing("UNKNOWN", {})["in_scope"])


class ReplayCutoffTests(unittest.TestCase):
    def test_regular_session_cutoff_uses_prior_daily_candle(self):
        calendar = v17_mtf.get_us_calendar()
        sessions = calendar.sessions_in_range("2025-01-01", "2026-07-28")
        rows = []
        for position, session in enumerate(sessions):
            value = 100.0 + position
            rows.append({
                "open": value,
                "high": value + 1,
                "low": value - 1,
                "close": value + 0.5,
                "volume": 1_000_000,
            })
        daily = pd.DataFrame(rows, index=sessions)
        prefix, baseline = v17_mtf_replay.daily_prefix_for_cutoff(
            daily,
            pd.Timestamp(datetime(2026, 7, 28, 13, 30, tzinfo=NY)),
        )
        self.assertEqual(baseline, "2026-07-27")
        self.assertEqual(pd.Timestamp(prefix.index[-1]).date().isoformat(), baseline)

    def test_post_close_cutoff_still_uses_previous_session_foundation(self):
        calendar = v17_mtf.get_us_calendar()
        sessions = calendar.sessions_in_range("2025-01-01", "2026-07-28")
        daily = pd.DataFrame({
            "open": range(len(sessions)),
            "high": [value + 2 for value in range(len(sessions))],
            "low": [value for value in range(len(sessions))],
            "close": [value + 1 for value in range(len(sessions))],
            "volume": 1_000_000,
        }, index=sessions)
        _, baseline = v17_mtf_replay.daily_prefix_for_cutoff(
            daily,
            pd.Timestamp(datetime(2026, 7, 28, 16, 1, tzinfo=NY)),
        )
        self.assertEqual(baseline, "2026-07-27")

    def test_first_current_hour_does_not_compare_with_previous_day_hour(self):
        source = synthetic_source()
        last_session = source.index[-1].date()
        cutoff = datetime(
            last_session.year,
            last_session.month,
            last_session.day,
            10,
            30,
            tzinfo=NY,
        )
        output, _ = v17_mtf.evaluate_mtf_source(
            source,
            daily_result={
                "status": "HOLD",
                "output_signal": "No_Buy",
                "momentum_state": "NONE",
                "v16_primary_regime_passed": False,
            },
            cutoff=cutoff,
        )
        self.assertEqual(output["mtf_1h_bars"], 1)
        self.assertEqual(
            output["mtf_1h_progression_state"],
            "CURRENT_SESSION_START",
        )
        self.assertEqual(output["mtf_1h_improved_components"], "")
        self.assertEqual(output["mtf_1h_regressed_components"], "")


class DailyBacktestScopeTests(unittest.TestCase):
    def test_explicit_symbol_cannot_bypass_verified_master_scope(self):
        verified = pd.DataFrame({
            "ticker": ["AAPL"],
            "market": ["US"],
            "security_name": ["Apple"],
            "sector": ["Technology"],
            "listing_exchange": ["NASDAQ"],
            "source_file": ["test"],
            "is_etf": ["N"],
        })
        args = SimpleNamespace(
            us_master="ignored.csv",
            symbols=["OTCXYZ"],
            max_symbols=0,
        )
        with patch.object(
            v17_us_daily_backtest,
            "load_master",
            return_value=verified,
        ):
            with self.assertRaisesRegex(ValueError, "not verified"):
                v17_us_daily_backtest.load_universe(args)


if __name__ == "__main__":
    unittest.main()
