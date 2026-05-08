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

    # 1. Drop duplicates
    df.drop_duplicates(subset=["date"], keep="last", inplace=True)

    # 2. Ensure datetime
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])

    # 3. Remove weekends
    df = df[df["date"].dt.dayofweek < 5]

    # 4. Fix invalid rates
    df["rate"] = pd.to_numeric(df["rate"], errors="coerce")
    df.loc[df["rate"] <= 0, "rate"] = np.nan
    df["rate"] = df["rate"].ffill()

    # 5. Outlier smoothing
    df["daily_return"] = df["rate"].pct_change()

    q_low = df["daily_return"].quantile(0.01)
    q_high = df["daily_return"].quantile(0.99)

    outliers = (df["daily_return"] < q_low) | (df["daily_return"] > q_high)

    df.loc[outliers, "rate"] = np.nan
    df["rate"] = df["rate"].interpolate()

    # recompute safely
    df["daily_return"] = df["rate"].pct_change()

    # 6. Fill macro columns
    macro_cols = [
        "Inflation", "Money_Supply", "Foreign_Reserves",
        "Current_Account_Balance", "Lending_Interest_Rate",
        "Real_Interest_Rate", "GDP_Growth", "us_cpi",
        "us_cpi_yoy", "us_fed_rate"
    ]

    for col in macro_cols:
        if col in df.columns:
            df[col] = df[col].ffill().bfill()

    df = df.dropna(subset=["rate"])
    df.reset_index(drop=True, inplace=True)

    logger.info(f"Cleaning complete: {df.shape}")

    return df