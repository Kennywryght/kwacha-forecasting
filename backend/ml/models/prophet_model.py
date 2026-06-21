"""Prophet model implementation for time series forecasting.

This module provides a Prophet-based forecaster with:
- Automatic seasonality detection
- Changepoint detection
- Holiday effects
- Confidence intervals
"""

import os
import pickle
import joblib
import warnings
import numpy as np
import pandas as pd
from typing import Optional, Dict, Any, List
from datetime import datetime

from prophet import Prophet
from prophet.diagnostics import cross_validation, performance_metrics

from ml.models.base_model import BaseForecaster
from ml.utils.metrics import compute_all_metrics
from core.logging_config import get_logger

warnings.filterwarnings("ignore")
logger = get_logger(__name__)


class ProphetForecaster(BaseForecaster):
    """
    Prophet model for time series forecasting.

    Features:
    - Automatic seasonality detection
    - Changepoint detection
    - Holiday effects
    - Uncertainty intervals
    - Cross-validation support
    """

    def __init__(
        self,
        yearly_seasonality: bool = False,
        weekly_seasonality: bool = True,
        daily_seasonality: bool = False,
        changepoint_prior_scale: float = 0.05,
        seasonality_prior_scale: float = 10.0,
        holidays_prior_scale: float = 10.0,
        changepoint_range: float = 0.8,
        n_changepoints: int = 25,
        uncertainty_samples: int = 1000
    ):
        """
        Initialize Prophet forecaster.

        Args:
            yearly_seasonality: Whether to include yearly seasonality
            weekly_seasonality: Whether to include weekly seasonality
            daily_seasonality: Whether to include daily seasonality
            changepoint_prior_scale: Flexibility of trend changes
            seasonality_prior_scale: Strength of seasonality
            holidays_prior_scale: Strength of holiday effects
            changepoint_range: Proportion of history for changepoints
            n_changepoints: Number of potential changepoints
            uncertainty_samples: Number of uncertainty samples
        """
        super().__init__("prophet")

        self.yearly_seasonality = yearly_seasonality
        self.weekly_seasonality = weekly_seasonality
        self.daily_seasonality = daily_seasonality
        self.changepoint_prior_scale = changepoint_prior_scale
        self.seasonality_prior_scale = seasonality_prior_scale
        self.holidays_prior_scale = holidays_prior_scale
        self.changepoint_range = changepoint_range
        self.n_changepoints = n_changepoints
        self.uncertainty_samples = uncertainty_samples

        self.model = None
        self.last_date = None
        self.train_df = None

    # ============================================================
    # Core Methods
    # ============================================================

    def _prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare data for Prophet.

        Args:
            df: Input DataFrame

        Returns:
            DataFrame with 'ds' and 'y' columns
        """
        df = self._clean_dataframe(df)

        if "date" not in df.columns:
            raise ValueError("DataFrame must contain 'date' column")

        df = df.sort_values("date")
        df = df.dropna(subset=["rate"])

        if len(df) < 30:
            raise ValueError(f"Not enough data: {len(df)} rows (need at least 30)")

        prophet_df = pd.DataFrame({
            "ds": df["date"],
            "y": df["rate"].astype(float)
        })

        prophet_df = prophet_df.dropna()
        self.last_date = df["date"].iloc[-1]

        self.training_start = df["date"].iloc[0]
        self.training_end = df["date"].iloc[-1]
        self.training_date_range = (self.training_start, self.training_end)

        self.train_df = prophet_df
        return prophet_df

    def _create_model(self) -> Prophet:
        """
        Create a Prophet model with configured parameters.

        Returns:
            Configured Prophet model
        """
        return Prophet(
            yearly_seasonality=self.yearly_seasonality,
            weekly_seasonality=self.weekly_seasonality,
            daily_seasonality=self.daily_seasonality,
            changepoint_prior_scale=self.changepoint_prior_scale,
            seasonality_prior_scale=self.seasonality_prior_scale,
            holidays_prior_scale=self.holidays_prior_scale,
            changepoint_range=self.changepoint_range,
            n_changepoints=self.n_changepoints,
            uncertainty_samples=self.uncertainty_samples
        )

    def fit(self, df: pd.DataFrame) -> None:
        """
        Fit Prophet model.

        Args:
            df: DataFrame with 'date' and 'rate' columns
        """
        logger.info("🚀 Prophet training started")

        prophet_df = self._prepare_data(df)

        # Split for validation
        split_idx = int(len(prophet_df) * 0.85)
        train_df = prophet_df.iloc[:split_idx]
        test_df = prophet_df.iloc[split_idx:]

        # Train on full data
        self.model = self._create_model()
        self.model.fit(prophet_df)

        self.is_fitted = True
        logger.info(f"✅ Prophet training complete ({len(prophet_df)} rows)")

    def refit(self, df: pd.DataFrame) -> None:
        """
        Refit the model on new data.

        Args:
            df: DataFrame with new data
        """
        logger.info("⚡ Prophet refit")

        prophet_df = self._prepare_data(df)

        self.model = self._create_model()
        self.model.fit(prophet_df)

        self.is_fitted = True
        logger.info("✅ Prophet refit complete")

    def predict(self, horizon: int) -> Dict[str, Any]:
        """
        Generate forecasts for a given horizon.

        Args:
            horizon: Number of days to forecast

        Returns:
            Dictionary with dates, predictions, and confidence intervals
        """
        if not self.is_fitted or self.model is None:
            raise RuntimeError("Prophet model not fitted")

        try:
            future = self.model.make_future_dataframe(
                periods=horizon,
                freq="D",
                include_history=False
            )

            forecast = self.model.predict(future)

            # Extract predictions
            predicted = forecast["yhat"].values
            lower = forecast["yhat_lower"].values
            upper = forecast["yhat_upper"].values

            dates = forecast["ds"].dt.strftime("%Y-%m-%d").tolist()

            return self._format_forecast_output(dates, predicted, lower, upper)

        except Exception as e:
            logger.error(f"Prophet prediction failed: {e}")
            raise

    def cross_validate(
        self,
        horizon: int = 30,
        initial: int = 365,
        period: int = 30
    ) -> pd.DataFrame:
        """
        Perform cross-validation on the model.

        Args:
            horizon: Forecast horizon
            initial: Initial training period (days)
            period: Period between cutoffs (days)

        Returns:
            DataFrame with cross-validation results
        """
        if not self.is_fitted or self.model is None:
            raise RuntimeError("Prophet model not fitted")

        if self.train_df is None:
            raise ValueError("No training data available")

        try:
            df_cv = cross_validation(
                self.model,
                horizon=f"{horizon} days",
                initial=f"{initial} days",
                period=f"{period} days"
            )

            df_metrics = performance_metrics(df_cv)

            logger.info(f"✅ Cross-validation complete: {len(df_cv)} predictions")
            return df_metrics

        except Exception as e:
            logger.warning(f"Cross-validation failed: {e}")
            return pd.DataFrame()

    def get_changepoints(self) -> List[pd.Timestamp]:
        """
        Get detected changepoints.

        Returns:
            List of changepoint dates
        """
        if not self.is_fitted or self.model is None:
            return []

        try:
            changepoints = self.model.changepoints
            return changepoints.tolist() if changepoints is not None else []
        except Exception:
            return []

    def get_seasonality_components(self) -> Dict[str, pd.Series]:
        """
        Extract seasonality components from the model.

        Returns:
            Dictionary of seasonality components
        """
        if not self.is_fitted or self.model is None:
            return {}

        try:
            # Create future dataframe for a full year
            future = self.model.make_future_dataframe(
                periods=365,
                freq="D",
                include_history=False
            )
            forecast = self.model.predict(future)

            components = {}
            for col in forecast.columns:
                if col.startswith("yearly") or col.startswith("weekly"):
                    components[col] = forecast[col]

            return components

        except Exception as e:
            logger.warning(f"Failed to extract seasonality: {e}")
            return {}

    # ============================================================
    # Model Persistence
    # ============================================================

    def save(self, path: str) -> None:
        """Save the model to disk using joblib."""
        os.makedirs(os.path.dirname(path), exist_ok=True)

        metadata = {
            "name": self.name,
            "yearly_seasonality": self.yearly_seasonality,
            "weekly_seasonality": self.weekly_seasonality,
            "daily_seasonality": self.daily_seasonality,
            "changepoint_prior_scale": self.changepoint_prior_scale,
            "seasonality_prior_scale": self.seasonality_prior_scale,
            "holidays_prior_scale": self.holidays_prior_scale,
            "changepoint_range": self.changepoint_range,
            "n_changepoints": self.n_changepoints,
            "uncertainty_samples": self.uncertainty_samples,
            "metrics": self.metrics,
            "is_fitted": self.is_fitted,
            "training_date_range": self.training_date_range,
            "last_date": self.last_date,
            "model_version": self.model_version,
            "creation_time": self.creation_time
        }

        # Save both the Prophet model and metadata
        joblib.dump({
            "metadata": metadata,
            "model": self.model,
            "train_df": self.train_df
        }, path)

        logger.info(f"✅ Prophet model saved to {path}")

    def load(self, path: str) -> None:
        """Load the model from disk. Supports both old and new formats."""
        try:
            # Try loading with joblib first
            data = joblib.load(path)
            
            # Check if it's the new format (dict with metadata) or old format (raw Prophet)
            if isinstance(data, dict) and "metadata" in data:
                # New format
                metadata = data.get("metadata", {})
                for key, value in metadata.items():
                    if hasattr(self, key):
                        setattr(self, key, value)
                self.model = data.get("model")
                self.train_df = data.get("train_df")
            else:
                # Old format or raw Prophet model
                self.model = data
                self.train_df = None
                
            self.is_fitted = True
            logger.info(f"✅ Prophet model loaded from {path}")
            
        except Exception as e:
            logger.warning(f"Joblib load failed, trying pickle: {e}")
            # Fallback to pickle
            try:
                with open(path, "rb") as f:
                    data = pickle.load(f)
                
                if isinstance(data, dict):
                    metadata = data.get("metadata", {})
                    for key, value in metadata.items():
                        if hasattr(self, key):
                            setattr(self, key, value)
                    self.model = data.get("model")
                    self.train_df = data.get("train_df")
                else:
                    self.model = data
                    self.train_df = None
                    
                self.is_fitted = True
                logger.info(f"✅ Prophet model loaded from {path} (pickle fallback)")
            except Exception as e2:
                logger.error(f"All load methods failed: {e2}")
                raise
