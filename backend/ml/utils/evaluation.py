"""Model evaluation utilities.

This module provides functions for evaluating model predictions
and computing performance metrics.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Union, Optional
from ml.utils.metrics import compute_all_metrics


def evaluate_prediction_dict(
    pred_dict: Dict[str, Any],
    metrics: Optional[List[str]] = None
) -> Dict[str, float]:
    """
    Evaluate predictions from a model.

    Args:
        pred_dict: Dictionary with 'y_true' and 'y_pred' keys
        metrics: List of metrics to compute (None = all)

    Returns:
        Dictionary of metrics
    """
    # Extract arrays
    y_true = pred_dict.get("y_true")
    y_pred = pred_dict.get("y_pred")
    
    if y_true is None or y_pred is None:
        # Try alternative keys
        y_true = pred_dict.get("actual")
        y_pred = pred_dict.get("predicted")
    
    if y_true is None or y_pred is None:
        return {"error": "Missing y_true or y_pred"}
    
    # Convert to numpy arrays
    y_true = np.array(y_true, dtype=float).flatten()
    y_pred = np.array(y_pred, dtype=float).flatten()
    
    # Align lengths
    min_len = min(len(y_true), len(y_pred))
    y_true = y_true[:min_len]
    y_pred = y_pred[:min_len]
    
    if len(y_true) == 0:
        return {"error": "Empty arrays"}
    
    # Compute all metrics
    all_metrics = compute_all_metrics(y_true, y_pred)
    
    # Filter if specific metrics requested
    if metrics:
        return {k: v for k, v in all_metrics.items() if k in metrics}
    
    return all_metrics


def evaluate_forecast(
    actual: pd.Series,
    predicted: pd.Series,
    dates: Optional[pd.Series] = None
) -> Dict[str, Any]:
    """
    Evaluate a forecast with additional context.

    Args:
        actual: Actual values
        predicted: Predicted values
        dates: Dates for the predictions (optional)

    Returns:
        Dictionary with metrics and optional details
    """
    # Compute metrics
    metrics = compute_all_metrics(actual.values, predicted.values)
    
    # Compute additional diagnostics
    residuals = actual.values - predicted.values
    
    result = {
        "metrics": metrics,
        "residuals": {
            "mean": float(np.mean(residuals)),
            "std": float(np.std(residuals)),
            "min": float(np.min(residuals)),
            "max": float(np.max(residuals))
        },
        "predictions": {
            "min": float(np.min(predicted)),
            "max": float(np.max(predicted)),
            "mean": float(np.mean(predicted))
        }
    }
    
    # Add dates if provided
    if dates is not None:
        result["dates"] = dates.tolist()
    
    return result


def compare_models(
    model_predictions: Dict[str, Dict[str, Any]],
    actual: Union[np.ndarray, List[float]]
) -> pd.DataFrame:
    """
    Compare multiple model predictions.

    Args:
        model_predictions: Dictionary of {model_name: prediction_dict}
        actual: Actual values

    Returns:
        DataFrame with comparison results
    """
    results = []
    
    actual = np.array(actual, dtype=float)
    
    for model_name, pred_dict in model_predictions.items():
        y_pred = pred_dict.get("y_pred") or pred_dict.get("predicted")
        
        if y_pred is None:
            continue
        
        y_pred = np.array(y_pred, dtype=float).flatten()
        
        # Align lengths
        min_len = min(len(actual), len(y_pred))
        y_true = actual[:min_len]
        y_pred = y_pred[:min_len]
        
        if len(y_true) == 0:
            continue
        
        # Compute metrics
        metrics = compute_all_metrics(y_true, y_pred)
        metrics["model"] = model_name
        
        results.append(metrics)
    
    if not results:
        return pd.DataFrame()
    
    # Create DataFrame and sort by RMSE
    df = pd.DataFrame(results)
    if "rmse" in df.columns:
        df = df.sort_values("rmse")
    
    return df