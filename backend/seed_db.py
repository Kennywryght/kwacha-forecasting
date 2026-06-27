import os, sys
sys.path.insert(0, '.')

from db.database import init_db, SessionLocal
from db.models import ExchangeRate
from sqlalchemy import func
from datetime import date, timedelta
import pandas as pd
import numpy as np

init_db()
db = SessionLocal()

count = db.query(func.count(ExchangeRate.id)).scalar()
print(f'Current rows: {count}')

# Step 1: Seed from CSV if empty (3504 rows with research data)
if count == 0:
    paths = ['data/raw/mwk_usd_final_dataset.csv', '../data/raw/mwk_usd_final_dataset.csv']
    for p in paths:
        if os.path.exists(p):
            print(f'Loading: {p}')
            df = pd.read_csv(p)
            df['date'] = pd.to_datetime(df['date'])
            added = 0
            for _, row in df.iterrows():
                try:
                    db.add(ExchangeRate(
                        date=row['date'].date() if hasattr(row['date'], 'date') else pd.to_datetime(row['date']).date(),
                        rate=float(row['rate']),
                        source=str(row.get('source', 'csv_import'))
                    ))
                    added += 1
                except:
                    pass
            db.commit()
            print(f'Seeded {added} rows from CSV')
            break

# Step 2: Fill gaps between last CSV date and yesterday
latest = db.query(ExchangeRate).order_by(ExchangeRate.date.desc()).first()
yesterday = date.today() - timedelta(days=1)

if latest and latest.date < yesterday:
    print(f'Filling gap: {latest.date} → {yesterday}')
    
    # Get last 30 days of data for trend calculation
    recent = db.query(ExchangeRate).filter(
        ExchangeRate.date >= latest.date - timedelta(days=30)
    ).order_by(ExchangeRate.date.asc()).all()
    
    if len(recent) >= 5:
        rates = [float(r.rate) for r in recent]
        last_rate = rates[-1]
        current_date = latest.date + timedelta(days=1)
        
        # Calculate trend from recent data
        trend = np.mean([rates[i+1] - rates[i] for i in range(len(rates)-1)])
        volatility = np.std([rates[i+1] - rates[i] for i in range(len(rates)-1)])
        
        filled = 0
        while current_date <= yesterday:
            if current_date.weekday() < 5:  # Business days only
                # Small variation based on historical volatility
                change = np.random.normal(trend, max(volatility * 0.5, 0.01))
                last_rate += change
                last_rate = round(max(last_rate, 100), 2)
                
                existing = db.query(ExchangeRate).filter(ExchangeRate.date == current_date).first()
                if not existing:
                    db.add(ExchangeRate(
                        date=current_date,
                        rate=last_rate,
                        source='gap_fill'
                    ))
                    filled += 1
            
            current_date += timedelta(days=1)
        
        db.commit()
        print(f'Filled {filled} days')

# Step 3: Add today's rate from live API
today = date.today()
existing_today = db.query(ExchangeRate).filter(ExchangeRate.date == today).first()

if existing_today:
    # Update today's rate with live data
    from ml.pipeline.live_fetcher import fetch_current_rate
    live = fetch_current_rate()
    if live and live.get('rate'):
        existing_today.rate = live['rate']
        existing_today.source = 'live_api'
        db.commit()
        print(f'Updated today rate: {live["rate"]}')
    else:
        print(f'Today rate unchanged: {existing_today.rate}')
else:
    from ml.pipeline.live_fetcher import fetch_current_rate
    live = fetch_current_rate()
    if live and live.get('rate'):
        db.add(ExchangeRate(date=today, rate=live['rate'], source='live_api'))
        db.commit()
        print(f'Added today rate: {live["rate"]}')
    else:
        print('No live rate available for today')

# Final status
total = db.query(func.count(ExchangeRate.id)).scalar()
latest = db.query(ExchangeRate).order_by(ExchangeRate.date.desc()).first()
print(f'Final: {total} rows, Latest: {latest.date} = {latest.rate} (source: {latest.source})')
db.close()