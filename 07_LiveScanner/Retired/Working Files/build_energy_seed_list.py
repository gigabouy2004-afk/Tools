import csv
import re
from pathlib import Path

SOURCE_FILES = [
    Path(r"d:\Tools\00_StockCodeMaster\02_Stock\004-US_EnergyStockCodes.csv"),
    Path(r"d:\Tools\00_StockCodeMaster\02_Stock\004-StockCodes_Sector_Energy_Industry-Refining&Marketing.csv"),
    Path(r"d:\Tools\00_StockCodeMaster\02_Stock\004-StockCodes_Sector_Energy_Industry-Oil&Gas.csv"),
]

OUT_DIR = Path(r"d:\Tools\07_LiveScanner\input")
OUT_FILE = OUT_DIR / "seed_energy_codes_all.csv"
OUT_FILE_CORE = OUT_DIR / "seed_energy_codes_core.csv"

TICKER_RE = re.compile(r"^[A-Z][A-Z0-9\.\-]{0,9}$")


def sanitize_symbol(raw: str) -> str | None:
    if not raw:
        return None
    s = raw.strip().upper()
    s = s.replace(" ", "")
    # Common cleanup from mixed exports
    s = s.replace("�", "")
    s = s.replace("ANIMA", "")
    if not s or s in {"SYMBOL", "TICKERS", "TICKER", "NAME"}:
        return None
    if not TICKER_RE.match(s):
        return None
    return s


def extract_symbols(path: Path) -> list[str]:
    symbols: list[str] = []
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        reader = csv.reader(f)
        header = next(reader, [])
        header_map = {h.strip().lower(): i for i, h in enumerate(header)}

        # Prefer explicit ticker/symbol column when present
        idx = None
        for candidate in ("symbol", "ticker", "tickers"):
            if candidate in header_map:
                idx = header_map[candidate]
                break

        for row in reader:
            if not row:
                continue
            raw = row[idx] if idx is not None and idx < len(row) else row[0]
            symbol = sanitize_symbol(raw)
            if symbol:
                symbols.append(symbol)
    return symbols


def write_seed(path: Path, symbols: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["ticker"])
        for s in symbols:
            writer.writerow([s])


def main() -> None:
    symbol_to_sources: dict[str, set[str]] = {}

    for src in SOURCE_FILES:
        if not src.exists():
            continue
        for symbol in extract_symbols(src):
            symbol_to_sources.setdefault(symbol, set()).add(src.name)

    all_symbols = sorted(symbol_to_sources.keys())
    # Core list: symbols present in at least 2 source files (higher confidence)
    core_symbols = sorted([s for s, sources in symbol_to_sources.items() if len(sources) >= 2])

    write_seed(OUT_FILE, all_symbols)
    write_seed(OUT_FILE_CORE, core_symbols)

    print(f"ALL_COUNT {len(all_symbols)}")
    print(f"CORE_COUNT {len(core_symbols)}")
    print(f"ALL_FILE {OUT_FILE}")
    print(f"CORE_FILE {OUT_FILE_CORE}")


if __name__ == "__main__":
    main()
