from CONFIG.settings import (
    ACTIVE_CONTEXTS,
    ACTIVE_GENERIC_FACTS,
    ACTIVE_INDICATORS,
    ENGINE_MODE,
    ENGINE_MODE_QUICK_SETUP,
    MACD_TIMEFRAMES,
    PRIMARY_TECH_TIMEFRAME,
    SETUP_BRIDGE_TIMEFRAME,
    SETUP_MACD_HISTOGRAM_RISING_STREAK,
    SETUP_PRICE_MIN_ADVANCE_PCT,
    SETUP_PRIMARY_TIMEFRAME,
    SETUP_REJECT_EXTENDED_UP,
    SETUP_REJECT_GAP_UP,
    SETUP_REJECT_HIGH_ATRP,
    SETUP_REQUIRE_EMA200_BULL_ZONE,
    SETUP_RSI_MAX,
    SETUP_RSI_MIN,
    SETUP_RSI_HEADROOM_FULL_SCORE_PCT,
    SETUP_RSI_HEADROOM_MIN_SCORE_PCT,
    SETUP_TRIGGER_TIMEFRAME
)
from LAYERS.L3.l3_compute_layer import L3ComputeLayer
from LAYERS.L4.l4_messaging import L4Messaging
from MODELS.contracts import IndicatorRequest, L1Result, TacticalDecision


class L2Orchestrator:

    @staticmethod
    def plan(
        l1_result: L1Result
    ) -> list[IndicatorRequest]:

        if not l1_result.escalation_required:

            return []

        requests = []

        for fact_name in ACTIVE_GENERIC_FACTS:

            if fact_name == "EMA200":

                requests.append(
                    IndicatorRequest(
                        name="EMA200",
                        timeframes=[PRIMARY_TECH_TIMEFRAME]
                    )
                )

            elif fact_name == "PRICE_CONTEXT":

                requests.append(
                    IndicatorRequest(
                        name="PRICE_CONTEXT",
                        timeframes=[PRIMARY_TECH_TIMEFRAME]
                    )
                )

            elif fact_name == "SESSION_CONTEXT":

                requests.append(
                    IndicatorRequest(
                        name="SESSION_CONTEXT",
                        timeframes=[PRIMARY_TECH_TIMEFRAME]
                    )
                )

        for indicator_name in ACTIVE_INDICATORS:

            if indicator_name == "MACD":

                requests.append(
                    IndicatorRequest(
                        name="MACD",
                        timeframes=MACD_TIMEFRAMES
                    )
                )

            else:

                requests.append(
                    IndicatorRequest(
                        name=indicator_name,
                        timeframes=[PRIMARY_TECH_TIMEFRAME]
                    )
                )

        for context_name in ACTIVE_CONTEXTS:

            requests.append(
                IndicatorRequest(
                    name=context_name,
                    timeframes=[PRIMARY_TECH_TIMEFRAME]
                )
            )

        return requests

    @staticmethod
    def process(
        symbol: str,
        l1_result: L1Result
    ) -> TacticalDecision:

        if ENGINE_MODE == ENGINE_MODE_QUICK_SETUP:

            return L2Orchestrator.process_setup_scan(
                symbol,
                l1_result
            )

        requests = L2Orchestrator.plan(
            l1_result
        )

        computed_values = {}
        indicators_used = []

        for request in requests:

            timeframe = request.timeframes[0]

            try:

                if request.name == "EMA200":

                    computed_values["EMA200"] = (
                        L3ComputeLayer.EMA200(
                            symbol,
                            timeframe
                        )
                    )

                elif request.name == "PRICE_CONTEXT":

                    computed_values["PRICE_CONTEXT"] = (
                        L3ComputeLayer.PRICE_CONTEXT(
                            symbol,
                            timeframe
                        )
                    )

                elif request.name == "SESSION_CONTEXT":

                    computed_values["SESSION_CONTEXT"] = (
                        L3ComputeLayer.SESSION_CONTEXT(
                            symbol,
                            timeframe
                        )
                    )

                elif request.name == "MACD":

                    computed_values["MACD"] = (
                        L3ComputeLayer.MACD_SUITE(
                            symbol,
                            request.timeframes
                        )
                    )

                elif request.name == "PPO":

                    computed_values["PPO"] = (
                        L3ComputeLayer.PPO(
                            symbol,
                            timeframe
                        )
                    )

                elif request.name == "RSI":

                    computed_values["RSI"] = (
                        L3ComputeLayer.RSI(
                            symbol,
                            timeframe
                        )
                    )

                elif request.name == "ADX_DMI":

                    computed_values["ADX_DMI"] = (
                        L3ComputeLayer.ADX_DMI(
                            symbol,
                            timeframe
                        )
                    )

                elif request.name == "OBV":

                    computed_values["OBV"] = (
                        L3ComputeLayer.OBV(
                            symbol,
                            timeframe
                        )
                    )

                elif request.name == "CMF":

                    computed_values["CMF"] = (
                        L3ComputeLayer.CMF(
                            symbol,
                            timeframe
                        )
                    )

                elif request.name == "ATRP":

                    computed_values["ATRP"] = (
                        L3ComputeLayer.ATRP(
                            symbol,
                            timeframe
                        )
                    )

                elif request.name == "MARKET_CONTEXT":

                    computed_values["MARKET_CONTEXT"] = (
                        L3ComputeLayer.MARKET_CONTEXT(
                            symbol,
                            timeframe
                        )
                    )

                elif request.name == "RELATED_INSTRUMENT_CONTEXT":

                    computed_values["RELATED_INSTRUMENT_CONTEXT"] = (
                        L3ComputeLayer.RELATED_INSTRUMENT_CONTEXT(
                            symbol,
                            timeframe
                        )
                    )

            except Exception as error:

                computed_values.setdefault(
                    "ERRORS",
                    []
                ).append(
                    f"{request.name}: {error}"
                )

            indicators_used.append(
                request.name
            )

        state, confidence, capital_action, reason = (
            L2Orchestrator._decide(
                computed_values
            )
        )

        message = L4Messaging.build(
            symbol=symbol,
            l1_result=l1_result,
            tactical_state=state,
            confidence=confidence,
            capital_action=capital_action,
            decision_reason=reason,
            computed_values=computed_values
        )

        return TacticalDecision(
            symbol=symbol,
            tactical_state=state,
            confidence=confidence,
            capital_action=capital_action,
            message=message,
            indicators_used=indicators_used,
            computed_values=computed_values
        )

    @staticmethod
    def process_setup_scan(
        symbol: str,
        l1_result: L1Result
    ) -> TacticalDecision:

        computed_values = {}
        indicators_used = []

        price_ladder = L2Orchestrator._compute_setup_fact(
            symbol,
            "PRICE_LADDER_CONTEXT",
            computed_values
        )
        indicators_used.append("PRICE_LADDER_CONTEXT")

        if price_ladder is None:

            return L2Orchestrator._setup_decision(
                symbol=symbol,
                l1_result=l1_result,
                state="REJECTED_PRICE_LADDER_UNAVAILABLE",
                setup_happens=False,
                confidence="HIGH",
                capital_action="DO_NOT_ENTER",
                reason="Price ladder could not be computed.",
                computed_values=computed_values,
                indicators_used=indicators_used,
                rejection_stage="PRICE_LADDER_GATE",
                setup_score=0
            )

        price_passed, price_reason = (
            L2Orchestrator._price_ladder_passed(
                price_ladder
            )
        )

        if not price_passed:

            return L2Orchestrator._setup_decision(
                symbol=symbol,
                l1_result=l1_result,
                state="REJECTED_NO_DAILY_PRICE_ADVANCE",
                setup_happens=False,
                confidence="HIGH",
                capital_action="DO_NOT_ENTER",
                reason=price_reason,
                computed_values=computed_values,
                indicators_used=indicators_used,
                rejection_stage="PRICE_LADDER_GATE",
                setup_score=0
            )

        macd_suite = {}

        for timeframe in [
            SETUP_PRIMARY_TIMEFRAME,
            SETUP_BRIDGE_TIMEFRAME,
            SETUP_TRIGGER_TIMEFRAME
        ]:

            try:

                macd_suite[timeframe] = L3ComputeLayer.MACD(
                    symbol,
                    timeframe
                )

            except Exception as error:

                computed_values.setdefault(
                    "ERRORS",
                    []
                ).append(
                    f"MACD_{timeframe}: {error}"
                )

                return L2Orchestrator._setup_decision(
                    symbol=symbol,
                    l1_result=l1_result,
                    state="REJECTED_MACD_UNAVAILABLE",
                    setup_happens=False,
                    confidence="HIGH",
                    capital_action="DO_NOT_ENTER",
                    reason=(
                        "MACD setup drill-down could not be "
                        f"computed for {timeframe}."
                    ),
                    computed_values=computed_values,
                    indicators_used=indicators_used + ["MACD"],
                    rejection_stage="MACD_GATE",
                    setup_score=2
                )

        computed_values["MACD"] = macd_suite
        indicators_used.append("MACD")

        macd_1d = macd_suite[SETUP_PRIMARY_TIMEFRAME]
        macd_4h = macd_suite[SETUP_BRIDGE_TIMEFRAME]
        macd_1h = macd_suite[SETUP_TRIGGER_TIMEFRAME]

        if not L2Orchestrator._macd_daily_constructive(
            macd_1d
        ):

            return L2Orchestrator._setup_decision(
                symbol=symbol,
                l1_result=l1_result,
                state="REJECTED_DAILY_MACD_NOT_CONSTRUCTIVE",
                setup_happens=False,
                confidence="HIGH",
                capital_action="DO_NOT_ENTER",
                reason=(
                    "P(x) passed, but 1D MACD is not "
                    "constructive enough to investigate "
                    "lower timeframes."
                ),
                computed_values=computed_values,
                indicators_used=indicators_used,
                rejection_stage="DAILY_MACD_GATE",
                setup_score=2
            )

        if not L2Orchestrator._macd_bridge_constructive(
            macd_4h
        ):

            return L2Orchestrator._setup_decision(
                symbol=symbol,
                l1_result=l1_result,
                state="SETUP_FORMING_WAIT_FOR_4H",
                setup_happens=False,
                confidence="MEDIUM",
                capital_action="WAIT",
                reason=(
                    "Daily price and 1D MACD are constructive, "
                    "but 4H MACD has not confirmed that the "
                    "move is translating downward."
                ),
                computed_values=computed_values,
                indicators_used=indicators_used,
                rejection_stage="FOUR_HOUR_MACD_GATE",
                setup_score=4
            )

        if not L2Orchestrator._macd_trigger_active(
            macd_1h
        ):

            return L2Orchestrator._setup_decision(
                symbol=symbol,
                l1_result=l1_result,
                state="SETUP_FORMING_WAIT_FOR_1H",
                setup_happens=False,
                confidence="MEDIUM",
                capital_action="WAIT",
                reason=(
                    "Daily and 4H conditions are constructive, "
                    "but the current 1H MACD trigger is not "
                    "accelerating yet."
                ),
                computed_values=computed_values,
                indicators_used=indicators_used,
                rejection_stage="ONE_HOUR_MACD_GATE",
                setup_score=6
            )

        for fact_name in [
            "EMA200",
            "PRICE_CONTEXT",
            "SESSION_CONTEXT",
            "RSI",
            "ADX_DMI",
            "OBV",
            "CMF",
            "ATRP"
        ]:

            L2Orchestrator._compute_setup_fact(
                symbol,
                fact_name,
                computed_values
            )

            indicators_used.append(
                fact_name
            )

        support_passed, support_state, support_reason, setup_score = (
            L2Orchestrator._setup_support_passed(
                computed_values
            )
        )

        if not support_passed:

            return L2Orchestrator._setup_decision(
                symbol=symbol,
                l1_result=l1_result,
                state=support_state,
                setup_happens=False,
                confidence="HIGH",
                capital_action="DO_NOT_ENTER",
                reason=support_reason,
                computed_values=computed_values,
                indicators_used=indicators_used,
                rejection_stage="SUPPORT_FILTER_GATE",
                setup_score=setup_score
            )

        setup_state = (
            "PRE_BULL_SETUP_NOW"
            if macd_1d.state == "BEARISH"
            else "BULL_CONTINUATION_SETUP_NOW"
        )

        confidence = L2Orchestrator._setup_confidence(
            setup_score,
            computed_values
        )

        capital_action = "ELIGIBLE_FOR_FRESH_POSITION"

        atrp = computed_values.get("ATRP")

        if atrp and atrp.get("risk") == "HIGH":

            capital_action = "ELIGIBLE_SMALL_POSITION_RISK_CONTROL"

        reason = (
            "P(x) daily price progression passed; "
            "1D MACD is constructive; 4H confirms the "
            "move is translating downward; current 1H "
            "MACD is accelerating."
        )

        return L2Orchestrator._setup_decision(
            symbol=symbol,
            l1_result=l1_result,
            state=setup_state,
            setup_happens=True,
            confidence=confidence,
            capital_action=capital_action,
            reason=reason,
            computed_values=computed_values,
            indicators_used=indicators_used,
            rejection_stage=None,
            setup_score=setup_score
        )

    @staticmethod
    def no_change(
        symbol: str,
        l1_result: L1Result
    ) -> TacticalDecision:

        return TacticalDecision(
            symbol=symbol,
            tactical_state="NO_L2_TRIGGER",
            confidence="HIGH",
            capital_action="STATUS_QUO",
            message=(
                f"{symbol}: "
                f"L1={l1_result.regime_state}; "
                f"L2 was not triggered. "
                f"{l1_result.reason}."
            ),
            indicators_used=[],
            computed_values={}
        )

    @staticmethod
    def _compute_setup_fact(
        symbol: str,
        fact_name: str,
        computed_values: dict
    ):

        try:

            if fact_name == "PRICE_LADDER_CONTEXT":

                computed_values[fact_name] = (
                    L3ComputeLayer.PRICE_LADDER_CONTEXT(
                        symbol,
                        SETUP_PRIMARY_TIMEFRAME
                    )
                )

            elif fact_name == "EMA200":

                computed_values[fact_name] = (
                    L3ComputeLayer.EMA200(
                        symbol,
                        SETUP_PRIMARY_TIMEFRAME
                    )
                )

            elif fact_name == "PRICE_CONTEXT":

                computed_values[fact_name] = (
                    L3ComputeLayer.PRICE_CONTEXT(
                        symbol,
                        SETUP_PRIMARY_TIMEFRAME
                    )
                )

            elif fact_name == "SESSION_CONTEXT":

                computed_values[fact_name] = (
                    L3ComputeLayer.SESSION_CONTEXT(
                        symbol,
                        SETUP_PRIMARY_TIMEFRAME
                    )
                )

            elif fact_name == "RSI":

                computed_values[fact_name] = (
                    L3ComputeLayer.RSI(
                        symbol,
                        SETUP_PRIMARY_TIMEFRAME
                    )
                )

            elif fact_name == "ADX_DMI":

                computed_values[fact_name] = (
                    L3ComputeLayer.ADX_DMI(
                        symbol,
                        SETUP_PRIMARY_TIMEFRAME
                    )
                )

            elif fact_name == "OBV":

                computed_values[fact_name] = (
                    L3ComputeLayer.OBV(
                        symbol,
                        SETUP_PRIMARY_TIMEFRAME
                    )
                )

            elif fact_name == "CMF":

                computed_values[fact_name] = (
                    L3ComputeLayer.CMF(
                        symbol,
                        SETUP_PRIMARY_TIMEFRAME
                    )
                )

            elif fact_name == "ATRP":

                computed_values[fact_name] = (
                    L3ComputeLayer.ATRP(
                        symbol,
                        SETUP_PRIMARY_TIMEFRAME
                    )
                )

            return computed_values.get(
                fact_name
            )

        except Exception as error:

            computed_values.setdefault(
                "ERRORS",
                []
            ).append(
                f"{fact_name}: {error}"
            )

            return None

    @staticmethod
    def _price_ladder_passed(
        price_ladder: dict
    ) -> tuple[bool, str]:

        if not price_ladder:

            return (
                False,
                "Price ladder data is unavailable."
            )

        p0_gt_p1 = price_ladder.get(
            "p0_gt_p1",
            False
        )

        p0_gt_px = price_ladder.get(
            "p0_gt_px",
            False
        )

        advance_pct = price_ladder.get(
            "advance_pct"
        )

        advance_ok = (
            advance_pct is not None
            and
            advance_pct >= SETUP_PRICE_MIN_ADVANCE_PCT
        )

        if p0_gt_p1 and p0_gt_px and advance_ok:

            return (
                True,
                (
                    "P(x) passed: latest completed close is "
                    "above P-1 and P-X with sufficient advance."
                )
            )

        return (
            False,
            (
                "P(x) failed: latest completed close is not "
                "showing enough daily price progression "
                f"(P0={price_ladder.get('p0')}, "
                f"P-1={price_ladder.get('p1')}, "
                f"P-X={price_ladder.get('px')}, "
                f"advance={advance_pct}%)."
            )
        )

    @staticmethod
    def _macd_daily_constructive(
        macd
    ) -> bool:

        if macd is None:

            return False

        if (
            macd.state == "BULLISH"
            and
            macd.histogram_slope >= 0
        ):

            return True

        return (
            macd.state == "BEARISH"
            and
            macd.histogram_slope > 0
            and
            macd.histogram_rising_streak >= 1
        )

    @staticmethod
    def _macd_bridge_constructive(
        macd
    ) -> bool:

        if macd is None:

            return False

        if (
            macd.state == "BULLISH"
            and
            macd.histogram_slope >= 0
        ):

            return True

        return (
            macd.histogram_slope > 0
            and
            (
                macd.spread_contracting
                or
                macd.histogram_rising_streak >= 1
            )
        )

    @staticmethod
    def _macd_trigger_active(
        macd
    ) -> bool:

        if macd is None:

            return False

        return (
            macd.histogram_slope > 0
            and
            macd.histogram_rising_streak >= (
                SETUP_MACD_HISTOGRAM_RISING_STREAK
            )
            and
            (
                macd.state == "BULLISH"
                or
                macd.spread_contracting
            )
        )

    @staticmethod
    def _setup_support_passed(
        computed_values
    ) -> tuple[bool, str, str, int]:

        score = 9

        ema200 = computed_values.get("EMA200")

        if SETUP_REQUIRE_EMA200_BULL_ZONE:

            if not ema200:

                return (
                    False,
                    "REJECTED_EMA200_UNAVAILABLE",
                    "EMA200 could not be computed.",
                    score
                )

            if not getattr(
                ema200,
                "is_sufficient",
                True
            ):

                return (
                    False,
                    "REJECTED_EMA200_INSUFFICIENT_HISTORY",
                    getattr(
                        ema200,
                        "reason",
                        "EMA200 history is insufficient."
                    ),
                    score
                )

            if (
                ema200.zone != "BULL_ZONE"
                or
                ema200.slope_state == "FALLING"
            ):

                return (
                    False,
                    "REJECTED_EMA200_NOT_SUPPORTIVE",
                    (
                        "EMA200 support failed: price is not "
                        "above a supportive EMA200 structure."
                    ),
                    score
                )

            score += 2

        session_context = computed_values.get(
            "SESSION_CONTEXT"
        )

        if session_context:

            if (
                SETUP_REJECT_EXTENDED_UP
                and
                session_context.get("state") == "EXTENDED_UP"
            ):

                return (
                    False,
                    "WATCH_NOT_CHASE_SESSION_EXTENDED",
                    (
                        "Setup is constructive, but the current "
                        "session is already extended upward."
                    ),
                    score
                )

            if (
                SETUP_REJECT_GAP_UP
                and
                session_context.get("gap_state") == "GAP_UP"
            ):

                return (
                    False,
                    "WATCH_NOT_CHASE_GAP_UP",
                    (
                        "Setup is constructive, but the current "
                        "session opened with a gap up."
                    ),
                    score
                )

        rsi = computed_values.get("RSI")

        if rsi:

            latest_rsi = rsi.get("rsi")

            if (
                latest_rsi is not None
                and
                latest_rsi < SETUP_RSI_MIN
            ):

                return (
                    False,
                    "REJECTED_RSI_TOO_WEAK",
                    (
                        "RSI is below the setup strength "
                        "threshold."
                    ),
                    score
                )

            if (
                latest_rsi is not None
                and
                latest_rsi > SETUP_RSI_MAX
            ):

                return (
                    False,
                    "WATCH_NOT_CHASE_RSI_EXTENDED",
                    (
                        "RSI is above the setup chase-control "
                        "threshold."
                    ),
                    score
                )

            if latest_rsi is not None:

                rsi_headroom = SETUP_RSI_MAX - latest_rsi
                rsi_band = max(
                    SETUP_RSI_MAX - SETUP_RSI_MIN,
                    1
                )
                rsi_headroom_pct = (
                    rsi_headroom /
                    rsi_band
                ) * 100

                rsi_room_score = 0

                if rsi_headroom_pct >= SETUP_RSI_HEADROOM_FULL_SCORE_PCT:

                    rsi_room_score = 2

                elif rsi_headroom_pct >= SETUP_RSI_HEADROOM_MIN_SCORE_PCT:

                    rsi_room_score = 1

                computed_values["RSI_HEADROOM"] = {
                    "headroom": round(
                        float(rsi_headroom),
                        4
                    ),
                    "headroom_pct": round(
                        float(rsi_headroom_pct),
                        4
                    ),
                    "room_score": rsi_room_score,
                    "full_score_pct": SETUP_RSI_HEADROOM_FULL_SCORE_PCT,
                    "min_score_pct": SETUP_RSI_HEADROOM_MIN_SCORE_PCT,
                    "max_rsi": SETUP_RSI_MAX
                }

                score += rsi_room_score

            score += 1

        adx = computed_values.get("ADX_DMI")

        if adx:

            if (
                adx.get("direction") == "BEARISH"
                and
                adx.get("strength") == "STRONG"
            ):

                return (
                    False,
                    "REJECTED_STRONG_BEARISH_ADX",
                    (
                        "ADX/DMI still confirms a strong bearish "
                        "trend."
                    ),
                    score
                )

            if adx.get("direction") == "BULLISH":

                score += 1

        obv = computed_values.get("OBV")
        cmf = computed_values.get("CMF")

        if obv and obv.get("state") == "ACCUMULATION":

            score += 1

        if cmf and cmf.get("state") == "ACCUMULATION":

            score += 1

        if (
            obv
            and
            cmf
            and
            obv.get("state") == "DISTRIBUTION"
            and
            cmf.get("state") == "DISTRIBUTION"
        ):

            return (
                False,
                "REJECTED_DISTRIBUTION_PRESSURE",
                (
                    "Both OBV and CMF show distribution, so "
                    "participation does not support fresh entry."
                ),
                score
            )

        atrp = computed_values.get("ATRP")

        if atrp and atrp.get("risk") == "HIGH":

            if SETUP_REJECT_HIGH_ATRP:

                return (
                    False,
                    "REJECTED_HIGH_VOLATILITY_RISK",
                    (
                        "ATRP is high and high-volatility setups "
                        "are disabled by configuration."
                    ),
                    score
                )

            score -= 1

        return (
            True,
            "SUPPORT_FILTERS_PASSED",
            "Support filters passed.",
            score
        )

    @staticmethod
    def _setup_confidence(
        setup_score: int,
        computed_values
    ) -> str:

        atrp = computed_values.get("ATRP")

        if (
            atrp
            and
            atrp.get("risk") == "HIGH"
            and
            setup_score < 13
        ):

            return "MEDIUM"

        if setup_score >= 13:

            return "HIGH"

        if setup_score >= 10:

            return "MEDIUM"

        return "LOW"

    @staticmethod
    def _setup_decision(
        symbol: str,
        l1_result: L1Result,
        state: str,
        setup_happens: bool,
        confidence: str,
        capital_action: str,
        reason: str,
        computed_values: dict,
        indicators_used: list[str],
        rejection_stage: str | None,
        setup_score: int | None
    ) -> TacticalDecision:

        message = L4Messaging.build_setup(
            symbol=symbol,
            l1_result=l1_result,
            setup_state=state,
            setup_happens=setup_happens,
            confidence=confidence,
            capital_action=capital_action,
            decision_reason=reason,
            computed_values=computed_values,
            rejection_stage=rejection_stage,
            setup_score=setup_score
        )

        return TacticalDecision(
            symbol=symbol,
            tactical_state=state,
            confidence=confidence,
            capital_action=capital_action,
            message=message,
            indicators_used=indicators_used,
            computed_values=computed_values,
            setup_happens=setup_happens,
            setup_score=setup_score,
            rejection_stage=rejection_stage
        )

    @staticmethod
    def _decide(
        computed_values
    ):

        macd_suite = computed_values.get(
            "MACD",
            {}
        )

        macd_1h = macd_suite.get("1h")
        macd_4h = macd_suite.get("4h")
        macd_1d = macd_suite.get("1d")

        if not (macd_1h and macd_4h and macd_1d):

            errors = computed_values.get(
                "ERRORS",
                []
            )

            error_text = (
                " L3 errors: " +
                " | ".join(errors)
                if errors
                else ""
            )

            return (
                "INSUFFICIENT_TECHNICAL_DATA",
                "LOW",
                "REVIEW_MANUALLY",
                (
                    "Required MACD timeframes are incomplete."
                    f"{error_text}"
                )
            )

        support = L2Orchestrator._support_profile(
            computed_values
        )

        reason_tail = L2Orchestrator._support_reason(
            support
        )

        session_context = computed_values.get(
            "SESSION_CONTEXT"
        )

        ema200 = computed_values.get("EMA200")

        if (
            ema200
            and
            not getattr(
                ema200,
                "is_sufficient",
                True
            )
        ):

            return (
                "INSUFFICIENT_HISTORY_FOR_BASELINE",
                "LOW",
                "REVIEW_MANUALLY",
                (
                    f"{ema200.reason}. "
                    "L2 tactical classification is withheld "
                    "because the EMA200 baseline is not valid. "
                    f"{reason_tail}"
                )
            )

        lower_timeframe_bearish_count = sum(
            [
                macd_4h.state == "BEARISH",
                macd_1h.state == "BEARISH"
            ]
        )

        lower_timeframe_bullish_count = sum(
            [
                macd_4h.state == "BULLISH",
                macd_1h.state == "BULLISH"
            ]
        )

        support_bullish_dominant = (
            support["bullish_score"] >=
            support["bearish_score"] + 2
        )

        daily_bear_transition_risk = (
            macd_1d.histogram <= 0
            or
            macd_1d.crossover_distance <= 0.02
        )

        daily_bullish_deteriorating = (
            macd_1d.state == "BULLISH"
            and
            macd_1d.histogram_slope < 0
        )

        pre_bear = (
            daily_bullish_deteriorating
            and
            (
                support["bearish_score"] >= 3
                or
                (
                    lower_timeframe_bearish_count == 2
                    and
                    daily_bear_transition_risk
                    and
                    not support_bullish_dominant
                )
            )
        )

        if pre_bear:

            return (
                "PRE_BEAR_CROSSOVER",
                L2Orchestrator._confidence(
                    support,
                    direction="BEARISH"
                ),
                "PROTECT_CAPITAL",
                (
                    "The 1D MACD structure is still bullish, "
                    "but deterioration is visible through "
                    "lower timeframe or supporting indicators. "
                    f"{reason_tail}"
                )
            )

        bull_pullback_risk = (
            daily_bullish_deteriorating
            and
            (
                lower_timeframe_bearish_count > 0
                or
                support["bearish_score"] > 0
            )
        )

        if bull_pullback_risk:

            return (
                "BULL_STRUCTURE_PULLBACK_RISK",
                L2Orchestrator._confidence(
                    support,
                    direction="BULLISH"
                ),
                "HOLD_WITH_RISK_CONTROL",
                (
                    "The 1D MACD structure remains bullish, "
                    "but momentum is cooling on lower "
                    "timeframes or support indicators. "
                    "This is a risk-control condition, not a "
                    "capital-protection crossover warning yet. "
                    f"{reason_tail}"
                )
            )

        prebull_support_confirmed = (
            support["bullish_score"] >= 3
            and
            support["bullish_score"] >
            support["bearish_score"]
        )

        daily_bearish_recovering = (
            macd_1d.state == "BEARISH"
            and
            macd_1d.histogram_slope > 0
        )

        pre_bull = (
            daily_bearish_recovering
            and
            lower_timeframe_bullish_count > 0
            and
            prebull_support_confirmed
        )

        if pre_bull:

            action = "ACCUMULATION_WATCH"
            action_reason = ""

            if (
                session_context
                and
                session_context.get("state") == "EXTENDED_UP"
            ):

                action = "WATCH_NOT_CHASE"
                action_reason = (
                    " Price is already extended in the "
                    "current session, so do not chase the "
                    "move."
                )

            return (
                "PRE_BULL_CROSSOVER",
                L2Orchestrator._confidence(
                    support,
                    direction="BULLISH"
                ),
                action,
                (
                    "The 1D MACD structure is still bearish, "
                    "but recovery is visible through lower "
                    "timeframe or supporting indicators. "
                    f"{action_reason} "
                    f"{reason_tail}"
                )
            )

        weak_pre_bull = (
            daily_bearish_recovering
            and
            lower_timeframe_bullish_count > 0
        )

        if weak_pre_bull:

            return (
                "EARLY_RECOVERY_INSIDE_BEAR_STRUCTURE",
                "MEDIUM",
                "WAIT_FOR_1D_CONFIRMATION",
                (
                    "Recovery is visible below the daily "
                    "timeframe, but the support profile is "
                    "not strong enough for an accumulation "
                    "watch. "
                    f"{reason_tail}"
                )
            )

        if (
            macd_1d.state == "BEARISH"
            and
            macd_4h.state == "BEARISH"
        ):

            if macd_1h.state == "BULLISH":

                return (
                    "EARLY_RECOVERY_INSIDE_BEAR_STRUCTURE",
                    "MEDIUM",
                    "WAIT_FOR_1D_CONFIRMATION",
                    (
                        "Bearish pressure is confirmed on "
                        "1D and 4H, while 1H is bullish. "
                        f"{reason_tail}"
                    )
                )

            return (
                "BEAR_CROSSOVER_CONFIRMED",
                L2Orchestrator._confidence(
                    support,
                    direction="BEARISH"
                ),
                "PROTECT_CAPITAL",
                (
                    "Bearish crossover pressure is confirmed "
                    "on the higher timeframes. "
                    f"{reason_tail}"
                )
            )

        if (
            macd_1d.state == "BULLISH"
            and
            macd_4h.state == "BULLISH"
        ):

            action = "HOLD_OR_GROW"

            if support["risk_state"] == "HIGH":

                action = "HOLD_WITH_RISK_CONTROL"

            return (
                "BULL_STRUCTURE_SECURED",
                L2Orchestrator._confidence(
                    support,
                    direction="BULLISH"
                ),
                action,
                (
                    "Bullish alignment is confirmed across "
                    "the higher timeframes. "
                    f"{reason_tail}"
                )
            )

        return (
            "STATUS_QUO_NO_CROSSOVER",
            "MEDIUM",
            "STATUS_QUO",
            (
                "Mixed timeframe signals are present. "
                f"{reason_tail}"
            )
        )

    @staticmethod
    def _support_profile(
        computed_values
    ) -> dict:

        bullish_score = 0
        bearish_score = 0
        notes = []

        ppo = computed_values.get("PPO")

        if ppo:

            if ppo["state"] == "BULLISH":

                bullish_score += 1
                notes.append("PPO bullish")

            else:

                bearish_score += 1
                notes.append("PPO bearish")

        rsi = computed_values.get("RSI")

        if rsi:

            if rsi["state"] == "BULLISH":

                bullish_score += 1
                notes.append("RSI constructive")

            elif rsi["state"] == "BEARISH":

                bearish_score += 1
                notes.append("RSI weak")

        adx = computed_values.get("ADX_DMI")

        if adx and adx["strength"] == "STRONG":

            if adx["direction"] == "BULLISH":

                bullish_score += 1
                notes.append("ADX confirms bullish trend")

            else:

                bearish_score += 1
                notes.append("ADX confirms bearish trend")

        obv = computed_values.get("OBV")

        if obv:

            if obv["state"] == "ACCUMULATION":

                bullish_score += 1
                notes.append("OBV accumulation")

            elif obv["state"] == "DISTRIBUTION":

                bearish_score += 1
                notes.append("OBV distribution")

        cmf = computed_values.get("CMF")

        if cmf:

            if cmf["state"] == "ACCUMULATION":

                bullish_score += 1
                notes.append("CMF accumulation")

            elif cmf["state"] == "DISTRIBUTION":

                bearish_score += 1
                notes.append("CMF distribution")

        ema200 = computed_values.get("EMA200")

        if ema200:

            if not getattr(
                ema200,
                "is_sufficient",
                True
            ):

                notes.append(
                    getattr(
                        ema200,
                        "reason",
                        "EMA200 history insufficient"
                    )
                )

            elif (
                ema200.zone == "BULL_ZONE"
                and
                ema200.slope_state in ["RISING", "FLAT"]
            ):

                bullish_score += 1
                notes.append("EMA200 structure supportive")

            elif (
                ema200.zone == "BEAR_ZONE"
                or
                ema200.slope_state == "FALLING"
            ):

                bearish_score += 1
                notes.append("EMA200 structure weak")

        atrp = computed_values.get("ATRP")

        risk_state = (
            atrp["risk"]
            if atrp
            else "UNKNOWN"
        )

        if risk_state == "HIGH":

            notes.append("high volatility risk")

        price_context = computed_values.get(
            "PRICE_CONTEXT"
        )

        if price_context:

            if price_context["state"] == "NEAR_HIGH":

                notes.append("price near 52-week high")

            elif price_context["state"] == "NEAR_LOW":

                notes.append("price near 52-week low")

        session_context = computed_values.get(
            "SESSION_CONTEXT"
        )

        if session_context:

            if session_context["state"] == "EXTENDED_UP":

                notes.append(
                    "price already extended upward today"
                )

            elif session_context["state"] == "EXTENDED_DOWN":

                notes.append(
                    "price sharply lower today"
                )

            if session_context["gap_state"] == "GAP_UP":

                notes.append(
                    "opened with a bullish gap"
                )

            elif session_context["gap_state"] == "GAP_DOWN":

                notes.append(
                    "opened with a bearish gap"
                )

        return {
            "bullish_score": bullish_score,
            "bearish_score": bearish_score,
            "risk_state": risk_state,
            "notes": notes
        }

    @staticmethod
    def _confidence(
        support: dict,
        direction: str
    ) -> str:

        score = (
            support["bullish_score"]
            if direction == "BULLISH"
            else support["bearish_score"]
        )

        if support["risk_state"] == "HIGH":

            return "MEDIUM"

        if score >= 3:

            return "HIGH"

        if score >= 1:

            return "MEDIUM"

        return "LOW"

    @staticmethod
    def _support_reason(
        support: dict
    ) -> str:

        notes = support["notes"]

        if not notes:

            return "No additional support indicators are available."

        return (
            "Support profile: " +
            "; ".join(notes) +
            "."
        )
