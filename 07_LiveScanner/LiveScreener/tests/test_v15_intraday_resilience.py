import unittest
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pandas as pd

import Live_Scanner_v15 as scanner


class IntradayVolumeTests(unittest.TestCase):
    def test_regular_session_elapsed_fraction(self):
        ny = ZoneInfo("America/New_York")
        context = {
            "_regular_start": datetime(2026, 7, 28, 9, 30, tzinfo=ny),
            "_regular_end": datetime(2026, 7, 28, 16, 0, tzinfo=ny),
            "_now_local": datetime(2026, 7, 28, 11, 5, tzinfo=ny),
            "phase": "REGULAR",
        }

        fraction = scanner.regular_session_elapsed_fraction(context)

        self.assertAlmostEqual(fraction, 95 / 390)

    def test_partial_regular_volume_uses_elapsed_session_adjustment(self):
        comparison = scanner.calculate_volume_comparison(
            current_volume=25,
            volume_avg_20=100,
            current_candle_partial=True,
            candle_state="CURRENT_PARTIAL",
            elapsed_session_fraction=0.25,
        )

        self.assertAlmostEqual(comparison["raw_volume_ratio"], 0.25)
        self.assertAlmostEqual(comparison["relative_volume_ratio"], 1.0)
        self.assertAlmostEqual(comparison["projected_full_session_volume"], 100.0)
        self.assertEqual(comparison["volume_ratio_basis"], "ELAPSED_SESSION_ADJUSTED")

    def test_completed_volume_keeps_full_session_ratio(self):
        comparison = scanner.calculate_volume_comparison(
            current_volume=25,
            volume_avg_20=100,
            current_candle_partial=False,
            candle_state="COMPLETED",
            elapsed_session_fraction=None,
        )

        self.assertAlmostEqual(comparison["raw_volume_ratio"], 0.25)
        self.assertAlmostEqual(comparison["relative_volume_ratio"], 0.25)
        self.assertAlmostEqual(comparison["projected_full_session_volume"], 25.0)
        self.assertEqual(comparison["volume_ratio_basis"], "FULL_SESSION")

    def test_non_regular_partial_volume_is_explicitly_unconfirmed(self):
        comparison = scanner.calculate_volume_comparison(
            current_volume=10,
            volume_avg_20=100,
            current_candle_partial=True,
            candle_state="NON_REGULAR_PARTIAL",
            elapsed_session_fraction=None,
        )

        self.assertAlmostEqual(comparison["raw_volume_ratio"], 0.10)
        self.assertIsNone(comparison["relative_volume_ratio"])
        self.assertIsNone(comparison["projected_full_session_volume"])
        self.assertEqual(comparison["volume_ratio_basis"], "PARTIAL_UNCONFIRMED")


class ProvisionalEntryTests(unittest.TestCase):
    @staticmethod
    def _buy_result():
        return {
            "status": "BUY",
            "output_signal": "Buy_Strong_Momentum",
            "classification": "V15_Promotion_Buy",
            "OUT_MESSAGE": "BUY",
            "message": "BUY",
            "reason": "All V15 promotion gates passed.",
            "momentum_state": "LEADER",
            "v15_primary_regime_passed": True,
            "leadership_ok": True,
            "entry_extension_safe": True,
            "entry_adx_ok": True,
            "entry_volume_ok": True,
            "adx_directional_bullish": True,
            "adx_at_or_above_20": True,
            "volume_at_or_above_average": True,
        }

    def test_partial_buy_is_preserved_as_explicit_provisional_candidate(self):
        result = scanner.mark_provisional_buy_candidate(
            self._buy_result(), candle_state="CURRENT_PARTIAL"
        )

        self.assertEqual(result["status"], "HOLD")
        self.assertEqual(result["output_signal"], "Provisional_Buy_Strong_Momentum")
        self.assertEqual(result["classification"], "PROVISIONAL_BUY")
        self.assertEqual(result["OUT_MESSAGE"], "PROVISIONAL_BUY")
        self.assertTrue(result["provisional_entry_candidate"])
        self.assertEqual(result["provisional_signal"], "Buy_Strong_Momentum")
        self.assertEqual(result["candle_confirmation"], "PROVISIONAL")
        self.assertEqual(result["entry_state"], "PROVISIONAL_CONFIRMED")
        self.assertEqual(result["shadow_recommended_status"], "HOLD")

    def test_extension_risk_still_takes_priority_over_provisional_state(self):
        source = self._buy_result()
        source["entry_extension_safe"] = False

        result = scanner.mark_provisional_buy_candidate(
            source, candle_state="CURRENT_PARTIAL"
        )

        self.assertEqual(result["entry_state"], "WAIT_EXTENDED")
        self.assertEqual(result["shadow_recommended_status"], "HOLD")


class RunDiagnosticsTests(unittest.TestCase):
    def test_rate_limited_run_is_invalid_and_reports_mode_accounting(self):
        results = [
            {
                "ticker": "AAA",
                "status": "HOLD",
                "momentum_state": "LEADER",
                "entry_state": "PROVISIONAL_CONFIRMED",
                "provisional_entry_candidate": True,
                "provisional_signal": "Buy_Strong_Momentum",
                "effective_candle_mode": "intraday",
                "candle_state": "CURRENT_PARTIAL",
                "candle_fallback": False,
            },
            {
                "ticker": "BBB",
                "status": "HOLD",
                "momentum_state": "DEVELOPING",
                "entry_state": "WAIT_VOLUME",
                "effective_candle_mode": "completed",
                "candle_state": "COMPLETED",
                "candle_fallback": True,
            },
            {
                "ticker": "CCC",
                "status": "ERROR",
                "classification": "Error_RateLimited",
                "message": "Too Many Requests. Rate limited. Try after a while",
            },
            {
                "ticker": "DDD",
                "status": "HOLD",
                "momentum_state": "WEAK",
                "entry_state": "WAIT_MOMENTUM",
                "effective_candle_mode": "intraday",
                "candle_state": "CURRENT_PARTIAL",
                "candle_fallback": False,
            },
        ]

        diagnostics = scanner.summarize_run_diagnostics(
            results,
            max_error_rate_pct=10.0,
            max_rate_limit_error_rate_pct=1.0,
        )

        self.assertEqual(diagnostics["run_quality_status"], "INVALID")
        self.assertEqual(diagnostics["error_count"], 1)
        self.assertEqual(diagnostics["rate_limit_error_count"], 1)
        self.assertAlmostEqual(diagnostics["error_rate_pct"], 25.0)
        self.assertAlmostEqual(diagnostics["rate_limit_error_rate_pct"], 25.0)
        self.assertEqual(diagnostics["provisional_buy_count"], 1)
        self.assertEqual(diagnostics["provisional_buy_symbols"], ["AAA"])
        self.assertEqual(diagnostics["effective_mode_breakup"]["intraday"], 2)
        self.assertEqual(diagnostics["candle_fallback_count"], 1)
        self.assertIn("error rate", " ".join(diagnostics["run_quality_reasons"]).lower())
        self.assertIn(
            "rate-limit",
            " ".join(diagnostics["run_quality_reasons"]).lower(),
        )


class YahooRetryTests(unittest.TestCase):
    def setUp(self):
        scanner.configure_yahoo_request_policy(
            max_attempts=3,
            retry_base_seconds=0.0,
            retry_max_seconds=0.0,
            min_request_interval_seconds=0.0,
        )
        scanner.reset_yahoo_request_state()

    def tearDown(self):
        scanner.configure_yahoo_request_policy(
            max_attempts=scanner.DEFAULT_YAHOO_MAX_ATTEMPTS,
            retry_base_seconds=scanner.DEFAULT_YAHOO_RETRY_BASE_SECONDS,
            retry_max_seconds=scanner.DEFAULT_YAHOO_RETRY_MAX_SECONDS,
            min_request_interval_seconds=(
                scanner.DEFAULT_YAHOO_MIN_REQUEST_INTERVAL_SECONDS
            ),
        )
        scanner.reset_yahoo_request_state()

    @patch("Live_Scanner_v15.time.sleep", return_value=None)
    def test_rate_limit_is_retried_before_succeeding(self, _sleep):
        attempts = {"count": 0}

        def operation():
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise RuntimeError("Too Many Requests. Rate limited. Try after a while")
            return "ok"

        value = scanner.execute_yahoo_request(operation, operation_name="unit-test")

        self.assertEqual(value, "ok")
        self.assertEqual(attempts["count"], 3)


class OutputSchemaTests(unittest.TestCase):
    def test_display_and_internal_messages_have_unique_headers(self):
        frame = pd.DataFrame(
            [
                {
                    "ticker": "AAA",
                    "OUT_MESSAGE": "PROVISIONAL_BUY",
                    "message": "Internal explanation",
                }
            ]
        )

        output = scanner.prepare_v15_details_output(frame)

        self.assertIn("Ticker", output.columns)
        self.assertIn("Display Message", output.columns)
        self.assertIn("Internal Message", output.columns)
        casefolded = [str(column).casefold() for column in output.columns]
        self.assertEqual(len(casefolded), len(set(casefolded)))


if __name__ == "__main__":
    unittest.main()
