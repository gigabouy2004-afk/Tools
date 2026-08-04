
"""L1 Contextual Stability Gate."""

from MODELS.contracts import MarketContext, L1Result


class L1Engine:

    @staticmethod
    def evaluate(context: MarketContext) -> L1Result:

        unstable_conditions = []

        if context.macd_histogram_slope < 0:
            unstable_conditions.append(
                "MACD histogram slope deteriorating"
            )

        if len(unstable_conditions) > 0:
            return L1Result(
                symbol=context.symbol,
                regime_state="REGIME_UNSTABLE",
                escalation_required=True,
                explanation=unstable_conditions
            )

        return L1Result(
            symbol=context.symbol,
            regime_state="REGIME_STABLE",
            escalation_required=False,
            explanation=["No tactical escalation required"]
        )
