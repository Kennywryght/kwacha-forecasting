import os
import sys

# Must run from backend/ folder — this adds backend to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../backend"))

from ml.pipeline.loader import load_raw_csv
from ml.pipeline.cleaner import clean_data
from ml.pipeline.gap_filler import fill_gap
from ml.pipeline.feature_engineer import engineer_features
from ml.pipeline.db_seeder import seed_exchange_rates, seed_macro_indicators
from core.logging_config import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)


def main():
    logger.info("=" * 50)
    logger.info("DATABASE SEED STARTED")
    logger.info("=" * 50)

    # Step 1 — Load
    df = load_raw_csv()

    # Step 2 — Clean
    df = clean_data(df)

    # Step 3 — Fill the Nov 2024 → Apr 2026 gap
    df = fill_gap(df)

    # Step 4 — Engineer features
    df = engineer_features(df)

    # Step 5 — Save processed CSV
    out_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../data/processed/mwk_usd_clean.csv")
    )
    df.to_csv(out_path, index=False)
    logger.info(f"Processed CSV saved → {out_path}")

    # Step 6 — Seed database
    seed_exchange_rates(df)
    seed_macro_indicators(df)

    logger.info("=" * 50)
    logger.info("DATABASE SEED COMPLETE")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()