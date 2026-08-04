from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

from CONFIG.settings import (
    ADX_PERIOD,
    ATR_PERIOD,
    ATRP_HIGH_RISK_PCT,
    ATRP_MEDIUM_RISK_PCT,
    CMF_PERIOD,
    MARKET_CONTEXT_SYMBOLS,
    MACD_FAST,
    MACD_SIGNAL,
    MACD_SLOW,
    RELATED_INSTRUMENTS,
    RSI_PERIOD,
    SESSION_EXTENDED_MOVE_PCT,
    SESSION_GAP_MOVE_PCT,
    SETUP_PRICE_LOOKBACK_X,
    SETUP_PRICE_USE_COMPLETED_DAILY_CLOSE
)
from IO.data_loader import DataLoader
from LAYERS.L3.ema_engine import EMAEngine
from LAYERS.L3.macd_engine import MACDEngine
from MODELS.contracts import EMAResult, MACDResult


class L3ComputeLayer:

    @staticmethod
    def MACD(
        symbol: str,
        timeframe: str
    ) -> MACDResult:

        df = DataLoader.load(
            symbol,
            timeframe
        )

        return MACDEngine.calculate_macd(
            df,
            timeframe
        )

    @staticmethod
    def MACD_SUITE(
        symbol: str,
        timeframes: list[str]
    ) -> dict[str, MACDResult]:

        return {
            timeframe: L3ComputeLayer.MACD(
                symbol,
                timeframe
            )
            for timeframe in timeframes
        }

    @staticmethod
    def EMA200(
        symbol: str,
        timeframe: str = "1d"
    ) -> EMAResult:

        df = DataLoader.load(
            symbol,
            timeframe
        )

        return EMAEngine.get_ema200(
            df,
            timeframe
        )

    @staticmethod
    def PPO(
        symbol: str,
        timeframe: str = "1d"
    ) -> dict:

        df = DataLoader.load(
            symbol,
            timeframe
        )

        close = L3ComputeLayer._series(
            df,
            "Close"
        )

        ema_fast = close.ewm(
            span=MACD_FAST,
            adjust=False
        ).mean()

        ema_slow = close.ewm(
            span=MACD_SLOW,
            adjust=False
        ).mean()

        ppo = (
            (
                ema_fast -
                ema_slow
            ) / ema_slow
        ) * 100

        signal = ppo.ewm(
            span=MACD_SIGNAL,
            adjust=False
        ).mean()

        histogram = ppo - signal

        return {
            "timeframe": timeframe,
            "ppo": L3ComputeLayer._round(ppo.iloc[-1]),
            "signal": L3ComputeLayer._round(signal.iloc[-1]),
            "histogram": L3ComputeLayer._round(histogram.iloc[-1]),
            "histogram_slope": L3ComputeLayer._round(
                histogram.iloc[-1] -
                histogram.iloc[-2]
            ),
            "state": (
                "BULLISH"
                if ppo.iloc[-1] > signal.iloc[-1]
                else "BEARISH"
            )
        }

    @staticmethod
    def RSI(
        symbol: str,
        timeframe: str = "1d"
    ) -> dict:

        df = DataLoader.load(
            symbol,
            timeframe
        )

        close = L3ComputeLayer._series(
            df,
            "Close"
        )

        delta = close.diff()

        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)

        avg_gain = gain.ewm(
            alpha=1 / RSI_PERIOD,
            adjust=False
        ).mean()

        avg_loss = loss.ewm(
            alpha=1 / RSI_PERIOD,
            adjust=False
        ).mean()

        rs = avg_gain / avg_loss.replace(0, float("nan"))
        rsi = 100 - (100 / (1 + rs))
        rsi = rsi.fillna(100)

        latest_rsi = float(rsi.iloc[-1])

        state = "NEUTRAL"

        if latest_rsi >= 60:

            state = "BULLISH"

        elif latest_rsi < 40:

            state = "BEARISH"

        return {
            "timeframe": timeframe,
            "rsi": L3ComputeLayer._round(latest_rsi),
            "slope": L3ComputeLayer._round(
                rsi.iloc[-1] -
                rsi.iloc[-2]
            ),
            "state": state
        }

    @staticmethod
    def ADX_DMI(
        symbol: str,
        timeframe: str = "1d"
    ) -> dict:

        df = DataLoader.load(
            symbol,
            timeframe
        )

        high = L3ComputeLayer._series(df, "High")
        low = L3ComputeLayer._series(df, "Low")
        close = L3ComputeLayer._series(df, "Close")

        plus_dm_raw = high.diff()
        minus_dm_raw = -low.diff()

        plus_dm = plus_dm_raw.where(
            (plus_dm_raw > minus_dm_raw) &
            (plus_dm_raw > 0),
            0
        )

        minus_dm = minus_dm_raw.where(
            (minus_dm_raw > plus_dm_raw) &
            (minus_dm_raw > 0),
            0
        )

        atr = L3ComputeLayer._atr(
            high,
            low,
            close,
            ADX_PERIOD
        )

        plus_di = 100 * (
            plus_dm.ewm(
                alpha=1 / ADX_PERIOD,
                adjust=False
            ).mean() / atr.replace(0, float("nan"))
        )

        minus_di = 100 * (
            minus_dm.ewm(
                alpha=1 / ADX_PERIOD,
                adjust=False
            ).mean() / atr.replace(0, float("nan"))
        )

        dx = (
            (
                plus_di -
                minus_di
            ).abs() /
            (
                plus_di +
                minus_di
            ).replace(0, float("nan"))
        ) * 100

        adx = dx.ewm(
            alpha=1 / ADX_PERIOD,
            adjust=False
        ).mean()

        latest_adx = float(adx.iloc[-1])
        latest_plus_di = float(plus_di.iloc[-1])
        latest_minus_di = float(minus_di.iloc[-1])

        direction = (
            "BULLISH"
            if latest_plus_di > latest_minus_di
            else "BEARISH"
        )

        strength = (
            "STRONG"
            if latest_adx >= 25
            else "WEAK"
        )

        return {
            "timeframe": timeframe,
            "adx": L3ComputeLayer._round(latest_adx),
            "plus_di": L3ComputeLayer._round(latest_plus_di),
            "minus_di": L3ComputeLayer._round(latest_minus_di),
            "direction": direction,
            "strength": strength,
            "state": f"{direction}_{strength}"
        }

    @staticmethod
    def OBV(
        symbol: str,
        timeframe: str = "1d"
    ) -> dict:

        df = DataLoader.load(
            symbol,
            timeframe
        )

        close = L3ComputeLayer._series(df, "Close")
        volume = L3ComputeLayer._series(df, "Volume")

        direction = close.diff().apply(
            lambda value: 1
            if value > 0
            else -1
            if value < 0
            else 0
        )

        obv = (
            direction *
            volume
        ).fillna(0).cumsum()

        lookback = min(
            5,
            len(obv) - 1
        )

        slope = obv.iloc[-1] - obv.iloc[-lookback - 1]

        state = "NEUTRAL"

        if slope > 0:

            state = "ACCUMULATION"

        elif slope < 0:

            state = "DISTRIBUTION"

        return {
            "timeframe": timeframe,
            "obv": L3ComputeLayer._round(obv.iloc[-1]),
            "slope": L3ComputeLayer._round(slope),
            "state": state
        }

    @staticmethod
    def CMF(
        symbol: str,
        timeframe: str = "1d"
    ) -> dict:

        df = DataLoader.load(
            symbol,
            timeframe
        )

        high = L3ComputeLayer._series(df, "High")
        low = L3ComputeLayer._series(df, "Low")
        close = L3ComputeLayer._series(df, "Close")
        volume = L3ComputeLayer._series(df, "Volume")

        range_value = (
            high -
            low
        ).replace(0, float("nan"))

        multiplier = (
            (
                close -
                low
            ) -
            (
                high -
                close
            )
        ) / range_value

        money_flow_volume = multiplier.fillna(0) * volume

        cmf = (
            money_flow_volume
            .rolling(CMF_PERIOD)
            .sum() /
            volume
            .rolling(CMF_PERIOD)
            .sum()
            .replace(0, float("nan"))
        )

        latest_cmf = float(cmf.iloc[-1])

        state = "NEUTRAL"

        if latest_cmf > 0.05:

            state = "ACCUMULATION"

        elif latest_cmf < -0.05:

            state = "DISTRIBUTION"

        return {
            "timeframe": timeframe,
            "cmf": L3ComputeLayer._round(latest_cmf),
            "state": state
        }

    @staticmethod
    def ATRP(
        symbol: str,
        timeframe: str = "1d"
    ) -> dict:

        df = DataLoader.load(
            symbol,
            timeframe
        )

        high = L3ComputeLayer._series(df, "High")
        low = L3ComputeLayer._series(df, "Low")
        close = L3ComputeLayer._series(df, "Close")

        atr = L3ComputeLayer._atr(
            high,
            low,
            close,
            ATR_PERIOD
        )

        atrp = (
            atr /
            close
        ) * 100

        latest_atrp = float(atrp.iloc[-1])

        risk = "LOW"

        if latest_atrp >= ATRP_HIGH_RISK_PCT:

            risk = "HIGH"

        elif latest_atrp >= ATRP_MEDIUM_RISK_PCT:

            risk = "MEDIUM"

        return {
            "timeframe": timeframe,
            "atrp": L3ComputeLayer._round(latest_atrp),
            "risk": risk,
            "state": risk
        }

    @staticmethod
    def PRICE_CONTEXT(
        symbol: str,
        timeframe: str = "1d"
    ) -> dict:

        df = DataLoader.load(
            symbol,
            timeframe
        )

        recent_df = df.tail(252)

        close = L3ComputeLayer._series(recent_df, "Close")
        high = L3ComputeLayer._series(recent_df, "High")
        low = L3ComputeLayer._series(recent_df, "Low")

        latest_close = float(close.iloc[-1])
        high_52w = float(high.max())
        low_52w = float(low.min())

        return {
            "timeframe": timeframe,
            "latest_price": L3ComputeLayer._round(latest_close),
            "high_52w": L3ComputeLayer._round(high_52w),
            "low_52w": L3ComputeLayer._round(low_52w),
            "distance_from_52w_high_pct": L3ComputeLayer._round(
                (
                    (
                        latest_close -
                        high_52w
                    ) / high_52w
                ) * 100
            ),
            "distance_from_52w_low_pct": L3ComputeLayer._round(
                (
                    (
                        latest_close -
                        low_52w
                    ) / low_52w
                ) * 100
            ),
            "state": (
                "NEAR_HIGH"
                if latest_close >= high_52w * 0.95
                else "NEAR_LOW"
                if latest_close <= low_52w * 1.10
                else "MID_RANGE"
            )
        }

    @staticmethod
    def PRICE_LADDER_CONTEXT(
        symbol: str,
        timeframe: str = "1d",
        lookback_x: int | None = None,
        use_completed_daily_close: bool | None = None
    ) -> dict:

        lookback_x = (
            SETUP_PRICE_LOOKBACK_X
            if lookback_x is None
            else lookback_x
        )

        use_completed_daily_close = (
            SETUP_PRICE_USE_COMPLETED_DAILY_CLOSE
            if use_completed_daily_close is None
            else use_completed_daily_close
        )

        df = DataLoader.load(
            symbol,
            timeframe,
            use_live_price=not use_completed_daily_close
        )

        if use_completed_daily_close and timeframe == "1d":

            df = L3ComputeLayer._drop_open_daily_session(
                df
            )

        close = L3ComputeLayer._series(
            df,
            "Close"
        )

        required_points = lookback_x + 1

        if len(close) < required_points:

            raise ValueError(
                "Price ladder requires at least "
                f"{required_points} completed closes; "
                f"{len(close)} available"
            )

        p0 = float(close.iloc[-1])
        p1 = float(close.iloc[-2])
        px = float(close.iloc[-lookback_x - 1])

        advance_pct = (
            (
                p0 -
                px
            ) / px
        ) * 100

        recent_diffs = (
            close
            .tail(required_points)
            .diff()
            .dropna()
        )

        higher_close_count = int(
            (
                recent_diffs > 0
            ).sum()
        )

        lower_close_count = int(
            (
                recent_diffs < 0
            ).sum()
        )

        state = "FLAT"

        if p0 > p1 and p0 > px:

            state = "ADVANCING"

        elif p0 < p1 and p0 < px:

            state = "DECLINING"

        return {
            "timeframe": timeframe,
            "lookback_x": lookback_x,
            "uses_completed_daily_close": use_completed_daily_close,
            "p0": L3ComputeLayer._round(p0),
            "p1": L3ComputeLayer._round(p1),
            "px": L3ComputeLayer._round(px),
            "advance_pct": L3ComputeLayer._round(
                advance_pct
            ),
            "p0_gt_p1": p0 > p1,
            "p0_gt_px": p0 > px,
            "higher_close_count": higher_close_count,
            "lower_close_count": lower_close_count,
            "state": state
        }

    @staticmethod
    def SESSION_CONTEXT(
        symbol: str,
        timeframe: str = "1d"
    ) -> dict:

        df = DataLoader.load(
            symbol,
            timeframe
        )

        if len(df) < 2:

            raise ValueError(
                "Session context requires at least two daily rows"
            )

        close = L3ComputeLayer._series(df, "Close")
        open_price = L3ComputeLayer._series(df, "Open")

        latest_price = float(
            close.iloc[-1]
        )

        previous_close = float(
            close.iloc[-2]
        )

        latest_open = float(
            open_price.iloc[-1]
        )

        day_change_pct = (
            (
                latest_price -
                previous_close
            ) / previous_close
        ) * 100

        opening_gap_pct = (
            (
                latest_open -
                previous_close
            ) / previous_close
        ) * 100

        intraday_change_pct = (
            (
                latest_price -
                latest_open
            ) / latest_open
        ) * 100

        session_state = "NORMAL"

        if day_change_pct >= SESSION_EXTENDED_MOVE_PCT:

            session_state = "EXTENDED_UP"

        elif day_change_pct <= -SESSION_EXTENDED_MOVE_PCT:

            session_state = "EXTENDED_DOWN"

        gap_state = "NO_GAP"

        if opening_gap_pct >= SESSION_GAP_MOVE_PCT:

            gap_state = "GAP_UP"

        elif opening_gap_pct <= -SESSION_GAP_MOVE_PCT:

            gap_state = "GAP_DOWN"

        return {
            "timeframe": timeframe,
            "latest_price": L3ComputeLayer._round(
                latest_price
            ),
            "previous_close": L3ComputeLayer._round(
                previous_close
            ),
            "open_price": L3ComputeLayer._round(
                latest_open
            ),
            "day_change_pct": L3ComputeLayer._round(
                day_change_pct
            ),
            "opening_gap_pct": L3ComputeLayer._round(
                opening_gap_pct
            ),
            "intraday_change_pct": L3ComputeLayer._round(
                intraday_change_pct
            ),
            "state": session_state,
            "gap_state": gap_state
        }

    @staticmethod
    def MARKET_CONTEXT(
        symbol: str,
        timeframe: str = "1d"
    ) -> dict:

        return L3ComputeLayer._context_suite(
            MARKET_CONTEXT_SYMBOLS,
            timeframe
        )

    @staticmethod
    def RELATED_INSTRUMENT_CONTEXT(
        symbol: str,
        timeframe: str = "1d"
    ) -> dict:

        related_symbols = RELATED_INSTRUMENTS.get(
            symbol.upper(),
            []
        )

        return L3ComputeLayer._context_suite(
            related_symbols,
            timeframe
        )

    @staticmethod
    def _context_suite(
        symbols: list[str],
        timeframe: str
    ) -> dict:

        context = {}

        for context_symbol in symbols:

            try:

                df = DataLoader.load(
                    context_symbol,
                    timeframe
                )

                close = L3ComputeLayer._series(
                    df,
                    "Close"
                )

                context[context_symbol] = {
                    "latest_price": L3ComputeLayer._round(
                        close.iloc[-1]
                    ),
                    "day_change_pct": L3ComputeLayer._round(
                        (
                            (
                                close.iloc[-1] -
                                close.iloc[-2]
                            ) / close.iloc[-2]
                        ) * 100
                    ),
                    "macd_state": L3ComputeLayer.MACD(
                        context_symbol,
                        timeframe
                    ).state
                }

            except Exception as error:

                context[context_symbol] = {
                    "error": str(error)
                }

        return context

    @staticmethod
    def _series(
        df: pd.DataFrame,
        column: str
    ) -> pd.Series:

        series = pd.to_numeric(
            df[column],
            errors="coerce"
        ).dropna()

        if len(series) < 2:

            raise ValueError(
                f"{column} requires at least two values"
            )

        return series

    @staticmethod
    def _atr(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int
    ) -> pd.Series:

        previous_close = close.shift(1)

        true_range = pd.concat(
            [
                high - low,
                (
                    high -
                    previous_close
                ).abs(),
                (
                    low -
                    previous_close
                ).abs()
            ],
            axis=1
        ).max(axis=1)

        return true_range.ewm(
            alpha=1 / period,
            adjust=False
        ).mean()

    @staticmethod
    def _round(
        value,
        digits: int = 4
    ):

        if pd.isna(value):

            return None

        return round(
            float(value),
            digits
        )

    @staticmethod
    def _drop_open_daily_session(
        df: pd.DataFrame
    ) -> pd.DataFrame:

        if df.empty:

            return df

        latest_index = pd.Timestamp(
            df.index[-1]
        )

        latest_date = latest_index.date()

        now_ny = datetime.now(
            ZoneInfo("America/New_York")
        )

        market_close_buffer = now_ny.replace(
            hour=16,
            minute=10,
            second=0,
            microsecond=0
        )

        if (
            latest_date == now_ny.date()
            and
            now_ny < market_close_buffer
        ):

            return df.iloc[:-1]

        return df
