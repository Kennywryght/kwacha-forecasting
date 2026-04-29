import pandas as pd
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from db.database import SessionLocal
from db.models import ExchangeRate
from core.logging_config import get_logger

logger = get_logger(__name__)

def seed_exchange_rates():
    db = SessionLocal()
    try:
        # Path to the dataset
        # Try Raw first, then Processed as fallback
        path = os.path.join("data", "raw", "mwk_usd_final_dataset.csv")
        if not os.path.exists(path):
            path = os.path.join("data", "processed", "mwk_usd_clean.csv")

        if not os.path.exists(path):
            logger.error("❌ CRITICAL: CSV file not found in 'data/raw' or 'data/processed'. Cannot seed DB.")
            return

        logger.info(f"📂 Loading Exchange Rates from: {path}")
        
        # Read CSV
        df = pd.read_csv(path)
        
        # Normalize column names just in case
        # Expected columns: Date, MWK_USD (or date, rate)
        df.columns = [c.lower().replace(" ", "_") for c in df.columns]
        
        if 'date' not in df.columns or 'mwk_usd' not in df.columns:
            # Try mapping common variations
            if 'rate' in df.columns:
                df.rename(columns={'rate': 'mwk_usd'}, inplace=True)
            else:
                logger.error("❌ CSV missing required columns (Date, MWK_USD or rate)")
                return

        # Convert types
        df['date'] = pd.to_datetime(df['date'])
        
        count = 0
        logger.info("💾 Inserting historical data into DB...")
        
        for _, row in df.iterrows():
            # Check if date already exists
            existing = db.query(ExchangeRate).filter(ExchangeRate.date == row['date'].date()).first()
            
            if not existing:
                rate = ExchangeRate(
                    date=row['date'].date(),
                    rate=float(row['mwk_usd']),
                    source='historical_csv'
                )
                db.add(rate)
                count += 1
            
        db.commit()
        logger.info(f"✅ Successfully seeded {count} historical exchange rates to DB.")
        
    except Exception as e:
        logger.error(f"💥 Seeder failed: {e}")
        db.rollback()
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    seed_exchange_rates()