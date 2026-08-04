from pathlib import Path

import pandas as pd

from IO.data_loader import DataLoader

from LAYERS.L3.macd_engine import (
    MACDEngine
)

from LAYERS.L3.ema_engine import (
    EMAEngine
)

from LAYERS.L1.l1_engine import (
    L1Engine
)

from LAYERS.L2.l2_orchestrator import (
    L2Orchestrator
)

from CORE.baseline_registry import (
    BaselineRegistry
)

from OUTPUT.execution_reporter import (
    ExecutionReporter
)


OUTPUT_FILE = (
    "STORAGE/ACTIVE_BASELINE.csv"
)

ENGINE_NAME = (
    "PMDE vNext"
)

VERSION = (
    "V_NEXT"
)

RUN_MODE = (
    "ADHOC_LIVE_VALIDATION"
)

INPUT_FILE = (
    "D:/Tools/StockCodeMaster/01_nasdaq_EnergyCodes.csv"
#    "INPUT/symbols.csv"
)


#
# SYMBOL LOADER
#

def load_symbols():

    df = pd.read_csv(
        INPUT_FILE
    )

    first_column = df.columns[0]

    symbols = (

        df[first_column]

        .dropna()

        .astype(str)

        .str.strip()

        .str.upper()
    )

    symbols = list(
        dict.fromkeys(symbols)
    )

    return symbols


#
# BUILD OUTPUT ROW
#

def build_output_row(

    symbol,

    ema_result,

    l1_result,

    tactical,

    macd_suite

):

    macd_1d = macd_suite["1d"]

    macd_4h = macd_suite["4h"]

    macd_1h = macd_suite["1h"]

    zone = (

        "BULL_ZONE"

        if ema_result[
            "distance_pct"
        ] > 0

        else "BEAR_ZONE"
    )

    row = {

        "Symbol":
            symbol,

        "Zone":
            zone,

        "L1_State":
            l1_result.regime_state,

        "L2_Hypothesis":
            tactical["state"],

        "L2_MACD":
            macd_4h["state"],

        "L3_Substantiation":
            tactical["message"],

        "Final_State":
            tactical["state"],

        "Momentum_State":
            macd_1d["state"],

        "Participation_State":
            "NOT_USED",

        "Trend_Strength_State":
            "ACTIVE",

        "Exhaustion_State":
            "NEUTRAL",

        "Volatility_State":
            "NORMAL",

        "EMA200":
            round(
                ema_result["ema200"],
                2
            ),

        "EMA200_D_Pct":
            round(
                ema_result[
                    "distance_pct"
                ],
                2
            ),

        #
        # 1H
        #

        "MACD_1H":
            macd_1h["macd"],

        "SIGNAL_1H":
            macd_1h["signal"],

        "HISTOGRAM_1H":
            macd_1h["histogram"],

        #
        # 4H
        #

        "MACD_4H":
            macd_4h["macd"],

        "SIGNAL_4H":
            macd_4h["signal"],

        "HISTOGRAM_4H":
            macd_4h["histogram"],

        #
        # 1D
        #

        "MACD_1D":
            macd_1d["macd"],

        "SIGNAL_1D":
            macd_1d["signal"],

        "HISTOGRAM_1D":
            macd_1d["histogram"],

        #
        # EXPLANATION
        #

        "PMDE_Explanation":

            f"Zone={zone}; "

            f"L1={l1_result.regime_state}; "

            f"L2={tactical['state']}"
    }

    return row


#
# MAIN
#

def main():

    BaselineRegistry.validate_output_location()

    symbols = load_symbols()

    reporter = ExecutionReporter(

        output_file=OUTPUT_FILE,

        engine_name=ENGINE_NAME,

        version=VERSION,

        run_mode=RUN_MODE,

        input_file=INPUT_FILE
    )

    print("")
    print("=" * 70)
    print(
        "PMDE EXECUTION STARTED"
    )
    print("=" * 70)
    print("")

    for symbol in symbols:

        try:

            print(
                f"Processing {symbol}"
            )

            #
            # DATA
            #

            df_1d = DataLoader.load(
                symbol,
                "1d"
            )

            #
            # EMA
            #

            ema_result = (
                EMAEngine.get_ema200(
                    df_1d
                )
            )

            #
            # MACD SUITE
            #

            macd_suite = (
                MACDEngine
                .get_macd_suite(
                    symbol
                )
            )

            #
            # L1
            #

            l1_result = (
                L1Engine.evaluate(

                    macd_suite["1d"][
                        "histogram_slope"
                    ]
                )
            )

            #
            # L2
            #

            tactical = (
                L2Orchestrator.process(

                    symbol,
                    macd_suite
                )
            )

            #
            # BUILD ROW
            #

            row = build_output_row(

                symbol,

                ema_result,

                l1_result,

                tactical,

                macd_suite
            )

            reporter.record_success(
                row
            )

        except Exception:

            reporter.record_failure(
                symbol
            )

    #
    # FINALIZE OUTPUT
    #

    reporter.finalize(
        total_symbols=len(symbols)
    )


if __name__ == "__main__":
    main()