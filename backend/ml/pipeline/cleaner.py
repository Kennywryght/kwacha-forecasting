"""Data cleaning module for MWK/USD exchange rate data.

This module provides robust data cleaning functionality including:
- Duplicate removal
- Date validation and weekend handling
- Outlier detection and treatment
- Gap filling for macroeconomic indicators
- Validation of exchange rate plausibility
"""

import pandas as pd
import numpy as np
from typing import Optional, Tuple
from datetime import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from core.logging_config import get_logger

logger = get_logger(__name__)

# Configuration constants
MWK_USD_MIN = 100.0  # Historical minimum
MWK_USD_MAX = 2500.0  # Current maximum
OUTLIER_MAD_THRESHOLD = 5.0  # Median Absolute Deviation threshold
MIN_ROWS_AFTER_CLEANING = 100


def clean_data(
    df: pd.DataFrame,
    remove_weekends: bool = True,
    outlier_method: str = "mad",  # "mad" or "percentile"
    mad_threshold: float = OUTLIER_MAD_THRESHOLD,
    percentile_low: float = 0.005,
    percentile_high: float = 0.995,
    fill_macro: bool = True,
    validate_rate_plausibility: bool = True,
    verbose: bool = True
) -> pd.DataFrame:
    """
    Clean and prepare exchange rate data for analysis.

    Args:
        df: Raw DataFrame with exchange rate data
        remove_weekends: Whether to remove weekend data points
        outlier_method: Method for outlier detection ('mad' or 'percentile')
        mad_threshold: Threshold for MAD outlier detection
        percentile_low: Lower percentile for outlier detection
        percentile_high: Upper percentile for outlier detection
        fill_macro: Whether to fill macroeconomic indicators
        validate_rate_plausibility: Whether to check rate bounds
        verbose: Whether to log detailed cleaning statistics

    Returns:
        Cleaned DataFrame with validated rates

    Raises:
        ValueError: If cleaning results in insufficient data
    """
    logger.info("Starting data cleaning...")
    original_shape = df.shape

    if df.empty:
        raise ValueError("Cannot clean empty DataFrame")

    df = df.copy()

    # ============================================================
    # 1. Drop duplicates
    # ============================================================
    duplicates_before = len(df)
    df.drop_duplicates(subset=["date"], keep="last", inplace=True)
    duplicates_after = len(df)

    if verbose:
        logger.info(f"Removed {duplicates_before - duplicates_after} duplicate rows")

    # ============================================================
    # 2. Ensure datetime
    # ============================================================
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    invalid_dates = df["date"].isna().sum()
    if invalid_dates > 0:
        logger.warning(f"Removed {invalid_dates} rows with invalid dates")
    df = df.dropna(subset=["date"])

    # Sort by date
    df.sort_values("date", inplace=True)
    df.reset_index(drop=True, inplace=True)

    # ============================================================
    # 3. Remove weekends (if configured)
    # ============================================================
    if remove_weekends:
        weekend_rows = df["date"].dt.dayofweek >= 5
        if weekend_rows.any():
            df = df[~weekend_rows]
            if verbose:
                logger.info(f"Removed {weekend_rows.sum()} weekend rows")

    # ============================================================
    # 4. Validate and clean rate column
    # ============================================================
    df["rate"] = pd.to_numeric(df["rate"], errors="coerce")

    # Apply plausibility check
    if validate_rate_plausibility:
        invalid_mask = (df["rate"] < MWK_USD_MIN) | (df["rate"] > MWK_USD_MAX)
        if invalid_mask.any():
            logger.warning(f"Found {invalid_mask.sum()} rows with implausible rates")
            df.loc[invalid_mask, "rate"] = np.nan

    # Initial forward fill for obvious missing values
    initial_nan = df["rate"].isna().sum()
    if initial_nan > 0:
        logger.info(f"Forward-filling {initial_nan} missing rate values")
        df["rate"] = df["rate"].ffill()

    # ============================================================
    # 5. Outlier detection and treatment
    # ============================================================
    df["daily_return"] = df["rate"].pct_change()

    if outlier_method == "mad":
        # MAD-based outlier detection (more robust than percentile)
        median_return = df["daily_return"].median()
        mad = np.median(np.abs(df["daily_return"] - median_return))

        if mad > 0:  # Avoid division by zero
            outlier_mask = np.abs(df["daily_return"] - median_return) > (mad_threshold * mad)
            outlier_count = outlier_mask.sum()
        else:
            outlier_mask = pd.Series(False, index=df.index)
            outlier_count = 0

    else:  # percentile method
        q_low = df["daily_return"].quantile(percentile_low)
        q_high = df["daily_return"].quantile(percentile_high)
        outlier_mask = (df["daily_return"] < q_low) | (df["daily_return"] > q_high)
        outlier_count = outlier_mask.sum()

    if outlier_count > 0:
        logger.info(f"Detected {outlier_count} outliers ({outlier_count/len(df)*100:.2f}%)")

        # Replace outliers with NaN and interpolate
        df.loc[outlier_mask, "rate"] = np.nan

        # Use linear interpolation for outliers (better than ffill for isolated spikes)
        df["rate"] = df["rate"].interpolate(method="linear", limit_direction="both")

    # Recompute daily returns after interpolation
    df["daily_return"] = df["rate"].pct_change()

    # ============================================================
    # 6. Use existing quality flags if present
    # ============================================================
    if "is_extreme_day" in df.columns:
        extreme_count = df["is_extreme_day"].sum()
        if extreme_count > 0:
            logger.info(f"Found {extreme_count} rows marked as extreme days")
            # Don't remove, but flag for model weighting

    if "is_interpolated" in df.columns:
        interpolated_count = df["is_interpolated"].sum()
        if interpolated_count > 0:
            logger.info(f"Found {interpolated_count} rows marked as interpolated")

    # ============================================================
    # 7. Fill macroeconomic indicators
    # ============================================================
    if fill_macro:
        macro_cols = [
            "Inflation", "Money_Supply", "Foreign_Reserves",
            "Current_Account_Balance", "Lending_Interest_Rate",
            "Real_Interest_Rate", "GDP_Growth", "us_cpi",
            "us_cpi_yoy", "us_fed_rate"
        ]

        for col in macro_cols:
            if col in df.columns:
                before_nan = df[col].isna().sum()
                if before_nan > 0:
                    # Forward fill first, then backward fill
                    df[col] = df[col].ffill().bfill()
                    after_nan = df[col].isna().sum()
                    if verbose and after_nan < before_nan:
                        logger.debug(f"Filled {before_nan - after_nan} NaNs in {col}")

    # ============================================================
    # 8. Final cleaning and validation
    # ============================================================
    # Remove any remaining rows with NaN rates
    final_nan_count = df["rate"].isna().sum()
    if final_nan_count > 0:
        logger.warning(f"Removing {final_nan_count} rows with NaN rates")
        df = df.dropna(subset=["rate"])

    # Reset index
    df.reset_index(drop=True, inplace=True)

    # ============================================================
    # 9. Log final statistics and validate
    # ============================================================
    final_shape = df.shape
    logger.info(f"Cleaning complete: {duplicates_before} → {final_shape[0]} rows")

    if final_shape[0] < MIN_ROWS_AFTER_CLEANING:
        raise ValueError(
            f"Cleaning resulted in only {final_shape[0]} rows. "
            f"Minimum required: {MIN_ROWS_AFTER_CLEANING}"
        )

    # Log key statistics
    if verbose:
        logger.info(f"Date range: {df['date'].min()} to {df['date'].max()}")
        logger.info(f"Rate range: {df['rate'].min():.2f} to {df['rate'].max():.2f}")
        logger.info(f"Mean rate: {df['rate'].mean():.2f}")

    return df


def detect_outliers_mad(
    series: pd.Series,
    threshold: float = OUTLIER_MAD_THRESHOLD
) -> pd.Series:
    """
    Detect outliers using Median Absolute Deviation method.

    Args:
        series: Input series
        threshold: MAD threshold multiplier

    Returns:
        Boolean mask of outliers
    """
    median = series.median()
    mad = np.median(np.abs(series - median))

    if mad == 0:
        return pd.Series(False, index=series.index)

    return np.abs(series - median) > (threshold * mad)


def detect_outliers_iqr(
    series: pd.Series,
    multiplier: float = 1.5
) -> pd.Series:
    """
    Detect outliers using IQR method.

    Args:
        series: Input series
        multiplier: IQR multiplier

    Returns:
        Boolean mask of outliers
    """
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1

    lower_bound = q1 - multiplier * iqr
    upper_bound = q3 + multiplier * iqr

    return (series < lower_bound) | (series > upper_bound)