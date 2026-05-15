# backend/ml/utils/trainer.py
import logging
import warnings
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import joblib  # new import for model persistence

from ml.models.arima_model import ARIMAForecaster
from ml.models.arimax_model import ARIMAXForecaster
from ml.models.prophet_model import ProphetForecaster
from ml.models.lstm_model import LSTMForecaster
from ml.utils.io_utils import ensure_dirs
from ml.utils.metrics import compute_all_metrics
from ml.utils.evaluation import (
    evaluate_prediction_dict,
    evaluate_prediction_dataframe
)

warnings.filterwarnings("ignore")
logger = logging.getLogger(__name__)

OUTPUT_DIR = "outputs/metrics"
PLOT_DIR  = "outputs/plots"
MODEL_DIR = "ml/artifacts"


def clean_dataset(df):
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")
    df = df.dropna(subset=["rate"])
    df = df.replace([np.inf, -np.inf], np.nan).ffill().bfill()
    return df


def time_series_split(df, ratio=0.9):
    split = int(len(df) * ratio)
    return df.iloc[:split], df.iloc[split:]


def train_models(df):
    logger.info("🚀 Forecast pipeline started")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(PLOT_DIR, exist_ok=True)
    os.makedirs(MODEL_DIR, exist_ok=True)

    df = clean_dataset(df)
    train_df, test_df = time_series_split(df)
    results = []          # will hold dicts only for successful models

    # ---- Model objects (will hold the last successfully trained instance of each) ----
    arima_model = None
    arimax_model = None
    prophet_model = None
    lstm_model = None

    # ---------- ARIMA ----------
    try:
        logger.info("Training ARIMA...")
        m = ARIMAForecaster()
        m.fit(train_df)
        pred = m.predict(test_df)
        metrics = evaluate_prediction_dict(pred)
        m.metrics = metrics
        results.append({"model": "ARIMA", **metrics})
        arima_model = m   # save object
        logger.info(f"ARIMA Metrics: {metrics}")
    except Exception as e:
        logger.exception(f"ARIMA failed: {e}")

    # ---------- ARIMAX ----------
    try:
        logger.info("Training ARIMAX...")
        m = ARIMAXForecaster()
        m.fit(train_df)
        pred = m.predict(test_df)
        metrics = evaluate_prediction_dict(pred)
        m.metrics = metrics
        results.append({"model": "ARIMAX", **metrics})
        arimax_model = m
        logger.info(f"ARIMAX Metrics: {metrics}")
    except Exception as e:
        logger.exception(f"ARIMAX failed: {e}")

    # ---------- Prophet ----------
    try:
        logger.info("Training Prophet...")
        m = ProphetForecaster()
        m.fit(train_df)
        pred_df = m.predict(len(test_df))
        prophet_pred = {
            "y_true": test_df["rate"].values.tolist(),
            "y_pred": pred_df["predicted"]
        }
        metrics = evaluate_prediction_dict(prophet_pred)
        m.metrics = metrics
        results.append({
            "model": "Prophet",
            **metrics
        })
        prophet_model = m
        logger.info(f"Prophet Metrics: {metrics}")
    except Exception as e:
        logger.exception(f"Prophet failed: {e}")

    # ---------- LSTM ----------
    try:
        logger.info("Training LSTM...")
        m = LSTMForecaster()
        m.fit(train_df)
        pred_dict = m.predict(test_df)   # returns dict
        metrics = compute_all_metrics(
            np.array(pred_dict["y_true"]),
            np.array(pred_dict["y_pred"])
        )
        m.metrics = metrics
        results.append({"model": "LSTM", **metrics})
        lstm_model = m
        logger.info(f"LSTM Metrics: {metrics}")
    except Exception as e:
        logger.exception(f"LSTM failed: {e}")

    if not results:
        logger.error("❌ No model trained successfully")
        return None

    results_df = pd.DataFrame(results).sort_values("rmse")

    # Save comparison CSV and plot (existing)
    results_df.to_csv(os.path.join(OUTPUT_DIR, "model_comparison.csv"), index=False)

    plt.figure(figsize=(8, 5))
    plt.bar(results_df["model"], results_df["rmse"])
    plt.title("Model RMSE Comparison")
    plt.ylabel("RMSE")
    plt.tight_layout()
    plt.savefig(os.path.join(PLOT_DIR, "comparison.png"))
    plt.close()

    # ---- Save the best model object ----
    best_model_name = results_df.iloc[0]["model"]
    model_map = {
        "ARIMA": arima_model,
        "ARIMAX": arimax_model,
        "Prophet": prophet_model,
        "LSTM": lstm_model
    }
    best_model_obj = model_map.get(best_model_name)
    if best_model_obj is not None:
        joblib.dump(best_model_obj, os.path.join(MODEL_DIR, "best_model.pkl"))
        logger.info(f"Best model '{best_model_name}' saved to best_model.pkl")
    else:
        logger.warning(f"Could not retrieve best model object for {best_model_name}")

    best = results_df.iloc[0]
    print("\n🏆 BEST MODEL:")
    print(best.to_dict())
    logger.info(f"Best Model: {best['model']}")
    return results_df