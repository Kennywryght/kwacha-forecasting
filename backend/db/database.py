import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Set database path
if os.getenv('RENDER') or os.getenv('ENVIRONMENT') == 'production':
    DB_PATH = '/tmp/data/mwk_forecasting.db'
    os.makedirs('/tmp/data', exist_ok=True)
else:
    DB_PATH = 'data/mwk_forecasting.db'

DATABASE_URL = f'sqlite:///{DB_PATH}'
print(f'Database: {DATABASE_URL}')

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    import db.models
    Base.metadata.create_all(bind=engine)
    print('Tables created')
    
    # Auto-seed from CSV if empty
    from sqlalchemy import func
    db = SessionLocal()
    try:
        count = db.query(func.count(db.models.ExchangeRate.id)).scalar()
        if count == 0:
            print('Seeding data from CSV...')
            import pandas as pd
            
            paths = [
                'data/raw/mwk_usd_final_dataset.csv',
                'data/processed/mwk_usd_clean.csv',
            ]
            
            for path in paths:
                if os.path.exists(path):
                    print(f'Found: {path}')
                    df = pd.read_csv(path)
                    date_col = next((c for c in df.columns if c.lower() == 'date'), None)
                    rate_col = next((c for c in df.columns if c.lower() in ['rate', 'mwk_usd', 'close']), None)
                    
                    if date_col and rate_col:
                        df[date_col] = pd.to_datetime(df[date_col])
                        for _, row in df.iterrows():
                            try:
                                db.add(db.models.ExchangeRate(
                                    date=row[date_col].date(),
                                    rate=float(row[rate_col]),
                                    source='seed'
                                ))
                            except:
                                pass
                        db.commit()
                        print(f'Seeded {len(df)} rows')
                        break
            else:
                print('No CSV found - DB empty')
        else:
            print(f'DB has {count} rows')
    finally:
        db.close()
