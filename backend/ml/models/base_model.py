"""Base forecaster class with common functionality for all models.

This module provides the abstract base class that all forecasting models
inherit from, ensuring consistent API and common utilities.
"""

import numpy as np
import pandas as pd
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Union
from datetime import datetime, timedelta
import json
import os


class BaseForecaster(ABC):
    """Abstract base class for all forecasting models."""

    def __init__(self, name: str):
        """
        Initialize the forecaster.

        Args:
            name: Unique identifier for the model
        """
        self.name = name
        self.is_fitted = False
        self.metrics: Dict[str, float] = {}
        self.training_date_range: Optional[tuple] = None
        self.feature_importance: Optional[Dict[str, float]] = None
        self.model_version: str = "1.0.0"
        self.creation_time: str = datetime.now().isoformat()

    # ============================================================
    # Core Abstract Methods
    # ============================================================

    @abstractmethod
    def fit(self, df: pd.DataFrame) -> None:
        """Fit the model on training data."""
        pass

    @abstractmethod
    def predict(self, horizon: int) -> Dict[str, Any]:
        """
        Generate forecasts for a given horizon.

        Args:
            horizon: Number of steps to forecast

        Returns:
            Dictionary with 'dates', 'predicted', 'lower_bound', 'upper_bound'
        """
        pass

    @abstractmethod
    def save(self, path: str) -> None:
        """Save the model to disk."""
        pass

    @abstractmethod
    def load(self, path: str) -> None:
        """Load the model from disk."""
        pass

    # ============================================================
    # Optional Methods (can be overridden)
    # ============================================================

    def refit(self, df: pd.DataFrame) -> None:
        """
        Refit the model on new data (faster than full fit).

        Default implementation calls fit().
        """
        self.fit(df)

    def predict_with_confidence(
        self,
        horizon: int,
        confidence_level: float = 0.95
    ) -> Dict[str, Any]:
        """
        Generate forecasts with confidence intervals.

        Default implementation uses predict() and adds confidence intervals
        based on historical residuals.

        Args:
            horizon: Number of steps to forecast
            confidence_level: Confidence level for intervals (0-1)

        Returns:
            Dictionary with predictions and confidence intervals
        """
        result = self.predict(horizon)

        if "lower_bound" not in result or "upper_bound" not in result:
            if hasattr(self, "_residuals") and len(self._residuals) > 0:
                std_residual = np.std(self._residuals)
                z_score = 1.96
                result["lower_bound"] = [
                    p - z_score * std_residual for p in result["predicted"]
                ]
                result["upper_bound"] = [
                    p + z_score * std_residual for p in result["predicted"]
                ]
            else:
                result["lower_bound"] = [p * 0.95 for p in result["predicted"]]
                result["upper_bound"] = [p * 1.05 for p in result["predicted"]]

        return result

    def evaluate(self, test_df: pd.DataFrame) -> Dict[str, float]:
        """Evaluate the model on test data."""
        from ml.utils.metrics import compute_all_metrics

        result = self.predict(len(test_df))
        y_true = test_df["rate"].values[:len(result["predicted"])]
        self.metrics = compute_all_metrics(y_true, result["predicted"])
        self._residuals = np.array(y_true) - np.array(result["predicted"])

        return self.metrics

    # ============================================================
    # Utility Methods
    # ============================================================

    def _safe_metric(self, key: str, default: float = 999.0) -> float:
        """Safely get a metric value."""
        try:
            if not self.metrics:
                return default
            val = self.metrics.get(key, default)
            if val is None or np.isnan(val) or np.isinf(val):
                return default
            return float(val)
        except Exception:
            return default

    def _generate_dates(
        self,
        start_date: Union[str, pd.Timestamp, datetime],
        horizon: int,
        business_days_only: bool = False
    ) -> List[str]:
        """Generate future dates for forecasting."""
        start = pd.to_datetime(start_date)

        if business_days_only:
            dates = pd.bdate_range(start=start, periods=horizon)
        else:
            dates = pd.date_range(start=start + timedelta(days=1), periods=horizon)

        return [d.strftime("%Y-%m-%d") for d in dates]

    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean and prepare DataFrame for modeling.
        
        FIXED: Only drops rows where essential columns (date, rate) are NaN,
        not the entire DataFrame which would lose all data when macro columns have NaN.
        """
        df = df.copy()

        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")

        df = df.drop_duplicates(subset=["date"] if "date" in df.columns else None)

        # Replace infinities
        df = df.replace([np.inf, -np.inf], np.nan)

        # Sort by date
        if "date" in df.columns:
            df = df.sort_values("date")

        # Forward fill then backward fill (only for essential columns)
        essential_cols = ["rate"]
        for col in essential_cols:
            if col in df.columns:
                df[col] = df[col].ffill().bfill()
        
        # Forward/backward fill other numeric columns (but don't require them)
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if col not in essential_cols:
                df[col] = df[col].ffill().bfill()

        # FIX: Only drop rows where essential columns are NaN
        if "rate" in df.columns:
            df = df.dropna(subset=["rate", "date"])
        else:
            df = df.dropna(subset=["date"])
            
        # For other columns, fill remaining NaN with 0
        df = df.fillna(0)

        return df.reset_index(drop=True)

    def _format_forecast_output(
        self,
        dates: List[Union[str, pd.Timestamp, datetime]],
        predicted: List[float],
        lower_bound: Optional[List[float]] = None,
        upper_bound: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """Format forecast output consistently."""
        date_strings = [
            d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d)
            for d in dates
        ]

        result = {
            "dates": date_strings,
            "predicted": [float(p) for p in predicted],
        }

        if lower_bound is not None:
            result["lower_bound"] = [float(l) for l in lower_bound]

        if upper_bound is not None:
            result["upper_bound"] = [float(u) for u in upper_bound]

        return result

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary for serialization."""
        return {
            "name": self.name,
            "is_fitted": self.is_fitted,
            "metrics": self.metrics,
            "training_date_range": self.training_date_range,
            "model_version": self.model_version,
            "creation_time": self.creation_time,
            "feature_importance": self.feature_importance
        }

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', fitted={self.is_fitted})"
