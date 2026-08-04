import os
import json
import time
import random
import logging
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import pandas as pd
import numpy as np


# -----------------------------
# CONFIG
# -----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

INPUT_FILE = os.path.join(BASE_DIR, "input", "matched-Filtered.csv")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
LOG_DIR = os.path.join(BASE_DIR, "logs")

MAX_WORKERS = 16
MAX_RETRIES = 3
TIMEOUT = 10
BASE_BACKOFF = 0.5

DRY_RUN = False


# -----------------------------
# ENV VALIDATION
# -----------------------------
def validate_environment():
    errors = []

    if not os.path.exists(INPUT_FILE):
        errors.append(f"Missing input file: {INPUT_FILE}")
    elif not os.access(INPUT_FILE, os.R_OK):
        errors.append(f"No read access: {INPUT_FILE}")
    elif os.path.getsize(INPUT_FILE) == 0:
        errors.append(f"Input file is empty: {INPUT_FILE}")

    for d in (OUTPUT_DIR, LOG_DIR):
        if not os.path.exists(d):
            try:
                os.makedirs(d, exist_ok=True)
            except Exception as e:
                errors.append(f"Cannot create {d}: {e}")
        elif not os.access(d, os.W_OK):
            errors.append(f"No write access: {d}")

    if errors:
        raise RuntimeError("\n".join(errors))


# -----------------------------
# LOGGING
# -----------------------------
def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(os.path.join(LOG_DIR, "run.log")),
            logging.StreamHandler()
        ]
    )


# -----------------------------
# LOAD INPUT
# -----------------------------
def load_and_validate_funds():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        raw = [line.strip() for line in f]

    seen, unique, duplicates = set(), [], set()

    for i, fund in enumerate(raw, 1):
        if not fund:
            logging.warning(f"Empty line {i}")
            continue

        if fund in seen:
            duplicates.add(fund)
        else:
            seen.add(fund)
            unique.append(fund)

    if duplicates:
        pd.DataFrame({"duplicate": list(duplicates)}).to_csv(
            os.path.join(OUTPUT_DIR, "duplicate_funds.csv"), index=False
        )

    logging.info(f"Loaded {len(unique)} unique funds")
    return unique


# -----------------------------
# AMFI MASTER
# -----------------------------
def fetch_amfi_master():
    url = "https://www.amfiindia.com/spages/NAVAll.txt"
    r = requests.get(url, timeout=TIMEOUT)
    r.raise_for_status()

    rows = []
    for line in r.text.split("\n"):
        parts = line.split(";")
        if len(parts) > 5:
            rows.append((parts[3], parts[0]))

    return pd.DataFrame(rows, columns=["scheme_name", "scheme_code"])


# -----------------------------
# MAPPING
# -----------------------------
def build_mapping(funds, amfi_df):
    lookup = dict(zip(amfi_df["scheme_name"], amfi_df["scheme_code"]))

    mapping, missing = {}, []

    for fund in funds:
        if fund in lookup:
            mapping[fund] = lookup[fund]
        else:
            missing.append(fund)

    if missing:
        pd.DataFrame({"missing": missing}).to_csv(
            os.path.join(OUTPUT_DIR, "unmatched_funds.csv"), index=False
        )

    logging.info(f"Mapped: {len(mapping)} | Missing: {len(missing)}")
    return mapping


# -----------------------------
# FETCH NAV
# -----------------------------
def fetch_nav_history(code):
    url = f"https://api.mfapi.in/mf/{code}"

    for attempt in range(MAX_RETRIES):
        try:
            r = requests.get(url, timeout=TIMEOUT)
            if r.status_code != 200:
                raise Exception(r.status_code)

            data = r.json().get("data", [])
            if not data:
                return None

            df = pd.DataFrame(data)
            df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y")
            df["nav"] = df["nav"].astype(float)

            return df.sort_values("date")[["date", "nav"]]

        except:
            if attempt == MAX_RETRIES - 1:
                return None
            time.sleep(BASE_BACKOFF * (2 ** attempt))


# -----------------------------
# LOOKUP
# -----------------------------
def nav_lookup(df, target):
    dates = df["date"].values.astype("datetime64[ns]")
    idx = np.searchsorted(dates, np.datetime64(target), side="right") - 1
    return None if idx < 0 else df["nav"].iloc[idx]


# -----------------------------
# DATES
# -----------------------------
def get_dates():
    t = datetime.today()
    return {
        "TODAY": t,
        "1M": t - timedelta(days=30),
        "3M": t - timedelta(days=90),
        "6M": t - timedelta(days=180),
        "YTD": datetime(t.year, 1, 1),
    }


# -----------------------------
# ENGINE (FIXED)
# -----------------------------
def run_engine(mapping):
    dates = get_dates()

    results = {"1M": [], "3M": [], "6M": [], "YTD": []}

    success, failed = 0, 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(fetch_nav_history, c): f for f, c in mapping.items()}

        for i, fut in enumerate(as_completed(futures), 1):
            fund = futures[fut]

            try:
                df = fut.result()
                if df is None:
                    failed += 1
                    continue

                nav_today = nav_lookup(df, dates["TODAY"])
                if nav_today is None:
                    failed += 1
                    continue

                for period in ["1M", "3M", "6M", "YTD"]:
                    nav_from = nav_lookup(df, dates[period])

                    if nav_from is not None:
                        ret = ((nav_today - nav_from) / nav_from) * 100
                        results[period].append((fund, ret))

                success += 1

            except Exception as e:
                logging.error(f"Error processing {fund}: {e}")
                failed += 1

            if i % 100 == 0:
                logging.info(f"{i} funds processed")

    return results, success, failed


# -----------------------------
# RANK WITH VALIDATION
# -----------------------------
def rank(results):
    output = []

    for period, vals in results.items():

        if len(vals) < 3:
            logging.warning(
                f"{period}: Only {len(vals)} funds available (<3). Output will be partial."
            )

        top3 = sorted(vals, key=lambda x: x[1], reverse=True)[:3]

        row = {"Period": period}

        # Always fill 3 columns even if missing
        for i in range(3):
            if i < len(top3):
                fund, ret = top3[i]
                row[f"Top{i+1} Fund"] = fund
                row[f"Top{i+1} Return %"] = round(ret, 2)
            else:
                row[f"Top{i+1} Fund"] = "N/A"
                row[f"Top{i+1} Return %"] = "N/A"

        output.append(row)

    df = pd.DataFrame(output)
    df.to_csv(os.path.join(OUTPUT_DIR, "top_funds_output.csv"), index=False)

    return df


# -----------------------------
# MAIN
# -----------------------------
def main():
    validate_environment()
    setup_logging()

    logging.info("Pipeline start")

    funds = load_and_validate_funds()
    amfi = fetch_amfi_master()
    mapping = build_mapping(funds, amfi)

    if DRY_RUN:
        logging.info("Dry run only")
        return

    results, success, failed = run_engine(mapping)
    final = rank(results)

    summary = {
        "total_input": len(funds),
        "mapped": len(mapping),
        "success": success,
        "failed": failed,
        "timestamp": datetime.now().isoformat()
    }

    with open(os.path.join(OUTPUT_DIR, "run_summary.json"), "w") as f:
        json.dump(summary, f, indent=4)

    logging.info(summary)
    print("\nFinal Output:\n", final)


if __name__ == "__main__":
    main()