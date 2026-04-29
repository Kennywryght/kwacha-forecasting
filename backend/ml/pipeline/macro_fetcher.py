import pandas as pd
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from core.logging_config import get_logger
from db.database import SessionLocal
from db.models import MacroIndicator

try:
    import pandas_datareader.data as web
    import pandas_datareader.wb as wb
    PANDAS_DATA_AVAILABLE = True
except ImportError:
    PANDAS_DATA_AVAILABLE = False

logger = get_logger(__name__)


def fetch_us_macro_data(start_date: str) -> pd.DataFrame:
    if not PANDAS_DATA_AVAILABLE:
        return pd.DataFrame()

    try:
        us_fed = web.DataReader('FEDFUNDS', 'fred', start=start_date)
        us_cpi = web.DataReader('CPIAUCSL', 'fred', start=start_date)

        us_fed.rename(columns={'FEDFUNDS': 'us_fed_rate'}, inplace=True)
        us_cpi.rename(columns={'CPIAUCSL': 'us_cpi'}, inplace=True)

        df = pd.merge(us_fed, us_cpi, left_index=True, right_index=True, how='outer')
        df.index.name = 'date'
        df.reset_index(inplace=True)

        return df

    except Exception as e:
        logger.warning(f"US macro fetch failed: {e}")
        return pd.DataFrame()


def fetch_malawi_macro_data() -> pd.DataFrame:
    if not PANDAS_DATA_AVAILABLE:
        return pd.DataFrame()

    try:
        indicators = {
            'FP.CPI.TOTL.ZG': 'inflation',
            'NY.GDP.MKTP.KD.ZG': 'gdp_growth'
        }

        df = wb.download(indicator=indicators.keys(), country='MWI', start=2020, end=2026)

        if df.empty:
            return pd.DataFrame()

        df.reset_index(inplace=True)
        df.rename(columns={
            'year': 'date',
            'FP.CPI.TOTL.ZG': 'inflation',
            'NY.GDP.MKTP.KD.ZG': 'gdp_growth'
        }, inplace=True)

        df['date'] = pd.to_datetime(df['date'], format='%Y')

        return df[['date', 'inflation', 'gdp_growth']]

    except Exception as e:
        logger.warning(f"Malawi macro fetch failed: {e}")
        return pd.DataFrame()


def merge_and_process_macro(start_date: str):
    logger.info("🚀 Macro pipeline started")

    us_df = fetch_us_macro_data(start_date)
    mw_df = fetch_malawi_macro_data()

    if us_df.empty and mw_df.empty:
        logger.warning("No macro data available")
        return

    # Convert Malawi annual → daily
    if not mw_df.empty:
        mw_df.set_index('date', inplace=True)
        mw_daily = mw_df.resample('D').ffill().reset_index()
    else:
        mw_daily = pd.DataFrame()

    # Merge
    if not us_df.empty and not mw_daily.empty:
        df = pd.merge(us_df, mw_daily, on='date', how='outer')
    elif not us_df.empty:
        df = us_df
    else:
        df = mw_daily

    if df.empty:
        return

    # Feature engineering
    df['us_cpi_yoy'] = df['us_cpi'].pct_change(252) * 100 if 'us_cpi' in df else None
    df['inflation_diff'] = df['inflation'] - df['us_cpi_yoy'] if 'inflation' in df else None
    df['interest_rate_diff'] = 0.0

    df.ffill(inplace=True)
    df.bfill(inplace=True)

    # Save
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
                us_cpi=row.get('us_cpi'),
                us_cpi_yoy=row.get('us_cpi_yoy'),
                us_fed_rate=row.get('us_fed_rate'),
                inflation_diff=row.get('inflation_diff'),
                interest_rate_diff=row.get('interest_rate_diff'),
                source='macro_pipeline'
            ))

        db.bulk_save_objects(objects)
        db.commit()

        logger.info(f" Saved {len(objects)} macro rows")

    except Exception as e:
        db.rollback()
        logger.error(f"DB save failed: {e}")
    finally:
        db.close()