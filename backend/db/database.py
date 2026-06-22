"""Database configuration - PRODUCTION READY."""

import os
import sys

# SET DATABASE PATH BEFORE ANYTHING ELSE
# On Render/Docker, always use /tmp which is guaranteed writable
if os.getenv('RENDER') or os.getenv('ENVIRONMENT') == 'production':
    DB_PATH = '/tmp/data/mwk_forecasting.db'
    os.makedirs('/tmp/data', exist_ok=True)
else:
    DB_PATH = os.getenv('DATABASE_URL', 'sqlite:///./data/mwk_forecasting.db')
    if DB_PATH.startswith('sqlite:///'):
        db_file = DB_PATH.replace('sqlite:///', '')
        db_dir = os.path.dirname(db_file)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

DATABASE_URL = f'sqlite:///{DB_PATH}' if not DB_PATH.startswith('sqlite:///') else DB_PATH
print(f"🗄️  Database: {DATABASE_URL}")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Create all tables."""
    import db.models
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created")
