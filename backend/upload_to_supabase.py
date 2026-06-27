"""
Upload directly to Supabase PostgreSQL using psycopg2
"""
import sys, os
sys.path.insert(0, '.')

# Your Supabase connection
DATABASE_URL = "postgresql://postgres:Kwacha2002@db.demjygpvuignkqfggbzb.supabase.co:5432/postgres"

import psycopg2
from db.database import SessionLocal
from db.models import ExchangeRate

# Connect to Supabase
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# Load local data
db = SessionLocal()
rates = db.query(ExchangeRate).order_by(ExchangeRate.date.asc()).all()
db.close()

print(f'Uploading {len(rates)} rows to Supabase...')

uploaded = 0
for r in rates:
    try:
        cur.execute("""
            INSERT INTO exchange_rates (date, rate, open_rate, high_rate, low_rate, daily_return, is_interpolated, source)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (date) DO UPDATE SET
                rate = EXCLUDED.rate,
                source = EXCLUDED.source
        """, (
            r.date, float(r.rate),
            float(r.open_rate) if r.open_rate else None,
            float(r.high_rate) if r.high_rate else None,
            float(r.low_rate) if r.low_rate else None,
            float(r.daily_return) if r.daily_return else None,
            r.is_interpolated or False,
            r.source or 'historical'
        ))
        uploaded += 1
        if uploaded % 500 == 0:
            conn.commit()
            print(f'  Uploaded {uploaded}/{len(rates)}')
    except Exception as e:
        print(f'  Error: {e}')

conn.commit()
cur.execute("SELECT COUNT(*) FROM exchange_rates")
count = cur.fetchone()[0]
print(f'\nDone! {uploaded} uploaded, {count} total in Supabase')
cur.close()
conn.close()