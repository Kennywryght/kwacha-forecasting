import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
from ml.pipeline.loader import load_data
from ml.models.prophet_model import ProphetForecaster
from core.logging_config import setup_logging

setup_logging()

# Load data
print("📊 Loading data...")
df = load_data()
print(f"Raw data shape: {df.shape}")
print(f"Columns: {df.columns.tolist()}")
print(f"Date column exists: {'date' in df.columns}")
print(f"Rate column exists: {'rate' in df.columns}")
print(f"\nFirst 5 rows:")
print(df.head())
print(f"\nRate column nulls: {df['rate'].isnull().sum() if 'rate' in df.columns else 'N/A'}")

# Try preparing data step by step
prophet = ProphetForecaster()

# Step 1: Clean dataframe
df_clean = prophet._clean_dataframe(df)
print(f"\nAfter clean: {df_clean.shape}")
print(f"First 5 cleaned rows:")
print(df_clean.head())

# Step 2: Sort and filter
if "date" in df_clean.columns:
    df_sorted = df_clean.sort_values("date")
    df_filtered = df_sorted.dropna(subset=["rate"])
    print(f"\nAfter filtering nulls: {df_filtered.shape}")
    print(f"First 5 filtered rows:")
    print(df_filtered.head())
    
    # Check the 'rate' column values
    print(f"\nRate column type: {df_filtered['rate'].dtype}")
    print(f"Rate sample values: {df_filtered['rate'].head().tolist()}")
    
    # Create prophet dataframe manually
    prophet_df = pd.DataFrame({
        "ds": df_filtered["date"],
        "y": df_filtered["rate"].astype(float)
    })
    print(f"\nProphet df shape: {prophet_df.shape}")
    print(f"Prophet df nulls: {prophet_df.isnull().sum().sum()}")
