import pandas as pd
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from core.config import get_settings
from core.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()


def load_raw_csv() -> pd.DataFrame:
    path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../../../data/raw/mwk_usd_final_dataset.csv")
    )
    logger.info(f"Loading raw CSV: {path}")
    if not os.path.exists(path):
        raise FileNotFoundError(f"CSV not found at: {path}")

    df = pd.read_csv(path, parse_dates=["Date"])
    df.rename(columns={"Date": "date", "MWK_USD": "rate"}, inplace=True)
    df["date"] = pd.to_datetime(df["date"])
    df.sort_values("date", inplace=True)
    df.reset_index(drop=True, inplace=True)

    logger.info(f"Loaded {len(df)} rows | {df['date'].min().date()} → {df['date'].max().date()}")
    return df