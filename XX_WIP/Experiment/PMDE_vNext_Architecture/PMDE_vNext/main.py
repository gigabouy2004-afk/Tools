
"""PMDE vNext execution entry point."""

from CORE.context_builder import build_market_context
from LAYERS.L1.l1_engine import L1Engine
from LAYERS.L2.l2_orchestrator import L2Orchestrator
from LAYERS.L4.l4_messaging import L4Messaging


def main():

    context = build_market_context(
        symbol="AOSL",
        timeframe="1d",
        latest_price=37.9,
        ema200=26.63,
        macd=1.10,
        macd_signal=1.02,
        macd_histogram=0.08,
        macd_histogram_slope=-0.03
    )

    l1_result = L1Engine.evaluate(context)

    print(f"L1 STATE => {l1_result.regime_state}")

    if l1_result.escalation_required:

        tactical = L2Orchestrator.investigate_macd(
            symbol="AOSL",
            macd_inputs_1d={
                "macd": 1.10,
                "signal": 1.02,
                "histogram": 0.08,
                "histogram_slope": -0.03
            },
            macd_inputs_4h={
                "macd": -0.02,
                "signal": 0.04,
                "histogram": -0.06,
                "histogram_slope": -0.02
            }
        )

        message = L4Messaging.generate(tactical)

        print(message)


if __name__ == "__main__":
    main()
