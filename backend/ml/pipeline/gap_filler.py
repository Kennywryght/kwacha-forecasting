import pandas as pd
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from core.logging_config import get_logger

logger = get_logger(__name__)


def fill_gaps(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean gap handler (NO synthetic data).
    
    - Ensures continuous business-day index
    - Fills small missing gaps using interpolation
    - DOES NOT create future fake data
    """
    
    # CRITICAL FIX: Handle empty dataframe or missing 'date' immediately
    if df.empty or 'date' not in df.columns:
        logger.warning("⚠️ Gap Filler: Input DF is empty or missing 'date'. Skipping.")
        return df

    df = df.copy()
    df.sort_values("date", inplace=True)
    df["date"] = pd.to_datetime(df["date"])

    # Remove any rows where date is NaT to prevent bdate_range crash
    df = df.dropna(subset=['date'])

    if df.empty:
        logger.warning("⚠️ Gap Filler: DF empty after removing NaT dates. Skipping.")
        return df

    # CRITICAL FIX: Verify min/max are not NaT before generating range
    start_date = df["date"].min()
    end_date = df["date"].max()

    if pd.isna(start_date) or pd.isna(end_date):
        logger.error("❌ Cannot fill gaps: Invalid date range (NaT detected).")
        return df

    # Create full business day range
    full_dates = pd.bdate_range(start=start_date, end=end_date)

    df = df.set_index("date").reindex(full_dates).rename_axis("date").reset_index()

    # Interpolate ONLY internal missing values
    df["rate"] = df["rate"].interpolate(method="linear")

    # Recompute daily return
    df["daily_return"] = df["rate"].pct_change() * 100

    # Mark interpolated rows
    df["is_interpolated"] = df["rate"].isna()

    logger.info(f"Gaps handled (no synthetic future data). Rows: {len(df)}")

    return df