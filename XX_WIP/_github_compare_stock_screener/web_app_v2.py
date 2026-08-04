from __future__ import annotations

import csv
from datetime import datetime
from email.parser import BytesParser
from email.policy import default
import html
import json
import logging
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs
import uuid

from engine_v2.compute import compute_symbol_indicators


HOST = "127.0.0.1"
PORT = 8001
ROOT = Path(__file__).resolve().parent
UPLOAD_DIR = ROOT / "uploads"
TEXT_FILE = ROOT / "ui_text.json"
DEFAULT_SYMBOLS_FILE = "clean_universe.csv"
DEFAULT_OUTPUT_FILE = "screener_output_v2.csv"
DEFAULT_HTML_OUTPUT = "screener_report_v2.html"
LOG_FILE = "web_app_v2.log"
DEFAULT_PROCESS_BATCH_SIZE = 30
MAX_PROCESS_BATCH_SIZE = 150
MIN_PROCESS_BATCH_SIZE = 30
INITIAL_BATCH_UNIVERSE_PCT = 0.03
LOW_HIT_RATE_THRESHOLD = 0.10
POLL_SECONDS = 2
JOB_RETENTION_SECONDS = 60 * 60
MAX_RETAINED_COMPLETED_JOBS = 20
RUN_JOBS: dict[str, dict] = {}
RUN_JOBS_LOCK = threading.Lock()

FALLBACK_EXCHANGES = ["BSE", "NASDAQ", "NSE", "NYSE"]
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
STAGE_FAMILIES = ["CROSSOVER", "DIVERGENCE", "MOMENTUM_TRADING", "STATUS_QUO"]
NUMBER_FIELDS = {
    "max_symbols": "Max symbols",
    "price_min": "Price min",
    "price_max": "Price max",
    "market_cap_min": "Market cap min",
    "market_cap_max": "Market cap max",
    "avg_volume_min": "Avg volume min",
    "avg_volume_max": "Avg volume max",
    "rsi_min": "RSI min",
    "rsi_max": "RSI max",
    "adx_min": "ADX min",
    "adx_max": "ADX max",
    "bollinger_pct_min": "Bollinger %b min",
    "bollinger_pct_max": "Bollinger %b max",
    "crossover_freshness": "Crossover freshness bars",
    "divergence_lookback": "Divergence lookback",
    "divergence_recent_window": "Divergence recent window",
}
RANGE_FIELDS = [
    ("price_min", "price_max", "Price"),
    ("market_cap_min", "market_cap_max", "Market cap"),
    ("avg_volume_min", "avg_volume_max", "Average volume"),
    ("rsi_min", "rsi_max", "RSI"),
    ("adx_min", "adx_max", "ADX"),
    ("bollinger_pct_min", "bollinger_pct_max", "Bollinger %b"),
]


def _load_text() -> dict[str, str]:
    try:
        with TEXT_FILE.open("r", encoding="utf-8") as handle:
            values = json.load(handle)
        return {str(key): str(value) for key, value in values.items()}
    except Exception:
        return {}


TEXT = _load_text()


def t(key: str, default: str | None = None) -> str:
    return TEXT.get(key, default if default is not None else key)


def _first(form: dict[str, list[str]], key: str, default: str = "") -> str:
    return form.get(key, [default])[0].strip()


def _form_values(form: dict[str, list[str]] | None = None) -> dict[str, object]:
    form = form or {}
    return {
        "symbols_file": _first(form, "symbols_file", DEFAULT_SYMBOLS_FILE),
        "manual_symbols": _first(form, "manual_symbols", ""),
        "max_symbols": _first(form, "max_symbols", "50"),
        "output_file": _first(form, "output_file", DEFAULT_OUTPUT_FILE),
        "html_output": _first(form, "html_output", DEFAULT_HTML_OUTPUT),
        "exchange": form.get("exchange", []),
        "sector": form.get("sector", []),
        "industry": form.get("industry", []),
        "instrument_mode": _first(form, "instrument_mode", "EQUITY").upper(),
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
        "crossover_freshness": _first(form, "crossover_freshness", "3"),
        "divergence_lookback": _first(form, "divergence_lookback", "20"),
        "divergence_recent_window": _first(form, "divergence_recent_window", "5"),
        "stage_families": form.get("stage_families", ["CROSSOVER", "DIVERGENCE", "MOMENTUM_TRADING", "STATUS_QUO"]),
    }


def _float_or_none(value: object) -> float | None:
    text = str(value).strip()
    return float(text) if text else None


def _int_or_none(value: object) -> int | None:
    text = str(value).strip()
    return int(text) if text else None


def _workspace_path(filename: str) -> Path:
    if not filename:
        raise ValueError("File path cannot be blank.")
    path = (ROOT / filename).resolve()
    if ROOT not in [path, *path.parents]:
        raise ValueError("Path must stay inside the project folder.")
    return path


def _validate_values(values: dict[str, object]) -> None:
    instrument_mode = str(values.get("instrument_mode", "")).upper()
    if instrument_mode not in {"EQUITY", "ETF", "BOTH"}:
        raise ValueError("Select Instrument Type as Equity, ETF, or Both.")

    selected_stage_families = set(_selected(values, "stage_families"))
    invalid_families = selected_stage_families - set(STAGE_FAMILIES)
    if invalid_families:
        raise ValueError(f"Unknown stage family selected: {', '.join(sorted(invalid_families))}.")
    if not selected_stage_families:
        raise ValueError("Select at least one stage family.")

    parsed: dict[str, float | None] = {}
    for key, label in NUMBER_FIELDS.items():
        raw = str(values.get(key, "")).strip()
        if not raw:
            parsed[key] = None
            continue
        try:
            parsed[key] = float(raw)
        except ValueError as exc:
            raise ValueError(f"{label} must be a number or left blank.") from exc
        if parsed[key] is not None and parsed[key] < 0:
            raise ValueError(f"{label} cannot be negative.")

    max_symbols = _int_or_none(values.get("max_symbols", ""))
    if max_symbols is not None and max_symbols <= 0:
        raise ValueError("Max symbols must be a positive whole number or left blank.")

    for low_key, high_key, label in RANGE_FIELDS:
        low = parsed.get(low_key)
        high = parsed.get(high_key)
        if low is not None and high is not None and low > high:
            raise ValueError(f"{label} min cannot be greater than {label} max.")

    if str(values.get("symbols_file", "")).strip():
        path = _workspace_path(str(values["symbols_file"]))
        if not path.exists() or not path.is_file():
            raise ValueError(f"Symbols file not found: {values['symbols_file']}")


def _clean_symbol(symbol: object) -> str:
    normalized = str(symbol).strip().upper().replace("/", "-")
    if not normalized or normalized in {"NAN", "NONE", "NULL", "SYMBOL", "TICKER", "ACT SYMBOL", "NASDAQ SYMBOL"}:
        return ""
    if any(ch.isspace() for ch in normalized) or "," in normalized or "|" in normalized:
        return ""
    if len(normalized) > 20:
        return ""
    allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-^=")
    if any(ch not in allowed for ch in normalized):
        return ""
    return normalized


def _normalize_symbol(symbol: str, exchange: str | None = None) -> str:
    cleaned = _clean_symbol(symbol)
    if not cleaned:
        return ""
    if exchange and exchange.strip().upper() == "NSE" and "." not in cleaned:
        return f"{cleaned}.NS"
    return cleaned


def _unique_symbols(symbols: list[str]) -> list[str]:
    return list(dict.fromkeys(symbol for symbol in symbols if symbol))


def _manual_symbol_list(value: object) -> list[str]:
    symbols = [_normalize_symbol(item) for item in re.split(r"[\s,;]+", str(value or ""))]
    return _unique_symbols(symbols)


def _detect_delimiter(first_line: str) -> str:
    if first_line.count("|") > first_line.count(",") and first_line.count("|") > 0:
        return "|"
    if "\t" in first_line:
        return "\t"
    return ","


def _load_symbols_file(symbols_file: str) -> list[str]:
    path = _workspace_path(symbols_file)
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        first_line = handle.readline()
        handle.seek(0)
        reader = csv.DictReader(handle, delimiter=_detect_delimiter(first_line))
        if reader.fieldnames:
            normalized_fields = {" ".join(field.strip().upper().replace("_", " ").split()): field for field in reader.fieldnames}
            symbol_field = next(
                (normalized_fields[name] for name in ["TICKER", "ACT SYMBOL", "NASDAQ SYMBOL", "SYMBOL"] if name in normalized_fields),
                None,
            )
            exchange_field = normalized_fields.get("EXCHANGE")
            if symbol_field:
                return _unique_symbols([
                    _normalize_symbol(row.get(symbol_field, ""), row.get(exchange_field, "") if exchange_field else None)
                    for row in reader
                ])

    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        reader = csv.reader(handle, delimiter=_detect_delimiter(handle.readline()))
        handle.seek(0)
        return _unique_symbols([_normalize_symbol(row[0]) for row in reader if row])


def _combined_symbols(values: dict[str, object]) -> tuple[list[str], int, int]:
    symbols_file = str(values.get("symbols_file", "")).strip()
    file_symbols = _load_symbols_file(symbols_file) if symbols_file else []
    manual_symbols = _manual_symbol_list(values.get("manual_symbols", ""))
    symbols = _unique_symbols(file_symbols + manual_symbols)
    if not symbols:
        raise ValueError("Enter at least one manual ticker or select a symbols file.")
    return symbols, len(file_symbols), len(manual_symbols)


def _limited_symbols(values: dict[str, object], symbols: list[str]) -> list[str]:
    max_symbols = _int_or_none(values.get("max_symbols", ""))
    if max_symbols is None:
        return symbols
    return symbols[:max_symbols]


def _initial_batch_size(total_symbols: int) -> int:
    if total_symbols <= 0:
        return MIN_PROCESS_BATCH_SIZE
    percent_size = int(total_symbols * INITIAL_BATCH_UNIVERSE_PCT)
    batch_size = max(MIN_PROCESS_BATCH_SIZE, percent_size)
    return max(1, min(total_symbols, MAX_PROCESS_BATCH_SIZE, batch_size))


def _summarize_run_values(values: dict[str, object]) -> dict[str, object]:
    return {
        "symbols_file": values.get("symbols_file", ""),
        "manual_symbols": values.get("manual_symbols", ""),
        "max_symbols": values.get("max_symbols", ""),
        "output_file": values.get("output_file", ""),
        "html_output": values.get("html_output", ""),
        "exchange": values.get("exchange", []),
        "sector": values.get("sector", []),
        "industry": values.get("industry", []),
        "instrument_mode": values.get("instrument_mode", ""),
        "price_min": values.get("price_min", ""),
        "price_max": values.get("price_max", ""),
        "market_cap_min": values.get("market_cap_min", ""),
        "market_cap_max": values.get("market_cap_max", ""),
        "avg_volume_min": values.get("avg_volume_min", ""),
        "avg_volume_max": values.get("avg_volume_max", ""),
        "rsi_min": values.get("rsi_min", ""),
        "rsi_max": values.get("rsi_max", ""),
        "adx_min": values.get("adx_min", ""),
        "adx_max": values.get("adx_max", ""),
        "bollinger_pct_min": values.get("bollinger_pct_min", ""),
        "bollinger_pct_max": values.get("bollinger_pct_max", ""),
        "crossover_freshness": values.get("crossover_freshness", ""),
        "divergence_lookback": values.get("divergence_lookback", ""),
        "divergence_recent_window": values.get("divergence_recent_window", ""),
        "stage_families": values.get("stage_families", []),
    }


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
    return parse_qs(body.decode("utf-8", errors="replace"), keep_blank_values=True)


def _selected(values: dict[str, object], key: str) -> list[str]:
    value = values.get(key, [])
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)] if value else []


def _options(choices: list[str], selected: list[str]) -> str:
    merged = sorted({*choices, *selected}, key=str.upper)
    return "".join(
        f'<option value="{html.escape(choice)}" {"selected" if choice in selected else ""}>{html.escape(choice)}</option>'
        for choice in merged
    )


def _input(values: dict[str, object], name: str, input_type: str = "text", step: str | None = None) -> str:
    attrs = [f'name="{html.escape(name)}"', f'type="{html.escape(input_type)}"', f'value="{html.escape(str(values.get(name, "")))}"']
    if step:
        attrs.append(f'step="{html.escape(step)}"')
    if input_type == "number":
        attrs.append('min="0"')
    return f"<input {' '.join(attrs)}>"


def _field(label_key: str, control: str) -> str:
    return f"""
    <label class="field">
      <span>{html.escape(t(label_key))}</span>
      {control}
    </label>
    """


def _stage_controls(values: dict[str, object]) -> str:
    selected = set(_selected(values, "stage_families"))
    labels = {
        "CROSSOVER": t("stage.crossover"),
        "DIVERGENCE": t("stage.divergence"),
        "MOMENTUM_TRADING": t("stage.momentum_trading"),
        "STATUS_QUO": t("stage.status_quo"),
    }
    return "".join(
        f"""
        <label class="check-card">
          <input type="checkbox" name="stage_families" value="{family}" {"checked" if family in selected else ""}>
          <span>{html.escape(labels[family])}</span>
        </label>
        """
        for family in STAGE_FAMILIES
    )


def _instrument_controls(values: dict[str, object]) -> str:
    selected = str(values.get("instrument_mode", "EQUITY"))
    choices = [
        ("EQUITY", t("instrument.equity")),
        ("ETF", t("instrument.etf")),
        ("BOTH", t("instrument.both")),
    ]
    return "".join(
        f"""
        <label class="segmented-option">
          <input type="radio" name="instrument_mode" value="{value}" {"checked" if selected == value else ""}>
          <span>{html.escape(label)}</span>
        </label>
        """
        for value, label in choices
    )


def _results_panel(submitted: bool) -> str:
    title = t("results.submitted.title") if submitted else t("results.placeholder.title")
    body = t("results.submitted.body") if submitted else t("results.placeholder.body")
    return _render_results_panel(message=body, title=title)


def _render_results_panel(
    rows: list[dict[str, object]] | None = None,
    message: str = "",
    error: str = "",
    title: str | None = None,
) -> str:
    rows = rows or []
    table_rows = "\n".join(
        f"""
        <tr>
          <td>{html.escape(str(row.get("Symbol", "")))}</td>
          <td>{html.escape(str(row.get("Baseline", "")))}</td>
          <td>{html.escape(str(row.get("Stage", "")))}</td>
          <td>{html.escape(str(row.get("Confidence", "")))}</td>
          <td>{html.escape(str(row.get("Reason", "")))}</td>
        </tr>
        """
        for row in rows
    )
    if not table_rows:
        table_rows = '<tr><td colspan="5" class="empty">No matching symbols yet.</td></tr>'
    display_title = title or t("nav.results")
    return f"""
    <section class="panel results-panel" id="results">
      <div class="section-heading">
        <h2>{html.escape(display_title)}</h2>
        <p>{html.escape(message)}</p>
      </div>
      {f'<div class="message">{html.escape(message)}</div>' if message else ''}
      {f'<div class="error">{html.escape(error)}</div>' if error else ''}
      <table>
        <thead>
          <tr>
            <th>{html.escape(t("table.symbol"))}</th>
            <th>{html.escape(t("table.baseline"))}</th>
            <th>{html.escape(t("table.stage"))}</th>
            <th>{html.escape(t("table.confidence"))}</th>
            <th>{html.escape(t("table.reason"))}</th>
          </tr>
        </thead>
        <tbody>{table_rows}</tbody>
      </table>
    </section>
    """


def _cleanup_jobs_locked(now: float | None = None) -> None:
    now = time.time() if now is None else now
    expired_ids = [
        job_id
        for job_id, job in RUN_JOBS.items()
        if job.get("is_done") and now - float(job.get("updated_at", now)) > JOB_RETENTION_SECONDS
    ]
    for job_id in expired_ids:
        logging.info("Cleaning completed v2 job %s from memory after retention window.", job_id)
        RUN_JOBS.pop(job_id, None)

    completed_jobs = sorted(
        (
            (float(job.get("updated_at", 0)), job_id)
            for job_id, job in RUN_JOBS.items()
            if job.get("is_done")
        ),
        reverse=True,
    )
    for _, job_id in completed_jobs[MAX_RETAINED_COMPLETED_JOBS:]:
        logging.info("Cleaning completed v2 job %s from memory after retained job cap.", job_id)
        RUN_JOBS.pop(job_id, None)


def _job_progress_callback(job_id: str):
    def update(**payload: object) -> None:
        with RUN_JOBS_LOCK:
            job = RUN_JOBS.get(job_id)
            if not job:
                return
            job.update(payload)
            job["updated_at"] = time.time()
    return update


def _run_engine(
    values: dict[str, object],
    progress_callback=None,
    job_id: str | None = None,
) -> tuple[list[dict[str, object]], str]:
    _validate_values(values)
    run_job_id = job_id or "sync"
    run_timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    all_symbols, file_symbol_count, manual_symbol_count = _combined_symbols(values)
    symbols = _limited_symbols(values, all_symbols)
    stage_families = _selected(values, "stage_families")
    logging.info(
        "V2 job %s initialized. total_symbols=%d selected_symbols=%d file_symbols=%d manual_symbols=%d stage_families=%s",
        run_job_id,
        len(all_symbols),
        len(symbols),
        file_symbol_count,
        manual_symbol_count,
        ",".join(stage_families),
    )
    rows: list[dict[str, object]] = []
    total_symbols = len(symbols)
    processed_symbols = 0
    batches = 0
    batch_size = _initial_batch_size(total_symbols)
    max_batch_size = min(MAX_PROCESS_BATCH_SIZE, total_symbols) if total_symbols else DEFAULT_PROCESS_BATCH_SIZE
    batch_adjustments: list[str] = []
    while processed_symbols < total_symbols:
        batch_symbols = symbols[processed_symbols:processed_symbols + batch_size]
        if not batch_symbols:
            break
        previous_match_count = len(rows)
        batches += 1
        for symbol in batch_symbols:
            try:
                indicators = compute_symbol_indicators(symbol)
                baseline_macd = indicators.get("baseline_macd_1d", {})
                rsi = indicators.get("rsi_1d", {})
                adx = indicators.get("adx_1d", {})
                bollinger = indicators.get("bollinger_1d", {})
                rows.append({
                    "Symbol": symbol,
                    "Baseline": baseline_macd.get("regime", "UNKNOWN"),
                    "Stage": "UNCLASSIFIED",
                    "Confidence": "",
                    "Reason": (
                        f"Computed TA only. Price={indicators.get('latest_price')}; "
                        f"MACD={baseline_macd.get('macd')}; RSI={rsi.get('rsi')}; "
                        f"ADX={adx.get('adx')}; Bollinger%b={bollinger.get('percent_b')}."
                    ),
                })
            except Exception as exc:
                logging.warning("V2 compute failed for %s: %s", symbol, exc)
                rows.append({
                    "Symbol": symbol,
                    "Baseline": "ERROR",
                    "Stage": "ERROR",
                    "Confidence": "",
                    "Reason": f"Compute failed: {exc}",
                })
        processed_symbols += len(batch_symbols)
        new_matches = len(rows) - previous_match_count
        hit_rate = new_matches / len(batch_symbols) if batch_symbols else 0.0
        if progress_callback:
            progress_callback(
                rows=list(rows),
                message=(
                    f"Initialized {processed_symbols} of {total_symbols} symbols in {batches} batches; "
                    f"current batch size {batch_size}; matched {len(rows)} placeholder rows. "
                    "Stage classification will be wired next."
                ),
                processed_symbols=processed_symbols,
                total_symbols=total_symbols,
                batches=batches,
                batch_size=batch_size,
                matched=len(rows),
                is_done=False,
            )
        if processed_symbols < total_symbols and batch_size < max_batch_size:
            next_batch_size = batch_size
            if new_matches == 0:
                next_batch_size = min(max_batch_size, batch_size * 2)
            elif hit_rate < LOW_HIT_RATE_THRESHOLD:
                next_batch_size = min(max_batch_size, max(batch_size + 1, int(batch_size * 1.5)))
            else:
                next_batch_size = min(max_batch_size, max(batch_size + 1, int(batch_size * 1.5)))
            if next_batch_size != batch_size:
                logging.info(
                    "V2 job %s increasing batch size from %d to %d after batch %d hit rate %.1f%%.",
                    run_job_id,
                    batch_size,
                    next_batch_size,
                    batches,
                    hit_rate * 100,
                )
                batch_adjustments.append(f"{batch_size}->{next_batch_size} after batch {batches} ({hit_rate:.1%} hit rate)")
                batch_size = next_batch_size
    message = (
        f"Run initialized at {run_timestamp}. Loaded {len(all_symbols)} unique symbols "
        f"({file_symbol_count} from file, {manual_symbol_count} manual); selected {total_symbols} for this run. "
        f"Initialized in {batches} adaptive batches; final batch size {batch_size}. "
        f"Stage families: {', '.join(stage_families)}. Compute-only indicator layer completed."
        f"{' Batch size adjustments: ' + '; '.join(batch_adjustments) + '.' if batch_adjustments else ''}"
    )
    return rows, message


def _run_engine_job(job_id: str) -> None:
    with RUN_JOBS_LOCK:
        job = RUN_JOBS[job_id]
        values = job["values"]
        run_parameters = job.get("run_parameters", {})
    logging.info("V2 job %s started with parameters: %s", job_id, json.dumps(run_parameters, sort_keys=True))
    try:
        rows, message = _run_engine(values, progress_callback=_job_progress_callback(job_id), job_id=job_id)
        with RUN_JOBS_LOCK:
            job = RUN_JOBS.get(job_id)
            if job:
                job.update({
                    "rows": rows,
                    "message": message,
                    "error": "",
                    "is_done": True,
                    "updated_at": time.time(),
                })
                _cleanup_jobs_locked()
        logging.info("V2 job %s completed. message=%s", job_id, message)
    except Exception as exc:
        logging.exception("V2 background job failed")
        with RUN_JOBS_LOCK:
            job = RUN_JOBS.get(job_id)
            if job:
                job.update({
                    "error": str(exc),
                    "is_done": True,
                    "updated_at": time.time(),
                })
                _cleanup_jobs_locked()
        logging.info("V2 job %s failed with parameters: %s", job_id, json.dumps(run_parameters, sort_keys=True))


def _start_engine_job(values: dict[str, object]) -> str:
    _validate_values(values)
    job_id = uuid.uuid4().hex
    run_parameters = _summarize_run_values(values)
    with RUN_JOBS_LOCK:
        _cleanup_jobs_locked()
        RUN_JOBS[job_id] = {
            "values": values,
            "run_parameters": run_parameters,
            "rows": [],
            "message": "Engine queued. Waiting for initialization.",
            "error": "",
            "is_done": False,
            "processed_symbols": 0,
            "total_symbols": 0,
            "matched": 0,
            "started_at": time.time(),
            "updated_at": time.time(),
        }
    logging.info("Queued v2 job %s with parameters: %s", job_id, json.dumps(run_parameters, sort_keys=True))
    thread = threading.Thread(target=_run_engine_job, args=(job_id,), daemon=True)
    thread.start()
    return job_id


def _get_job(job_id: str) -> dict | None:
    with RUN_JOBS_LOCK:
        _cleanup_jobs_locked()
        job = RUN_JOBS.get(job_id)
        return dict(job) if job else None


def _render_page(values: dict[str, object] | None = None, submitted: bool = False) -> str:
    values = values or _form_values()
    exchange_options = _options(FALLBACK_EXCHANGES, _selected(values, "exchange"))
    sector_options = _options(FALLBACK_SECTORS, _selected(values, "sector"))
    industry_options = _options(FALLBACK_INDUSTRIES, _selected(values, "industry"))
    stage_controls = _stage_controls(values)
    instrument_controls = _instrument_controls(values)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(t("app.title"))}</title>
  <style>
    :root {{
      --bg: #f4f7fb;
      --panel: #ffffff;
      --border: #d7e0ea;
      --text: #1f2933;
      --muted: #637083;
      --accent: #1769aa;
      --accent-strong: #0f4c81;
      --surface: #eef4fa;
      --danger: #b42318;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: Arial, Helvetica, sans-serif;
      font-size: 14px;
      line-height: 1.45;
    }}
    header {{
      background: #102a43;
      color: white;
      padding: 22px 28px;
      border-bottom: 1px solid #0b1f33;
    }}
    .header-inner {{
      max-width: 1220px;
      margin: 0 auto;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 18px;
    }}
    h1, h2 {{ margin: 0; letter-spacing: 0; }}
    h1 {{ font-size: 25px; font-weight: 700; }}
    h2 {{ font-size: 17px; }}
    .subtitle {{ margin-top: 4px; color: #c9d8e8; }}
    .badge {{
      border: 1px solid #7aa5c7;
      border-radius: 999px;
      padding: 5px 10px;
      color: #dbeafe;
      white-space: nowrap;
    }}
    main {{
      max-width: 1220px;
      margin: 22px auto 48px;
      padding: 0 18px;
    }}
    form {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) 340px;
      gap: 18px;
      align-items: start;
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 18px;
      box-shadow: 0 1px 2px rgba(16, 42, 67, 0.05);
    }}
    .stack {{ display: grid; gap: 18px; }}
    .section-heading {{
      display: flex;
      justify-content: space-between;
      align-items: end;
      gap: 16px;
      margin-bottom: 14px;
    }}
    .section-heading p {{
      margin: 0;
      color: var(--muted);
      max-width: 560px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
    }}
    .grid.two {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    .field {{
      display: grid;
      gap: 5px;
      min-width: 0;
    }}
    .field span, .label {{
      font-weight: 700;
      color: #34495e;
      font-size: 13px;
    }}
    input, select, textarea {{
      width: 100%;
      border: 1px solid #bcccdc;
      border-radius: 6px;
      padding: 9px 10px;
      font-size: 14px;
      background: white;
      color: var(--text);
    }}
    select {{ min-height: 96px; }}
    textarea {{
      min-height: 76px;
      resize: vertical;
      font-family: Arial, Helvetica, sans-serif;
    }}
    .segmented {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 6px;
    }}
    .segmented-option input, .check-card input {{ position: absolute; opacity: 0; pointer-events: none; }}
    .segmented-option span, .check-card span {{
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 38px;
      border: 1px solid #bcccdc;
      border-radius: 6px;
      background: white;
      color: #334e68;
      font-weight: 700;
      text-align: center;
      padding: 8px;
    }}
    .segmented-option input:checked + span, .check-card input:checked + span {{
      border-color: var(--accent);
      background: #e7f2fb;
      color: var(--accent-strong);
    }}
    .stage-grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px;
    }}
    .actions {{
      position: sticky;
      top: 14px;
      display: grid;
      gap: 12px;
    }}
    button, .secondary-button {{
      border: 0;
      border-radius: 6px;
      padding: 11px 14px;
      font-size: 14px;
      font-weight: 700;
      cursor: pointer;
    }}
    button.primary {{
      background: var(--accent);
      color: white;
    }}
    .secondary-button {{
      display: inline-flex;
      justify-content: center;
      color: var(--accent-strong);
      background: var(--surface);
      text-decoration: none;
    }}
    .run-note {{
      color: var(--muted);
      margin: 0;
      font-size: 13px;
    }}
    .results-panel {{ margin-top: 18px; }}
    .empty-state {{
      display: grid;
      gap: 4px;
      padding: 14px;
      background: var(--surface);
      border: 1px dashed #9fb3c8;
      border-radius: 8px;
      margin-bottom: 14px;
    }}
    .empty-state span {{ color: var(--muted); }}
    .message, .error {{
      padding: 10px 12px;
      border-radius: 6px;
      margin-bottom: 12px;
      border: 1px solid #b6d7f0;
      background: #edf7ff;
      color: #174a7c;
    }}
    .error {{
      border-color: #f1b8b8;
      background: #fff1f0;
      color: var(--danger);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: white;
      overflow: hidden;
      border-radius: 6px;
    }}
    th, td {{
      padding: 9px 10px;
      border-bottom: 1px solid var(--border);
      text-align: left;
      vertical-align: top;
    }}
    th {{
      font-size: 12px;
      color: #52606d;
      background: #f7fafc;
      text-transform: uppercase;
    }}
    @media (max-width: 920px) {{
      form {{ grid-template-columns: 1fr; }}
      .actions {{ position: static; }}
      .grid, .grid.two, .stage-grid, .segmented {{ grid-template-columns: 1fr; }}
      .header-inner, .section-heading {{ align-items: start; flex-direction: column; }}
    }}
  </style>
</head>
<body>
  <header>
    <div class="header-inner">
      <div>
        <h1>{html.escape(t("app.title"))}</h1>
        <div class="subtitle">{html.escape(t("app.subtitle"))}</div>
      </div>
      <div class="badge">{html.escape(t("app.badge"))}</div>
    </div>
  </header>
  <main>
    <form id="scanner-form" method="post" action="/start" enctype="multipart/form-data">
      <div class="stack">
        <section class="panel" id="input">
          <div class="section-heading">
            <h2>{html.escape(t("section.input.title"))}</h2>
            <p>{html.escape(t("section.input.help"))}</p>
          </div>
          <div class="grid two">
            {_field("field.symbols_file", _input(values, "symbols_file"))}
            {_field("field.upload_csv", '<input id="uploaded-symbols-file" name="uploaded_symbols_file" type="file" accept=".csv,text/csv">')}
          </div>
          <div class="grid two">
            {_field("field.manual_symbols", f'<textarea name="manual_symbols" placeholder="NVDA, AAPL, MSFT">{html.escape(str(values.get("manual_symbols", "")))}</textarea>')}
            <div class="grid">
              {_field("field.max_symbols", _input(values, "max_symbols", "number", "1"))}
              {_field("field.output_file", _input(values, "output_file"))}
              {_field("field.html_output", _input(values, "html_output"))}
            </div>
          </div>
        </section>

        <section class="panel" id="filters">
          <div class="section-heading">
            <h2>{html.escape(t("section.filters.title"))}</h2>
          </div>
          <div class="grid">
            {_field("field.exchange", f'<select name="exchange" multiple>{exchange_options}</select>')}
            {_field("field.sector", f'<select name="sector" multiple>{sector_options}</select>')}
            {_field("field.industry", f'<select name="industry" multiple>{industry_options}</select>')}
          </div>
          <div class="field" style="margin-top: 12px;">
            <span>{html.escape(t("field.instrument_type"))}</span>
            <div class="segmented">{instrument_controls}</div>
          </div>
        </section>

        <section class="panel">
          <div class="section-heading">
            <h2>{html.escape(t("section.ranges.title"))}</h2>
          </div>
          <div class="grid">
            {_field("field.price_min", _input(values, "price_min", "number", "0.01"))}
            {_field("field.price_max", _input(values, "price_max", "number", "0.01"))}
            {_field("field.market_cap_min", _input(values, "market_cap_min", "number", "1"))}
            {_field("field.market_cap_max", _input(values, "market_cap_max", "number", "1"))}
            {_field("field.avg_volume_min", _input(values, "avg_volume_min", "number", "1"))}
            {_field("field.avg_volume_max", _input(values, "avg_volume_max", "number", "1"))}
          </div>
        </section>

        <section class="panel" id="parameters">
          <div class="section-heading">
            <h2>{html.escape(t("section.ta.title"))}</h2>
          </div>
          <div class="grid">
            {_field("field.rsi_min", _input(values, "rsi_min", "number", "0.01"))}
            {_field("field.rsi_max", _input(values, "rsi_max", "number", "0.01"))}
            {_field("field.adx_min", _input(values, "adx_min", "number", "0.01"))}
            {_field("field.adx_max", _input(values, "adx_max", "number", "0.01"))}
            {_field("field.bollinger_pct_min", _input(values, "bollinger_pct_min", "number", "0.01"))}
            {_field("field.bollinger_pct_max", _input(values, "bollinger_pct_max", "number", "0.01"))}
            {_field("field.crossover_freshness", _input(values, "crossover_freshness", "number", "1"))}
            {_field("field.divergence_lookback", _input(values, "divergence_lookback", "number", "1"))}
            {_field("field.divergence_recent_window", _input(values, "divergence_recent_window", "number", "1"))}
          </div>
        </section>

        <section class="panel" id="stages">
          <div class="section-heading">
            <h2>{html.escape(t("section.stages.title"))}</h2>
          </div>
          <div class="stage-grid">{stage_controls}</div>
        </section>

        {_results_panel(submitted)}
      </div>

      <aside class="actions">
        <section class="panel">
          <div class="field">
            <span>{html.escape(t("section.run.title"))}</span>
            <p class="run-note">{html.escape(t("section.run.help"))}</p>
          </div>
          <div style="display: grid; gap: 8px; margin-top: 14px;">
            <button id="run-button" class="primary" type="submit">{html.escape(t("button.run"))}</button>
            <a class="secondary-button" href="/">{html.escape(t("button.reset"))}</a>
          </div>
        </section>
      </aside>
    </form>
  </main>
  <script>
    const form = document.getElementById('scanner-form');
    const button = document.getElementById('run-button');
    const resultsPanel = document.getElementById('results');
    const symbolsFileInput = form.querySelector('[name="symbols_file"]');
    const uploadedSymbolsFile = document.getElementById('uploaded-symbols-file');
    let activePoll = null;

    function safeUploadName(filename) {{
      const base = filename.split(/[/\\\\]/).pop() || '';
      return base.replace(/[^A-Za-z0-9._-]/g, '_');
    }}

    uploadedSymbolsFile.addEventListener('change', () => {{
      const file = uploadedSymbolsFile.files && uploadedSymbolsFile.files[0];
      if (file) {{
        symbolsFileInput.value = 'uploads/' + safeUploadName(file.name);
      }}
    }});

    async function pollStatus(jobId) {{
      const response = await fetch('/status?job_id=' + encodeURIComponent(jobId));
      const body = await response.text();
      const currentResultsPanel = document.getElementById('results');
      currentResultsPanel.outerHTML = body;
      if (response.headers.get('X-Run-Done') === '1') {{
        if (activePoll) {{
          clearInterval(activePoll);
          activePoll = null;
        }}
        button.disabled = false;
        button.textContent = '{html.escape(t("button.run"))}';
      }}
    }}

    form.addEventListener('submit', async (event) => {{
      event.preventDefault();
      if (activePoll) {{
        clearInterval(activePoll);
        activePoll = null;
      }}
      button.disabled = true;
      button.textContent = 'Starting...';
      try {{
        const response = await fetch('/start', {{
          method: 'POST',
          body: new FormData(form)
        }});
        const data = await response.json();
        if (!response.ok) {{
          throw new Error(data.error || 'Unable to start scanner.');
        }}
        button.textContent = 'Running...';
        await pollStatus(data.job_id);
        activePoll = setInterval(() => pollStatus(data.job_id).catch((error) => {{
          const panel = document.getElementById('results');
          panel.insertAdjacentHTML('afterbegin', '<div class="error">Unable to refresh progress: ' + String(error) + '</div>');
        }}), {POLL_SECONDS * 1000});
      }} catch (error) {{
        const panel = document.getElementById('results');
        panel.insertAdjacentHTML('afterbegin', '<div class="error">Unable to run scanner: ' + String(error) + '</div>');
        button.disabled = false;
        button.textContent = '{html.escape(t("button.run"))}';
      }}
    }});
  </script>
</body>
</html>"""


class UnifiedScannerHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path.startswith("/status"):
            _, _, query = self.path.partition("?")
            job_id = _first(parse_qs(query), "job_id")
            job = _get_job(job_id)
            if not job:
                self._send_html(_render_results_panel(error="Run not found.", title=t("nav.results")), status=404, done=True)
                return
            self._send_html(
                _render_results_panel(
                    rows=job.get("rows", []),
                    message=job.get("message", ""),
                    error=job.get("error", ""),
                    title=t("nav.results"),
                ),
                done=bool(job.get("is_done")),
            )
            return
        self._send_html(_render_page())

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        values = _form_values(_parse_post(self.headers, raw))
        try:
            if self.path.startswith("/start"):
                job_id = _start_engine_job(values)
                self._send_json({"job_id": job_id})
                return
            rows, message = _run_engine(values)
            self._send_html(_render_page(values, submitted=True).replace(
                _results_panel(True),
                _render_results_panel(rows=rows, message=message, title=t("nav.results")),
            ))
        except ValueError as exc:
            if self.path.startswith("/start"):
                self._send_json({"error": str(exc)}, status=400)
                return
            self._send_html(_render_page(values, submitted=True).replace(
                _results_panel(True),
                _render_results_panel(error=str(exc), title=t("nav.results")),
            ), status=400)
        except Exception as exc:
            logging.exception("V2 web handler failed")
            if self.path.startswith("/start"):
                self._send_json({"error": str(exc)}, status=500)
                return
            self._send_html(_render_page(values, submitted=True).replace(
                _results_panel(True),
                _render_results_panel(error=str(exc), title=t("nav.results")),
            ), status=500)

    def log_message(self, format: str, *args: object) -> None:
        logging.info(format, *args)

    def _send_html(self, body: str, status: int = 200, done: bool | None = None) -> None:
        payload = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        if done is not None:
            self.send_header("X-Run-Done", "1" if done else "0")
        self.end_headers()
        self.wfile.write(payload)

    def _send_json(self, body: dict[str, object], status: int = 200) -> None:
        payload = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


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
    server = ThreadingHTTPServer((HOST, PORT), UnifiedScannerHandler)
    logging.info("%s running at http://%s:%s. Logs: %s", t("app.title"), HOST, PORT, log_path)
    server.serve_forever()


if __name__ == "__main__":
    main()
