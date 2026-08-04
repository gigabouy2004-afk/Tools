from pathlib import Path

import CONFIG.settings as runtime_settings


PROJECT_ROOT = Path(__file__).resolve().parent

ENGINE_MODE_FULL_BASELINE = "FULL_BASELINE"
ENGINE_MODE_QUICK_CROSSOVER = "QUICK_CROSSOVER"
ENGINE_MODE_QUICK_SETUP = "QUICK_SETUP"

SUPPORTED_ENGINE_MODES = [
    ENGINE_MODE_FULL_BASELINE,
    ENGINE_MODE_QUICK_CROSSOVER,
    ENGINE_MODE_QUICK_SETUP
]

# ======================================================================
# USER RUN SWITCHES - EDIT THIS BLOCK FOR NORMAL RUNS
# ======================================================================

#ENGINE_MODE = ENGINE_MODE_QUICK_SETUP
ENGINE_MODE =  ENGINE_MODE_QUICK_CROSSOVER


# Quick setup now runs this ad-hoc list by default. Use one symbol per
# list item; comma-separated strings are also accepted defensively.
HARDCODED_SYMBOLS = [
    "UMAC",
    "NNE",
    "RDW",
    "RKLB"
]

INPUT_FILE = "D:/Tools/StockCodeMaster/USA/00-NYSE_NASDAQ_Common_Stocks_Sector-Technology-Semiconductor.csv"
REPORT_OUTPUT_FILE = "Output_00-NYSE_NASDAQ_Common_Stocks_Sector-Technology.csv"

INPUT_SYMBOL_COLUMN = None
INPUT_EXCHANGE_COLUMN = None
DEFAULT_EXCHANGE = None
FALLBACK_SYMBOLS = []
SORT_UNIQUE_SYMBOLS = False

# Quick setup source switches. The CSV input file is intentionally off
# for quick setup so ad-hoc runs do not expand into the whole sector file.
QUICK_SETUP_INCLUDE_INPUT_FILE = False
QUICK_SETUP_INCLUDE_BASELINE_SYMBOLS = False

# False means the quick setup report keeps every assessed symbol, including
# rejected/wait states, so the rejection reason is visible.
SETUP_OUTPUT_ONLY_CONFIRMED = False

# ======================================================================
# ADVANCED ENGINE CONSTANTS - DO NOT EDIT FOR NORMAL RUNS
# ======================================================================

MACD_FAST = 8
MACD_SLOW = 21
MACD_SIGNAL = 5

EMA_PERIOD = 200
EMA_SLOPE_LOOKBACK = 20

RSI_PERIOD = 14
ADX_PERIOD = 14
CMF_PERIOD = 20
ATR_PERIOD = 14

ATRP_MEDIUM_RISK_PCT = 3.0
ATRP_HIGH_RISK_PCT = 5.0

SESSION_EXTENDED_MOVE_PCT = 5.0
SESSION_GAP_MOVE_PCT = 3.0

DEFAULT_LOOKBACK = "1y"

SETUP_PRICE_LOOKBACK_X = 5
SETUP_PRICE_MIN_ADVANCE_PCT = 0.5
SETUP_PRICE_USE_COMPLETED_DAILY_CLOSE = True

SETUP_PRIMARY_TIMEFRAME = "1d"
SETUP_BRIDGE_TIMEFRAME = "4h"
SETUP_TRIGGER_TIMEFRAME = "1h"
SETUP_MACD_HISTOGRAM_RISING_STREAK = 2

SETUP_REQUIRE_EMA200_BULL_ZONE = True
SETUP_REJECT_EXTENDED_UP = True
SETUP_REJECT_GAP_UP = False
SETUP_REJECT_HIGH_ATRP = False
SETUP_RSI_MIN = 45
SETUP_RSI_MAX = 78
SETUP_RSI_HEADROOM_FULL_SCORE_PCT = 35
SETUP_RSI_HEADROOM_MIN_SCORE_PCT = 10

USE_LIVE_PRICE_FOR_DAILY = True
LIVE_PRICE_INTERVAL = "1m"
LIVE_PRICE_PERIOD = "1d"
LIVE_PRICE_PREPOST = False

DATA_INTERVALS = {
    "1h": "1h",
    "4h": "1h",
    "1d": "1d",
    "1w": "1wk"
}

DATA_PERIODS = {
    "1h": "30d",
    "4h": "60d",
    "1d": "5y",
    "1w": "5y"
}

BASELINE_FILE = str(
    PROJECT_ROOT /
    "STORAGE" /
    "ACTIVE_BASELINE.csv"
)

EXECUTION_REPORT_FILES = {
    ENGINE_MODE_FULL_BASELINE: str(
        PROJECT_ROOT /
        "OUTPUT" /
        "PMDE_EXECUTION_FULL_BASELINE_REPORT.csv"
    ),
    ENGINE_MODE_QUICK_CROSSOVER: str(
        PROJECT_ROOT /
        "OUTPUT" /
        "PMDE_EXECUTION_QUICK_CROSSOVER_REPORT.csv"
    ),
    ENGINE_MODE_QUICK_SETUP: str(
        PROJECT_ROOT /
        "OUTPUT" /
        "PMDE_EXECUTION_QUICK_SETUP_REPORT.csv"
    )
}

EXECUTION_REPORT_FILE = (
    REPORT_OUTPUT_FILE
    or
    EXECUTION_REPORT_FILES.get(
        ENGINE_MODE,
        EXECUTION_REPORT_FILES[ENGINE_MODE_FULL_BASELINE]
    )
)

FORCE_L2_ASSESSMENT = True
L1_PRICE_CHANGE_TRIGGER_PCT = 0.0

QUICK_CROSSOVER_OUTPUT_ONLY_PROBABLES = True
QUICK_CROSSOVER_STATES = [
    "PRE_BULL_CROSSOVER",
    "PRE_BEAR_CROSSOVER",
    "EARLY_RECOVERY_INSIDE_BEAR_STRUCTURE"
]
QUICK_CROSSOVER_BASELINE_STATES = [
    "PRE_BULL_CROSSOVER",
    "PRE_BEAR_CROSSOVER"
]
QUICK_CROSSOVER_INCLUDE_BASELINE_WATCHLIST = True
QUICK_CROSSOVER_INCLUDE_INPUT_SYMBOLS = True
QUICK_CROSSOVER_UPDATE_BASELINE = True

ACTIVE_GENERIC_FACTS = [
    "EMA200",
    "PRICE_CONTEXT",
    "SESSION_CONTEXT"
]

ACTIVE_INDICATORS = [
    "MACD",
    "PPO",
    "RSI",
    "ADX_DMI",
    "OBV",
    "CMF",
    "ATRP"
]

ACTIVE_CONTEXTS = []

MACD_TIMEFRAMES = [
    "1h",
    "4h",
    "1d"
]

PRIMARY_TECH_TIMEFRAME = "1d"

MARKET_CONTEXT_SYMBOLS = [
    "SPY",
    "QQQ",
    "^NSEI"
]

RELATED_INSTRUMENTS = {
    "AMD": [
        "AMDL",
        "ADMY",
        "AMDU",
        "AMDS"
    ]
}


def apply_runtime_settings():

    runtime_names = [
        "ACTIVE_CONTEXTS",
        "ACTIVE_GENERIC_FACTS",
        "ACTIVE_INDICATORS",
        "ADX_PERIOD",
        "ATR_PERIOD",
        "ATRP_HIGH_RISK_PCT",
        "ATRP_MEDIUM_RISK_PCT",
        "BASELINE_FILE",
        "CMF_PERIOD",
        "DATA_INTERVALS",
        "DATA_PERIODS",
        "DEFAULT_EXCHANGE",
        "DEFAULT_LOOKBACK",
        "EMA_PERIOD",
        "EMA_SLOPE_LOOKBACK",
        "ENGINE_MODE",
        "ENGINE_MODE_FULL_BASELINE",
        "ENGINE_MODE_QUICK_CROSSOVER",
        "ENGINE_MODE_QUICK_SETUP",
        "EXECUTION_REPORT_FILE",
        "EXECUTION_REPORT_FILES",
        "FALLBACK_SYMBOLS",
        "FORCE_L2_ASSESSMENT",
        "HARDCODED_SYMBOLS",
        "INPUT_EXCHANGE_COLUMN",
        "INPUT_FILE",
        "INPUT_SYMBOL_COLUMN",
        "L1_PRICE_CHANGE_TRIGGER_PCT",
        "LIVE_PRICE_INTERVAL",
        "LIVE_PRICE_PERIOD",
        "LIVE_PRICE_PREPOST",
        "MACD_FAST",
        "MACD_SIGNAL",
        "MACD_SLOW",
        "MACD_TIMEFRAMES",
        "MARKET_CONTEXT_SYMBOLS",
        "PRIMARY_TECH_TIMEFRAME",
        "PROJECT_ROOT",
        "QUICK_CROSSOVER_BASELINE_STATES",
        "QUICK_CROSSOVER_INCLUDE_BASELINE_WATCHLIST",
        "QUICK_CROSSOVER_INCLUDE_INPUT_SYMBOLS",
        "QUICK_CROSSOVER_OUTPUT_ONLY_PROBABLES",
        "QUICK_CROSSOVER_STATES",
        "QUICK_CROSSOVER_UPDATE_BASELINE",
        "QUICK_SETUP_INCLUDE_BASELINE_SYMBOLS",
        "QUICK_SETUP_INCLUDE_INPUT_FILE",
        "RELATED_INSTRUMENTS",
        "RSI_PERIOD",
        "SESSION_EXTENDED_MOVE_PCT",
        "SESSION_GAP_MOVE_PCT",
        "SETUP_BRIDGE_TIMEFRAME",
        "SETUP_MACD_HISTOGRAM_RISING_STREAK",
        "SETUP_OUTPUT_ONLY_CONFIRMED",
        "SETUP_PRICE_LOOKBACK_X",
        "SETUP_PRICE_MIN_ADVANCE_PCT",
        "SETUP_PRICE_USE_COMPLETED_DAILY_CLOSE",
        "SETUP_PRIMARY_TIMEFRAME",
        "SETUP_REJECT_EXTENDED_UP",
        "SETUP_REJECT_GAP_UP",
        "SETUP_REJECT_HIGH_ATRP",
        "SETUP_REQUIRE_EMA200_BULL_ZONE",
        "SETUP_RSI_HEADROOM_FULL_SCORE_PCT",
        "SETUP_RSI_HEADROOM_MIN_SCORE_PCT",
        "SETUP_RSI_MAX",
        "SETUP_RSI_MIN",
        "SETUP_TRIGGER_TIMEFRAME",
        "SORT_UNIQUE_SYMBOLS",
        "SUPPORTED_ENGINE_MODES",
        "USE_LIVE_PRICE_FOR_DAILY"
    ]

    for name in runtime_names:

        setattr(
            runtime_settings,
            name,
            globals()[name]
        )


apply_runtime_settings()

from CORE.baseline_registry import BaselineRegistry
from IO.symbol_loader import SymbolLoader
from LAYERS.L1.l1_engine import L1Engine
from OUTPUT.execution_reporter import ExecutionReporter


OUTPUT_FILE = EXECUTION_REPORT_FILE

ENGINE_NAME = "PMDE vNext"

VERSION = "V_NEXT"

RUN_MODE = ENGINE_MODE


def validate_engine_mode():

    if ENGINE_MODE not in SUPPORTED_ENGINE_MODES:

        raise RuntimeError(
            "Unsupported ENGINE_MODE "
            f"'{ENGINE_MODE}'. Supported modes: "
            f"{', '.join(SUPPORTED_ENGINE_MODES)}"
        )


def load_symbols():

    baseline_symbols = []
    baseline_watch_symbols = []
    baseline_watch_count = 0
    load_warnings = []

    should_load_baseline = (
        ENGINE_MODE == ENGINE_MODE_QUICK_CROSSOVER
        or
        (
            ENGINE_MODE == ENGINE_MODE_QUICK_SETUP
            and
            QUICK_SETUP_INCLUDE_BASELINE_SYMBOLS
        )
    )

    if should_load_baseline:

        try:

            baseline_df = BaselineRegistry.load()

            if not baseline_df.empty and "symbol" in baseline_df.columns:

                baseline_symbols = SymbolLoader.normalize_list(
                    baseline_df["symbol"].dropna().tolist(),
                    default_exchange=DEFAULT_EXCHANGE,
                    sort_unique=SORT_UNIQUE_SYMBOLS
                )

                if "tactical_state" in baseline_df.columns:

                    watch_df = baseline_df[
                        baseline_df["tactical_state"]
                        .astype(str)
                        .isin(QUICK_CROSSOVER_BASELINE_STATES)
                    ]

                    baseline_watch_symbols = SymbolLoader.normalize_list(
                        watch_df["symbol"].dropna().tolist(),
                        default_exchange=DEFAULT_EXCHANGE,
                        sort_unique=SORT_UNIQUE_SYMBOLS
                    )

                    baseline_watch_count = len(
                        baseline_watch_symbols
                    )

        except Exception as error:

            load_warnings.append(
                f"BASELINE_SOURCE_ERROR: {error}"
            )

    file_symbols = []

    should_load_input_file = (
        bool(INPUT_FILE)
        and
        (
            ENGINE_MODE != ENGINE_MODE_QUICK_SETUP
            or
            QUICK_SETUP_INCLUDE_INPUT_FILE
        )
    )

    if should_load_input_file:

        try:

            file_symbols = SymbolLoader.load(
                input_file=INPUT_FILE,
                symbol_column=INPUT_SYMBOL_COLUMN,
                exchange_column=INPUT_EXCHANGE_COLUMN,
                default_exchange=DEFAULT_EXCHANGE,
                fallback_symbols=[],
                sort_unique=SORT_UNIQUE_SYMBOLS
            )

        except Exception as error:

            load_warnings.append(
                f"FILE_SOURCE_ERROR: {error}"
            )

    elif INPUT_FILE and ENGINE_MODE == ENGINE_MODE_QUICK_SETUP:

        load_warnings.append(
            "INPUT_FILE_SKIPPED_FOR_QUICK_SETUP"
        )

    hardcoded_symbols = SymbolLoader.normalize_list(
        HARDCODED_SYMBOLS,
        default_exchange=DEFAULT_EXCHANGE,
        sort_unique=SORT_UNIQUE_SYMBOLS
    )

    fallback_symbols = SymbolLoader.normalize_list(
        FALLBACK_SYMBOLS,
        default_exchange=DEFAULT_EXCHANGE,
        sort_unique=SORT_UNIQUE_SYMBOLS
    )

    configured_input_symbols = SymbolLoader.merge_sources(
        [
            file_symbols,
            hardcoded_symbols,
            fallback_symbols
        ],
        sort_unique=SORT_UNIQUE_SYMBOLS
    )

    input_symbol_count = len(configured_input_symbols)
    resolved_symbol_source = "INPUT_SOURCES"
    symbols = configured_input_symbols

    if ENGINE_MODE == ENGINE_MODE_QUICK_SETUP:

        setup_sources = []
        setup_source_labels = []

        if hardcoded_symbols:

            setup_sources.append(
                hardcoded_symbols
            )
            setup_source_labels.append("ADHOC_SYMBOLS")

        if fallback_symbols:

            setup_sources.append(
                fallback_symbols
            )
            setup_source_labels.append("FALLBACK_SYMBOLS")

        if QUICK_SETUP_INCLUDE_INPUT_FILE and file_symbols:

            setup_sources.append(
                file_symbols
            )
            setup_source_labels.append("INPUT_FILE")

        if QUICK_SETUP_INCLUDE_BASELINE_SYMBOLS and baseline_symbols:

            setup_sources.append(
                baseline_symbols
            )
            setup_source_labels.append("BASELINE")

        symbols = SymbolLoader.merge_sources(
            setup_sources,
            sort_unique=SORT_UNIQUE_SYMBOLS
        )

        resolved_symbol_source = (
            "+".join(setup_source_labels)
            if setup_source_labels
            else "NONE"
        )

    if ENGINE_MODE == ENGINE_MODE_QUICK_CROSSOVER:

        crossover_sources = []

        if QUICK_CROSSOVER_INCLUDE_BASELINE_WATCHLIST:

            crossover_sources.append(
                baseline_watch_symbols
            )

        if QUICK_CROSSOVER_INCLUDE_INPUT_SYMBOLS:

            crossover_sources.append(
                configured_input_symbols
            )

        symbols = SymbolLoader.merge_sources(
            crossover_sources,
            sort_unique=SORT_UNIQUE_SYMBOLS
        )

        if (
            baseline_watch_symbols
            and
            input_symbol_count
        ):

            resolved_symbol_source = (
                "BASELINE_WATCHLIST_PLUS_INPUT"
            )

        elif baseline_watch_symbols:

            resolved_symbol_source = "BASELINE_WATCHLIST"

        elif input_symbol_count:

            resolved_symbol_source = "INPUT_SOURCES"

        else:

            resolved_symbol_source = "NONE"

    if not symbols:

        warning_text = (
            " ".join(load_warnings)
            if load_warnings
            else (
                f"No symbols available for {ENGINE_MODE}."
            )
        )

        raise RuntimeError(
            f"No symbols available for processing. {warning_text}"
        )

    return {
        "symbols": symbols,
        "file_count": len(file_symbols),
        "hardcoded_count": len(hardcoded_symbols),
        "fallback_count": len(fallback_symbols),
        "baseline_count": len(baseline_symbols),
        "baseline_watch_count": baseline_watch_count,
        "input_symbol_count": input_symbol_count,
        "resolved_symbol_source": resolved_symbol_source,
        "warnings": load_warnings
    }


def format_symbol_preview(
    symbols,
    limit=30
):

    if len(symbols) <= limit:

        return ", ".join(symbols)

    visible_symbols = ", ".join(
        symbols[:limit]
    )

    return (
        f"{visible_symbols}, ... "
        f"({len(symbols)} total)"
    )


def main():

    BaselineRegistry.validate_output_location()

    try:

        validate_engine_mode()

        symbol_load = load_symbols()

    except Exception as error:

        reporter = ExecutionReporter(
            output_file=OUTPUT_FILE,
            engine_name=ENGINE_NAME,
            version=VERSION,
            run_mode=RUN_MODE,
            input_file=INPUT_FILE,
            metadata={
                "INPUT_FILE": INPUT_FILE,
                "HARDCODED_SYMBOLS": "|".join(HARDCODED_SYMBOLS),
                "FALLBACK_SYMBOLS": "|".join(FALLBACK_SYMBOLS),
                "ENGINE_MODE": ENGINE_MODE,
                "QUICK_SETUP_INCLUDE_INPUT_FILE": (
                    QUICK_SETUP_INCLUDE_INPUT_FILE
                ),
                "QUICK_SETUP_INCLUDE_BASELINE_SYMBOLS": (
                    QUICK_SETUP_INCLUDE_BASELINE_SYMBOLS
                ),
                "SETUP_OUTPUT_ONLY_CONFIRMED": (
                    SETUP_OUTPUT_ONLY_CONFIRMED
                ),
                "SUPPORTED_ENGINE_MODES": "|".join(
                    SUPPORTED_ENGINE_MODES
                ),
                "FORCE_L2_ASSESSMENT": FORCE_L2_ASSESSMENT,
                "MACD_FAST": MACD_FAST,
                "MACD_SLOW": MACD_SLOW,
                "MACD_SIGNAL": MACD_SIGNAL,
                "SETUP_PRICE_LOOKBACK_X": SETUP_PRICE_LOOKBACK_X,
                "SETUP_PRICE_MIN_ADVANCE_PCT": SETUP_PRICE_MIN_ADVANCE_PCT,
                "SETUP_PRIMARY_TIMEFRAME": SETUP_PRIMARY_TIMEFRAME,
                "SETUP_BRIDGE_TIMEFRAME": SETUP_BRIDGE_TIMEFRAME,
                "SETUP_TRIGGER_TIMEFRAME": SETUP_TRIGGER_TIMEFRAME,
                "SETUP_MACD_HISTOGRAM_RISING_STREAK": (
                    SETUP_MACD_HISTOGRAM_RISING_STREAK
                ),
                "SETUP_RSI_HEADROOM_FULL_SCORE_PCT": (
                    SETUP_RSI_HEADROOM_FULL_SCORE_PCT
                ),
                "SETUP_RSI_HEADROOM_MIN_SCORE_PCT": (
                    SETUP_RSI_HEADROOM_MIN_SCORE_PCT
                ),
                "QUICK_CROSSOVER_OUTPUT_ONLY_PROBABLES": (
                    QUICK_CROSSOVER_OUTPUT_ONLY_PROBABLES
                ),
                "QUICK_CROSSOVER_INCLUDE_BASELINE_WATCHLIST": (
                    QUICK_CROSSOVER_INCLUDE_BASELINE_WATCHLIST
                ),
                "QUICK_CROSSOVER_INCLUDE_INPUT_SYMBOLS": (
                    QUICK_CROSSOVER_INCLUDE_INPUT_SYMBOLS
                ),
                "QUICK_CROSSOVER_UPDATE_BASELINE": (
                    QUICK_CROSSOVER_UPDATE_BASELINE
                ),
                "QUICK_CROSSOVER_BASELINE_STATES": "|".join(
                    QUICK_CROSSOVER_BASELINE_STATES
                ),
                "QUICK_CROSSOVER_STATES": "|".join(
                    QUICK_CROSSOVER_STATES
                ),
                "USE_LIVE_PRICE_FOR_DAILY": USE_LIVE_PRICE_FOR_DAILY,
                "LIVE_PRICE_INTERVAL": LIVE_PRICE_INTERVAL,
                "LIVE_PRICE_PERIOD": LIVE_PRICE_PERIOD,
                "LIVE_PRICE_PREPOST": LIVE_PRICE_PREPOST
            },
            output_columns=(
                L1Engine.SETUP_OUTPUT_COLUMNS
                if ENGINE_MODE == ENGINE_MODE_QUICK_SETUP
                else None
            )
        )

        print("")
        print("=" * 70)
        print("PMDE INPUT LOAD FAILED")
        print("=" * 70)
        print(str(error))
        print("=" * 70)

        reporter.record_failure(
            "INPUT_LOAD",
            error
        )

        reporter.finalize(
            total_symbols=0
        )

        raise SystemExit(1) from error

    symbols = symbol_load["symbols"]

    reporter = ExecutionReporter(
        output_file=OUTPUT_FILE,
        engine_name=ENGINE_NAME,
        version=VERSION,
        run_mode=RUN_MODE,
        input_file=INPUT_FILE,
        metadata={
            "FILE_SYMBOL_COUNT": symbol_load["file_count"],
            "HARDCODED_SYMBOL_COUNT": symbol_load["hardcoded_count"],
            "FALLBACK_SYMBOL_COUNT": symbol_load["fallback_count"],
            "BASELINE_SYMBOL_COUNT": symbol_load["baseline_count"],
            "BASELINE_WATCH_SYMBOL_COUNT": (
                symbol_load["baseline_watch_count"]
            ),
            "INPUT_SYMBOL_COUNT": symbol_load["input_symbol_count"],
            "RESOLVED_SYMBOL_SOURCE": (
                symbol_load["resolved_symbol_source"]
            ),
            "ACTIVE_SYMBOLS": "|".join(symbols),
            "INPUT_WARNINGS": " | ".join(symbol_load["warnings"]),
            "ENGINE_MODE": ENGINE_MODE,
            "QUICK_SETUP_INCLUDE_INPUT_FILE": (
                QUICK_SETUP_INCLUDE_INPUT_FILE
            ),
            "QUICK_SETUP_INCLUDE_BASELINE_SYMBOLS": (
                QUICK_SETUP_INCLUDE_BASELINE_SYMBOLS
            ),
            "SETUP_OUTPUT_POLICY": (
                "CONFIRMED_ONLY"
                if SETUP_OUTPUT_ONLY_CONFIRMED
                else "ALL_ASSESSED_SYMBOLS"
            ),
            "SUPPORTED_ENGINE_MODES": "|".join(
                SUPPORTED_ENGINE_MODES
            ),
            "FORCE_L2_ASSESSMENT": FORCE_L2_ASSESSMENT,
            "MACD_FAST": MACD_FAST,
            "MACD_SLOW": MACD_SLOW,
            "MACD_SIGNAL": MACD_SIGNAL,
            "SETUP_PRICE_LOOKBACK_X": SETUP_PRICE_LOOKBACK_X,
            "SETUP_PRICE_MIN_ADVANCE_PCT": SETUP_PRICE_MIN_ADVANCE_PCT,
            "SETUP_PRIMARY_TIMEFRAME": SETUP_PRIMARY_TIMEFRAME,
            "SETUP_BRIDGE_TIMEFRAME": SETUP_BRIDGE_TIMEFRAME,
            "SETUP_TRIGGER_TIMEFRAME": SETUP_TRIGGER_TIMEFRAME,
            "SETUP_MACD_HISTOGRAM_RISING_STREAK": (
                SETUP_MACD_HISTOGRAM_RISING_STREAK
            ),
            "SETUP_REQUIRE_EMA200_BULL_ZONE": SETUP_REQUIRE_EMA200_BULL_ZONE,
            "SETUP_REJECT_EXTENDED_UP": SETUP_REJECT_EXTENDED_UP,
            "SETUP_REJECT_GAP_UP": SETUP_REJECT_GAP_UP,
            "SETUP_REJECT_HIGH_ATRP": SETUP_REJECT_HIGH_ATRP,
            "SETUP_RSI_MIN": SETUP_RSI_MIN,
            "SETUP_RSI_MAX": SETUP_RSI_MAX,
            "SETUP_RSI_HEADROOM_FULL_SCORE_PCT": (
                SETUP_RSI_HEADROOM_FULL_SCORE_PCT
            ),
            "SETUP_RSI_HEADROOM_MIN_SCORE_PCT": (
                SETUP_RSI_HEADROOM_MIN_SCORE_PCT
            ),
            "SETUP_OUTPUT_ONLY_CONFIRMED": SETUP_OUTPUT_ONLY_CONFIRMED,
            "QUICK_CROSSOVER_OUTPUT_ONLY_PROBABLES": (
                QUICK_CROSSOVER_OUTPUT_ONLY_PROBABLES
            ),
            "QUICK_CROSSOVER_INCLUDE_BASELINE_WATCHLIST": (
                QUICK_CROSSOVER_INCLUDE_BASELINE_WATCHLIST
            ),
            "QUICK_CROSSOVER_INCLUDE_INPUT_SYMBOLS": (
                QUICK_CROSSOVER_INCLUDE_INPUT_SYMBOLS
            ),
            "QUICK_CROSSOVER_UPDATE_BASELINE": (
                QUICK_CROSSOVER_UPDATE_BASELINE
            ),
            "QUICK_CROSSOVER_BASELINE_STATES": "|".join(
                QUICK_CROSSOVER_BASELINE_STATES
            ),
            "QUICK_CROSSOVER_STATES": "|".join(
                QUICK_CROSSOVER_STATES
            ),
            "USE_LIVE_PRICE_FOR_DAILY": USE_LIVE_PRICE_FOR_DAILY,
            "LIVE_PRICE_INTERVAL": LIVE_PRICE_INTERVAL,
            "LIVE_PRICE_PERIOD": LIVE_PRICE_PERIOD,
            "LIVE_PRICE_PREPOST": LIVE_PRICE_PREPOST,
            "DATA_PERIOD_1D": DATA_PERIODS["1d"],
            "DATA_PERIOD_4H": DATA_PERIODS["4h"],
            "DATA_PERIOD_1H": DATA_PERIODS["1h"],
            "ACTIVE_GENERIC_FACTS": "|".join(
                ACTIVE_GENERIC_FACTS
            )
        },
        output_columns=(
            L1Engine.SETUP_OUTPUT_COLUMNS
            if ENGINE_MODE == ENGINE_MODE_QUICK_SETUP
            else None
        )
    )

    print("")
    print("=" * 70)
    print("PMDE EXECUTION STARTED")
    print("=" * 70)
    print("")
    print(f"ENGINE MODE   : {ENGINE_MODE}")
    print(f"OUTPUT FILE   : {OUTPUT_FILE}")
    if ENGINE_MODE == ENGINE_MODE_QUICK_SETUP:
        print(
            "SETUP OUTPUT  : "
            + (
                "CONFIRMED ONLY"
                if SETUP_OUTPUT_ONLY_CONFIRMED
                else "ALL ASSESSED SYMBOLS"
            )
        )
        print(
            "QS INPUT FILE : "
            + (
                "ENABLED"
                if QUICK_SETUP_INCLUDE_INPUT_FILE
                else "DISABLED"
            )
        )
        print(
            "QS BASELINE   : "
            + (
                "ENABLED"
                if QUICK_SETUP_INCLUDE_BASELINE_SYMBOLS
                else "DISABLED"
            )
        )
    print(f"INPUT FILE    : {INPUT_FILE}")
    print(f"FILE SYMBOLS  : {symbol_load['file_count']}")
    print(f"HARDCODED     : {symbol_load['hardcoded_count']}")
    print(f"FALLBACK      : {symbol_load['fallback_count']}")
    print(f"BASELINE      : {symbol_load['baseline_count']}")
    print(f"BASELINE WATCH: {symbol_load['baseline_watch_count']}")
    print(f"SOURCE        : {symbol_load['resolved_symbol_source']}")
    print(f"SYMBOL COUNT  : {len(symbols)}")
    print(f"SYMBOLS READ  : {format_symbol_preview(symbols)}")
    for warning in symbol_load["warnings"]:
        print(f"WARNING       : {warning}")
    print("")

    for symbol in symbols:

        try:

            print(
                f"Processing {symbol}"
            )

            assessment = L1Engine.assess(
                symbol
            )

            if ENGINE_MODE == ENGINE_MODE_QUICK_SETUP:

                setup_flag = (
                    "YES"
                    if assessment.tactical_decision.setup_happens
                    else "NO"
                )

                print(
                    "Result "
                    f"{symbol}: Setup={setup_flag}; "
                    f"State={assessment.tactical_decision.tactical_state}; "
                    f"Score={assessment.tactical_decision.setup_score}; "
                    f"Rejected_At="
                    f"{assessment.tactical_decision.rejection_stage}"
                )

            should_record = (
                ENGINE_MODE != ENGINE_MODE_QUICK_SETUP
                or
                not SETUP_OUTPUT_ONLY_CONFIRMED
                or
                assessment.tactical_decision.setup_happens
            )

            if (
                ENGINE_MODE == ENGINE_MODE_QUICK_CROSSOVER
                and
                QUICK_CROSSOVER_OUTPUT_ONLY_PROBABLES
            ):

                should_record = (
                    assessment.tactical_decision.tactical_state
                    in QUICK_CROSSOVER_STATES
                )

            if should_record:

                reporter.record_success(
                    assessment.output_row
                )

            else:

                reporter.record_filtered(
                    assessment.output_row
                )

            if (
                (
                    ENGINE_MODE == ENGINE_MODE_FULL_BASELINE
                    or
                    (
                        ENGINE_MODE == ENGINE_MODE_QUICK_CROSSOVER
                        and
                        QUICK_CROSSOVER_UPDATE_BASELINE
                    )
                )
                and
                assessment.baseline_record
            ):

                BaselineRegistry.update(
                    assessment.baseline_record
                )

        except Exception as error:

            reporter.record_failure(
                symbol,
                error
            )

    reporter.finalize(
        total_symbols=len(symbols)
    )


if __name__ == "__main__":
    main()
