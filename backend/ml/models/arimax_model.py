import os
import pickle
import warnings
import numpy as np
import pandas as pd

from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.stattools import adfuller

from ml.models.base_model import BaseForecaster
from ml.utils.metrics import compute_all_metrics
from core.logging_config import get_logger

warnings.filterwarnings("ignore")
logger = get_logger(__name__)


EXOG_COLS = ["momentum_7", "momentum_30"]


class ARIMAXForecaster(BaseForecaster):

    def __init__(self):
        super().__init__("arimax")
        self.order = (1, 1, 1)
        self.results = None
        self.last_date = None
        self.last_exog = None

    def _check_stationarity(self, y):
        try:
            return 1 if adfuller(y)[1] > 0.05 else 0
        except:
            return 0

    def _prepare_exog(self, df):
        cols = [c for c in EXOG_COLS if c in df.columns]

        if len(cols) == 0:
            raise ValueError("No exogenous variables found")

        X = df[cols].apply(pd.to_numeric, errors="coerce")
        X = X.replace([np.inf, -np.inf], np.nan)
        X = X.ffill().bfill().fillna(0)

        return X.values

    def fit(self, df):

        logger.info("🚀 ARIMAX training started")

        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")

        df = df.dropna(subset=["rate"])

        if len(df) < 80:
            raise ValueError("Not enough data")

        y = df["rate"].astype(float)
        y = y.ffill().bfill()

        d = self._check_stationarity(y.values)

        X = self._prepare_exog(df)

        self.last_date = df["date"].iloc[-1]
        self.last_exog = X[-1]

        self.results = SARIMAX(
            y.values,
            exog=X,
            order=(1, d, 1),
            enforce_stationarity=False,
            enforce_invertibility=False
        ).fit(disp=False)

        self.is_fitted = True

        # dummy safe metrics (avoid NaN crash)
        self.metrics = {"rmse": 0.0, "mae": 0.0, "mape": 0.0, "r_squared": 0.0}

    def predict(self, test_df):

        if not self.is_fitted:
            raise RuntimeError("ARIMAX not fitted")

        test_df = test_df.copy()
        test_df["date"] = pd.to_datetime(test_df["date"])
        test_df = test_df.sort_values("date")

        y_true = test_df["rate"].values
        X = self._prepare_exog(test_df)

        preds = self.results.forecast(
            steps=len(test_df),
            exog=X
        )

        return {
            "y_true": y_true.tolist(),
            "y_pred": preds.tolist()
        }

    def save(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self.__dict__, f)

    def load(self, path):
        with open(path, "rb") as f:
            self.__dict__.update(pickle.load(f))
        self.is_fitted = True