import numpy as np
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score


def compute_rmse(actual: np.ndarray, predicted: np.ndarray) -> float:
    return float(np.sqrt(mean_squared_error(actual, predicted)))


def compute_mae(actual: np.ndarray, predicted: np.ndarray) -> float:
    return float(mean_absolute_error(actual, predicted))


def compute_mape(actual: np.ndarray, predicted: np.ndarray) -> float:
    actual    = np.array(actual, dtype=float)
    predicted = np.array(predicted, dtype=float)
    mask = actual > 0
    return float(np.mean(np.abs((actual[mask] - predicted[mask]) / actual[mask])) * 100)


def compute_r2(actual: np.ndarray, predicted: np.ndarray) -> float:
    return float(r2_score(actual, predicted))


def compute_all_metrics(actual: np.ndarray, predicted: np.ndarray) -> dict:
    actual    = np.array(actual, dtype=float)
    predicted = np.array(predicted, dtype=float)
    return {
        "rmse":      compute_rmse(actual, predicted),
        "mae":       compute_mae(actual, predicted),
        "mape":      compute_mape(actual, predicted),
        "r_squared": compute_r2(actual, predicted),
    }