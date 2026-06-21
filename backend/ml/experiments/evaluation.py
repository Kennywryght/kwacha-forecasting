"""Model evaluation utilities for comparing forecasting models.

This module provides standardized evaluation for all models
with consistent metrics and comparison capabilities.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List, Union
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

from ml.utils.metrics import compute_all_metrics
from core.logging_config import get_logger

logger = get_logger(__name__)


class ModelEvaluator:
    """
    Standardized model evaluation with consistent metrics.

    Features:
    - Normalizes outputs from different model APIs
    - Computes comprehensive metrics
    - Compares multiple models
    - Saves evaluation results
    """

    @staticmethod
    def normalize_output(output: Union[Dict, pd.DataFrame, tuple]) -> tuple:
        """
        Convert various model outputs to (y_true, y_pred) arrays.

        Args:
            output: Model prediction output

        Returns:
            Tuple of (y_true, y_pred) as numpy arrays

        Raises:
            ValueError: If output format is not recognized
        """
        # Dictionary format
        if isinstance(output, dict):
            # Try common keys
            y_true = output.get("y_true") or output.get("actual")
            y_pred = output.get("y_pred") or output.get("predicted")

            if y_true is not None and y_pred is not None:
                return np.array(y_true), np.array(y_pred)

            # Try dates dictionary format (from forecast methods)
            if "dates" in output and "predicted" in output:
                return np.array([]), np.array(output["predicted"])

            raise ValueError(f"Unrecognized dict format: {output.keys()}")

        # DataFrame format
        if isinstance(output, pd.DataFrame):
            if "y_true" in output.columns and "y_pred" in output.columns:
                return output["y_true"].values, output["y_pred"].values

            if "actual" in output.columns and "predicted" in output.columns:
                return output["actual"].values, output["predicted"].values

            raise ValueError("DataFrame must contain 'y_true' and 'y_pred' columns")

        # Tuple format
        if isinstance(output, tuple) and len(output) == 2:
            return np.array(output[0]), np.array(output[1])

        raise ValueError(f"Unknown output format: {type(output)}")

    def evaluate_model(
        self,
        model: Any,
        name: str,
        test_df: pd.DataFrame,
        horizon: Optional[int] = None,
        **predict_kwargs
    ) -> Dict[str, Any]:
        """
        Evaluate a single model on test data.

        Args:
            model: Fitted model with predict() method
            name: Model name
            test_df: Test DataFrame with 'rate' column
            horizon: Forecast horizon (for Prophet-style models)
            **predict_kwargs: Additional arguments for predict()

        Returns:
            Dictionary with model name and metrics
        """
        try:
            # Get predictions
            if hasattr(model, "predict"):
                if horizon is not None:
                    output = model.predict(horizon, **predict_kwargs)
                else:
                    output = model.predict(test_df, **predict_kwargs)
            else:
                raise ValueError(f"Model {name} has no predict() method")

            # Normalize output
            y_true, y_pred = self.normalize_output(output)

            # If no y_true, we can't compute metrics
            if len(y_true) == 0:
                logger.warning(f"{name}: No true values for evaluation")
                return {
                    "model": name,
                    "rmse": np.nan,
                    "mae": np.nan,
                    "mape": np.nan,
                    "r_squared": np.nan,
                    "n_samples": len(y_pred),
                    "error": "No true values"
                }

            # Align lengths
            min_len = min(len(y_true), len(y_pred))
            y_true = y_true[:min_len]
            y_pred = y_pred[:min_len]

            if min_len == 0:
                return {
                    "model": name,
                    "rmse": np.nan,
                    "mae": np.nan,
                    "mape": np.nan,
                    "r_squared": np.nan,
                    "n_samples": 0,
                    "error": "Empty predictions"
                }

            # Compute metrics
            metrics = compute_all_metrics(y_true, y_pred)

            return {
                "model": name,
                "rmse": metrics["rmse"],
                "mae": metrics["mae"],
                "mape": metrics["mape"],
                "r_squared": metrics["r_squared"],
                "n_samples": min_len,
            }

        except Exception as e:
            logger.error(f"{name} evaluation failed: {e}")
            return {
                "model": name,
                "rmse": np.nan,
                "mae": np.nan,
                "mape": np.nan,
                "r_squared": np.nan,
                "n_samples": 0,
                "error": str(e)
            }

    def evaluate_all(
        self,
        models: Dict[str, Any],
        test_df: pd.DataFrame,
        horizon: Optional[int] = None,
        **predict_kwargs
    ) -> pd.DataFrame:
        """
        Evaluate multiple models and return comparison DataFrame.

        Args:
            models: Dictionary of {name: model}
            test_df: Test DataFrame
            horizon: Forecast horizon for Prophet-style models
            **predict_kwargs: Additional arguments for predict()

        Returns:
            DataFrame sorted by RMSE with all metrics
        """
        results = []

        for name, model in models.items():
            # Prophet special case
            if name.lower() == "prophet" and horizon is None:
                horizon = len(test_df)

            result = self.evaluate_model(
                model, name, test_df,
                horizon=horizon,
                **predict_kwargs
            )
            results.append(result)

        df = pd.DataFrame(results)

        # Sort by RMSE if available
        if "rmse" in df.columns and not df["rmse"].isna().all():
            df = df.sort_values("rmse")

        return df

    def compare_predictions(
        self,
        predictions: Dict[str, np.ndarray],
        y_true: np.ndarray
    ) -> pd.DataFrame:
        """
        Compare pre-computed predictions.

        Args:
            predictions: Dictionary of {name: predictions}
            y_true: True values

        Returns:
            DataFrame with comparison metrics
        """
        results = []

        y_true = np.array(y_true)

        for name, y_pred in predictions.items():
            y_pred = np.array(y_pred)

            # Align lengths
            min_len = min(len(y_true), len(y_pred))
            y_true_aligned = y_true[:min_len]
            y_pred_aligned = y_pred[:min_len]

            if min_len == 0:
                continue

            metrics = compute_all_metrics(y_true_aligned, y_pred_aligned)

            results.append({
                "model": name,
                "rmse": metrics["rmse"],
                "mae": metrics["mae"],
                "mape": metrics["mape"],
                "r_squared": metrics["r_squared"],
                "n_samples": min_len
            })

        df = pd.DataFrame(results)

        if "rmse" in df.columns:
            df = df.sort_values("rmse")

        return df

    def save_evaluation(
        self,
        results_df: pd.DataFrame,
        output_path: str = "outputs/metrics/model_evaluation.csv"
    ) -> None:
        """
        Save evaluation results to CSV.

        Args:
            results_df: DataFrame from evaluate_all()
            output_path: Path to save CSV
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        results_df.to_csv(output_path, index=False)
        logger.info(f"✅ Evaluation saved to {output_path}")


# Convenience function
def quick_evaluate(
    model: Any,
    name: str,
    test_df: pd.DataFrame,
    **kwargs
) -> Dict[str, float]:
    """
    Quick evaluation of a single model.

    Args:
        model: Fitted model
        name: Model name
        test_df: Test DataFrame
        **kwargs: Additional arguments for ModelEvaluator.evaluate_model()

    Returns:
        Dictionary with metrics
    """
    evaluator = ModelEvaluator()
    result = evaluator.evaluate_model(model, name, test_df, **kwargs)
    return {k: v for k, v in result.items() if k != "model"}