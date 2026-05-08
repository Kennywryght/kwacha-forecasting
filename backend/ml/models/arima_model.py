import os
import pickle
import warnings
import numpy as np
import pandas as pd

from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.stattools import adfuller

from ml.models.base_model import BaseForecaster
from ml.utils.metrics import compute_all_metrics
from core.logging_config import get_logger

warnings.filterwarnings("ignore")
logger = get_logger(__name__)


class ARIMAForecaster(BaseForecaster):

    def __init__(self):
        super().__init__("arima")

        self.model = None
        self.fitted_model = None

        self.order = (1, 1, 1)

        self.last_date = None
        self.last_value = None

        self.metrics = {}

    # -----------------------------
    def _find_diff_order(self, series):
        try:
            p_value = adfuller(series)[1]
            return 1 if p_value > 0.05 else 0
        except:
            return 0

    # -----------------------------
    def _find_best_order(self, series, d):
        best_aic = np.inf
        best_order = (1, d, 1)

        for p in [0, 1, 2]:
            for q in [0, 1, 2]:
                if p == 0 and q == 0:
                    continue
                try:
                    model = ARIMA(series, order=(p, d, q))
                    res = model.fit()

                    if res.aic < best_aic:
                        best_aic = res.aic
                        best_order = (p, d, q)
                except:
                    continue

        return best_order

    # -----------------------------
    def fit(self, df):

        logger.info("🚀 ARIMA training started")

        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")

        df = df[df["date"] >= "2013-01-01"]
        df = df.dropna(subset=["rate"])

        if len(df) < 80:
            raise ValueError("Not enough data")

        y = df["rate"].astype(float)
        y = y.ffill().bfill().values

        self.last_date = df["date"].iloc[-1]
        self.last_value = float(y[-1])

        d = self._find_diff_order(y)
        self.order = self._find_best_order(y, d)

        self.fitted_model = ARIMA(
            y,
            order=self.order
        ).fit()

        # ---------------- validation
        eval_size = min(60, int(len(y) * 0.1))
        train, test = y[:-eval_size], y[-eval_size:]

        history = list(train)
        preds = []

        for actual in test:
            try:
                model = ARIMA(history, order=self.order).fit()
                pred = model.forecast(steps=1)[0]
            except:
                pred = history[-1]

            preds.append(pred)
            history.append(actual)

        self.metrics = self._clean_metrics(
            compute_all_metrics(test, preds)
        )

        self.is_fitted = True

    # -----------------------------
    def predict(self, horizon):

        forecast = self.fitted_model.get_forecast(steps=horizon)

        mean = np.array(forecast.predicted_mean)
        ci = forecast.conf_int()

        lower = np.array(ci.iloc[:, 0])
        upper = np.array(ci.iloc[:, 1])

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
            pickle.dump({
                "model": self.fitted_model,
                "order": self.order,
                "metrics": self.metrics,
                "last_date": self.last_date,
                "last_value": self.last_value
            }, f)

    def load(self, path):
        with open(path, "rb") as f:
            data = pickle.load(f)

        self.fitted_model = data["model"]
        self.order = data["order"]
        self.metrics = data["metrics"]
        self.last_date = data["last_date"]
        self.last_value = data["last_value"]

        self.is_fitted = True

    def _clean_metrics(self, metrics):
        return {
            "rmse": float(metrics.get("rmse", np.nan)),
            "mae": float(metrics.get("mae", np.nan)),
            "mape": float(metrics.get("mape", np.nan)),
            "r_squared": float(metrics.get("r_squared", np.nan)),
        }