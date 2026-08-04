import pandas as pd
import yfinance as yf

def get_symbol(company_name):
    """
    Searches Yahoo Finance for the ticker symbol of a given company name.
    """
    try:
        search_results = yf.search(company_name)
        if search_results and len(search_results) > 0:
            # Returns the symbol of the first match
            return search_results[0].get('symbol', 'Not Found')
        return 'Not Found'
    except Exception:
        return 'Error'

def process_energy_companies(input_file, output_file):
    # Load the CSV file
    # Adjust 'header' and 'names' depending on your specific CSV structure
    try:
        df = pd.read_csv(input_file, header=None, names=['Company'])
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    # Process each row
    print("Processing names, this may take a while...")
    df['Symbols'] = df['Company'].apply(get_symbol)

    # Save to CSV
    df.to_csv(output_file, index=False)
    print(f"Success. Data saved to {output_file}")

if __name__ == "__main__":
    # Ensure your file is in the same directory
    input_csv = 'Energy_Stock_Companies_Names.csv'
    output_csv = 'Energy_Stocks_With_Symbols.csv'
    
    process_energy_companies(input_csv, output_csv)