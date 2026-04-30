import pandas as pd
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from core.config import get_settings
from core.logging_config import get_logger
from db.database import SessionLocal
from db.models import ExchangeRate, MacroIndicator

logger = get_logger(__name__)
settings = get_settings()


def load_processed_csv() -> pd.DataFrame:
    """
    Load already cleaned + feature-engineered dataset
    """
    path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "../../../../data/processed/mwk_usd_clean.csv"
        )
    )

    logger.info(f"📂 Loading PROCESSED CSV: {path}")

    if not os.path.exists(path):
        logger.warning("⚠️ Processed CSV not found, falling back to raw dataset...")

        raw_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "../../../../data/raw/mwk_usd_final_dataset.csv"
            )
        )

        if not os.path.exists(raw_path):
            raise FileNotFoundError("❌ No dataset found (processed or raw)")

        df = pd.read_csv(raw_path, parse_dates=["Date"])
        df.rename(columns={"Date": "date", "MWK_USD": "rate"}, inplace=True)

        df["date"] = pd.to_datetime(df["date"])
        df.sort_values("date", inplace=True)
        df.reset_index(drop=True, inplace=True)

        df["is_preprocessed"] = False
        return df

    df = pd.read_csv(path)

    if "date" not in df.columns:
        raise ValueError("❌ Processed CSV must contain 'date' column")

    df["date"] = pd.to_datetime(df["date"])
    df.sort_values("date", inplace=True)
    df.reset_index(drop=True, inplace=True)

    # 🔥 IMPORTANT FLAG
    df["is_preprocessed"] = True

    logger.info(f"✅ Loaded {len(df)} rows from processed dataset")

    return df


def load_data(source: str = "db") -> pd.DataFrame:

    if source == "db":
        db = SessionLocal()

        try:
            rates = (
                db.query(ExchangeRate)
                .filter(ExchangeRate.rate != None)
                .order_by(ExchangeRate.date.asc())
                .all()
            )

            rates_df = pd.DataFrame([{
                "date": r.date,
                "rate": r.rate,
                "open_rate": r.open_rate,
                "high_rate": r.high_rate,
                "low_rate": r.low_rate,
                "daily_return": r.daily_return,
            } for r in rates])

            if rates_df.empty:
                logger.warning("⚠️ Exchange Rates DB is empty.")
                return pd.DataFrame()

            macros = db.query(MacroIndicator).all()

            macro_df = pd.DataFrame([{
                "date": m.date,
                "Inflation": m.inflation,
                "Money_Supply": m.money_supply_m2,
                "Foreign_Reserves": m.foreign_reserves,
                "Current_Account_Balance": m.current_account_balance,
                "Lending_Interest_Rate": m.lending_interest_rate,
                "Real_Interest_Rate": m.real_interest_rate,
                "GDP_Growth": m.gdp_growth,
                "us_cpi": m.us_cpi,
                "us_cpi_yoy": m.us_cpi_yoy,
                "us_fed_rate": m.us_fed_rate,
                "inflation_diff": m.inflation_diff,
                "interest_rate_diff": m.interest_rate_diff,
            } for m in macros])

            if macro_df.empty:
                logger.warning("⚠️ No macro data → using rates only")
                df = rates_df.copy()
            else:
                logger.info("🔗 Merging macro data...")
                df = pd.merge(rates_df, macro_df, on="date", how="left")

            df["date"] = pd.to_datetime(df["date"])
            df.sort_values("date", inplace=True)
            df.reset_index(drop=True, inplace=True)

            df["is_preprocessed"] = False  # DB always needs processing

            return df

        finally:
            db.close()

    elif source == "csv":
        return load_processed_csv()

    else:
        raise ValueError(f"Unknown source: {source}")