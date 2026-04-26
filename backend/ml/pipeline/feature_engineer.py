import pandas as pd
import numpy as np
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from core.logging_config import get_logger

logger = get_logger(__name__)


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    logger.info("Engineering features...")
    df = df.copy()
    df.sort_values("date", inplace=True)
    df.reset_index(drop=True, inplace=True)

    # ── Lag features (what the rate was N days ago)
    for lag in [1, 3, 7, 14, 30]:
        df[f"lag_{lag}"] = df["rate"].shift(lag)

    # ── Rolling statistics
    for window in [7, 14, 30, 60]:
        df[f"rolling_mean_{window}"] = df["rate"].rolling(window).mean()
        df[f"rolling_std_{window}"]  = df["rate"].rolling(window).std()

    # ── Rolling min/max (captures range pressure)
    df["rolling_min_30"] = df["rate"].rolling(30).min()
    df["rolling_max_30"] = df["rate"].rolling(30).max()

    # ── Momentum indicators
    df["momentum_7"]  = df["rate"] - df["rate"].shift(7)
    df["momentum_30"] = df["rate"] - df["rate"].shift(30)

    # ── Rate of change
    df["roc_7"]  = df["rate"].pct_change(7)  * 100
    df["roc_30"] = df["rate"].pct_change(30) * 100

    # ── Calendar features
    df["year"]        = df["date"].dt.year
    df["month"]       = df["date"].dt.month
    df["quarter"]     = df["date"].dt.quarter
    df["day_of_week"] = df["date"].dt.dayofweek
    df["day_of_year"] = df["date"].dt.dayofyear
    df["week_of_year"]= df["date"].dt.isocalendar().week.astype(int)

    # ── Cyclical encoding (so month 12 and month 1 are close numerically)
    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)
    df["dow_sin"]   = np.sin(2 * np.pi * df["day_of_week"] / 5)
    df["dow_cos"]   = np.cos(2 * np.pi * df["day_of_week"] / 5)

    # ── Macro differentials (already in dataset, recalculate cleanly)
    if "Inflation" in df.columns and "us_cpi_yoy" in df.columns:
        df["inflation_diff"] = df["Inflation"] - df["us_cpi_yoy"]

    if "Lending_Interest_Rate" in df.columns and "us_fed_rate" in df.columns:
        df["interest_rate_diff"] = df["Lending_Interest_Rate"] - df["us_fed_rate"]

    # ── Drop rows with NaN from lag/rolling (first 60 rows)
    df.dropna(subset=["lag_30", "rolling_mean_30"], inplace=True)
    df.reset_index(drop=True, inplace=True)

    logger.info(f"Feature engineering complete. Shape: {df.shape}")
    return df