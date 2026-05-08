import numpy as np
import pandas as pd

from ml.utils.metrics import compute_all_metrics


def align_arrays(actual, predicted):
    """
    Ensures arrays are same length and clean.
    """

    actual = np.array(actual, dtype=float)
    predicted = np.array(predicted, dtype=float)

    min_len = min(len(actual), len(predicted))

    actual = actual[:min_len]
    predicted = predicted[:min_len]

    mask = (
        ~np.isnan(actual)
        & ~np.isnan(predicted)
        & ~np.isinf(actual)
        & ~np.isinf(predicted)
    )

    actual = actual[mask]
    predicted = predicted[mask]

    return actual, predicted


def evaluate_forecast(actual, predicted):
    """
    Safe evaluation wrapper for all models.
    """

    actual, predicted = align_arrays(actual, predicted)

    if len(actual) == 0:
        return {
            "rmse": 9999,
            "mae": 9999,
            "mape": 9999,
            "r_squared": -999,
        }

    return compute_all_metrics(actual, predicted)


def evaluate_prediction_dict(pred_dict):
    """
    Handles:
    {
        "y_true": [...],
        "y_pred": [...]
    }
    """

    actual = pred_dict.get("y_true", [])
    predicted = pred_dict.get("y_pred", [])

    return evaluate_forecast(actual, predicted)


def evaluate_prediction_dataframe(df):
    """
    Handles dataframe outputs from LSTM.
    """

    if df.empty:
        return {
            "rmse": 9999,
            "mae": 9999,
            "mape": 9999,
            "r_squared": -999,
        }

    return evaluate_forecast(
        df["y_true"].values,
        df["y_pred"].values
    )