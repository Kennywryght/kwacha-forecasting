import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from ml.models.arima_model import ARIMAForecaster
from ml.models.arimax_model import ARIMAXForecaster
from core.logging_config import setup_logging

setup_logging()

# Test ARIMA
print("Testing ARIMA load...")
try:
    arima = ARIMAForecaster()
    arima.load("ml/artifacts/arima.pkl")
    print("✅ ARIMA loaded successfully!")
    print(f"  Order: {arima.order}")
    print(f"  Is fitted: {arima.is_fitted}")
except Exception as e:
    print(f"❌ ARIMA load failed: {e}")

print()

# Test ARIMAX
print("Testing ARIMAX load...")
try:
    arimax = ARIMAXForecaster()
    arimax.load("ml/artifacts/arimax.pkl")
    print("✅ ARIMAX loaded successfully!")
    print(f"  Order: {arimax.order}")
    print(f"  Is fitted: {arimax.is_fitted}")
except Exception as e:
    print(f"❌ ARIMAX load failed: {e}")
