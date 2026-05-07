import pandas as pd
from prophet import Prophet
from datetime import date
import joblib
import os
import logging
import numpy as np
import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)


class ProphetForecaster:
    def __init__(self, model_path="ml/artifacts/prophet.pkl"):
        self.model = None
        self.model_path = model_path
        self.metrics = {}
        self.is_fitted = False
        self.train_start = None
        self.train_end = None

        self.exog_cols = [
            "Inflation",
            "Foreign_Reserves",
            "Lending_Interest_Rate",
            "us_fed_rate",
            "inflation_diff",
            "interest_rate_diff",
        ]

        self.regressor_cols = []

    # -----------------------------
    # FIT (NOW ACCEPTS TRAIN DATA)
    # -----------------------------
    def fit(self, train_df: pd.DataFrame) -> None:
        logger.info("Prophet: Preparing training data...")

        if "date" not in train_df.columns or "rate" not in train_df.columns:
            raise ValueError(f"Missing required columns: {train_df.columns.tolist()}")

        df_prophet = train_df.copy().rename(columns={"date": "ds", "rate": "y"})

        self.train_start = df_prophet["ds"].min().date()
        self.train_end = df_prophet["ds"].max().date()

        cols = ["ds", "y"] + [c for c in self.exog_cols if c in df_prophet.columns]
        df_prophet = df_prophet[cols]

        self.regressor_cols = [c for c in self.exog_cols if c in df_prophet.columns]

        self.model = Prophet()

        for col in self.regressor_cols:
            self.model.add_regressor(col)

        self.model.fit(df_prophet)

        self.is_fitted = True
        logger.info("✅ Prophet model trained")

    # -----------------------------
    # PREDICT ON TEST SET
    # -----------------------------
    def predict(self, test_df: pd.DataFrame) -> pd.DataFrame:
        if not self.is_fitted:
            raise ValueError("Model not trained yet")

        df_future = test_df.copy().rename(columns={"date": "ds"})

        cols = ["ds"] + [c for c in self.regressor_cols if c in df_future.columns]
        df_future = df_future[cols]

        forecast = self.model.predict(df_future)

        result = pd.DataFrame({
            "date": forecast["ds"],
            "y_true": test_df["rate"].values,
            "y_pred": forecast["yhat"].values
        })

        return result

    # -----------------------------
    # EVALUATE + SAVE PLOT
    # -----------------------------
    def evaluate(self, predictions: pd.DataFrame):
        y_true = predictions["y_true"].values
        y_pred = predictions["y_pred"].values

        rmse = np.sqrt(np.mean((y_true - y_pred) ** 2))
        mae = np.mean(np.abs(y_true - y_pred))
        mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100
        r2 = 1 - (
            np.sum((y_true - y_pred) ** 2)
            / np.sum((y_true - np.mean(y_true)) ** 2)
        )

        self.metrics = {
            "rmse": rmse,
            "mae": mae,
            "mape": mape,
            "r_squared": r2,
        }

        logger.info(
            f"Prophet Evaluation → RMSE={rmse:.4f}, MAE={mae:.4f}, "
            f"MAPE={mape:.2f}%, R2={r2:.4f}"
        )

        return self.metrics

    # -----------------------------
    # SAVE FORECAST PLOT (🔥 DEMO)
    # -----------------------------
    def save_plot(self, predictions: pd.DataFrame):
        os.makedirs("outputs/plots", exist_ok=True)

        plt.figure(figsize=(10, 5))
        plt.plot(predictions["date"], predictions["y_true"], label="Actual", color="blue")
        plt.plot(predictions["date"], predictions["y_pred"], label="Forecast", linestyle="--", color="red")

        plt.title("Prophet Forecast vs Actual")
        plt.xlabel("Date")
        plt.ylabel("Exchange Rate")
        plt.legend()

        path = "outputs/plots/prophet_forecast.png"
        plt.savefig(path)
        plt.close()

        logger.info(f"📊 Forecast plot saved → {path}")

    # -----------------------------
    # SAVE MODEL
    # -----------------------------
    def save(self, path: str = None):
        path = path or self.model_path
        os.makedirs(os.path.dirname(path), exist_ok=True)

        joblib.dump(
            {
                "model": self.model,
                "metrics": self.metrics,
                "train_start": self.train_start.isoformat() if self.train_start else None,
                "train_end": self.train_end.isoformat() if self.train_end else None,
            },
            path,
        )

        logger.info(f"Model saved to {path}")

    # -----------------------------
    # LOAD MODEL
    # -----------------------------
    def load(self, path: str = None):
        path = path or self.model_path

        data = joblib.load(path)
        self.model = data["model"]
        self.metrics = data.get("metrics", {})

        raw_start = data.get("train_start")
        raw_end = data.get("train_end")

        self.train_start = date.fromisoformat(raw_start) if raw_start else None
        self.train_end = date.fromisoformat(raw_end) if raw_end else None

        self.is_fitted = True

        logger.info(f"Model loaded from {path}")