class L4Messaging:

    @staticmethod
    def build_setup(
        symbol,
        l1_result,
        setup_state,
        setup_happens,
        confidence,
        capital_action,
        decision_reason,
        computed_values,
        rejection_stage=None,
        setup_score=None
    ):

        price_ladder = computed_values.get(
            "PRICE_LADDER_CONTEXT",
            {}
        )

        macd_suite = computed_values.get(
            "MACD",
            {}
        )

        macd_1d = macd_suite.get("1d")
        macd_4h = macd_suite.get("4h")
        macd_1h = macd_suite.get("1h")

        ema200 = computed_values.get("EMA200")
        rsi = computed_values.get("RSI")
        rsi_headroom = computed_values.get(
            "RSI_HEADROOM"
        )
        adx = computed_values.get("ADX_DMI")
        obv = computed_values.get("OBV")
        cmf = computed_values.get("CMF")
        atrp = computed_values.get("ATRP")
        session_context = computed_values.get(
            "SESSION_CONTEXT"
        )

        setup_flag = (
            "YES"
            if setup_happens
            else "NO"
        )

        parts = [
            f"{symbol}: Setup={setup_flag}",
            f"State={setup_state}",
            f"Confidence={confidence}",
            f"Capital_Action={capital_action}"
        ]

        if setup_score is not None:

            parts.append(
                f"Setup_Score={setup_score}"
            )

        if rejection_stage:

            parts.append(
                f"Rejected_At={rejection_stage}"
            )

        parts.append(
            decision_reason
        )

        if price_ladder:

            parts.append(
                "P(x): "
                f"P0={price_ladder.get('p0')}, "
                f"P-1={price_ladder.get('p1')}, "
                f"P-X={price_ladder.get('px')}, "
                f"advance={price_ladder.get('advance_pct')}%"
            )

        macd_parts = []

        for label, result in [
            ("1D", macd_1d),
            ("4H", macd_4h),
            ("1H", macd_1h)
        ]:

            if result:

                macd_parts.append(
                    f"{label}={result.state}/"
                    f"hist={result.histogram}/"
                    f"slope={result.histogram_slope}/"
                    f"rise={result.histogram_rising_streak}"
                )

        if macd_parts:

            parts.append(
                "MACD path: " +
                ", ".join(macd_parts)
            )

        support_parts = []

        if ema200:

            support_parts.append(
                "EMA200="
                f"{ema200.zone}/"
                f"{ema200.slope_state}"
            )

        if rsi:

            support_parts.append(
                f"RSI={rsi.get('rsi')}"
            )

        if rsi_headroom:

            support_parts.append(
                "RSI_Headroom="
                f"{rsi_headroom.get('headroom')}/"
                f"{rsi_headroom.get('headroom_pct')}%/"
                f"score={rsi_headroom.get('room_score')}"
            )

        if adx:

            support_parts.append(
                "ADX="
                f"{adx.get('direction')}/"
                f"{adx.get('strength')}"
            )

        if obv:

            support_parts.append(
                f"OBV={obv.get('state')}"
            )

        if cmf:

            support_parts.append(
                f"CMF={cmf.get('state')}"
            )

        if atrp:

            support_parts.append(
                "ATRP="
                f"{atrp.get('atrp')}%/"
                f"{atrp.get('risk')}"
            )

        if session_context:

            support_parts.append(
                "Session="
                f"{session_context.get('state')}/"
                f"{session_context.get('day_change_pct')}%"
            )

        if support_parts:

            parts.append(
                "Support: " +
                ", ".join(support_parts)
            )

        errors = computed_values.get(
            "ERRORS",
            []
        )

        if errors:

            parts.append(
                "L3 errors: " +
                " | ".join(errors)
            )

        clean_parts = [
            str(part).rstrip(".")
            for part in parts
            if part
        ]

        return ". ".join(clean_parts) + "."

    @staticmethod
    def build(
        symbol,
        l1_result,
        tactical_state,
        confidence,
        capital_action,
        decision_reason,
        computed_values
    ):

        macd_suite = computed_values.get(
            "MACD",
            {}
        )

        ema200 = computed_values.get(
            "EMA200"
        )

        ppo = computed_values.get("PPO")
        rsi = computed_values.get("RSI")
        adx = computed_values.get("ADX_DMI")
        obv = computed_values.get("OBV")
        cmf = computed_values.get("CMF")
        atrp = computed_values.get("ATRP")
        price_context = computed_values.get(
            "PRICE_CONTEXT"
        )
        session_context = computed_values.get(
            "SESSION_CONTEXT"
        )

        macd_1d = macd_suite.get("1d")
        macd_4h = macd_suite.get("4h")
        macd_1h = macd_suite.get("1h")

        macd_text = (
            "MACD unavailable"
        )

        if macd_1d and macd_4h and macd_1h:

            macd_text = (
                f"MACD states: "
                f"1D={macd_1d.state}, "
                f"4H={macd_4h.state}, "
                f"1H={macd_1h.state}"
            )

        ema_text = (
            "EMA200 unavailable"
        )

        if ema200:

            if not getattr(
                ema200,
                "is_sufficient",
                True
            ):

                ema_text = (
                    "EMA200 unavailable: "
                    f"{ema200.reason}"
                )

            else:

                ema_text = (
                    f"EMA200 zone={ema200.zone}, "
                    f"distance={ema200.distance_pct}%, "
                    f"slope={ema200.slope_state}"
                )

        support_parts = []

        if ppo:

            support_parts.append(
                f"PPO={ppo['state']}"
            )

        if rsi:

            support_parts.append(
                f"RSI={rsi['rsi']}"
            )

        if adx:

            support_parts.append(
                f"ADX={adx['adx']} "
                f"{adx['direction']}/{adx['strength']}"
            )

        if obv:

            support_parts.append(
                f"OBV={obv['state']}"
            )

        if cmf:

            support_parts.append(
                f"CMF={cmf['state']}"
            )

        if atrp:

            support_parts.append(
                f"ATRP={atrp['atrp']}% "
                f"{atrp['risk']}"
            )

        if price_context:

            support_parts.append(
                f"52W={price_context['state']}"
            )

        if session_context:

            support_parts.append(
                "Session="
                f"{session_context['state']} "
                f"{session_context['day_change_pct']}%"
            )

            if session_context["gap_state"] != "NO_GAP":

                support_parts.append(
                    "Gap="
                    f"{session_context['gap_state']} "
                    f"{session_context['opening_gap_pct']}%"
                )

        support_text = "No extended support indicators."

        if support_parts:

            support_text = (
                "Extended support: " +
                ", ".join(support_parts) +
                "."
            )

        return (
            f"{symbol}: "
            f"L1={l1_result.regime_state}; "
            f"L2={tactical_state} "
            f"({confidence}); "
            f"Capital_Action={capital_action}. "
            f"{decision_reason} "
            f"{macd_text}; "
            f"{ema_text}. "
            f"{support_text}"
        )
