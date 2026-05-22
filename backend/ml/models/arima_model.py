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
        self.fitted_model = None
        self.order = (1, 1, 1)          # will be updated after training
        self.last_date = None
        self.last_value = None
        self.metrics = {}

    # -----------------------------
    def _find_diff_order(self, series):
        try:
            return 1 if adfuller(series)[1] > 0.05 else 0
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
                    model = ARIMA(
                        series,
                        order=(p, d, q),
                        enforce_stationarity=False,
                        enforce_invertibility=False
                    )
                    res = model.fit()

                    if res.aic < best_aic:
                        best_aic = res.aic
                        best_order = (p, d, q)
                except:
                    continue

        return best_order

    # -----------------------------
    def fit(self, df):
        """
        Full training: finds best order, fits model, computes validation metrics.
        """
        logger.info("🚀 ARIMA training started")

        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")

        df = df[df["date"] >= "2013-01-01"]
        df = df.dropna(subset=["rate"])

        if len(df) < 80:
            raise ValueError("Not enough data")

        y = df["rate"].astype(float)
        y = y.ffill().bfill()

        self.last_date = df["date"].iloc[-1]
        self.last_value = float(y.iloc[-1])

        # Find the best order (only during initial training)
        d = self._find_diff_order(y.values)
        self.order = self._find_best_order(y.values, d)

        self.fitted_model = ARIMA(
            y,
            order=self.order,
            enforce_stationarity=False,
            enforce_invertibility=False
        ).fit()

        # ---------------- validation
        eval_size = min(60, int(len(y) * 0.1))
        train, test = y.iloc[:-eval_size], y.iloc[-eval_size:]

        history = list(train.values)
        preds = []

        for actual in test.values:
            try:
                model = ARIMA(history, order=self.order).fit()
                pred = model.forecast(steps=1)[0]
            except:
                pred = history[-1]

            preds.append(float(pred))
            history.append(actual)

        self.metrics = compute_all_metrics(test.values, preds)
        self.is_fitted = True

    # -----------------------------
    def refit(self, df):
        """
        Fast re‑fit on new data using the already‑tuned order.
        Does **not** re‑run order search or validation.
        """
        logger.info("⚡ ARIMA fast refit (using existing order)")

        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")

        df = df[df["date"] >= "2013-01-01"]
        df = df.dropna(subset=["rate"])

        if len(df) < 80:
            raise ValueError("Not enough data")

        y = df["rate"].astype(float)
        y = y.ffill().bfill()

        self.last_date = df["date"].iloc[-1]
        self.last_value = float(y.iloc[-1])

        # Fit directly with the existing order (no search)
        self.fitted_model = ARIMA(
            y,
            order=self.order,
            enforce_stationarity=False,
            enforce_invertibility=False
        ).fit()

        self.is_fitted = True
        # metrics are not updated – keep the old validation metrics

    # -----------------------------
    def predict(self, test_df):
        if not self.is_fitted:
            raise RuntimeError("ARIMA not fitted")

        test_df = test_df.copy()
        test_df["date"] = pd.to_datetime(test_df["date"])
        test_df = test_df.sort_values("date")

        y_true = test_df["rate"].values
        history = list(self.fitted_model.data.endog)
        preds = []

        for actual in y_true:
            try:
                model = ARIMA(history, order=self.order).fit()
                yhat = model.forecast(steps=1)[0]
            except:
                yhat = history[-1]

            preds.append(float(yhat))
            history.append(actual)

        return {
            "y_true": y_true.tolist(),
            "y_pred": preds
        }

    # -----------------------------
    def forecast(self, horizon: int):
        """
        Forecast 'horizon' steps ahead from the last fitted date.
        Returns a dict with keys:
            dates       : list of Python date objects
            predicted   : list of floats
            lower_bound : list of floats (if available)
            upper_bound : list of floats (if available)
        """
        if not self.is_fitted:
            raise RuntimeError("ARIMA not fitted")

        fc = self.fitted_model.get_forecast(steps=horizon)
        pred_mean = fc.predicted_mean
        conf_int = fc.conf_int()

        # conf_int can be DataFrame or numpy array
        if isinstance(conf_int, pd.DataFrame):
            lower = conf_int.iloc[:, 0].tolist()
            upper = conf_int.iloc[:, 1].tolist()
        else:
            lower = conf_int[:, 0].tolist()
            upper = conf_int[:, 1].tolist()

        # Create future dates as Python date objects
        start = pd.Timestamp(self.last_date) + pd.Timedelta(days=1)
        future_dates = [(start + pd.Timedelta(days=i)).date() for i in range(horizon)]

        return {
            "dates": future_dates,
            "predicted": pred_mean.tolist(),
            "lower_bound": lower,
            "upper_bound": upper,
        }

    # -----------------------------
    def save(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self.__dict__, f)

    def load(self, path):
        with open(path, "rb") as f:
            self.__dict__.update(pickle.load(f))
        self.is_fitted = True