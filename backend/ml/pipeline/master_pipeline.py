"""Master pipeline orchestrator for MWK/USD forecasting.

This module provides a simplified entry point for running the entire pipeline
with sensible defaults. It orchestrates data fetching, preprocessing,
feature engineering, and model training.
"""

import logging
import sys
import os
from datetime import datetime
from typing import Optional, Dict, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from ml.pipeline.live_fetcher import fetch_latest_data
from ml.pipeline.db_seeder import save_to_db
from ml.pipeline.loader import load_data
from ml.pipeline.cleaner import clean_data
from ml.pipeline.gap_filler import fill_gaps
from ml.pipeline.feature_engineer import engineer_features
from ml.utils.trainer import train_models
from ml.utils.mlflow_tracker import MLflowTracker
from db.database import SessionLocal

logger = logging.getLogger(__name__)


def run_pipeline(
    force_retrain: bool = False,
    models: Optional[list] = None,
    use_live_data: bool = True
) -> Dict[str, Any]:
    """
    Run the master pipeline with simplified configuration.

    Args:
        force_retrain: Whether to force retraining of all models
        models: List of models to train ('arima', 'arimax', 'prophet', 'lstm', 'ensemble')
        use_live_data: Whether to fetch live data

    Returns:
        Dictionary with pipeline results
    """
    logger.info("=" * 60)
    logger.info("🚀 Starting master pipeline...")
    logger.info(f"Started at: {datetime.now().isoformat()}")
    logger.info(f"Force retrain: {force_retrain}")
    logger.info(f"Models: {models or 'all'}")
    logger.info("=" * 60)

    results = {
        "status": "started",
        "timestamp": datetime.now().isoformat(),
        "steps": {}
    }

    # ============================================================
    # 1. Fetch latest data (optional)
    # ============================================================
    if use_live_data:
        logger.info("📡 Fetching latest data...")
        try:
            raw_data = fetch_latest_data()
            if raw_data is not None and not raw_data.empty:
                db = SessionLocal()
                try:
                    save_to_db(db, raw_data)
                    logger.info(f"✅ Saved {len(raw_data)} new records")
                finally:
                    db.close()
                results["steps"]["data_fetch"] = {"status": "success", "rows": len(raw_data)}
            else:
                logger.warning("⚠️ No new data fetched")
        except Exception as e:
            logger.warning(f"⚠️ Live fetch failed: {e}")
            results["steps"]["data_fetch"] = {"status": "warning", "error": str(e)}
    else:
        logger.info("⏭️ Skipping live data fetch")

    # ============================================================
    # 2. Load data
    # ============================================================
    logger.info("📂 Loading dataset...")
    df = load_data("db")
    MIN_ROWS = 1000

    if df is None or df.empty or len(df) < MIN_ROWS:
        logger.warning(f"⚠️ DB insufficient → using CSV")
        df = load_data("csv")

    if df is None or df.empty:
        logger.error("❌ No data available")
        results["status"] = "failed"
        return results

    logger.info(f"✅ Data loaded: {df.shape}")
    results["steps"]["data_load"] = {"status": "success", "shape": df.shape}

    # ============================================================
    # 3. Preprocess if needed
    # ============================================================
    is_preprocessed = len(df.columns) > 10 and "rolling_mean_30" in df.columns

    if not is_preprocessed:
        logger.info("🧹 Cleaning data...")
        df = clean_data(df)

        logger.info("🧩 Filling gaps...")
        df = fill_gaps(df)

        logger.info("⚙️ Engineering features...")
        df = engineer_features(df)

        results["steps"]["preprocessing"] = {"status": "success", "shape": df.shape}
    else:
        logger.info("⏭️ Skipping preprocessing (dataset already processed)")
        results["steps"]["preprocessing"] = {"status": "skipped"}

    if df is None or df.empty:
        logger.error("❌ Data empty after preprocessing")
        results["status"] = "failed"
        return results

    # ============================================================
    # 4. Train models
    # ============================================================
    logger.info("🤖 Training models...")

    try:
        trained_models = train_models(
            df,
            models_to_train=models,
            force_retrain=force_retrain
        )

        if trained_models:
            logger.info(f"✅ Trained models: {list(trained_models.keys())}")
            results["steps"]["training"] = {
                "status": "success",
                "models": list(trained_models.keys())
            }
        else:
            logger.warning("⚠️ No models trained")
            results["steps"]["training"] = {"status": "warning", "message": "No models trained"}

    except Exception as e:
        logger.error(f"❌ Model training failed: {e}")
        results["steps"]["training"] = {"status": "failed", "error": str(e)}
        results["status"] = "failed"
        return results

    # ============================================================
    # 5. Summary
    # ============================================================
    results["status"] = "completed"
    results["end_timestamp"] = datetime.now().isoformat()

    logger.info("=" * 60)
    logger.info("✅ Pipeline completed successfully!")
    logger.info("=" * 60)

    return results


if __name__ == "__main__":
    # Run pipeline when script is executed directly
    run_pipeline()