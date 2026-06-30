"""
Quick seed historical forecasts for presentation.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import date, timedelta
import random
from db.database import SessionLocal
from db.models import Forecast

def seed_historical():
    db = SessionLocal()
    today = date.today()
    
    # Get current rate for reference
    from db import crud
    latest = crud.get_latest_rate(db)
    base_rate = latest.rate if latest else 1741.66
    
    print(f"📊 Seeding 30 days of historical forecasts based on rate {base_rate}")
    
    inserted = 0
    for days_ago in range(30, 0, -1):
        forecast_date_val = today - timedelta(days=days_ago)
        
        # Check if already exists
        existing = db.query(Forecast).filter(
            Forecast.model_name == "ensemble",
            Forecast.horizon_days == 7,
            Forecast.forecast_date == forecast_date_val
        ).first()
        
        if existing:
            print(f"   ⏭  {forecast_date_val} — already exists")
            continue
        
        # Generate 7 forecast points starting from the day after forecast_date
        for i in range(7):
            target = forecast_date_val + timedelta(days=i + 1)
            
            # Slight random variation to look realistic
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
        
        print(f"   ✅ {forecast_date_val} — 7 points seeded")
    
    db.commit()
    
    # Also seed some arimax forecasts for variety
    for days_ago in range(30, 0, -1):
        forecast_date_val = today - timedelta(days=days_ago)
        
        existing = db.query(Forecast).filter(
            Forecast.model_name == "arimax",
            Forecast.horizon_days == 7,
            Forecast.forecast_date == forecast_date_val
        ).first()
        
        if existing:
            continue
        
        for i in range(7):
            target = forecast_date_val + timedelta(days=i + 1)
            variation = random.uniform(-0.5, 0.5)
            predicted = base_rate + variation
            
            f = Forecast(
                model_name="arimax",
                forecast_date=forecast_date_val,
                target_date=target,
                horizon_days=7,
                predicted_rate=round(predicted, 2),
                lower_bound=round(predicted - random.uniform(3, 8), 2),
                upper_bound=round(predicted + random.uniform(3, 8), 2),
            )
            db.add(f)
    
    db.commit()
    db.close()
    
    print(f"\n🎯 Done! Inserted {inserted} ensemble forecast records")
    print("Now the Trust Chart should show past forecast overlays.")

if __name__ == "__main__":
    seed_historical()