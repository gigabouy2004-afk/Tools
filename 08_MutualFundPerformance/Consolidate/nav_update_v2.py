import pandas as pd
import requests
import re
import os
import sys
import time
from copy import copy
from datetime import datetime, date, timedelta
from openpyxl import load_workbook
from openpyxl.utils import column_index_from_string, get_column_letter

# =========================
# CONFIG
# =========================
FILE_PATH = r"D:\Tools\MutualFundPerformance\Consolidate\ALL_MF_NAV_PullupSheet.xlsx"
SHEET_NAME = "NAV PullSheet"
AMFI_URL = "https://www.amfiindia.com/spages/NAVAll.txt"
AMFI_HISTORY_URL = "https://portal.amfiindia.com/DownloadNAVHistoryReport_Po.aspx"
MATCH_THRESHOLD = 3
LOG_FILE = "nav_update_log.txt"
DATE_START_COL = 10  # Column K to represent column - "01-Jan"
MIN_ALLOWED_DATE = date(2026, 1, 1)
MIN_CORE_TOKENS = 4
BLOCKED_FALLBACK_TOKENS = {"liquid", "overnight"}

# =========================
# CLI DATE (OPTIONAL)
# =========================
input_date = sys.argv[1] if len(sys.argv) > 1 else None

# =========================
# LOGGING
# =========================
def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except:
        pass

# =========================
# DATE RESOLUTION
# =========================
def format_header_date(d):
    return f"{d.day}-{d.strftime('%b')}"


def parse_date_value(value, default_year=None, allow_partial=True):
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    text = str(value).strip()
    if not text or text.startswith("="):
        return None

    formats = [
        "%Y-%m-%d",
        "%d-%b-%Y",
        "%d-%B-%Y",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%B %d %Y",
        "%b %d %Y",
        "%B %d, %Y",
        "%b %d, %Y",
        "%d %B %Y",
        "%d %b %Y",
    ]

    for fmt in formats:
        try:
            parsed = datetime.strptime(text, fmt)
            return date(parsed.year, parsed.month, parsed.day)
        except ValueError:
            continue

    if allow_partial:
        year = default_year or datetime.today().year
        for fmt in ("%d-%b-%Y", "%d-%B-%Y"):
            try:
                parsed = datetime.strptime(f"{text}-{year}", fmt)
                return date(parsed.year, parsed.month, parsed.day)
            except ValueError:
                continue

    return None


def parse_partial_date_value(value):
    if value is None:
        return None

    text = str(value).strip()
    if not text or text.startswith("="):
        return None

    for fmt in ("%d-%b-%Y", "%d-%B-%Y"):
        try:
            parsed = datetime.strptime(f"{text}-2000", fmt)
            return parsed.month, parsed.day
        except ValueError:
            continue

    return None


def resolve_date(d):
    if d:
        parsed = parse_date_value(d, datetime.today().year)
        if parsed is None:
            raise ValueError(f"Invalid date format: {d}")
    else:
        parsed = datetime.today().date()

    return parsed


def validate_target_date(target_date):
    if target_date < MIN_ALLOWED_DATE:
        raise ValueError(
            "Input date must be on or after "
            f"{format_header_date(MIN_ALLOWED_DATE)}-{MIN_ALLOWED_DATE.year}"
        )


def resolve_formula_date(formula, date_by_col):
    if not isinstance(formula, str) or not formula.startswith("="):
        return None

    match = re.fullmatch(r"=([A-Z]+)1\s*([+-])\s*(\d+)", formula.strip(), re.I)
    if not match:
        return None

    ref_col = column_index_from_string(match.group(1).upper())
    ref_date = date_by_col.get(ref_col)
    if ref_date is None:
        return None

    days = int(match.group(3))
    if match.group(2) == "-":
        days = -days

    return ref_date + timedelta(days=days)


def infer_partial_header_year(col, date_by_col, fallback_year):
    known_cols = sorted(date_by_col)

    previous_cols = [known_col for known_col in known_cols if known_col < col]
    if previous_cols:
        return date_by_col[previous_cols[-1]].year

    next_cols = [known_col for known_col in known_cols if known_col > col]
    if next_cols:
        return date_by_col[next_cols[0]].year

    return fallback_year


def get_date_columns(ws, target_year):
    date_by_col = {}

    for col in range(DATE_START_COL, ws.max_column + 1):
        parsed = parse_date_value(
            ws.cell(row=1, column=col).value,
            allow_partial=False,
        )
        if parsed is not None:
            date_by_col[col] = parsed

    changed = True
    while changed:
        changed = False
        for col in range(DATE_START_COL, ws.max_column + 1):
            if col in date_by_col:
                continue

            parsed = resolve_formula_date(ws.cell(row=1, column=col).value, date_by_col)
            if parsed is not None:
                date_by_col[col] = parsed
                changed = True

    for col in range(DATE_START_COL, ws.max_column + 1):
        if col in date_by_col:
            continue

        partial = parse_partial_date_value(ws.cell(row=1, column=col).value)
        if partial is None:
            continue

        year = infer_partial_header_year(col, date_by_col, target_year)
        month, day = partial
        date_by_col[col] = date(year, month, day)

    return date_by_col


def copy_column_style(ws, source_col, target_col):
    if source_col < 1:
        return

    for row in range(1, ws.max_row + 1):
        source = ws.cell(row=row, column=source_col)
        target = ws.cell(row=row, column=target_col)
        if source.has_style:
            target._style = copy(source._style)
        if source.number_format:
            target.number_format = source.number_format
        if source.alignment:
            target.alignment = copy(source.alignment)
        if source.font:
            target.font = copy(source.font)
        if source.fill:
            target.fill = copy(source.fill)
        if source.border:
            target.border = copy(source.border)


def write_header_date(ws, col, header_date):
    header = ws.cell(row=1, column=col)
    header.value = datetime.combine(header_date, datetime.min.time())
    header.number_format = "d-mmm"


def find_or_insert_date_column(ws, target_date):
    date_by_col = get_date_columns(ws, target_date.year)
    matches = [col for col, header_date in date_by_col.items() if header_date == target_date]

    if matches:
        col = matches[0]
        log(f"Updating existing column {get_column_letter(col)}: {format_header_date(target_date)}")
        return col

    previous_cols = [
        (header_date, col)
        for col, header_date in date_by_col.items()
        if header_date < target_date
    ]

    if previous_cols:
        _, previous_col = max(previous_cols)
        insert_col = previous_col + 1
    else:
        insert_col = DATE_START_COL

    ws.insert_cols(insert_col)
    style_source_col = insert_col - 1 if insert_col > DATE_START_COL else insert_col + 1
    copy_column_style(ws, style_source_col, insert_col)

    for old_col, header_date in sorted(date_by_col.items(), reverse=True):
        if old_col >= insert_col:
            write_header_date(ws, old_col + 1, header_date)

    write_header_date(ws, insert_col, target_date)

    log(
        f"Created new column {get_column_letter(insert_col)}: "
        f"{format_header_date(target_date)}"
    )

    return insert_col

# =========================
# NORMALIZE TEXT
# =========================
def normalize(text):
    text = str(text).lower()
    text = text.replace("\xa0", " ")
    text = text.replace("off-shore", "offshore")
    text = text.replace("off shore", "offshore")
    text = text.replace("u.s.", "us")
    text = text.replace("u s", "us")
    text = re.sub(r'[^a-z0-9 ]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def name_tokens(text):
    return set(normalize(text).split())


def get_plan(text):
    tokens = normalize(text).split()
    if "direct" in tokens:
        return "direct"
    if "regular" in tokens:
        return "regular"
    return None


def get_option(text):
    tokens = normalize(text).split()
    return "idcw" if "idcw" in tokens else "growth"


def get_core(text):
    clean = str(text).replace("\xa0", " ").strip()
    if " - " in clean:
        clean = clean.split(" - ", 1)[0]
    else:
        clean = clean[:20]
        if len(str(text).replace("\xa0", " ").strip()) > 20 and " " in clean:
            clean = clean.rsplit(" ", 1)[0]

    return normalize(clean)


def contains_all_tokens(name, required_parts):
    tokens = name_tokens(name)

    for part in required_parts:
        part_tokens = name_tokens(part)
        if not part_tokens.issubset(tokens):
            return False

    return True


def find_best_nav_match(fund, df_amfi):
    target = normalize(fund)
    plan = get_plan(fund)
    option = get_option(fund)
    core = get_core(fund)

    exact = df_amfi[df_amfi["normalized_name"] == target]
    if not exact.empty:
        return "exact", exact.iloc[0]["nav"]

    plan_option_parts = [core, option]
    if plan is not None:
        plan_option_parts.insert(1, plan)

    plan_option = df_amfi[
        df_amfi["name"].apply(
            lambda name: len(name_tokens(core)) >= MIN_CORE_TOKENS
            and contains_all_tokens(name, plan_option_parts)
        )
    ]
    if not plan_option.empty:
        return "core+plan+option", plan_option.iloc[0]["nav"]

    core_only = df_amfi[
        df_amfi["name"].apply(
            lambda name: len(name_tokens(core)) >= MIN_CORE_TOKENS
            and contains_all_tokens(name, [core])
        )
    ]
    if not core_only.empty:
        return "core", core_only.iloc[0]["nav"]

    short_core_plan_option = df_amfi[
        df_amfi["name"].apply(
            lambda name: contains_all_tokens(name, plan_option_parts)
            and not (name_tokens(name) & BLOCKED_FALLBACK_TOKENS)
        )
    ]
    if not short_core_plan_option.empty:
        return "short-core+plan+option", short_core_plan_option.iloc[0]["nav"]

    return None, None

# =========================
# FILE VALIDATION
# =========================
def validate_file(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")
    if not os.access(path, os.R_OK):
        raise PermissionError("No read access")

# =========================
# LOAD SHEET
# =========================
def load_sheet(path, sheet_name):
    wb = load_workbook(path)
    if sheet_name not in wb.sheetnames:
        raise ValueError(f"Sheet not found: {sheet_name}")
    return wb, wb[sheet_name]


def amfi_date(d):
    return f"{d.day:02d}-{d.strftime('%b')}-{d.year}"


def parse_amfi_line(line):
    if ";" not in line:
        return None

    parts = [part.strip() for part in line.split(";")]

    # Historical NAV download:
    # Scheme Code;Scheme Name;ISIN Div Payout/ISIN Growth;ISIN Div Reinvestment;
    # Net Asset Value;Repurchase Price;Sale Price;Date
    if len(parts) >= 8 and parts[0].isdigit():
        return {
            "scheme_code": parts[0],
            "name": parts[1],
            "nav": parts[4],
            "date": parts[7],
        }

    # Latest NAVAll.txt:
    # Scheme Code;ISIN Div Payout/ISIN Growth;ISIN Div Reinvestment;
    # Scheme Name;Net Asset Value;Date
    if len(parts) >= 6 and parts[0].isdigit():
        return {
            "scheme_code": parts[0],
            "name": parts[3],
            "nav": parts[4],
            "date": parts[5],
        }

    return None


def build_amfi_dataframe(records):
    if len(records) == 0:
        raise ValueError("No AMFI rows found")

    df = pd.DataFrame(records)

    df["nav"] = pd.to_numeric(df["nav"], errors="coerce")
    df = df.dropna(subset=["nav"])

    if df.empty:
        raise ValueError("No valid NAV values found")

    df["nav_date"] = df["date"].apply(parse_date_value)
    df["normalized_name"] = df["name"].apply(normalize)

    nav_dates = df["date"].dropna().unique()
    log(f"AMFI NAV dates: {list(nav_dates[:3])}")
    log(f"Valid AMFI rows: {len(df)}")

    return df

# =========================
# FIXED FETCH ROUTINE
# =========================
def fetch_amfi(target_date, max_retries=3, timeout=30):

    last_error = None
    target_amfi_date = amfi_date(target_date)

    for attempt in range(1, max_retries + 1):

        try:
            log(f"Fetching AMFI historical data for {target_amfi_date} (attempt {attempt})...")

            resp = requests.get(
                AMFI_HISTORY_URL,
                params={"frmdt": target_amfi_date, "todt": target_amfi_date},
                timeout=timeout,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            resp.raise_for_status()

            lines = resp.text.split("\n")
            records = []

            for line in lines:
                record = parse_amfi_line(line)
                if record is not None:
                    records.append(record)

            return build_amfi_dataframe(records)

        except Exception as e:
            last_error = e
            log(f"Fetch failed (attempt {attempt}): {e}")

            if attempt < max_retries:
                time.sleep(2)
            else:
                raise RuntimeError(f"AMFI fetch failed after retries: {last_error}")

# =========================
# MAIN
# =========================
def main():

    start_time = time.time()
    log("---- START ----")

    # DATE
    try:
        target_date = resolve_date(input_date)
        validate_target_date(target_date)
        target_date_label = format_header_date(target_date)
        log(f"Target date: {target_date_label}")
    except Exception as e:
        log(f"ERROR: {e}")
        return

    # FILE
    try:
        validate_file(FILE_PATH)
        log(f"File OK: {FILE_PATH}")
    except Exception as e:
        log(f"ERROR: {e}")
        return

    # LOAD SHEET
    try:
        wb, ws = load_sheet(FILE_PATH, SHEET_NAME)
        log(f"Sheet loaded: {SHEET_NAME}")
    except Exception as e:
        log(f"ERROR: {e}")
        return

    # =========================
    # COLUMN HANDLING
    # =========================
    col = find_or_insert_date_column(ws, target_date)

    # FETCH AMFI
    try:
        df_amfi = fetch_amfi(target_date)
    except Exception as e:
        log(f"ERROR: {e}")
        return

    df_target = df_amfi[df_amfi["nav_date"] == target_date]
    if df_target.empty:
        available_dates = sorted(
            {
                nav_date
                for nav_date in df_amfi["nav_date"].dropna()
                if nav_date >= MIN_ALLOWED_DATE
            },
            reverse=True,
        )
        available_labels = [
            f"{format_header_date(nav_date)}-{nav_date.year}"
            for nav_date in available_dates[:5]
        ]
        log(f"ERROR: No AMFI NAV rows found for {target_date_label}-{target_date.year}")
        if available_labels:
            log(f"AMFI available recent dates: {available_labels}")
        return

    df_amfi = df_target

    log(f"AMFI rows for {target_date_label}: {len(df_amfi)}")

    # =========================
    # READ FUNDS (STRICT)
    # =========================
    funds = []
    max_row = ws.max_row

    log(f"Excel max_row: {max_row}")

    for r in range(2, max_row + 1):
        val = ws[f"B{r}"].value

        if val is None:
            continue

        val = str(val).strip()

        if val.lower() == "fund name":
            continue

        if val != "":
            funds.append((r, val))

    log(f"Total funds read: {len(funds)}")

    if len(funds) == 0:
        log("ERROR: No valid fund names found")
        return

    # =========================
    # MATCHING
    # =========================
    updated = 0
    skipped = 0
    not_updated = 0

    for row_idx, fund in funds:

        cell = ws.cell(row=row_idx, column=col)

        match_type, best_nav = find_best_nav_match(fund, df_amfi)

        if best_nav is not None:
            cell.value = float(best_nav)
            updated += 1
        else:
            not_updated += 1

    if updated == 0:
        log("No tracked fund NAVs found for this date; workbook not saved")
        log("---- SUMMARY ----")
        log(f"File: {FILE_PATH}")
        log(f"Date column: {target_date_label}")
        log(f"Total funds: {len(funds)}")
        log(f"Updated: {updated}")
        log(f"Skipped: {skipped}")
        log(f"Not updated (no AMFI NAV for this date): {not_updated}")
        log(f"Execution time: {round(time.time() - start_time, 2)}s")
        return

    # =========================
    # SAVE
    # =========================
    try:
        wb.save(FILE_PATH)
        log("File saved successfully")
    except Exception as e:
        log(f"ERROR saving file: {e}")
        return

    # =========================
    # SUMMARY
    # =========================
    log("---- SUMMARY ----")
    log(f"File: {FILE_PATH}")
    log(f"Date column: {target_date_label}")
    log(f"Total funds: {len(funds)}")
    log(f"Updated: {updated}")
    log(f"Skipped: {skipped}")
    log(f"Not updated (no AMFI NAV for this date): {not_updated}")
    log(f"Execution time: {round(time.time() - start_time, 2)}s")

# =========================
# ENTRY
# =========================
if __name__ == "__main__":
    try:
        main()
    finally:
        log("---- END OF RUN ----")
