"""Feature engineering module for MWK/USD forecasting.

This module creates features for time series forecasting including:
- Lag features with configurable horizons
- Rolling statistics (mean, std, min, max)
- Momentum indicators
- Temporal features (day of week, month, quarter, etc.)
- Cyclical encodings for temporal features
- Macroeconomic differential features
"""

import pandas as pd
import numpy as np
from typing import List, Optional, Dict, Any
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from core.logging_config import get_logger

logger = get_logger(__name__)


# Configuration defaults
DEFAULT_LAGS = [1, 3, 7, 14, 30, 60, 90]
DEFAULT_ROLLING_WINDOWS = [7, 14, 30, 60, 90]
DEFAULT_MOMENTUM_WINDOWS = [7, 14, 30, 60]
DEFAULT_ROLLING_MIN_MAX_WINDOW = 30


def engineer_features(
    df: pd.DataFrame,
    lags: List[int] = DEFAULT_LAGS,
    rolling_windows: List[int] = DEFAULT_ROLLING_WINDOWS,
    momentum_windows: List[int] = DEFAULT_MOMENTUM_WINDOWS,
    rolling_min_max_window: int = DEFAULT_ROLLING_MIN_MAX_WINDOW,
    add_cyclical_features: bool = True,
    add_macro_diffs: bool = True,
    verbose: bool = True
) -> pd.DataFrame:
    """
    Engineer features for time series forecasting.

    Args:
        df: Input DataFrame with 'date' and 'rate' columns
        lags: List of lag values to create
        rolling_windows: List of window sizes for rolling statistics
        momentum_windows: List of windows for momentum features
        rolling_min_max_window: Window size for min/max features
        add_cyclical_features: Whether to add cyclical temporal encodings
        add_macro_diffs: Whether to add macroeconomic differential features
        verbose: Whether to log progress

    Returns:
        DataFrame with engineered features

    Raises:
        ValueError: If required columns are missing
    """
    logger.info("Starting feature engineering...")

    if df.empty:
        raise ValueError("Cannot engineer features on empty DataFrame")

    required_cols = ["date", "rate"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Required column '{col}' not found in DataFrame")

    # Copy and sort
    df = df.copy()
    df.sort_values("date", inplace=True)
    df.reset_index(drop=True, inplace=True)

    # Ensure rate is numeric
    df["rate"] = pd.to_numeric(df["rate"], errors="coerce")
    if df["rate"].isna().any():
        logger.warning(f"Found {df['rate'].isna().sum()} NaN rates, filling forward")
        df["rate"] = df["rate"].ffill()

    original_shape = df.shape

    # ============================================================
    # 1. LAG FEATURES
    # ============================================================
    for lag in lags:
        df[f"lag_{lag}"] = df["rate"].shift(lag)
        if verbose and lag % 10 == 0:
            logger.debug(f"Created lag_{lag}")

    # ============================================================
    # 2. ROLLING STATISTICS
    # ============================================================
    for window in rolling_windows:
        # Mean
        df[f"rolling_mean_{window}"] = df["rate"].rolling(
            window=window, min_periods=1
        ).mean()

        # Standard deviation
        df[f"rolling_std_{window}"] = df["rate"].rolling(
            window=window, min_periods=1
        ).std()

        if verbose and window % 30 == 0:
            logger.debug(f"Created rolling features for window {window}")

    # Min and max (using default window)
    df[f"rolling_min_{rolling_min_max_window}"] = df["rate"].rolling(
        window=rolling_min_max_window, min_periods=1
    ).min()

    df[f"rolling_max_{rolling_min_max_window}"] = df["rate"].rolling(
        window=rolling_min_max_window, min_periods=1
    ).max()

    # ============================================================
    # 3. MOMENTUM FEATURES
    # ============================================================
    for window in momentum_windows:
        df[f"momentum_{window}"] = df["rate"] - df["rate"].shift(window)
        df[f"roc_{window}"] = df["rate"].pct_change(window) * 100

    # ============================================================
    # 4. DATE/TEMPORAL FEATURES
    # ============================================================
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # Basic temporal features
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["quarter"] = df["date"].dt.quarter
    df["day_of_week"] = df["date"].dt.dayofweek
    df["day_of_year"] = df["date"].dt.dayofyear
    df["week_of_year"] = df["date"].dt.isocalendar().week.astype(int)

    # Add is_weekend flag
    df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)

    # ============================================================
    # 5. CYCLICAL ENCODINGS
    # ============================================================
    if add_cyclical_features:
        # Month cycle
        df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
        df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)

        # Day of week cycle
        df["dow_sin"] = np.sin(2 * np.pi * df["day_of_week"] / 7)
        df["dow_cos"] = np.cos(2 * np.pi * df["day_of_week"] / 7)

        # Quarter cycle
        df["quarter_sin"] = np.sin(2 * np.pi * df["quarter"] / 4)
        df["quarter_cos"] = np.cos(2 * np.pi * df["quarter"] / 4)

        logger.debug("Added cyclical temporal encodings")

    # ============================================================
    # 6. MACROECONOMIC DIFFERENTIALS
    # ============================================================
    if add_macro_diffs:
        # Inflation differential (Malawi - US)
        if "Inflation" in df.columns and "us_cpi_yoy" in df.columns:
            df["inflation_diff"] = df["Inflation"] - df["us_cpi_yoy"]
            logger.debug("Added inflation differential feature")

        # Interest rate differential (Malawi - US)
        if "Lending_Interest_Rate" in df.columns and "us_fed_rate" in df.columns:
            df["interest_rate_diff"] = (
                df["Lending_Interest_Rate"] - df["us_fed_rate"]
            )
            logger.debug("Added interest rate differential feature")

        # Real interest rate differential
        if "Real_Interest_Rate" in df.columns:
            df["real_interest_diff"] = df["Real_Interest_Rate"] - df["us_fed_rate"] if "us_fed_rate" in df.columns else np.nan
            logger.debug("Added real interest rate differential feature")

    # ============================================================
    # 7. HANDLE MISSING VALUES
    # ============================================================
    # Replace infinities with NaN
    df.replace([np.inf, -np.inf], np.nan, inplace=True)

    # For time series, forward fill is usually safer than interpolation
    df.ffill(inplace=True)
    df.bfill(inplace=True)

    # Remove rows where rate is still NaN
    if df["rate"].isna().any():
        nan_count = df["rate"].isna().sum()
        logger.warning(f"Removing {nan_count} rows with NaN rates after filling")
        df = df.dropna(subset=["rate"])

    final_shape = df.shape

    if final_shape[0] < 100:
        logger.warning(f"⚠️ Dataset is very small after feature engineering ({final_shape[0]} rows)")

    logger.info(f"Feature engineering complete: {original_shape[1]} → {final_shape[1]} features, {final_shape[0]} rows")

    return df


def create_lagged_features(
    df: pd.DataFrame,
    column: str,
    lags: List[int]
) -> pd.DataFrame:
    """
    Create lagged features for a specific column.

    Args:
        df: Input DataFrame
        column: Column name to create lags for
        lags: List of lag values

    Returns:
        DataFrame with lagged features added
    """
    df = df.copy()
    for lag in lags:
        df[f"{column}_lag_{lag}"] = df[column].shift(lag)
    return df


def create_rolling_features(
    df: pd.DataFrame,
    column: str,
    windows: List[int],
    stats: List[str] = ["mean", "std"]
) -> pd.DataFrame:
    """
    Create rolling statistics features.

    Args:
        df: Input DataFrame
        column: Column name to compute rolling stats for
        windows: List of window sizes
        stats: List of statistics to compute

    Returns:
        DataFrame with rolling features added
    """
    df = df.copy()

    for window in windows:
        for stat in stats:
            if stat == "mean":
                df[f"{column}_rolling_mean_{window}"] = df[column].rolling(
                    window=window, min_periods=1
                ).mean()
            elif stat == "std":
                df[f"{column}_rolling_std_{window}"] = df[column].rolling(
                    window=window, min_periods=1
                ).std()
            elif stat == "min":
                df[f"{column}_rolling_min_{window}"] = df[column].rolling(
                    window=window, min_periods=1
                ).min()
            elif stat == "max":
                df[f"{column}_rolling_max_{window}"] = df[column].rolling(
                    window=window, min_periods=1
                ).max()

    return df