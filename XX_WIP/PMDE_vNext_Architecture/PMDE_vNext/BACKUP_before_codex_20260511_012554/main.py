"""PMDE vNext execution entry point."""

from CONFIG.indicator_config import INPUT_CONFIG
from IO.symbol_loader import SymbolLoader


ENGINE_NAME = "PMDE vNext"


def load_symbols() -> list[str]:

    return SymbolLoader.load(
        input_file=INPUT_CONFIG.get("input_file"),
        symbol_column=INPUT_CONFIG.get("symbol_column"),
        exchange_column=INPUT_CONFIG.get("exchange_column"),
        default_exchange=INPUT_CONFIG.get("default_exchange"),
        fallback_symbols=INPUT_CONFIG.get("fallback_symbols"),
        sort_unique=INPUT_CONFIG.get("sort_unique", True)
    )


def process_symbol(symbol: str):

    raise NotImplementedError(
        "Live technical processing is not wired in this architecture "
        "folder yet. Symbol input loading is active; the next step is "
        "to connect L2 to L3 compute/data loading for each symbol."
    )


def main():

    print("")
    print("=" * 70)
    print(f"{ENGINE_NAME} EXECUTION STARTED")
    print("=" * 70)
    print("")

    try:

        symbols = load_symbols()

    except Exception as error:

        print("INPUT LOAD FAILED")
        print(str(error))
        raise

    print(
        f"Input file : {INPUT_CONFIG.get('input_file')}"
    )
    print(
        f"Symbols    : {len(symbols)}"
    )
    print("")

    success_count = 0
    failure_count = 0

    for symbol in symbols:

        try:

            print(
                f"Processing {symbol}"
            )

            process_symbol(symbol)

            success_count += 1

        except Exception as error:

            failure_count += 1
            print(
                f"FAILED {symbol}: {error}"
            )

    print("")
    print("=" * 70)
    print(f"{ENGINE_NAME} EXECUTION COMPLETED")
    print("=" * 70)
    print(f"TOTAL SYMBOLS : {len(symbols)}")
    print(f"SUCCESS       : {success_count}")
    print(f"FAILED        : {failure_count}")
    print("=" * 70)


if __name__ == "__main__":
    main()
