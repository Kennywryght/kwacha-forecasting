"""
Fetch real MWK/USD data using Frankfurter API (free, no key needed).
"""

import sys
import os
sys.path.insert(0, 'backend')

import requests
import pandas as pd
from datetime import datetime, timedelta
from db.database import SessionLocal
from db.models import ExchangeRate
from sqlalchemy import func
from core.logging_config import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)

def fetch_frankfurter_data():
    """Fetch MWK/USD from Frankfurter API."""
    
    db = SessionLocal()
    
    try:
        # Check current data
        latest = db.query(func.max(ExchangeRate.date)).scalar()
        logger.info(f"Latest date in DB: {latest}")
        
        # Get real data from Frankfurter (free, no API key)
        # Frankfurter gives USD→MWK rate (how many MWK per 1 USD)
        start_date = '2024-11-01'  # Go back a bit to get overlapping real data
        end_date = datetime.now().strftime('%Y-%m-%d')
        
        url = f"https://api.frankfurter.app/{start_date}..{end_date}?from=USD&to=MWK"
        logger.info(f"Fetching from Frankfurter: {start_date} to {end_date}")
        
        response = requests.get(url, timeout=15)
        
        if response.status_code != 200:
            logger.error(f"Frankfurter API error: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return
        
        data = response.json()
        
        if 'rates' not in data:
            logger.error("No 'rates' in response")
            logger.error(f"Response: {data}")
            return
        
        inserted = 0
        updated = 0
        
        for date_str, rates in sorted(data['rates'].items()):
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            rate_mwk = rates.get('MWK')
            
            if not rate_mwk:
                continue
            
            # Frankfurter returns: 1 USD = X MWK
            # We want MWK/USD (which is the same - how many MWK per 1 USD)
            # So rate_mwk is already what we want
            
            # Check if date exists
            existing = db.query(ExchangeRate).filter(
                ExchangeRate.date == date_obj
            ).first()
            
            if existing:
                # Update if current rate looks synthetic (flat)
                if existing.is_interpolated or existing.source == 'csv':
                    existing.rate = float(rate_mwk)
                    existing.source = 'frankfurter_api'
                    existing.is_interpolated = False
                    updated += 1
            else:
                # Insert new row
                new_rate = ExchangeRate(
                    date=date_obj,
                    rate=float(rate_mwk),
                    source='frankfurter_api',
                    is_interpolated=False
                )
                db.add(new_rate)
                inserted += 1
        
        db.commit()
        
        logger.info(f"✅ Inserted {inserted} new rows")
        logger.info(f"✅ Updated {updated} existing rows")
        
        # Show summary of what we got
        if inserted > 0 or updated > 0:
            latest_rates = db.query(ExchangeRate).filter(
                ExchangeRate.date >= start_date
            ).order_by(ExchangeRate.date.desc()).limit(10).all()
            
            print("\n=== Latest 10 Rates After Update ===")
            for r in latest_rates:
                print(f"{r.date}: {r.rate:.4f} (source: {r.source})")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    fetch_frankfurter_data()
