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


def load_raw_csv() -> pd.DataFrame:
    # CHANGE: Replaced raw path with processed path as requested
    path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../../../data/processed/mwk_usd_clean.csv")
    )
    
    logger.info(f"Loading CSV: {path}")
    if not os.path.exists(path):
        # Fallback to check the raw location if processed is missing
        logger.warning("Processed CSV not found, checking raw location...")
        raw_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../../../data/raw/mwk_usd_final_dataset.csv")
        )
        if os.path.exists(raw_path):
            logger.warning("Using Raw CSV as fallback for loader.")
            path = raw_path
        else:
            raise FileNotFoundError(f"CSV not found at processed or raw location.")

    df = pd.read_csv(path, parse_dates=["Date"])
    df.rename(columns={"Date": "date", "MWK_USD": "rate"}, inplace=True)
    df["date"] = pd.to_datetime(df["date"])
    df.sort_values("date", inplace=True)
    df.reset_index(drop=True, inplace=True)

    logger.info(f"Loaded {len(df)} rows | {df['date'].min().date()} → {df['date'].max().date()}")
    return df

def load_data(source: str = "db") -> pd.DataFrame:
    """
    Master loader for pipeline.
    
    source:
        - "db" → load from DB
        - "csv" → fallback to local dataset
    """

    if source == "db":
        db = SessionLocal()

        try:
            # Load exchange rates
            rates = (
                db.query(ExchangeRate)
                .filter(ExchangeRate.rate != None)  # Exclude records with null rates
                .order_by(ExchangeRate.date.asc())
                .all())
            rates_df = pd.DataFrame([{
                "date": r.date,
                "rate": r.rate,
                "open_rate": r.open_rate,
                "high_rate": r.high_rate,
                "low_rate": r.low_rate,
                "daily_return": r.daily_return,
            } for r in rates])

            # Check if rates_df is empty
            if rates_df.empty:
                logger.warning("⚠️ Exchange Rates DB is empty. Returning empty DataFrame.")
                return pd.DataFrame()

            # Load macro data
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

            # Merge datasets
            if macro_df is None or macro_df.empty:
                logger.warning("⚠️ Macro data is empty — proceeding without macro indicators")
                df = rates_df.copy()
            else:
                if "date" not in macro_df.columns:
                    logger.warning("⚠️ Macro data missing 'date' column — skipping merge")
                    df = rates_df.copy()
                else:
                    logger.info("🔗 Merging Exchange Rates with Macro Indicators...")
                    df = pd.merge(rates_df, macro_df, on="date", how="left")

            df["date"] = pd.to_datetime(df["date"])
            df.sort_values("date", inplace=True)
            df.reset_index(drop=True, inplace=True)
            df = df[df["date"] >= pd.to_datetime("2013-01-01")]
            df = df[df["date"] <= pd.Timestamp.today()]

            return df

        finally:
            db.close()

    elif source == "csv":
        # Use the helper function which now points to the processed file
        return load_raw_csv()

    else:
        raise ValueError(f"Unknown source: {source}")