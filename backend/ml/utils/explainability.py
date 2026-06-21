"""Model explainability module.

This module provides tools for explaining model predictions using:
- Permutation importance
- SHAP values
- Feature importance plots
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import joblib
import logging
from typing import Optional, Dict, Any, List, Tuple
from sklearn.inspection import permutation_importance

try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False

logger = logging.getLogger(__name__)


def permutation_importance_for_model(
    model: Any,
    X: pd.DataFrame,
    y: pd.Series,
    feature_names: List[str],
    output_dir: str = "outputs/explain",
    n_repeats: int = 10,
    random_state: int = 42
) -> pd.DataFrame:
    """
    Compute and plot permutation feature importance.

    Args:
        model: Fitted model with .predict() method
        X: Feature DataFrame
        y: Target Series
        feature_names: List of feature names
        output_dir: Directory to save outputs
        n_repeats: Number of repeats for permutation importance
        random_state: Random seed

    Returns:
        DataFrame with importance scores
    """
    os.makedirs(output_dir, exist_ok=True)

    # Create predictor function
    def predict_fn(data):
        if isinstance(data, pd.DataFrame):
            preds = model.predict(data)
        else:
            preds = model.predict(pd.DataFrame(data, columns=feature_names))
        
        if isinstance(preds, dict):
            return np.array(preds.get("y_pred", preds.get("predicted", [])))
        return np.array(preds).flatten()

    # Compute permutation importance
    try:
        result = permutation_importance(
            model, X, y,
            n_repeats=n_repeats,
            random_state=random_state,
            scoring=None  # Uses model's default scoring
        )
        
        importances = result.importances_mean
        std = result.importances_std
        indices = np.argsort(importances)[::-1]
        
    except Exception as e:
        logger.warning(f"Permutation importance failed, using fallback: {e}")
        # Fallback: compute correlation-based importance
        importances = []
        for col in feature_names:
            corr = np.abs(np.corrcoef(X[col], y)[0, 1])
            importances.append(corr if not np.isnan(corr) else 0)
        importances = np.array(importances)
        std = np.zeros_like(importances)
        indices = np.argsort(importances)[::-1]

    # Create plot
    plt.figure(figsize=(10, 6))
    plt.title("Permutation Feature Importance", fontsize=14)
    plt.bar(
        range(len(importances)),
        importances[indices],
        yerr=std[indices],
        align="center",
        capsize=5
    )
    plt.xticks(
        range(len(importances)),
        [feature_names[i] for i in indices],
        rotation=45,
        ha="right"
    )
    plt.ylabel("Importance", fontsize=12)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "permutation_importance.png"), dpi=150)
    plt.close()

    # Save results
    importance_df = pd.DataFrame({
        "feature": feature_names,
        "importance_mean": importances,
        "importance_std": std
    }).sort_values("importance_mean", ascending=False)
    
    importance_df.to_csv(
        os.path.join(output_dir, "permutation_importance.csv"),
        index=False
    )

    logger.info(f"✅ Permutation importance saved to {output_dir}")
    return importance_df


def shap_kernel_explain(
    model: Any,
    X: pd.DataFrame,
    feature_names: List[str],
    output_dir: str = "outputs/explain",
    nsamples: int = 100,
    background_samples: int = 50
) -> Optional[np.ndarray]:
    """
    Generate SHAP explanations using KernelExplainer.

    Args:
        model: Fitted model with .predict() method
        X: Feature DataFrame
        feature_names: List of feature names
        output_dir: Directory to save outputs
        nsamples: Number of samples to explain
        background_samples: Number of background samples

    Returns:
        SHAP values array or None if failed
    """
    if not SHAP_AVAILABLE:
        logger.warning("SHAP not available. Install with: pip install shap")
        return None

    os.makedirs(output_dir, exist_ok=True)

    try:
        # Define prediction function
        def predict_fn(data):
            if isinstance(data, pd.DataFrame):
                preds = model.predict(data)
            else:
                preds = model.predict(pd.DataFrame(data, columns=feature_names))
            
            if isinstance(preds, dict):
                return np.array(preds.get("y_pred", preds.get("predicted", [])))
            return np.array(preds).flatten()

        # Convert to numpy
        X_array = X.values
        
        # Use background samples
        n_bg = min(background_samples, len(X_array))
        background = shap.kmeans(X_array, n_bg)
        
        # Create explainer
        explainer = shap.KernelExplainer(predict_fn, background)
        
        # Compute SHAP values
        n_samples = min(nsamples, len(X_array))
        shap_values = explainer.shap_values(X_array[:n_samples], nsamples=n_samples)
        
        # Create summary plots
        # Summary plot
        shap.summary_plot(
            shap_values,
            X_array[:n_samples],
            feature_names=feature_names,
            show=False
        )
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, "shap_summary.png"), dpi=150)
        plt.close()

        # Bar plot
        shap.summary_plot(
            shap_values,
            X_array[:n_samples],
            feature_names=feature_names,
            plot_type="bar",
            show=False
        )
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, "shap_bar.png"), dpi=150)
        plt.close()

        # Save SHAP values
        np.save(os.path.join(output_dir, "shap_values.npy"), shap_values)
        np.save(os.path.join(output_dir, "shap_test_data.npy"), X_array[:n_samples])

        logger.info(f"✅ SHAP explanations saved to {output_dir}")
        return shap_values
        
    except Exception as e:
        logger.warning(f"SHAP explanation failed: {e}")
        return None


def run_explainability(
    df: pd.DataFrame,
    model_dir: str = "ml/artifacts",
    output_dir: str = "outputs/explain",
    method: str = "permutation",
    model: Optional[Any] = None
) -> Optional[pd.DataFrame]:
    """
    Run explainability on the best model.

    Args:
        df: DataFrame with features
        model_dir: Directory containing saved models
        output_dir: Output directory for explanations
        method: 'permutation' or 'shap'
        model: Pre-loaded model (optional)

    Returns:
        Importance DataFrame or None
    """
    os.makedirs(output_dir, exist_ok=True)

    # Load model if not provided
    if model is None:
        model_path = os.path.join(model_dir, "best_model.pkl")
        if os.path.exists(model_path):
            try:
                model = joblib.load(model_path)
            except Exception as e:
                logger.warning(f"Failed to load model: {e}")
                return None
        else:
            # Try LSTM directory
            lstm_path = os.path.join(model_dir, "best_model")
            if os.path.exists(lstm_path):
                from ml.models.lstm_model import LSTMForecaster
                model = LSTMForecaster()
                try:
                    model.load(lstm_path)
                except Exception as e:
                    logger.warning(f"Failed to load LSTM model: {e}")
                    return None

    if model is None:
        logger.warning("No model found for explainability")
        return None

    # Prepare data
    df = df.copy()
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")

    # Use last 20% as test data
    split_idx = int(len(df) * 0.8)
    test_df = df.iloc[split_idx:]

    # Identify features
    exclude_cols = ["date", "rate", "is_interpolated", "daily_return"]
    feature_cols = [c for c in test_df.columns if c not in exclude_cols]
    
    X_test = test_df[feature_cols]
    y_test = test_df["rate"]

    logger.info(f"🔍 Running explainability with {len(feature_cols)} features")

    # Run selected method
    if method == "permutation":
        return permutation_importance_for_model(
            model, X_test, y_test, feature_cols, output_dir
        )
    elif method == "shap":
        shap_kernel_explain(model, X_test, feature_cols, output_dir)
        return None
    else:
        logger.error(f"Unknown method: {method}")
        return None