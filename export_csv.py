import sys; sys.path.insert(0, 'backend')
import pandas as pd
from db.database import SessionLocal
from db.models import ExchangeRate

db = SessionLocal()
rates = db.query(ExchangeRate).order_by(ExchangeRate.date.asc()).all()
db.close()

df = pd.DataFrame([{
    'date': r.date,
    'rate': float(r.rate),
    'open_rate': float(r.open_rate) if r.open_rate else '',
    'high_rate': float(r.high_rate) if r.high_rate else '',
    'low_rate': float(r.low_rate) if r.low_rate else '',
    'daily_return': float(r.daily_return) if r.daily_return else '',
    'is_interpolated': r.is_interpolated,
    'source': r.source or 'historical',
} for r in rates])

df.to_csv('data/raw/mwk_usd_final_dataset.csv', index=False)
print(f'Saved {len(df)} rows to data/raw/mwk_usd_final_dataset.csv')
print(f'Date range: {df["date"].min()} to {df["date"].max()}')
print(f'Last rate: {df["rate"].iloc[-1]}')
