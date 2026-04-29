import pandas as pd
import numpy as np
import pickle
import os
import warnings
warnings.filterwarnings("ignore")

from itertools import product
from ml.models.base_model import BaseForecaster
from ml.utils.metrics import compute_all_metrics
from core.logging_config import get_logger
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.stattools import adfuller

logger = get_logger(__name__)


EXOG_COLS = [
    "momentum_7",
    "momentum_30",
]

P_VALUES = [0, 1, 2]
Q_VALUES = [0, 1, 2]


class ARIMAXForecaster(BaseForecaster):

    def __init__(self, order=(1, 1, 1)):
        super().__init__("arimax")

        self.order = order
        self.model = None
        self.results = None

        self.scaler = StandardScaler()
        self.feature_cols = []
        self.exog_cols = EXOG_COLS

        self.last_date = None
        self.last_exog = None
        self.last_level = None

        self.diff_order = 0
        self.best_p = 0
        self.best_q = 1

    # --------------------------------------------------
    def _check_stationarity(self, y):
        try:
            p = adfuller(y)[1]
            if p > 0.05:
                return 1
        except Exception:
            pass
        return 0

    # --------------------------------------------------
    def _get_target(self, df):
        if "rate" in df.columns:
            return df["rate"]
        elif "usd_mwk" in df.columns:
            return df["usd_mwk"]
        else:
            raise ValueError("Target column not found")

    # --------------------------------------------------
    def _prepare_exog(self, df):
        df = df.copy()

        cols = [c for c in self.exog_cols if c in df.columns]
        if len(cols) == 0:
            raise ValueError("No valid exogenous variables found")

        X = df[cols].copy()
        X = X.apply(pd.to_numeric, errors="coerce")
        X = X.ffill().bfill().fillna(0)
        X = X.clip(lower=X.quantile(0.05), upper=X.quantile(0.95), axis=1)

        return X

    # --------------------------------------------------
    def _fit_sarimax(self, y, X_scaled, d, p=1, q=1, maxiter=500):
        model = SARIMAX(
            y,
            exog=X_scaled,
            order=(p, d, q),
            enforce_stationarity=False,
            enforce_invertibility=False
        )
        try:
            res = model.fit(disp=False, maxiter=maxiter)
            if not res.mle_retvals.get("converged", True):
                res = model.fit(disp=False, maxiter=maxiter, method="powell")
        except Exception:
            res = model.fit(disp=False, maxiter=maxiter, method="powell")
        return res

    # --------------------------------------------------
    def _find_best_order(self, y_trans, X_scaled, d):
        best_bic = np.inf
        best_p, best_q = 0, 1

        for p, q in product(P_VALUES, Q_VALUES):
            if p == 0 and q == 0:
                continue
            try:
                res = SARIMAX(
                    y_trans,
                    exog=X_scaled,
                    order=(p, d, q),
                    enforce_stationarity=False,
                    enforce_invertibility=False
                ).fit(disp=False, maxiter=200)

                if res.bic < best_bic:
                    best_bic = res.bic
                    best_p, best_q = p, q

            except Exception:
                continue

        return best_p, best_q

    # --------------------------------------------------
    def fit(self, df):

        logger.info("ARIMAX: training started")

        # 🚨 CRITICAL DATA FILTER (NEW)
        df = df.copy()
        df = df.sort_values("date")
        df = df[df["date"] >= pd.to_datetime("2013-01-01")]
        df = df[df["date"] <= pd.Timestamp.today()]
        df = df.dropna(subset=["rate"])

        if len(df) < 100:
            raise ValueError("Not enough clean data to train ARIMAX")

        df = df.reset_index(drop=True)

        y = self._get_target(df).astype(float)
        y = y.clip(lower=y.quantile(0.01), upper=y.quantile(0.99))

        self.last_date = df["date"].iloc[-1]
        self.last_level = float(y.iloc[-1])

        self.diff_order = self._check_stationarity(y)
        y_trans = np.diff(y.values) if self.diff_order == 1 else y.values

        X = self._prepare_exog(df)

        if self.diff_order == 1:
            X = X.iloc[1:]

        y_trans = pd.Series(y_trans).reset_index(drop=True)
        X = X.reset_index(drop=True)

        min_len = min(len(X), len(y_trans))
        X = X.iloc[:min_len]
        y_trans = y_trans.iloc[:min_len]

        self.feature_cols = X.columns.tolist()
        X_scaled = self.scaler.fit_transform(X)

        self.best_p, self.best_q = self._find_best_order(
            y_trans, X_scaled, self.diff_order
        )

        self.results = self._fit_sarimax(
            y_trans, X_scaled,
            d=self.diff_order, p=self.best_p, q=self.best_q
        )

        self.last_exog = X_scaled[-1]

        # ---------------- WALK-FORWARD ----------------
        eval_size = min(60, int(len(df) * 0.1))
        train_end = len(df) - eval_size

        preds = []
        current_res = self.results

        for i in range(eval_size):
            idx = train_end + i

            X_next = self._prepare_exog(df.iloc[[idx]])
            X_next_scaled = self.scaler.transform(X_next)

            try:
                pred_diff = current_res.forecast(
                    steps=1,
                    exog=X_next_scaled.reshape(1, -1)
                )[0]
            except Exception:
                pred_diff = float(y_trans.iloc[-1])  # ✅ FIXED BUG

            if self.diff_order == 1:
                prev_level = float(y.iloc[idx - 1])
                pred_level = prev_level + pred_diff
            else:
                pred_level = pred_diff

            preds.append(pred_level)

            # extend state (safe)
            try:
                if self.diff_order == 1:
                    actual_trans = float(
                        y.iloc[idx] - y.iloc[idx - 1]
                    )
                else:
                    actual_trans = float(y.iloc[idx])

                X_obs_scaled = self.scaler.transform(
                    self._prepare_exog(df.iloc[[idx]])
                )

                current_res = current_res.extend(
                    endog=[actual_trans],
                    exog=X_obs_scaled
                )
            except Exception:
                pass

        actual = y.values[-eval_size:]
        preds = np.array(preds)

        self.metrics = compute_all_metrics(actual, preds)

        logger.info(
            f"ARIMAX RMSE={self.metrics['rmse']:.4f} | "
            f"MAE={self.metrics['mae']:.4f} | "
            f"MAPE={self.metrics['mape']:.4f}% | "
            f"R2={self.metrics['r_squared']:.4f}"
        )

        self.is_fitted = True

    # --------------------------------------------------
    def predict(self, horizon, scenario="baseline"):

        if not self.is_fitted:
            raise RuntimeError("ARIMAX not fitted")

        future_exog = np.tile(self.last_exog, (horizon, 1))

        forecast = self.results.get_forecast(
            steps=horizon,
            exog=future_exog
        )

        mean = forecast.predicted_mean.values
        ci = forecast.conf_int()
        lower = ci.iloc[:, 0].values
        upper = ci.iloc[:, 1].values

        if self.diff_order == 1:
            mean  = self.last_level + np.cumsum(mean)
            lower = self.last_level + np.cumsum(lower)
            upper = self.last_level + np.cumsum(upper)

        dates = self._business_dates(
            self.last_date + pd.Timedelta(days=1),
            horizon
        )

        return {
            "dates": [d.strftime("%Y-%m-%d") for d in dates],
            "predicted": list(map(float, mean)),
            "lower_bound": list(map(float, lower)),
            "upper_bound": list(map(float, upper))
        }

    # --------------------------------------------------
    def _safe_metric(self, key, default=999):
        try:
            if self.metrics is None:
                return default
            return self.metrics.get(key, default)
        except Exception:
            return default

    def get_metrics(self):
        return self.metrics if self.metrics is not None else {
            "rmse": 999,
            "mae": 999,
            "mape": 999,
            "r_squared": -999
        }

    # --------------------------------------------------
    def save(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self.__dict__, f)

    def load(self, path):
        with open(path, "rb") as f:
            self.__dict__.update(pickle.load(f))
        self.is_fitted = True