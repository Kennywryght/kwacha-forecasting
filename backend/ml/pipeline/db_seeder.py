import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime
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

def save_to_db(db, df: pd.DataFrame):
    """
    Master pipeline DB writer.
    - Inserts ONLY new records (no duplicates)
    - Safe for automation (daily runs)
    """

    create_all_tables()

    inserted = 0
    skipped = 0

    try:
        for _, row in df.iterrows():
            date_val = pd.to_datetime(row["date"]).date()

            # Check if already exists
            existing = db.query(ExchangeRate).filter(
                ExchangeRate.date == date_val
            ).first()

            if existing:
                # Replacing synthetic or old data with real data
                existing.rate = float(row["rate"])
                existing.open_rate = float(row["open_rate"]) if "open_rate" in df.columns and pd.notna(row.get("open_rate")) else existing.open_rate
                existing.high_rate = float(row["high_rate"]) if "high_rate" in df.columns and pd.notna(row.get("high_rate")) else existing.high_rate
                existing.low_rate = float(row["low_rate"]) if "low_rate" in df.columns and pd.notna(row.get("low_rate")) else existing.low_rate
                existing.daily_return = float(row["daily_return"]) if pd.notna(row.get("daily_return")) else existing.daily_return
                existing.source = "live_pipeline"
                existing.updated_at = datetime.utcnow()

                db.add(existing)
                skipped += 1
                continue

            record = ExchangeRate(
                date=date_val,
                rate=float(row["rate"]),
                open_rate=float(row["open_rate"]) if "open_rate" in df.columns and pd.notna(row.get("open_rate")) else None,
                high_rate=float(row["high_rate"]) if "high_rate" in df.columns and pd.notna(row.get("high_rate")) else None,
                low_rate=float(row["low_rate"]) if "low_rate" in df.columns and pd.notna(row.get("low_rate")) else None,
                daily_return=float(row["daily_return"]) if pd.notna(row.get("daily_return")) else None,
                is_interpolated=bool(row.get("is_interpolated", False)),
                source="live_pipeline",
            )

            db.add(record)
            inserted += 1

        db.commit()

        logger.info(f"DB Update → Inserted: {inserted}, Skipped: {skipped}")

    except Exception as e:
        db.rollback()
        logger.error(f"save_to_db failed: {e}")
        raise