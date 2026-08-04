import pandas as pd

# ============================================================
# INPUT / OUTPUT FILES
# ============================================================

INPUT_FILE = "nasdaq_screeer_BaseFile.csv"
OUTPUT_FILE = "nasdaq_filtered_output.csv"

# ============================================================
# LOAD CSV
# ============================================================

df = pd.read_csv(INPUT_FILE)

# Optional:
# print(df.columns.tolist())

# ============================================================
# COLUMN MAPPING
# Change these to match your CSV column names
# ============================================================

PRICE_COLUMN = "Price"
VOLUME_COLUMN = "Volume"
SECTOR_COLUMN = "Sector"
INDUSTRY_COLUMN = "Industry"
COUNTRY_COLUMN = "Country"
MARKET_CAP_COLUMN = "Market Cap"
EXCHANGE_COLUMN = "Exchange"

# ============================================================
# BASE FILTERS
# ============================================================

MIN_PRICE = 10.0
MIN_VOLUME = 10_000

filtered_df = df[
    (df[PRICE_COLUMN] >= MIN_PRICE) &
    (df[VOLUME_COLUMN] >= MIN_VOLUME)
]

# ============================================================
# OPTIONAL FILTERS
# Uncomment / modify as needed
# ============================================================

# ------------------------------------------------------------
# Sector Filter
# ------------------------------------------------------------

# ALLOWED_SECTORS = [
#     "Technology",
#     "Healthcare",
#     "Financial"
# ]

# filtered_df = filtered_df[
#     filtered_df[SECTOR_COLUMN].isin(ALLOWED_SECTORS)
# ]

# ------------------------------------------------------------
# Industry Filter
# ------------------------------------------------------------

# ALLOWED_INDUSTRIES = [
#     "Semiconductors",
#     "Biotechnology",
#     "Software"
# ]

# filtered_df = filtered_df[
#     filtered_df[INDUSTRY_COLUMN].isin(ALLOWED_INDUSTRIES)
# ]

# ------------------------------------------------------------
# Country / Location Filter
# ------------------------------------------------------------

# ALLOWED_COUNTRIES = [
#     "USA",
#     "Canada"
# ]

# filtered_df = filtered_df[
#     filtered_df[COUNTRY_COLUMN].isin(ALLOWED_COUNTRIES)
# ]

# ------------------------------------------------------------
# Exchange Filter
# ------------------------------------------------------------

# filtered_df = filtered_df[
#     filtered_df[EXCHANGE_COLUMN] == "NASDAQ"
# ]

# ------------------------------------------------------------
# Market Cap Filter
# ------------------------------------------------------------

# MIN_MARKET_CAP = 500_000_000
# MAX_MARKET_CAP = 50_000_000_000

# filtered_df = filtered_df[
#     (filtered_df[MARKET_CAP_COLUMN] >= MIN_MARKET_CAP) &
#     (filtered_df[MARKET_CAP_COLUMN] <= MAX_MARKET_CAP)
# ]

# ------------------------------------------------------------
# Custom Price Range
# ------------------------------------------------------------

# MIN_PRICE = 10
# MAX_PRICE = 100

# filtered_df = filtered_df[
#     (filtered_df[PRICE_COLUMN] >= MIN_PRICE) &
#     (filtered_df[PRICE_COLUMN] <= MAX_PRICE)
# ]

# ------------------------------------------------------------
# Relative Volume Placeholder
# ------------------------------------------------------------

# RVOL_COLUMN = "Relative Volume"

# filtered_df = filtered_df[
#     filtered_df[RVOL_COLUMN] >= 2
# ]

# ------------------------------------------------------------
# Float Placeholder
# ------------------------------------------------------------

# FLOAT_COLUMN = "Float"
# MIN_FLOAT = 5_000_000

# filtered_df = filtered_df[
#     filtered_df[FLOAT_COLUMN] >= MIN_FLOAT
# ]

# ------------------------------------------------------------
# Short Interest Placeholder
# ------------------------------------------------------------

# SHORT_INTEREST_COLUMN = "Short Float %"

# filtered_df = filtered_df[
#     filtered_df[SHORT_INTEREST_COLUMN] >= 10
# ]

# ============================================================
# SORTING
# ============================================================

filtered_df = filtered_df.sort_values(
    by=[PRICE_COLUMN, VOLUME_COLUMN],
    ascending=[False, False]
)

# ============================================================
# EXPORT
# ============================================================

filtered_df.to_csv(OUTPUT_FILE, index=False)

# ============================================================
# SUMMARY
# ============================================================

print("Original rows :", len(df))
print("Filtered rows :", len(filtered_df))
print("Saved output  :", OUTPUT_FILE)

print("\nTop 10 Results:")
print(filtered_df.head(10))