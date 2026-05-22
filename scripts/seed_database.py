import os
import sys
import pandas as pd
from datetime import datetime

# Adjust module discovery pointer
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))

from db.database import SessionLocal, engine, Base
from db.models import ExchangeRate, MacroIndicator

def sync_local_database():
    print("🔄 Initializing Local Data Synchronization...")
    
    # Target path containing clean engineered output from Colab
    csv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/processed/mwk_usd_clean.csv"))
    
    if not os.path.exists(csv_path):
        print(f"❌ Error: Processed data file not found at {csv_path}.")
        print("Please download your 'mwk_usd_clean.csv' file from Colab and place it in your 'data/processed/' directory.")
        return

    # Drop and recreate tables to ensure an entirely clean state
    print("⏳ Clearing previous database state for clean sync...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        print("📖 Reading exported dataset...")
        df = pd.read_csv(csv_path)
        
        # Ensure date index parsing matches correctly
        if 'date' not in df.columns and 'Date' in df.columns:
            df.rename(columns={'Date': 'date'}, inplace=True)
        if 'date' not in df.columns:
            # Fallback if date is the dataframe index
            df.reset_index(inplace=True)
            df.rename(columns={'index': 'date', 'level_0': 'date'}, inplace=True, errors='ignore')

        df['date'] = pd.to_datetime(df['date']).dt.date

        exchange_rate_objects = []
        macro_indicator_objects = []

        print(f"📊 Processing {len(df)} historical data frames...")
        for _, row in df.iterrows():
            # Build Exchange Rate Entity
            rate_entry = ExchangeRate(
                date=row['date'],
                rate=float(row.get('rate', row.get('Rate', 0))),
                open_rate=float(row['open_rate']) if pd.notna(row.get('open_rate')) else None,
                high_rate=float(row['high_rate']) if pd.notna(row.get('high_rate')) else None,
                low_rate=float(row['low_rate']) if pd.notna(row.get('low_rate')) else None,
                daily_return=float(row['daily_return']) if pd.notna(row.get('daily_return')) else None,
                is_interpolated=bool(row.get('is_interpolated', False)),
                source="colab_sync"
            )
            exchange_rate_objects.append(rate_entry)

            # Build Macro Indicator Entity (If any macro features were engineered in Colab)
            if any(col in df.columns for col in ['inflation', 'us_cpi', 'gdp_growth']):
                macro_entry = MacroIndicator(
                    date=row['date'],
                    inflation=float(row['inflation']) if pd.notna(row.get('inflation')) else None,
                    money_supply_m2=float(row['money_supply_m2']) if pd.notna(row.get('money_supply_m2')) else None,
                    foreign_reserves=float(row['foreign_reserves']) if pd.notna(row.get('foreign_reserves')) else None,
                    gdp_growth=float(row['gdp_growth']) if pd.notna(row.get('gdp_growth')) else None,
                    us_cpi=float(row['us_cpi']) if pd.notna(row.get('us_cpi')) else None,
                    source="colab_sync"
                )
                macro_indicator_objects.append(macro_entry)

        # Bulk save records for optimal load speed
        print("📥 Inserting records into local SQLite/Postgres database pools...")
        db.bulk_save_objects(exchange_rate_objects)
        if macro_indicator_objects:
            db.bulk_save_objects(macro_indicator_objects)
        
        db.commit()
        print(f"🚀 Success! Synced {len(exchange_rate_objects)} exchange rate timelines into the database cleanly.")

    except Exception as e:
        db.rollback()
        print(f"❌ Synchronization script failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    sync_local_database()