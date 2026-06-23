"""ARIMAX model implementation with exogenous variables.

This module provides ARIMAX (ARIMA with Exogenous regressors) for
incorporating external factors like macroeconomic indicators.
"""

import os
import pickle
import warnings
import numpy as np
import pandas as pd
from typing import Optional, Dict, Any, List, Tuple

from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.stattools import adfuller

from ml.models.base_model import BaseForecaster
from ml.utils.metrics import compute_all_metrics
from core.logging_config import get_logger

warnings.filterwarnings("ignore")
logger = get_logger(__name__)


class ARIMAXForecaster(BaseForecaster):
    """
    ARIMAX model with exogenous variables.

    Features:
    - ARIMA with external regressors
    - Auto-order selection
    - Confidence intervals
    - Feature importance estimation
    """

    def __init__(
        self,
        exog_cols: Optional[List[str]] = None,
        order: Optional[Tuple[int, int, int]] = None,
        max_p: int = 3,
        max_d: int = 2,
        max_q: int = 3,
        use_auto_order: bool = True
    ):
        """
        Initialize ARIMAX forecaster.

        Args:
            exog_cols: List of exogenous column names
            order: (p, d, q) order, auto-detected if None
            max_p: Maximum p for auto-order selection
            max_d: Maximum d for auto-order selection
            max_q: Maximum q for auto-order selection
            use_auto_order: Whether to auto-select optimal order
        """
        super().__init__("arimax")

        self.exog_cols = exog_cols or [
            "momentum_7", "momentum_30", "rolling_mean_7",
            "inflation_diff", "interest_rate_diff"
        ]
        self.order = order or (1, 1, 1)
        self.max_p = max_p
        self.max_d = max_d
        self.max_q = max_q
        self.use_auto_order = use_auto_order

        self.fitted_model = None
        self.last_date = None
        self.last_exog = None
        self.residuals = None
        self._residuals = []

    # ============================================================
    # Core Methods
    # ============================================================

    def _check_stationarity(self, y: np.ndarray) -> int:
        """Check stationarity and determine differencing order."""
        try:
            if len(y) < 10:
                return 0
            result = adfuller(y, autolag='AIC')
            return 1 if result[1] > 0.05 else 0
        except Exception:
            return 1

    def _prepare_exog(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare exogenous variables.

        Args:
            df: Input DataFrame

        Returns:
            DataFrame with exogenous variables
        """
        df = df.copy()

        # Filter available columns
        available_cols = [c for c in self.exog_cols if c in df.columns]

        if not available_cols:
            logger.warning("No exogenous columns found, using momentum features")
            available_cols = ["momentum_7", "momentum_30"]

        # Extract and clean
        X = df[available_cols].apply(pd.to_numeric, errors="coerce")
        X = X.ffill().bfill().fillna(0)

        return X

    def _prepare_data(self, df: pd.DataFrame) -> Tuple[np.ndarray, pd.DataFrame, pd.Timestamp]:
        """Prepare data for modeling."""
        df = self._clean_dataframe(df)

        if "date" not in df.columns:
            raise ValueError("DataFrame must contain 'date' column")

        df = df.sort_values("date")
        df = df.dropna(subset=["rate"])

        if len(df) < 60:
            raise ValueError(f"Not enough data: {len(df)} rows (need at least 60)")

        y = df["rate"].astype(float).ffill().bfill().values
        X = self._prepare_exog(df)

        if len(X) == 0:
            raise ValueError("No valid exogenous variables available")

        self.last_date = df["date"].iloc[-1]
        self.last_exog = X.iloc[-1].values

        self.training_start = df["date"].iloc[0]
        self.training_end = df["date"].iloc[-1]
        self.training_date_range = (self.training_start, self.training_end)

        return y, X, self.last_date

    def _find_best_order(
        self,
        y: np.ndarray,
        X: np.ndarray,
        d: int
    ) -> Tuple[int, int, int]:
        """
        Find optimal ARIMAX order using AIC.

        Args:
            y: Target series
            X: Exogenous variables
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
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        model = SARIMAX(
                            y,
                            exog=X,
                            order=(p, d, q),
                            enforce_stationarity=False,
                            enforce_invertibility=False
                        )
                        result = model.fit(disp=False)

                    if result.aic < best_aic:
                        best_aic = result.aic
                        best_order = (p, d, q)
                except Exception:
                    continue

        logger.debug(f"Selected order: {best_order} (AIC: {best_aic:.2f})")
        return best_order

    def fit(self, df: pd.DataFrame) -> None:
        """
        Fit ARIMAX model.

        Args:
            df: DataFrame with 'date', 'rate', and exogenous columns
        """
        logger.info("🚀 ARIMAX training started")

        y, X, last_date = self._prepare_data(df)

        # Determine stationarity
        d = self._check_stationarity(y)

        # Find optimal order if enabled
        if self.use_auto_order:
            self.order = self._find_best_order(y, X.values, d)
            logger.info(f"Selected order: {self.order}")

        # Fit model
        try:
            self.fitted_model = SARIMAX(
                y,
                exog=X.values,
                order=self.order,
                enforce_stationarity=False,
                enforce_invertibility=False
            ).fit(disp=False)

            # Store residuals
            self.residuals = self.fitted_model.resid
            
            # Handle both numpy array and list cases
            if isinstance(self.residuals, np.ndarray):
                self._residuals = self.residuals.tolist()
            elif isinstance(self.residuals, list):
                self._residuals = self.residuals
            else:
                self._residuals = []

            self.is_fitted = True
            logger.info(f"✅ ARIMAX fitted successfully (AIC: {self.fitted_model.aic:.2f})")

        except Exception as e:
            logger.error(f"ARIMAX fitting failed: {e}")
            raise

    def refit(self, df: pd.DataFrame) -> None:
        """
        Fast refit using existing order.

        Args:
            df: DataFrame with new data
        """
        logger.info("⚡ ARIMAX fast refit")

        y, X, last_date = self._prepare_data(df)

        try:
            self.fitted_model = SARIMAX(
                y,
                exog=X.values,
                order=self.order,
                enforce_stationarity=False,
                enforce_invertibility=False
            ).fit(disp=False)

            self.residuals = self.fitted_model.resid
            
            # Handle both numpy array and list cases
            if isinstance(self.residuals, np.ndarray):
                self._residuals = self.residuals.tolist()
            elif isinstance(self.residuals, list):
                self._residuals = self.residuals
            else:
                self._residuals = []
                
            self.is_fitted = True

            logger.info("✅ ARIMAX refit complete")

        except Exception as e:
            logger.error(f"ARIMAX refit failed: {e}")
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
            raise RuntimeError("ARIMAX model not fitted")

        try:
            # Use last_exog for forecasting
            if self.last_exog is not None:
                future_exog = np.array([self.last_exog] * horizon)
            else:
                future_exog = None

            forecast = self.fitted_model.get_forecast(
                steps=horizon,
                exog=future_exog
            )

            predicted_raw = forecast.predicted_mean
            if hasattr(predicted_raw, 'values'):
                predicted = predicted_raw.values
            elif hasattr(predicted_raw, 'tolist'):
                predicted = predicted_raw.tolist()
            else:
                predicted = list(predicted_raw)
            
            conf_int = forecast.conf_int()

            if isinstance(conf_int, pd.DataFrame):
                lower = conf_int.iloc[:, 0].tolist()
                upper = conf_int.iloc[:, 1].tolist()
            else:
                lower = list(conf_int[:, 0])
                upper = list(conf_int[:, 1])

            dates = self._generate_dates(self.last_date, horizon)

            return self._format_forecast_output(dates, predicted, lower, upper)

        except Exception as e:
            logger.error(f"ARIMAX prediction failed: {e}")
            raise

    # ============================================================
    # Model Persistence
    # ============================================================

    def save(self, path: str) -> None:
        """Save the model to disk."""
        os.makedirs(os.path.dirname(path), exist_ok=True)

        metadata = {
            "name": self.name,
            "order": self.order,
            "exog_cols": self.exog_cols,
            "max_p": self.max_p,
            "max_d": self.max_d,
            "max_q": self.max_q,
            "use_auto_order": self.use_auto_order,
            "metrics": self.metrics,
            "is_fitted": self.is_fitted,
            "training_date_range": self.training_date_range,
            "last_date": self.last_date,
            "last_exog": self.last_exog,
            "model_version": self.model_version,
            "creation_time": self.creation_time
        }

        with open(path, "wb") as f:
            pickle.dump({
                "metadata": metadata,
                "model": self.fitted_model,
                "residuals": self.residuals
            }, f)

        logger.info(f"✅ ARIMAX model saved to {path}")

    def load(self, path: str) -> None:
        """Load the model from disk."""
        with open(path, "rb") as f:
            data = pickle.load(f)

        metadata = data.get("metadata", {})
        for key, value in metadata.items():
            if hasattr(self, key):
                setattr(self, key, value)

        self.fitted_model = data.get("model")
        self.residuals = data.get("residuals", [])
        
        # Handle both numpy array and list cases
        if isinstance(self.residuals, np.ndarray):
            self._residuals = self.residuals.tolist()
        elif isinstance(self.residuals, list):
            self._residuals = self.residuals
        else:
            self._residuals = []

        self.is_fitted = True
        logger.info(f"✅ ARIMAX model loaded from {path}")