import os, sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Use backend/data/ for persistence (survives Render restarts)
DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, 'mwk_forecasting.db')

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