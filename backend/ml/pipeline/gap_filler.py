import pandas as pd
import numpy as np
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from core.logging_config import get_logger

logger = get_logger(__name__)


def fill_gap(df: pd.DataFrame) -> pd.DataFrame:
    """
    Dataset ends Nov 2024. Today is Apr 2026.
    We fill the gap with a realistic trend + noise model so the
    LSTM and ARIMA have continuous data to train and predict on.
    Real live rates will overwrite this via the API fetcher later.
    """
    df = df.copy()
    last_date = df["date"].max()
    today = pd.Timestamp("2026-04-18")

    if last_date >= today:
        logger.info("No gap to fill.")
        return df

    logger.info(f"Filling gap: {last_date.date()} → {today.date()}")

    # Business days only (no weekends)
    new_dates = pd.bdate_range(start=last_date + pd.Timedelta(days=1), end=today)
    logger.info(f"Business days to fill: {len(new_dates)}")

    # Use last 90 days to estimate trend slope
    recent = df.tail(90).copy()
    x = np.arange(len(recent))
    y = recent["rate"].values
    slope, intercept = np.polyfit(x, y, 1)
    logger.info(f"Trend slope: {slope:.4f} MWK/day")

    # Generate rates: trend + random walk noise calibrated to historical volatility
    hist_std = df["daily_return"].std()
    last_rate = df["rate"].iloc[-1]
    generated_rates = []
    current_rate = last_rate

    for i in range(len(new_dates)):
        # Trend nudge + noise
        trend_nudge = slope * 0.3
        noise = np.random.normal(0, hist_std * current_rate / 100)
        current_rate = max(current_rate + trend_nudge + noise, last_rate * 0.8)
        generated_rates.append(round(current_rate, 2))

    # Build gap DataFrame matching existing columns
    gap_df = pd.DataFrame({"date": new_dates, "rate": generated_rates})
    gap_df["daily_return"] = gap_df["rate"].pct_change() * 100

    # Forward fill all macro columns from last known values
    last_row = df.iloc[-1]
    macro_cols = [
        "Inflation", "Money_Supply", "Foreign_Reserves",
        "Current_Account_Balance", "Lending_Interest_Rate",
        "Real_Interest_Rate", "GDP_Growth", "us_cpi",
        "us_cpi_yoy", "us_fed_rate", "inflation_diff", "interest_rate_diff",
        "Population"
    ]
    for col in macro_cols:
        if col in df.columns:
            gap_df[col] = last_row.get(col, np.nan)

    # Tag as interpolated
    gap_df["is_interpolated"] = True
    df["is_interpolated"] = False

    combined = pd.concat([df, gap_df], ignore_index=True)
    combined.sort_values("date", inplace=True)
    combined.reset_index(drop=True, inplace=True)

    logger.info(f"Gap filled. Total rows: {len(combined)}")
    return combined