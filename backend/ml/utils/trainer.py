import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import logging

from ml.models.arima_model import ARIMAModel
from ml.models.arimax_model import ARIMAXModel
from ml.models.prophet_model import ProphetForecaster
from ml.models.lstm_model import LSTMForecaster
# (You’ll add LSTM later if not yet ready)

logger = logging.getLogger(__name__)

OUTPUT_DIR = "outputs/metrics"
PLOT_DIR = "outputs/plots"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(PLOT_DIR, exist_ok=True)


# -----------------------------
# METRICS FUNCTION
# -----------------------------
def compute_metrics(y_true, y_pred):
    rmse = np.sqrt(np.mean((y_true - y_pred) ** 2))
    mae = np.mean(np.abs(y_true - y_pred))
    mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100

    return {
        "rmse": rmse,
        "mae": mae,
        "mape": mape,
    }


# -----------------------------
# TIME SERIES SPLIT
# -----------------------------
def time_series_split(df, split_ratio=0.8):
    split_idx = int(len(df) * split_ratio)
    return df[:split_idx], df[split_idx:]


# -----------------------------
# TRAIN ALL MODELS
# -----------------------------
def train_models(df):
    logger.info("🚀 Starting model training pipeline...")

    train_df, test_df = time_series_split(df)

    results = []

    # -------------------------
    # ARIMA
    # -------------------------
    try:
        arima = ARIMAModel()
        arima.fit(train_df)

        pred = arima.predict(test_df)

        metrics = compute_metrics(pred["y_true"], pred["y_pred"])
        metrics["model"] = "ARIMA"

        results.append(metrics)

        logger.info(f"ARIMA done: {metrics}")

    except Exception as e:
        logger.error(f"ARIMA failed: {e}")

    # -------------------------
    # ARIMAX
    # -------------------------
    try:
        arimax = ARIMAXModel()
        arimax.fit(train_df)

        pred = arimax.predict(test_df)

        metrics = compute_metrics(pred["y_true"], pred["y_pred"])
        metrics["model"] = "ARIMAX"

        results.append(metrics)

        logger.info(f"ARIMAX done: {metrics}")

    except Exception as e:
        logger.error(f"ARIMAX failed: {e}")

    # -------------------------
    # PROPHET
    # -------------------------
    try:
        prophet = ProphetForecaster()
        prophet.fit(train_df)

        pred = prophet.predict(test_df)

        metrics = prophet.evaluate(pred)
        metrics["model"] = "Prophet"

        prophet.save_plot(pred)

        results.append(metrics)

        logger.info(f"Prophet done: {metrics}")

    except Exception as e:
        logger.error(f"Prophet failed: {e}")
        
        # -------------------------
    # LSTM
    # -------------------------
    try:
        lstm = LSTMForecaster()

        lstm.fit(train_df)

        pred = lstm.predict(test_df)

        metrics = lstm.evaluate(pred)

        metrics["model"] = "LSTM"

        lstm.save_results(pred)

        results.append(metrics)

        logger.info(f"LSTM done: {metrics}")

    except Exception as e:
        logger.error(f"LSTM failed: {e}")

    # -------------------------
    # SAVE RESULTS
    # -------------------------
    results_df = pd.DataFrame(results)

    results_df = results_df.sort_values(by="rmse")

    results_path = f"{OUTPUT_DIR}/model_comparison.csv"
    results_df.to_csv(results_path, index=False)

    logger.info(f"📊 Model comparison saved → {results_path}")

    # -------------------------
    # PLOT COMPARISON
    # -------------------------
    plt.figure(figsize=(8, 5))
    plt.bar(results_df["model"], results_df["rmse"])
    plt.title("Model Comparison (RMSE)")
    plt.xlabel("Model")
    plt.ylabel("RMSE")

    plot_path = f"{PLOT_DIR}/model_comparison.png"
    plt.savefig(plot_path)
    plt.close()

    logger.info(f"📈 Comparison plot saved → {plot_path}")

    # -------------------------
    # PRINT BEST MODEL
    # -------------------------
    best_model = results_df.iloc[0]

    print("\n🏆 BEST MODEL:")
    print(best_model)

    return results_df