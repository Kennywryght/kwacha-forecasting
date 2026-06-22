#!/bin/bash
# Render prestart script - seeds database from CSV

cd /opt/render/project/src

echo "Looking for CSV files..."
find . -name "*.csv" -type f 2>/dev/null

python3 << 'PYEOF'
import os, sys
sys.path.insert(0, 'backend')
os.chdir('backend')

from db.database import init_db, SessionLocal
from db.models import ExchangeRate
from sqlalchemy import func
import pandas as pd

init_db()
db = SessionLocal()
count = db.query(func.count(ExchangeRate.id)).scalar()
print(f'Current rows: {count}')

if count == 0:
    csv_paths = [
        'data/raw/mwk_usd_final_dataset.csv',
        '../data/raw/mwk_usd_final_dataset.csv',
        'data/processed/mwk_usd_clean.csv',
        '../data/processed/mwk_usd_clean.csv',
    ]
    for p in csv_paths:
        if os.path.exists(p):
            print(f'LOADING: {p}')
            df = pd.read_csv(p)
            date_col = [c for c in df.columns if c.lower()=='date'][0]
            rate_col = [c for c in df.columns if c.lower() in ['rate','mwk_usd']][0]
            df[date_col] = pd.to_datetime(df[date_col])
            n = 0
            for _, row in df.iterrows():
                try:
                    db.add(ExchangeRate(date=row[date_col].date(), rate=float(row[rate_col]), source='seed'))
                    n += 1
                except:
                    pass
            db.commit()
            print(f'SEEDED {n} rows')
            break
    else:
        print('NO CSV FOUND')
else:
    print(f'Database already has {count} rows')

db.close()
print('Done seeding')
PYEOF
