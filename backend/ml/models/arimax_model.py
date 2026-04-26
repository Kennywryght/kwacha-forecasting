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


# --------------------------------------------------
# EXOG FEATURES
#
# momentum_7:  corr=0.19 with eval diffs, safe (uses rate[t-7])
# momentum_30: corr=0.24 with eval diffs, only 0.48 corr with mom7
#              — genuinely complementary signal
#
# All other candidates eliminated:
#   daily_return:  look-ahead leak (encodes current rate change)
#   lag features:  0.996 mutual corr = multicollinearity
#   macro features: corr < 0.03 with y_diff
#   rolling_mean/std: include current row = look-ahead leak
#   roc_7: 0.978 corr with momentum_7 = redundant
# --------------------------------------------------
EXOG_COLS = [
    "momentum_7",   # rate - rate.shift(7), corr=0.19 with y_diff in eval
    "momentum_30",  # rate - rate.shift(30), corr=0.24 with y_diff in eval
]

# BIC-penalized search — autocorr analysis shows only lag-1 is significant
# so we bias toward simpler orders like (0,1,1) matching ARIMA's structure
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
    # STATIONARITY CHECK
    # --------------------------------------------------
    def _check_stationarity(self, y):
        try:
            p = adfuller(y)[1]
            if p > 0.05:
                logger.debug(f"Non-stationary (p={p:.4f}) → diff=1")
                return 1
        except Exception:
            pass
        return 0

    # --------------------------------------------------
    # PREP TARGET
    # --------------------------------------------------
    def _get_target(self, df):
        if "rate" in df.columns:
            return df["rate"]
        elif "usd_mwk" in df.columns:
            return df["usd_mwk"]
        else:
            raise ValueError("Target column not found (rate/usd_mwk)")

    # --------------------------------------------------
    # CLEAN EXOG
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
    # FIT SARIMAX WITH POWELL FALLBACK
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
                logger.debug(f"Primary optimizer did not converge for ({p},{d},{q}), trying Powell")
                res = model.fit(disp=False, maxiter=maxiter, method="powell")
        except Exception:
            res = model.fit(disp=False, maxiter=maxiter, method="powell")
        return res

    # --------------------------------------------------
    # ORDER SEARCH — use BIC to penalize complexity
    # Autocorrelation analysis shows only lag-1 is significant,
    # so BIC correctly steers toward (0,1,1) over (2,1,2)
    # --------------------------------------------------
    def _find_best_order(self, y_trans, X_scaled, d):
        best_bic = np.inf
        best_p, best_q = 0, 1

        logger.info(f"ARIMAX: searching orders p={P_VALUES} q={Q_VALUES} (BIC)")

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

                # FIX: use BIC not AIC — penalizes extra AR/MA params more strongly
                # prevents overfitting to autocorrelation structure
                if res.bic < best_bic:
                    best_bic = res.bic
                    best_p, best_q = p, q

            except Exception:
                continue

        logger.info(f"ARIMAX: best order=({best_p},{d},{best_q}) BIC={best_bic:.2f}")
        return best_p, best_q

    # --------------------------------------------------
    # FIT
    # --------------------------------------------------
    def fit(self, df):

        logger.info("ARIMAX: training started")

        df = df.copy()
        df = df.sort_values("date").reset_index(drop=True)

        y = self._get_target(df).astype(float)
        y = y.clip(lower=y.quantile(0.01), upper=y.quantile(0.99))

        df = df.loc[y.index].reset_index(drop=True)
        y = y.reset_index(drop=True)

        self.last_date = df["date"].iloc[-1]
        self.last_level = float(y.iloc[-1])

        # Determine diff_order ONCE — locked for entire fit + walk-forward
        self.diff_order = self._check_stationarity(y)
        y_trans = np.diff(y.values) if self.diff_order == 1 else y.values

        # -------------------------
        # EXOG
        # -------------------------
        X = self._prepare_exog(df)

        if self.diff_order == 1:
            X = X.iloc[1:]

        y_trans = pd.Series(y_trans).reset_index(drop=True)
        X = X.reset_index(drop=True)

        min_len = min(len(X), len(y_trans))
        X = X.iloc[:min_len]
        y_trans = y_trans.iloc[:min_len]

        # -------------------------
        # SCALE
        # -------------------------
        self.feature_cols = X.columns.tolist()
        X_scaled = self.scaler.fit_transform(X)

        # -------------------------
        # ORDER SEARCH (BIC)
        # -------------------------
        self.best_p, self.best_q = self._find_best_order(
            y_trans, X_scaled, self.diff_order
        )

        final_p = self.best_p
        final_q = self.best_q
        final_d = self.diff_order

        logger.info(f"ARIMAX: fitting final model with order=({final_p},{final_d},{final_q})")

        self.results = self._fit_sarimax(
            y_trans, X_scaled,
            d=final_d, p=final_p, q=final_q
        )

        self.last_exog = X_scaled[-1]

        # -------------------------
        # WALK-FORWARD VALIDATION using extend()
        #
        # extend() correctly propagates the Kalman filter state after
        # each observed value — this preserves the MA error-correction
        # mechanism that makes ARIMA(0,1,1) so effective.
        #
        # FIX: level inversion now uses the actual observed level at each
        # step, not train_end-1, eliminating the off-by-one gap.
        # -------------------------
        eval_size = min(60, int(len(df) * 0.1))
        train_end = len(df) - eval_size

        # Fit base model on training window only
        train_window = df.iloc[:train_end].copy()

        y_train = self._get_target(train_window).astype(float)
        y_train = y_train.clip(y_train.quantile(0.01), y_train.quantile(0.99))
        y_train = y_train.reset_index(drop=True)

        y_train_trans = np.diff(y_train.values) if final_d == 1 else y_train.values

        X_train = self._prepare_exog(train_window)
        if final_d == 1:
            X_train = X_train.iloc[1:]

        X_train = X_train.reset_index(drop=True)
        min_len = min(len(X_train), len(y_train_trans))
        X_train = X_train.iloc[:min_len]
        y_train_trans = y_train_trans[:min_len]
        X_train_scaled = self.scaler.transform(X_train)

        try:
            base_res = self._fit_sarimax(
                y_train_trans, X_train_scaled,
                d=final_d, p=final_p, q=final_q,
                maxiter=300
            )
        except Exception:
            base_res = self.results

        # Roll forward one step at a time
        preds = []
        current_res = base_res

        for i in range(eval_size):
            idx = train_end + i

            # Exog for the step we are about to forecast
            X_next = self._prepare_exog(df.iloc[[idx]])
            X_next_scaled = self.scaler.transform(X_next)

            try:
                pred_diff = current_res.forecast(
                    steps=1,
                    exog=X_next_scaled.reshape(1, -1)
                )[0]
            except Exception:
                pred_diff = float(y_diff[-1]) if final_d == 1 else float(y.iloc[idx - 1])

            # FIX: use actual observed level at current step for inversion
            # not a fixed train_end anchor — eliminates level drift
            if final_d == 1:
                actual_prev_level = float(self._get_target(df).iloc[idx - 1])
                pred_level = actual_prev_level + pred_diff
            else:
                pred_level = pred_diff

            preds.append(pred_level)

            # Extend model with actual observed value — preserves error correction
            try:
                if final_d == 1:
                    actual_trans = float(
                        self._get_target(df).iloc[idx] - self._get_target(df).iloc[idx - 1]
                    )
                else:
                    actual_trans = float(self._get_target(df).iloc[idx])

                X_obs_scaled = self.scaler.transform(
                    self._prepare_exog(df.iloc[[idx]])
                )
                current_res = current_res.extend(
                    endog=[actual_trans],
                    exog=X_obs_scaled
                )
            except Exception:
                pass  # keep current_res if extend fails

        actual = self._get_target(df).values[-eval_size:]
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
    # PREDICT
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
    # COMPATIBILITY HELPERS
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
    # SAVE / LOAD
    # --------------------------------------------------
    def save(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self.__dict__, f)

    def load(self, path):
        with open(path, "rb") as f:
            self.__dict__.update(pickle.load(f))
        self.is_fitted = True