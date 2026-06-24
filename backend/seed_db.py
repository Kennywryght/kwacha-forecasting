import os, sys
sys.path.insert(0, '.')

from db.database import init_db, SessionLocal
from db.models import ExchangeRate
from sqlalchemy import func
from datetime import date
import pandas as pd

init_db()
db = SessionLocal()

# Check current state
count = db.query(func.count(ExchangeRate.id)).scalar()
latest = db.query(ExchangeRate).order_by(ExchangeRate.date.desc()).first()
if latest:
    print(f'Current: {count} rows, Latest: {latest.date} = {latest.rate} (source: {latest.source})')
else:
    print(f'Current: {count} rows')

# Step 1: Seed historical CSV data (only if database is empty)
if count == 0:
    paths = ['data/raw/mwk_usd_final_dataset.csv', '../data/raw/mwk_usd_final_dataset.csv']
    for p in paths:
        if os.path.exists(p):
            print(f'Loading historical data: {p}')
            df = pd.read_csv(p)
            dc = [c for c in df.columns if c.lower()=='date'][0]
            rc = [c for c in df.columns if c.lower() in ['rate','mwk_usd']][0]
            df[dc] = pd.to_datetime(df[dc])
            added = 0
            for _, row in df.iterrows():
                try:
                    db.add(ExchangeRate(date=row[dc].date(), rate=float(row[rc]), source='historical_csv'))
                    added += 1
                except:
                    pass
            db.commit()
            print(f'Seeded {added} historical rows')
            break

# Step 2: Always update today's rate from Google
today = date.today()
existing = db.query(ExchangeRate).filter(ExchangeRate.date == today).first()

print('Fetching today rate from Google...')
try:
    
    result = fetch_current_rate()
    
    if result and result.get('rate'):
        if existing:
            old_rate = existing.rate
            old_source = existing.source
            existing.rate = result['rate']
            existing.source = 'google'
            print(f'✅ Updated today rate: {old_rate} → {result["rate"]} (was: {old_source})')
        else:
            db.add(ExchangeRate(date=today, rate=result['rate'], source='google'))
            print(f'✅ Added today Google rate: {result["rate"]}')
        db.commit()
    else:
        print('⚠️ Google failed, keeping existing rate' if existing else '❌ No rate available')
except Exception as e:
    print(f'Error fetching Google rate: {e}')
    if not existing:
        print('Trying API fallback...')
        try:
            from ml.pipeline.live_fetcher import fetch_current_rate
            live = fetch_current_rate()
            if live and live.get('rate'):
                db.add(ExchangeRate(date=today, rate=live['rate'], source='live_api'))
                db.commit()
                print(f'Added API fallback: {live["rate"]}')
        except Exception as e2:
            print(f'Fallback also failed: {e2}')

# Final status
total = db.query(func.count(ExchangeRate.id)).scalar()
latest = db.query(ExchangeRate).order_by(ExchangeRate.date.desc()).first()
print(f'Final: {total} rows, Latest: {latest.date} = {latest.rate} (source: {latest.source})')
db.close()