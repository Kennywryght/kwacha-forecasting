"""Database configuration and session management."""

import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from core.config import get_settings

settings = get_settings()

# Fix for Render: Ensure data directory exists
def get_database_url():
    """Get database URL with proper path handling for deployment."""
    db_url = settings.database_url
    
    if db_url.startswith('sqlite:///'):
        # Extract path from SQLite URL
        db_path = db_url.replace('sqlite:///', '')
        
        # Handle relative paths
        if not os.path.isabs(db_path):
            # Try multiple possible base directories
            possible_bases = [
                os.getcwd(),  # Current working directory
                os.path.dirname(os.path.abspath(__file__)),  # This file's directory
                '/opt/render/project/src/backend',  # Render default
                '/app',  # Docker default
            ]
            
            for base in possible_bases:
                full_path = os.path.join(base, db_path)
                db_dir = os.path.dirname(full_path)
                if os.path.exists(base):
                    os.makedirs(db_dir, exist_ok=True)
                    db_url = f'sqlite:///{full_path}'
                    break
            else:
                # Fallback: use /tmp which is always writable on Render
                db_dir = '/tmp/data'
                os.makedirs(db_dir, exist_ok=True)
                db_url = f'sqlite:////tmp/data/mwk_forecasting.db'
        else:
            # Absolute path - ensure directory exists
            db_dir = os.path.dirname(db_path)
            os.makedirs(db_dir, exist_ok=True)
    
    return db_url

DATABASE_URL = get_database_url()

# Create engine with proper SQLite settings
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    pool_pre_ping=True,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """Dependency for FastAPI to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_all_tables():
    """Create all database tables."""
    from db.models import ExchangeRate, MacroIndicator, Forecast, ModelRun, DataFetchLog  # noqa
    Base.metadata.create_all(bind=engine)
    print(f"✅ Database tables created at: {DATABASE_URL}")

def init_db():
    """Initialize database with tables."""
    create_all_tables()
