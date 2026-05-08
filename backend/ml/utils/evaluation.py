# backend/ml/utils/evaluation.py
import numpy as np
import pandas as pd
from ml.utils.metrics import compute_all_metrics

def evaluate_prediction_dict(pred: dict) -> dict:
    """
    pred must have keys 'y_true' and 'y_pred' (list/array).
    Returns dict of metrics.
    """
    if not isinstance(pred, dict) or "y_true" not in pred or "y_pred" not in pred:
        raise ValueError("Prediction dict must contain 'y_true' and 'y_pred'")
    y_true = np.asarray(pred["y_true"], dtype=float)
    y_pred = np.asarray(pred["y_pred"], dtype=float)
    return compute_all_metrics(y_true, y_pred)

def evaluate_prediction_dataframe(df: pd.DataFrame) -> dict:
    """
    DataFrame must have columns 'y_true' and 'y_pred'.
    """
    if "y_true" not in df.columns or "y_pred" not in df.columns:
        raise ValueError("DataFrame must contain 'y_true' and 'y_pred' columns")
    return compute_all_metrics(df["y_true"].values, df["y_pred"].values)