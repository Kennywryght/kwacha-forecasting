import logging

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

    # -----------------------------------------------------
    # 1. Fetch latest data (non-blocking)
    # -----------------------------------------------------
    logger.info("📡 Fetching latest data...")
    try:
        raw_data = fetch_latest_data()
        if raw_data is not None:
            db = SessionLocal()
            save_to_db(db, raw_data)
            db.close()
    except Exception as e:
        logger.warning(f"⚠️ Live fetch failed: {e}")

    # -----------------------------------------------------
    # 2. Load data (DB → CSV fallback)
    # -----------------------------------------------------
    logger.info("📂 Loading dataset...")
    df = load_data("db")

    MIN_ROWS = 1000

    if df is None or df.empty or len(df) < MIN_ROWS:
        logger.warning(f"⚠️ DB insufficient ({0 if df is None else len(df)} rows) → using CSV")
        df = load_data("csv")

    if df is None or df.empty:
        logger.error("❌ No data available")
        return None

    logger.info(f"✅ Data loaded: {df.shape}")

    # -----------------------------------------------------
    # 3. Detect if dataset is already preprocessed
    # -----------------------------------------------------
    is_preprocessed = False

    try:
        # Heuristic: processed dataset has many columns (your CSV has ~33)
        if len(df.columns) > 10:
            is_preprocessed = True
    except Exception:
        is_preprocessed = False

    # -----------------------------------------------------
    # 4. Safely evaluate preprocessed flag (handle Series)
    # -----------------------------------------------------
    def _to_bool(val):
        """Convert various types to a strict boolean, handling pandas Series/DataFrame."""
        if hasattr(val, 'iloc'):          # pandas Series or DataFrame
            if val.empty:
                return False
            # Take first element and recursively convert
            return _to_bool(val.iloc[0])
        return bool(val)

    preprocessed_flag = _to_bool(is_preprocessed)

    # -----------------------------------------------------
    # 5. Cleaning + Feature Engineering (only if needed)
    # -----------------------------------------------------
    if not preprocessed_flag:
        logger.info("🧹 Cleaning data...")
        df = clean_data(df)

        logger.info("🧩 Filling gaps...")
        df = fill_gaps(df)

        logger.info("⚙️ Engineering features...")
        df = engineer_features(df)
    else:
        logger.info("⏭️ Skipping preprocessing (already processed dataset)")

    if df is None or df.empty:
        logger.error("❌ Data empty after processing")
        return None

    # -----------------------------------------------------
    # 6. Train models
    # -----------------------------------------------------
    logger.info("🤖 Training models...")
    results = train_models(df)

    if results:
        logger.info("✅ Pipeline completed successfully!")
    else:
        logger.warning("⚠️ No models trained")

    return results