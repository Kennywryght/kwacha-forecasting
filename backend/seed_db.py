import os, sys
os.chdir('/opt/render/project/src/backend')
sys.path.insert(0, '.')

from db.database import init_db, SessionLocal
from db.models import ExchangeRate
from sqlalchemy import func
from datetime import date, timedelta
import pandas as pd
import numpy as np

init_db()
db = SessionLocal()

# Step 1: Seed from CSV if empty
count = db.query(func.count(ExchangeRate.id)).scalar()
print(f'Rows before: {count}')

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

# Step 2: ALWAYS add projected data to today
real_data = db.query(ExchangeRate).filter(
    ExchangeRate.date >= '2024-08-01'
).order_by(ExchangeRate.date.asc()).all()

if len(real_data) >= 5:
    rates = [float(r.rate) for r in real_data]
    last_rate = rates[-1]
    last_date = real_data[-1].date
    
    print(f'Last real: {last_date} Rate: {last_rate:.2f}')
    
    current_date = last_date + timedelta(days=1)
    today = date.today()
    current_rate = last_rate
    added = 0
    skipped = 0
    
    while current_date <= today:
        if current_date.weekday() < 5:  # Weekday
            # Small realistic variation
            change = np.random.normal(0, 0.5)  # Small daily changes
            current_rate += change
            current_rate = round(max(current_rate, 100), 2)
            
            existing = db.query(ExchangeRate).filter(ExchangeRate.date == current_date).first()
            if not existing:
                db.add(ExchangeRate(date=current_date, rate=current_rate, source='projection'))
                added += 1
            else:
                skipped += 1
        
        current_date += timedelta(days=1)
    
    db.commit()
    print(f'Added {added} projected days, skipped {skipped} existing')
    print(f'Final rate: {current_rate:.2f}')

total = db.query(func.count(ExchangeRate.id)).scalar()
latest = db.query(ExchangeRate).order_by(ExchangeRate.date.desc()).first()
print(f'Total: {total}, Latest: {latest.date} = {latest.rate}')
db.close()
