# Fix pretrain.py to use database instead of CSV
with open('backend/pretrain.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace CSV loading with database loading
old = """# Find CSV
csv_paths = ['data/raw/mwk_usd_final_dataset.csv', '../data/raw/mwk_usd_final_dataset.csv']
df = None
for p in csv_paths:
    if os.path.exists(p):
        df = pd.read_csv(p)
        dc = [c for c in df.columns if c.lower()=='date'][0]
        rc = [c for c in df.columns if c.lower() in ['rate','mwk_usd']][0]
        df = df.rename(columns={dc: 'date', rc: 'rate'})
        df['date'] = pd.to_datetime(df['date'])
        break

if df is not None and len(df) > 30:"""

new = """# Load from database (has projected data to today)
from db.database import SessionLocal
from db.models import ExchangeRate
db = SessionLocal()
rates = db.query(ExchangeRate).order_by(ExchangeRate.date.asc()).all()
db.close()

if len(rates) > 30:
    import pandas as pd
    df = pd.DataFrame([{'date': r.date, 'rate': r.rate} for r in rates])
    df['date'] = pd.to_datetime(df['date'])
    print(f'Loaded {len(df)} rows from database ({df[\"date\"].min()} to {df[\"date\"].max()})')"""

content = content.replace(old, new)

with open('backend/pretrain.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('pretrain.py updated to use database')
