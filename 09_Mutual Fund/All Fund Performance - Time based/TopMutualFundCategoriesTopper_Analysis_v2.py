import os
import re
import pandas as pd
from mftool import Mftool
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# =========================================================
# CONFIGURATION
# =========================================================

# Output directory
OUTPUT_DIR = r"D:\MF_Output"

# Top funds to export
TOP_COUNT = 50

# Parallel workers
MAX_WORKERS = 50

# =========================================================
# INCLUSION TOKENS
# Fund MUST contain all these tokens
# =========================================================

INCLUSION_TOKENS = {
    "DIRECT",
    "GROWTH"
}

# =========================================================
# EXCLUSION TOKENS
# Any token match rejects the fund
# =========================================================

EXCLUSION_TOKENS = {
    "ETF",
    "FOF",
    "GOLD",
    "SILVER",
    "ARBITRAGE",
    "IDCW",
    "DIVIDEND",
    "REGULAR",
    "LIQUID",
    "OVERNIGHT",
    "CHILDREN",
    "RETIREMENT"
}

# =========================================================
# EXCLUSION PHRASES
# Used for multi-word matching
# =========================================================

EXCLUSION_PHRASES = [
    "ULTRA SHORT",
    "MONEY MARKET",
    "FIXED MATURITY",
    "CAPITAL PROTECTION"
]

# =========================================================
# GLOBAL MFTOOL OBJECT
# =========================================================

obj = Mftool()

# =========================================================
# STRING NORMALIZATION
# =========================================================

def normalize_string(text):
    """
    Normalize text by:
    - Uppercasing
    - Removing special characters
    - Compressing spaces
    """

    text = text.upper()

    # Replace non-alphanumeric chars with space
    text = re.sub(r'[^A-Z0-9]', ' ', text)

    # Compress multiple spaces
    text = re.sub(r'\s+', ' ', text).strip()

    return text


def tokenize_string(text):
    """
    Convert normalized string into token set.
    """

    normalized = normalize_string(text)

    return set(normalized.split())


# =========================================================
# FILTERS
# =========================================================

def passes_inclusion_filters(tokens):
    """
    All inclusion tokens must exist.
    """

    return INCLUSION_TOKENS.issubset(tokens)


def passes_exclusion_filters(tokens, normalized_name):
    """
    Reject if:
    - Any exclusion token exists
    - Any exclusion phrase exists
    """

    # Token exclusion
    if not tokens.isdisjoint(EXCLUSION_TOKENS):
        return False

    # Phrase exclusion
    for phrase in EXCLUSION_PHRASES:

        normalized_phrase = normalize_string(phrase)

        if normalized_phrase in normalized_name:
            return False

    return True


# =========================================================
# NAV EXTRACTION
# =========================================================

def get_nav_with_fallback(hist_df, target_date):
    """
    Get NAV for target date or closest previous date.
    """

    hist_df['date'] = pd.to_datetime(
        hist_df['date'],
        dayfirst=True
    ).dt.date

    past_data = hist_df.loc[
        hist_df['date'] <= target_date
    ].sort_values(
        by='date',
        ascending=False
    )

    if not past_data.empty:

        row = past_data.iloc[0]

        return row['nav'], row['date']

    return None, None


# =========================================================
# MAIN PROCESSOR
# =========================================================

def process_scheme(
    code,
    name,
    start_target,
    end_target,
    activity_threshold
):

    try:

        # =================================================
        # FETCH SCHEME DETAILS
        # =================================================

        details = obj.get_scheme_details(code)

        scheme_type = details.get(
            'scheme_type',
            ''
        ).upper()

        # =================================================
        # OPEN ENDED ONLY
        # =================================================

        if "OPEN ENDED" not in scheme_type:
            return None

        if "CLOSED" in scheme_type:
            return None

        # =================================================
        # FETCH HISTORICAL NAV
        # =================================================

        hist_data = obj.get_scheme_historical_nav(code)

        if 'data' not in hist_data:
            return None

        if not hist_data['data']:
            return None

        df_hist = pd.DataFrame(hist_data['data'])

        # =================================================
        # ACTIVE FUND CHECK
        # =================================================

        latest_nav_date = pd.to_datetime(
            df_hist.iloc[0]['date'],
            dayfirst=True
        ).date()

        if latest_nav_date < activity_threshold:
            return None

        # =================================================
        # START NAV
        # =================================================

        nav_s, date_s = get_nav_with_fallback(
            df_hist,
            start_target
        )

        # =================================================
        # END NAV
        # =================================================

        nav_e, date_e = get_nav_with_fallback(
            df_hist,
            end_target
        )

        if not nav_s or not nav_e:
            return None

        # =================================================
        # RETURN CALCULATION
        # =================================================

        growth = round(
            (
                (float(nav_e) - float(nav_s))
                / float(nav_s)
            ) * 100,
            2
        )

        # =================================================
        # RETURN RESULT
        # =================================================

        return {
            "Scheme Name": name,
            "Category": details.get(
                'scheme_category',
                'N/A'
            ),
            f"NAV ({date_s})": nav_s,
            f"NAV ({date_e})": nav_e,
            "Growth %": growth
        }

    except Exception:
        return None


# =========================================================
# MAIN FUNCTION
# =========================================================

def fetch_top_funds(
    SD_str,
    ED_str,
    top_count=TOP_COUNT,
    max_workers=MAX_WORKERS
):

    # =====================================================
    # DATE CONVERSION
    # =====================================================

    start_target = datetime.strptime(
        SD_str,
        "%d-%m-%Y"
    ).date()

    end_target = datetime.strptime(
        ED_str,
        "%d-%m-%Y"
    ).date()

    activity_threshold = end_target - timedelta(days=10)

    print("\n🚀 Starting Mutual Fund Analysis")

    # =====================================================
    # FETCH ALL SCHEMES
    # =====================================================

    all_schemes = obj.get_scheme_codes()

    print(
        f"📊 Total schemes fetched: "
        f"{len(all_schemes)}"
    )

    # =====================================================
    # PRE-FILTERING
    # =====================================================

    filtered_schemes = {}

    for code, name in all_schemes.items():

        normalized_name = normalize_string(name)

        tokens = tokenize_string(name)

        # ---------------------------------------------
        # Inclusion Filter
        # ---------------------------------------------

        if not passes_inclusion_filters(tokens):
            continue

        # ---------------------------------------------
        # Exclusion Filter
        # ---------------------------------------------

        if not passes_exclusion_filters(
            tokens,
            normalized_name
        ):
            continue

        # ---------------------------------------------
        # ACCEPT FUND
        # ---------------------------------------------

        filtered_schemes[code] = name

    # =====================================================
    # FIXED FUND UNIVERSE
    # =====================================================

    print(
        f"✅ Funds after filtering: "
        f"{len(filtered_schemes)}"
    )

    print(
        "\n📡 Starting NAV comparison..."
    )

    # =====================================================
    # PROCESS FILTERED FUNDS
    # =====================================================

    final_results = []

    with ThreadPoolExecutor(
        max_workers=max_workers
    ) as executor:

        futures = {
            executor.submit(
                process_scheme,
                code,
                name,
                start_target,
                end_target,
                activity_threshold
            ): code
            for code, name in filtered_schemes.items()
        }

        total = len(futures)

        for idx, future in enumerate(
            as_completed(futures),
            start=1
        ):

            result = future.result()

            if result:
                final_results.append(result)

            if idx % 100 == 0:

                print(
                    f"📡 Processed "
                    f"{idx}/{total}",
                    end="\r"
                )

    # =====================================================
    # NO RESULT CHECK
    # =====================================================

    if not final_results:

        print("\n⚠️ No valid results found.")

        return

    # =====================================================
    # SORT RESULTS
    # =====================================================

    df_final = pd.DataFrame(final_results)

    df_top = (
        df_final
        .sort_values(
            by="Growth %",
            ascending=False
        )
        .head(top_count)
    )

    # =====================================================
    # DATE STAMPED FILE
    # =====================================================

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    output_file = (
        f"MutualFundAnalysis_"
        f"{timestamp}.csv"
    )

    # =====================================================
    # CREATE DIRECTORY
    # =====================================================

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    full_output_path = os.path.join(
        OUTPUT_DIR,
        output_file
    )

    # =====================================================
    # SAVE OUTPUT
    # =====================================================

    with open(
        full_output_path,
        mode='w',
        newline='',
        encoding='utf-8'
    ) as f:

        f.write(
            "Mutual Fund Top Performance Analysis\n"
        )

        f.write(
            f"Analysis Dates: "
            f"{SD_str} to {ED_str}\n"
        )

        f.write(
            f"Filtered Fund Universe: "
            f"{len(filtered_schemes)}\n"
        )

        f.write(
            f"Qualified Funds: "
            f"{len(df_top)}\n\n"
        )

        df_top.to_csv(
            f,
            index=False
        )

    # =====================================================
    # FINAL OUTPUT
    # =====================================================

    print("\n\n✅ Analysis Complete")

    print(
        f"\n📁 Output File:\n"
        f"{full_output_path}"
    )

    print(
        f"\n🏆 Top {top_count} Funds:\n"
    )

    print(
        df_top[
            ["Scheme Name", "Growth %"]
        ]
        .head(10)
        .to_string(index=False)
    )


# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":

    fetch_top_funds(
        SD_str="02-01-2026",
        ED_str="29-04-2026"
    )