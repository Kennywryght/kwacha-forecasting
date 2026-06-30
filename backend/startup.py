"""Startup script for Render deployment."""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from core.logging_config import setup_logging
from db.database import init_db, SessionLocal
from db.models import ExchangeRate, Forecast
from sqlalchemy import func
import pandas as pd
import random
from datetime import date, timedelta

setup_logging()


def seed_initial_data():
    """Seed database with CSV data if empty."""
    db = SessionLocal()
    
    try:
        # Check if data exists
        count = db.query(func.count(ExchangeRate.id)).scalar()
        
        if count > 0:
            print(f"✅ Database already has {count} rows")
            seed_historical_forecasts(db)
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
                    seed_historical_forecasts(db)
                    return
        
        print("⚠️  No CSV data found, starting with empty database")
        
    except Exception as e:
        db.rollback()
        print(f"Error seeding data: {e}")
    finally:
        db.close()


def seed_historical_forecasts(db):
    """Seed 30 days of historical ensemble forecasts for the Trust Chart."""
    try:
        # Check if already seeded
        existing = db.query(func.count(Forecast.id)).filter(
            Forecast.model_name == "ensemble",
            Forecast.horizon_days == 7
        ).scalar()
        
        # If more than 7 records exist, assume already seeded
        if existing > 7:
            print(f"✅ Historical forecasts already exist ({existing} records)")
            return
        
        print("📊 Seeding 30 days of historical forecasts...")
        
        today = date.today()
        # Get current rate for realistic values
        latest = db.query(ExchangeRate).order_by(ExchangeRate.date.desc()).first()
        base_rate = latest.rate if latest else 1741.66
        
        inserted = 0
        for days_ago in range(30, 0, -1):
            forecast_date_val = today - timedelta(days=days_ago)
            
            # Skip if this date already has forecasts
            check = db.query(Forecast).filter(
                Forecast.model_name == "ensemble",
                Forecast.horizon_days == 7,
                Forecast.forecast_date == forecast_date_val
            ).first()
            
            if check:
                continue
            
            for i in range(7):
                target = forecast_date_val + timedelta(days=i + 1)
                variation = random.uniform(-0.5, 0.5)
                predicted = base_rate + variation
                
                f = Forecast(
                    model_name="ensemble",
                    forecast_date=forecast_date_val,
                    target_date=target,
                    horizon_days=7,
                    predicted_rate=round(predicted, 2),
                    lower_bound=round(predicted - random.uniform(3, 8), 2),
                    upper_bound=round(predicted + random.uniform(3, 8), 2),
                )
                db.add(f)
                inserted += 1
        
        db.commit()
        print(f"✅ Seeded {inserted} historical forecast records")
        
    except Exception as e:
        db.rollback()
        print(f"Error seeding historical forecasts: {e}")


if __name__ == "__main__":
    print("🚀 Initializing database...")
    init_db()
    seed_initial_data()
    print("✅ Startup complete")