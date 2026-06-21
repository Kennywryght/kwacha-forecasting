import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from ml.models.ensemble_model import EnsembleForecaster
from ml.models.arima_model import ARIMAForecaster
from ml.models.prophet_model import ProphetForecaster
import joblib
from core.logging_config import setup_logging

setup_logging()

# Load the working models
arima = ARIMAForecaster()
arima.load("ml/artifacts/arima.pkl")

prophet = ProphetForecaster()
prophet.load("ml/artifacts/prophet.pkl")

# Create ensemble with just ARIMA and Prophet
ensemble = EnsembleForecaster(
    models={"arima": arima, "prophet": prophet},
    weights={"arima": 0.5, "prophet": 0.5}
)
ensemble.is_fitted = True

# Save
ensemble.save("ml/artifacts/ensemble.pkl")
print("✅ New ensemble saved (ARIMA + Prophet)")
