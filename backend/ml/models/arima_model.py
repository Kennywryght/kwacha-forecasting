"""ARIMA model implementation for time series forecasting.

This module provides a robust ARIMA implementation with:
- Auto-detection of optimal order
- Confidence intervals
- Model persistence
- Validation metrics
"""

import os
import pickle
import warnings
import numpy as np
import pandas as pd
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime

from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.stattools import adfuller
from statsmodels.tsa.statespace.sarimax import SARIMAX

from ml.models.base_model import BaseForecaster
from ml.utils.metrics import compute_all_metrics
from core.logging_config import get_logger

warnings.filterwarnings("ignore")
logger = get_logger(__name__)


class ARIMAForecaster(BaseForecaster):
    """
    ARIMA model for time series forecasting.

    Features:
    - Automatic order selection using AIC
    - Confidence intervals
    - Validation metrics
    - Model persistence

    Configuration:
        order: (p, d, q) tuple, auto-detected if None
        seasonal_order: (P, D, Q, s) tuple for SARIMA
        trend: 'c', 't', 'ct', or None
    """

    def __init__(
        self,
        order: Optional[Tuple[int, int, int]] = None,
        seasonal_order: Optional[Tuple[int, int, int, int]] = None,
        trend: Optional[str] = 'c',
        max_p: int = 3,
        max_d: int = 2,
        max_q: int = 3,
        use_auto_order: bool = True
    ):
        """
        Initialize ARIMA forecaster.

        Args:
            order: (p, d, q) order, auto-detected if None
            seasonal_order: (P, D, Q, s) seasonal order
            trend: Trend component ('c', 't', 'ct', None)
            max_p: Maximum p for auto-order selection
            max_d: Maximum d for auto-order selection
            max_q: Maximum q for auto-order selection
            use_auto_order: Whether to auto-select optimal order
        """
        super().__init__("arima")

        self.order = order or (1, 1, 1)
        self.seasonal_order = seasonal_order
        self.trend = trend
        self.max_p = max_p
        self.max_d = max_d
        self.max_q = max_q
        self.use_auto_order = use_auto_order

        self.fitted_model = None
        self.last_date = None
        self.last_value = None
        self.residuals = None
        self._residuals = []

        # Training metadata
        self.training_start = None
        self.training_end = None

    # ============================================================
    # Core Methods
    # ============================================================

    def _check_stationarity(self, series: np.ndarray) -> int:
        """Check stationarity and determine differencing order."""
        try:
            if len(series) < 10:
                return 0
            result = adfuller(series, autolag='AIC')
            return 1 if result[1] > 0.05 else 0
        except Exception as e:
            logger.warning(f"Stationarity check failed: {e}")
            return 1

    def _find_best_order(
        self,
        series: np.ndarray,
        d: int
    ) -> Tuple[int, int, int]:
        """
        Find optimal ARIMA order using AIC.

        Args:
            series: Time series data
            d: Differencing order

        Returns:
            Optimal (p, d, q) tuple
        """
        best_aic = np.inf
        best_order = (1, d, 1)

        for p in range(0, self.max_p + 1):
            for q in range(0, self.max_q + 1):
                if p == 0 and q == 0:
                    continue

                try:
                    model = ARIMA(
                        series,
                        order=(p, d, q),
                        trend='n' if self.order[1] > 0 else self.trend,
                        enforce_stationarity=False,
                        enforce_invertibility=False
                    )
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        res = model.fit(method_kwargs={'disp': False})

                    if res.aic < best_aic:
                        best_aic = res.aic
                        best_order = (p, d, q)
                except Exception:
                    continue

        logger.debug(f"Selected order: {best_order} (AIC: {best_aic:.2f})")
        return best_order

    def _prepare_data(self, df: pd.DataFrame) -> Tuple[pd.Series, pd.Timestamp]:
        """Prepare data for modeling."""
        df = self._clean_dataframe(df)

        if "date" not in df.columns:
            raise ValueError("DataFrame must contain 'date' column")

        df = df.sort_values("date")
        df = df.dropna(subset=["rate"])

        if len(df) < 50:
            raise ValueError(f"Not enough data: {len(df)} rows (need at least 50)")

        y = df["rate"].astype(float).ffill().bfill()

        self.training_start = df["date"].iloc[0]
        self.training_end = df["date"].iloc[-1]
        self.last_date = df["date"].iloc[-1]
        self.last_value = float(y.iloc[-1])

        # Store training date range
        self.training_date_range = (self.training_start, self.training_end)

        return y, self.last_date

    def fit(self, df: pd.DataFrame) -> None:
        """
        Fit ARIMA model with auto-order selection.

        Args:
            df: DataFrame with 'date' and 'rate' columns
        """
        logger.info(f"🚀 ARIMA training started (max_p={self.max_p}, max_q={self.max_q})")

        y, last_date = self._prepare_data(df)

        # Determine stationarity
        d = self._check_stationarity(y.values)

        # Find optimal order if enabled
        if self.use_auto_order:
            logger.debug("Auto-selecting optimal order...")
            self.order = self._find_best_order(y.values, d)
            logger.info(f"Selected order: {self.order}")

        # Fit model
        try:
            self.fitted_model = ARIMA(
                y,
                order=self.order,
                trend='n' if self.order[1] > 0 else self.trend,
                enforce_stationarity=False,
                enforce_invertibility=False
            ).fit(method_kwargs={'disp': False})

            # Store residuals for uncertainty
            self.residuals = self.fitted_model.resid
            
            # FIX: Handle both numpy array and list cases
            if isinstance(self.residuals, np.ndarray):
                self._residuals = self.residuals.tolist()
            elif isinstance(self.residuals, list):
                self._residuals = self.residuals
            else:
                self._residuals = []

            self.is_fitted = True
            logger.info(f"✅ ARIMA fitted successfully (AIC: {self.fitted_model.aic:.2f})")

        except Exception as e:
            logger.error(f"ARIMA fitting failed: {e}")
            raise

    def refit(self, df: pd.DataFrame) -> None:
        """
        Fast refit using existing order (no auto-selection).

        Args:
            df: DataFrame with new data
        """
        logger.info("⚡ ARIMA fast refit (using existing order)")

        y, last_date = self._prepare_data(df)

        try:
            self.fitted_model = ARIMA(
                y,
                order=self.order,
                trend='n' if self.order[1] > 0 else self.trend,
                enforce_stationarity=False,
                enforce_invertibility=False
            ).fit(method_kwargs={'disp': False})

            self.residuals = self.fitted_model.resid
            
            # FIX: Handle both numpy array and list cases
            if isinstance(self.residuals, np.ndarray):
                self._residuals = self.residuals.tolist()
            elif isinstance(self.residuals, list):
                self._residuals = self.residuals
            else:
                self._residuals = []
                
            self.is_fitted = True

            logger.info(f"✅ ARIMA refit complete (AIC: {self.fitted_model.aic:.2f})")

        except Exception as e:
            logger.error(f"ARIMA refit failed: {e}")
            raise

    def predict(self, horizon: int) -> Dict[str, Any]:
        """
        Generate forecasts for a given horizon.

        Args:
            horizon: Number of days to forecast

        Returns:
            Dictionary with dates, predictions, and confidence intervals
        """
        if not self.is_fitted:
            raise RuntimeError("ARIMA model not fitted")

        try:
            forecast = self.fitted_model.get_forecast(steps=horizon)

            predicted_raw = forecast.predicted_mean
            if hasattr(predicted_raw, 'values'):
                predicted = predicted_raw.values
            elif hasattr(predicted_raw, 'tolist'):
                predicted = predicted_raw.tolist()
            else:
                predicted = list(predicted_raw)
            
            conf_int = forecast.conf_int()

            # Extract confidence intervals
            if isinstance(conf_int, pd.DataFrame):
                lower = conf_int.iloc[:, 0].tolist()
                upper = conf_int.iloc[:, 1].tolist()
            else:
                lower = list(conf_int[:, 0])
                upper = list(conf_int[:, 1])

            # Generate dates
            dates = self._generate_dates(self.last_date, horizon)

            return self._format_forecast_output(dates, predicted, lower, upper)

        except Exception as e:
            logger.error(f"ARIMA prediction failed: {e}")
            raise

    # ============================================================
    # Model Persistence
    # ============================================================

    def save(self, path: str) -> None:
        """Save the model to disk."""
        os.makedirs(os.path.dirname(path), exist_ok=True)

        # Create metadata
        metadata = {
            "name": self.name,
            "order": self.order,
            "seasonal_order": self.seasonal_order,
            "trend": self.trend,
            "max_p": self.max_p,
            "max_d": self.max_d,
            "max_q": self.max_q,
            "use_auto_order": self.use_auto_order,
            "metrics": self.metrics,
            "is_fitted": self.is_fitted,
            "training_date_range": self.training_date_range,
            "last_date": self.last_date,
            "last_value": self.last_value,
            "model_version": self.model_version,
            "creation_time": self.creation_time
        }

        # Also save the statsmodels model
        with open(path, "wb") as f:
            pickle.dump({
                "metadata": metadata,
                "model": self.fitted_model,
                "residuals": self.residuals
            }, f)

        logger.info(f"✅ ARIMA model saved to {path}")

    def load(self, path: str) -> None:
        """Load the model from disk."""
        with open(path, "rb") as f:
            data = pickle.load(f)

        # Restore metadata
        metadata = data.get("metadata", {})
        for key, value in metadata.items():
            if hasattr(self, key):
                setattr(self, key, value)

        # Restore model
        self.fitted_model = data.get("model")
        self.residuals = data.get("residuals", [])
        
        # FIX: Handle both numpy array and list cases
        if isinstance(self.residuals, np.ndarray):
            self._residuals = self.residuals.tolist()
        elif isinstance(self.residuals, list):
            self._residuals = self.residuals
        else:
            self._residuals = []

        self.is_fitted = True
        logger.info(f"✅ ARIMA model loaded from {path}")


# ============================================================
# Factory function for easy creation
# ============================================================

def create_arima_forecaster(
    auto_order: bool = True,
    max_p: int = 3,
    max_q: int = 3,
    **kwargs
) -> ARIMAForecaster:
    """
    Create an ARIMA forecaster with sensible defaults.

    Args:
        auto_order: Whether to auto-select optimal order
        max_p: Maximum p for auto-order selection
        max_q: Maximum q for auto-order selection
        **kwargs: Additional arguments for ARIMAForecaster

    Returns:
        Configured ARIMAForecaster instance
    """
    return ARIMAForecaster(
        use_auto_order=auto_order,
        max_p=max_p,
        max_q=max_q,
        **kwargs
    )