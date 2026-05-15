import logging
import os
import pandas as pd
import numpy as np

from ml.pipeline.loader import load_data
from ml.pipeline.cleaner import clean_data
from ml.pipeline.gap_filler import fill_gaps
from ml.pipeline.feature_engineer import engineer_features
from ml.utils.trainer import train_models
from ml.utils.tuner import (tune_arima_auto, tune_arimax_auto, tune_prophet, tune_lstm)
from ml.utils.explainability import run_explainability

logger = logging.getLogger(__name__)


def run_full_pipeline():
    logger.info("="*60)
    logger.info("FULL PIPELINE: base training + hyperparameter tuning + explainability")
    logger.info("="*60)

    # ---- 1. Load and preprocess data ----
    df = load_data("db")
    if df is None or df.empty:
        df = load_data("csv")
    if df is None or df.empty:
        logger.error("No data available")
        return

    if len(df.columns) < 10:   # not yet engineered
        df = clean_data(df)
        df = fill_gaps(df)
        df = engineer_features(df)
    logger.info(f"Data ready: {df.shape}")

    # ---- 2. Base model training (saves best_model.pkl) ----
    logger.info("Step 1/3: Training base models...")
    train_models(df)   # already saves best model

    # ---- 3. Hyperparameter tuning ----
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
        # Serialise only basic types
        clean_results = {}
        for k, v in tuning_results.items():
            if isinstance(v, dict):
                clean_results[k] = {kk: vv for kk, vv in v.items() if not callable(vv) and type(vv) in [int, float, str, list, dict, tuple, bool]}
        json.dump(clean_results, f, indent=2, default=str)
    logger.info(f"Tuning results saved to outputs/metrics/tuning_results.json")

    # ---- 4. Explainability ----
    logger.info("Step 3/3: Explainability on best base model...")
    run_explainability(df)

    logger.info("Full pipeline completed. All outputs in 'outputs/' and 'ml/artifacts/'.")