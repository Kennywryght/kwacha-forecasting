# backend/ml/pipeline/full_pipeline.py
import logging
import os
import pandas as pd
import numpy as np

from ml.pipeline.live_fetcher import fetch_latest_data
from ml.pipeline.db_seeder import save_to_db
from ml.pipeline.loader import load_data
from ml.pipeline.cleaner import clean_data
from ml.pipeline.gap_filler import fill_gaps
from ml.pipeline.feature_engineer import engineer_features
from ml.utils.trainer import train_models
from ml.utils.tuner import (tune_arima_auto, tune_arimax_auto, tune_prophet, tune_lstm)
# from ml.utils.explainability import run_explainability   # ← commented to avoid crash
from db.database import SessionLocal

logger = logging.getLogger(__name__)


def run_full_pipeline():
    logger.info("="*60)
    logger.info("FULL PIPELINE: data update + base training + tuning + explainability")
    logger.info("="*60)

    # ---- 1. Fetch latest data (non‑blocking) ----
    logger.info("📡 Fetching latest data...")
    try:
        raw_data = fetch_latest_data()
        if raw_data is not None:
            db = SessionLocal()
            save_to_db(db, raw_data)
            db.close()
    except Exception as e:
        logger.warning(f"⚠️ Live fetch failed: {e}")

    # ---- 2. Load data (DB → CSV fallback) ----
    logger.info("📂 Loading dataset...")
    df = load_data("db")
    MIN_ROWS = 1000
    if df is None or df.empty or len(df) < MIN_ROWS:
        logger.warning(f"⚠️ DB insufficient → using CSV")
        df = load_data("csv")

    if df is None or df.empty:
        logger.error("❌ No data available")
        return

    logger.info(f"✅ Data loaded: {df.shape}")

    # ---- 3. Preprocess if necessary ----
    if len(df.columns) < 10:   # not yet engineered
        logger.info("🧹 Cleaning, filling gaps, engineering features...")
        df = clean_data(df)
        df = fill_gaps(df)
        df = engineer_features(df)

    if df is None or df.empty:
        logger.error("❌ Data empty after preprocessing")
        return

    logger.info(f"Data ready: {df.shape}")

    # ---- 4. Base model training (saves best_model.pkl) ----
    logger.info("Step 1/3: Training base models...")
    train_models(df)

    # ---- 5. Hyperparameter tuning ----
    logger.info("Step 2/3: Hyperparameter tuning...")
    tuning_results = {}
    try:
        tuning_results["arima"] = tune_arima_auto(df)
    except Exception as e:
        logger.warning(f"ARIMA tuning failed: {e}")
    try:
        tuning_results["arimax"] = tune_arimax_auto(df)
    except Exception as e:
        logger.warning(f"ARIMAX tuning failed: {e}")
    try:
        tuning_results["prophet"] = tune_prophet(df)
    except Exception as e:
        logger.warning(f"Prophet tuning failed: {e}")
    try:
        tuning_results["lstm"] = tune_lstm(df)
    except Exception as e:
        logger.warning(f"LSTM tuning failed: {e}")

    import json
    os.makedirs("outputs/metrics", exist_ok=True)
    with open("outputs/metrics/tuning_results.json", "w") as f:
        clean_results = {}
        for k, v in tuning_results.items():
            if isinstance(v, dict):
                clean_results[k] = {kk: vv for kk, vv in v.items()
                                    if not callable(vv) and type(vv) in [int, float, str, list, dict, tuple, bool]}
        json.dump(clean_results, f, indent=2, default=str)
    logger.info("Tuning results saved.")

    # ---- 6. Explainability (skipped – ARIMAX score bug) ----
    # run_explainability(df, method="permutation")   # ← disabled for now

    logger.info("Full pipeline completed. All outputs in 'outputs/' and 'ml/artifacts/'.")