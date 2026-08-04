import argparse
import os
import pandas as pd
import requests


def get_ticker_from_yahoo(company_name, region, sector, industry):
  url = "https://query2.finance.yahoo.com/v1/finance/search"
  user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
  params = {"q": company_name, "quotes_count": 15, "country": "United States"}
  
  try:
    res = requests.get(
        url=url, params=params, headers={"User-Agent": user_agent}, timeout=10
    )
    data = res.json()
    if "quotes" in data:
      for quote in data["quotes"]:
        symbol = str(quote.get("symbol", "")).strip()
        exchange = str(quote.get("exchange", "")).strip()
        longname = str(quote.get("longname", "")).strip()
        shortname = str(quote.get("shortname", "")).strip()

        # Validate Region
        is_us_listed = exchange in [
            "NYQ", "NMS", "NGM", "NCM", "NYSE", "NASDAQ", "ASE", "PCX"
        ] and "." not in symbol
        
        if region.lower() == "us" and not is_us_listed:
            continue

        # Validate Company Name (flexible matching for corporate suffixes)
        comp_clean = company_name.lower().replace(",", "").replace(".", "").strip()
        long_clean = longname.lower().replace(",", "").replace(".", "").strip()
        short_clean = shortname.lower().replace(",", "").replace(".", "").strip()
        
        name_match = (
            comp_clean in long_clean or long_clean in comp_clean or
            comp_clean in short_clean or short_clean in comp_clean
        )
        
        if not name_match:
            continue

        # Validate Sector and Industry
        api_sector = str(quote.get("sector", "")).strip()
        api_industry = str(quote.get("industry", "")).strip()

        if not api_sector or not api_industry:
            prof_url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{symbol}"
            prof_params = {"modules": "assetProfile"}
            try:
                prof_res = requests.get(
                    url=prof_url, params=prof_params, headers={"User-Agent": user_agent}, timeout=5
                )
                prof_data = prof_res.json()
                profile = prof_data.get("quoteSummary", {}).get("result", [{}])[0].get("assetProfile", {})
                api_sector = str(profile.get("sector", "")).strip()
                api_industry = str(profile.get("industry", "")).strip()
            except Exception:
                pass

        sector_match = (sector.lower() == api_sector.lower()) if pd.notna(sector) and sector else True
        industry_match = (industry.lower() == api_industry.lower()) if pd.notna(industry) and industry else True

        if sector_match and industry_match:
            return symbol

  except Exception as e:
    print(f"Error fetching ticker for {company_name}: {e}")
  return ""


def process_stock_file(file_path, output_path=None):
  if not os.path.exists(file_path):
    raise FileNotFoundError(f"Input file not found: {file_path}")

  check_path = output_path if output_path else file_path
  parent_dir = os.path.dirname(os.path.abspath(check_path))
  if not os.access(parent_dir if parent_dir else ".", os.W_OK):
    raise PermissionError(
        f"Permission denied: Cannot write to location '{check_path}'"
    )

  if file_path.endswith(".csv"):
    df = pd.read_csv(file_path)
  elif file_path.endswith((".xls", ".xlsx")):
    df = pd.read_excel(file_path)
  else:
    raise ValueError("Unsupported file format. Please provide a CSV or Excel file.")

  # Ensure columns are present based on the expected input layout
  expected_cols = ["Company-Name", "Region", "Sector", "Industry"]
  for col in expected_cols:
      if col not in df.columns:
          raise ValueError(f"Missing required column in input file: {col}")

  total_read = len(df)
  success_count = 0
  error_count = 0
  tickers = []

  for index, row in df.iterrows():
    company_name = str(row["Company-Name"]).strip()
    region = str(row["Region"]).strip()
    sector = str(row["Sector"]).strip()
    industry = str(row["Industry"]).strip()
    
    print(f"Searching ticker matching Name, Region, Sector & Industry for: {company_name}")

    ticker = get_ticker_from_yahoo(company_name, region, sector, industry)

    if ticker:
      success_count += 1
      tickers.append(ticker)
    else:
      error_count += 1
      tickers.append("FLAGGED_MISMATCH")

  # Insert Ticker as Column A
  if "Ticker" in df.columns:
      df.drop(columns=["Ticker"], inplace=True)
  df.insert(0, "Ticker", tickers)

  if output_path is None:
    output_path = file_path

  if output_path.endswith(".csv"):
    df.to_csv(output_path, index=False)
  else:
    df.to_excel(output_path, index=False)

  absolute_output_path = os.path.abspath(output_path)

  print("\n--- Execution Summary ---")
  print(f"Total Rows Read: {total_read}")
  print(f"Successfully Processed: {success_count}")
  print(f"Errors / Flagged: {error_count}")
  print(f"Output File Location: {absolute_output_path}")

  return df


if __name__ == "__main__":
  parser = argparse.ArgumentParser(
      description=(
          "Find US stock tickers with strict Company Name, Region, Sector,"
          " and Industry matching."
      )
  )
  parser.add_argument(
      "-i",
      "--input",
      required=True,
      help="Path to input CSV or Excel file",
  )
  parser.add_argument(
      "-o",
      "--output",
      default=None,
      help="Path to output file (defaults to overwriting input file)",
  )

  args = parser.parse_args()
  process_stock_file(args.input, args.output)