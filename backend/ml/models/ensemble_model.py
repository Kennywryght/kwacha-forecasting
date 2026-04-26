import pandas as pd
import numpy as np
import pickle
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from ml.models.base_model import BaseForecaster
from core.logging_config import get_logger

logger = get_logger(__name__)


class EnsembleForecaster(BaseForecaster):
    """
    Improved Ensemble (SAFE STACKING APPROACH)

    Programmer notes:
    - Replaces MAPE weighting (unstable)
    - Uses RMSE-based inverse weighting (more reliable)
    - Ensures normalization stability
    """

    def __init__(self, arima, arimax):
        super().__init__("ensemble")

        self.arima = arima
        self.arimax = arimax

        # default weights (will be overwritten in fit)
        self.weights = {"arima": 0.5, "arimax": 0.5}

    # ---------------------------------------------------------
    # FIXED: more stable weight learning
    # ---------------------------------------------------------
    def fit(self, df: pd.DataFrame) -> None:

        # -------------------------------
        # Extract RMSE safely
        # -------------------------------
        arima_rmse = self.arima._safe_metric("rmse", 999)
        arimax_rmse = self.arimax._safe_metric("rmse", 999)

        # Programmer note:
        # Lower RMSE = better model = higher weight
        arima_score = 1.0 / max(arima_rmse, 1e-6)
        arimax_score = 1.0 / max(arimax_rmse, 1e-6)

        total = arima_score + arimax_score

        # normalize weights
        self.weights = {
            "arima": round(arima_score / total, 4),
            "arimax": round(arimax_score / total, 4),
        }

        logger.info(
            f"[ENSEMBLE WEIGHTS] ARIMA={self.weights['arima']} | ARIMAX={self.weights['arimax']}"
        )

        # ---------------------------------------
        # Combined metrics (weighted performance)
        # ---------------------------------------
        self.metrics = {
            "rmse": round(
                self.weights["arima"] * arima_rmse +
                self.weights["arimax"] * arimax_rmse,
                4
            ),
            "mae": round(
                self.weights["arima"] * self.arima._safe_metric("mae") +
                self.weights["arimax"] * self.arimax._safe_metric("mae"),
                4
            ),
            "mape": round(
                self.weights["arima"] * self.arima._safe_metric("mape") +
                self.weights["arimax"] * self.arimax._safe_metric("mape"),
                4
            ),
            "r_squared": round(
                max(
                    self.arima._safe_metric("r_squared"),
                    self.arimax._safe_metric("r_squared")
                ),
                4
            ),
        }

        self.is_fitted = True

    # ---------------------------------------------------------
    # FIXED: safer blending + numerical stability
    # ---------------------------------------------------------
    def predict(self, horizon: int) -> dict:

        a_pred = self.arima.predict(horizon)
        x_pred = self.arimax.predict(horizon)

        wa = self.weights["arima"]
        wx = self.weights["arimax"]

        # -------------------------------
        # Core forecast blend
        # -------------------------------
        blended = [
            round(wa * a + wx * x, 2)
            for a, x in zip(a_pred["predicted"], x_pred["predicted"])
        ]

        # -------------------------------
        # Uncertainty blending (better consistency)
        # -------------------------------
        lower = [
            round(wa * a + wx * x, 2)
            for a, x in zip(a_pred["lower_bound"], x_pred["lower_bound"])
        ]

        upper = [
            round(wa * a + wx * x, 2)
            for a, x in zip(a_pred["upper_bound"], x_pred["upper_bound"])
        ]

        return {
            "dates": a_pred["dates"],
            "predicted": blended,
            "lower_bound": lower,
            "upper_bound": upper,
        }

    # ---------------------------------------------------------
    # SAVE (unchanged but stable)
    # ---------------------------------------------------------
    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)

        with open(path, "wb") as f:
            pickle.dump({
                "weights": self.weights,
                "metrics": self.metrics
            }, f)

        logger.info(f"Ensemble saved → {path}")

    def load(self, path: str) -> None:
        with open(path, "rb") as f:
            data = pickle.load(f)

        self.weights = data["weights"]
        self.metrics = data["metrics"]
        self.is_fitted = True

        logger.info(f"Ensemble loaded → {path}")