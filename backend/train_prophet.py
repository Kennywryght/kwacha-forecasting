import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
from ml.models.prophet_model import ProphetForecaster
from ml.pipeline.loader import load_data  # Adjust if different
from core.logging_config import setup_logging

# Setup logging
setup_logging()

# Load data
print("📊 Loading data...")
df = load_data()  # or whatever function loads your data
print(f"Loaded {len(df)} rows")

# Train Prophet
print("🚀 Training Prophet model...")
prophet = ProphetForecaster()
prophet.fit(df)

# Save model
model_path = "ml/artifacts/prophet.pkl"
prophet.save(model_path)
print(f"✅ Prophet model saved to {model_path}")
