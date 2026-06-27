import pandas as pd
df = pd.read_csv('data/raw/mwk_usd_final_dataset.csv')
print(f'Rows: {len(df)}')
print(f'Date range: {df["date"].min()} to {df["date"].max()}')
print(f'Columns: {list(df.columns)}')
