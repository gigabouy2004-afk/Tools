
from MODELS.contracts import L1Result


class L1Engine:

    @staticmethod
    def evaluate(
        histogram_slope: float
    ) -> L1Result:

        if histogram_slope < 0:

            return L1Result(
                regime_state="REGIME_UNSTABLE",
                escalation_required=True,
                reason="Momentum deterioration detected"
            )

        return L1Result(
            regime_state="REGIME_STABLE",
            escalation_required=False,
            reason="No deterioration detected"
        )
