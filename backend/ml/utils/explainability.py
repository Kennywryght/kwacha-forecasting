# backend/ml/utils/explainability.py
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import joblib
import logging
from sklearn.inspection import permutation_importance
import shap

logger = logging.getLogger(__name__)


def permutation_importance_for_model(model, X: pd.DataFrame, y: pd.Series,
                                     feature_names: list, output_dir: str = "outputs/explain",
                                     n_repeats: int = 10):
    """
    Compute and plot permutation feature importance for a fitted model.
    Works with any model that has a .predict() method.
    """
    os.makedirs(output_dir, exist_ok=True)

    # Sklearn's permutation_importance uses the model's .score() method by default,
    # but we can supply a custom scorer that uses .predict()
    def scorer(m, X):
        preds = m.predict(X)
        if isinstance(preds, dict):
            return np.array(preds["y_pred"])
        return np.array(preds)

    result = permutation_importance(
        model, X, y, n_repeats=n_repeats, random_state=42,
        scoring=None  # will use model's .score() if available, else fallback
    )

    importances = result.importances_mean
    std = result.importances_std
    indices = np.argsort(importances)[::-1]

    plt.figure(figsize=(10, 6))
    plt.title("Permutation Feature Importance")
    plt.bar(range(len(importances)), importances[indices], yerr=std[indices], align="center")
    plt.xticks(range(len(importances)), [feature_names[i] for i in indices], rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "permutation_importance.png"), dpi=100)
    plt.close()

    importance_df = pd.DataFrame({
        "feature": feature_names,
        "importance_mean": importances,
        "importance_std": std
    }).sort_values("importance_mean", ascending=False)
    importance_df.to_csv(os.path.join(output_dir, "permutation_importance.csv"), index=False)

    logger.info(f"Permutation importance saved to {output_dir}")
    return importance_df


def shap_kernel_explain(model, X: pd.DataFrame, feature_names: list,
                        output_dir: str = "outputs/explain",
                        nsamples: int = 100):
    """
    Generate SHAP explanations using KernelExplainer (model-agnostic).
    Works with any model that has a .predict() method returning a 1D array.
    X: DataFrame of feature columns (no target).
    """
    os.makedirs(output_dir, exist_ok=True)

    # Ensure we pass numpy array to SHAP
    X_array = X.values

    # Predict function wrapper (ensure returns 1D array)
    def predict_fn(data):
        # data is a 2D array; convert back to DataFrame if model expects that
        df = pd.DataFrame(data, columns=feature_names)
        preds = model.predict(df)
        if isinstance(preds, dict):
            return np.array(preds["y_pred"])
        return np.array(preds).flatten()

    # Use a small background sample (e.g., 50 rows) to speed up
    background = shap.kmeans(X_array, min(50, len(X_array)))
    explainer = shap.KernelExplainer(predict_fn, background)
    shap_values = explainer.shap_values(X_array[:nsamples], nsamples=nsamples)

    # Summary plot
    shap.summary_plot(shap_values, X_array[:nsamples], feature_names=feature_names, show=False)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "shap_summary.png"), dpi=100)
    plt.close()

    # Bar plot
    shap.summary_plot(shap_values, X_array[:nsamples], feature_names=feature_names,
                      plot_type="bar", show=False)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "shap_bar.png"), dpi=100)
    plt.close()

    # Save SHAP values
    np.save(os.path.join(output_dir, "shap_values.npy"), shap_values)
    np.save(os.path.join(output_dir, "shap_test_data.npy"), X_array[:nsamples])

    logger.info(f"SHAP explanations saved to {output_dir}")
    return shap_values


def run_explainability(df: pd.DataFrame, model_dir: str = "ml/artifacts",
                       output_dir: str = "outputs/explain", method: str = "permutation"):
    """
    Load best model, compute explainability using chosen method.
    method: 'permutation' or 'shap'
    """
    model_path = os.path.join(model_dir, "best_model.pkl")
    if not os.path.exists(model_path):
        logger.warning("No best_model.pkl found. Run training first.")
        return
    model = joblib.load(model_path)

    # Use last 20% of data as test set
    split_idx = int(len(df) * 0.8)
    test_df = df.iloc[split_idx:]
    feature_cols = [c for c in test_df.columns if c not in ["date", "rate", "is_interpolated", "daily_return"]]
    X_test = test_df[feature_cols]
    y_test = test_df["rate"]

    if method == "permutation":
        return permutation_importance_for_model(model, X_test, y_test, feature_cols, output_dir)
    elif method == "shap":
        return shap_kernel_explain(model, X_test, feature_cols, output_dir)
    else:
        logger.error(f"Unknown method: {method}")