from datetime import UTC, datetime

import pandas as pd

from CONFIG.settings import (
    ENGINE_MODE,
    ENGINE_MODE_QUICK_CROSSOVER,
    ENGINE_MODE_QUICK_SETUP,
    FORCE_L2_ASSESSMENT,
    L1_PRICE_CHANGE_TRIGGER_PCT
)
from CORE.baseline_registry import BaselineRegistry
from IO.data_loader import DataLoader
from LAYERS.L2.l2_orchestrator import L2Orchestrator
from MODELS.contracts import BasicSnapshot, L1Assessment, L1Result


class L1Engine:

    SETUP_OUTPUT_COLUMNS = [
        "Symbol",
        "Setup_Happens",
        "Setup_State",
        "Capital_Action",
        "Confidence",
        "Setup_Score",
        "Rejection_Stage",
        "L1_State",
        "Primary_Reason",
        "Latest_Price",
        "Price_Ladder_State",
        "Price_Lookback_X",
        "P0_Close",
        "P1_Close",
        "PX_Close",
        "PX_Advance_Pct",
        "Higher_Close_Count",
        "MACD_1D_State",
        "MACD_1D_Histogram",
        "MACD_1D_Histogram_Slope",
        "MACD_1D_Rising_Streak",
        "MACD_4H_State",
        "MACD_4H_Histogram",
        "MACD_4H_Histogram_Slope",
        "MACD_4H_Rising_Streak",
        "MACD_1H_State",
        "MACD_1H_Histogram",
        "MACD_1H_Histogram_Slope",
        "MACD_1H_Rising_Streak",
        "EMA200_Zone",
        "EMA200_D_Pct",
        "EMA200_Slope_State",
        "RSI_1D",
        "RSI_Headroom",
        "RSI_Headroom_Pct",
        "RSI_Room_Score",
        "ADX_Direction",
        "ADX_Strength",
        "OBV_State",
        "CMF_State",
        "ATRP_Risk",
        "Session_State",
        "Session_Change_Pct",
        "Gap_State",
        "Price_Context_State",
        "Setup_Explanation",
        "Final_State"
    ]

    @staticmethod
    def assess(
        symbol: str
    ) -> L1Assessment:

        snapshot = L1Engine._load_basic_snapshot(
            symbol
        )

        if ENGINE_MODE == ENGINE_MODE_QUICK_SETUP:

            l1_result = L1Result(
                symbol=symbol,
                regime_state="QUICK_SETUP_REQUESTED",
                escalation_required=True,
                reason=(
                    "Quick setup mode active; L2 will apply "
                    "P(x), MACD, and support filters"
                ),
                latest_price=snapshot.latest_price,
                data_fetch_timestamp=snapshot.data_fetch_timestamp
            )

            tactical_decision = L2Orchestrator.process(
                symbol,
                l1_result
            )

            output_row = L1Engine.build_output_row(
                symbol,
                l1_result,
                tactical_decision
            )

            return L1Assessment(
                symbol=symbol,
                l1_result=l1_result,
                tactical_decision=tactical_decision,
                output_row=output_row,
                baseline_record=None
            )

        if ENGINE_MODE == ENGINE_MODE_QUICK_CROSSOVER:

            l1_result = L1Result(
                symbol=symbol,
                regime_state="QUICK_CROSSOVER_REVIEW",
                escalation_required=True,
                reason=(
                    "Quick crossover mode active; symbol was "
                    "loaded from the configured quick-crossover "
                    "universe and sent to L2"
                ),
                latest_price=snapshot.latest_price,
                data_fetch_timestamp=snapshot.data_fetch_timestamp
            )

            tactical_decision = L2Orchestrator.process(
                symbol,
                l1_result
            )

            output_row = L1Engine.build_output_row(
                symbol,
                l1_result,
                tactical_decision
            )

            baseline_record = L1Engine.build_baseline_record(
                symbol,
                l1_result,
                tactical_decision
            )

            return L1Assessment(
                symbol=symbol,
                l1_result=l1_result,
                tactical_decision=tactical_decision,
                output_row=output_row,
                baseline_record=baseline_record
            )

        previous_record = BaselineRegistry.get_symbol(
            symbol
        )

        l1_result = L1Engine.evaluate(
            symbol=symbol,
            latest_price=snapshot.latest_price,
            previous_record=previous_record
        )
        l1_result.data_fetch_timestamp = (
            snapshot.data_fetch_timestamp
        )

        if l1_result.escalation_required:

            tactical_decision = L2Orchestrator.process(
                symbol,
                l1_result
            )

        else:

            tactical_decision = L2Orchestrator.no_change(
                symbol,
                l1_result
            )

        output_row = L1Engine.build_output_row(
            symbol,
            l1_result,
            tactical_decision
        )

        baseline_record = L1Engine.build_baseline_record(
            symbol,
            l1_result,
            tactical_decision
        )

        return L1Assessment(
            symbol=symbol,
            l1_result=l1_result,
            tactical_decision=tactical_decision,
            output_row=output_row,
            baseline_record=baseline_record
        )

    @staticmethod
    def evaluate(
        symbol: str,
        latest_price: float,
        previous_record=None
    ) -> L1Result:

        if latest_price <= 0:

            return L1Result(
                symbol=symbol,
                regime_state="REGIME_UNSTABLE",
                escalation_required=True,
                reason="Latest price is not valid",
                latest_price=latest_price
            )

        if FORCE_L2_ASSESSMENT:

            return L1Result(
                symbol=symbol,
                regime_state="FORCED_L2_REVIEW",
                escalation_required=True,
                reason=(
                    "Full L2 assessment forced by settings; "
                    "L1 baseline stability not evaluated"
                ),
                latest_price=latest_price
            )

        if previous_record is None:

            return L1Result(
                symbol=symbol,
                regime_state="REGIME_UNSTABLE",
                escalation_required=True,
                reason="No active baseline record exists",
                latest_price=latest_price
            )

        previous_price = L1Engine._safe_float(
            previous_record.get(
                "latest_price"
            )
        )

        if previous_price is None or previous_price <= 0:

            return L1Result(
                symbol=symbol,
                regime_state="REGIME_UNSTABLE",
                escalation_required=True,
                reason="Previous baseline price is not valid",
                latest_price=latest_price
            )

        rounded_latest_price = round(
            latest_price,
            4
        )

        rounded_previous_price = round(
            previous_price,
            4
        )

        change_pct = abs(
            (
                rounded_latest_price -
                rounded_previous_price
            ) / rounded_previous_price
        ) * 100

        if change_pct > L1_PRICE_CHANGE_TRIGGER_PCT:

            return L1Result(
                symbol=symbol,
                regime_state="REGIME_UNSTABLE",
                escalation_required=True,
                reason=(
                    "Latest price changed by "
                    f"{round(change_pct, 4)}%"
                ),
                latest_price=latest_price
            )

        return L1Result(
            symbol=symbol,
            regime_state="REGIME_STABLE",
            escalation_required=False,
            reason="No baseline trigger detected",
            latest_price=latest_price
        )

    @staticmethod
    def build_output_row(
        symbol: str,
        l1_result: L1Result,
        tactical_decision
    ) -> dict:

        if ENGINE_MODE == ENGINE_MODE_QUICK_SETUP:

            return L1Engine.build_setup_output_row(
                symbol,
                l1_result,
                tactical_decision
            )

        computed_values = (
            tactical_decision.computed_values
            if tactical_decision
            else {}
        )

        ema200 = computed_values.get("EMA200")

        macd_suite = computed_values.get(
            "MACD",
            {}
        )

        macd_1h = macd_suite.get("1h")
        macd_4h = macd_suite.get("4h")
        macd_1d = macd_suite.get("1d")
        ppo = computed_values.get("PPO")
        rsi = computed_values.get("RSI")
        rsi_headroom = computed_values.get("RSI_HEADROOM")
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

        row = {
            "Symbol": symbol,
            "Zone": L1Engine._field(
                ema200,
                "zone",
                "NOT_COMPUTED"
            ),
            "L1_State": l1_result.regime_state,
            "L1_Reason": l1_result.reason,
            "L2_Hypothesis": tactical_decision.tactical_state,
            "Capital_Action": tactical_decision.capital_action,
            "L2_MACD": L1Engine._field(
                macd_4h,
                "state",
                "NOT_USED"
            ),
            "L2_Confidence": tactical_decision.confidence,
            "L2_Indicators_Used": "|".join(
                tactical_decision.indicators_used
            ),
            "L3_Substantiation": tactical_decision.message,
            "PMDE_Explanation": tactical_decision.message,
            "Final_State": tactical_decision.tactical_state,
            "Momentum_State": L1Engine._field(
                macd_1d,
                "state",
                "NOT_USED"
            ),
            "Participation_State": (
                f"OBV={L1Engine._field(obv, 'state', 'NOT_USED')};"
                f"CMF={L1Engine._field(cmf, 'state', 'NOT_USED')}"
            ),
            "Trend_Strength_State": L1Engine._field(
                adx,
                "state",
                "NOT_USED"
            ),
            "Exhaustion_State": L1Engine._field(
                rsi,
                "state",
                "NOT_USED"
            ),
            "Volatility_State": L1Engine._field(
                atrp,
                "risk",
                "NOT_USED"
            ),
            "Session_State": L1Engine._field(
                session_context,
                "state",
                "NOT_USED"
            ),
            "Session_Change_Pct": L1Engine._round_field(
                session_context,
                "day_change_pct"
            ),
            "Opening_Gap_Pct": L1Engine._round_field(
                session_context,
                "opening_gap_pct"
            ),
            "Intraday_Change_Pct": L1Engine._round_field(
                session_context,
                "intraday_change_pct"
            ),
            "Gap_State": L1Engine._field(
                session_context,
                "gap_state",
                "NOT_USED"
            ),
            "EMA200": L1Engine._round_field(
                ema200,
                "ema200"
            ),
            "EMA200_Status": (
                "NOT_COMPUTED"
                if ema200 is None
                else
                "VALID"
                if L1Engine._field(
                    ema200,
                    "is_sufficient",
                    False
                )
                else
                "INSUFFICIENT_HISTORY"
            ),
            "EMA200_Data_Points": L1Engine._field(
                ema200,
                "data_points"
            ),
            "EMA200_Reason": L1Engine._field(
                ema200,
                "reason",
                ""
            ),
            "Latest_Price": round(
                l1_result.latest_price,
                4
            ),
            "EMA200_D_Pct": L1Engine._round_field(
                ema200,
                "distance_pct"
            ),
            "EMA200_Slope_Pct": L1Engine._round_field(
                ema200,
                "slope_pct"
            ),
            "EMA200_Slope_State": L1Engine._field(
                ema200,
                "slope_state",
                "NOT_COMPUTED"
            ),
            "MACD_1H": L1Engine._round_field(
                macd_1h,
                "macd"
            ),
            "SIGNAL_1H": L1Engine._round_field(
                macd_1h,
                "signal"
            ),
            "HISTOGRAM_1H": L1Engine._round_field(
                macd_1h,
                "histogram"
            ),
            "MACD_4H": L1Engine._round_field(
                macd_4h,
                "macd"
            ),
            "SIGNAL_4H": L1Engine._round_field(
                macd_4h,
                "signal"
            ),
            "HISTOGRAM_4H": L1Engine._round_field(
                macd_4h,
                "histogram"
            ),
            "MACD_1D": L1Engine._round_field(
                macd_1d,
                "macd"
            ),
            "SIGNAL_1D": L1Engine._round_field(
                macd_1d,
                "signal"
            ),
            "HISTOGRAM_1D": L1Engine._round_field(
                macd_1d,
                "histogram"
            ),
            "PPO_1D": L1Engine._round_field(
                ppo,
                "ppo"
            ),
            "PPO_SIGNAL_1D": L1Engine._round_field(
                ppo,
                "signal"
            ),
            "PPO_HISTOGRAM_1D": L1Engine._round_field(
                ppo,
                "histogram"
            ),
            "PPO_STATE_1D": L1Engine._field(
                ppo,
                "state",
                "NOT_USED"
            ),
            "RSI_1D": L1Engine._round_field(
                rsi,
                "rsi"
            ),
            "RSI_STATE_1D": L1Engine._field(
                rsi,
                "state",
                "NOT_USED"
            ),
            "ADX_1D": L1Engine._round_field(
                adx,
                "adx"
            ),
            "DI_PLUS_1D": L1Engine._round_field(
                adx,
                "plus_di"
            ),
            "DI_MINUS_1D": L1Engine._round_field(
                adx,
                "minus_di"
            ),
            "ADX_DIRECTION_1D": L1Engine._field(
                adx,
                "direction",
                "NOT_USED"
            ),
            "ADX_STRENGTH_1D": L1Engine._field(
                adx,
                "strength",
                "NOT_USED"
            ),
            "OBV_1D": L1Engine._round_field(
                obv,
                "obv"
            ),
            "OBV_STATE_1D": L1Engine._field(
                obv,
                "state",
                "NOT_USED"
            ),
            "CMF_1D": L1Engine._round_field(
                cmf,
                "cmf"
            ),
            "CMF_STATE_1D": L1Engine._field(
                cmf,
                "state",
                "NOT_USED"
            ),
            "ATRP_1D": L1Engine._round_field(
                atrp,
                "atrp"
            ),
            "ATRP_RISK_1D": L1Engine._field(
                atrp,
                "risk",
                "NOT_USED"
            ),
            "High_52W": L1Engine._round_field(
                price_context,
                "high_52w"
            ),
            "Low_52W": L1Engine._round_field(
                price_context,
                "low_52w"
            ),
            "Distance_From_52W_High_Pct": L1Engine._round_field(
                price_context,
                "distance_from_52w_high_pct"
            ),
            "Distance_From_52W_Low_Pct": L1Engine._round_field(
                price_context,
                "distance_from_52w_low_pct"
            ),
            "Price_Context_State": L1Engine._field(
                price_context,
                "state",
                "NOT_COMPUTED"
            )
        }

        return row

    @staticmethod
    def build_setup_output_row(
        symbol: str,
        l1_result: L1Result,
        tactical_decision
    ) -> dict:

        computed_values = (
            tactical_decision.computed_values
            if tactical_decision
            else {}
        )

        price_ladder = computed_values.get(
            "PRICE_LADDER_CONTEXT"
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
        price_context = computed_values.get(
            "PRICE_CONTEXT"
        )

        row = {
            "Symbol": symbol,
            "Setup_Happens": (
                "YES"
                if tactical_decision.setup_happens
                else "NO"
            ),
            "Setup_State": tactical_decision.tactical_state,
            "Capital_Action": tactical_decision.capital_action,
            "Confidence": tactical_decision.confidence,
            "Setup_Score": tactical_decision.setup_score,
            "Rejection_Stage": tactical_decision.rejection_stage,
            "L1_State": l1_result.regime_state,
            "Primary_Reason": tactical_decision.message,
            "Latest_Price": round(
                l1_result.latest_price,
                4
            ),
            "Price_Ladder_State": L1Engine._field(
                price_ladder,
                "state"
            ),
            "Price_Lookback_X": L1Engine._field(
                price_ladder,
                "lookback_x"
            ),
            "P0_Close": L1Engine._round_field(
                price_ladder,
                "p0"
            ),
            "P1_Close": L1Engine._round_field(
                price_ladder,
                "p1"
            ),
            "PX_Close": L1Engine._round_field(
                price_ladder,
                "px"
            ),
            "PX_Advance_Pct": L1Engine._round_field(
                price_ladder,
                "advance_pct"
            ),
            "Higher_Close_Count": L1Engine._field(
                price_ladder,
                "higher_close_count"
            ),
            "MACD_1D_State": L1Engine._field(
                macd_1d,
                "state"
            ),
            "MACD_1D_Histogram": L1Engine._round_field(
                macd_1d,
                "histogram"
            ),
            "MACD_1D_Histogram_Slope": L1Engine._round_field(
                macd_1d,
                "histogram_slope"
            ),
            "MACD_1D_Rising_Streak": L1Engine._field(
                macd_1d,
                "histogram_rising_streak"
            ),
            "MACD_4H_State": L1Engine._field(
                macd_4h,
                "state"
            ),
            "MACD_4H_Histogram": L1Engine._round_field(
                macd_4h,
                "histogram"
            ),
            "MACD_4H_Histogram_Slope": L1Engine._round_field(
                macd_4h,
                "histogram_slope"
            ),
            "MACD_4H_Rising_Streak": L1Engine._field(
                macd_4h,
                "histogram_rising_streak"
            ),
            "MACD_1H_State": L1Engine._field(
                macd_1h,
                "state"
            ),
            "MACD_1H_Histogram": L1Engine._round_field(
                macd_1h,
                "histogram"
            ),
            "MACD_1H_Histogram_Slope": L1Engine._round_field(
                macd_1h,
                "histogram_slope"
            ),
            "MACD_1H_Rising_Streak": L1Engine._field(
                macd_1h,
                "histogram_rising_streak"
            ),
            "EMA200_Zone": L1Engine._field(
                ema200,
                "zone"
            ),
            "EMA200_D_Pct": L1Engine._round_field(
                ema200,
                "distance_pct"
            ),
            "EMA200_Slope_State": L1Engine._field(
                ema200,
                "slope_state"
            ),
            "RSI_1D": L1Engine._round_field(
                rsi,
                "rsi"
            ),
            "RSI_Headroom": L1Engine._round_field(
                rsi_headroom,
                "headroom"
            ),
            "RSI_Headroom_Pct": L1Engine._round_field(
                rsi_headroom,
                "headroom_pct"
            ),
            "RSI_Room_Score": L1Engine._field(
                rsi_headroom,
                "room_score"
            ),
            "ADX_Direction": L1Engine._field(
                adx,
                "direction"
            ),
            "ADX_Strength": L1Engine._field(
                adx,
                "strength"
            ),
            "OBV_State": L1Engine._field(
                obv,
                "state"
            ),
            "CMF_State": L1Engine._field(
                cmf,
                "state"
            ),
            "ATRP_Risk": L1Engine._field(
                atrp,
                "risk"
            ),
            "Session_State": L1Engine._field(
                session_context,
                "state"
            ),
            "Session_Change_Pct": L1Engine._round_field(
                session_context,
                "day_change_pct"
            ),
            "Gap_State": L1Engine._field(
                session_context,
                "gap_state"
            ),
            "Price_Context_State": L1Engine._field(
                price_context,
                "state"
            ),
            "Setup_Explanation": tactical_decision.message,
            "Final_State": tactical_decision.tactical_state
        }

        return row

    @staticmethod
    def build_baseline_record(
        symbol: str,
        l1_result: L1Result,
        tactical_decision
    ) -> dict:

        return {
            "symbol": symbol,
            "timestamp": datetime.now(UTC).isoformat(),
            "data_fetch_timestamp": l1_result.data_fetch_timestamp,
            "engine_mode": ENGINE_MODE,
            "latest_price": round(
                l1_result.latest_price,
                4
            ),
            "l1_state": l1_result.regime_state,
            "l1_reason": l1_result.reason,
            "tactical_state": tactical_decision.tactical_state,
            "confidence": tactical_decision.confidence,
            "capital_action": tactical_decision.capital_action,
            "message": tactical_decision.message,
            "indicators_used": "|".join(
                tactical_decision.indicators_used
            )
        }

    @staticmethod
    def _load_basic_snapshot(
        symbol: str
    ) -> BasicSnapshot:

        df_1d = DataLoader.load(
            symbol,
            "1d"
        )

        close = pd.to_numeric(
            df_1d["Close"],
            errors="coerce"
        ).dropna()

        if close.empty:

            raise ValueError(
                f"No close values available for {symbol}"
            )

        return BasicSnapshot(
            symbol=symbol,
            timestamp=datetime.now(UTC),
            latest_price=float(
                close.values[-1]
            ),
            source_timeframe="1d",
            data_fetch_timestamp=(
                DataLoader.get_fetch_timestamp(
                    symbol,
                    "1d"
                )
            )
        )

    @staticmethod
    def _safe_float(
        value
    ):

        try:

            return float(value)

        except (TypeError, ValueError):

            return None

    @staticmethod
    def _field(
        value,
        name,
        default=None
    ):

        if value is None:

            return default

        if isinstance(value, dict):

            return value.get(
                name,
                default
            )

        return getattr(
            value,
            name,
            default
        )

    @staticmethod
    def _round_field(
        value,
        name
    ):

        field_value = L1Engine._field(
            value,
            name
        )

        if field_value is None:

            return None

        return round(
            float(field_value),
            4
        )
