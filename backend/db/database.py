from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import QueuePool, NullPool
from core.config import get_settings

settings = get_settings()

connect_args = {}
pool_args = {}

if "sqlite" in settings.database_url:
    # SQLite configuration for concurrent access
    connect_args["check_same_thread"] = False
    connect_args["timeout"] = 30  # Wait up to 30s for database lock
    
    # Use QueuePool even for SQLite to handle concurrent requests
    pool_args["poolclass"] = QueuePool
    pool_args["pool_size"] = 10  # Allow up to 10 concurrent connections
    pool_args["max_overflow"] = 5  # Allow 5 extra connections under load
    pool_args["pool_timeout"] = 30  # Wait 30s for available connection
    pool_args["pool_recycle"] = 1800  # Recycle connections after 30 minutes
    pool_args["pool_pre_ping"] = True  # Verify connections before using
else:
    # For PostgreSQL/MySQL, use connection pooling
    pool_args["poolclass"] = QueuePool
    pool_args["pool_size"] = 10
    pool_args["max_overflow"] = 10
    pool_args["pool_timeout"] = 30
    pool_args["pool_recycle"] = 3600
    pool_args["pool_pre_ping"] = True

# Create engine with proper pooling configuration
engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    echo=settings.debug,
    **pool_args
)

# Enable WAL mode for SQLite to improve concurrent read/write performance
if "sqlite" in settings.database_url:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        """Enable WAL mode and set busy timeout for SQLite"""
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA cache_size=-20000")  # 20MB cache
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

# Connection pool event listeners for debugging
@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_connection, connection_record, connection_proxy):
    """Log when connection is checked out from pool"""
    if settings.debug:
        print(f"Connection checked out: {id(dbapi_connection)}")

@event.listens_for(engine, "checkin")
def receive_checkin(dbapi_connection, connection_record):
    """Log when connection is returned to pool"""
    if settings.debug:
        print(f"Connection checked in: {id(dbapi_connection)}")

@event.listens_for(engine, "connect")
def receive_connect(dbapi_connection, connection_record):
    """Log when new connection is created"""
    if settings.debug:
        print(f"New connection created: {id(dbapi_connection)}")

# Create session factory with optimized settings
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,  # Prevent expired object access
)


class Base(DeclarativeBase):
    pass


def get_db():
    """
    FastAPI dependency that provides a database session.
    Ensures proper cleanup even if exceptions occur.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def create_all_tables():
    """Create all database tables defined in models"""
    from db import models  # noqa: F401
    Base.metadata.create_all(bind=engine)


def get_pool_status():
    """Get current connection pool status for monitoring"""
    pool = engine.pool
    return {
        "size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "total": pool.size() + pool.overflow(),
    }