"""
Fetch MWK/USD data from Nov 2024 to present to fill the gap.
"""

import sys
import os
sys.path.insert(0, 'backend')

import yfinance as yf
import pandas as pd
from datetime import datetime
from db.database import SessionLocal
from db.models import ExchangeRate
from sqlalchemy import func
from core.logging_config import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)

def fill_data_gap():
    """Fetch real data from Nov 2024 to present."""
    
    db = SessionLocal()
    
    try:
        # Check what we have
        latest = db.query(func.max(ExchangeRate.date)).scalar()
        logger.info(f"Latest date in DB: {latest}")
        
        if latest and latest >= datetime.now().date():
            logger.info("Database is already up to date!")
            return
        
        # Fetch from Yahoo Finance
        start_date = '2024-11-19' if not latest else latest.strftime('%Y-%m-%d')
        logger.info(f"Fetching MWK/USD from {start_date} to present...")
        
        try:
            # MWK/USD via Yahoo Finance
            ticker = yf.Ticker("MWKUSD=X")
            df = ticker.history(start=start_date)
            
            if not df.empty:
                df = df.reset_index()
                df['date'] = pd.to_datetime(df['Date']).dt.date
                
                inserted = 0
                for _, row in df.iterrows():
                    # Check if date already exists
                    existing = db.query(ExchangeRate).filter(
                        ExchangeRate.date == row['date']
                    ).first()
                    
                    if not existing:
                        new_rate = ExchangeRate(
                            date=row['date'],
                            rate=float(row['Close']),
                            open_rate=float(row['Open']),
                            high_rate=float(row['High']),
                            low_rate=float(row['Low']),
                            source='yahoo_finance',
                            is_interpolated=False
                        )
                        db.add(new_rate)
                        inserted += 1
                
                db.commit()
                logger.info(f"✅ Inserted {inserted} new rows from Yahoo Finance")
            else:
                logger.warning("Yahoo Finance returned no data")
                
        except Exception as e:
            logger.warning(f"Yahoo Finance failed: {e}")
            logger.info("Trying Frankfurter API fallback...")
            
            # Fallback: Frankfurter API
            import requests
            
            url = f"https://api.frankfurter.app/{start_date}..{datetime.now().strftime('%Y-%m-%d')}?from=USD&to=MWK"
            response = requests.get(url)
            data = response.json()
            
            if 'rates' in data:
                inserted = 0
                for date_str, rates in data['rates'].items():
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                    rate_mwk = rates.get('MWK')
                    
                    if rate_mwk:
                        existing = db.query(ExchangeRate).filter(
                            ExchangeRate.date == date_obj
                        ).first()
                        
                        if not existing:
                            # Convert: if USD→MWK=1100, then 1 MWK = 1/1100 USD
                            # We want MWK/USD (how many MWK per 1 USD)
                            new_rate = ExchangeRate(
                                date=date_obj,
                                rate=float(rate_mwk),
                                source='frankfurter_api',
                                is_interpolated=False
                            )
                            db.add(new_rate)
                            inserted += 1
                
                db.commit()
                logger.info(f"✅ Inserted {inserted} new rows from Frankfurter API")
            else:
                logger.error("All data sources failed!")
                
    except Exception as e:
        db.rollback()
        logger.error(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    fill_data_gap()
