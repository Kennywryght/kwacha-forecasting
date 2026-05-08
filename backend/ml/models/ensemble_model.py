import os
import pickle
import numpy as np

from ml.models.base_model import BaseForecaster
from core.logging_config import get_logger

logger = get_logger(__name__)


class EnsembleForecaster(BaseForecaster):

    def __init__(self, models: dict):

        super().__init__("ensemble")

        # dictionary of trained models
        self.models = models

        # learned weights
        self.weights = {}

        self.metrics = {}

    # =====================================================
    # SAFE MODEL FILTER
    # =====================================================
    def _valid_models(self):

        valid = {}

        for name, model in self.models.items():

            try:

                if (
                    model is not None and
                    hasattr(model, "is_fitted") and
                    model.is_fitted
                ):

                    rmse = model._safe_metric("rmse")

                    if rmse < 999:
                        valid[name] = model

            except Exception:
                continue

        return valid

    # =====================================================
    # TRAIN ENSEMBLE
    # =====================================================
    def fit(self, df=None):

        valid_models = self._valid_models()

        if len(valid_models) == 0:
            raise ValueError(
                "No valid trained models available"
            )

        # -------------------------------------------------
        # RMSE-BASED WEIGHTING
        # -------------------------------------------------
        scores = {}

        for name, model in valid_models.items():

            rmse = model._safe_metric("rmse")

            score = 1.0 / max(rmse, 1e-6)

            scores[name] = score

        total_score = sum(scores.values())

        self.weights = {

            name: round(score / total_score, 4)

            for name, score in scores.items()
        }

        logger.info(
            f"✅ Ensemble Weights → {self.weights}"
        )

        # -------------------------------------------------
        # COMBINED METRICS
        # -------------------------------------------------
        self.metrics = {

            "rmse": round(
                sum(
                    self.weights[name] *
                    valid_models[name]._safe_metric("rmse")

                    for name in valid_models
                ),
                4
            ),

            "mae": round(
                sum(
                    self.weights[name] *
                    valid_models[name]._safe_metric("mae")

                    for name in valid_models
                ),
                4
            ),

            "mape": round(
                sum(
                    self.weights[name] *
                    valid_models[name]._safe_metric("mape")

                    for name in valid_models
                ),
                4
            ),

            "r_squared": round(
                max(
                    valid_models[name]._safe_metric(
                        "r_squared",
                        -999
                    )

                    for name in valid_models
                ),
                4
            )
        }

        logger.info(
            f"📊 Ensemble Metrics → {self.metrics}"
        )

        self.is_fitted = True

    # =====================================================
    # FORECAST
    # =====================================================
    def predict(self, horizon):

        if not self.is_fitted:
            raise RuntimeError(
                "Ensemble model not fitted"
            )

        valid_models = self._valid_models()

        if len(valid_models) == 0:
            raise RuntimeError(
                "No valid models available"
            )

        forecasts = {}

        # -------------------------------------------------
        # COLLECT FORECASTS
        # -------------------------------------------------
        for name, model in valid_models.items():

            try:

                pred = model.predict(horizon)

                forecasts[name] = pred

            except Exception as e:

                logger.warning(
                    f"{name} forecast failed: {e}"
                )

        if len(forecasts) == 0:
            raise RuntimeError(
                "All ensemble forecasts failed"
            )

        # -------------------------------------------------
        # USE FIRST MODEL DATES
        # -------------------------------------------------
        first_model = list(forecasts.keys())[0]

        dates = forecasts[first_model]["dates"]

        # -------------------------------------------------
        # BLEND PREDICTIONS
        # -------------------------------------------------
        blended = np.zeros(horizon)

        lower = np.zeros(horizon)

        upper = np.zeros(horizon)

        for name, forecast in forecasts.items():

            weight = self.weights.get(name, 0)

            blended += (
                np.array(forecast["predicted"]) * weight
            )

            lower += (
                np.array(forecast["lower_bound"]) * weight
            )

            upper += (
                np.array(forecast["upper_bound"]) * weight
            )

        return {

            "dates": dates,

            "predicted": list(
                map(float, blended)
            ),

            "lower_bound": list(
                map(float, lower)
            ),

            "upper_bound": list(
                map(float, upper)
            )
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

                "weights": self.weights,
                "metrics": self.metrics

            }, f)

        logger.info(
            f"✅ Ensemble saved → {path}"
        )

    # =====================================================
    # LOAD
    # =====================================================
    def load(self, path):

        with open(path, "rb") as f:

            data = pickle.load(f)

        self.weights = data["weights"]

        self.metrics = data["metrics"]

        self.is_fitted = True

        logger.info(
            f"✅ Ensemble loaded ← {path}"
        )