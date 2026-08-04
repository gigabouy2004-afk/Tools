class L4Messaging:

    @staticmethod
    def build(
        symbol,
        l1_result,
        tactical_result,
        macd_1d=None,
        macd_4h=None,
        macd_1h=None
    ):

        lines = []

        lines.append("=" * 60)
        lines.append(f"SYMBOL : {symbol}")
        lines.append("=" * 60)

        lines.append(
            f"L1 STATUS      : "
            f"{l1_result.regime_state}"
        )

        lines.append(
            f"TACTICAL STATE : "
            f"{tactical_result['state']}"
        )

        lines.append("")

        lines.append(
            tactical_result["message"]
        )

        lines.append("=" * 60)

        return "\\n".join(lines)