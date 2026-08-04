import pandas as pd

path = r'D:/TMP/Momentum_Scanner_USA_Technology_05-7-2026.csv'
df = pd.read_csv(path)
print('rows', len(df))
print('cols', len(df.columns))
print(df.columns.tolist())
print(df['Final_Decision'].value_counts(dropna=False).to_string())
print('\nSample Active:')
print(df[df['Final_Decision']=='MOMENTUM_ACTIVE'][['Ticker','Final_Decision','Score','Action_Status','Entry_Timing_Status','Final_Decision_Reason']].head(30).to_string(index=False))
