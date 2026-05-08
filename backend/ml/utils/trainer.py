import logging
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from ml.models.arima_model import ARIMAForecaster
from ml.models.arimax_model import ARIMAXForecaster
from ml.models.prophet_model import ProphetForecaster
from ml.models.lstm_model import LSTMForecaster
from ml.utils.io_utils import ensure_dirs
from ml.utils.db_logger import log_model_run

from ml.utils.metrics import compute_all_metrics
from ml.utils.io_utils import ensure_dirs

warnings.filterwarnings("ignore")
logger = logging.getLogger(__name__)

OUTPUT_DIR = "outputs/metrics"
PLOT_DIR = "outputs/plots"


def safe_metrics(model, name):
    m = getattr(model, "metrics", {}) or {}

    return {
        "model": name,
        "rmse": float(m.get("rmse", 9999)),
        "mae": float(m.get("mae", 9999)),
        "mape": float(m.get("mape", 9999)),
        "r_squared": float(m.get("r_squared", -999)),
    }


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

    # ==========================================
    # ENSURE OUTPUT DIRECTORIES EXIST
    # ==========================================
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(PLOT_DIR, exist_ok=True)
    os.makedirs(MODEL_DIR, exist_ok=True)

    df = clean_dataset(df)

    train_df, test_df = time_series_split(df)

    results = []

    # ==========================================
    # IMPORT EVALUATION
    # ==========================================
    from ml.utils.evaluation import (
        evaluate_prediction_dict,
        evaluate_prediction_dataframe
    )

    # =================================================
    # ARIMA
    # =================================================
    try:
        logger.info("Training ARIMA...")

        m = ARIMAForecaster()

        m.fit(train_df)

        pred = m.predict(test_df)

        metrics = evaluate_prediction_dict(pred)

        m.metrics = metrics

        results.append(safe_metrics(m, "ARIMA"))

        logger.info(f"ARIMA Metrics: {metrics}")

    except Exception as e:
        logger.exception(f"ARIMA failed: {e}")

    # =================================================
    # ARIMAX
    # =================================================
    try:
        logger.info("Training ARIMAX...")

        m = ARIMAXForecaster()

        m.fit(train_df)

        pred = m.predict(test_df)

        metrics = evaluate_prediction_dict(pred)

        m.metrics = metrics

        results.append(safe_metrics(m, "ARIMAX"))

        logger.info(f"ARIMAX Metrics: {metrics}")

    except Exception as e:
        logger.exception(f"ARIMAX failed: {e}")

    # =================================================
    # PROPHET
    # =================================================
    try:
        logger.info("Training Prophet...")

        m = ProphetForecaster()

        m.fit(train_df)

        pred = m.predict(len(test_df))

        prophet_pred = {
            "y_true": test_df["rate"].values,
            "y_pred": pred["predicted"]
        }

        metrics = evaluate_prediction_dict(prophet_pred)

        m.metrics = metrics

        results.append(safe_metrics(m, "Prophet"))

        logger.info(f"Prophet Metrics: {metrics}")

    except Exception as e:
        logger.exception(f"Prophet failed: {e}")

    # =================================================
    # LSTM
    # =================================================
    try:
        logger.info("Training LSTM...")

        m = LSTMForecaster()

        m.fit(train_df)

        pred_df = m.predict(test_df)

        metrics = evaluate_prediction_dataframe(pred_df)

        m.metrics = metrics

        results.append(safe_metrics(m, "LSTM"))

        logger.info(f"LSTM Metrics: {metrics}")

    except Exception as e:
        logger.exception(f"LSTM failed: {e}")

    # ==========================================
    # RESULTS TABLE
    # ==========================================
    results_df = pd.DataFrame(results)

    if results_df.empty:
        logger.error("❌ No successful model training")
        return None

    results_df = results_df.sort_values("rmse")

    # ==========================================
    # SAVE RESULTS
    # ==========================================
    csv_path = os.path.join(
        OUTPUT_DIR,
        "model_comparison.csv"
    )

    results_df.to_csv(csv_path, index=False)

    # ==========================================
    # PLOT RESULTS
    # ==========================================
    plt.figure(figsize=(8, 5))

    plt.bar(
        results_df["model"],
        results_df["rmse"]
    )

    plt.title("Model RMSE Comparison")

    plt.ylabel("RMSE")

    plt.tight_layout()

    plot_path = os.path.join(
        PLOT_DIR,
        "comparison.png"
    )

    plt.savefig(plot_path)

    plt.close()

    # ==========================================
    # PRINT BEST MODEL
    # ==========================================
    best = results_df.iloc[0]

    print("\n🏆 BEST MODEL:")
    print(best)

    logger.info(f"Best Model: {best['model']}")

    return results_df