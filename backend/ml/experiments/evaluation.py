import numpy as np
import pandas as pd
from ml.utils.metrics import compute_all_metrics


class ModelEvaluator:

    # -------------------------------------------------
    # STANDARDIZE OUTPUT FROM ANY MODEL
    # -------------------------------------------------
    @staticmethod
    def normalize_output(output):
        """
        Converts all model outputs into:
        y_true, y_pred arrays
        """

        if isinstance(output, dict):
            return np.array(output["y_true"]), np.array(output["y_pred"])

        if isinstance(output, pd.DataFrame):
            return (
                output["y_true"].values,
                output["y_pred"].values
            )

        raise ValueError("Unknown model output format")

    # -------------------------------------------------
    # EVALUATE ONE MODEL
    # -------------------------------------------------
    def evaluate_model(self, model, name, test_df, horizon=None):

        try:
            # Prophet uses horizon
            if hasattr(model, "predict") and horizon is not None:
                output = model.predict(horizon)

            else:
                output = model.predict(test_df)

            y_true, y_pred = self.normalize_output(output)

            metrics = compute_all_metrics(y_true, y_pred)

            return {
                "model": name,
                **metrics
            }

        except Exception as e:
            return {
                "model": name,
                "rmse": 9999,
                "mae": 9999,
                "mape": 9999,
                "r_squared": -999,
                "error": str(e)
            }

    # -------------------------------------------------
    # COMPARE ALL MODELS
    # -------------------------------------------------
    def evaluate_all(self, models, train_df, test_df):

        results = []

        for name, model in models.items():

            # Prophet special case
            if name.lower() == "prophet":
                horizon = len(test_df)
                res = self.evaluate_model(
                    model,
                    name,
                    test_df,
                    horizon=horizon
                )
            else:
                res = self.evaluate_model(
                    model,
                    name,
                    test_df
                )

            results.append(res)

        df = pd.DataFrame(results)

        df = df.sort_values("rmse")

        return df