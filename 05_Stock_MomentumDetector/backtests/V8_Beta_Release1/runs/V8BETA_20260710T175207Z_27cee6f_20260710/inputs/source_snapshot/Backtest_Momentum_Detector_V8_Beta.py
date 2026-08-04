import argparse
import hashlib
import json
import math
import random
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

import Beta_Context_V8 as beta_context
import Momentum_Detector_V8 as engine


DEFAULT_PILOT_TICKERS = ["NET", "CSX", "ILMN", "ICHR", "PL", "CVV", "ETN", "ACA", "MATX"]
DEFAULT_OUTPUT_ROOT = Path("backtests") / "V8_Beta_Release1" / "runs"
DEFAULT_SEED = 20260710
FORWARD_HORIZONS = (1, 5, 10, 21, 63, 126)
PATH_WINDOWS = (21, 63)


def finite_number(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_value(*args):
    try:
        return subprocess.check_output(
            ["git", *args],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "UNKNOWN"


def clean_record(record):
    cleaned = {}
    for key, value in record.items():
        if isinstance(value, pd.Timestamp):
            cleaned[key] = value.date().isoformat()
        elif value is None or (not isinstance(value, str) and pd.isna(value)):
            cleaned[key] = ""
        elif isinstance(value, (bool, int, str)):
            cleaned[key] = value
        elif hasattr(value, "item"):
            cleaned[key] = value.item()
        else:
            cleaned[key] = value
    return cleaned


def write_csv(records, path, fieldnames=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame([clean_record(record) for record in records])
    if fieldnames is not None:
        frame = frame.reindex(columns=fieldnames)
    frame.to_csv(path, index=False)
    return len(frame)


def load_metadata(master_path, tickers):
    columns = ["Ticker", "Symbol", "Security Name", "Listing Exchange", "MarketCap", "Sector", "Industry"]
    if not master_path.exists():
        return {}, pd.DataFrame(columns=columns)
    frame = pd.read_csv(master_path)
    ticker_column = "Ticker" if "Ticker" in frame.columns else "Symbol"
    frame[ticker_column] = frame[ticker_column].astype(str).str.strip().str.upper()
    subset = frame[frame[ticker_column].isin(tickers)].copy()
    available = [column for column in columns if column in subset.columns]
    snapshot = subset[available].copy()
    metadata = {}
    for _, row in subset.iterrows():
        ticker = str(row[ticker_column]).strip().upper()
        metadata[ticker] = {
            "Security_Name": row.get("Security Name", ""),
            "Listing_Exchange": row.get("Listing Exchange", ""),
            "MarketCap": row.get("MarketCap", ""),
            "Sector": row.get("Sector", "Unknown") or "Unknown",
            "Industry": row.get("Industry", "Unknown") or "Unknown",
        }
    return metadata, snapshot


def save_prices(df, path):
    output = df.copy()
    output.index.name = "Date"
    path.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(path, date_format="%Y-%m-%d")


def timing_for_history(calc_df):
    return engine.evaluate_intraday_timing(calc_df, pd.DataFrame(), quote={})


def market_regime(benchmark_df, signal_date):
    history = benchmark_df.loc[benchmark_df.index <= signal_date, "Close"].dropna()
    if len(history) < 250:
        return "UNAVAILABLE"
    ema_200 = engine.ema(history, 200)
    latest_ema = finite_number(ema_200.iloc[-1])
    prior_ema = finite_number(ema_200.iloc[-51]) if len(ema_200) >= 251 else None
    close = finite_number(history.iloc[-1])
    if latest_ema is None or prior_ema is None or close is None or prior_ema == 0:
        return "UNAVAILABLE"
    slope = ((latest_ema / prior_ema) - 1.0) * 100.0
    if close > latest_ema and slope > 0:
        return "BULL"
    if close < latest_ema and slope < 0:
        return "BEAR"
    return "TRANSITION"


def forward_outcomes(raw_df, signal_position):
    result = {"Entry_Date": "", "Entry_Open": ""}
    for horizon in FORWARD_HORIZONS:
        result[f"Forward_{horizon}D_Return_Pct"] = ""
    for window in PATH_WINDOWS:
        result[f"MAE_{window}D_Pct"] = ""
        result[f"MFE_{window}D_Pct"] = ""
        result[f"Realized_Volatility_{window}D_Annualized_Pct"] = ""

    entry_position = signal_position + 1
    if entry_position >= len(raw_df):
        return result
    entry_open = finite_number(raw_df["Open"].iloc[entry_position])
    if entry_open is None or entry_open <= 0:
        return result
    result["Entry_Date"] = raw_df.index[entry_position].date().isoformat()
    result["Entry_Open"] = entry_open

    for horizon in FORWARD_HORIZONS:
        target_position = signal_position + horizon
        if target_position < len(raw_df):
            target_close = finite_number(raw_df["Close"].iloc[target_position])
            if target_close is not None:
                result[f"Forward_{horizon}D_Return_Pct"] = ((target_close / entry_open) - 1.0) * 100.0

    for window in PATH_WINDOWS:
        end_position = signal_position + window
        if end_position >= len(raw_df):
            continue
        path = raw_df.iloc[entry_position : end_position + 1]
        result[f"MAE_{window}D_Pct"] = ((path["Low"].min() / entry_open) - 1.0) * 100.0
        result[f"MFE_{window}D_Pct"] = ((path["High"].max() / entry_open) - 1.0) * 100.0
        daily_returns = path["Close"].pct_change(fill_method=None).dropna()
        if len(daily_returns) >= 2:
            result[f"Realized_Volatility_{window}D_Annualized_Pct"] = daily_returns.std(ddof=1) * math.sqrt(252) * 100.0
    return result


def replay_ticker(ticker, raw_df, benchmark_df, benchmark_ticker, metadata):
    exchange_profile = engine.exchange_profile_for_ticker(ticker, "auto")
    calc_df = engine.calculate_v5_indicators(
        raw_df,
        benchmark_df,
        benchmark_ticker=benchmark_ticker,
        exchange_profile=exchange_profile,
    )
    signals = []
    daily_audit = []
    prior_active = False
    episode_number = 0

    for position in range(engine.MIN_HISTORY_BARS - 1, len(calc_df)):
        history = calc_df.iloc[: position + 1]
        row = history.iloc[-1]
        scores, weekly_trend = engine.score_v5(row)
        timing = timing_for_history(history)
        scores = engine.apply_commercial_readiness_score(row, scores, weekly_trend, timing)
        long_term_status, reason = engine.classify_signal(row, scores, weekly_trend, timing)
        output = engine.build_output_row(
            ticker,
            row,
            scores,
            weekly_trend,
            timing,
            long_term_status,
            reason,
        )
        active = beta_context.is_beta_postprocessor_eligible(output, engine.CONFIRMED_ENTRY_MIN_SCORE)
        signal_date = calc_df.index[position]
        episode_start = active and not prior_active
        daily_audit.append(
            {
                "Ticker": ticker,
                "Signal_Date": signal_date.date().isoformat(),
                "Final_Decision": output["Final_Decision"],
                "Score": output["Score"],
                "Active_Threshold": engine.CONFIRMED_ENTRY_MIN_SCORE,
                "Episode_Start": episode_start,
                "Final_Decision_Reason": output["Final_Decision_Reason"],
            }
        )

        if episode_start:
            episode_number += 1
            stock_history = raw_df.loc[raw_df.index <= signal_date]
            benchmark_history = benchmark_df.loc[benchmark_df.index <= signal_date]
            beta = beta_context.calculate_beta_context(stock_history, benchmark_history, benchmark_ticker)
            signal = {
                "Signal_ID": f"{ticker}_{signal_date.strftime('%Y%m%d')}_{episode_number:03d}",
                "Ticker": ticker,
                "Signal_Date": signal_date.date().isoformat(),
                "Episode_Number": episode_number,
                "Final_Decision": output["Final_Decision"],
                "Score": output["Score"],
                "Active_Threshold": engine.CONFIRMED_ENTRY_MIN_SCORE,
                "Score_Message": beta_context.build_beta_message(beta),
                "Benchmark_Ticker": benchmark_ticker,
                "Market_Regime": market_regime(benchmark_history, signal_date),
                **metadata,
                **beta,
                **forward_outcomes(raw_df, position),
            }
            signals.append(signal)
        prior_active = active
    return signals, daily_audit


def numeric_summary(frame, grouping):
    return_columns = [f"Forward_{horizon}D_Return_Pct" for horizon in FORWARD_HORIZONS]
    path_columns = [
        column
        for window in PATH_WINDOWS
        for column in (f"MAE_{window}D_Pct", f"MFE_{window}D_Pct", f"Realized_Volatility_{window}D_Annualized_Pct")
    ]
    rows = []
    if frame.empty:
        return rows
    for keys, group in frame.groupby(grouping, dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        row = dict(zip(grouping, keys))
        row["Signal_Count"] = len(group)
        row["Unique_Tickers"] = group["Ticker"].nunique()
        for column in return_columns:
            values = pd.to_numeric(group[column], errors="coerce").dropna()
            row[f"Mean_{column}"] = values.mean() if not values.empty else ""
            row[f"Median_{column}"] = values.median() if not values.empty else ""
            row[f"Positive_Rate_{column}"] = (values > 0).mean() * 100 if not values.empty else ""
        for column in path_columns:
            values = pd.to_numeric(group[column], errors="coerce").dropna()
            row[f"Median_{column}"] = values.median() if not values.empty else ""
        rows.append(row)
    return rows


def write_random_validation_sample(signals, validation_dir, seed, sample_size):
    sample_size = min(sample_size, len(signals))
    if sample_size == 0:
        write_csv([], validation_dir / "random_round_01_sample.csv", ["Validation_Order", "Signal_ID"])
        return 0
    selected_indexes = random.Random(seed).sample(range(len(signals)), sample_size)
    records = []
    expected = []
    for validation_order, index in enumerate(selected_indexes, start=1):
        signal = signals[index]
        records.append(
            {
                "Validation_Order": validation_order,
                "Signal_ID": signal["Signal_ID"],
                "Ticker": signal["Ticker"],
                "Signal_Date": signal["Signal_Date"],
                "Stored_Input_File": f"inputs/prices/{signal['Ticker']}.csv",
                "Benchmark_Input_File": f"inputs/benchmarks/{signal['Benchmark_Ticker']}.csv",
                "Validation_Status": "PENDING_OFFLINE_REVIEW",
            }
        )
        expected.append({"Validation_Order": validation_order, **signal})
    write_csv(records, validation_dir / "random_round_01_sample.csv")
    write_csv(expected, validation_dir / "random_round_01_expected.csv")
    return sample_size


def write_checksums(run_dir):
    checksum_path = run_dir / "checksums.sha256"
    lines = []
    for path in sorted(run_dir.rglob("*")):
        if not path.is_file() or path == checksum_path:
            continue
        relative = path.relative_to(run_dir).as_posix()
        lines.append(f"{sha256_file(path)}  {relative}")
    checksum_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(lines)


def parse_args():
    parser = argparse.ArgumentParser(description="Traceable V8 Release-1 Beta backtest")
    parser.add_argument("--tickers", nargs="+", default=DEFAULT_PILOT_TICKERS)
    parser.add_argument("--period", default="10y")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--validation-sample-size", type=int, default=50)
    return parser.parse_args()


def main():
    args = parse_args()
    tickers = list(dict.fromkeys(str(ticker).strip().upper() for ticker in args.tickers if str(ticker).strip()))
    commit = git_value("rev-parse", "--short", "HEAD")
    started = datetime.now(timezone.utc)
    run_id = f"V8BETA_{started.strftime('%Y%m%dT%H%M%SZ')}_{commit}_{args.seed}"
    run_dir = args.output_root.resolve() / run_id
    inputs_dir = run_dir / "inputs"
    outputs_dir = run_dir / "outputs"
    validation_dir = run_dir / "validation"
    for directory in (inputs_dir, outputs_dir, validation_dir):
        directory.mkdir(parents=True, exist_ok=True)

    source_snapshot_dir = inputs_dir / "source_snapshot"
    (source_snapshot_dir / "config").mkdir(parents=True, exist_ok=True)
    source_files = [
        Path(engine.__file__),
        Path(beta_context.__file__),
        Path(__file__),
        Path(__file__).resolve().parent / "Validate_V8_Beta_Backtest.py",
    ]
    for source_file in source_files:
        shutil.copy2(source_file, source_snapshot_dir / source_file.name)
    shutil.copy2(
        beta_context.DEFAULT_MESSAGE_MAP,
        source_snapshot_dir / "config" / beta_context.DEFAULT_MESSAGE_MAP.name,
    )

    metadata, universe_snapshot = load_metadata(engine.TICKER_INPUT_CSV, tickers)
    universe_snapshot.to_csv(inputs_dir / "universe_snapshot.csv", index=False)

    price_cache = {}
    benchmark_cache = {}
    signals = []
    daily_audit = []
    failures = []
    for ticker in tickers:
        print(f"Downloading and replaying {ticker}...")
        raw_df = engine.fetch_daily_data(ticker, args.period)
        if len(raw_df) < engine.MIN_HISTORY_BARS:
            failures.append({"Ticker": ticker, "Reason": f"only {len(raw_df)} price bars"})
            continue
        price_cache[ticker] = raw_df
        save_prices(raw_df, inputs_dir / "prices" / f"{ticker}.csv")
        benchmark_ticker = engine.benchmark_for_ticker(ticker, "auto", engine.US_DEFAULT_BENCHMARK)
        if benchmark_ticker not in benchmark_cache:
            benchmark_cache[benchmark_ticker] = engine.fetch_daily_data(benchmark_ticker, args.period)
            save_prices(benchmark_cache[benchmark_ticker], inputs_dir / "benchmarks" / f"{benchmark_ticker}.csv")
        ticker_signals, ticker_audit = replay_ticker(
            ticker,
            raw_df,
            benchmark_cache[benchmark_ticker],
            benchmark_ticker,
            metadata.get(
                ticker,
                {
                    "Security_Name": "",
                    "Listing_Exchange": "",
                    "MarketCap": "",
                    "Sector": "Unknown",
                    "Industry": "Unknown",
                },
            ),
        )
        signals.extend(ticker_signals)
        daily_audit.extend(ticker_audit)

    signal_count = write_csv(signals, outputs_dir / "signal_audit.csv")
    daily_count = write_csv(daily_audit, outputs_dir / "daily_decision_audit.csv")
    write_csv(failures, outputs_dir / "download_failures.csv", ["Ticker", "Reason"])
    signal_frame = pd.DataFrame(signals)
    summary_specs = {
        "beta_band_summary.csv": ["Beta_Risk_Band"],
        "beta_market_interactions.csv": ["Beta_Risk_Band", "Market_Regime"],
        "beta_sector_interactions.csv": ["Beta_Risk_Band", "Sector"],
        "beta_industry_interactions.csv": ["Beta_Risk_Band", "Industry"],
    }
    for filename, grouping in summary_specs.items():
        records = numeric_summary(signal_frame, grouping) if not signal_frame.empty else []
        write_csv(records, outputs_dir / filename, [*grouping, "Signal_Count", "Unique_Tickers"] if not records else None)

    sample_count = write_random_validation_sample(
        signals,
        validation_dir,
        args.seed,
        args.validation_sample_size,
    )
    completed = datetime.now(timezone.utc)
    manifest = {
        "Run_ID": run_id,
        "Started_UTC": started.isoformat(),
        "Completed_UTC": completed.isoformat(),
        "Replay_Mode": "HISTORICAL_DAILY_EOD_EPISODE_START",
        "Engine_File": "Momentum_Detector_V8.py",
        "Engine_SHA256": sha256_file(Path(engine.__file__)),
        "Beta_Module_SHA256": sha256_file(Path(beta_context.__file__)),
        "Message_Map_SHA256": sha256_file(beta_context.DEFAULT_MESSAGE_MAP),
        "Git_Commit": git_value("rev-parse", "HEAD"),
        "Git_Worktree_Dirty": bool(git_value("status", "--porcelain")),
        "Python": sys.version,
        "Pandas": pd.__version__,
        "YFinance": getattr(engine.yf, "__version__", "UNKNOWN"),
        "Random_Seed": args.seed,
        "Requested_Period": args.period,
        "Requested_Tickers": tickers,
        "Completed_Tickers": sorted(price_cache),
        "Active_Trigger": {
            "Final_Decision": "MOMENTUM_ACTIVE",
            "Minimum_Score": engine.CONFIRMED_ENTRY_MIN_SCORE,
            "CLI_Filter_Used": False,
        },
        "Beta_Parameters": {
            "Window_Returns": beta_context.DEFAULT_BETA_WINDOW,
            "Minimum_Observations": beta_context.DEFAULT_MIN_BETA_OBSERVATIONS,
            "Weak_Fit_R2": beta_context.DEFAULT_WEAK_FIT_R2,
            "Benchmark": engine.US_DEFAULT_BENCHMARK,
        },
        "Row_Counts": {
            "Signals": signal_count,
            "Daily_Decisions": daily_count,
            "Random_Validation_Sample": sample_count,
            "Random_Validation_Expected": sample_count,
            "Failures": len(failures),
        },
        "Offline_Traceability": {
            "Source_Snapshot": "inputs/source_snapshot",
            "Stored_Prices": "inputs/prices",
            "Stored_Benchmarks": "inputs/benchmarks",
            "Random_Sample": "validation/random_round_01_sample.csv",
            "Expected_Values": "validation/random_round_01_expected.csv",
            "Checksum_File": "checksums.sha256",
        },
        "Forward_Return_Convention": "Signal at day D close; hypothetical entry at D+1 open; horizon N exits at D+N close.",
        "Known_Limitations": [
            "Daily replay cannot reconstruct historical intraday, pre-market, post-market, analyst, EPS, or event messages.",
            "This pilot is an episode-start observational study, not a portfolio simulation and not investment advice.",
            "Sector and industry labels are the stored master-library snapshot, not point-in-time classifications.",
        ],
    }
    (run_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    checksum_count = write_checksums(run_dir)
    print(f"Run complete: {run_dir}")
    print(f"Signals: {signal_count} | Daily decisions: {daily_count} | Hashed artifacts: {checksum_count}")
    return 0 if signal_count else 2


if __name__ == "__main__":
    raise SystemExit(main())
