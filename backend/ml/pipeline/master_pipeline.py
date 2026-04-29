import logging
from datetime import datetime

from ml.pipeline.live_fetcher import fetch_latest_data
from ml.pipeline.db_seeder import save_to_db
from ml.pipeline.loader import load_data
from ml.pipeline.cleaner import clean_data
from ml.pipeline.gap_filler import fill_gaps
from ml.pipeline.feature_engineer import engineer_features

from ml.utils.trainer import train_models
from db.database import SessionLocal

logger = logging.getLogger(__name__)


def run_pipeline():
    logger.info("🚀 Starting full pipeline...")

    # 1. Fetch latest data (Best effort)
    logger.info("📡 Attempting to fetch latest exchange rate data...")
    try:
        raw_data = fetch_latest_data()
        if raw_data is not None:
            logger.info("💾 Saving fetched data to database...")
            db = SessionLocal()
            save_to_db(db, raw_data)
            db.close()
        else:
            logger.info("⚠️ No new data fetched, continuing with existing DB data.")
    except Exception as e:
        logger.warning(f"⚠️ Live fetch failed, but continuing: {e}")

    # 2. Load full dataset (Priority: DB -> CSV Fallback)
    logger.info("📂 Loading dataset from DB...")
    df = load_data(source="db")

    if df.empty:
        logger.warning("⚠️ DB is empty. Attempting to load from CSV fallback...")
        df = load_data(source="csv")

    # Critical Check
    if df.empty:
        logger.error("❌ FATAL: No data available in DB or CSV. Aborting pipeline.")
        return None

    logger.info(f"✅ Data loaded successfully. Shape: {df.shape}")

    # 3. Clean data
    logger.info("🧹 Cleaning data...")
    df = clean_data(df)

    # 4. Fill gaps
    logger.info("🧩 Filling missing values...")
    df = fill_gaps(df)

    if df.empty:
        logger.error("❌ Data empty after gap filling.")
        return None

    # 5. Feature engineering
    logger.info("⚙️ Engineering features...")
    df = engineer_features(df)

    # 6. Train models
    logger.info("🤖 Training models...")
    results = train_models(df)

    if results:
        logger.info("✅ Pipeline completed successfully!")
    else:
        logger.warning("⚠️ Pipeline completed, but model training returned no results.")

    return results