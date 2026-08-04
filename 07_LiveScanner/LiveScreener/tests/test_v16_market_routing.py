import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

import Live_Scanner_v16 as scanner


class SimplifiedMarketRoutingTests(unittest.TestCase):
    def setUp(self):
        self.ny = ZoneInfo("America/New_York")
        self.ist = ZoneInfo("Asia/Kolkata")

    def test_suffix_alone_selects_market_and_timezone(self):
        misleading_metadata = {
            "exchangeTimezoneName": "Asia/Kolkata",
            "fullExchangeName": "NSE",
        }

        us_context = scanner.get_market_context(
            "AAPL",
            metadata=misleading_metadata,
            now=datetime(2026, 7, 28, 11, 0, tzinfo=self.ny),
        )
        nse_context = scanner.get_market_context(
            "RELIANCE.NS",
            metadata={
                "exchangeTimezoneName": "America/New_York",
                "fullExchangeName": "NYSE",
            },
            now=datetime(2026, 7, 28, 10, 0, tzinfo=self.ist),
        )
        bse_context = scanner.get_market_context(
            "500325.BO",
            now=datetime(2026, 7, 28, 10, 0, tzinfo=self.ist),
        )

        self.assertEqual(us_context["market"], "NYSE")
        self.assertEqual(us_context["_timezone"], self.ny)
        self.assertEqual(nse_context["market"], "NSE")
        self.assertEqual(nse_context["_timezone"], self.ist)
        self.assertEqual(bse_context["market"], "BSE")
        self.assertEqual(bse_context["_timezone"], self.ist)

    def test_every_non_indian_suffix_uses_us_rules(self):
        self.assertEqual(scanner.resolve_market("AAPL"), "NYSE")
        self.assertEqual(scanner.resolve_market("SPY"), "NYSE")
        self.assertEqual(scanner.resolve_market("7203.T"), "NYSE")
        self.assertEqual(scanner.resolve_market("VOD.L"), "NYSE")

    def test_us_has_only_regular_or_closed_phase(self):
        cases = [
            (datetime(2026, 7, 28, 8, 0, tzinfo=self.ny), "CLOSED"),
            (datetime(2026, 7, 28, 11, 0, tzinfo=self.ny), "REGULAR"),
            (datetime(2026, 7, 28, 17, 0, tzinfo=self.ny), "CLOSED"),
        ]

        for now, expected_phase in cases:
            with self.subTest(expected_phase=expected_phase):
                context = scanner.get_market_context("IBM", now=now)
                self.assertEqual(context["phase"], expected_phase)
                self.assertFalse(context["_allow_premarket"])
                self.assertFalse(context["_allow_postmarket"])
                self.assertFalse(context["_allow_extended_hours"])

    def test_same_utc_moment_uses_us_or_india_suffix_clock(self):
        same_moment = datetime(
            2026,
            7,
            28,
            4,
            30,
            tzinfo=ZoneInfo("UTC"),
        )

        us_context = scanner.get_market_context("IBM", now=same_moment)
        nse_context = scanner.get_market_context(
            "RELIANCE.NS",
            now=same_moment,
        )
        bse_context = scanner.get_market_context(
            "500325.BO",
            now=same_moment,
        )

        self.assertEqual(us_context["phase"], "CLOSED")
        self.assertEqual(nse_context["phase"], "REGULAR")
        self.assertEqual(bse_context["phase"], "REGULAR")
        self.assertEqual(us_context["market_time_local"][11:16], "00:30")
        self.assertEqual(nse_context["market_time_local"][11:16], "10:00")


class RegularSessionFrameTests(unittest.TestCase):
    def test_filter_includes_regular_bars_only(self):
        ny = ZoneInfo("America/New_York")
        context = scanner.get_market_context(
            "IBM",
            now=datetime(2026, 7, 28, 17, 0, tzinfo=ny),
        )
        index = pd.DatetimeIndex(
            [
                datetime(2026, 7, 28, 8, 0, tzinfo=ny),
                datetime(2026, 7, 28, 9, 30, tzinfo=ny),
                datetime(2026, 7, 28, 15, 59, tzinfo=ny),
                datetime(2026, 7, 28, 16, 1, tzinfo=ny),
            ]
        )
        minute_frame = pd.DataFrame(
            {"close": [1, 2, 3, 4]},
            index=index,
        )

        filtered = scanner.filter_intraday_to_session(
            minute_frame,
            context,
        )

        self.assertEqual(filtered["close"].tolist(), [2, 3])


class AutoCombinationTests(unittest.TestCase):
    @staticmethod
    def _confirmed(status="BUY"):
        return {
            "status": status,
            "output_signal": (
                "Buy_Momentum_Extension" if status == "BUY" else "No_Buy"
            ),
            "classification": "BUY#3" if status == "BUY" else "NO_BUY",
            "reason": "Completed candle result",
            "momentum_state": (
                "LEADER" if status == "BUY" else "DEVELOPING"
            ),
            "entry_state": (
                "CONFIRMED" if status == "BUY" else "WAIT_TRIGGER"
            ),
            "price": 100.0,
            "session_date": "2026-07-27",
        }

    @staticmethod
    def _live_provisional():
        return {
            "status": "HOLD",
            "output_signal": "Provisional_Buy_Momentum_Extension",
            "classification": "PROVISIONAL_BUY",
            "reason": "Pending completed candle",
            "momentum_state": "LEADER",
            "entry_state": "PROVISIONAL_CONFIRMED",
            "provisional_entry_candidate": True,
            "provisional_signal": "Buy_Momentum_Extension",
            "price": 102.0,
            "relative_volume_ratio": 1.5,
            "raw_volume_ratio": 0.8,
            "volume_ratio_basis": "ELAPSED_SESSION_ADJUSTED",
            "adx": 30.0,
            "rsi": 65.0,
            "stoch_k": 60.0,
            "stoch_d": 55.0,
        }

    def test_confirmed_buy_remains_primary_with_live_overlay(self):
        combined = scanner.combine_auto_evaluations(
            self._confirmed("BUY"),
            self._live_provisional(),
            market_phase="REGULAR",
            confirmed_candle_state="LAST_COMPLETED",
            live_candle_state="CURRENT_PARTIAL",
        )

        self.assertEqual(combined["status"], "BUY")
        self.assertEqual(
            combined["auto_action_source"],
            "COMPLETED_BASELINE",
        )
        self.assertEqual(
            combined["auto_combined_state"],
            "CONFIRMED_BUY_LIVE_SUPPORTIVE",
        )
        self.assertTrue(
            combined["live_overlay_provisional_entry_candidate"]
        )
        self.assertEqual(combined["live_overlay_price"], 102.0)
        self.assertEqual(combined["price"], 100.0)

    def test_live_provisional_is_primary_when_baseline_is_not_buy(self):
        combined = scanner.combine_auto_evaluations(
            self._confirmed("HOLD"),
            self._live_provisional(),
            market_phase="REGULAR",
            confirmed_candle_state="LAST_COMPLETED",
            live_candle_state="CURRENT_PARTIAL",
        )

        self.assertEqual(combined["status"], "HOLD")
        self.assertEqual(combined["classification"], "PROVISIONAL_BUY")
        self.assertEqual(combined["auto_action_source"], "LIVE_OVERLAY")
        self.assertEqual(
            combined["auto_combined_state"],
            "PROVISIONAL_BUY_ONLY",
        )
        self.assertEqual(combined["confirmed_status"], "HOLD")


if __name__ == "__main__":
    unittest.main()
