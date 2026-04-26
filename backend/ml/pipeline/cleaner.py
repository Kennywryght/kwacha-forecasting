import pandas as pd
import numpy as np
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from core.logging_config import get_logger

logger = get_logger(__name__)


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    logger.info("Starting data cleaning...")
    df = df.copy()

    # 1. Drop duplicates on date
    before = len(df)
    df.drop_duplicates(subset=["date"], keep="last", inplace=True)
    logger.info(f"Duplicates removed: {before - len(df)}")

    # 2. Remove weekends (forex market closed)
    df = df[df["date"].dt.dayofweek < 5].copy()
    logger.info(f"Rows after removing weekends: {len(df)}")

    # 3. Fix zero or negative rates (impossible values)
    bad_rates = df["rate"] <= 0
    if bad_rates.sum() > 0:
        logger.warning(f"Zero/negative rates found: {bad_rates.sum()} — fixing with forward fill")
        df.loc[bad_rates, "rate"] = np.nan
        df["rate"] = df["rate"].ffill()

    # 4. Fix outliers using IQR method on daily returns
    df["daily_return"] = df["rate"].pct_change() * 100
    Q1 = df["daily_return"].quantile(0.01)
    Q3 = df["daily_return"].quantile(0.99)
    outliers = (df["daily_return"] < Q1) | (df["daily_return"] > Q3)
    logger.info(f"Outliers detected: {outliers.sum()}")
    df.loc[outliers, "rate"] = np.nan
    df["rate"] = df["rate"].interpolate(method="linear")
    df["daily_return"] = df["rate"].pct_change() * 100

    # 5. Fill remaining macro nulls with forward fill then backward fill
    macro_cols = [
        "Inflation", "Money_Supply", "Foreign_Reserves",
        "Current_Account_Balance", "Lending_Interest_Rate",
        "Real_Interest_Rate", "GDP_Growth", "us_cpi",
        "us_cpi_yoy", "us_fed_rate"
    ]
    for col in macro_cols:
        if col in df.columns:
            df[col] = df[col].ffill().bfill()

    logger.info(f"Cleaning complete. Final rows: {len(df)}")
    return df