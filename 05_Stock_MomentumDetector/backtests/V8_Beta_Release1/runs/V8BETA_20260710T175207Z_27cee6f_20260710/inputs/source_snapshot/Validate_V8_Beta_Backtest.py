import argparse
import hashlib
import importlib
import math
import sys
from pathlib import Path

import pandas as pd


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_checksums(run_dir):
    failures = []
    checksum_path = run_dir / "checksums.sha256"
    listed_files = set()
    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", 1)
        listed_files.add(Path(relative).as_posix())
        path = run_dir / Path(relative)
        if not path.is_file():
            failures.append(f"missing: {relative}")
        elif sha256_file(path) != expected:
            failures.append(f"hash mismatch: {relative}")
    actual_files = {
        path.relative_to(run_dir).as_posix()
        for path in run_dir.rglob("*")
        if path.is_file() and path != checksum_path
    }
    for relative in sorted(actual_files - listed_files):
        failures.append(f"unexpected file not in checksum inventory: {relative}")
    return failures


def load_prices(path):
    frame = pd.read_csv(path, parse_dates=["Date"], index_col="Date")
    frame.index = pd.to_datetime(frame.index).tz_localize(None).normalize()
    return frame


def close_enough(left, right, tolerance=1e-9):
    try:
        left_number = float(left)
        right_number = float(right)
    except (TypeError, ValueError):
        return str(left) == str(right)
    if math.isnan(left_number) and math.isnan(right_number):
        return True
    return math.isclose(left_number, right_number, rel_tol=tolerance, abs_tol=tolerance)


def recompute_signal(engine, beta_context, ticker, signal_date, stock_df, benchmark_df):
    benchmark_ticker = engine.benchmark_for_ticker(ticker, "auto", engine.US_DEFAULT_BENCHMARK)
    calc_df = engine.calculate_v5_indicators(
        stock_df,
        benchmark_df,
        benchmark_ticker=benchmark_ticker,
        exchange_profile=engine.exchange_profile_for_ticker(ticker, "auto"),
    )
    signal_timestamp = pd.Timestamp(signal_date)
    history = calc_df.loc[calc_df.index <= signal_timestamp]
    row = history.iloc[-1]
    scores, weekly_trend = engine.score_v5(row)
    timing = engine.evaluate_intraday_timing(history, pd.DataFrame(), quote={})
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
    beta = beta_context.calculate_beta_context(
        stock_df.loc[stock_df.index <= signal_timestamp],
        benchmark_df.loc[benchmark_df.index <= signal_timestamp],
        benchmark_ticker,
    )
    return output, beta


def parse_args():
    parser = argparse.ArgumentParser(description="Read-only offline validator for a stored V8 Beta run")
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--limit", type=int, default=0, help="Validate only the first N sampled rows; zero validates all")
    return parser.parse_args()


def main():
    args = parse_args()
    run_dir = args.run_dir.resolve()
    checksum_failures = verify_checksums(run_dir)
    if checksum_failures:
        for failure in checksum_failures:
            print(f"CHECKSUM_FAIL: {failure}")
        return 1

    source_dir = run_dir / "inputs" / "source_snapshot"
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(source_dir))
    engine = importlib.import_module("Momentum_Detector_V8")
    beta_context = importlib.import_module("Beta_Context_V8")
    expected = pd.read_csv(run_dir / "validation" / "random_round_01_expected.csv")
    if args.limit > 0:
        expected = expected.head(args.limit)

    failures = []
    price_cache = {}
    benchmark_cache = {}
    for _, record in expected.iterrows():
        ticker = str(record["Ticker"])
        benchmark_ticker = str(record["Benchmark_Ticker"])
        if ticker not in price_cache:
            price_cache[ticker] = load_prices(run_dir / "inputs" / "prices" / f"{ticker}.csv")
        if benchmark_ticker not in benchmark_cache:
            benchmark_cache[benchmark_ticker] = load_prices(
                run_dir / "inputs" / "benchmarks" / f"{benchmark_ticker}.csv"
            )
        output, beta = recompute_signal(
            engine,
            beta_context,
            ticker,
            record["Signal_Date"],
            price_cache[ticker],
            benchmark_cache[benchmark_ticker],
        )
        comparisons = {
            "Final_Decision": output["Final_Decision"],
            "Score": output["Score"],
            "Beta_252D": beta["Beta_252D"],
            "Beta_R2_252D": beta["Beta_R2_252D"],
            "Beta_Risk_Band": beta["Beta_Risk_Band"],
        }
        for field, actual in comparisons.items():
            if not close_enough(record[field], actual):
                failures.append(
                    f"{record['Signal_ID']} {field}: stored={record[field]!r}, recomputed={actual!r}"
                )

    if failures:
        for failure in failures:
            print(f"REPLAY_FAIL: {failure}")
        return 1
    print(f"PASS: {len(expected)} sampled signals replayed exactly; all stored checksums are valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
