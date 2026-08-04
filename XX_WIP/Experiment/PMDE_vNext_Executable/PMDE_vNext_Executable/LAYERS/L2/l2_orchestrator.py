class L2Orchestrator:

    @staticmethod
    def process(
        symbol,
        macd_suite
    ):

        macd_1h = macd_suite["1h"]
        macd_4h = macd_suite["4h"]
        macd_1d = macd_suite["1d"]

        # STRUCTURAL WEAKNESS
        if (
            macd_1d["state"] == "BEARISH"
            and
            macd_4h["state"] == "BEARISH"
        ):

            # LOWER TF RECOVERY
            if macd_1h["state"] == "BULLISH":

                return {
                    "state": (
                        "COUNTERTREND_RECOVERY"
                    ),

                    "confidence": "HIGH",

                    "message": (
                        "Bearish crossover "
                        "pressure confirmed "
                        "in 1D and 4H cycles. "
                        "1H bullish crossover "
                        "detected. Possible "
                        "early reversal propagation "
                        "emerging from lower "
                        "timeframe."
                    )
                }

            return {
                "state": "PRE_BEAR",

                "confidence": "HIGH",

                "message": (
                    "Bearish crossover "
                    "confirmed in higher "
                    "timeframes."
                )
            }

        # STRUCTURAL STRENGTH
        if (
            macd_1d["state"] == "BULLISH"
            and
            macd_4h["state"] == "BULLISH"
        ):

            return {
                "state": (
                    "STRUCTURAL_BULLISH"
                ),

                "confidence": "HIGH",

                "message": (
                    "Bullish alignment "
                    "confirmed across "
                    "higher timeframes."
                )
            }

        return {
            "state": "TRANSITIONAL",

            "confidence": "MEDIUM",

            "message": (
                "Mixed timeframe "
                "signals detected."
            )
        }