import os, sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

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
    from db.models import ExchangeRate, MacroIndicator, Forecast, ModelRun, DataFetchLog
    Base.metadata.create_all(bind=engine)
    print('Tables created')
    
    # Auto-seed if empty
    from sqlalchemy import func
    import pandas as pd
    db = SessionLocal()
    try:
        count = db.query(func.count(ExchangeRate.id)).scalar()
        if count == 0:
            print('Seeding...')
            for p in ['data/raw/mwk_usd_final_dataset.csv', '../data/raw/mwk_usd_final_dataset.csv']:
                if os.path.exists(p):
                    df = pd.read_csv(p)
                    dc = [c for c in df.columns if c.lower()=='date'][0]
                    rc = [c for c in df.columns if c.lower() in ['rate','mwk_usd']][0]
                    df[dc] = pd.to_datetime(df[dc])
                    for _, row in df.iterrows():
                        try:
                            db.add(ExchangeRate(date=row[dc].date(), rate=float(row[rc]), source='seed'))
                        except: pass
                    db.commit()
                    print(f'Seeded {len(df)} rows')
                    break
        else:
            print(f'DB has {count} rows')
    finally:
        db.close()
