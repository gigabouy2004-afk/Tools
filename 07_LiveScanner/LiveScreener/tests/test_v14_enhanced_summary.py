import unittest

import pandas as pd

from Live_Scanner_v14_Enhanced import (
    STATUS_BUY_SIGNAL,
    STATUS_ERROR,
    STATUS_HOLD,
    included_session_date,
    summarize_data_through,
)


class DataThroughSummaryTests(unittest.TestCase):
    def test_included_session_date_uses_last_frame_row(self):
        frame = pd.DataFrame(
            {"close": [100.0, 101.0]},
            index=pd.to_datetime(["2026-07-23", "2026-07-24"]),
        )

        self.assertEqual(included_session_date(frame), "2026-07-24")

    def test_summary_reports_one_shared_session_date(self):
        results = [
            {"status": STATUS_BUY_SIGNAL, "session_date": "2026-07-24"},
            {"status": STATUS_HOLD, "session_date": "2026-07-24"},
        ]

        self.assertEqual(summarize_data_through(results), "2026-07-24")

    def test_summary_discloses_mixed_market_session_range(self):
        results = [
            {"status": STATUS_BUY_SIGNAL, "session_date": "2026-07-24"},
            {"status": STATUS_HOLD, "session_date": "2026-07-25"},
            {"status": STATUS_HOLD, "session_date": "2026-07-27"},
        ]

        self.assertEqual(
            summarize_data_through(results),
            "2026-07-24 to 2026-07-27 (3 session dates)",
        )

    def test_summary_ignores_error_placeholders(self):
        results = [
            {"status": STATUS_ERROR, "session_date": "2026-07-27"},
            {"status": STATUS_HOLD, "session_date": "2026-07-24"},
        ]

        self.assertEqual(summarize_data_through(results), "2026-07-24")

    def test_summary_reports_unavailable_without_successful_dates(self):
        results = [
            {"status": STATUS_ERROR, "session_date": "2026-07-27"},
            {"status": STATUS_ERROR, "session_date": None},
        ]

        self.assertEqual(summarize_data_through(results), "Unavailable")


if __name__ == "__main__":
    unittest.main()
