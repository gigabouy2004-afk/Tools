import random
from pathlib import Path
import pandas as pd
import yfinance as yf

INPUT_PATH = Path(r'D:/TMP/Momentum_Scanner_USA_Technology_05-7-2026.csv')

assert INPUT_PATH.exists(), f'Missing file: {INPUT_PATH}'

df = pd.read_csv(INPUT_PATH)

# Confirm engine categories
counts = df['Final_Decision'].value_counts(dropna=False)
print('Counts:')
print(counts)
print()

# Active sample set: validate all
active_df = df[df['Final_Decision'] == 'MOMENTUM_ACTIVE']
hold_df = df[df['Final_Decision'] == 'MOMENTUM_PRESENT_WAIT_CONFIRMATION']
reject_df = df[df['Final_Decision'] == 'REJECT']

print('Active rows:', len(active_df))
print('Hold rows:', len(hold_df))
print('Reject rows:', len(reject_df))
print()

# Choose random sample for hold and reject
random.seed(12345)
hold_sample = hold_df.sample(n=min(100, len(hold_df)), random_state=12345)
reject_sample = reject_df.sample(n=min(100, len(reject_df)), random_state=12345)

# Helper functions

def fetch_daily_data(ticker, period='1mo'):
    ticker_obj = yf.Ticker(ticker)
    try:
        hist = ticker_obj.history(period=period, interval='1d', auto_adjust=False)
    except Exception as exc:
        print(f'Failed historical fetch for {ticker}: {exc}')
        return pd.DataFrame()
    return hist


def check_active_row(row):
    ticker = row['Ticker']
    hist = fetch_daily_data(ticker, period='3mo')
    if hist.empty:
        return {'Ticker': ticker, 'error': 'no live data'}

    latest = hist.iloc[-1]
    ema10 = latest['Close'] if False else None
    result = {
        'Ticker': ticker,
        'Score': row['Score'],
        'Entry_Timing_Status': row['Entry_Timing_Status'],
        'Final_Decision_Reason': row['Final_Decision_Reason'],
        'Close': row['Close'],
        'Live_Close': latest['Close'],
        'Volume': latest['Volume'],
        'Recent_Close': latest['Close'],
        'Notes': '',
    }
    return result


results_active = [check_active_row(row) for _, row in active_df.iterrows()]

print('Active checks done:', len(results_active))
print('Sample Active results:')
print(results_active[:5])
