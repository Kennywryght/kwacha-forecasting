"""Ensemble model combining multiple forecasters.

This module provides an ensemble forecaster that combines predictions
from multiple base models using weighted averaging.
"""

import os
import pickle
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from ml.models.base_model import BaseForecaster
from core.logging_config import get_logger

logger = get_logger(__name__)


class EnsembleForecaster(BaseForecaster):
    """
    Ensemble forecaster combining multiple models.

    Features:
    - Weighted averaging based on validation performance
    - Robust to model failures
    - Dynamic weighting
    - Automatic model selection
    """

    def __init__(
        self,
        models: Dict[str, BaseForecaster],
        weights: Optional[Dict[str, float]] = None,
        weighting_scheme: str = "rmse",  # "rmse", "mae", "equal"
        min_weight: float = 0.05,
        max_models: int = 5
    ):
        """
        Initialize ensemble forecaster.

        Args:
            models: Dictionary of {name: model} to ensemble
            weights: Pre-defined weights (optional)
            weighting_scheme: How to compute weights
            min_weight: Minimum weight for any model
            max_models: Maximum number of models to include
        """
        super().__init__("ensemble")

        self.models = models
        self.weights = weights or {}
        self.weighting_scheme = weighting_scheme
        self.min_weight = min_weight
        self.max_models = max_models

        self.active_models = {}
        self.metrics = {}

    # ============================================================
    # Core Methods
    # ============================================================

    def _get_valid_models(self) -> Dict[str, BaseForecaster]:
        """
        Filter to only valid, fitted models.

        Returns:
            Dictionary of valid models
        """
        valid = {}

        for name, model in self.models.items():
            try:
                if model is None:
                    continue

                # Handle both dict-style models and object-style models
                if isinstance(model, dict):
                    if not model.get("is_fitted", False):
                        continue
                    if "predict" not in model and "model" not in model:
                        continue
                else:
                    if not hasattr(model, "is_fitted"):
                        continue
                    if not model.is_fitted:
                        continue
                    if not hasattr(model, "predict"):
                        continue

                valid[name] = model

            except Exception as e:
                logger.warning(f"Model {name} validation failed: {e}")
                continue

        return valid

    def _compute_weights(self) -> Dict[str, float]:
        """
        Compute weights based on validation metrics.

        Returns:
            Dictionary of {model_name: weight}
        """
        valid_models = self._get_valid_models()

        if not valid_models:
            raise ValueError("No valid models available for weighting")

        if self.weights and all(k in valid_models for k in self.weights):
            # Use provided weights
            total = sum(self.weights.values())
            if total > 0:
                return {k: v / total for k, v in self.weights.items() if k in valid_models}

        # Compute weights from metrics
        if self.weighting_scheme == "equal":
            n = len(valid_models)
            return {name: 1.0 / n for name in valid_models}

        # Get scores for each model
        scores = {}

        for name, model in valid_models.items():
            if isinstance(model, dict):
                # Dict-style model
                rmse = model.get("metrics", {}).get("rmse", 999)
                mae = model.get("metrics", {}).get("mae", 999)
                mape = model.get("metrics", {}).get("mape", 999)
            else:
                # Object-style model
                rmse = model._safe_metric("rmse", 999)
                mae = model._safe_metric("mae", 999)
                mape = model._safe_metric("mape", 999)

            if self.weighting_scheme == "rmse":
                score = 1.0 / max(rmse, 0.001)
            elif self.weighting_scheme == "mae":
                score = 1.0 / max(mae, 0.001)
            elif self.weighting_scheme == "mape":
                score = 1.0 / max(mape, 0.001)
            else:
                score = 1.0

            scores[name] = score

        # Normalize weights
        total_score = sum(scores.values())

        if total_score <= 0:
            # Fallback to equal weights
            n = len(valid_models)
            return {name: 1.0 / n for name in valid_models}

        weights = {}
        for name, score in scores.items():
            weight = score / total_score
            # Apply minimum weight
            if weight < self.min_weight and len(valid_models) > 1:
                weight = self.min_weight
            weights[name] = weight

        # Re-normalize after applying min weight
        total = sum(weights.values())
        if total > 0:
            weights = {k: v / total for k, v in weights.items()}

        return weights

    def fit(self, df: Optional[pd.DataFrame] = None) -> None:
        """
        Fit the ensemble (compute weights).

        Args:
            df: Training data (optional)
        """
        logger.info("🚀 Ensemble training started")

        valid_models = self._get_valid_models()

        if not valid_models:
            raise ValueError("No valid trained models available for ensemble")

        # Compute weights
        self.weights = self._compute_weights()
        self.active_models = {k: valid_models[k] for k in self.weights}

        self.is_fitted = True

        logger.info(f"✅ Ensemble fitted with weights: {self.weights}")

    def predict(self, horizon: int) -> Dict[str, Any]:
        """
        Generate ensemble forecast by combining all active models.

        Args:
            horizon: Number of days to forecast

        Returns:
            Dictionary with dates, predictions, and confidence intervals
        """
        if not self.is_fitted:
            raise RuntimeError("Ensemble model not fitted")

        if not self.active_models:
            raise RuntimeError("No active models available")

        # Collect forecasts from each model
        forecasts = {}
        for name, model in self.active_models.items():
            try:
                if isinstance(model, dict):
                    # Dict-style model (xgboost, lightgbm)
                    from api.routes.forecasts import _predict_ml_model
                    pred = _predict_ml_model(model, horizon)
                else:
                    # Object-style model (arima, arimax, prophet)
                    pred = model.predict(horizon)
                forecasts[name] = pred
            except Exception as e:
                logger.warning(f"{name} forecast failed: {e}")

        if not forecasts:
            raise RuntimeError("All ensemble models failed to forecast")

        # Use first model's dates
        first_model = list(forecasts.keys())[0]
        dates = forecasts[first_model]["dates"]

        # Get weights for models that succeeded
        active_weights = {
            name: self.weights.get(name, 0)
            for name in forecasts
        }

        # Re-normalize weights
        total_weight = sum(active_weights.values())
        if total_weight <= 0:
            n = len(forecasts)
            active_weights = {name: 1.0 / n for name in forecasts}
        else:
            active_weights = {k: v / total_weight for k, v in active_weights.items()}

        # Initialize arrays
        blended_pred = np.zeros(horizon)
        blended_lower = np.zeros(horizon)
        blended_upper = np.zeros(horizon)

        # Blend predictions using weights
        for name, forecast in forecasts.items():
            weight = active_weights.get(name, 0)

            if "predicted" in forecast:
                preds = np.array(forecast["predicted"][:horizon])
                blended_pred[:len(preds)] += preds * weight

            if "lower_bound" in forecast:
                lowers = np.array(forecast["lower_bound"][:horizon])
                blended_lower[:len(lowers)] += lowers * weight
            elif "lower" in forecast:
                lowers = np.array(forecast["lower"][:horizon])
                blended_lower[:len(lowers)] += lowers * weight

            if "upper_bound" in forecast:
                uppers = np.array(forecast["upper_bound"][:horizon])
                blended_upper[:len(uppers)] += uppers * weight
            elif "upper" in forecast:
                uppers = np.array(forecast["upper"][:horizon])
                blended_upper[:len(uppers)] += uppers * weight

        # If no confidence intervals, estimate from ensemble spread
        if np.all(blended_lower == 0) or np.all(blended_upper == 0):
            pred_arrays = [np.array(f["predicted"][:horizon]) for f in forecasts.values()]
            std_dev = np.std(pred_arrays, axis=0)
            blended_lower = blended_pred - 1.96 * std_dev
            blended_upper = blended_pred + 1.96 * std_dev

        return self._format_forecast_output(
            dates[:horizon],
            blended_pred.tolist(),
            blended_lower.tolist(),
            blended_upper.tolist()
        )

    # ============================================================
    # Model Persistence
    # ============================================================

    def save(self, path: str) -> None:
        """Save the ensemble model to disk."""
        os.makedirs(os.path.dirname(path), exist_ok=True)

        metadata = {
            "name": self.name,
            "weights": self.weights,
            "weighting_scheme": self.weighting_scheme,
            "min_weight": self.min_weight,
            "max_models": self.max_models,
            "metrics": self.metrics,
            "is_fitted": self.is_fitted,
            "model_version": self.model_version,
            "creation_time": self.creation_time,
            "active_models": list(self.active_models.keys())
        }

        with open(path, "wb") as f:
            pickle.dump({
                "metadata": metadata,
                "models": self.models,
                "weights": self.weights
            }, f)

        logger.info(f"✅ Ensemble saved to {path}")

    def load(self, path: str) -> None:
        """Load the ensemble model from disk."""
        with open(path, "rb") as f:
            data = pickle.load(f)

        metadata = data.get("metadata", {})
        for key, value in metadata.items():
            if hasattr(self, key):
                setattr(self, key, value)

        # Restore models
        self.models = data.get("models", {})
        self.weights = data.get("weights", {})

        # Validate and set active models
        self.active_models = self._get_valid_models()

        # Mark as fitted only if we have valid models
        if self.active_models:
            self.is_fitted = True
            logger.info(f"✅ Ensemble loaded from {path} ({len(self.active_models)} active models)")
        else:
            self.is_fitted = False
            logger.warning(f"⚠️ Ensemble loaded but no valid models found")