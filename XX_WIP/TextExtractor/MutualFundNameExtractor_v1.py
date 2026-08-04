import pandas as pd
import re
import os

# === CONFIG ===
base_folder = r"D:/Tools/TextExtractor"   # change this path

input_filename = "NAV_2026-01-02.csv"               # or "input.xlsx"
text_column = "NAV Name"

search_str1 = "Direct"
search_str2 = "Growth"

matched_filename = "matched.txt"
not_matched_filename = "not_matched.txt"


# === BUILD FULL PATHS ===
input_file = os.path.join(base_folder, input_filename)
matched_output = os.path.join(base_folder, matched_filename)
not_matched_output = os.path.join(base_folder, not_matched_filename)


# === NORMALIZATION FUNCTION ===
def normalize_and_tokenize(text):
    if pd.isna(text):
        return set()
    text = str(text).lower()
    tokens = re.findall(r'[a-z0-9]+', text)
    return set(tokens)


# === LOAD DATA ===
if input_file.endswith(".xlsx"):
    df = pd.read_excel(input_file)
else:
    df = pd.read_csv(input_file)

total_rows = len(df)


# === PREPARE SEARCH TOKENS ===
search_tokens = normalize_and_tokenize(search_str1) | normalize_and_tokenize(search_str2)


# === PROCESS DATA ===
matched_rows = []
not_matched_rows = []
processed_rows = 0

for _, row in df.iterrows():
    original_text = row.get(text_column)

    if pd.isna(original_text):
        not_matched_rows.append("")
        continue

    processed_rows += 1

    text_tokens = normalize_and_tokenize(original_text)

    if search_tokens.issubset(text_tokens):
        matched_rows.append(original_text)
    else:
        not_matched_rows.append(original_text)


# === WRITE OUTPUT FILES ===
with open(matched_output, "w", encoding="utf-8") as f:
    for line in matched_rows:
        f.write(str(line).strip() + "\n")

with open(not_matched_output, "w", encoding="utf-8") as f:
    for line in not_matched_rows:
        f.write(str(line).strip() + "\n")


# === STATISTICS ===
matched_count = len(matched_rows)
not_matched_count = len(not_matched_rows)

print("=== PROCESSING SUMMARY ===")
print(f"Base folder            : {base_folder}")
print(f"Input file             : {input_file}")
print(f"Total rows in file     : {total_rows}")
print(f"Rows processed         : {processed_rows}")
print(f"Matched rows           : {matched_count}")
print(f"Not matched rows       : {not_matched_count}")
print(f"Matched file           : {matched_output}")
print(f"Not matched file       : {not_matched_output}")