import argparse
import re
from pathlib import Path

import pandas as pd


DEFAULT_INPUT_FILE = Path("D:/Tools/StockCodeMaster/ETF/00_NYSE_NASDAQ_ETF_Master_Library-PlainETF.csv")
DEFAULT_OUTPUT_FILE = Path("D:/Tools/ETF_Comparator/INPUT/ETF_Classification_Mapping.csv")


def contains_any(text, keywords):
    text = str(text).lower()
    return any(re.search(keyword.lower(), text) for keyword in keywords)


def first_matching_label(text, rules, default_value="Other"):
    for label, keywords in rules:
        if contains_any(text, keywords):
            return label
    return default_value


def matching_labels(text, rules):
    return [
        label
        for label, keywords in rules
        if contains_any(text, keywords)
    ]


ASSET_CLASS_RULES = [
    ("Crypto", [r"\bbitcoin\b", r"\bbtc\b", r"\bether\b", r"\bethereum\b", r"\bcrypto\b", r"\bdogecoin\b", r"\bsolana\b", r"\bxrp\b", r"\bblockchain\b"]),
    ("Commodity", [r"\bgold\b", r"\bsilver\b", r"\bcopper\b", r"\bcommodity\b", r"\bcommodities\b", r"\boil\b", r"\bnatural gas\b", r"\buranium\b", r"\blithium\b"]),
    ("Fixed Income", [r"\bbond\b", r"\bbonds\b", r"\btreasury\b", r"\bmunicipal\b", r"\bmuni\b", r"\bincome securities\b", r"\bhigh yield\b", r"\bduration\b", r"\bt-bill\b"]),
    ("Real Estate", ["reit", "real estate"]),
    ("Currency", [r"\bcurrency\b", r"\bdollar\b", r"\busd\b", r"\byen\b", r"\beuro\b"]),
    ("Multi Asset", ["multi-asset", "multi asset", "allocation"]),
    ("Equity", ["equity", "stock", "shares", "s&p", "nasdaq", "russell", "dow jones", "msci"]),
]

STRATEGY_RULES = [
    ("Leveraged", ["2x", "3x", "leveraged", "ultra", "bull 2", "bull 3"]),
    ("Inverse", ["inverse", "short", "bear", "bearish"]),
    ("Covered Call", ["covered call", "buywrite", "option income", "premium income"]),
    ("Dividend/Income", ["dividend", "income", "yield", "distribution"]),
    ("Municipal Bond", [r"\bmunicipal\b", r"\bmuni\b"]),
    ("Active", ["active", "actively managed"]),
    ("ESG/Sustainable", ["esg", "sustainable", "responsible", "climate", "clean"]),
    ("Factor", ["value", "growth", "quality", "momentum", "low volatility", "minimum volatility", "equal weight"]),
    ("Target Maturity", ["defined maturity", "target maturity", "bulletshares", "ibonds"]),
]

THEME_RULES = [
    ("Semiconductor", ["semiconductor", "semiconductors", "phlx sox"]),
    ("Bitcoin", [r"\bbitcoin\b", r"\bbtc\b"]),
    ("Ethereum", [r"\bethereum\b", r"\bether\b"]),
    ("Crypto Broad", [r"\bcrypto\b", r"\bblockchain\b", r"\bdogecoin\b", r"\bsolana\b", r"\bxrp\b"]),
    ("AI & Robotics", ["artificial intelligence", r"\bai\b", "robotics", "automation", "quantum"]),
    ("Technology", ["technology", "tech", "nasdaq", "software", "cybersecurity", "cloud", "internet", "digital"]),
    ("Energy", ["energy", "oil", "gas", "natural gas", "uranium", "nuclear"]),
    ("Clean Energy", ["clean energy", "solar", "wind", "renewable", "battery", "lithium"]),
    ("Healthcare", ["healthcare", "health care", "biotech", "pharmaceutical", "medical"]),
    ("Financials", ["financial", "bank", "insurance", "fintech"]),
    ("Consumer", ["consumer", "retail", "ecommerce", "online retail"]),
    ("Real Estate", ["real estate", "reit"]),
    ("Infrastructure", ["infrastructure"]),
    ("Gold/Silver/Metals", [r"\bgold\b", r"\bsilver\b", r"\bcopper\b", "metals", "miners"]),
    ("Bonds", [r"\bbond\b", r"\bbonds\b", r"\btreasury\b", r"\bhigh yield\b", r"\bmunicipal\b", r"\bmuni\b", r"\bduration\b", r"\bt-bill\b"]),
    ("Dividend/Income", ["dividend", "income", "yield", "covered call", "option income", "premium income"]),
]

GEOGRAPHY_RULES = [
    ("Emerging Markets", ["emerging markets", "emerging market"]),
    ("Developed ex-US", ["developed markets", "international developed", "eafe", "ex-us", "ex us", "ex-u.s.", "ex u.s."]),
    ("Global", ["global", "world", "all country"]),
    ("Europe", ["europe", "eurozone"]),
    ("Asia Pacific", ["asia pacific", "asia-pacific", "asia"]),
    ("China", ["china", "chinese"]),
    ("India", ["india"]),
    ("Japan", ["japan"]),
    ("South Korea", ["korea", "south korea"]),
    ("Taiwan", ["taiwan"]),
    ("Brazil", ["brazil"]),
    ("Mexico", ["mexico"]),
    ("Canada", ["canada"]),
    ("Australia", ["australia"]),
    ("United Kingdom", ["united kingdom", " uk ", "u.k."]),
    ("United States", ["u.s.", "us ", "usa", "united states", "s&p 500", "russell", "dow jones", "nasdaq"]),
]


def classify_etf(security_name, default_geography):
    name = f" {security_name} "
    asset_class = first_matching_label(name, ASSET_CLASS_RULES, default_value="Equity")
    strategy = first_matching_label(name, STRATEGY_RULES, default_value="Plain")
    theme = first_matching_label(name, THEME_RULES, default_value="Broad Market")
    geography = first_matching_label(name, GEOGRAPHY_RULES, default_value=default_geography)

    flags = sorted(set(
        matching_labels(name, ASSET_CLASS_RULES)
        + matching_labels(name, STRATEGY_RULES)
        + matching_labels(name, THEME_RULES)
        + matching_labels(name, GEOGRAPHY_RULES)
    ))

    return {
        "Asset Class": asset_class,
        "Strategy": strategy,
        "Theme": theme,
        "Geography": geography,
        "Category Flags": "; ".join(flags),
    }


def build_classification_mapping(input_file, output_file, ticker_column, name_column, default_geography):
    if not input_file.exists():
        raise FileNotFoundError(f"Missing ETF master file: {input_file}")

    df = pd.read_csv(input_file, dtype=str).fillna("")
    if ticker_column not in df.columns:
        raise ValueError(f"Ticker column '{ticker_column}' not found. Available columns: {', '.join(df.columns)}")

    has_name_column = bool(name_column) and name_column in df.columns
    if name_column and not has_name_column:
        print(f"[WARN] Name column '{name_column}' not found. Classification will use ticker text only.")

    rows = []
    for _, row in df.iterrows():
        ticker = str(row.get(ticker_column, "")).strip().upper()
        if not ticker:
            continue

        security_name = str(row.get(name_column, "")).strip() if has_name_column else ticker
        classification = classify_etf(security_name, default_geography)
        rows.append({
            "Ticker": ticker,
            "Security Name": security_name,
            **classification,
        })

    mapping_df = pd.DataFrame(rows).drop_duplicates(subset=["Ticker"]).sort_values("Ticker")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    mapping_df.to_csv(output_file, index=False)
    print_classification_summary(mapping_df)
    print(f"[INFO] Saved classification mapping -> {output_file}")
    return mapping_df


def print_classification_summary(mapping_df):
    for column in ["Asset Class", "Strategy", "Theme", "Geography"]:
        print(f"\n[{column}]")
        counts = mapping_df[column].fillna("Unclassified").value_counts().head(25)
        for label, count in counts.items():
            print(f"{label}: {count}")


def parse_args():
    parser = argparse.ArgumentParser(description="Build ETF classification mapping CSV from an ETF master file.")
    parser.add_argument("--input-file", type=Path, default=DEFAULT_INPUT_FILE)
    parser.add_argument("--output-file", type=Path, default=DEFAULT_OUTPUT_FILE)
    parser.add_argument("--ticker-column", default="Ticker")
    parser.add_argument("--name-column", default="Security Name")
    parser.add_argument("--default-geography", default="United States")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    build_classification_mapping(
        args.input_file,
        args.output_file,
        args.ticker_column,
        args.name_column,
        args.default_geography,
    )
