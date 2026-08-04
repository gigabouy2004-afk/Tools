from __future__ import annotations

import csv
from email.parser import BytesParser
from email.policy import default
import html
import logging
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import subprocess
import time
from urllib.parse import parse_qs

from column_renderer import MAIN_RESULT_COLUMNS, render_headers, render_row
from stock_screener import (
    ScreenerFilters,
    StockScreener,
    build_output_rows,
    describe_filter_conditions,
    export_rows,
    normalize_exchange,
    parse_list,
    sort_output_rows,
)
from html_formatter import generate_html_report


HOST = "127.0.0.1"
PORT = 8000
ROOT = Path(__file__).resolve().parent
UPLOAD_DIR = ROOT / "uploads"
DEFAULT_SYMBOLS_FILE = "clean_universe.csv"
DEFAULT_NSE_SYMBOLS_FILE = "uploads/EQUITY_L.csv"
DEFAULT_OUTPUT_FILE = "screener_output.csv"
DEFAULT_HTML_OUTPUT = "screener_report.html"
LOG_FILE = "web_app.log"
DEFAULT_PROCESS_BATCH_SIZE = 30
MAX_PROCESS_BATCH_SIZE = 150
LOW_HIT_RATE_THRESHOLD = 0.10
CANDIDATE_STATES = [
    "PRE_BULL_CROSSOVER",
    "PRE_BEAR_CROSSOVER",
    "BULL_EXTENDED",
    "SETUP_CANDIDATE",
    "BULLISH_DIVERGENCE",
    "BEARISH_DIVERGENCE",
]
FALLBACK_EXCHANGES = [
    "BSE",
    "NASDAQ",
    "NSE",
    "NYSE",
]
FALLBACK_SECTORS = [
    "Basic Materials",
    "Communication Services",
    "Consumer Cyclical",
    "Consumer Defensive",
    "Energy",
    "ETF",
    "Financial Services",
    "Healthcare",
    "Industrials",
    "Real Estate",
    "Technology",
    "Utilities",
]
FALLBACK_INDUSTRIES = [
    "Auto Manufacturers",
    "Banks - Diversified",
    "Consumer Electronics",
    "Exchange Traded Fund",
    "Internet Content & Information",
    "Internet Retail",
    "Semiconductors",
    "Software - Infrastructure",
]


def _stop_existing_web_app_processes() -> None:
    current_pid = os.getpid()
    parent_pid = os.getppid()
    script_name = Path(__file__).name
    command = (
        "$currentPid = " + str(current_pid) + "; "
        "$parentPid = " + str(parent_pid) + "; "
        "$scriptName = '" + script_name.replace("'", "''") + "'; "
        "Get-CimInstance Win32_Process -Filter \"name = 'python.exe'\" | "
        "Where-Object { $_.ProcessId -ne $currentPid -and $_.ProcessId -ne $parentPid -and $_.CommandLine -like \"*$scriptName*\" } | "
        "ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
    )
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        time.sleep(0.5)
    except Exception as exc:
        logging.warning("Could not stop existing web_app.py processes: %s", exc)
NUMBER_FIELDS = {
    "price_min": "Price Min",
    "price_max": "Price Max",
    "market_cap_min": "Market Cap Min",
    "market_cap_max": "Market Cap Max",
    "avg_volume_min": "Avg Daily Volume Min",
    "avg_volume_max": "Avg Daily Volume Max",
    "rsi_min": "RSI Min",
    "rsi_max": "RSI Max",
    "adx_min": "ADX Min",
    "adx_max": "ADX Max",
    "bollinger_pct_min": "Bollinger %b Min",
    "bollinger_pct_max": "Bollinger %b Max",
}
RANGE_FIELDS = [
    ("price_min", "price_max", "Price"),
    ("market_cap_min", "market_cap_max", "Market Cap"),
    ("avg_volume_min", "avg_volume_max", "Avg Daily Volume"),
    ("rsi_min", "rsi_max", "RSI"),
    ("adx_min", "adx_max", "ADX"),
    ("bollinger_pct_min", "bollinger_pct_max", "Bollinger %b"),
]


def _first(form: dict[str, list[str]], key: str, default: str = "") -> str:
    return form.get(key, [default])[0].strip()


def _list_value(form: dict[str, list[str]], key: str, default: list[str] | None = None) -> list[str]:
    values = form.get(key, default or [])
    cleaned: list[str] = []
    for value in values:
        cleaned.extend(parse_list(value))
    return cleaned


def _float_or_none(value: str) -> float | None:
    value = value.strip()
    return float(value) if value else None


def _int_or_none(value: str) -> int | None:
    value = value.strip()
    return int(value) if value else None


def _default_symbols_file() -> str:
    nse_path = ROOT / DEFAULT_NSE_SYMBOLS_FILE
    return DEFAULT_NSE_SYMBOLS_FILE if nse_path.exists() else DEFAULT_SYMBOLS_FILE


def _form_values(form: dict[str, list[str]] | None = None) -> dict[str, str | list[str]]:
    submitted = form is not None
    form = form or {}
    return {
        "symbols_file": _first(form, "symbols_file", _default_symbols_file()),
        "max_symbols": _first(form, "max_symbols", "50"),
        "output_file": _first(form, "output_file", DEFAULT_OUTPUT_FILE),
        "html_output": _first(form, "html_output", DEFAULT_HTML_OUTPUT),
        "exchange": _list_value(form, "exchange"),
        "sector": _list_value(form, "sector"),
        "industry": _list_value(form, "industry"),
        "instrument_type": _first(form, "instrument_type", "EQUITY"),
        "price_min": _first(form, "price_min", ""),
        "price_max": _first(form, "price_max", ""),
        "market_cap_min": _first(form, "market_cap_min", ""),
        "market_cap_max": _first(form, "market_cap_max", ""),
        "avg_volume_min": _first(form, "avg_volume_min", ""),
        "avg_volume_max": _first(form, "avg_volume_max", ""),
        "rsi_min": _first(form, "rsi_min", ""),
        "rsi_max": _first(form, "rsi_max", ""),
        "adx_min": _first(form, "adx_min", ""),
        "adx_max": _first(form, "adx_max", ""),
        "bollinger_pct_min": _first(form, "bollinger_pct_min", ""),
        "bollinger_pct_max": _first(form, "bollinger_pct_max", ""),
        "states": form.get("states", [] if submitted else ["PRE_BULL_CROSSOVER", "PRE_BEAR_CROSSOVER", "BULL_EXTENDED", "SETUP_CANDIDATE"]),
    }


def _filters_from_values(values: dict[str, str | list[str]]) -> ScreenerFilters:
    return ScreenerFilters(
        exchanges=list(values["exchange"]) if isinstance(values["exchange"], list) else parse_list(str(values["exchange"])),
        sectors=list(values["sector"]) if isinstance(values["sector"], list) else parse_list(str(values["sector"])),
        industries=list(values["industry"]) if isinstance(values["industry"], list) else parse_list(str(values["industry"])),
        types=parse_list(str(values["instrument_type"])) if values["instrument_type"] else [],
        price_min=_float_or_none(str(values["price_min"])),
        price_max=_float_or_none(str(values["price_max"])),
        market_cap_min=_float_or_none(str(values["market_cap_min"])),
        market_cap_max=_float_or_none(str(values["market_cap_max"])),
        avg_volume_min=_float_or_none(str(values["avg_volume_min"])),
        avg_volume_max=_float_or_none(str(values["avg_volume_max"])),
        rsi_min=_float_or_none(str(values["rsi_min"])),
        rsi_max=_float_or_none(str(values["rsi_max"])),
        adx_min=_float_or_none(str(values["adx_min"])),
        adx_max=_float_or_none(str(values["adx_max"])),
        bollinger_pct_min=_float_or_none(str(values["bollinger_pct_min"])),
        bollinger_pct_max=_float_or_none(str(values["bollinger_pct_max"])),
        states=list(values["states"]) if isinstance(values["states"], list) else parse_list(str(values["states"])),
    )


def _validate_values(values: dict[str, str | list[str]]) -> None:
    parsed: dict[str, float | None] = {}
    for key, label in NUMBER_FIELDS.items():
        raw = str(values[key]).strip()
        if not raw:
            parsed[key] = None
            continue
        try:
            parsed[key] = float(raw)
        except ValueError as exc:
            raise ValueError(f"{label} must be a number or left blank.") from exc
    max_symbols = str(values["max_symbols"]).strip()
    if max_symbols:
        try:
            if int(max_symbols) <= 0:
                raise ValueError
        except ValueError as exc:
            raise ValueError("Max Symbols must be a positive whole number or left blank.") from exc
    for low_key, high_key, label in RANGE_FIELDS:
        low = parsed[low_key]
        high = parsed[high_key]
        if low is not None and high is not None and low > high:
            raise ValueError(f"{label} Min cannot be greater than {label} Max.")


def _workspace_path(filename: str) -> Path:
    path = (ROOT / filename).resolve()
    if ROOT not in [path, *path.parents]:
        raise ValueError("Output path must stay inside the project folder.")
    return path


def _file_link(path_value: str, label: str, route: str) -> str:
    if not path_value:
        return ""
    path = _workspace_path(path_value)
    if not path.exists():
        return ""
    href = f"{route}?file={html.escape(path.name)}"
    return f'<a class="link" href="{href}" target="_blank" rel="noopener">{html.escape(label)}</a>'


def _read_unique_values(column: str, fallback: list[str] | None = None) -> list[str]:
    values: set[str] = set(fallback or [])
    for filename in [DEFAULT_SYMBOLS_FILE, "symbols.csv", "tech_sample.csv"]:
        path = ROOT / filename
        if not path.exists():
            continue
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                if not reader.fieldnames or column not in reader.fieldnames:
                    continue
                for row in reader:
                    value = (row.get(column) or "").strip()
                    if value:
                        values.add(value.replace("â€”", " - "))
        except OSError:
            continue
    return sorted(values, key=str.upper)


def _infer_exchanges_from_symbols_file(symbols_file: str) -> list[str]:
    if not symbols_file:
        return []
    try:
        path = _workspace_path(symbols_file)
    except ValueError:
        return []
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames:
                return []
            normalized_columns = {field.strip().upper() for field in reader.fieldnames}
            if {"SYMBOL", "SERIES", "ISIN NUMBER"}.issubset(normalized_columns):
                return ["NSE"]
            exchange_field = next((field for field in reader.fieldnames if field.strip().lower() == "exchange"), None)
            if not exchange_field:
                return []
            values = {
                normalize_exchange((row.get(exchange_field) or "").strip())
                for row in reader
                if (row.get(exchange_field) or "").strip()
            }
            return sorted({value for value in values if value}, key=str.upper)
    except OSError:
        return []


def _options(name: str, choices: list[str], selected: list[str]) -> str:
    all_choices = sorted({*choices, *selected}, key=str.upper)
    return "\n".join(
        f'<option value="{html.escape(choice)}" {"selected" if choice in selected else ""}>{html.escape(choice)}</option>'
        for choice in all_choices
    )


def _parse_post(headers, body: bytes) -> dict[str, list[str]]:
    content_type = headers.get("Content-Type", "")
    if content_type.startswith("multipart/form-data"):
        parser = BytesParser(policy=default)
        message = parser.parsebytes(
            f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("utf-8") + body
        )
        form: dict[str, list[str]] = {}
        for part in message.iter_parts():
            name = part.get_param("name", header="content-disposition")
            if not name:
                continue
            filename = part.get_filename()
            payload = part.get_payload(decode=True) or b""
            if filename:
                if payload:
                    UPLOAD_DIR.mkdir(exist_ok=True)
                    safe_name = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in Path(filename).name)
                    path = UPLOAD_DIR / safe_name
                    path.write_bytes(payload)
                    form["symbols_file"] = [str(path.relative_to(ROOT))]
                continue
            charset = part.get_content_charset() or "utf-8"
            form.setdefault(name, []).append(payload.decode(charset, errors="replace").strip())
        return form
    return parse_qs(body.decode("utf-8"))


def _run_screener(values: dict[str, str | list[str]]) -> tuple[list[dict], str]:
    _validate_values(values)
    filters = _filters_from_values(values)
    symbols = StockScreener.load_universe(str(values["symbols_file"]))
    total_symbols = len(symbols)
    max_results = _int_or_none(str(values["max_symbols"]))
    batch_size = min(DEFAULT_PROCESS_BATCH_SIZE, total_symbols) if total_symbols else DEFAULT_PROCESS_BATCH_SIZE
    batch_size = max(1, batch_size)
    screener = StockScreener(filters)
    rows: list[dict] = []
    output_rows: list[dict] = []
    processed_symbols = 0
    batches = 0
    max_batch_size = min(MAX_PROCESS_BATCH_SIZE, total_symbols) if total_symbols else DEFAULT_PROCESS_BATCH_SIZE
    batch_adjustments: list[str] = []
    while processed_symbols < total_symbols:
        batch_symbols = symbols[processed_symbols:processed_symbols + batch_size]
        if not batch_symbols:
            break
        previous_match_count = len(output_rows)
        batches += 1
        batch_rows = screener.screen(batch_symbols)
        rows.extend(batch_rows)
        processed_symbols += len(batch_symbols)
        output_rows.extend(build_output_rows(batch_rows, filters))
        output_rows = sort_output_rows(output_rows)
        new_matches = len(output_rows) - previous_match_count
        hit_rate = new_matches / len(batch_symbols) if batch_symbols else 0.0
        logging.info(
            "Batch %d processed %d symbols at batch size %d (%d/%d); new matches %d; total matched %d/%s; hit rate %.1f%%.",
            batches,
            len(batch_symbols),
            batch_size,
            processed_symbols,
            total_symbols,
            new_matches,
            len(output_rows),
            max_results if max_results is not None else "all",
            hit_rate * 100,
        )
        if max_results is not None and len(output_rows) >= max_results:
            output_rows = sort_output_rows(output_rows)[:max_results]
            break
        if processed_symbols < total_symbols and batch_size < max_batch_size:
            next_batch_size = batch_size
            if new_matches == 0:
                next_batch_size = min(max_batch_size, batch_size * 2)
            elif hit_rate < LOW_HIT_RATE_THRESHOLD:
                next_batch_size = min(max_batch_size, max(batch_size + 1, int(batch_size * 1.5)))
            if next_batch_size != batch_size:
                logging.info(
                    "Increasing batch size from %d to %d after batch %d hit rate %.1f%%.",
                    batch_size,
                    next_batch_size,
                    batches,
                    hit_rate * 100,
                )
                batch_adjustments.append(f"{batch_size}->{next_batch_size} after batch {batches} ({hit_rate:.1%} hit rate)")
                batch_size = next_batch_size
    csv_path = str(values["output_file"])
    html_path = str(values["html_output"])
    output_rows = sort_output_rows(output_rows)
    export_rows(output_rows, csv_path)
    generate_html_report(output_rows, html_path, describe_filter_conditions(filters))
    skipped_count = processed_symbols - len(rows)
    stop_text = (
        f"Stopped after reaching the Max Results target of {max_results}."
        if max_results is not None and len(output_rows) >= max_results
        else "Universe exhausted before reaching the Max Results target."
        if max_results is not None
        else "Processed the full universe."
    )
    message = (
        f"Processed {processed_symbols} of {total_symbols} symbols in {batches} batches; final batch size {batch_size}. "
        f"{stop_text} Processed {len(rows)} with market data"
        f"{f'; skipped {skipped_count}' if skipped_count else ''}. "
        f"Returning {len(output_rows)} matching candidates after applying filters and selected states. "
        f"Wrote results to {csv_path} and {html_path}."
        f"{' Batch size adjustments: ' + '; '.join(batch_adjustments) + '.' if batch_adjustments else ''}"
    )
    return output_rows, message


def _render_results_panel(
    values: dict[str, str | list[str]],
    rows: list[dict] | None = None,
    message: str = "",
    error: str = "",
) -> str:
    rows = rows or []
    table_rows = "\n".join(
        render_row(row, MAIN_RESULT_COLUMNS, use_display_format=True)
        for row in rows
    )
    if not table_rows:
        table_rows = f'<tr><td colspan="{len(MAIN_RESULT_COLUMNS)}" class="empty">No matching symbols yet.</td></tr>'
    table_headers = render_headers(MAIN_RESULT_COLUMNS)
    return f"""
        {f'<div class="message">{html.escape(message)}</div>' if message else ''}
        {f'<div class="error">{html.escape(error)}</div>' if error else ''}
        {'<p class="empty-note">No rows appear when analyzed symbols either fail the base filters, do not meet the selected candidate states, or could not be analyzed from the market data provider.</p>' if message and not rows else ''}
        <div class="results-toolbar">
            <div>
                <h2>Matched Results</h2>
                <p>{len(rows)} visible candidates</p>
            </div>
            <div class="result-links">
                {_file_link(str(values['html_output']), 'Open HTML report', '/report')}
                {_file_link(str(values['output_file']), 'Download CSV', '/download')}
            </div>
        </div>
        <div class="table-wrap">
            <table>
                <thead>
                    <tr>{table_headers}</tr>
                </thead>
                <tbody>{table_rows}</tbody>
            </table>
        </div>
    """


def _render_page(values: dict[str, str | list[str]], rows: list[dict] | None = None, message: str = "", error: str = "") -> str:
    rows = rows or []
    selected_exchanges = values["exchange"] if isinstance(values["exchange"], list) else parse_list(str(values["exchange"]))
    selected_sectors = values["sector"] if isinstance(values["sector"], list) else parse_list(str(values["sector"]))
    selected_industries = values["industry"] if isinstance(values["industry"], list) else parse_list(str(values["industry"]))
    selected_states = set(values["states"] if isinstance(values["states"], list) else [])
    exchange_choices = sorted(
        {
            *_read_unique_values("Exchange", FALLBACK_EXCHANGES),
            *_infer_exchanges_from_symbols_file(str(values["symbols_file"])),
        },
        key=str.upper,
    )
    exchange_options = _options("exchange", exchange_choices, selected_exchanges)
    sector_options = _options("sector", _read_unique_values("Sector", FALLBACK_SECTORS), selected_sectors)
    industry_options = _options("industry", _read_unique_values("Industry", FALLBACK_INDUSTRIES), selected_industries)
    state_controls = "\n".join(
        f"""
        <label class="check">
            <input type="checkbox" name="states" value="{state}" {'checked' if state in selected_states else ''}>
            <span>{state}</span>
        </label>
        """
        for state in CANDIDATE_STATES
    )

    return f"""<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Stock Screener</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; background: #eef2f6; color: #1f2933; }}
        header {{ background: #17324d; color: white; padding: 16px 24px; }}
        header h1 {{ margin: 0 0 4px; font-size: 22px; }}
        header p {{ margin: 0; color: #d9e8f5; }}
        main {{ display: grid; grid-template-columns: 360px minmax(0, 1fr); gap: 18px; height: calc(100vh - 76px); padding: 18px; }}
        form {{ background: white; border: 1px solid #d9e2ec; border-radius: 8px; padding: 16px; overflow-y: auto; }}
        .grid {{ display: grid; grid-template-columns: 1fr; gap: 12px; }}
        label {{ display: grid; gap: 6px; font-size: 13px; font-weight: 600; }}
        input, select {{ border: 1px solid #bcccdc; border-radius: 6px; padding: 9px 10px; font-size: 14px; background: white; }}
        select {{ min-height: 92px; }}
        .hint {{ color: #52606d; font-size: 12px; margin-top: 5px; }}
        .states {{ display: grid; gap: 8px; margin-top: 14px; }}
        .check {{ display: flex; align-items: center; gap: 6px; border: 1px solid #d9e2ec; border-radius: 6px; padding: 8px 10px; background: #f8fafc; }}
        .check input {{ padding: 0; }}
        .actions {{ display: flex; flex-wrap: wrap; gap: 12px; align-items: center; margin-top: 18px; }}
        button {{ background: #0b7285; color: white; border: 0; border-radius: 6px; padding: 11px 16px; font-weight: 700; cursor: pointer; }}
        button:disabled {{ cursor: wait; opacity: 0.75; }}
        .link {{ color: #0b7285; font-weight: 700; text-decoration: none; }}
        .link:hover {{ text-decoration: underline; }}
        .running {{ display: none; color: #334e68; font-size: 13px; font-weight: 700; }}
        form.is-running .running {{ display: inline; }}
        .message {{ margin: 0 0 12px; padding: 12px; border-radius: 6px; background: #e6fffa; border: 1px solid #96f2d7; }}
        .error {{ margin: 0 0 12px; padding: 12px; border-radius: 6px; background: #fff5f5; border: 1px solid #ffc9c9; }}
        .empty-note {{ margin: 12px 0 0; color: #52606d; font-size: 13px; }}
        .results-panel {{ background: white; border: 1px solid #d9e2ec; border-radius: 8px; padding: 16px; overflow: hidden; min-width: 0; }}
        .results-toolbar {{ display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; margin-bottom: 12px; }}
        .results-toolbar h2 {{ margin: 0 0 4px; font-size: 18px; }}
        .results-toolbar p {{ margin: 0; color: #52606d; font-size: 13px; }}
        .result-links {{ display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 12px; }}
        .table-wrap {{ height: calc(100vh - 190px); overflow-y: auto; overflow-x: hidden; border: 1px solid #e5e7eb; border-radius: 8px; }}
        table {{ width: 100%; border-collapse: collapse; table-layout: fixed; }}
        th, td {{ text-align: left; border-bottom: 1px solid #e5e7eb; padding: 7px 6px; font-size: 12px; line-height: 1.35; vertical-align: top; overflow-wrap: anywhere; }}
        th {{ background: #f1f5f9; position: sticky; top: 0; z-index: 1; }}
        .col-Symbol {{ width: 6%; }}
        .col-CompanyName {{ width: 14%; }}
        .col-Exchange {{ width: 6%; }}
        .col-Sector {{ width: 9%; }}
        .col-Industry {{ width: 13%; }}
        .col-MarketCap, .col-AvgDailyVolume, .col-AvgMonthlyVolume, .col-LatestPrice {{ width: 7%; text-align: right; white-space: nowrap; }}
        .col-CandidateState {{ width: 12%; }}
        .col-WeightedScore {{ width: 7%; text-align: right; white-space: nowrap; }}
        .empty {{ text-align: center; color: #697586; padding: 24px; }}
        @media (max-width: 900px) {{
            main {{ grid-template-columns: 1fr; height: auto; }}
            form {{ max-height: none; }}
            .table-wrap {{ height: 70vh; }}
        }}
    </style>
</head>
<body>
    <header>
        <h1>Stock Screener</h1>
        <p>Enter base filters, then run the universe list through the screener engine.</p>
    </header>
    <main>
        <form id="screener-form" method="post" action="/" enctype="multipart/form-data">
            <div class="grid">
                <label>Symbols File
                    <input name="symbols_file" value="{html.escape(str(values['symbols_file']))}">
                    <input name="uploaded_symbols_file" type="file" accept=".csv,text/csv">
                    <span class="hint">Choose a local CSV with a Symbol column. NSE files are converted to Yahoo's .NS format automatically.</span>
                </label>
                <label>Max Results
                    <input name="max_symbols" type="number" min="1" step="1" value="{html.escape(str(values['max_symbols']))}">
                    <span class="hint">Return up to this many matching rows after processing. The engine scans the universe in batches of up to {DEFAULT_PROCESS_BATCH_SIZE} until this target is met.</span>
                </label>
                <label>CSV Output
                    <input name="output_file" value="{html.escape(str(values['output_file']))}">
                </label>
                <label>Standalone HTML Report File
                    <input name="html_output" value="{html.escape(str(values['html_output']))}">
                    <span class="hint">This is a saved report file. The table below is the inline preview on this page.</span>
                </label>
                <label>Exchange
                    <select name="exchange" multiple>{exchange_options}</select>
                </label>
                <label>Sector
                    <select name="sector" multiple>{sector_options}</select>
                </label>
                <label>Industry
                    <select name="industry" multiple>{industry_options}</select>
                </label>
                <label>Instrument Type
                    <input name="instrument_type" placeholder="EQUITY, ETF" value="{html.escape(str(values['instrument_type']))}">
                </label>
                <label>Price Min
                    <input name="price_min" type="number" step="0.01" value="{html.escape(str(values['price_min']))}">
                </label>
                <label>Price Max
                    <input name="price_max" type="number" step="0.01" value="{html.escape(str(values['price_max']))}">
                </label>
                <label>Market Cap Min
                    <input name="market_cap_min" type="number" step="1" value="{html.escape(str(values['market_cap_min']))}">
                </label>
                <label>Market Cap Max
                    <input name="market_cap_max" type="number" step="1" value="{html.escape(str(values['market_cap_max']))}">
                </label>
                <label>Avg Daily Volume Min
                    <input name="avg_volume_min" type="number" step="1" value="{html.escape(str(values['avg_volume_min']))}">
                </label>
                <label>Avg Daily Volume Max
                    <input name="avg_volume_max" type="number" step="1" value="{html.escape(str(values['avg_volume_max']))}">
                </label>
                <label>RSI Min
                    <input name="rsi_min" type="number" step="0.01" value="{html.escape(str(values['rsi_min']))}">
                </label>
                <label>RSI Max
                    <input name="rsi_max" type="number" step="0.01" value="{html.escape(str(values['rsi_max']))}">
                </label>
                <label>ADX Min
                    <input name="adx_min" type="number" step="0.01" value="{html.escape(str(values['adx_min']))}">
                </label>
                <label>ADX Max
                    <input name="adx_max" type="number" step="0.01" value="{html.escape(str(values['adx_max']))}">
                </label>
                <label>Bollinger %b Min
                    <input name="bollinger_pct_min" type="number" step="0.01" value="{html.escape(str(values['bollinger_pct_min']))}">
                </label>
                <label>Bollinger %b Max
                    <input name="bollinger_pct_max" type="number" step="0.01" value="{html.escape(str(values['bollinger_pct_max']))}">
                </label>
            </div>
            <div class="states">{state_controls}</div>
            <div class="actions">
                <button id="run-button" type="submit">Run Screener</button>
                <span class="running">Running screener. Keep this tab open until results appear.</span>
                {_file_link(str(values['html_output']), 'Open latest HTML report', '/report')}
                {_file_link(str(values['output_file']), 'Download latest CSV', '/download')}
            </div>
        </form>
        <section id="results-panel" class="results-panel">
            {_render_results_panel(values, rows, message=message, error=error)}
        </section>
    </main>
    <script>
        const form = document.getElementById('screener-form');
        const button = document.getElementById('run-button');
        const resultsPanel = document.getElementById('results-panel');
        async function getResult(event) {{
            event.preventDefault();
            form.classList.add('is-running');
            button.disabled = true;
            button.textContent = 'Running...';
            resultsPanel.innerHTML = '<div class="message">Running screener. Results will appear here when complete.</div>' + resultsPanel.innerHTML;
            try {{
                const response = await fetch('/results', {{
                    method: 'POST',
                    body: new FormData(form)
                }});
                const body = await response.text();
                resultsPanel.innerHTML = body;
            }} catch (error) {{
                resultsPanel.innerHTML = '<div class="error">Unable to run screener: ' + String(error) + '</div>';
            }} finally {{
                form.classList.remove('is-running');
                button.disabled = false;
                button.textContent = 'Run Screener';
            }}
        }}
        form.addEventListener('submit', getResult);
    </script>
</body>
</html>"""


class ScreenerHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path.startswith("/report"):
            self._send_file("file", "text/html; charset=utf-8")
            return
        if self.path.startswith("/download"):
            self._send_file("file", "text/csv; charset=utf-8")
            return
        self._send_html(_render_page(_form_values()))

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        values = _form_values(_parse_post(self.headers, raw))
        try:
            output_rows, message = _run_screener(values)
            if self.path.startswith("/results"):
                self._send_html(_render_results_panel(values, output_rows, message=message))
                return
            self._send_html(_render_page(values, output_rows, message=message))
        except ValueError as exc:
            if self.path.startswith("/results"):
                self._send_html(_render_results_panel(values, error=str(exc)), status=400)
                return
            self._send_html(_render_page(values, error=str(exc)), status=400)
        except Exception as exc:
            logging.exception("Web screener failed")
            if self.path.startswith("/results"):
                self._send_html(_render_results_panel(values, error=str(exc)), status=500)
                return
            self._send_html(_render_page(values, error=str(exc)), status=500)

    def log_message(self, format: str, *args: object) -> None:
        logging.info(format, *args)

    def _send_html(self, body: str, status: int = 200) -> None:
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_file(self, query_key: str, content_type: str) -> None:
        try:
            _, _, query = self.path.partition("?")
            filename = _first(parse_qs(query), query_key)
            path = _workspace_path(filename)
            if not path.exists() or not path.is_file():
                self._send_html(_render_page(_form_values(), error=f"File not found: {filename}"), status=404)
                return
            data = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            if content_type.startswith("text/csv"):
                self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
            self.end_headers()
            self.wfile.write(data)
        except Exception as exc:
            logging.exception("Unable to serve file")
            self._send_html(_render_page(_form_values(), error=str(exc)), status=500)


def main() -> None:
    log_path = ROOT / LOG_FILE
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_path, encoding="utf-8"),
        ],
    )
    _stop_existing_web_app_processes()
    server = ThreadingHTTPServer((HOST, PORT), ScreenerHandler)
    logging.info("Open http://%s:%s to run the screener. Logs: %s", HOST, PORT, log_path)
    server.serve_forever()


if __name__ == "__main__":
    main()
