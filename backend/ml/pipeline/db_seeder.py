import pandas as pd
import numpy as np
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from db.database import SessionLocal, create_all_tables
from db.models import ExchangeRate, MacroIndicator
from core.logging_config import get_logger

logger = get_logger(__name__)


def seed_exchange_rates(df: pd.DataFrame):
    create_all_tables()
    db = SessionLocal()
    try:
        # Clear existing data
        db.query(ExchangeRate).delete()
        db.commit()

        records = []
        for _, row in df.iterrows():
            records.append(ExchangeRate(
                date            = row["date"].date(),
                rate            = float(row["rate"]),
                daily_return    = float(row["daily_return"]) if pd.notna(row.get("daily_return")) else None,
                is_interpolated = bool(row.get("is_interpolated", False)),
                source          = "csv_import",
            ))

        db.bulk_save_objects(records)
        db.commit()
        logger.info(f"exchange_rates → {len(records)} rows inserted")

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to seed exchange_rates: {e}")
        raise
    finally:
        db.close()


def seed_macro_indicators(df: pd.DataFrame):
    db = SessionLocal()
    try:
        db.query(MacroIndicator).delete()
        db.commit()

        macro_cols = [
            "Inflation", "Money_Supply", "Foreign_Reserves",
            "Current_Account_Balance", "Lending_Interest_Rate",
            "Real_Interest_Rate", "GDP_Growth", "us_cpi",
            "us_cpi_yoy", "us_fed_rate", "inflation_diff", "interest_rate_diff"
        ]

        # One record per month (resample to monthly)
        df_monthly = df.copy()
        df_monthly.set_index("date", inplace=True)
        df_monthly = df_monthly.resample("MS")[macro_cols].first().reset_index()

        records = []
        for _, row in df_monthly.iterrows():
            records.append(MacroIndicator(
                date                    = row["date"].date(),
                inflation               = _safe(row, "Inflation"),
                money_supply_m2         = _safe(row, "Money_Supply"),
                foreign_reserves        = _safe(row, "Foreign_Reserves"),
                current_account_balance = _safe(row, "Current_Account_Balance"),
                lending_interest_rate   = _safe(row, "Lending_Interest_Rate"),
                real_interest_rate      = _safe(row, "Real_Interest_Rate"),
                gdp_growth              = _safe(row, "GDP_Growth"),
                us_cpi                  = _safe(row, "us_cpi"),
                us_cpi_yoy              = _safe(row, "us_cpi_yoy"),
                us_fed_rate             = _safe(row, "us_fed_rate"),
                inflation_diff          = _safe(row, "inflation_diff"),
                interest_rate_diff      = _safe(row, "interest_rate_diff"),
                source                  = "csv_import",
            ))

        db.bulk_save_objects(records)
        db.commit()
        logger.info(f"macro_indicators → {len(records)} rows inserted")

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to seed macro_indicators: {e}")
        raise
    finally:
        db.close()


def _safe(row, col):
    val = row.get(col)
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None
    return float(val)