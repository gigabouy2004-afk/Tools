import argparse
import csv
import hashlib
import json
import shutil
import statistics
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import ETF_Context_V8 as etf_context


DEFAULT_SAMPLE_STOCKS = ["NVDA", "AAPL", "MSFT", "TSLA", "AMZN"]
DEFAULT_OUTPUT_ROOT = Path("backtests") / "V8_ETF_Phase2" / "runs"
MAX_VALIDATION_STALENESS_DAYS = 60


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_value(*args):
    try:
        return subprocess.check_output(["git", *args], text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return "UNKNOWN"


def write_csv(records, path, fieldnames=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = []
        for record in records:
            for field in record:
                if field not in fieldnames:
                    fieldnames.append(field)
    with open(path, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)


def percentile(values, probability):
    values = sorted(float(value) for value in values)
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    position = (len(values) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    fraction = position - lower
    return values[lower] + (values[upper] - values[lower]) * fraction


def decode_json_value_after(page_html, marker):
    position = page_html.find(marker)
    if position < 0:
        raise etf_context.ETFProviderSchemaError(f"holdings page missing {marker}")
    value_start = position + len(marker)
    value, _ = json.JSONDecoder().raw_decode(page_html[value_start:])
    return value


def parse_holdings_validation_page(page_html):
    holdings = decode_json_value_after(page_html, '"top_holdings":')
    if not isinstance(holdings, list) or not holdings:
        raise etf_context.ETFProviderSchemaError("holdings page returned no top holdings")
    report_timestamp = decode_json_value_after(page_html, '"holding_report_date":')
    try:
        as_of_date = datetime.fromtimestamp(float(report_timestamp), tz=timezone.utc).date().isoformat()
    except (TypeError, ValueError, OSError):
        as_of_date = ""
    parsed = []
    for rank, holding in enumerate(holdings[:10], start=1):
        symbol = etf_context.normalize_ticker(str(holding.get("symbol", "")).split(":")[-1])
        parsed.append(
            {
                "Rank": rank,
                "Holding_Ticker": symbol,
                "Holding_Name": holding.get("name", ""),
                "Holding_Weight_Pct_Validation": holding.get("weight", ""),
            }
        )
    return parsed, as_of_date


def validate_mapping_against_holdings(stock_code, mapping, timeout_seconds):
    exchange = mapping["ETF_Exchange_Provider"]
    etf_ticker = mapping["ETF_Ticker"]
    url = f"https://www.tradingview.com/symbols/{exchange}-{etf_ticker}/holdings/"
    response = etf_context.fetch_source_page(url, timeout_seconds)
    top_holdings, as_of_date = parse_holdings_validation_page(response["Body"])
    match = next((holding for holding in top_holdings if holding["Holding_Ticker"] == stock_code), None)
    try:
        freshness_age_days = (datetime.now(timezone.utc).date() - datetime.fromisoformat(as_of_date).date()).days
    except (TypeError, ValueError):
        freshness_age_days = None
    freshness_pass = freshness_age_days is not None and freshness_age_days <= MAX_VALIDATION_STALENESS_DAYS
    validation_pass = bool(match) and freshness_pass
    return {
        "Validation_URL": url,
        "Validation_HTTP_Status": response["HTTP_Status"],
        "Validation_Latency_Ms": response["Latency_Ms"],
        "Validation_HTML_SHA256": response["Body_SHA256"],
        "Validation_As_Of_Date": as_of_date,
        "Validation_Freshness_Age_Days": freshness_age_days if freshness_age_days is not None else "",
        "Validation_Freshness_Max_Days": MAX_VALIDATION_STALENESS_DAYS,
        "Validation_Freshness_Pass": freshness_pass,
        "Validation_Top10_Match": bool(match),
        "Validation_Rank": match["Rank"] if match else "",
        "Validation_Weight_Pct": match["Holding_Weight_Pct_Validation"] if match else "",
        "Validation_Status": "PASS" if validation_pass else "FAIL",
    }


def write_checksums(run_dir):
    checksum_path = run_dir / "checksums.sha256"
    lines = []
    for path in sorted(run_dir.rglob("*")):
        if not path.is_file() or path == checksum_path:
            continue
        lines.append(f"{sha256_file(path)}  {path.relative_to(run_dir).as_posix()}")
    checksum_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(lines)


def parse_args():
    parser = argparse.ArgumentParser(description="V8 Phase-2 direct ETF mapping quality backtest")
    parser.add_argument("--stocks", nargs="+", default=DEFAULT_SAMPLE_STOCKS)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--timeout-seconds", type=float, default=etf_context.DEFAULT_TIMEOUT_SECONDS)
    return parser.parse_args()


def main():
    args = parse_args()
    stocks = list(dict.fromkeys(etf_context.normalize_ticker(value) for value in args.stocks if value))
    started = datetime.now(timezone.utc)
    commit = git_value("rev-parse", "--short", "HEAD")
    run_id = f"V8ETF_{started.strftime('%Y%m%dT%H%M%SZ')}_{commit}"
    run_dir = args.output_root.resolve() / run_id
    inputs_dir = run_dir / "inputs"
    outputs_dir = run_dir / "outputs"
    source_dir = inputs_dir / "source_snapshot"
    (source_dir / "config").mkdir(parents=True, exist_ok=True)
    outputs_dir.mkdir(parents=True, exist_ok=True)

    source_files = [
        Path(etf_context.__file__),
        Path(__file__),
        Path(__file__).resolve().parent / "Momentum_Detector_V8.py",
        Path(__file__).resolve().parent / "tests" / "test_etf_context_v8.py",
    ]
    for source_file in source_files:
        shutil.copy2(source_file, source_dir / source_file.name)
    shutil.copy2(
        etf_context.DEFAULT_MESSAGE_MAP,
        source_dir / "config" / etf_context.DEFAULT_MESSAGE_MAP.name,
    )
    shutil.copy2(etf_context.DEFAULT_STOCK_MASTER_PATH, inputs_dir / "stock_master_snapshot.csv")
    shutil.copy2(etf_context.DEFAULT_US_ETF_MASTER_PATH, inputs_dir / "us_etf_master_snapshot.csv")

    stock_rows = []
    mapping_rows = []
    production_latencies = []
    validation_latencies = []
    production_request_count = 0
    validation_request_count = 0

    for stock in stocks:
        print(f"Testing direct stock-to-ETF mapping for {stock}...")
        context = etf_context.get_etf_mapping_context(
            stock,
            stock_master_path=inputs_dir / "stock_master_snapshot.csv",
            etf_master_path=inputs_dir / "us_etf_master_snapshot.csv",
            timeout_seconds=args.timeout_seconds,
            use_cache=False,
        )
        production_request_count += 1
        if context.get("Latency_Ms") not in ("", None):
            production_latencies.append(float(context["Latency_Ms"]))
        validations = []
        for mapping in context.get("Mappings", []):
            validation_request_count += 1
            try:
                validation = validate_mapping_against_holdings(stock, mapping, args.timeout_seconds)
            except Exception as exc:
                validation = {
                    "Validation_URL": "",
                    "Validation_HTTP_Status": "",
                    "Validation_Latency_Ms": "",
                    "Validation_HTML_SHA256": "",
                    "Validation_As_Of_Date": "",
                    "Validation_Freshness_Age_Days": "",
                    "Validation_Freshness_Max_Days": MAX_VALIDATION_STALENESS_DAYS,
                    "Validation_Freshness_Pass": False,
                    "Validation_Top10_Match": False,
                    "Validation_Rank": "",
                    "Validation_Weight_Pct": "",
                    "Validation_Status": f"ERROR: {exc}",
                }
            if validation.get("Validation_Latency_Ms") not in ("", None):
                validation_latencies.append(float(validation["Validation_Latency_Ms"]))
            validations.append(validation)
            mapping_rows.append(
                {
                    "Stock_Code": stock,
                    "Provider": context["Provider"],
                    "Source_URL": context["Source_URL"],
                    "ETF_Ticker": mapping["ETF_Ticker"],
                    "ETF_Name": mapping["ETF_Name"],
                    "ETF_Exchange_Provider": mapping["ETF_Exchange_Provider"],
                    "Listing_Exchange_Local": mapping["Listing_Exchange_Local"],
                    "Holding_Weight_Pct_Direct": mapping["Holding_Weight_Pct"],
                    "Top10_Evidence": mapping["Top10_Evidence"],
                    "Top10_Proof_Threshold_Pct": mapping["Top10_Proof_Threshold_Pct"],
                    **validation,
                }
            )

        stock_rows.append(
            {
                "Stock_Code": stock,
                "ETF_Status": context["ETF_Status"],
                "Source_URL": context["Source_URL"],
                "HTTP_Status": context["HTTP_Status"],
                "Production_Latency_Ms": context["Latency_Ms"],
                "Source_HTML_SHA256": context["Source_HTML_SHA256"],
                "Raw_Candidate_Count": context["Raw_Candidate_Count"],
                "Eligible_Top10_Before_Limit_Count": context["Eligible_Top10_Before_Limit_Count"],
                "Verified_Top10_Count": context["Verified_Top10_Count"],
                "Rejected_Candidate_Count": context["Rejected_Candidate_Count"],
                "Mapped_ETFs": etf_context.format_mapped_etf_codes(context),
                "Holdings_Validation_Count": len(validations),
                "Holdings_Validation_Pass_Count": sum(
                    validation.get("Validation_Status") == "PASS" for validation in validations
                ),
                "All_Returned_Mappings_Validated": bool(validations)
                and all(validation.get("Validation_Status") == "PASS" for validation in validations),
            }
        )

    write_csv(stock_rows, outputs_dir / "five_stock_api_quality_summary.csv")
    write_csv(mapping_rows, outputs_dir / "verified_mapping_detail.csv")
    failures = [row for row in mapping_rows if row["Validation_Status"] != "PASS"]
    completed = datetime.now(timezone.utc)
    manifest = {
        "Run_ID": run_id,
        "Started_UTC": started.isoformat(),
        "Completed_UTC": completed.isoformat(),
        "Purpose": "V8 ETF Phases 2A-2C direct mapping API/data-quality backtest",
        "Sample_Stocks": stocks,
        "Provider": etf_context.PROVIDER_NAME,
        "Provider_Mode": "ONE_DIRECT_STOCK_PAGE_PER_PRODUCTION_LOOKUP",
        "Top10_Proof": {
            "Method": "WEIGHT_GT_100_DIV_11_NON_LEVERAGED_US_ETF",
            "Threshold_Pct": etf_context.TOP10_GUARANTEE_MIN_WEIGHT_PCT,
            "Conservative": True,
        },
        "Validation_Max_Staleness_Days": MAX_VALIDATION_STALENESS_DAYS,
        "Production_Request_Count": production_request_count,
        "Production_Per_Stock": production_request_count / len(stocks) if stocks else 0,
        "Validation_Request_Count": validation_request_count,
        "Validation_Requests_Are_Production_Reachable": False,
        "Returned_Mapping_Count": len(mapping_rows),
        "Validation_Pass_Count": len(mapping_rows) - len(failures),
        "Validation_Failure_Count": len(failures),
        "Production_Latency_Ms": {
            "Median": statistics.median(production_latencies) if production_latencies else None,
            "P95": percentile(production_latencies, 0.95),
            "Maximum": max(production_latencies) if production_latencies else None,
        },
        "Validation_Latency_Ms": {
            "Median": statistics.median(validation_latencies) if validation_latencies else None,
            "P95": percentile(validation_latencies, 0.95),
        },
        "Git_Commit": git_value("rev-parse", "HEAD"),
        "Git_Worktree_Dirty": bool(git_value("status", "--porcelain")),
        "Python": sys.version,
        "Source_Hashes": {
            "ETF_Context_V8.py": sha256_file(Path(etf_context.__file__)),
            "Momentum_Detector_V8.py": sha256_file(Path(__file__).resolve().parent / "Momentum_Detector_V8.py"),
            "Message_Map": sha256_file(etf_context.DEFAULT_MESSAGE_MAP),
        },
        "Known_Limitations": [
            "The selected source is a public TradingView stock-to-funds page, not a documented developer API contract.",
            "Only the first 100 direct exposure rows rendered by the source are available.",
            "The conservative proof omits valid top-ten holdings at or below 100/11 percent rather than guessing rank.",
            "The provider's reverse page does not publish a holdings as-of date; the separate validation page does.",
            "Validation holdings-page requests are test-only and are not reachable from Momentum_Detector_V8.py.",
        ],
    }
    (run_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    checksum_count = write_checksums(run_dir)
    print(f"Run complete: {run_dir}")
    print(
        f"Production requests: {production_request_count} | Returned mappings: {len(mapping_rows)} | "
        f"Validation failures: {len(failures)} | Hashed artifacts: {checksum_count}"
    )
    return 0 if not failures and len(mapping_rows) > 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
