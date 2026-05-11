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

        self.metrics = {}

    # =====================================================
    # PREPARE DATA
    # =====================================================

    def prepare_data(self, df):

        df = df.copy()

        df["date"] = pd.to_datetime(df["date"])

        df = df.sort_values("date")

        prophet_df = pd.DataFrame()

        prophet_df["ds"] = df["date"]

        prophet_df["y"] = df["rate"].astype(float)

        prophet_df = prophet_df.replace(
            [np.inf, -np.inf],
            np.nan
        )

        prophet_df = prophet_df.ffill().bfill()

        prophet_df = prophet_df.dropna()

        return prophet_df

    # =====================================================
    # TRAIN
    # =====================================================

    def fit(self, df):

        logger.info("🚀 Training Prophet...")

        df = self.prepare_data(df)

        split_idx = int(len(df) * 0.9)

        train_df = df.iloc[:split_idx]

        test_df = df.iloc[split_idx:]

        eval_model = Prophet(
            yearly_seasonality=False,
            weekly_seasonality=False,
            daily_seasonality=False,
            changepoint_prior_scale=0.001
        )

        eval_model.fit(train_df)

        future = eval_model.make_future_dataframe(
            periods=len(test_df),
            freq="D"
        )

        forecast = eval_model.predict(future)

        preds = forecast["yhat"].tail(len(test_df)).values

        actual = test_df["y"].values

        self.metrics = compute_all_metrics(
            actual,
            preds
        )

        # retrain on full data
        self.model = Prophet(
            yearly_seasonality=False,
            weekly_seasonality=False,
            daily_seasonality=False,
            changepoint_prior_scale=0.001
        )

        self.model.fit(df)

        self.is_fitted = True

        logger.info("✅ Prophet training complete")

    # =====================================================
    # PREDICT
    # =====================================================

    def predict(self, horizon):

        if not self.is_fitted:
            raise RuntimeError("Model not fitted")

        future = self.model.make_future_dataframe(
            periods=horizon,
            freq="D"
        )

        forecast = self.model.predict(future)

        forecast = forecast.tail(horizon)

        return {
            "dates": forecast["ds"].tolist(),
            "predicted": forecast["yhat"].tolist(),
            "lower": forecast["yhat_lower"].tolist(),
            "upper": forecast["yhat_upper"].tolist()
        }

    # =====================================================
    # SAVE
    # =====================================================

    def save(self, path):

        os.makedirs(
            os.path.dirname(path),
            exist_ok=True
        )

        with open(path, "wb") as f:

            pickle.dump({
                "model": self.model,
                "metrics": self.metrics
            }, f)

    # =====================================================
    # LOAD
    # =====================================================

    def load(self, path):

        with open(path, "rb") as f:

            data = pickle.load(f)

        self.model = data["model"]

        self.metrics = data["metrics"]

        self.is_fitted = True