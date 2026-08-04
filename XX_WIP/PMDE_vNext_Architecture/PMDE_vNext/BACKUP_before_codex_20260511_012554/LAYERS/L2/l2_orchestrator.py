
"""Primary orchestration layer for PMDE."""

from LAYERS.L3.macd_engine import MACDEngine
from MODELS.contracts import TacticalDecision


class L2Orchestrator:

    @staticmethod
    def investigate_macd(
        symbol: str,
        macd_inputs_1d: dict,
        macd_inputs_4h: dict = None
    ) -> TacticalDecision:

        macd_1d = MACDEngine.get_macd(
            symbol=symbol,
            timeframe="1d",
            **macd_inputs_1d
        )

        if (
            macd_1d.histogram_slope < 0 and
            macd_1d.crossover_distance < 0.25
        ):

            if macd_inputs_4h:

                macd_4h = MACDEngine.get_macd(
                    symbol=symbol,
                    timeframe="4h",
                    **macd_inputs_4h
                )

                if macd_4h.macd < macd_4h.signal:
                    return TacticalDecision(
                        symbol=symbol,
                        tactical_state="PRE_BEAR",
                        decision_reason=(
                            "1D hinted deterioration and "
                            "4H confirmed bearish crossover."
                        ),
                        confidence="HIGH"
                    )

        return TacticalDecision(
            symbol=symbol,
            tactical_state="STANDARD_TREND",
            decision_reason="No confirmed tactical deterioration.",
            confidence="LOW"
        )
