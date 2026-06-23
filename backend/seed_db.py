import os, sys
os.chdir('/opt/render/project/src/backend')
sys.path.insert(0, '.')

from db.database import init_db, SessionLocal
from db.models import ExchangeRate  # Import the model directly
from sqlalchemy import func
import pandas as pd

init_db()
db = SessionLocal()
count = db.query(func.count(ExchangeRate.id)).scalar()
print(f'Rows: {count}')

if count == 0:
    paths = ['data/raw/mwk_usd_final_dataset.csv', '../data/raw/mwk_usd_final_dataset.csv']
    for p in paths:
        if os.path.exists(p):
            print(f'Loading: {p}')
            df = pd.read_csv(p)
            date_col = [c for c in df.columns if c.lower()=='date'][0]
            rate_col = [c for c in df.columns if c.lower() in ['rate','mwk_usd']][0]
            df[date_col] = pd.to_datetime(df[date_col])
            for _, row in df.iterrows():
                try:
                    db.add(ExchangeRate(date=row[date_col].date(), rate=float(row[rate_col]), source='seed'))
                except: pass
            db.commit()
            print(f'Done seeding')
            break
    else:
        print('No CSV found. Listing files:')
        import subprocess
        result = subprocess.run(['find', '/opt/render/project/src', '-name', '*.csv'], capture_output=True, text=True)
        print(result.stdout[:500])
db.close()
