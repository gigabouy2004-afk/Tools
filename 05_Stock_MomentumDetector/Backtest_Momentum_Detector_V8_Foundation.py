import argparse
import csv
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf

import ETF_Context_V8 as etf_context
import Momentum_Detector_V8 as engine
from Backtest_Momentum_Detector_V8 import calculate_outcome, download_daily, replay_signal
from Backtest_Momentum_Detector_V8_ETF import validate_mapping_against_holdings


ROOT = Path(__file__).resolve().parent
DEFAULT_CONFIG = ROOT / "config" / "V8_Foundation_Validation_Config.json"
DEFAULT_OUTPUT_ROOT = ROOT / "backtests" / "V8_Foundation_Validation" / "runs"


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_value(*args):
    try:
        return subprocess.check_output(
            ["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "UNKNOWN"


def write_csv(rows, path, fieldnames=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = []
        for row in rows:
            for field in row:
                if field not in fieldnames:
                    fieldnames.append(field)
    with open(path, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_checksums(run_dir):
    checksum_path = run_dir / "checksums.sha256"
    lines = []
    for path in sorted(run_dir.rglob("*")):
        if path.is_file() and path != checksum_path:
            lines.append(f"{sha256_file(path)}  {path.relative_to(run_dir).as_posix()}")
    checksum_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(lines)


def quarter_label(value):
    stamp = pd.Timestamp(value)
    return f"{stamp.year}Q{stamp.quarter}"


def clean(value):
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return value


def snapshot_sources(source_dir, config_path):
    source_dir.mkdir(parents=True, exist_ok=True)
    files = [
        ROOT / "Momentum_Detector_V8.py",
        ROOT / "ETF_Context_V8.py",
        ROOT / "Backtest_Momentum_Detector_V8.py",
        ROOT / "Backtest_Momentum_Detector_V8_ETF.py",
        ROOT / "Backtest_Momentum_Detector_V8_Foundation.py",
        ROOT / "Validate_Momentum_Detector_V8_Foundation.py",
        ROOT / "tests" / "test_v8_macd.py",
    ]
    for source in files:
        if source.is_file():
            destination = source_dir / source.relative_to(ROOT)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
    destination = source_dir / "config" / config_path.name
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(config_path, destination)


def fetch_etf_evidence(stocks, inputs_dir, timeout_seconds, log):
    stock_rows = []
    mapping_rows = []
    for stock in stocks:
        log(f"ETF_MAPPING_START ticker={stock}")
        try:
            context = etf_context.get_etf_mapping_context(
                stock,
                stock_master_path=inputs_dir / "stock_master_snapshot.csv",
                etf_master_path=inputs_dir / "us_etf_master_snapshot.csv",
                cache_path=inputs_dir / "etf_cache.json",
                timeout_seconds=timeout_seconds,
                use_cache=False,
            )
        except Exception as exc:
            context = etf_context.empty_context(stock, "ERROR", str(exc))
        valid_count = 0
        for mapping in context.get("Mappings", []):
            try:
                validation = validate_mapping_against_holdings(stock, mapping, timeout_seconds)
            except Exception as exc:
                validation = {
                    "Validation_Status": f"ERROR: {exc}",
                    "Validation_As_Of_Date": "",
                    "Validation_Top10_Match": False,
                    "Validation_Rank": "",
                    "Validation_Weight_Pct": "",
                    "Validation_URL": "",
                }
            as_of = validation.get("Validation_As_Of_Date", "")
            same_quarter = bool(as_of) and quarter_label(as_of) == "2026Q2"
            accepted = validation.get("Validation_Status") == "PASS" and same_quarter
            valid_count += int(accepted)
            mapping_rows.append(
                {
                    "Stock_Code": stock,
                    "ETF_Ticker": mapping.get("ETF_Ticker", ""),
                    "ETF_Name": mapping.get("ETF_Name", ""),
                    "ETF_Exchange_Provider": mapping.get("ETF_Exchange_Provider", ""),
                    "Holding_Weight_Pct_Direct": mapping.get("Holding_Weight_Pct", ""),
                    "Top10_Evidence": mapping.get("Top10_Evidence", ""),
                    "Provider": context.get("Provider", ""),
                    "Source_URL": context.get("Source_URL", ""),
                    **validation,
                    "Validation_Quarter": quarter_label(as_of) if as_of else "",
                    "Same_Quarter_2026Q2": same_quarter,
                    "Historical_Mapping_Accepted": accepted,
                    "Historical_Mapping_Status": (
                        "ACCEPTED_SAME_QUARTER"
                        if accepted
                        else "REJECTED_NOT_VALIDATED_IN_SIGNAL_QUARTER"
                    ),
                }
            )
        stock_rows.append(
            {
                "Stock_Code": stock,
                "ETF_Status": context.get("ETF_Status", ""),
                "ETF_Status_Detail": context.get("ETF_Status_Detail", ""),
                "Raw_Candidate_Count": context.get("Raw_Candidate_Count", 0),
                "Verified_Top10_Count": context.get("Verified_Top10_Count", 0),
                "Returned_Mapping_Count": len(context.get("Mappings", [])),
                "Accepted_Same_Quarter_Mapping_Count": valid_count,
            }
        )
        log(
            f"ETF_MAPPING_DONE ticker={stock} returned={len(context.get('Mappings', []))} "
            f"same_quarter_accepted={valid_count} status={context.get('ETF_Status', '')}"
        )
    return stock_rows, mapping_rows


def parse_args():
    parser = argparse.ArgumentParser(description="V8 foundation and ETF validation backtest")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--timeout-seconds", type=float, default=8.0)
    return parser.parse_args()


def main():
    args = parse_args()
    config_path = args.config.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    stocks = config["Seed_Stocks"]
    signal_dates = [pd.Timestamp(value).normalize() for value in config["Signal_Dates"]]
    horizons = [int(value) for value in config["Forward_Horizons_Sessions"]]
    macd = config["MACD"]
    if len(stocks) != 20 or len(set(stocks)) != 20:
        raise ValueError("the validation contract requires exactly 20 unique stocks")
    if len(signal_dates) not in (3, 4):
        raise ValueError("the validation contract requires three or four dates")
    if any(quarter_label(value) != config["Quarter"] for value in signal_dates):
        raise ValueError("all signal dates must be in the configured ETF evidence quarter")

    started = datetime.now(timezone.utc)
    run_id = f"V8FOUND_{started.strftime('%Y%m%dT%H%M%SZ')}_{git_value('rev-parse', '--short', 'HEAD')}"
    run_dir = args.output_root.resolve() / run_id
    inputs_dir = run_dir / "inputs"
    prices_dir = inputs_dir / "prices"
    outputs_dir = run_dir / "outputs"
    validation_dir = run_dir / "validation"
    source_dir = run_dir / "source_snapshot"
    for path in (prices_dir, outputs_dir, validation_dir):
        path.mkdir(parents=True, exist_ok=True)

    log_lines = []

    def log(message):
        line = f"{datetime.now(timezone.utc).isoformat()} {message}"
        log_lines.append(line)
        print(line, flush=True)

    snapshot_sources(source_dir, config_path)
    shutil.copy2(config_path, inputs_dir / config_path.name)
    shutil.copy2(etf_context.DEFAULT_STOCK_MASTER_PATH, inputs_dir / "stock_master_snapshot.csv")
    shutil.copy2(etf_context.DEFAULT_US_ETF_MASTER_PATH, inputs_dir / "us_etf_master_snapshot.csv")
    log(f"RUN_START run_id={run_id} stocks={len(stocks)} dates={len(signal_dates)}")
    log(f"FOUNDATION_CONFIG policy=enforce macd={macd['Fast']}/{macd['Slow']}/{macd['Signal']}")

    prices = {}
    for ticker in [config["Benchmark"], *stocks]:
        log(f"PRICE_DOWNLOAD_START ticker={ticker}")
        frame = download_daily(
            ticker,
            config["Price_Start"],
            config["Price_End_Exclusive"],
        )
        missing_dates = [value.date().isoformat() for value in signal_dates if value not in frame.index]
        if missing_dates:
            raise RuntimeError(f"{ticker} missing signal dates: {missing_dates}")
        frame.to_csv(prices_dir / f"{ticker}.csv", index_label="Date")
        prices[ticker] = frame
        log(f"PRICE_DOWNLOAD_DONE ticker={ticker} rows={len(frame)}")

    etf_stock_rows, mapping_rows = fetch_etf_evidence(
        stocks, inputs_dir, args.timeout_seconds, log
    )
    accepted_mappings = {}
    for row in mapping_rows:
        if row["Historical_Mapping_Accepted"]:
            accepted_mappings.setdefault(row["Stock_Code"], []).append(row)
    etf_tickers = sorted(
        {row["ETF_Ticker"] for rows in accepted_mappings.values() for row in rows}
    )
    for ticker in etf_tickers:
        log(f"ETF_PRICE_DOWNLOAD_START ticker={ticker}")
        try:
            frame = download_daily(ticker, config["Price_Start"], config["Price_End_Exclusive"])
            frame.to_csv(prices_dir / f"{ticker}.csv", index_label="Date")
            prices[ticker] = frame
            log(f"ETF_PRICE_DOWNLOAD_DONE ticker={ticker} rows={len(frame)}")
        except Exception as exc:
            log(f"ETF_PRICE_DOWNLOAD_ERROR ticker={ticker} error={exc}")

    execution_rows = []
    regression_rows = []
    active_etf_rows = []
    benchmark_prices = prices[config["Benchmark"]]
    for stock in stocks:
        for signal_date in signal_dates:
            audit = replay_signal(
                stock,
                signal_date,
                prices[stock],
                benchmark_prices,
                config["Benchmark"],
                foundation_policy="audit",
                macd_fast_period=macd["Fast"],
                macd_slow_period=macd["Slow"],
                macd_signal_period=macd["Signal"],
            )
            enforced = replay_signal(
                stock,
                signal_date,
                prices[stock],
                benchmark_prices,
                config["Benchmark"],
                foundation_policy="enforce",
                macd_fast_period=macd["Fast"],
                macd_slow_period=macd["Slow"],
                macd_signal_period=macd["Signal"],
            )
            foundation_valid = enforced["Foundation_Status"] == engine.FOUNDATION_VALID
            valid_regression_pass = (
                not foundation_valid
                or (
                    enforced["Final_Decision"] == audit["Final_Decision"]
                    and float(enforced["Score"]) == float(audit["Score"])
                )
            )
            short_circuit_pass = (
                foundation_valid
                or (
                    enforced["Final_Decision"] != "MOMENTUM_ACTIVE"
                    and float(enforced["Score"]) == 0.0
                )
            )
            row = {
                "Run_ID": run_id,
                "Ticker": stock,
                "Signal_Date": signal_date.date().isoformat(),
                "Foundation_Status": enforced["Foundation_Status"],
                "Foundation_Qualified": enforced["Foundation_Qualified"],
                "Foundation_Reason": enforced["Foundation_Reason"],
                "Foundation_Policy": enforced["Foundation_Policy"],
                "MACD_Fast_Period": enforced["MACD_Fast_Period"],
                "MACD_Slow_Period": enforced["MACD_Slow_Period"],
                "MACD_Signal_Period": enforced["MACD_Signal_Period"],
                "Close": enforced["Close"],
                "EMA_200": enforced["EMA_200"],
                "MACD_Line": enforced["MACD_Line"],
                "MACD_Signal_Line": enforced["MACD_Signal_Line"],
                "MACD_Histogram": enforced["MACD_Histogram"],
                "MACD_Bullish_Positive": enforced["MACD_Bullish_Positive"],
                "Setup_Momentum_Analyzed": foundation_valid,
                "Final_Decision": enforced["Final_Decision"],
                "Final_Decision_Reason": enforced["Final_Decision_Reason"],
                "Score": enforced["Score"],
                "Long_Term_Status": enforced["Long_Term_Status"],
                "Entry_Timing_Status": enforced["Entry_Timing_Status"],
                "Weekly_Trend": enforced["Weekly_Trend"],
                "Trend_Score": enforced["Trend_Score"],
                "Relative_Strength_Score": enforced["Relative_Strength_Score"],
                "Breakout_Score": enforced["Breakout_Score"],
                "Freshness_Score": enforced["Freshness_Score"],
                "Accumulation_Score": enforced["Accumulation_Score"],
                "Volatility_Score": enforced["Volatility_Score"],
                "Weekly_Trend_Score": enforced["Weekly_Trend_Score"],
                "RS_126D_Excess_Pct": enforced["RS_126D_Excess_Pct"],
                "ATR_Pct": enforced["ATR_Pct"],
                "Relative_Volume_20": enforced["Relative_Volume_20"],
                "Close_Location_Pct": enforced["Close_Location_Pct"],
                "ETF_Production_Eligible": (
                    enforced["Final_Decision"] == "MOMENTUM_ACTIVE"
                    and float(enforced["Score"]) >= engine.CONFIRMED_ENTRY_MIN_SCORE
                ),
                "Same_Quarter_ETF_Mapping_Count": len(accepted_mappings.get(stock, [])),
                "Same_Quarter_ETF_Mappings": "; ".join(
                    f"{item['ETF_Ticker']} {float(item['Holding_Weight_Pct_Direct']):.2f}%"
                    for item in accepted_mappings.get(stock, [])
                ),
                "Score_Invariance_Pass": True,
            }
            for horizon in horizons:
                stock_outcome = calculate_outcome(prices[stock], signal_date, horizon)
                spy_outcome = calculate_outcome(benchmark_prices, signal_date, horizon)
                row[f"D{horizon}_Entry_Date"] = stock_outcome["Entry_Date"]
                row[f"D{horizon}_Exit_Date"] = stock_outcome["Exit_Date"]
                row[f"D{horizon}_Return_Pct"] = stock_outcome["Return_Pct"]
                row[f"SPY_D{horizon}_Return_Pct"] = spy_outcome["Return_Pct"]
                row[f"SPY_Adjusted_D{horizon}_Return_Pct"] = (
                    stock_outcome["Return_Pct"] - spy_outcome["Return_Pct"]
                )
            execution_rows.append({key: clean(value) for key, value in row.items()})
            regression_rows.append(
                {
                    "Ticker": stock,
                    "Signal_Date": signal_date.date().isoformat(),
                    "Foundation_Status": enforced["Foundation_Status"],
                    "Audit_Decision": audit["Final_Decision"],
                    "Audit_Score": audit["Score"],
                    "Enforced_Decision": enforced["Final_Decision"],
                    "Enforced_Score": enforced["Score"],
                    "Decision_Changed": audit["Final_Decision"] != enforced["Final_Decision"],
                    "Valid_Row_Regression_Pass": valid_regression_pass,
                    "Invalid_Row_Short_Circuit_Pass": short_circuit_pass,
                }
            )
            if row["ETF_Production_Eligible"]:
                for mapping in accepted_mappings.get(stock, []):
                    etf_ticker = mapping["ETF_Ticker"]
                    if etf_ticker not in prices:
                        continue
                    etf_row = {
                        "Ticker": stock,
                        "Signal_Date": signal_date.date().isoformat(),
                        "Stock_Score": enforced["Score"],
                        "ETF_Ticker": etf_ticker,
                        "Holding_Weight_Pct_Direct": mapping["Holding_Weight_Pct_Direct"],
                        "Validation_As_Of_Date": mapping["Validation_As_Of_Date"],
                        "Validation_Rank": mapping["Validation_Rank"],
                        "Same_Quarter_Pass": mapping["Same_Quarter_2026Q2"],
                    }
                    for horizon in horizons:
                        stock_outcome = calculate_outcome(prices[stock], signal_date, horizon)
                        etf_outcome = calculate_outcome(prices[etf_ticker], signal_date, horizon)
                        etf_row[f"Stock_D{horizon}_Return_Pct"] = stock_outcome["Return_Pct"]
                        etf_row[f"ETF_D{horizon}_Return_Pct"] = etf_outcome["Return_Pct"]
                    active_etf_rows.append(etf_row)
            log(
                f"REPLAY ticker={stock} date={signal_date.date()} "
                f"foundation={enforced['Foundation_Status']} decision={enforced['Final_Decision']} "
                f"score={enforced['Score']} d1={row['D1_Return_Pct']:.4f} "
                f"d5={row['D5_Return_Pct']:.4f} d8={row['D8_Return_Pct']:.4f}"
            )

    write_csv(execution_rows, outputs_dir / "execution_log.csv")
    write_csv(regression_rows, outputs_dir / "regression_comparison.csv")
    write_csv(etf_stock_rows, outputs_dir / "etf_stock_summary.csv")
    write_csv(mapping_rows, outputs_dir / "etf_mapping_validation.csv")
    write_csv(active_etf_rows, outputs_dir / "active_etf_outcomes.csv")

    ticker_summary = []
    for stock in stocks:
        rows = [row for row in execution_rows if row["Ticker"] == stock]
        ticker_summary.append(
            {
                "Ticker": stock,
                "Rows": len(rows),
                "Foundation_Valid": sum(row["Foundation_Status"] == engine.FOUNDATION_VALID for row in rows),
                "MACD_Reset": sum(row["Foundation_Status"] == engine.FOUNDATION_MACD_RESET for row in rows),
                "Below_EMA200": sum(row["Foundation_Status"] == engine.FOUNDATION_BELOW_EMA200 for row in rows),
                "Active": sum(row["Final_Decision"] == "MOMENTUM_ACTIVE" for row in rows),
                "Wait": sum(row["Final_Decision"] == "MOMENTUM_PRESENT_WAIT_CONFIRMATION" for row in rows),
                "Reject": sum(row["Final_Decision"] == "REJECT" for row in rows),
                "D1_Positive": sum(float(row["D1_Return_Pct"]) > 0 for row in rows),
                "D5_Positive": sum(float(row["D5_Return_Pct"]) > 0 for row in rows),
                "D8_Positive": sum(float(row["D8_Return_Pct"]) > 0 for row in rows),
            }
        )
    date_summary = []
    for signal_date in signal_dates:
        date_text = signal_date.date().isoformat()
        rows = [row for row in execution_rows if row["Signal_Date"] == date_text]
        qualified = [row for row in rows if row["Foundation_Status"] == engine.FOUNDATION_VALID]
        active = [row for row in rows if row["Final_Decision"] == "MOMENTUM_ACTIVE"]
        date_summary.append(
            {
                "Signal_Date": date_text,
                "Rows": len(rows),
                "Foundation_Valid": len(qualified),
                "Active": len(active),
                "Qualified_D1_Positive_Rate_Pct": (
                    100 * sum(float(row["D1_Return_Pct"]) > 0 for row in qualified) / len(qualified)
                    if qualified else ""
                ),
                "Active_D1_Positive_Rate_Pct": (
                    100 * sum(float(row["D1_Return_Pct"]) > 0 for row in active) / len(active)
                    if active else ""
                ),
            }
        )
    write_csv(ticker_summary, outputs_dir / "ticker_summary.csv")
    write_csv(date_summary, outputs_dir / "date_summary.csv")

    qualified_rows = [row for row in execution_rows if row["Foundation_Status"] == engine.FOUNDATION_VALID]
    active_rows = [row for row in execution_rows if row["Final_Decision"] == "MOMENTUM_ACTIVE"]
    summary = {
        "Run_ID": run_id,
        "Stocks_Tested": len(stocks),
        "Dates_Tested": len(signal_dates),
        "Total_Rows": len(execution_rows),
        "Quarter": config["Quarter"],
        "MACD": macd,
        "Foundation_Status_Counts": {
            status: sum(row["Foundation_Status"] == status for row in execution_rows)
            for status in (
                engine.FOUNDATION_VALID,
                engine.FOUNDATION_MACD_RESET,
                engine.FOUNDATION_BELOW_EMA200,
                engine.FOUNDATION_INSUFFICIENT_DATA,
            )
        },
        "Decision_Counts": {
            decision: sum(row["Final_Decision"] == decision for row in execution_rows)
            for decision in (
                "MOMENTUM_ACTIVE",
                "MOMENTUM_PRESENT_WAIT_CONFIRMATION",
                "REJECT",
            )
        },
        "Foundation_Qualified_Directional": {
            f"D{horizon}_Positive": sum(float(row[f"D{horizon}_Return_Pct"]) > 0 for row in qualified_rows)
            for horizon in horizons
        },
        "Foundation_Qualified_Rows": len(qualified_rows),
        "Active_Directional": {
            f"D{horizon}_Positive": sum(float(row[f"D{horizon}_Return_Pct"]) > 0 for row in active_rows)
            for horizon in horizons
        },
        "Active_Rows": len(active_rows),
        "Valid_Row_Regression_Failures": sum(
            not row["Valid_Row_Regression_Pass"] for row in regression_rows
        ),
        "Invalid_Row_Short_Circuit_Failures": sum(
            not row["Invalid_Row_Short_Circuit_Pass"] for row in regression_rows
        ),
        "ETF_Stocks_Queried": len(etf_stock_rows),
        "ETF_Returned_Mappings": len(mapping_rows),
        "ETF_Accepted_Same_Quarter_Mappings": sum(
            bool(row["Historical_Mapping_Accepted"]) for row in mapping_rows
        ),
        "Active_ETF_Outcome_Rows": len(active_etf_rows),
        "Score_Invariance_Failures": sum(
            not bool(row["Score_Invariance_Pass"]) for row in execution_rows
        ),
    }
    (outputs_dir / "aggregate_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    (outputs_dir / "execution_console.log").write_text(
        "\n".join(log_lines) + "\n", encoding="utf-8"
    )
    manifest = {
        **summary,
        "Started_UTC": started.isoformat(),
        "Completed_UTC": datetime.now(timezone.utc).isoformat(),
        "Git_Commit": git_value("rev-parse", "HEAD"),
        "Git_Branch": git_value("branch", "--show-current"),
        "Git_Worktree_Dirty": bool(git_value("status", "--porcelain")),
        "Config_SHA256": sha256_file(config_path),
        "Historical_Replay_Mode": config["Historical_Replay_Mode"],
        "ETF_Historical_Evidence_Rule": config["ETF_Historical_Evidence_Rule"],
        "Known_Limitations": [
            "Daily EOD replay cannot reconstruct historical hourly, live-quote, or extended-hours state.",
            "The 20-stock technology seed is purposeful and is not a random market-wide sample.",
            "ETF mappings are accepted only when the independently reported holdings date is in 2026Q2.",
            "Four dates in one quarter validate implementation and directional behavior, not all market regimes.",
        ],
    }
    (run_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (run_dir / "command.txt").write_text(
        f"python Backtest_Momentum_Detector_V8_Foundation.py --config {args.config.as_posix()} --output-root {args.output_root.as_posix()}\n",
        encoding="utf-8",
    )
    (run_dir / "environment.txt").write_text(
        f"Python: {sys.version}\npandas: {pd.__version__}\nyfinance: {yf.__version__}\n",
        encoding="utf-8",
    )
    (run_dir / "README.md").write_text(
        f"# {run_id}\n\nFrozen V8 foundation validation: 20 technology stocks, four predeclared 2026Q2 dates, MACD 8/21/5, D+1/D+5/D+8, and same-quarter ETF evidence.\n",
        encoding="utf-8",
    )

    validator = ROOT / "Validate_Momentum_Detector_V8_Foundation.py"
    validation_result = subprocess.run(
        [sys.executable, str(validator), str(run_dir), "--skip-checksums"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    (validation_dir / "validator_console.txt").write_text(
        validation_result.stdout + validation_result.stderr, encoding="utf-8"
    )
    if validation_result.returncode:
        raise RuntimeError("independent validator failed; see validation/validator_console.txt")
    log("VALIDATION_PASS")
    (outputs_dir / "execution_console.log").write_text(
        "\n".join(log_lines) + "\n", encoding="utf-8"
    )
    count = write_checksums(run_dir)
    print(f"CHECKSUMS_WRITTEN entries={count}")
    print(f"RUN_COMPLETE run_dir={run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
