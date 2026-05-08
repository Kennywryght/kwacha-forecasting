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

OUTPUT_DIR = "outputs/metrics"
PLOT_DIR = "outputs/plots"
MODEL_DIR = "ml/artifacts"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(PLOT_DIR, exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)


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

    df = clean_dataset(df)
    train_df, test_df = time_series_split(df)

    results = []

    # =====================================================
    # ARIMA
    # =====================================================
    try:
        m = ARIMAForecaster()
        m.fit(train_df)
        pred = m.predict(test_df)

        results.append(safe_metrics(m, "ARIMA"))
    except Exception as e:
        logger.exception(e)

    # =====================================================
    # ARIMAX
    # =====================================================
    try:
        m = ARIMAXForecaster()
        m.fit(train_df)
        pred = m.predict(test_df)

        results.append(safe_metrics(m, "ARIMAX"))
    except Exception as e:
        logger.exception(e)

    # =====================================================
    # PROPHET (🔥 FIXED INTERFACE)
    # =====================================================
    try:
        m = ProphetForecaster()
        m.fit(train_df)

        # 🔥 FIX: pass horizon, NOT dataframe
        horizon = len(test_df)

        pred = m.predict(horizon)

        results.append(safe_metrics(m, "Prophet"))

    except Exception as e:
        logger.exception(e)

    # =====================================================
    # LSTM
    # =====================================================
    try:
        m = LSTMForecaster()
        m.fit(train_df)
        pred = m.predict(test_df)

        results.append(safe_metrics(m, "LSTM"))
    except Exception as e:
        logger.exception(e)

    # =====================================================
    # RESULTS
    # =====================================================
    results_df = pd.DataFrame(results).sort_values("rmse")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(PLOT_DIR, exist_ok=True)
    
    results_df.to_csv(
        os.path.join(OUTPUT_DIR, "model_comparison.csv"),
        index=False
        
    )

    plt.figure()
    plt.bar(results_df["model"], results_df["rmse"])
    plt.title("Model Comparison")
    plt.savefig(os.path.join(PLOT_DIR, "comparison.png"))
    plt.close()

    print("\n🏆 BEST MODEL:")
    print(results_df.iloc[0])

    return results_df