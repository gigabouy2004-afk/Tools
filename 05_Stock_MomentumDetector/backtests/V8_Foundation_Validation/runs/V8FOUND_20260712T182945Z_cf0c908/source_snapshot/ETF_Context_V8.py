import csv
import hashlib
import html
import json
import math
import os
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

import pandas as pd


PROVIDER_NAME = "TRADINGVIEW_PUBLIC_STOCK_ETF_PAGE"
PROVIDER_VERSION = "1"
TRADINGVIEW_URL_TEMPLATE = "https://www.tradingview.com/symbols/{exchange}-{ticker}/etfs/"
DEFAULT_STOCK_MASTER_PATH = Path("D:/Tools/StockCodeMaster/02_Stock/01-07-US_Common_Stocks_Master_Library.csv")
DEFAULT_US_ETF_MASTER_PATH = Path("D:/Tools/StockCodeMaster/03_ETF/01-07-US_ETF_Master_Library.csv")
DEFAULT_MESSAGE_MAP = Path(__file__).resolve().parent / "config" / "V8_Post_Processor_Message_Map.csv"
DEFAULT_CACHE_PATH = Path("D:/Tools/Stock_MomentumDetector/Processed_Data/V8_ETF_Mapping_Cache.json")
DEFAULT_CACHE_TTL_HOURS = 24
DEFAULT_TIMEOUT_SECONDS = 8.0
DEFAULT_MAX_MAPPINGS = 3

# If a non-leveraged portfolio has non-negative weights summing to 100%, a
# holding above 100/11 percent cannot have ten larger holdings ahead of it.
TOP10_GUARANTEE_MIN_WEIGHT_PCT = 100.0 / 11.0

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) V8MomentumETFMapper/1.0"
LEVERAGED_OR_INVERSE_PATTERN = re.compile(
    r"(?:\b(?:leveraged|inverse|ultra|bear|short)\b|(?:^|\W)[+-]?[23]x(?:\W|$))",
    re.IGNORECASE,
)
ROW_PATTERN = re.compile(
    r'<tr[^>]*data-rowkey="([^:"]+):([^"]+)"[^>]*>(.*?)</tr>',
    re.IGNORECASE | re.DOTALL,
)
CELL_PATTERN = re.compile(r"<td[^>]*>(.*?)</td>", re.IGNORECASE | re.DOTALL)
TAG_PATTERN = re.compile(r"<[^>]+>")


class ETFProviderError(RuntimeError):
    pass


class ETFProviderSchemaError(ETFProviderError):
    pass


def utc_now():
    return datetime.now(timezone.utc)


def normalize_ticker(value):
    return str(value or "").strip().upper()


def _clean_text(value):
    return " ".join(html.unescape(TAG_PATTERN.sub(" ", str(value or ""))).split())


def _parse_weight(value):
    text = _clean_text(value).replace("%", "").replace(",", "").strip()
    try:
        number = float(text)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number >= 0 else None


def _map_stock_exchange(value):
    exchange = str(value or "").strip().upper()
    if "NASDAQ" in exchange:
        return "NASDAQ"
    if "ARCA" in exchange or "AMEX" in exchange or "NYSE MKT" in exchange:
        return "AMEX"
    if "NYSE" in exchange:
        return "NYSE"
    if "CBOE" in exchange or "BATS" in exchange:
        return "CBOE"
    return ""


@lru_cache(maxsize=8)
def load_stock_exchange_map(stock_master_path=str(DEFAULT_STOCK_MASTER_PATH)):
    path = Path(stock_master_path)
    if not path.is_file():
        return {}
    frame = pd.read_csv(path, dtype=str).fillna("")
    ticker_column = "Ticker" if "Ticker" in frame.columns else "Symbol"
    exchange_column = "Listing Exchange" if "Listing Exchange" in frame.columns else None
    if not exchange_column:
        return {}
    return {
        normalize_ticker(row[ticker_column]): _map_stock_exchange(row[exchange_column])
        for _, row in frame.iterrows()
        if normalize_ticker(row[ticker_column])
    }


@lru_cache(maxsize=8)
def load_us_etf_metadata(etf_master_path=str(DEFAULT_US_ETF_MASTER_PATH)):
    path = Path(etf_master_path)
    if not path.is_file():
        return {}
    frame = pd.read_csv(path, dtype=str).fillna("")
    ticker_column = "Ticker" if "Ticker" in frame.columns else "Symbol"
    metadata = {}
    for _, row in frame.iterrows():
        ticker = normalize_ticker(row.get(ticker_column, ""))
        if not ticker:
            continue
        searchable = " | ".join(
            str(row.get(column, ""))
            for column in ("Security Name", "Strategy", "Theme", "Category Flags")
        )
        metadata[ticker] = {
            "ETF_Name_Local": str(row.get("Security Name", "")).strip(),
            "Listing_Exchange_Local": str(row.get("Listing Exchange", "")).strip(),
            "Leveraged_Or_Inverse": bool(LEVERAGED_OR_INVERSE_PATTERN.search(searchable)),
        }
    return metadata


def build_source_url(stock_code, stock_exchange=None, stock_master_path=DEFAULT_STOCK_MASTER_PATH):
    ticker = normalize_ticker(stock_code)
    exchange = normalize_ticker(stock_exchange)
    if not exchange:
        exchange = load_stock_exchange_map(str(Path(stock_master_path).resolve())).get(ticker, "")
    if not ticker:
        raise ETFProviderError("stock code is empty")
    if not exchange:
        raise ETFProviderError(f"listing exchange unavailable for {ticker}")
    return TRADINGVIEW_URL_TEMPLATE.format(exchange=exchange, ticker=ticker), exchange


def fetch_source_page(url, timeout_seconds=DEFAULT_TIMEOUT_SECONDS):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=float(timeout_seconds)) as response:
            body = response.read().decode("utf-8", errors="replace")
            status_code = int(getattr(response, "status", 200))
            last_modified = response.headers.get("Last-Modified", "")
    except urllib.error.HTTPError as exc:
        raise ETFProviderError(f"provider HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise ETFProviderError(f"provider request failed: {exc.reason}") from exc
    except TimeoutError as exc:
        raise ETFProviderError("provider request timed out") from exc
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    if status_code != 200:
        raise ETFProviderError(f"provider HTTP {status_code}")
    if not body:
        raise ETFProviderSchemaError("provider returned an empty page")
    return {
        "Body": body,
        "HTTP_Status": status_code,
        "Latency_Ms": elapsed_ms,
        "Last_Modified": last_modified,
        "Body_SHA256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
    }


def parse_direct_exposure_rows(page_html):
    rows = []
    for match in ROW_PATTERN.finditer(page_html or ""):
        exchange, ticker, row_html = match.groups()
        cells = CELL_PATTERN.findall(row_html)
        if len(cells) < 3:
            continue
        weight = _parse_weight(cells[2])
        if weight is None:
            continue
        name_match = re.search(
            r'class="[^"]*tickerDescription[^"]*"[^>]*>(.*?)</a>',
            cells[0],
            re.IGNORECASE | re.DOTALL,
        )
        rows.append(
            {
                "ETF_Ticker": normalize_ticker(ticker),
                "ETF_Name": _clean_text(name_match.group(1)) if name_match else "",
                "ETF_Exchange_Provider": normalize_ticker(exchange),
                "Holding_Weight_Pct": weight,
            }
        )
    if not rows:
        raise ETFProviderSchemaError("provider page contained no parseable ETF exposure rows")
    return rows


def filter_verified_top10_mappings(
    exposure_rows,
    etf_master_path=DEFAULT_US_ETF_MASTER_PATH,
    max_mappings=DEFAULT_MAX_MAPPINGS,
):
    metadata = load_us_etf_metadata(str(Path(etf_master_path).resolve()))
    if not metadata:
        raise ETFProviderError("local US ETF master is unavailable or empty")

    accepted = []
    rejected = []
    for row in exposure_rows:
        ticker = normalize_ticker(row.get("ETF_Ticker"))
        weight = _parse_weight(row.get("Holding_Weight_Pct"))
        local = metadata.get(ticker)
        rejection_reason = ""
        if local is None:
            rejection_reason = "NOT_IN_LOCAL_US_ETF_MASTER"
        elif local["Leveraged_Or_Inverse"]:
            rejection_reason = "LEVERAGED_OR_INVERSE_EXCLUDED"
        elif weight is None or weight <= TOP10_GUARANTEE_MIN_WEIGHT_PCT:
            rejection_reason = "TOP10_NOT_PROVEN_BY_CONSERVATIVE_WEIGHT_TEST"

        record = {
            **row,
            "ETF_Ticker": ticker,
            "Holding_Weight_Pct": weight,
            "ETF_Name": row.get("ETF_Name") or (local or {}).get("ETF_Name_Local", ""),
            "Listing_Exchange_Local": (local or {}).get("Listing_Exchange_Local", ""),
        }
        if rejection_reason:
            record["Eligibility_Status"] = "EXCLUDED"
            record["Eligibility_Reason"] = rejection_reason
            rejected.append(record)
            continue

        record.update(
            {
                "Eligibility_Status": "VERIFIED_TOP10",
                "Eligibility_Reason": "",
                "Top10_Evidence": "WEIGHT_GT_100_DIV_11_NON_LEVERAGED_US_ETF",
                "Top10_Proof_Threshold_Pct": TOP10_GUARANTEE_MIN_WEIGHT_PCT,
            }
        )
        accepted.append(record)

    accepted.sort(key=lambda item: (-item["Holding_Weight_Pct"], item["ETF_Ticker"]))
    selected = accepted[: int(max_mappings)]
    for record in accepted[int(max_mappings) :]:
        overflow = dict(record)
        overflow["Eligibility_Status"] = "EXCLUDED"
        overflow["Eligibility_Reason"] = "OMITTED_BY_TOP3_LIMIT"
        rejected.append(overflow)
    rejected.sort(
        key=lambda item: (
            -(item["Holding_Weight_Pct"] if item["Holding_Weight_Pct"] is not None else -1),
            item["ETF_Ticker"],
        )
    )
    return selected, rejected


def empty_context(stock_code, status, detail=""):
    return {
        "Stock_Code": normalize_ticker(stock_code),
        "ETF_Status": status,
        "ETF_Status_Detail": detail,
        "ETF_Message_Rule_Code": "ETF_API_UNAVAILABLE",
        "Provider": PROVIDER_NAME,
        "Provider_Version": PROVIDER_VERSION,
        "Source_URL": "",
        "Stock_Exchange": "",
        "Retrieved_At": utc_now().isoformat(),
        "Provider_Data_As_Of": "",
        "Cache_Hit": False,
        "HTTP_Status": "",
        "Latency_Ms": "",
        "Source_HTML_SHA256": "",
        "Raw_Candidate_Count": 0,
        "Eligible_Top10_Before_Limit_Count": 0,
        "Verified_Top10_Count": 0,
        "Rejected_Candidate_Count": 0,
        "Mappings": [],
        "Rejected_Mappings": [],
    }


def _read_cache(cache_path):
    path = Path(cache_path)
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def _write_cache(cache_path, cache):
    path = Path(cache_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(cache, indent=2), encoding="utf-8")
    os.replace(temporary, path)


def _cache_entry_is_fresh(entry, now):
    try:
        expires_at = datetime.fromisoformat(entry["Expires_At"])
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return expires_at > now
    except (KeyError, TypeError, ValueError):
        return False


def get_etf_mapping_context(
    stock_code,
    stock_exchange=None,
    stock_master_path=DEFAULT_STOCK_MASTER_PATH,
    etf_master_path=DEFAULT_US_ETF_MASTER_PATH,
    cache_path=DEFAULT_CACHE_PATH,
    cache_ttl_hours=DEFAULT_CACHE_TTL_HOURS,
    timeout_seconds=DEFAULT_TIMEOUT_SECONDS,
    max_mappings=DEFAULT_MAX_MAPPINGS,
    use_cache=True,
    fetcher=fetch_source_page,
):
    ticker = normalize_ticker(stock_code)
    now = utc_now()
    cache_key = f"{PROVIDER_NAME}:{ticker}"
    if use_cache:
        cache = _read_cache(cache_path)
        entry = cache.get(cache_key, {})
        if _cache_entry_is_fresh(entry, now) and isinstance(entry.get("Context"), dict):
            context = dict(entry["Context"])
            context["Cache_Hit"] = True
            return context

    try:
        source_url, resolved_exchange = build_source_url(ticker, stock_exchange, stock_master_path)
        response = fetcher(source_url, timeout_seconds)
        exposure_rows = parse_direct_exposure_rows(response["Body"])
        accepted, rejected = filter_verified_top10_mappings(
            exposure_rows,
            etf_master_path=etf_master_path,
            max_mappings=max_mappings,
        )
        status = "OK" if accepted else "NO_VERIFIED_TOP10_MAPPING"
        rule_code = "ETF_TOP10_MAPPED" if accepted else "ETF_NO_TOP10_MAPPING"
        context = {
            "Stock_Code": ticker,
            "ETF_Status": status,
            "ETF_Status_Detail": "" if accepted else "no conservative top-ten mapping passed",
            "ETF_Message_Rule_Code": rule_code,
            "Provider": PROVIDER_NAME,
            "Provider_Version": PROVIDER_VERSION,
            "Source_URL": source_url,
            "Stock_Exchange": resolved_exchange,
            "Retrieved_At": now.isoformat(),
            "Provider_Data_As_Of": response.get("Last_Modified", ""),
            "Cache_Hit": False,
            "HTTP_Status": response.get("HTTP_Status", ""),
            "Latency_Ms": response.get("Latency_Ms", ""),
            "Source_HTML_SHA256": response.get("Body_SHA256", ""),
            "Raw_Candidate_Count": len(exposure_rows),
            "Eligible_Top10_Before_Limit_Count": len(accepted)
            + sum(item.get("Eligibility_Reason") == "OMITTED_BY_TOP3_LIMIT" for item in rejected),
            "Verified_Top10_Count": len(accepted),
            "Rejected_Candidate_Count": len(rejected),
            "Mappings": accepted,
            "Rejected_Mappings": rejected,
        }
        if use_cache:
            cache = _read_cache(cache_path)
            cache[cache_key] = {
                "Expires_At": (now + timedelta(hours=float(cache_ttl_hours))).isoformat(),
                "Context": context,
            }
            _write_cache(cache_path, cache)
        return context
    except Exception as exc:
        context = empty_context(ticker, "UNAVAILABLE", str(exc))
        if isinstance(exc, ETFProviderSchemaError):
            context["ETF_Status"] = "SCHEMA_ERROR"
            context["ETF_Message_Rule_Code"] = "ETF_MAPPING_PARTIAL"
        return context


@lru_cache(maxsize=8)
def load_message_templates(message_map_path=str(DEFAULT_MESSAGE_MAP)):
    templates = {}
    with open(message_map_path, "r", encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file):
            if str(row.get("Enabled", "")).strip().upper() not in {"1", "TRUE", "YES", "Y"}:
                continue
            rule_code = str(row.get("Rule_Code", "")).strip()
            if rule_code:
                templates[rule_code] = str(row.get("Template", "")).strip()
    return templates


def format_mapped_etf_codes(context):
    values = []
    for mapping in (context or {}).get("Mappings", []):
        weight = mapping.get("Holding_Weight_Pct")
        if weight is None:
            values.append(mapping["ETF_Ticker"])
        else:
            values.append(f"{mapping['ETF_Ticker']} {float(weight):.2f}%")
    return "; ".join(values)


def build_etf_message(context, message_map_path=DEFAULT_MESSAGE_MAP):
    templates = load_message_templates(str(Path(message_map_path).resolve()))
    rule_code = (context or {}).get("ETF_Message_Rule_Code", "ETF_API_UNAVAILABLE")
    template = templates.get(rule_code) or templates.get("ETF_API_UNAVAILABLE")
    if not template:
        return "Active momentum confirmed. ETF mapping context unavailable; Score is unchanged."
    values = {
        "ticker": (context or {}).get("Stock_Code", ""),
        "mapped_etf_codes": format_mapped_etf_codes(context),
        "status_detail": (context or {}).get("ETF_Status_Detail", "mapping unavailable"),
        "provider": (context or {}).get("Provider", PROVIDER_NAME),
    }
    return template.format_map(values)


def is_etf_postprocessor_eligible(output, active_threshold):
    try:
        score = float((output or {}).get("Score"))
    except (TypeError, ValueError):
        return False
    return (
        (output or {}).get("Final_Decision") == "MOMENTUM_ACTIVE"
        and math.isfinite(score)
        and score >= float(active_threshold)
    )


def apply_etf_postprocessor(
    output,
    active_threshold,
    stock_exchange=None,
    message_map_path=DEFAULT_MESSAGE_MAP,
    **lookup_options,
):
    if not is_etf_postprocessor_eligible(output, active_threshold):
        return None
    context = get_etf_mapping_context(
        output.get("Ticker", ""),
        stock_exchange=stock_exchange,
        **lookup_options,
    )
    output["Score_Message"] = build_etf_message(context, message_map_path)
    return context


def getETFMappedCodes(stock_code, **lookup_options):
    return format_mapped_etf_codes(get_etf_mapping_context(stock_code, **lookup_options))
