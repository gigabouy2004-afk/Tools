import argparse
import csv
import hashlib
import json
import math
import random
import shutil
import statistics
import subprocess
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf

import ETF_Context_V8 as etf_context
import Momentum_Detector_V8 as engine
from Backtest_Momentum_Detector_V8_ETF import validate_mapping_against_holdings


DEFAULT_CONFIG = Path("config/V8_Comprehensive_Backtest_Config.json")
DEFAULT_OUTPUT_ROOT = Path("backtests/V8_Comprehensive/runs")
ROOT = Path(__file__).resolve().parent


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


def write_csv(records, path, fieldnames=None):
    path = Path(path)
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


def clean_number(value):
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    if isinstance(value, float) and not math.isfinite(value):
        return ""
    return value


def mean_or_none(values):
    clean = [float(value) for value in values if value not in (None, "") and pd.notna(value)]
    return statistics.mean(clean) if clean else None


def median_or_none(values):
    clean = [float(value) for value in values if value not in (None, "") and pd.notna(value)]
    return statistics.median(clean) if clean else None


def parse_quarter(value):
    text = str(value).strip().upper()
    if len(text) != 6 or text[4] != "Q" or not text[:4].isdigit() or text[5] not in "1234":
        raise ValueError(f"invalid quarter: {value!r}; expected YYYYQn format such as 2026Q2")
    year = int(text[:4])
    quarter = int(text[5])
    start_month = 1 + (quarter - 1) * 3
    start = pd.Timestamp(year=year, month=start_month, day=1)
    end = start + pd.offsets.QuarterEnd(startingMonth=start_month + 2)
    return text, start.normalize(), end.normalize()


def quarter_label(value):
    stamp = pd.Timestamp(value)
    return f"{stamp.year}Q{stamp.quarter}"


def download_daily(ticker, start, end_exclusive, attempts=3):
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            df = yf.download(
                ticker,
                start=pd.Timestamp(start).date().isoformat(),
                end=pd.Timestamp(end_exclusive).date().isoformat(),
                auto_adjust=False,
                actions=True,
                progress=False,
                threads=False,
            )
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            if df.empty:
                raise RuntimeError("empty price response")
            df = df.copy()
            df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
            required = ["Open", "High", "Low", "Close", "Volume"]
            if any(field not in df.columns for field in required):
                raise RuntimeError(f"missing OHLCV fields: {list(df.columns)}")
            for optional in ["Adj Close", "Dividends", "Stock Splits"]:
                if optional not in df.columns:
                    df[optional] = 0.0 if optional != "Adj Close" else df["Close"]
            return df[["Open", "High", "Low", "Close", "Adj Close", "Volume", "Dividends", "Stock Splits"]].dropna(
                subset=required
            )
        except Exception as exc:
            last_error = exc
            if attempt < attempts:
                time.sleep(attempt * 2)
    raise RuntimeError(f"price download failed for {ticker}: {last_error}")


def engine_frame(price_df):
    return price_df[["Open", "High", "Low", "Close", "Volume"]].copy()


def daily_timing_policy(calc_df):
    return engine.evaluate_intraday_timing(calc_df, pd.DataFrame(), quote={})


def replay_signal(ticker, signal_date, stock_prices, benchmark_prices, benchmark_ticker):
    signal_date = pd.Timestamp(signal_date).normalize()
    stock_history = engine_frame(stock_prices.loc[:signal_date])
    benchmark_history = engine_frame(benchmark_prices.loc[:signal_date])
    if len(stock_history) < engine.MIN_HISTORY_BARS:
        raise ValueError(f"{ticker} has only {len(stock_history)} bars through {signal_date.date()}")
    stock_history = engine.apply_live_price_to_daily_data(stock_history, {})
    calc_df = engine.calculate_v5_indicators(
        stock_history,
        benchmark_history,
        benchmark_ticker=benchmark_ticker,
        exchange_profile=engine.exchange_profile_for_ticker(ticker),
    )
    row = calc_df.iloc[-1]
    timing = daily_timing_policy(calc_df)
    scores, weekly_trend = engine.score_v5(row)
    scores = engine.apply_commercial_readiness_score(row, scores, weekly_trend, timing)
    long_term_status, reason = engine.classify_signal(row, scores, weekly_trend, timing)
    return engine.build_output_row(
        ticker, row, scores, weekly_trend, timing, long_term_status, reason
    )


def calculate_outcome(price_df, signal_date, horizon):
    signal_date = pd.Timestamp(signal_date).normalize()
    if signal_date not in price_df.index:
        return None
    signal_position = price_df.index.get_loc(signal_date)
    if not isinstance(signal_position, int):
        signal_position = int(signal_position[0])
    entry_position = signal_position + 1
    exit_position = signal_position + int(horizon)
    if entry_position >= len(price_df) or exit_position >= len(price_df):
        return None
    entry = float(price_df.iloc[entry_position]["Open"])
    exit_price = float(price_df.iloc[exit_position]["Close"])
    if entry <= 0:
        return None
    return {
        "Entry_Date": price_df.index[entry_position].date().isoformat(),
        "Entry_Open": entry,
        "Exit_Date": price_df.index[exit_position].date().isoformat(),
        "Exit_Close": exit_price,
        "Return_Pct": ((exit_price / entry) - 1.0) * 100.0,
    }


def eligible_random_dates(price_df, quarter_start, quarter_end, max_horizon):
    dates = list(price_df.loc[(price_df.index >= quarter_start) & (price_df.index <= quarter_end)].index)
    eligible = []
    for signal_date in dates:
        outcome = calculate_outcome(price_df, signal_date, max_horizon)
        if outcome and pd.Timestamp(outcome["Exit_Date"]) <= quarter_end:
            eligible.append(signal_date)
    return eligible


def deterministic_date(dates, seed, ticker):
    if not dates:
        raise ValueError(f"no eligible random dates for {ticker}")
    ticker_seed = int(seed) + sum((index + 1) * ord(char) for index, char in enumerate(ticker))
    return random.Random(ticker_seed).choice(sorted(dates))


def same_quarter_message(mappings):
    parts = [f"{row['ETF_Ticker']} {float(row['Holding_Weight_Pct_Direct']):.2f}%" for row in mappings]
    return "Quarter-assumption ETF mappings: " + "; ".join(parts) + "."


def snapshot_sources(source_dir, config_path):
    source_dir.mkdir(parents=True, exist_ok=True)
    files = [
        ROOT / "Momentum_Detector_V8.py",
        ROOT / "ETF_Context_V8.py",
        ROOT / "Backtest_Momentum_Detector_V8_ETF.py",
        ROOT / "Backtest_Momentum_Detector_V8.py",
        ROOT / "Validate_Momentum_Detector_V8_Backtest.py",
        ROOT / "tests/test_v8_comprehensive_backtest.py",
    ]
    for source in files:
        if source.exists():
            destination = source_dir / source.relative_to(ROOT)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
    config_destination = source_dir / "config" / Path(config_path).name
    config_destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(config_path, config_destination)


def write_checksums(run_dir):
    checksum_path = run_dir / "checksums.sha256"
    lines = []
    for path in sorted(run_dir.rglob("*")):
        if path.is_file() and path != checksum_path:
            lines.append(f"{sha256_file(path)}  {path.relative_to(run_dir).as_posix()}")
    checksum_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(lines)


def parse_args():
    parser = argparse.ArgumentParser(description="V8 comprehensive same-quarter stock and ETF backtest")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    return parser.parse_args()


def main():
    args = parse_args()
    config_path = args.config.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    quarter, quarter_start, quarter_end = parse_quarter(config["Quarter"])
    horizons = sorted({int(value) for value in config["Horizon_Sessions"]})
    max_horizon = max(horizons)
    seed = int(config["Random_Seed"])
    candidates = list(dict.fromkeys(etf_context.normalize_ticker(value) for value in config["Candidate_Stocks"]))
    minimum_stocks = int(config["Minimum_Stocks"])
    benchmark = config["Benchmark"]

    started = datetime.now(timezone.utc)
    commit_short = git_value("rev-parse", "--short", "HEAD")
    run_id = f"V8FULL_{started.strftime('%Y%m%dT%H%M%SZ')}_{commit_short}_{seed}"
    run_dir = args.output_root.resolve() / run_id
    inputs_dir = run_dir / "inputs"
    outputs_dir = run_dir / "outputs"
    validation_dir = run_dir / "validation"
    source_dir = run_dir / "source_snapshot"
    prices_dir = inputs_dir / "prices"
    for directory in [inputs_dir, outputs_dir, validation_dir, source_dir, prices_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    execution_log_path = outputs_dir / "execution.log"

    def log(message):
        line = str(message)
        print(line, flush=True)
        with open(execution_log_path, "a", encoding="utf-8") as file:
            file.write(line + "\n")

    log(f"Run_ID={run_id}")
    log(f"Quarter={quarter} Seed={seed} Minimum_Stocks={minimum_stocks}")
    log(f"Replay_Mode={config['Historical_Replay_Mode']}")
    log(f"ETF_Assumption={config['ETF_Quarter_Assumption']}")

    snapshot_sources(source_dir, config_path)
    shutil.copy2(config_path, inputs_dir / "config_snapshot.json")
    shutil.copy2(etf_context.DEFAULT_STOCK_MASTER_PATH, inputs_dir / "stock_master_snapshot.csv")
    shutil.copy2(etf_context.DEFAULT_US_ETF_MASTER_PATH, inputs_dir / "us_etf_master_snapshot.csv")

    all_mapping_rows = []
    quarter_mappings = {}
    etf_request_count = 0
    validation_request_count = 0

    for stock in candidates:
        log(f"ETF_LOOKUP_START stock={stock}")
        context = etf_context.get_etf_mapping_context(
            stock,
            stock_master_path=inputs_dir / "stock_master_snapshot.csv",
            etf_master_path=inputs_dir / "us_etf_master_snapshot.csv",
            use_cache=False,
        )
        etf_request_count += 1
        stock_quarter_rows = []
        for mapping in context.get("Mappings", []):
            validation_request_count += 1
            try:
                validation = validate_mapping_against_holdings(
                    stock, mapping, etf_context.DEFAULT_TIMEOUT_SECONDS
                )
            except Exception as exc:
                validation = {
                    "Validation_Status": f"ERROR: {exc}",
                    "Validation_As_Of_Date": "",
                    "Validation_Top10_Match": False,
                    "Validation_Freshness_Pass": False,
                }
            as_of_date = validation.get("Validation_As_Of_Date", "")
            mapping_quarter = quarter_label(as_of_date) if as_of_date else ""
            quarter_match = mapping_quarter == quarter
            row = {
                "Stock_Code": stock,
                "ETF_Status": context.get("ETF_Status", ""),
                "Source_URL": context.get("Source_URL", ""),
                "Source_HTML_SHA256": context.get("Source_HTML_SHA256", ""),
                "Production_Latency_Ms": context.get("Latency_Ms", ""),
                "ETF_Ticker": mapping.get("ETF_Ticker", ""),
                "ETF_Name": mapping.get("ETF_Name", ""),
                "Holding_Weight_Pct_Direct": mapping.get("Holding_Weight_Pct", ""),
                "Top10_Evidence": mapping.get("Top10_Evidence", ""),
                **validation,
                "Validation_Quarter": mapping_quarter,
                "Requested_Test_Quarter": quarter,
                "Same_Quarter_Eligible": quarter_match and validation.get("Validation_Status") == "PASS",
                "Historical_Evidence_Mode": config["ETF_Quarter_Assumption"],
            }
            all_mapping_rows.append(row)
            if row["Same_Quarter_Eligible"]:
                stock_quarter_rows.append(row)
        if stock_quarter_rows:
            quarter_mappings[stock] = stock_quarter_rows
        log(
            f"ETF_LOOKUP_DONE stock={stock} returned={len(context.get('Mappings', []))} "
            f"same_quarter_pass={len(stock_quarter_rows)}"
        )

    selected_stocks = [stock for stock in candidates if stock in quarter_mappings]
    if len(selected_stocks) < minimum_stocks:
        write_csv(all_mapping_rows, outputs_dir / "etf_mapping_validation.csv")
        raise RuntimeError(
            f"only {len(selected_stocks)} stocks have same-quarter verified mappings; required {minimum_stocks}"
        )
    selected_stocks = selected_stocks[:minimum_stocks]
    quarter_mappings = {stock: quarter_mappings[stock] for stock in selected_stocks}
    log(f"SELECTED_STOCKS={','.join(selected_stocks)}")

    download_end = quarter_end + pd.Timedelta(days=1)
    price_start = pd.Timestamp(config["Price_Start"])
    required_symbols = list(dict.fromkeys(
        [benchmark]
        + selected_stocks
        + [row["ETF_Ticker"] for stock in selected_stocks for row in quarter_mappings[stock]]
    ))
    prices = {}
    price_manifest = []
    for symbol in required_symbols:
        log(f"PRICE_DOWNLOAD_START symbol={symbol}")
        frame = download_daily(symbol, price_start, download_end)
        prices[symbol] = frame
        price_path = prices_dir / f"{symbol}.csv"
        frame.to_csv(price_path, index_label="Date")
        price_manifest.append(
            {
                "Symbol": symbol,
                "Rows": len(frame),
                "First_Date": frame.index.min().date().isoformat(),
                "Last_Date": frame.index.max().date().isoformat(),
                "SHA256": sha256_file(price_path),
            }
        )
        log(f"PRICE_DOWNLOAD_DONE symbol={symbol} rows={len(frame)}")
    write_csv(price_manifest, inputs_dir / "price_manifest.csv")

    execution_rows = []
    random_rows = []
    random_etf_rows = []
    stock_summaries = []

    for stock in selected_stocks:
        stock_prices = prices[stock]
        benchmark_prices = prices[benchmark]
        quarter_dates = list(
            stock_prices.loc[
                (stock_prices.index >= quarter_start) & (stock_prices.index <= quarter_end)
            ].index
        )
        random_candidates = eligible_random_dates(
            stock_prices, quarter_start, quarter_end, max_horizon
        )
        random_date = deterministic_date(random_candidates, seed, stock)
        prior_dates = list(stock_prices.index[stock_prices.index < quarter_start])[-21:]
        non_active_streak = 0
        for prior_date in prior_dates:
            prior_output = replay_signal(
                stock, prior_date, stock_prices, benchmark_prices, benchmark
            )
            if prior_output["Final_Decision"] == "MOMENTUM_ACTIVE":
                non_active_streak = 0
            else:
                non_active_streak += 1
        stock_rows = []

        for signal_date in quarter_dates:
            output = replay_signal(stock, signal_date, stock_prices, benchmark_prices, benchmark)
            score_before_etf = float(output["Score"])
            production_eligible = (
                output["Final_Decision"] == "MOMENTUM_ACTIVE"
                and score_before_etf >= engine.CONFIRMED_ENTRY_MIN_SCORE
            )
            if production_eligible:
                output["Score_Message"] = same_quarter_message(quarter_mappings[stock])
            score_after_etf = float(output["Score"])
            if score_before_etf != score_after_etf:
                raise AssertionError(f"ETF score mutation for {stock} on {signal_date.date()}")

            primary_episode = (
                output["Final_Decision"] == "MOMENTUM_ACTIVE" and non_active_streak >= 21
            )
            row = {
                "Run_ID": run_id,
                "Ticker": stock,
                "Signal_Date": signal_date.date().isoformat(),
                "Random_Sample_Row": signal_date == random_date,
                "Historical_Replay_Mode": config["Historical_Replay_Mode"],
                "Intraday_Replay_Status": "UNAVAILABLE",
                "Live_Quote_Replay_Status": "UNAVAILABLE",
                "Final_Decision": output["Final_Decision"],
                "Final_Decision_Reason": output["Final_Decision_Reason"],
                "Score": output["Score"],
                "Score_Before_ETF": score_before_etf,
                "Score_After_ETF": score_after_etf,
                "Score_Invariance_Pass": score_before_etf == score_after_etf,
                "Long_Term_Status": output["Long_Term_Status"],
                "Entry_Timing_Status": output["Entry_Timing_Status"],
                "Weekly_Trend": output["Weekly_Trend"],
                "Trend_Score": output["Trend_Score"],
                "Relative_Strength_Score": output["Relative_Strength_Score"],
                "Breakout_Score": output["Breakout_Score"],
                "Freshness_Score": output["Freshness_Score"],
                "Accumulation_Score": output["Accumulation_Score"],
                "Volatility_Score": output["Volatility_Score"],
                "Weekly_Trend_Score": output["Weekly_Trend_Score"],
                "Close": output["Close"],
                "RS_126D_Excess_Pct": output["RS_126D_Excess_Pct"],
                "ATR_Pct": output["ATR_Pct"],
                "Relative_Volume_20": output["Relative_Volume_20"],
                "Close_Location_Pct": output["Close_Location_Pct"],
                "ETF_Production_Eligible": production_eligible,
                "ETF_Assumption": config["ETF_Quarter_Assumption"],
                "Same_Quarter_ETF_Mappings": "; ".join(
                    f"{item['ETF_Ticker']} {float(item['Holding_Weight_Pct_Direct']):.2f}%"
                    for item in quarter_mappings[stock]
                ),
                "ETF_Validation_As_Of_Dates": "; ".join(
                    sorted({item["Validation_As_Of_Date"] for item in quarter_mappings[stock]})
                ),
                "Score_Message": output.get("Score_Message", ""),
                "Primary_Episode": primary_episode,
                "Prior_Non_Active_Session_Count": non_active_streak,
            }
            for horizon in horizons:
                stock_outcome = calculate_outcome(stock_prices, signal_date, horizon)
                benchmark_outcome = calculate_outcome(benchmark_prices, signal_date, horizon)
                row[f"Forward_{horizon}D_Return_Pct"] = (
                    stock_outcome["Return_Pct"] if stock_outcome else ""
                )
                row[f"Benchmark_{horizon}D_Return_Pct"] = (
                    benchmark_outcome["Return_Pct"] if benchmark_outcome else ""
                )
                row[f"Benchmark_Adjusted_{horizon}D_Return_Pct"] = (
                    stock_outcome["Return_Pct"] - benchmark_outcome["Return_Pct"]
                    if stock_outcome and benchmark_outcome
                    else ""
                )
                row[f"Forward_{horizon}D_Exit_Date"] = (
                    stock_outcome["Exit_Date"] if stock_outcome else ""
                )
            execution_rows.append({key: clean_number(value) for key, value in row.items()})
            stock_rows.append(row)
            if output["Final_Decision"] == "MOMENTUM_ACTIVE":
                non_active_streak = 0
            else:
                non_active_streak += 1

        selected_row = next(row for row in stock_rows if row["Signal_Date"] == random_date.date().isoformat())
        random_rows.append(selected_row)

        for mapping in quarter_mappings[stock]:
            etf_ticker = mapping["ETF_Ticker"]
            etf_row = {
                "Run_ID": run_id,
                "Stock_Code": stock,
                "Random_Signal_Date": random_date.date().isoformat(),
                "Stock_Final_Decision": selected_row["Final_Decision"],
                "Stock_Score": selected_row["Score"],
                "ETF_Ticker": etf_ticker,
                "Holding_Weight_Pct_Direct": mapping["Holding_Weight_Pct_Direct"],
                "Validation_As_Of_Date": mapping["Validation_As_Of_Date"],
                "Validation_Rank": mapping.get("Validation_Rank", ""),
                "Validation_Status": mapping["Validation_Status"],
                "Same_Quarter_Pass": mapping["Same_Quarter_Eligible"],
                "Historical_Evidence_Mode": config["ETF_Quarter_Assumption"],
            }
            for horizon in horizons:
                stock_outcome = calculate_outcome(stock_prices, random_date, horizon)
                etf_outcome = calculate_outcome(prices[etf_ticker], random_date, horizon)
                benchmark_outcome = calculate_outcome(benchmark_prices, random_date, horizon)
                etf_row[f"Stock_{horizon}D_Return_Pct"] = stock_outcome["Return_Pct"]
                etf_row[f"ETF_{horizon}D_Return_Pct"] = etf_outcome["Return_Pct"]
                etf_row[f"ETF_Excess_SPY_{horizon}D_Pct"] = (
                    etf_outcome["Return_Pct"] - benchmark_outcome["Return_Pct"]
                )
                etf_row[f"Stock_Minus_ETF_{horizon}D_Pct"] = (
                    stock_outcome["Return_Pct"] - etf_outcome["Return_Pct"]
                )
                etf_row[f"Exit_Date_{horizon}D"] = etf_outcome["Exit_Date"]
            random_etf_rows.append(etf_row)

        stock_summaries.append(
            {
                "Ticker": stock,
                "Quarter_Rows": len(stock_rows),
                "Active_Rows": sum(row["Final_Decision"] == "MOMENTUM_ACTIVE" for row in stock_rows),
                "Wait_Rows": sum(
                    row["Final_Decision"] == "MOMENTUM_PRESENT_WAIT_CONFIRMATION"
                    for row in stock_rows
                ),
                "Reject_Rows": sum(row["Final_Decision"] == "REJECT" for row in stock_rows),
                "Primary_Active_Episodes": sum(bool(row["Primary_Episode"]) for row in stock_rows),
                "Random_Signal_Date": random_date.date().isoformat(),
                "Random_Final_Decision": selected_row["Final_Decision"],
                "Random_Score": selected_row["Score"],
                "Random_21D_Return_Pct": selected_row["Forward_21D_Return_Pct"],
                "Random_SPY_Adjusted_21D_Return_Pct": selected_row[
                    "Benchmark_Adjusted_21D_Return_Pct"
                ],
                "Same_Quarter_Mapping_Count": len(quarter_mappings[stock]),
                "Same_Quarter_Mappings": selected_row["Same_Quarter_ETF_Mappings"],
            }
        )
        log(
            f"REPLAY_DONE stock={stock} rows={len(stock_rows)} random_date={random_date.date()} "
            f"random_decision={selected_row['Final_Decision']} random_score={selected_row['Score']}"
        )

    write_csv(all_mapping_rows, outputs_dir / "etf_mapping_validation.csv")
    write_csv(execution_rows, outputs_dir / "execution_log.csv")
    write_csv(random_rows, outputs_dir / "random_date_results.csv")
    write_csv(random_etf_rows, outputs_dir / "random_etf_outcomes.csv")
    write_csv(stock_summaries, outputs_dir / "stock_summary.csv")

    active_episodes = [row for row in execution_rows if row["Primary_Episode"]]
    summary = {
        "Run_ID": run_id,
        "Quarter": quarter,
        "Random_Seed": seed,
        "Stocks_Tested": len(selected_stocks),
        "Stock_Dates_Replayed": len(execution_rows),
        "Random_Date_Rows": len(random_rows),
        "ETF_Production_Requests": etf_request_count,
        "ETF_Validation_Requests": validation_request_count,
        "Same_Quarter_Verified_Mappings": sum(
            bool(row["Same_Quarter_Eligible"]) for row in all_mapping_rows
        ),
        "Score_Invariance_Failures": sum(
            not bool(row["Score_Invariance_Pass"]) for row in execution_rows
        ),
        "Decision_Counts": {
            decision: sum(row["Final_Decision"] == decision for row in execution_rows)
            for decision in [
                "MOMENTUM_ACTIVE",
                "MOMENTUM_PRESENT_WAIT_CONFIRMATION",
                "REJECT",
            ]
        },
        "Primary_Active_Episodes": len(active_episodes),
        "Random_Sample_Mean_Stock_21D_Return_Pct": mean_or_none(
            row["Forward_21D_Return_Pct"] for row in random_rows
        ),
        "Random_Sample_Median_Stock_21D_Return_Pct": median_or_none(
            row["Forward_21D_Return_Pct"] for row in random_rows
        ),
        "Random_Sample_Mean_SPY_Adjusted_21D_Return_Pct": mean_or_none(
            row["Benchmark_Adjusted_21D_Return_Pct"] for row in random_rows
        ),
        "Random_ETF_Mean_21D_Return_Pct": mean_or_none(
            row["ETF_21D_Return_Pct"] for row in random_etf_rows
        ),
        "Random_ETF_Mean_Excess_SPY_21D_Pct": mean_or_none(
            row["ETF_Excess_SPY_21D_Pct"] for row in random_etf_rows
        ),
        "Active_Episode_Mean_21D_Return_Pct": mean_or_none(
            row["Forward_21D_Return_Pct"] for row in active_episodes
        ),
        "Active_Episode_Mean_SPY_Adjusted_21D_Return_Pct": mean_or_none(
            row["Benchmark_Adjusted_21D_Return_Pct"] for row in active_episodes
        ),
        "Evidence_Classification": (
            "TECHNICAL_SAMPLE_COMPLETE_INSUFFICIENT_FOR_BROAD_OPERATIONAL_SIGNOFF"
            if len(active_episodes) < 50
            else "TECHNICAL_SAMPLE_COMPLETE_REQUIRES_FULL_PLAN_REVIEW"
        ),
        "Historical_Replay_Mode": config["Historical_Replay_Mode"],
        "ETF_Historical_Evidence_Mode": config["ETF_Quarter_Assumption"],
    }
    (outputs_dir / "aggregate_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    manifest = {
        **summary,
        "Started_UTC": started.isoformat(),
        "Completed_UTC": datetime.now(timezone.utc).isoformat(),
        "Git_Commit": git_value("rev-parse", "HEAD"),
        "Git_Branch": git_value("branch", "--show-current"),
        "Git_Worktree_Dirty": bool(git_value("status", "--porcelain")),
        "Config_SHA256": sha256_file(config_path),
        "Source_Hashes": {
            "Momentum_Detector_V8.py": sha256_file(ROOT / "Momentum_Detector_V8.py"),
            "ETF_Context_V8.py": sha256_file(ROOT / "ETF_Context_V8.py"),
            "Backtest_Momentum_Detector_V8.py": sha256_file(ROOT / "Backtest_Momentum_Detector_V8.py"),
        },
        "Selected_Stocks": selected_stocks,
        "Horizon_Sessions": horizons,
        "Price_Start": config["Price_Start"],
        "Price_End_Inclusive": quarter_end.date().isoformat(),
        "Known_Limitations": [
            "Daily EOD replay cannot reconstruct V8 historical hourly timing or live/extended-hours quotes.",
            "The current StockCodeMaster universe has survivorship and classification-history limitations.",
            "TradingView reverse pages are public pages rather than a versioned developer API.",
            "ETF mappings are associated under the user-approved same-calendar-quarter stability assumption, not strict signal-date point-in-time holdings evidence.",
            "Ten stocks and one random date per stock are a technical sample and do not meet the broad evidence targets in the comprehensive plan.",
        ],
    }
    (run_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (run_dir / "command.txt").write_text(
        f"python Backtest_Momentum_Detector_V8.py --config {args.config.as_posix()} --output-root {args.output_root.as_posix()}\n",
        encoding="utf-8",
    )
    (run_dir / "environment.txt").write_text(
        f"Python: {sys.version}\npandas: {pd.__version__}\nyfinance: {yf.__version__}\n",
        encoding="utf-8",
    )
    readme = f"""# {run_id}

V8 comprehensive 10-stock same-quarter technical backtest for {quarter}.

- Stocks: {', '.join(selected_stocks)}
- Random seed: {seed}
- Daily rows replayed: {len(execution_rows)}
- Primary Active episodes: {len(active_episodes)}
- Same-quarter verified ETF mappings: {summary['Same_Quarter_Verified_Mappings']}
- Evidence classification: {summary['Evidence_Classification']}

ETF history uses `SAME_CALENDAR_QUARTER_STABILITY_ASSUMPTION`; it is not strict point-in-time historical holdings evidence.
"""
    (run_dir / "README.md").write_text(readme, encoding="utf-8")

    validator = ROOT / "Validate_Momentum_Detector_V8_Backtest.py"
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
        raise RuntimeError(f"independent validator failed; see {validation_dir / 'validator_console.txt'}")

    log("VALIDATION_PASS")
    log(f"RUN_COMPLETE run_dir={run_dir}")
    checksum_count = write_checksums(run_dir)
    print(f"CHECKSUMS_WRITTEN entries={checksum_count}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
