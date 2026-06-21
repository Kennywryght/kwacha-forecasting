"""Performance metrics for time series forecasting.

This module provides functions for computing standard forecasting metrics:
- RMSE (Root Mean Squared Error)
- MAE (Mean Absolute Error)
- MAPE (Mean Absolute Percentage Error)
- R² (Coefficient of Determination)
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Union
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score


def compute_rmse(
    actual: Union[np.ndarray, List[float]],
    predicted: Union[np.ndarray, List[float]]
) -> float:
    """
    Compute Root Mean Squared Error.

    Args:
        actual: Actual values
        predicted: Predicted values

    Returns:
        RMSE value
    """
    actual = np.array(actual, dtype=float)
    predicted = np.array(predicted, dtype=float)
    
    if len(actual) == 0 or len(predicted) == 0:
        return np.nan
    
    return float(np.sqrt(mean_squared_error(actual, predicted)))


def compute_mae(
    actual: Union[np.ndarray, List[float]],
    predicted: Union[np.ndarray, List[float]]
) -> float:
    """
    Compute Mean Absolute Error.

    Args:
        actual: Actual values
        predicted: Predicted values

    Returns:
        MAE value
    """
    actual = np.array(actual, dtype=float)
    predicted = np.array(predicted, dtype=float)
    
    if len(actual) == 0 or len(predicted) == 0:
        return np.nan
    
    return float(mean_absolute_error(actual, predicted))


def compute_mape(
    actual: Union[np.ndarray, List[float]],
    predicted: Union[np.ndarray, List[float]]
) -> float:
    """
    Compute Mean Absolute Percentage Error.

    Args:
        actual: Actual values
        predicted: Predicted values

    Returns:
        MAPE value (percentage)
    """
    actual = np.array(actual, dtype=float)
    predicted = np.array(predicted, dtype=float)
    
    if len(actual) == 0 or len(predicted) == 0:
        return np.nan
    
    # Avoid division by zero
    mask = np.abs(actual) > 1e-8
    
    if np.sum(mask) == 0:
        return np.nan
    
    mape = np.mean(np.abs((actual[mask] - predicted[mask]) / actual[mask])) * 100
    
    return float(mape)


def compute_r2(
    actual: Union[np.ndarray, List[float]],
    predicted: Union[np.ndarray, List[float]]
) -> float:
    """
    Compute R-squared (coefficient of determination).

    Args:
        actual: Actual values
        predicted: Predicted values

    Returns:
        R² value
    """
    actual = np.array(actual, dtype=float)
    predicted = np.array(predicted, dtype=float)
    
    if len(actual) == 0 or len(predicted) == 0:
        return np.nan
    
    # Handle constant target
    if np.var(actual) < 1e-8:
        return 0.0
    
    return float(r2_score(actual, predicted))


def compute_all_metrics(
    actual: Union[np.ndarray, List[float]],
    predicted: Union[np.ndarray, List[float]]
) -> Dict[str, float]:
    """
    Compute all standard forecasting metrics.

    Args:
        actual: Actual values
        predicted: Predicted values

    Returns:
        Dictionary with all metrics
    """
    actual = np.array(actual, dtype=float)
    predicted = np.array(predicted, dtype=float)
    
    return {
        "rmse": compute_rmse(actual, predicted),
        "mae": compute_mae(actual, predicted),
        "mape": compute_mape(actual, predicted),
        "r_squared": compute_r2(actual, predicted)
    }


def compute_directional_accuracy(
    actual: Union[np.ndarray, List[float]],
    predicted: Union[np.ndarray, List[float]]
) -> float:
    """
    Compute directional accuracy (sign of change).

    Args:
        actual: Actual values
        predicted: Predicted values

    Returns:
        Directional accuracy (0-1)
    """
    actual = np.array(actual, dtype=float)
    predicted = np.array(predicted, dtype=float)
    
    if len(actual) < 2:
        return np.nan
    
    # Compute direction of change
    actual_direction = np.sign(np.diff(actual))
    predicted_direction = np.sign(np.diff(predicted))
    
    # Align lengths
    min_len = min(len(actual_direction), len(predicted_direction))
    actual_direction = actual_direction[:min_len]
    predicted_direction = predicted_direction[:min_len]
    
    # Calculate accuracy
    correct = np.sum(actual_direction == predicted_direction)
    total = len(actual_direction)
    
    return float(correct / total) if total > 0 else np.nan


def compute_metrics_summary(
    actual: Union[np.ndarray, List[float]],
    predicted: Union[np.ndarray, List[float]],
    include_directional: bool = True
) -> Dict[str, float]:
    """
    Compute comprehensive metrics summary.

    Args:
        actual: Actual values
        predicted: Predicted values
        include_directional: Whether to include directional accuracy

    Returns:
        Dictionary with all computed metrics
    """
    metrics = compute_all_metrics(actual, predicted)
    
    if include_directional:
        metrics["directional_accuracy"] = compute_directional_accuracy(actual, predicted)
    
    return metrics