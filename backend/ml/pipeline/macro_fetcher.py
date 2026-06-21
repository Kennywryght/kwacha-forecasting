"""Macroeconomic data fetcher for MWK/USD forecasting.

This module fetches macroeconomic indicators from various sources:
- US Federal Reserve data via FRED
- World Bank data for Malawi
- Local fallback data
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import sys
import os
from typing import Optional, Dict, Any
from functools import wraps

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from core.logging_config import get_logger
from db.database import SessionLocal
from db.models import MacroIndicator

# Try importing pandas_datareader
try:
    import pandas_datareader.data as web
    import pandas_datareader.wb as wb
    PANDAS_DATA_AVAILABLE = True
except ImportError:
    PANDAS_DATA_AVAILABLE = False
    logger = get_logger(__name__)
    logger.warning("pandas_datareader not available, macro fetching will be limited")

logger = get_logger(__name__)


def retry(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Decorator for retrying failed API calls."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            current_delay = delay
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries >= max_retries:
                        logger.error(f"Failed after {max_retries} retries: {e}")
                        raise
                    logger.warning(f"Retry {retries}/{max_retries}: {e}")
                    time.sleep(current_delay)
                    current_delay *= backoff
            return None
        return wrapper
    return decorator


@retry(max_retries=3)
def fetch_us_macro_data(start_date: str) -> pd.DataFrame:
    """
    Fetch US macroeconomic data from FRED.

    Args:
        start_date: Start date for data fetch (YYYY-MM-DD)

    Returns:
        DataFrame with US macro indicators
    """
    if not PANDAS_DATA_AVAILABLE:
        logger.warning("pandas_datareader not available, returning empty DataFrame")
        return pd.DataFrame()

    try:
        logger.info(f"Fetching US macro data from {start_date}...")

        # Fetch Federal Funds Rate
        us_fed = web.DataReader('FEDFUNDS', 'fred', start=start_date)
        us_fed.rename(columns={'FEDFUNDS': 'us_fed_rate'}, inplace=True)

        # Fetch CPI
        us_cpi = web.DataReader('CPIAUCSL', 'fred', start=start_date)
        us_cpi.rename(columns={'CPIAUCSL': 'us_cpi'}, inplace=True)

        # Merge data
        df = pd.merge(us_fed, us_cpi, left_index=True, right_index=True, how='outer')
        df.index.name = 'date'
        df.reset_index(inplace=True)

        logger.info(f"✅ Retrieved {len(df)} rows of US macro data")
        return df

    except Exception as e:
        logger.error(f"US macro fetch failed: {e}")
        return pd.DataFrame()


@retry(max_retries=2)
def fetch_malawi_macro_data(start_year: int = 2020) -> pd.DataFrame:
    """
    Fetch Malawi macroeconomic data from World Bank.

    Args:
        start_year: Starting year for data fetch

    Returns:
        DataFrame with Malawi macro indicators
    """
    if not PANDAS_DATA_AVAILABLE:
        logger.warning("pandas_datareader not available, returning empty DataFrame")
        return pd.DataFrame()

    try:
        logger.info(f"Fetching Malawi macro data from {start_year}...")

        indicators = {
            'FP.CPI.TOTL.ZG': 'inflation',           # Inflation, consumer prices (annual %)
            'NY.GDP.MKTP.KD.ZG': 'gdp_growth',       # GDP growth (annual %)
            'FM.LBL.BMNY.ZG': 'money_supply_growth', # Broad money growth (annual %)
        }

        df = wb.download(
            indicator=indicators.keys(),
            country='MWI',
            start=start_year,
            end=datetime.now().year + 1
        )

        if df.empty:
            logger.warning("No Malawi data returned from World Bank")
            return pd.DataFrame()

        df.reset_index(inplace=True)
        df.rename(columns={
            'year': 'date',
            'FP.CPI.TOTL.ZG': 'inflation',
            'NY.GDP.MKTP.KD.ZG': 'gdp_growth',
            'FM.LBL.BMNY.ZG': 'money_supply_growth'
        }, inplace=True)

        df['date'] = pd.to_datetime(df['date'], format='%Y')

        logger.info(f"✅ Retrieved {len(df)} rows of Malawi macro data")
        return df[['date', 'inflation', 'gdp_growth', 'money_supply_growth']]

    except Exception as e:
        logger.error(f"Malawi macro fetch failed: {e}")
        return pd.DataFrame()


def merge_and_process_macro(
    start_date: str,
    save_to_db_flag: bool = True
) -> Optional[pd.DataFrame]:
    """
    Fetch, merge, and process macroeconomic data.

    Args:
        start_date: Start date for US data
        save_to_db_flag: Whether to save results to database

    Returns:
        Processed DataFrame or None if failed
    """
    logger.info("🚀 Macro pipeline started")

    # Fetch data
    us_df = fetch_us_macro_data(start_date)
    mw_df = fetch_malawi_macro_data()

    if us_df.empty and mw_df.empty:
        logger.warning("No macro data available")
        return None

    # Process Malawi data to daily frequency
    if not mw_df.empty:
        mw_df.set_index('date', inplace=True)
        mw_daily = mw_df.resample('D').ffill().reset_index()
        logger.info(f"Resampled Malawi data to daily: {mw_daily.shape}")
    else:
        mw_daily = pd.DataFrame()

    # Merge datasets
    if not us_df.empty and not mw_daily.empty:
        df = pd.merge(us_df, mw_daily, on='date', how='outer')
    elif not us_df.empty:
        df = us_df
    else:
        df = mw_daily

    if df.empty:
        logger.warning("Empty merged DataFrame")
        return None

    # Feature engineering
    if 'us_cpi' in df.columns:
        # Year-over-year CPI change
        df['us_cpi_yoy'] = df['us_cpi'].pct_change(252) * 100

    if 'inflation' in df.columns and 'us_cpi_yoy' in df.columns:
        df['inflation_diff'] = df['inflation'] - df['us_cpi_yoy']

    if 'us_fed_rate' in df.columns:
        if 'Lending_Interest_Rate' in df.columns:
            df['interest_rate_diff'] = df['Lending_Interest_Rate'] - df['us_fed_rate']

        # Create real interest rate if possible
        if 'inflation' in df.columns:
            df['real_fed_rate'] = df['us_fed_rate'] - df['inflation']

    # Fill missing values
    df.ffill(inplace=True)
    df.bfill(inplace=True)

    # Save to database
    if save_to_db_flag:
        db = SessionLocal()
        try:
            objects = []
            for _, row in df.iterrows():
                if pd.isna(row['date']):
                    continue

                objects.append(MacroIndicator(
                    date=row['date'].date(),
                    inflation=row.get('inflation'),
                    gdp_growth=row.get('gdp_growth'),
                    money_supply_growth=row.get('money_supply_growth'),
                    us_cpi=row.get('us_cpi'),
                    us_cpi_yoy=row.get('us_cpi_yoy'),
                    us_fed_rate=row.get('us_fed_rate'),
                    inflation_diff=row.get('inflation_diff'),
                    interest_rate_diff=row.get('interest_rate_diff'),
                    real_fed_rate=row.get('real_fed_rate'),
                    source='macro_pipeline'
                ))

            db.bulk_save_objects(objects)
            db.commit()
            logger.info(f"✅ Saved {len(objects)} macro rows to database")

        except Exception as e:
            db.rollback()
            logger.error(f"DB save failed: {e}")
        finally:
            db.close()

    logger.info(f"✅ Macro pipeline complete: {df.shape}")
    return df


def get_macro_data_interval(
    start_date: str,
    end_date: str
) -> pd.DataFrame:
    """
    Get macro data for a specific date interval.

    Args:
        start_date: Start date
        end_date: End date

    Returns:
        DataFrame with macro data
    """
    db = SessionLocal()
    try:
        query = db.query(MacroIndicator).filter(
            MacroIndicator.date >= pd.to_datetime(start_date).date(),
            MacroIndicator.date <= pd.to_datetime(end_date).date()
        )

        results = query.all()

        if not results:
            return pd.DataFrame()

        df = pd.DataFrame([{
            'date': r.date,
            'inflation': r.inflation,
            'gdp_growth': r.gdp_growth,
            'money_supply_growth': r.money_supply_growth,
            'us_cpi': r.us_cpi,
            'us_cpi_yoy': r.us_cpi_yoy,
            'us_fed_rate': r.us_fed_rate,
            'inflation_diff': r.inflation_diff,
            'interest_rate_diff': r.interest_rate_diff,
            'real_fed_rate': r.real_fed_rate
        } for r in results])

        df['date'] = pd.to_datetime(df['date'])
        df.sort_values('date', inplace=True)
        df.reset_index(drop=True, inplace=True)

        return df

    finally:
        db.close()