import os
import logging
import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from ml.models.arima_model import ARIMAForecaster
from ml.models.arimax_model import ARIMAXForecaster
from ml.models.prophet_model import ProphetForecaster
from ml.models.lstm_model import LSTMForecaster

warnings.filterwarnings("ignore")

logger = logging.getLogger(__name__)

# =========================================================
# OUTPUT DIRECTORIES
# =========================================================
OUTPUT_DIR = "outputs/metrics"
PLOT_DIR = "outputs/plots"
MODEL_DIR = "ml/artifacts"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(PLOT_DIR, exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)


# =========================================================
# SAFE METRIC EXTRACTION
# =========================================================
def safe_metrics(model, model_name):
    """
    Prevent crashes if metric keys differ.
    """

    metrics = getattr(model, "metrics", {}) or {}

    return {
        "model": model_name,
        "rmse": float(metrics.get("rmse", 9999)),
        "mae": float(metrics.get("mae", 9999)),
        "mape": float(metrics.get("mape", 9999)),
        "r_squared": float(
            metrics.get(
                "r_squared",
                metrics.get("r2", -999)
            )
        ),
    }


# =========================================================
# DATA CLEANING
# =========================================================
def clean_dataset(df):
    """
    Global dataset cleaning before training.
    """

    df = df.copy()

    if "date" not in df.columns:
        raise ValueError("Dataset must contain 'date' column")

    if "rate" not in df.columns:
        raise ValueError("Dataset must contain 'rate' column")

    df["date"] = pd.to_datetime(df["date"])

    df = df.sort_values("date")

    # remove future dates
    df = df[df["date"] <= pd.Timestamp.today()]

    # numeric safety
    numeric_cols = df.select_dtypes(include=[np.number]).columns

    df[numeric_cols] = (
        df[numeric_cols]
        .replace([np.inf, -np.inf], np.nan)
        .ffill()
        .bfill()
    )

    # remove remaining null target
    df = df.dropna(subset=["rate"])

    df = df.reset_index(drop=True)

    logger.info(f"✅ Clean dataset shape: {df.shape}")

    return df


# =========================================================
# TRAIN / TEST SPLIT
# =========================================================
def time_series_split(df, split_ratio=0.9):

    split_index = int(len(df) * split_ratio)

    train_df = df.iloc[:split_index].copy()
    test_df = df.iloc[split_index:].copy()

    return train_df, test_df


# =========================================================
# TRAIN ALL MODELS
# =========================================================
def train_models(df):

    logger.info("🚀 Starting forecasting pipeline...")

    # -----------------------------------------------------
    # CLEAN DATA
    # -----------------------------------------------------
    df = clean_dataset(df)

    train_df, test_df = time_series_split(df)

    logger.info(
        f"📊 Train size={len(train_df)} | "
        f"Test size={len(test_df)}"
    )

    results = []

    # =====================================================
    # ARIMA
    # =====================================================
    try:

        logger.info("========== TRAINING ARIMA ==========")

        arima = ARIMAForecaster()

        arima.fit(train_df)

        arima.save(
            f"{MODEL_DIR}/arima.pkl"
        )

        metrics = safe_metrics(
            arima,
            "ARIMA"
        )

        results.append(metrics)

        logger.info(f"✅ ARIMA complete → {metrics}")

    except Exception as e:

        logger.exception(f"❌ ARIMA failed: {e}")

    # =====================================================
    # ARIMAX
    # =====================================================
    try:

        logger.info("========== TRAINING ARIMAX ==========")

        arimax = ARIMAXForecaster()

        arimax.fit(train_df)

        arimax.save(
            f"{MODEL_DIR}/arimax.pkl"
        )

        metrics = safe_metrics(
            arimax,
            "ARIMAX"
        )

        results.append(metrics)

        logger.info(f"✅ ARIMAX complete → {metrics}")

    except Exception as e:

        logger.exception(f"❌ ARIMAX failed: {e}")

    # =====================================================
    # PROPHET
    # =====================================================
    try:

        logger.info("========== TRAINING PROPHET ==========")

        prophet = ProphetForecaster()

        prophet.fit(train_df)

        prophet.save(
            f"{MODEL_DIR}/prophet.pkl"
        )

        metrics = safe_metrics(
            prophet,
            "Prophet"
        )

        results.append(metrics)

        logger.info(f"✅ Prophet complete → {metrics}")

    except Exception as e:

        logger.exception(f"❌ Prophet failed: {e}")

    # =====================================================
    # LSTM
    # =====================================================
    try:

        logger.info("========== TRAINING LSTM ==========")

        lstm = LSTMForecaster()

        lstm.fit(train_df)

        predictions = lstm.predict(test_df)

        lstm.evaluate(predictions)

        lstm.save()

        lstm.save_results(predictions)

        metrics = safe_metrics(
            lstm,
            "LSTM"
        )

        results.append(metrics)

        logger.info(f"✅ LSTM complete → {metrics}")

    except Exception as e:

        logger.exception(f"❌ LSTM failed: {e}")

    # =====================================================
    # RESULTS TABLE
    # =====================================================
    if len(results) == 0:
        raise RuntimeError(
            "All models failed during training."
        )

    results_df = pd.DataFrame(results)

    results_df = results_df.sort_values(
        by="rmse",
        ascending=True
    )

    # -----------------------------------------------------
    # SAVE RESULTS
    # -----------------------------------------------------
    comparison_path = (
        f"{OUTPUT_DIR}/model_comparison.csv"
    )

    results_df.to_csv(
        comparison_path,
        index=False
    )

    logger.info(
        f"📊 Comparison saved → {comparison_path}"
    )

    # =====================================================
    # PLOT MODEL COMPARISON
    # =====================================================
    try:

        plt.figure(figsize=(10, 5))

        plt.bar(
            results_df["model"],
            results_df["rmse"]
        )

        plt.title("Model RMSE Comparison")

        plt.xlabel("Model")

        plt.ylabel("RMSE")

        plt.tight_layout()

        plot_path = (
            f"{PLOT_DIR}/model_comparison.png"
        )

        plt.savefig(plot_path)

        plt.close()

        logger.info(
            f"📈 Comparison plot saved → {plot_path}"
        )

    except Exception as e:

        logger.warning(
            f"Plot generation failed: {e}"
        )

    # =====================================================
    # BEST MODEL
    # =====================================================
    best_model = results_df.iloc[0]

    logger.info(
        f"🏆 BEST MODEL: {best_model['model']}"
    )

    print("\n🏆 BEST MODEL:")
    print(best_model)

    return results_df