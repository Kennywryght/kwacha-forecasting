"""Full pipeline for MWK/USD forecasting.

This module orchestrates the complete ML pipeline:
1. Data fetching from live sources
2. Data loading and preprocessing
3. Feature engineering
4. Model training (all models)
5. Hyperparameter tuning
6. Model evaluation and explainability
7. Artifact saving
"""

import logging
import os
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional

import pandas as pd
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from ml.pipeline.live_fetcher import fetch_latest_data
from ml.pipeline.db_seeder import save_to_db
from ml.pipeline.loader import load_data
from ml.pipeline.cleaner import clean_data
from ml.pipeline.gap_filler import fill_gaps
from ml.pipeline.feature_engineer import engineer_features
from ml.utils.trainer import train_models
from ml.utils.tuner import (
    tune_arima_auto,
    tune_arimax_auto,
    tune_prophet,
    tune_lstm,
    tune_ensemble
)
from ml.utils.explainability import run_explainability
from ml.utils.mlflow_tracker import MLflowTracker
from db.database import SessionLocal

logger = logging.getLogger(__name__)


def run_full_pipeline(
    force_retrain: bool = False,
    skip_tuning: bool = False,
    skip_explainability: bool = False,
    models_to_train: Optional[list] = None
) -> Dict[str, Any]:
    """
    Run the complete ML pipeline.

    Args:
        force_retrain: Whether to force retraining even if artifacts exist
        skip_tuning: Whether to skip hyperparameter tuning
        skip_explainability: Whether to skip model explainability
        models_to_train: List of models to train ('arima', 'arimax', 'prophet', 'lstm', 'ensemble')

    Returns:
        Dictionary with pipeline results
    """
    logger.info("=" * 60)
    logger.info("FULL PIPELINE: data update + training + tuning + explainability")
    logger.info(f"Started at: {datetime.now().isoformat()}")
    logger.info("=" * 60)

    results = {
        "status": "started",
        "timestamp": datetime.now().isoformat(),
        "steps": {}
    }

    # ============================================================
    # 1. Fetch latest data (non-blocking)
    # ============================================================
    logger.info("📡 Fetching latest data...")
    try:
        raw_data = fetch_latest_data()
        if raw_data is not None and not raw_data.empty:
            db = SessionLocal()
            try:
                save_to_db(db, raw_data)
                logger.info(f"✅ Saved {len(raw_data)} new records to database")
            finally:
                db.close()
            results["steps"]["data_fetch"] = {"status": "success", "rows": len(raw_data)}
        else:
            logger.warning("⚠️ No new data fetched")
            results["steps"]["data_fetch"] = {"status": "warning", "message": "No new data"}
    except Exception as e:
        logger.error(f"❌ Data fetch failed: {e}")
        results["steps"]["data_fetch"] = {"status": "failed", "error": str(e)}

    # ============================================================
    # 2. Load data (DB → CSV fallback)
    # ============================================================
    logger.info("📂 Loading dataset...")
    df = load_data("db")
    MIN_ROWS = 1000

    if df is None or df.empty or len(df) < MIN_ROWS:
        logger.warning(f"⚠️ DB insufficient ({0 if df is None else len(df)} rows) → using CSV")
        df = load_data("csv")

    if df is None or df.empty:
        logger.error("❌ No data available")
        results["status"] = "failed"
        return results

    logger.info(f"✅ Data loaded: {df.shape}")
    results["steps"]["data_load"] = {"status": "success", "shape": df.shape}

    # ============================================================
    # 3. Data validation and preprocessing
    # ============================================================
    is_preprocessed = False
    if len(df.columns) > 10 and "rolling_mean_30" in df.columns:
        is_preprocessed = True
        logger.info("⏭️ Dataset appears preprocessed, skipping cleaning")

    if not is_preprocessed:
        logger.info("🧹 Cleaning data...")
        try:
            df = clean_data(df)
            results["steps"]["cleaning"] = {"status": "success", "shape": df.shape}
        except Exception as e:
            logger.error(f"❌ Cleaning failed: {e}")
            results["steps"]["cleaning"] = {"status": "failed", "error": str(e)}
            results["status"] = "failed"
            return results

        logger.info("🧩 Filling gaps...")
        try:
            df = fill_gaps(df)
            results["steps"]["gap_fill"] = {"status": "success"}
        except Exception as e:
            logger.warning(f"⚠️ Gap filling failed: {e}")
            results["steps"]["gap_fill"] = {"status": "warning", "error": str(e)}

        logger.info("⚙️ Engineering features...")
        try:
            df = engineer_features(df)
            results["steps"]["feature_engineering"] = {"status": "success", "features": len(df.columns)}
        except Exception as e:
            logger.error(f"❌ Feature engineering failed: {e}")
            results["steps"]["feature_engineering"] = {"status": "failed", "error": str(e)}
            results["status"] = "failed"
            return results

    if df is None or df.empty:
        logger.error("❌ Data empty after preprocessing")
        results["status"] = "failed"
        return results

    # ============================================================
    # 4. Model training
    # ============================================================
    logger.info("🤖 Training models...")

    try:
        # Initialize MLflow tracker
        mlflow_tracker = MLflowTracker()

        # Train models
        trained_models = train_models(
            df,
            models_to_train=models_to_train,
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

    # ============================================================
    # 5. Hyperparameter tuning (optional)
    # ============================================================
    tuning_results = {}
    if not skip_tuning:
        logger.info("🔧 Hyperparameter tuning...")

        # Define models to tune
        tune_models = models_to_train or ["arima", "arimax", "prophet", "lstm"]

        for model_name in tune_models:
            try:
                if model_name == "arima":
                    tuning_results["arima"] = tune_arima_auto(df)
                elif model_name == "arimax":
                    tuning_results["arimax"] = tune_arimax_auto(df)
                elif model_name == "prophet":
                    tuning_results["prophet"] = tune_prophet(df)
                elif model_name == "lstm":
                    tuning_results["lstm"] = tune_lstm(df)
                elif model_name == "ensemble":
                    tuning_results["ensemble"] = tune_ensemble(df)
                logger.info(f"✅ Tuned {model_name}")
            except Exception as e:
                logger.warning(f"⚠️ Tuning {model_name} failed: {e}")
                tuning_results[model_name] = {"status": "failed", "error": str(e)}

        # Save tuning results
        os.makedirs("outputs/metrics", exist_ok=True)
        tuning_path = "outputs/metrics/tuning_results.json"

        clean_results = {}
        for k, v in tuning_results.items():
            if isinstance(v, dict):
                clean_results[k] = {
                    kk: vv for kk, vv in v.items()
                    if not callable(vv) and type(vv) in [int, float, str, list, dict, tuple, bool]
                }
            else:
                clean_results[k] = str(v) if v is not None else None

        with open(tuning_path, "w") as f:
            json.dump(clean_results, f, indent=2, default=str)

        logger.info(f"✅ Tuning results saved to {tuning_path}")
        results["steps"]["tuning"] = {"status": "success", "path": tuning_path}

    # ============================================================
    # 6. Model explainability (optional)
    # ============================================================
    if not skip_explainability:
        logger.info("🔍 Running explainability analysis...")
        try:
            explainability_results = run_explainability(df, method="permutation")
            logger.info("✅ Explainability complete")
            results["steps"]["explainability"] = {"status": "success"}
        except Exception as e:
            logger.warning(f"⚠️ Explainability failed: {e}")
            results["steps"]["explainability"] = {"status": "warning", "error": str(e)}

    # ============================================================
    # 7. Summary
    # ============================================================
    results["status"] = "completed"
    results["end_timestamp"] = datetime.now().isoformat()

    logger.info("=" * 60)
    logger.info("✅ Full pipeline completed successfully!")
    logger.info(f"Results: {json.dumps(results, indent=2, default=str)}")
    logger.info("=" * 60)

    return results


if __name__ == "__main__":
    # Run pipeline when script is executed directly
    run_full_pipeline()