"""
Run this script once to add performance indexes to the forecasts table.
Usage: python -m db.add_indexes
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import create_engine, text
from core.config import get_settings
from core.logging_config import get_logger

logger = get_logger(__name__)

def add_indexes():
    settings = get_settings()
    engine = create_engine(settings.database_url)
    
    indexes = [
        # Composite index for forecast lookups (most common query pattern)
        """
        CREATE INDEX IF NOT EXISTS idx_forecast_lookup 
        ON forecasts (model_name, horizon_days, forecast_date)
        """,
        
        # Index for target date queries
        """
        CREATE INDEX IF NOT EXISTS idx_forecast_target 
        ON forecasts (model_name, target_date)
        """,
        
        # Index for date range queries
        """
        CREATE INDEX IF NOT EXISTS idx_forecast_date_range 
        ON forecasts (forecast_date, model_name, horizon_days)
        """,
        
        # Index for model runs
        """
        CREATE INDEX IF NOT EXISTS idx_model_runs_active 
        ON model_runs (is_active)
        """,
        
        # Index for exchange rates date queries
        """
        CREATE INDEX IF NOT EXISTS idx_exchange_rates_date 
        ON exchange_rates (date)
        """,
    ]
    
    try:
        with engine.connect() as conn:
            for index_sql in indexes:
                logger.info(f"Creating index: {index_sql[:50]}...")
                conn.execute(text(index_sql))
                conn.commit()
        
        logger.info("✅ All indexes created successfully")
        
        # Verify indexes were created
        with engine.connect() as conn:
            if "sqlite" in settings.database_url:
                result = conn.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='index'"
                ))
            else:
                result = conn.execute(text(
                    "SELECT indexname FROM pg_indexes WHERE tablename = 'forecasts'"
                ))
            
            indexes_list = [row[0] for row in result]
            logger.info(f"Existing indexes: {indexes_list}")
            
    except Exception as e:
        logger.error(f"Failed to create indexes: {e}")
        raise
    finally:
        engine.dispose()

if __name__ == "__main__":
    add_indexes()