import random
from pathlib import Path

import pandas as pd
import yfinance as yf

import Momentum_Detector_V6 as engine

INPUT_PATH = Path(r'D:/TMP/Momentum_Scanner_USA_Technology_05-7-2026.csv')
assert INPUT_PATH.exists(), f'Missing file: {INPUT_PATH}'

OUTPUT_PATH = Path('D:/TMP/Momentum_Scanner_USA_Technology_05-7-2026_review.csv')


def fetch_daily_data(ticker, period='2y'):
    df = engine.fetch_daily_data(ticker, period=period)
    return df


def fetch_hourly_data(ticker):
    return engine.fetch_hourly_data(ticker)


def compute_current_classification(ticker, market='auto'):
    df = fetch_daily_data(ticker, period='2y')
    if df.empty:
        return None, 'no_daily_data'
    exchange_profile = engine.exchange_profile_for_ticker(ticker, market)
    benchmark_ticker = engine.benchmark_for_ticker(ticker, market)
    benchmark_df = fetch_daily_data(benchmark_ticker, period='2y')
    if benchmark_df.empty:
        return None, 'no_benchmark_data'
    calc_df = engine.calculate_v5_indicators(df, benchmark_df, benchmark_ticker=benchmark_ticker, exchange_profile=exchange_profile)
    if calc_df.empty:
        return None, 'calc_empty'
    latest = calc_df.iloc[-1:]
    hourly_df = fetch_hourly_data(ticker)
    timing = engine.evaluate_intraday_timing(latest, hourly_df, {})
    scores, weekly_trend = engine.score_v5(latest.iloc[0])
    scores = engine.apply_commercial_readiness_score(latest.iloc[0], scores, weekly_trend, timing)
    long_term_status, reason = engine.classify_signal(latest.iloc[0], scores, weekly_trend, timing)
    final_decision, _, final_reason = engine.resolve_final_decision(latest.iloc[0], scores, weekly_trend, timing, long_term_status, reason)
    return {
        'Final_Decision': final_decision,
        'Long_Term_Status': long_term_status,
        'Entry_Timing_Status': timing['status'],
        'Score': scores['final'],
        'Reason': final_reason,
        'Weekly_Trend': weekly_trend,
        'RS_126D_Excess_Pct': latest.iloc[0].get('RS_126D_Excess_Pct', float('nan')),
        'Close': latest.iloc[0]['Close'],
        'EMA_20': latest.iloc[0]['EMA_20'],
        'EMA_50': latest.iloc[0]['EMA_50'],
        'EMA_200': latest.iloc[0]['EMA_200'],
        'Close_Below_EMA20': latest.iloc[0]['Close_Below_EMA20'],
        'Close_Location_Pct': latest.iloc[0]['Close_Location_Pct'],
        'Relative_Volume_20': latest.iloc[0]['Relative_Volume_20'],
        'Avg_Dollar_Volume_50D': latest.iloc[0]['Avg_Dollar_Volume_50D'],
        'Liquidity_Status': latest.iloc[0]['Liquidity_Status'],
        'Distribution_Days_50': latest.iloc[0]['Distribution_Days_50'],
        'ATR_Pct': latest.iloc[0]['ATR_Pct'],
    }, None


def review_rows(rows, label):
    results = []
    for idx, row in rows.iterrows():
        ticker = row['Ticker']
        current, err = compute_current_classification(ticker)
        note = ''
        if err:
            note = err
        else:
            if label == 'Active':
                note = 'Matches Active' if current['Final_Decision'] == 'MOMENTUM_ACTIVE' else f'Now {current["Final_Decision"]}'
            else:
                note = 'Non-Active' if current['Final_Decision'] != 'MOMENTUM_ACTIVE' else 'Now Active'
        results.append({
            'Ticker': ticker,
            'Original_Final_Decision': row['Final_Decision'],
            'Original_Score': row['Score'],
            'Original_Action_Status': row['Action_Status'],
            'Original_Entry_Timing_Status': row['Entry_Timing_Status'],
            'Original_Reason': row['Final_Decision_Reason'],
            'Current_Final_Decision': current['Final_Decision'] if current else '',
            'Current_Score': current['Score'] if current else '',
            'Current_Action_Status': current['Long_Term_Status'] if current else '',
            'Current_Entry_Timing_Status': current['Entry_Timing_Status'] if current else '',
            'Current_Reason': current['Reason'] if current else '',
            'Current_Weekly_Trend': current['Weekly_Trend'] if current else '',
            'Current_Close': current['Close'] if current else '',
            'Current_EMA_20': current['EMA_20'] if current else '',
            'Current_EMA_50': current['EMA_50'] if current else '',
            'Current_EMA_200': current['EMA_200'] if current else '',
            'Current_Close_Below_EMA20': current['Close_Below_EMA20'] if current else '',
            'Current_Close_Location_Pct': current['Close_Location_Pct'] if current else '',
            'Current_Relative_Volume_20': current['Relative_Volume_20'] if current else '',
            'Current_Avg_Dollar_Volume_50D': current['Avg_Dollar_Volume_50D'] if current else '',
            'Current_Liquidity_Status': current['Liquidity_Status'] if current else '',
            'Current_Distribution_Days_50': current['Distribution_Days_50'] if current else '',
            'Current_ATR_Pct': current['ATR_Pct'] if current else '',
            'Review_Label': label,
            'Review_Note': note,
        })
    return pd.DataFrame(results)


df = pd.read_csv(INPUT_PATH)
active_df = df[df['Final_Decision'] == 'MOMENTUM_ACTIVE']
hold_df = df[df['Final_Decision'] == 'MOMENTUM_PRESENT_WAIT_CONFIRMATION']
reject_df = df[df['Final_Decision'] == 'REJECT']

hold_sample = hold_df.sample(n=min(100, len(hold_df)), random_state=12345)
reject_sample = reject_df.sample(n=min(100, len(reject_df)), random_state=12345)

print('Active count:', len(active_df))
print('Hold count:', len(hold_df))
print('Reject count:', len(reject_df))
print()

review_active = review_rows(active_df, 'Active')
review_hold = review_rows(hold_sample, 'Hold')
review_reject = review_rows(reject_sample, 'Reject')

summary = {
    'Active_CurrentActive': int((review_active['Current_Final_Decision'] == 'MOMENTUM_ACTIVE').sum()),
    'Active_CurrentNonActive': int((review_active['Current_Final_Decision'] != 'MOMENTUM_ACTIVE').sum()),
    'Hold_NowActive': int((review_hold['Current_Final_Decision'] == 'MOMENTUM_ACTIVE').sum()),
    'Hold_NowNonActive': int((review_hold['Current_Final_Decision'] != 'MOMENTUM_ACTIVE').sum()),
    'Reject_NowActive': int((review_reject['Current_Final_Decision'] == 'MOMENTUM_ACTIVE').sum()),
    'Reject_NowNonActive': int((review_reject['Current_Final_Decision'] != 'MOMENTUM_ACTIVE').sum()),
}

print('Summary:')
print(summary)

review_df = pd.concat([review_active, review_hold, review_reject], ignore_index=True)
review_df.to_csv(OUTPUT_PATH, index=False)
print(f'Review output written to {OUTPUT_PATH}')
