"""Startup script for Render deployment."""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from core.logging_config import setup_logging
from db.database import init_db, SessionLocal
from db.models import ExchangeRate
from sqlalchemy import func
import pandas as pd

setup_logging()

def seed_initial_data():
    """Seed database with CSV data if empty."""
    db = SessionLocal()
    
    try:
        # Check if data exists
        count = db.query(func.count(ExchangeRate.id)).scalar()
        
        if count > 0:
            print(f"✅ Database already has {count} rows")
            return
        
        print("📊 Seeding initial data...")
        
        # Try to load from CSV
        csv_paths = [
            'data/raw/mwk_usd_final_dataset.csv',
            'data/processed/mwk_usd_clean.csv',
            '../data/raw/mwk_usd_final_dataset.csv',
            '../data/processed/mwk_usd_clean.csv',
        ]
        
        for path in csv_paths:
            if os.path.exists(path):
                print(f"Loading from {path}")
                df = pd.read_csv(path)
                
                # Detect columns
                date_col = next((c for c in df.columns if c.lower() == 'date'), None)
                rate_col = next((c for c in df.columns if c.lower() in ['rate', 'close', 'mwk_usd']), None)
                
                if date_col and rate_col:
                    df[date_col] = pd.to_datetime(df[date_col])
                    df = df.dropna(subset=[date_col, rate_col])
                    
                    for _, row in df.iterrows():
                        rate = ExchangeRate(
                            date=row[date_col].date() if hasattr(row[date_col], 'date') else pd.to_datetime(row[date_col]).date(),
                            rate=float(row[rate_col]),
                            source='seed_data'
                        )
                        db.add(rate)
                    
                    db.commit()
                    print(f"✅ Seeded {len(df)} rows")
                    return
        
        print("⚠️  No CSV data found, starting with empty database")
        
    except Exception as e:
        db.rollback()
        print(f"Error seeding data: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    print("🚀 Initializing database...")
    init_db()
    seed_initial_data()
    print("✅ Startup complete")
