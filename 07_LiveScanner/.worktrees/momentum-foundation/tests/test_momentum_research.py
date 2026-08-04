import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

import momentum_research
import build_momentum_research_panel
from plain_language_output import build_plain_review_frame
import v17_mtf
import v17_mtf_replay


NY = ZoneInfo("America/New_York")


def daily_history(rows: int = 320) -> pd.DataFrame:
    calendar = v17_mtf.get_us_calendar()
    sessions = calendar.sessions_in_range("2024-01-01", "2026-07-29")[-rows:]
    position = np.arange(len(sessions), dtype=float)
    close = 50.0 + position * 0.12 + np.sin(position / 8.0)
    return pd.DataFrame(
        {
            "open": close - 0.15,
            "high": close + 0.75,
            "low": close - 0.65,
            "close": close,
            "volume": 500_000 + position * 1_000,
            "security_name": "Synthetic Equity",
            "sector": "Technology",
            "industry": "Software",
            "listing_exchange": "NASDAQ",
        },
        index=sessions,
    )


class HistoryTierTests(unittest.TestCase):
    def test_age_tracks_do_not_borrow_missing_long_history(self):
        self.assertEqual(
            momentum_research.history_tier(10),
            ("Observation only", "Not enough stock history"),
        )
        self.assertEqual(
            momentum_research.history_tier(50),
            ("Young listing", "Young-listing research"),
        )
        self.assertEqual(
            momentum_research.history_tier(150),
            ("Developing history", "Reduced-history research"),
        )
        self.assertEqual(
            momentum_research.history_tier(300),
            ("Established history", "Standard-history research"),
        )

    def test_young_listing_is_retained_with_unavailable_long_features(self):
        features = momentum_research.calculate_daily_features(
            daily_history(60),
            ticker="NEW",
        )
        self.assertEqual(features.iloc[-1]["history_tier"], "Young listing")
        self.assertTrue(features.iloc[-1]["ema_50_available"])
        self.assertFalse(features.iloc[-1]["ema_200_available"])
        self.assertFalse(
            features.iloc[-1]["standard_history_features_available"]
        )
        self.assertFalse(features.iloc[10]["atr_available"])
        self.assertFalse(features.iloc[20]["adx_available"])
        self.assertTrue(features.iloc[-1]["atr_available"])
        self.assertTrue(features.iloc[-1]["adx_available"])

    def test_stable_identity_retains_point_in_time_ticker_change(self):
        source = daily_history(30)
        source["security_id"] = "SEC-1"
        source["ticker"] = ["OLD"] * 15 + ["NEW"] * 15
        features = momentum_research.calculate_daily_features(
            source,
            ticker="NEW",
        )
        self.assertEqual(features.iloc[0]["ticker"], "OLD")
        self.assertEqual(features.iloc[-1]["ticker"], "NEW")
        self.assertTrue(features["security_id"].eq("SEC-1").all())


class ArchiveScopeTests(unittest.TestCase):
    def test_archive_loader_enforces_identity_equity_and_exchange_scope(self):
        rows = pd.DataFrame({
            "ticker": ["AAPL", "SPY", "OTCXYZ"],
            "security_id": ["SEC-1", "SEC-2", "SEC-3"],
            "date": ["2026-07-29"] * 3,
            "open": [100.0] * 3,
            "high": [101.0] * 3,
            "low": [99.0] * 3,
            "close": [100.5] * 3,
            "volume": [1_000_000] * 3,
            "listing_exchange": ["NASDAQ", "NASDAQ", "OTC"],
            "instrument_type": ["EQUITY", "ETF", "EQUITY"],
            "listing_date": ["2000-01-01"] * 3,
            "delisting_date": [None] * 3,
        })
        with TemporaryDirectory() as temporary:
            source = Path(temporary) / "archive.csv"
            rows.to_csv(source, index=False)
            loaded = (
                build_momentum_research_panel.load_long_daily_archive(source)
            )
        self.assertEqual(loaded["ticker"].tolist(), ["AAPL"])

    def test_archive_loader_refuses_missing_stable_identity(self):
        rows = pd.DataFrame({
            "ticker": ["AAPL"],
            "date": ["2026-07-29"],
            "open": [100.0],
            "high": [101.0],
            "low": [99.0],
            "close": [100.5],
            "volume": [1_000_000],
            "listing_exchange": ["NASDAQ"],
            "instrument_type": ["EQUITY"],
        })
        with TemporaryDirectory() as temporary:
            source = Path(temporary) / "archive.csv"
            rows.to_csv(source, index=False)
            with self.assertRaisesRegex(ValueError, "identity fields"):
                build_momentum_research_panel.load_long_daily_archive(source)

    def test_archive_loader_refuses_blank_stable_identity_values(self):
        rows = pd.DataFrame({
            "ticker": ["AAPL"],
            "security_id": [None],
            "date": ["2026-07-29"],
            "open": [100.0],
            "high": [101.0],
            "low": [99.0],
            "close": [100.5],
            "volume": [1_000_000],
            "listing_exchange": ["NASDAQ"],
            "instrument_type": ["EQUITY"],
            "listing_date": ["2000-01-01"],
            "delisting_date": [None],
        })
        with TemporaryDirectory() as temporary:
            source = Path(temporary) / "archive.csv"
            rows.to_csv(source, index=False)
            with self.assertRaisesRegex(ValueError, "stable security_id"):
                build_momentum_research_panel.load_long_daily_archive(source)


class PointInTimeFeatureTests(unittest.TestCase):
    def test_future_price_changes_do_not_change_prior_features(self):
        source = daily_history()
        original = momentum_research.calculate_daily_features(
            source,
            ticker="TEST",
        )
        changed = source.copy()
        changed.iloc[250:, changed.columns.get_loc("close")] *= 3.0
        changed.iloc[250:, changed.columns.get_loc("high")] *= 3.0
        changed.iloc[250:, changed.columns.get_loc("low")] *= 3.0
        recalculated = momentum_research.calculate_daily_features(
            changed,
            ticker="TEST",
        )
        fields = [
            "ema_20",
            "ema_50",
            "ema_200",
            "macd_histogram",
            "adx_14",
            "rsi_14",
            "daily_volume_ratio",
            "weekly_ema_50",
        ]
        for field in fields:
            self.assertAlmostEqual(
                float(original.iloc[240][field]),
                float(recalculated.iloc[240][field]),
                places=10,
            )

    def test_entry_after_foundation_and_forward_window_are_explicit(self):
        features = momentum_research.calculate_daily_features(
            daily_history(80),
            ticker="TEST",
        )
        panel = momentum_research.attach_forward_outcomes(
            features,
            contract=momentum_research.OutcomeContract(
                horizons=(5, 10),
                barrier_horizon=10,
            ),
        )
        position = 40
        self.assertEqual(
            panel.iloc[position]["hypothetical_entry_session"],
            panel.index[position + 1].strftime("%Y-%m-%d"),
        )
        self.assertAlmostEqual(
            float(panel.iloc[position]["hypothetical_entry_open"]),
            float(panel.iloc[position + 1]["open"]),
        )
        expected = (
            panel.iloc[position + 5]["close"]
            / panel.iloc[position + 1]["open"]
            - 1.0
        ) * 100.0
        self.assertAlmostEqual(
            float(panel.iloc[position]["forward_5_session_return_pct"]),
            float(expected),
            places=10,
        )
        self.assertFalse(
            bool(panel.iloc[-1]["outcome_10_sessions_complete"])
        )

    def test_daily_barrier_order_reports_same_session_ambiguity(self):
        self.assertEqual(
            momentum_research._barrier_outcome(
                highs=np.array([103.0]),
                lows=np.array([97.0]),
                upper=102.0,
                lower=98.0,
            ),
            "Both targets touched in the same session; order unknown",
        )


class ChronologicalSplitTests(unittest.TestCase):
    def test_forward_outcome_crossing_boundary_is_purged(self):
        panel = pd.DataFrame({
            "previous_completed_session": [
                "2024-01-02",
                "2024-01-03",
                "2024-01-04",
                "2024-01-05",
            ],
            "outcome_20_end_date": [
                "2024-01-03",
                "2024-01-05",
                "2024-01-06",
                None,
            ],
        })
        result = momentum_research.assign_chronological_split(
            panel,
            training_end="2024-01-03",
            calibration_end="2024-01-05",
            longest_horizon=20,
        )
        self.assertTrue(bool(result.iloc[0]["split_eligible"]))
        self.assertFalse(bool(result.iloc[1]["split_eligible"]))
        self.assertFalse(bool(result.iloc[2]["split_eligible"]))
        self.assertFalse(bool(result.iloc[3]["split_eligible"]))


class PlainLanguageOutputTests(unittest.TestCase):
    def test_public_review_contains_no_version_or_shadow_flags(self):
        technical = pd.DataFrame([{
            "ticker": "AAPL",
            "company_name": "Apple",
            "status": "HOLD",
            "classification": "NO_BUY",
            "reason": "Waiting for evidence",
            "v16_primary_regime_passed": True,
            "momentum_state": "DEVELOPING",
            "v17_daily_baseline_session_date": "2026-07-29",
            "v17_execution_session_date": "2026-07-30",
            "v17_current_development_state": (
                "DAILY_MOMENTUM_PARTIALLY_SUPPORTED"
            ),
            "mtf_4h_bars": 0,
            "mtf_4h_relation_to_daily": "UNAVAILABLE",
            "mtf_1h_bars": 2,
            "mtf_1h_relation_to_daily": "SUPPORTIVE",
            "mtf_1h_progression_state": "PROGRESSED",
            "v17_shadow_mode": True,
        }])
        review = build_plain_review_frame(technical)
        headers = " ".join(review.columns).lower()
        values = " ".join(review.iloc[0].astype(str)).lower()
        self.assertNotIn("v17", headers)
        self.assertNotIn("shadow", headers)
        self.assertNotIn("v17", values)
        self.assertNotIn("shadow", values)
        self.assertIn("previous completed session", headers)
        self.assertIn("current session", headers)

    def test_replay_export_removes_internal_prefixes(self):
        technical = pd.DataFrame([{
            "ticker": "AAPL",
            "daily_baseline_session_date": "2026-07-29",
            "v17_current_development_state": (
                "DAILY_MOMENTUM_PARTIALLY_SUPPORTED"
            ),
            "v17_true_momentum_candidate": False,
            "v17_shadow_mode": True,
            "v17_classification_active": False,
            "mtf_1h_bars": 2,
            "mtf_1h_relation_to_daily": "SUPPORTIVE",
            "mtf_1h_progression_state": "PROGRESSED",
            "d1_momentum_state": "DEVELOPING",
        }])
        public = v17_mtf_replay.prepare_public_replay_panel(technical)
        headers = " ".join(public.columns).lower()
        values = " ".join(public.iloc[0].astype(str)).lower()
        self.assertNotIn("v17", headers)
        self.assertNotIn("shadow", headers)
        self.assertNotIn("d1_", headers)
        self.assertIn("current_session_1h_bars", public.columns)
        self.assertNotIn("daily_momentum_partially_supported", values)
        self.assertEqual(
            public.iloc[0][
                "current_session_1h_relation_to_previous_session_view"
            ],
            "Supports the previous-session daily view",
        )
        self.assertEqual(
            public.iloc[0]["current_session_1h_progression_state"],
            "Improved during the current session",
        )


class CurrentSessionContractTests(unittest.TestCase):
    def test_after_close_today_is_not_the_previous_session(self):
        context = v17_mtf.us_market_context(
            datetime(2026, 7, 30, 17, 0, tzinfo=NY)
        )
        self.assertEqual(context["latest_completed_session_date"], "2026-07-30")
        self.assertEqual(context["previous_traded_session_date"], "2026-07-29")


if __name__ == "__main__":
    unittest.main()
