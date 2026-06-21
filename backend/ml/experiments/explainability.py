"""SHAP explainability module for model interpretation.

This module provides SHAP-based model explanations including:
- Feature importance
- Individual prediction explanations
- Summary plots
- Force plots
"""

import os
import sys
import pandas as pd
import numpy as np
import shap
import matplotlib.pyplot as plt
import warnings
from typing import Optional, List, Dict, Any, Tuple
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from core.logging_config import get_logger
from ml.utils.io_utils import load_data

logger = get_logger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────
DATA_PATH = "data/processed/mwk_usd_clean.csv"
OUTPUT_DIR = "outputs/shap"
TARGET_COLUMN = "rate"
SAMPLE_SIZE = 100  # Number of samples to explain
BACKGROUND_SIZE = 50  # Background samples for KernelExplainer

os.makedirs(OUTPUT_DIR, exist_ok=True)


def load_and_prepare_data(
    path: str = DATA_PATH,
    target: str = TARGET_COLUMN
) -> Tuple[pd.DataFrame, pd.Series, List[str]]:
    """
    Load and prepare data for SHAP analysis.

    Args:
        path: Path to data file
        target: Target column name

    Returns:
        Tuple of (X, y, feature_names)
    """
    logger.info(f"📊 Loading data from {path}")

    df = pd.read_csv(path, parse_dates=["date"])

    # Keep only numeric columns
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    # Ensure target is included
    if target not in numeric_cols:
        raise ValueError(f"Target column '{target}' not found")

    # Remove columns with too many missing values
    for col in numeric_cols:
        if df[col].isnull().sum() > 0.5 * len(df):
            numeric_cols.remove(col)
            logger.info(f"Removed {col} due to high missing values")

    # Select features
    feature_cols = [c for c in numeric_cols if c != target]

    # Handle missing values
    df = df[feature_cols + [target]].copy()
    df = df.ffill().bfill().dropna()

    X = df[feature_cols]
    y = df[target]

    logger.info(f"✅ Data loaded: {len(X)} rows, {len(feature_cols)} features")
    logger.info(f"   Features: {feature_cols}")

    return X, y, feature_cols


def train_model(
    X: pd.DataFrame,
    y: pd.Series,
    test_size: float = 0.2
) -> Tuple[RandomForestRegressor, pd.DataFrame, pd.Series]:
    """
    Train a RandomForest model for SHAP analysis.

    Args:
        X: Feature DataFrame
        y: Target Series
        test_size: Proportion for test set

    Returns:
        Tuple of (model, X_test, y_test)
    """
    logger.info("🚀 Training RandomForest for SHAP analysis")

    # Split data
    split_idx = int(len(X) * (1 - test_size))
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    # Train model
    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=10,
        min_samples_leaf=5,
        random_state=42,
        n_jobs=-1
    )

    model.fit(X_train, y_train)

    # Score
    score = model.score(X_test, y_test)
    logger.info(f"✅ Model trained (R² = {score:.4f})")

    return model, X_test, y_test


def compute_shap_values(
    model: RandomForestRegressor,
    X_sample: pd.DataFrame
) -> Tuple[shap.TreeExplainer, np.ndarray]:
    """
    Compute SHAP values for a sample.

    Args:
        model: Trained model
        X_sample: Sample DataFrame

    Returns:
        Tuple of (explainer, shap_values)
    """
    logger.info("🔍 Computing SHAP values...")

    # Use TreeExplainer for tree-based models
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_sample)

    logger.info(f"✅ SHAP values computed ({len(shap_values)} samples)")

    return explainer, shap_values


def save_shap_plots(
    shap_values: np.ndarray,
    X_sample: pd.DataFrame,
    feature_names: List[str],
    explainer: Optional[shap.TreeExplainer] = None,
    output_dir: str = OUTPUT_DIR
) -> None:
    """
    Generate and save SHAP plots.

    Args:
        shap_values: SHAP values array
        X_sample: Sample DataFrame
        feature_names: List of feature names
        explainer: SHAP explainer (for force plots)
        output_dir: Output directory
    """
    os.makedirs(output_dir, exist_ok=True)

    # 1. Summary plot (beeswarm)
    logger.info("📊 Generating summary plot...")
    plt.figure(figsize=(12, 8))
    shap.summary_plot(shap_values, X_sample, feature_names=feature_names, show=False)
    plt.tight_layout()
    plt.savefig(f"{output_dir}/shap_summary.png", dpi=150, bbox_inches="tight")
    plt.close()

    # 2. Feature importance bar plot
    logger.info("📊 Generating feature importance bar plot...")
    plt.figure(figsize=(10, 7))
    shap.summary_plot(shap_values, X_sample, feature_names=feature_names,
                      plot_type="bar", show=False)
    plt.tight_layout()
    plt.savefig(f"{output_dir}/shap_feature_importance.png", dpi=150, bbox_inches="tight")
    plt.close()

    # 3. Force plot for first sample (if explainer available)
    if explainer is not None and len(X_sample) > 0:
        logger.info("🔥 Generating force plot...")
        try:
            shap.force_plot(
                explainer.expected_value,
                shap_values[0],
                X_sample.iloc[0],
                matplotlib=True,
                show=False
            )
            plt.tight_layout()
            plt.savefig(f"{output_dir}/shap_force_plot.png", dpi=150, bbox_inches="tight")
            plt.close()
        except Exception as e:
            logger.warning(f"Force plot failed: {e}")

    logger.info(f"✅ SHAP plots saved to {output_dir}")


def interpret_features(
    shap_values: np.ndarray,
    X_sample: pd.DataFrame,
    feature_names: List[str]
) -> pd.DataFrame:
    """
    Interpret SHAP values to understand feature impacts.

    Args:
        shap_values: SHAP values array
        X_sample: Sample DataFrame
        feature_names: List of feature names

    Returns:
        DataFrame with feature interpretation
    """
    logger.info("🔍 Interpreting feature impacts...")

    # Mean absolute SHAP values for each feature
    mean_abs_shap = np.abs(shap_values).mean(axis=0)

    # Feature importance
    importance_df = pd.DataFrame({
        'feature': feature_names,
        'mean_abs_shap': mean_abs_shap,
        'direction': [
            'positive' if np.median(shap_values[:, i]) > 0 else 'negative'
            for i in range(len(feature_names))
        ]
    }).sort_values('mean_abs_shap', ascending=False)

    # Add correlation with feature
    for i, feature in enumerate(feature_names):
        corr = np.corrcoef(X_sample[feature], shap_values[:, i])[0, 1]
        importance_df.loc[i, 'correlation'] = corr

    # Save interpretation
    importance_df.to_csv(f"{OUTPUT_DIR}/feature_interpretation.csv", index=False)

    # Print top features
    print("\n🔍 SHAP FEATURE INTERPRETATION\n")
    print("Top 5 features by importance:")
    print("-" * 50)

    for _, row in importance_df.head(5).iterrows():
        print(f"Feature: {row['feature']}")
        print(f"Impact Strength: {row['mean_abs_shap']:.4f}")
        print(f"Direction: {row['direction']}")
        print(f"Correlation: {row['correlation']:.3f}")
        print("-" * 40)

    logger.info(f"✅ Feature interpretation saved to {OUTPUT_DIR}")

    return importance_df


def main():
    """Run the SHAP analysis pipeline."""
    print("\n🚀 Running SHAP Explainability...\n")

    try:
        # Load data
        X, y, feature_names = load_and_prepare_data()

        # Train model
        model, X_test, y_test = train_model(X, y)

        # Sample for SHAP (for performance)
        sample_size = min(SAMPLE_SIZE, len(X_test))
        X_sample = X_test.sample(sample_size, random_state=42)

        # Compute SHAP values
        explainer, shap_values = compute_shap_values(model, X_sample)

        # Save plots
        save_shap_plots(shap_values, X_sample, feature_names, explainer)

        # Interpret features
        interpret_features(shap_values, X_sample, feature_names)

        print("\n✅ SHAP analysis complete.")
        print(f"📁 Results saved in: {OUTPUT_DIR}")

    except Exception as e:
        logger.error(f"SHAP analysis failed: {e}")
        raise


if __name__ == "__main__":
    main()