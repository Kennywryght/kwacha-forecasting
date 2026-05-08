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

    # =========================
    # BASIC SORT + CLEAN
    # =========================
    df.sort_values("date", inplace=True)
    df.reset_index(drop=True, inplace=True)

    # ensure numeric safety
    df["rate"] = pd.to_numeric(df["rate"], errors="coerce")
    df = df.dropna(subset=["rate"])

    # =========================
    # LAG FEATURES
    # =========================
    for lag in [1, 3, 7, 14, 30]:
        df[f"lag_{lag}"] = df["rate"].shift(lag)

    # =========================
    # ROLLING FEATURES
    # =========================
    for window in [7, 14, 30, 60]:
        df[f"rolling_mean_{window}"] = df["rate"].rolling(window, min_periods=2).mean()
        df[f"rolling_std_{window}"] = df["rate"].rolling(window, min_periods=2).std()

    df["rolling_min_30"] = df["rate"].rolling(30, min_periods=2).min()
    df["rolling_max_30"] = df["rate"].rolling(30, min_periods=2).max()

    # =========================
    # MOMENTUM
    # =========================
    df["momentum_7"] = df["rate"] - df["rate"].shift(7)
    df["momentum_30"] = df["rate"] - df["rate"].shift(30)

    # =========================
    # RATE OF CHANGE
    # =========================
    df["roc_7"] = df["rate"].pct_change(7) * 100
    df["roc_30"] = df["rate"].pct_change(30) * 100

    # =========================
    # DATE FEATURES
    # =========================
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["quarter"] = df["date"].dt.quarter
    df["day_of_week"] = df["date"].dt.dayofweek
    df["day_of_year"] = df["date"].dt.dayofyear

    # FIX: ensure integer type for isocalendar
    df["week_of_year"] = df["date"].dt.isocalendar().week.astype(int)

    # =========================
    # CYCLICAL ENCODING
    # =========================
    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)
    df["dow_sin"] = np.sin(2 * np.pi * df["day_of_week"] / 7)
    df["dow_cos"] = np.cos(2 * np.pi * df["day_of_week"] / 7)

    # =========================
    # MACRO DIFFERENCES (SAFE)
    # =========================
    df["inflation_diff"] = np.nan
    df["interest_rate_diff"] = np.nan

    if "Inflation" in df.columns and "us_cpi_yoy" in df.columns:
        df["inflation_diff"] = df["Inflation"] - df["us_cpi_yoy"]

    if "Lending_Interest_Rate" in df.columns and "us_fed_rate" in df.columns:
        df["interest_rate_diff"] = (
            df["Lending_Interest_Rate"] - df["us_fed_rate"]
        )

    # =========================
    # CLEAN FINAL DATA
    # =========================

    # IMPORTANT: avoid destroying dataset
    df.replace([np.inf, -np.inf], np.nan, inplace=True)

    # fill forward/backward (critical for ARIMA + ARIMAX stability)
    df.ffill(inplace=True)
    df.bfill(inplace=True)

    # remove only remaining NaNs in core columns
    df = df.dropna(subset=["rate", "date"])

    # =========================
    # FINAL SAFETY CHECK
    # =========================
    if len(df) < 50:
        logger.warning("⚠️ Dataset is very small after feature engineering")

    logger.info(f"Feature engineering complete. Shape: {df.shape}")

    return df