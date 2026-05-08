import pandas as pd
import numpy as np
import pickle
import os
import warnings

from sklearn.preprocessing import StandardScaler
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

        self.results = None
        self.scaler = StandardScaler()

        self.exog_cols = EXOG_COLS

        self.last_date = None
        self.last_level = None

        self.diff_order = 0
        self.best_order = (1, 1, 1)

        self.metrics = {}

    # -----------------------------
    def _stationary(self, y):
        try:
            return 1 if adfuller(y)[1] > 0.05 else 0
        except:
            return 0

    # -----------------------------
    def _prepare_exog(self, df):

        cols = [c for c in self.exog_cols if c in df.columns]
        if not cols:
            raise ValueError("No exogenous features found")

        X = df[cols].copy()
        X = X.apply(pd.to_numeric, errors="coerce")

        X = X.replace([np.inf, -np.inf], np.nan)
        X = X.ffill().bfill().fillna(0)

        return X.values  # IMPORTANT FIX

    # -----------------------------
    def fit(self, df):

        logger.info("🚀 ARIMAX training started")

        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")

        df = df[df["date"] >= "2013-01-01"]
        df = df.dropna(subset=["rate"])

        if len(df) < 100:
            raise ValueError("Not enough data")

        y = df["rate"].astype(float).ffill().bfill().values

        self.last_date = df["date"].iloc[-1]
        self.last_level = float(y[-1])

        self.diff_order = self._stationary(y)
        y_trans = np.diff(y) if self.diff_order else y

        X = self._prepare_exog(df)

        if self.diff_order:
            X = X[1:]

        min_len = min(len(X), len(y_trans))
        X, y_trans = X[:min_len], y_trans[:min_len]

        self.scaler.fit(X)
        X_scaled = self.scaler.transform(X)

        self.results = SARIMAX(
            y_trans,
            exog=X_scaled,
            order=self.best_order,
            enforce_stationarity=False,
            enforce_invertibility=False
        ).fit(disp=False)

        # validation
        eval_size = min(60, int(len(y) * 0.1))
        preds = []

        for i in range(eval_size):
            idx = len(y) - eval_size + i

            X_next = self.scaler.transform(
                self._prepare_exog(df.iloc[[idx]])
            )

            try:
                pred = self.results.forecast(steps=1, exog=X_next.reshape(1, -1))[0]
            except:
                pred = y_trans[-1]

            if self.diff_order:
                pred = y[idx - 1] + pred

            preds.append(pred)

        actual = y[-eval_size:]

        self.metrics = compute_all_metrics(actual, preds)
        self.is_fitted = True

    # -----------------------------
    def predict(self, horizon):

        future_exog = np.tile(self.last_level, (horizon, len(self.exog_cols)))

        forecast = self.results.get_forecast(
            steps=horizon,
            exog=future_exog
        )

        mean = forecast.predicted_mean
        ci = forecast.conf_int()

        lower = ci.iloc[:, 0].values
        upper = ci.iloc[:, 1].values

        dates = self._business_dates(
            self.last_date + pd.Timedelta(days=1),
            horizon
        )

        return {
            "dates": [d.strftime("%Y-%m-%d") for d in dates],
            "predicted": mean.tolist(),
            "lower_bound": lower.tolist(),
            "upper_bound": upper.tolist(),
        }

    # -----------------------------
    def save(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)

        with open(path, "wb") as f:
            pickle.dump(self.results, f)

    def load(self, path):
        with open(path, "rb") as f:
            self.results = pickle.load(f)

        self.is_fitted = True