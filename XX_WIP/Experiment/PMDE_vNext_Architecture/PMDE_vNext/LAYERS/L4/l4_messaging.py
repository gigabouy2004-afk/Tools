
"""Semantic translation layer."""

from MODELS.contracts import TacticalDecision


class L4Messaging:

    @staticmethod
    def generate(decision: TacticalDecision) -> str:

        return (
            f"[{decision.symbol}] "
            f"{decision.tactical_state} | "
            f"{decision.decision_reason} | "
            f"Confidence={decision.confidence}"
        )
