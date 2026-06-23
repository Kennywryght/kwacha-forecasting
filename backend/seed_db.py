import os, sys
os.chdir('/opt/render/project/src/backend')
sys.path.insert(0, '.')

from db.database import init_db, SessionLocal
from db.models import ExchangeRate
from sqlalchemy import func
from datetime import date, timedelta
import pandas as pd
import numpy as np

# Step 1: Init and seed from CSV
init_db()
db = SessionLocal()
count = db.query(func.count(ExchangeRate.id)).scalar()
print(f'Rows before seed: {count}')

if count == 0:
    paths = ['data/raw/mwk_usd_final_dataset.csv', '../data/raw/mwk_usd_final_dataset.csv']
    for p in paths:
        if os.path.exists(p):
            print(f'Loading: {p}')
            df = pd.read_csv(p)
            dc = [c for c in df.columns if c.lower()=='date'][0]
            rc = [c for c in df.columns if c.lower() in ['rate','mwk_usd']][0]
            df[dc] = pd.to_datetime(df[dc])
            for _, row in df.iterrows():
                try:
                    db.add(ExchangeRate(date=row[dc].date(), rate=float(row[rc]), source='seed'))
                except: pass
            db.commit()
            print(f'Seeded {len(df)} rows')
            break

# Step 2: Add projected data from last real date to today
real_data = db.query(ExchangeRate).filter(
    ExchangeRate.date >= '2024-08-01'
).order_by(ExchangeRate.date.asc()).all()

if len(real_data) >= 30:
    rates = [float(r.rate) for r in real_data]
    last_rate = rates[-1]
    last_date = real_data[-1].date
    
    rates_series = pd.Series(rates)
    trend = rates_series.diff().mean()
    volatility = rates_series.diff().std()
    
    print(f'Last real: {last_date} Rate: {last_rate:.2f}')
    print(f'Trend: {trend:.4f} Vol: {volatility:.4f}')
    
    current_date = last_date + timedelta(days=1)
    today = date.today()
    current_rate = last_rate
    added = 0
    
    while current_date <= today:
        if current_date.weekday() < 5:
            base_change = trend
            random_component = np.random.normal(0, volatility * 0.3)
            daily_change = base_change + random_component
            daily_change = max(min(daily_change, current_rate * 0.01), -current_rate * 0.01)
            current_rate += daily_change
            current_rate = round(current_rate, 2)
            
            existing = db.query(ExchangeRate).filter(ExchangeRate.date == current_date).first()
            if not existing:
                db.add(ExchangeRate(date=current_date, rate=current_rate, source='projection'))
                added += 1
        
        current_date += timedelta(days=1)
    
    db.commit()
    print(f'Added {added} projected days')
    print(f'Final rate: {current_rate:.2f}')

total = db.query(func.count(ExchangeRate.id)).scalar()
latest = db.query(ExchangeRate).order_by(ExchangeRate.date.desc()).first()
print(f'Total: {total}, Latest: {latest.date} = {latest.rate}')
db.close()
