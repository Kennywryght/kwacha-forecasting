import pandas as pd
import numpy as np
import pickle
import os
import sys
import warnings
warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from ml.models.base_model import BaseForecaster
from ml.utils.metrics import compute_all_metrics
from core.logging_config import get_logger

logger = get_logger(__name__)


class ARIMAForecaster(BaseForecaster):

    def __init__(self):
        super().__init__("arima")
        self.model        = None
        self.fitted_model = None
        self.last_date    = None
        self.order        = None
    
    def _safe_metric(self, key, default=None):
        """
        Safe access to evaluation metrics for ensemble compatibility.
        Prevents ensemble crashes when metric missing.
        """
        try:
            if hasattr(self, "metrics") and self.metrics is not None:
                return self.metrics.get(key, default)
            return default
        except Exception:
            return default
    def fit(self, df: pd.DataFrame) -> None:
        from statsmodels.tsa.arima.model import ARIMA
        from pmdarima import auto_arima

        logger.info("ARIMA: Running auto_arima parameter search...")
        series           = df["rate"].values
        self.last_date   = df["date"].iloc[-1]
        self.train_start = df["date"].iloc[0]
        self.train_end   = df["date"].iloc[-1]

        # Find best order
        auto_result = auto_arima(
            series,
            start_p=0, max_p=4,
            start_q=0, max_q=4,
            d=None,
            seasonal=False,
            information_criterion="aic",
            stepwise=True,
            suppress_warnings=True,
            error_action="ignore",
        )
        self.order = auto_result.order
        logger.info("ARIMA: Best order = " + str(self.order))

        # Fit on full training data
        self.fitted_model = ARIMA(
            series,
            order=self.order,
            enforce_stationarity=False,
            enforce_invertibility=False
        ).fit(method_kwargs={"maxiter": 200})

        # ── Out-of-sample evaluation on last 60 days (ORIGINAL SCALE) ─────────
        # Use walk-forward: train on first n-60, predict next 60 one-step ahead
        eval_size  = min(60, int(len(series) * 0.1))
        train_part = series[:-eval_size]
        test_part  = series[-eval_size:]

        preds = []
        history = list(train_part)
        for i in range(eval_size):
            model_tmp = ARIMA(history, order=self.order)
            fit_tmp   = model_tmp.fit()
            yhat      = fit_tmp.forecast(steps=1)[0]
            preds.append(float(yhat))
            history.append(test_part[i])

        preds  = np.array(preds)
        actual = test_part

        self.metrics = compute_all_metrics(actual, preds)
        logger.info("ARIMA evaluation on ORIGINAL scale (walk-forward " +
                    str(eval_size) + " steps):")
        logger.info("  RMSE=" + str(round(self.metrics["rmse"], 4)) +
                    "  MAE=" + str(round(self.metrics["mae"], 4)) +
                    "  MAPE=" + str(round(self.metrics["mape"], 4)) + "%" +
                    "  R2=" + str(round(self.metrics["r_squared"], 4)))
        self.is_fitted = True

    def predict(self, horizon: int) -> dict:
        if not self.is_fitted:
            raise RuntimeError("ARIMA model not fitted yet.")

        forecast  = self.fitted_model.get_forecast(steps=horizon)
        mean_vals = forecast.predicted_mean
        ci        = forecast.conf_int(alpha=0.05)

        if hasattr(ci, "iloc"):
            lower = ci.iloc[:, 0].values
            upper = ci.iloc[:, 1].values
        elif hasattr(ci, "shape") and len(ci.shape) == 2:
            lower = ci[:, 0]
            upper = ci[:, 1]
        else:
            lower = np.array(mean_vals) * 0.98
            upper = np.array(mean_vals) * 1.02

        dates = self._business_dates(
            self.last_date + pd.Timedelta(days=1), horizon
        )

        return {
            "dates":       [d.strftime("%Y-%m-%d") for d in dates],
            "predicted":   [round(float(v), 2) for v in mean_vals],
            "lower_bound": [round(float(v), 2) for v in lower],
            "upper_bound": [round(float(v), 2) for v in upper],
        }

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump({
                "fitted_model": self.fitted_model,
                "order":        self.order,
                "last_date":    self.last_date,
                "train_start":  self.train_start,
                "train_end":    self.train_end,
                "metrics":      self.metrics,
            }, f)
        logger.info("ARIMA model saved to " + path)

    def load(self, path: str) -> None:
        with open(path, "rb") as f:
            data = pickle.load(f)
        self.fitted_model = data["fitted_model"]
        self.order        = data["order"]
        self.last_date    = data["last_date"]
        self.train_start  = data["train_start"]
        self.train_end    = data["train_end"]
        self.metrics      = data["metrics"]
        self.is_fitted    = True
        logger.info("ARIMA model loaded from " + path)
        
        
