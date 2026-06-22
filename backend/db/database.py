"""Database configuration and session management."""

import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Try to import settings, fallback to env vars
try:
    from core.config import get_settings
    settings = get_settings()
    DATABASE_URL = settings.database_url
except Exception:
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./data/mwk_forecasting.db')

# Ensure writable directory for SQLite
if DATABASE_URL.startswith('sqlite:///'):
    db_path = DATABASE_URL.replace('sqlite:///', '')
    
    # Use /tmp in production (always writable)
    if os.getenv('ENVIRONMENT') == 'production' or os.getenv('RENDER'):
        DATABASE_URL = 'sqlite:////tmp/data/mwk_forecasting.db'
        os.makedirs('/tmp/data', exist_ok=True)
    else:
        # Local development
        if not os.path.isabs(db_path):
            db_path = os.path.join(os.getcwd(), db_path)
        db_dir = os.path.dirname(db_path)
        os.makedirs(db_dir, exist_ok=True)
        DATABASE_URL = f'sqlite:///{db_path}'

print(f"🗄️  Database URL: {DATABASE_URL}")

# Create engine
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
    # Import models here to avoid circular imports
    import db.models  # noqa
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created")

def init_db():
    """Initialize database with tables."""
    create_all_tables()
