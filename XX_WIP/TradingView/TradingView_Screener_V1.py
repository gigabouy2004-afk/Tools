import argparse

from tradingview_screener import Query, col
from tradingview_screener.query import And, Or
import pandas as pd

US_ETF_EXCHANGES = ['AMEX', 'NASDAQ', 'NYSE', 'CBOE']

# TradingView ETF holdings-region theme options.
ThemeAsiaPacific = 'Asia-Pacific'
ThemeDevelopedMarkets = 'Developed markets'
ThemeEmergingMarkets = 'Emerging markets'
ThemeEurope = 'Europe'
ThemeFrontierMarkets = 'Frontier markets'
ThemeGlobal = 'Global'
ThemeGlobalExUS = 'Global Ex-U.S.'
ThemeLatinAmerica = 'Latin America'
ThemeMiddleEastAfrica = 'Middle East & Africa'
ThemeNorthAmerica = 'North America'

TRADINGVIEW_THEME_OPTIONS = [
    ThemeAsiaPacific,
    ThemeDevelopedMarkets,
    ThemeEmergingMarkets,
    ThemeEurope,
    ThemeFrontierMarkets,
    ThemeGlobal,
    ThemeGlobalExUS,
    ThemeLatinAmerica,
    ThemeMiddleEastAfrica,
    ThemeNorthAmerica,
]
AllThemes = ','.join(TRADINGVIEW_THEME_OPTIONS)

# Comma-separated options. CLI arguments replace this value when provided.
SELECTED_THEME_OPTIONS = AllThemes

# TradingView does not expose a reliable leveraged/inverse ETF flag in this endpoint.
# These description terms remove common leveraged, inverse, and daily reset products.
EXCLUDE_LEVERAGED_AND_INVERSE_ETFS = True
LEVERAGED_INVERSE_DESCRIPTION_TERMS = [
    '2X',
    '2x',
    '3X',
    '3x',
    'Ultra',
    'Bull',
    'Bear',
    'Leveraged',
    'Inverse',
    'Short',
    'ETN',
    'ETNs',
    'Daily Target',
]

ETF_COLUMNS = [
    'name',
    'description',
    'close',
    'change',
    'volume',
    'average_volume_30d_calc',
    'aum',
    'expense_ratio',
    'Perf.MTD',
    'open|1M',
    'Perf.1M',
    'Perf.3M',
    'Perf.6M',
    'Perf.YTD',
    'Perf.Y',
    'holdings_region.tr',
    'exchange',
    'type',
    'typespecs',
    'subtype',
]

COLUMN_NAMES = {
    'ticker': 'Ticker',
    'name': 'Symbol',
    'description': 'ETF Name',
    'close': 'Last Price',
    'change': 'Change %',
    'volume': 'Volume',
    'average_volume_30d_calc': 'Average Volume 30D',
    'aum': 'AUM',
    'expense_ratio': 'Expense Ratio %',
    'Perf.MTD': 'MTD %',
    'Perf.1M': '1M %',
    'Perf.3M': '3M %',
    'Perf.6M': '6M %',
    'Perf.YTD': 'YTD %',
    'Perf.Y': '1Y %',
    'holdings_region.tr': 'Theme Option',
    'exchange': 'Exchange',
    'type': 'Type',
    'typespecs': 'Type Specs',
    'subtype': 'Subtype',
}

OUTPUT_COLUMNS_TO_DROP = ['Ticker', 'Exchange', 'Type', 'Type Specs', 'Subtype']
OUTPUT_COLUMNS = [
    'Symbol',
    'ETF Name',
    'Theme Option',
    'Last Price',
    'Volume',
    'Average Volume 30D',
    'AUM',
    'Expense Ratio %',
    'Change %',
    'MTD %',
    '1M %',
    '3M %',
    '6M %',
    'YTD %',
    '1Y %',
]
INTEGER_COLUMNS = ['Volume', 'Average Volume 30D']


def make_output_file(theme_options):
    if set(theme_options) == set(TRADINGVIEW_THEME_OPTIONS):
        return 'all_etfs.csv'

    file_prefix = '_'.join(theme_options[0].lower().replace('.', '').replace('&', 'and').split())
    return f"{file_prefix}_etfs.csv"


def normalize_theme_option(theme_option):
    return ' '.join(theme_option.lower().replace('-', ' ').split()).rstrip('s')


def parse_theme_options(theme_options):
    if isinstance(theme_options, str):
        raw_options = theme_options.split(',')
    else:
        raw_options = []
        for theme_option in theme_options:
            raw_options.extend(theme_option.split(','))

    normalized_options = {
        normalize_theme_option(option): option for option in TRADINGVIEW_THEME_OPTIONS
    }

    resolved_options = []
    unknown_options = []
    for raw_option in raw_options:
        raw_option = raw_option.strip()
        if raw_option.lower() == 'all' or raw_option == '*':
            return TRADINGVIEW_THEME_OPTIONS

        normalized_option = normalize_theme_option(raw_option)
        if not normalized_option:
            continue

        resolved_option = normalized_options.get(normalized_option)
        if resolved_option:
            resolved_options.append(resolved_option)
        else:
            unknown_options.append(raw_option.strip())

    if unknown_options:
        supported_options = ', '.join(TRADINGVIEW_THEME_OPTIONS)
        raise ValueError(
            f"Unknown theme option(s): {', '.join(unknown_options)}. "
            f"Supported options: {supported_options}"
        )

    return resolved_options


def build_theme_filter(theme_options):
    filters = [col('holdings_region.tr') == theme_option for theme_option in theme_options]
    return filters[0] if len(filters) == 1 else Or(*filters)


def build_base_filters():
    filters = [col('exchange').isin(US_ETF_EXCHANGES)]

    if EXCLUDE_LEVERAGED_AND_INVERSE_ETFS:
        filters.extend(
            col('description').not_like(term)
            for term in LEVERAGED_INVERSE_DESCRIPTION_TERMS
        )

    return filters


def add_mtd_percent(df):
    if 'Perf.MTD' not in df or 'open|1M' not in df or 'close' not in df:
        return df

    last_price = pd.to_numeric(df['close'], errors='coerce')
    month_open = pd.to_numeric(df['open|1M'], errors='coerce')
    calculated_mtd = ((last_price - month_open) / month_open) * 100

    df['Perf.MTD'] = pd.to_numeric(df['Perf.MTD'], errors='coerce').fillna(calculated_mtd)
    return df.drop(columns=['open|1M'])


def format_output(df):
    df = add_mtd_percent(df)
    df = df.rename(columns=COLUMN_NAMES)
    df = df.drop(columns=OUTPUT_COLUMNS_TO_DROP, errors='ignore')

    numeric_columns = df.select_dtypes(include='number').columns
    df[numeric_columns] = df[numeric_columns].round(2)
    for column in INTEGER_COLUMNS:
        if column in df:
            df[column] = df[column].round(0).astype('Int64')

    if 'MTD %' in df:
        df = df.sort_values('MTD %', ascending=False, na_position='last')

    return df[[column for column in OUTPUT_COLUMNS if column in df.columns]]


def fetch_theme_etfs(theme_options=None, output_file=None):
    theme_options = parse_theme_options(theme_options or SELECTED_THEME_OPTIONS)
    output_file = output_file or make_output_file(theme_options)

    try:
        query = (
            Query()
            .set_markets('america')
            .select(*ETF_COLUMNS)
            .where(*build_base_filters())
            .where2(
                And(
                    build_theme_filter(theme_options),
                    col('type') == 'fund',
                    col('typespecs').has(['etf']),
                )
            )
            .order_by('aum', ascending=False)
            .limit(10000)
        )
        
        data = query.get_scanner_data(proxies={'http': '', 'https': ''})
        
        if data is not None and len(data) > 1:
            total_count = data[0]
            df = data[1]
            
            if not isinstance(df, pd.DataFrame):
                df = pd.DataFrame(df)
                
            if not df.empty:
                df = format_output(df)
                df.to_csv(output_file, index=False, float_format='%.2f')

                print(f"Successfully retrieved {len(df)} of {total_count} matching ETFs.")
                print(f"Theme options: {', '.join(theme_options)}")
                print(f"Saved results to {output_file}")
                print(df.head(20))
            else:
                print("Data returned, but the DataFrame is empty. Adjust your filters.")
        else:
            print("No data returned. Please verify the exchange settings.")
            
    except Exception as e:
        print(f"An error occurred: {e}")


def parse_args():
    parser = argparse.ArgumentParser(
        description='Fetch US-listed ETFs matching one or more TradingView theme options.'
    )
    parser.add_argument(
        'theme_options',
        nargs='*',
        help='Theme option(s), for example: "Developed markets" "Emerging markets". Commas, "all", and "*" are also accepted.',
    )
    parser.add_argument(
        '-o',
        '--output',
        help='CSV output path. Defaults to a file name based on the first search term.',
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    fetch_theme_etfs(args.theme_options or SELECTED_THEME_OPTIONS, args.output)
