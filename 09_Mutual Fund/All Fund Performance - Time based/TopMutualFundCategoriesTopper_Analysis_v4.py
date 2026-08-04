import os
import re
import pandas as pd

from mftool import Mftool

from datetime import datetime, timedelta
from dateutil import parser

from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed
)

# =========================================================
# CONFIGURATION
# =========================================================

OUTPUT_DIR = r"D:/Tools/Mutual Fund/All Fund Performance - Time based"

TOP_COUNT = 50

MAX_WORKERS = 50

# =========================================================
# INCLUSION TOKENS
# Fund MUST contain ALL these tokens
# =========================================================

INCLUSION_TOKENS = {
    "DIRECT",
    "GROWTH"
}

# =========================================================
# EXCLUSION TOKENS
# SINGLE-WORD exclusions
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
# MULTI-WORD exclusions
# =========================================================

EXCLUSION_PHRASES = [

    # Generic exclusions

    "ULTRA SHORT",
    "MONEY MARKET",
    "FIXED MATURITY",
    "CAPITAL PROTECTION",

    # Specific fund exclusions

    "MOTILAL OSWAL NASDAQ 100",

    "TAIWAN EQUITY FUND",

    "STRATEGIC METAL AND ENERGY EQUITY",

    "JAPAN EQUITY",

    "ICICI PRUDENTIAL NASDAQ 100 INDEX FUND",

    "MOTILAL OSWAL DEVELOPED MARKET EX US ETFS"
]

# =========================================================
# GLOBAL OBJECT
# =========================================================

obj = Mftool()

# =========================================================
# NORMALIZATION
# =========================================================

def normalize_string(text):
    """
    Normalize strings:
    - Uppercase
    - Remove special chars
    - Compress spaces
    """

    text = text.upper()

    text = re.sub(
        r'[^A-Z0-9]',
        ' ',
        text
    )

    text = re.sub(
        r'\s+',
        ' ',
        text
    ).strip()

    return text


def tokenize_string(text):
    """
    Convert normalized string to token set.
    """

    normalized = normalize_string(text)

    return set(normalized.split())


# =========================================================
# PRE-NORMALIZE EXCLUSION PHRASES
# =========================================================

NORMALIZED_EXCLUSION_PHRASES = [
    normalize_string(x)
    for x in EXCLUSION_PHRASES
]

# =========================================================
# DATE PARSER
# =========================================================

def parse_input_date(date_input):
    """
    Flexible date parser.

    Supports:
    - yyyy-mm-dd
    - dd-mm-yyyy
    - dd/mm/yyyy
    - yyyy/mm/dd
    - natural dates
    """

    if not date_input:
        return None

    try:

        return parser.parse(
            date_input,
            dayfirst=True
        ).date()

    except Exception:

        raise ValueError(
            f"Invalid date format: {date_input}"
        )

# =========================================================
# FILTERS
# =========================================================

def passes_inclusion_filters(tokens):
    """
    Fund must contain all inclusion tokens.
    """

    return INCLUSION_TOKENS.issubset(tokens)


def passes_exclusion_filters(
    tokens,
    normalized_name
):
    """
    Reject if:
    - exclusion token found
    - exclusion phrase found
    """

    # -----------------------------------------------------
    # TOKEN EXCLUSIONS
    # -----------------------------------------------------

    if not tokens.isdisjoint(EXCLUSION_TOKENS):
        return False

    # -----------------------------------------------------
    # PHRASE EXCLUSIONS
    # -----------------------------------------------------

    for phrase in NORMALIZED_EXCLUSION_PHRASES:

        if phrase in normalized_name:
            return False

    return True


# =========================================================
# NAV EXTRACTION
# =========================================================

def get_nav_with_fallback(
    hist_df,
    target_date
):
    """
    Get NAV for target date
    or closest previous date.
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
        # FETCH NAV HISTORY
        # =================================================

        hist_data = obj.get_scheme_historical_nav(code)

        if 'data' not in hist_data:
            return None

        if not hist_data['data']:
            return None

        df_hist = pd.DataFrame(
            hist_data['data']
        )

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
        # GROWTH %
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
# MAIN ANALYSIS FUNCTION
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

    activity_threshold = (
        end_target
        - timedelta(days=10)
    )

    print("\n🚀 Starting Mutual Fund Analysis")

    # =====================================================
    # FETCH ALL SCHEMES
    # =====================================================

    all_schemes = obj.get_scheme_codes()

    total_scheme_count = len(all_schemes)

    print(
        f"\n📊 Total Mutual Funds Available : "
        f"{total_scheme_count}"
    )

    # =====================================================
    # PRE-FILTERING
    # =====================================================

    filtered_schemes = {}

    for code, name in all_schemes.items():

        normalized_name = normalize_string(name)

        tokens = tokenize_string(name)

        # -------------------------------------------------
        # Inclusion filter
        # -------------------------------------------------

        if not passes_inclusion_filters(tokens):
            continue

        # -------------------------------------------------
        # Exclusion filter
        # -------------------------------------------------

        if not passes_exclusion_filters(
            tokens,
            normalized_name
        ):
            continue

        # -------------------------------------------------
        # ACCEPT FUND
        # -------------------------------------------------

        filtered_schemes[code] = name

    # =====================================================
    # FILTER STATS
    # =====================================================

    filtered_count = len(filtered_schemes)

    excluded_count = (
        total_scheme_count
        - filtered_count
    )

    print(
        f"✅ Funds After Filtering       : "
        f"{filtered_count}"
    )

    print(
        f"❌ Funds Excluded              : "
        f"{excluded_count}"
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

            for code, name
            in filtered_schemes.items()
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
    # RESULT CHECK
    # =====================================================

    if not final_results:

        print(
            "\n⚠️ No valid results found."
        )

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
    # DATE STAMPED OUTPUT FILE
    # =====================================================

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    output_file = (
        f"MutualFundAnalysis_"
        f"{timestamp}.csv"
    )

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    full_output_path = os.path.join(
        OUTPUT_DIR,
        output_file
    )

    # =====================================================
    # SAVE CSV
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
            "====================================\n"
        )

        f.write(
            f"Analysis Start Date : "
            f"{SD_str}\n"
        )

        f.write(
            f"Analysis End Date   : "
            f"{ED_str}\n"
        )

        f.write(
            f"Total Funds Available : "
            f"{total_scheme_count}\n"
        )

        f.write(
            f"Funds After Filtering : "
            f"{filtered_count}\n"
        )

        f.write(
            f"Funds Excluded : "
            f"{excluded_count}\n"
        )

        f.write(
            f"Top Funds Selected : "
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

    print("\n====================================")
    print(" MUTUAL FUND PERFORMANCE ANALYZER ")
    print("====================================\n")

    print(
        "Leave dates blank for "
        "YTD analysis.\n"
    )

    user_start = input(
        "Enter Start Date: "
    ).strip()

    user_end = input(
        "Enter End Date: "
    ).strip()

    # =====================================================
    # DATE HANDLING
    # =====================================================

    today = datetime.today().date()

    # -----------------------------------------------------
    # NO DATES -> YTD
    # -----------------------------------------------------

    if not user_start and not user_end:

        end_date = today

        start_date = datetime(
            today.year,
            1,
            1
        ).date()

        print(
            f"\n📅 Running YTD Analysis:"
            f"\nStart Date : {start_date}"
            f"\nEnd Date   : {end_date}"
        )

    # -----------------------------------------------------
    # ONLY END DATE -> YTD
    # -----------------------------------------------------

    elif not user_start and user_end:

        end_date = parse_input_date(
            user_end
        )

        start_date = datetime(
            end_date.year,
            1,
            1
        ).date()

        print(
            f"\n📅 Running YTD Analysis:"
            f"\nStart Date : {start_date}"
            f"\nEnd Date   : {end_date}"
        )

    # -----------------------------------------------------
    # BOTH DATES PROVIDED
    # -----------------------------------------------------

    else:

        start_date = parse_input_date(
            user_start
        )

        end_date = parse_input_date(
            user_end
        )

        print(
            f"\n📅 Running Custom Analysis:"
            f"\nStart Date : {start_date}"
            f"\nEnd Date   : {end_date}"
        )

    # =====================================================
    # EXECUTE
    # =====================================================

    fetch_top_funds(
        SD_str=start_date.strftime(
            "%d-%m-%Y"
        ),
        ED_str=end_date.strftime(
            "%d-%m-%Y"
        )
    )