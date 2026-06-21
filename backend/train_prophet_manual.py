import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
from ml.pipeline.loader import load_data
from prophet import Prophet
import joblib
from core.logging_config import setup_logging
from core.logging_config import get_logger

setup_logging()
logger = get_logger(__name__)

# Load data
print("📊 Loading data...")
df = load_data()
print(f"Raw data shape: {df.shape}")

# Manual preparation (skip the problematic _clean_dataframe)
df = df.sort_values("date")
df = df.dropna(subset=["rate"])
print(f"After basic filtering: {df.shape}")

# Check if 'is_preprocessed' column is causing the issue
print(f"\nis_preprocessed values: {df['is_preprocessed'].value_counts().to_dict()}")

# Create prophet dataframe
prophet_df = pd.DataFrame({
    "ds": pd.to_datetime(df["date"]),
    "y": df["rate"].astype(float)
})
prophet_df = prophet_df.dropna()
print(f"Prophet dataframe shape: {prophet_df.shape}")
print(f"First 5 rows:")
print(prophet_df.head())

if len(prophet_df) >= 30:
    # Train Prophet
    print("\n🚀 Training Prophet model...")
    model = Prophet(
        yearly_seasonality=False,
        weekly_seasonality=True,
        daily_seasonality=False
    )
    model.fit(prophet_df)
    
    # Save with joblib
    model_path = "ml/artifacts/prophet.pkl"
    joblib.dump(model, model_path)
    print(f"✅ Prophet model saved to {model_path}")
else:
    print(f"❌ Not enough data: {len(prophet_df)} rows")
