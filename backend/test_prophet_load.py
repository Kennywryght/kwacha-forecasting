import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import joblib
from core.logging_config import setup_logging

setup_logging()

# Test Prophet with joblib
print("Testing Prophet load...")
try:
    model = joblib.load("ml/artifacts/prophet.pkl")
    print("✅ Prophet loaded with joblib!")
    print(f"  Model type: {type(model)}")
except Exception as e:
    print(f"❌ Prophet load failed: {e}")

print()

# Test with ProphetForecaster wrapper
from ml.models.prophet_model import ProphetForecaster
print("Testing ProphetForecaster wrapper...")
try:
    prophet = ProphetForecaster()
    prophet.load("ml/artifacts/prophet.pkl")
    print("✅ ProphetForecaster loaded!")
except Exception as e:
    print(f"❌ ProphetForecaster load failed: {e}")
