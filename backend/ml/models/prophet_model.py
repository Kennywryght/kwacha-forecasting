import os
import pickle
import warnings
import numpy as np
import pandas as pd

from prophet import Prophet
from ml.models.base_model import BaseForecaster
from ml.utils.metrics import compute_all_metrics
from core.logging_config import get_logger

warnings.filterwarnings("ignore")
logger = get_logger(__name__)


class ProphetForecaster(BaseForecaster):

    def __init__(self):
        super().__init__("prophet")
        self.model = None
        self.last_date = None
        self.metrics = {}

    # =====================================================
    # DATA PREPARATION
    # =====================================================
    def _prepare_prophet_data(self, df):
        df = df.copy()

        prophet_df = pd.DataFrame()
        prophet_df["ds"] = pd.to_datetime(df["date"])

        if "rate" in df.columns:
            prophet_df["y"] = df["rate"]
        elif "usd_mwk" in df.columns:
            prophet_df["y"] = df["usd_mwk"]
        else:
            raise ValueError("Target column not found")

        prophet_df["y"] = (
            prophet_df["y"]
            .astype(float)
            .replace([np.inf, -np.inf], np.nan)
            .ffill()
            .bfill()
        )

        prophet_df["y"] = prophet_df["y"].clip(
            lower=prophet_df["y"].quantile(0.01),
            upper=prophet_df["y"].quantile(0.99),
        )

        return prophet_df.dropna().reset_index(drop=True)

    # =====================================================
    # TRAIN
    # =====================================================
    def fit(self, df):

        logger.info(" Prophet training started")

        df = self._clean_dataframe(df)
        df = df[["date", "rate"]].copy()
        df = df.rename(columns={"date": "ds", "rate": "y"})
        df = df.sort_values("ds")

        if len(df) < 100:
            raise ValueError("Not enough data for Prophet")

        self.last_date = df["ds"].iloc[-1]

        eval_size = min(60, int(len(df) * 0.1))

        train_df = df[:-eval_size]
        test_df = df[-eval_size:]

        eval_model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=False,
            changepoint_prior_scale=0.05
        )

        eval_model.fit(train_df)

        future = eval_model.make_future_dataframe(
            periods=eval_size,
            freq="B"
        )

        forecast = eval_model.predict(future)

        preds = forecast["yhat"].tail(eval_size).values
        actual = test_df["y"].values

        self.metrics = compute_all_metrics(actual, preds)

        # retrain full model
        self.model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=False,
            changepoint_prior_scale=0.05
        )
        self.model.fit(df)

        self.is_fitted = True

        logger.info(" Prophet training complete")

    # =====================================================
    # FORECAST
    # =====================================================
    def predict(self, horizon):

        if not self.is_fitted:
            raise RuntimeError("Prophet model not fitted")

        horizon = int(horizon)

        future = self.model.make_future_dataframe(
            periods=horizon,
            freq="B"
        )

        forecast = self.model.predict(future)
        forecast = forecast.tail(horizon)

        dates = forecast["ds"].tolist()
        predicted = forecast["yhat"].values
        lower = forecast["yhat_lower"].values
        upper = forecast["yhat_upper"].values

        return {
            "dates": dates,
            "predicted": predicted,
            "lower": lower,
            "upper": upper
        }

    # =====================================================
    # SAVE / LOAD
    # =====================================================
    def save(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)

        with open(path, "wb") as f:
            pickle.dump({
                "model": self.model,
                "last_date": self.last_date,
                "metrics": self.metrics,
            }, f)

        logger.info(f"✅ Prophet saved → {path}")

    def load(self, path):
        with open(path, "rb") as f:
            data = pickle.load(f)

        self.model = data["model"]
        self.last_date = data["last_date"]
        self.metrics = data["metrics"]
        self.is_fitted = True

        logger.info(f"✅ Prophet loaded ← {path}")