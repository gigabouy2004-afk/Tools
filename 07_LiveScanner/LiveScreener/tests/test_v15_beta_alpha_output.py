import unittest

from openpyxl import Workbook

from Live_Scanner_v15 import (
    fetch_listing_beta_alpha,
    format_v15_details_worksheet,
    parse_etf_alpha_beta,
)


class _FakeDataClient:
    def __init__(self, modules):
        self.modules = modules

    def get_raw_json(self, _url, params):
        module_name = params["modules"]
        module = self.modules.get(module_name, {})
        return {
            "quoteSummary": {
                "result": [{module_name: module}],
            }
        }


class _FakeTicker:
    def __init__(self, modules=None, info=None):
        self.ticker = "TEST"
        self._data = _FakeDataClient(modules or {})
        self._info = info or {}

    def get_info(self):
        return self._info


class V15BetaAlphaOutputTests(unittest.TestCase):
    def test_etf_parser_selects_three_year_values(self):
        fund_performance = {
            "riskOverviewStatistics": {
                "riskStatistics": [
                    {
                        "year": "1y",
                        "beta": {"raw": 0.70},
                        "alpha": {"raw": 1.20},
                    },
                    {
                        "year": "3y",
                        "beta": {"raw": 0.997},
                        "alpha": {"raw": -0.086},
                    },
                ]
            }
        }

        self.assertEqual(
            parse_etf_alpha_beta(fund_performance),
            {"beta": 1.0, "alpha": -0.09},
        )

    def test_equity_has_beta_and_intentionally_blank_alpha(self):
        ticker = _FakeTicker(
            modules={
                "defaultKeyStatistics": {
                    "beta": {"raw": 1.104},
                }
            }
        )

        self.assertEqual(
            fetch_listing_beta_alpha(ticker, {"instrumentType": "EQUITY"}),
            {"beta": 1.1, "alpha": None},
        )

    def test_etf_has_beta_and_alpha(self):
        ticker = _FakeTicker(
            modules={
                "fundPerformance": {
                    "riskOverviewStatistics": {
                        "riskStatistics": [
                            {
                                "year": "3y",
                                "beta": {"raw": 0.82},
                                "alpha": {"raw": 2.345},
                            }
                        ]
                    }
                }
            }
        )

        self.assertEqual(
            fetch_listing_beta_alpha(ticker, {"quoteType": "ETF"}),
            {"beta": 0.82, "alpha": 2.35},
        )

    def test_missing_provider_values_remain_blank(self):
        ticker = _FakeTicker()

        self.assertEqual(
            fetch_listing_beta_alpha(ticker, {"instrumentType": "EQUITY"}),
            {"beta": None, "alpha": None},
        )

    def test_details_sheet_freezes_after_alpha_and_formats_risk_columns(self):
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.append(
            [
                "Ticker",
                "engine_version",
                "v15_shadow_mode",
                "v15_classification_active",
                "Message",
                "Reason",
                "Company Name",
                "Price",
                "Currency",
                "Beta",
                "Alpha",
            ]
        )
        worksheet.append(
            ["TEST", "V15", True, False, "OK", "", "Test", 10, "USD", 1.1, None]
        )

        format_v15_details_worksheet(worksheet)

        self.assertEqual(worksheet.freeze_panes, "L2")
        self.assertEqual(worksheet["H2"].number_format, "0.00")
        self.assertEqual(worksheet["J2"].number_format, "0.00")
        self.assertEqual(worksheet["K2"].number_format, "0.00")
        self.assertEqual(worksheet.column_dimensions["J"].width, 12)
        self.assertEqual(worksheet.column_dimensions["K"].width, 12)


if __name__ == "__main__":
    unittest.main()
