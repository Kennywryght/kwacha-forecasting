import pandas as pd
from prophet import Prophet
from datetime import date
import joblib
import os
import logging
import numpy as np

logger = logging.getLogger(__name__)


class ProphetForecaster:
    def __init__(self, model_path="ml/artifacts/prophet.pkl"):
        # model holds the trained Prophet object, None until fit() is called
        self.model = None

        # path where the serialized model artifact will be written to / read from
        self.model_path = model_path

        # populated after fit() with rmse, mae, mape, r_squared
        self.metrics = {}

        # guard flag checked before prediction to prevent calling predict on an untrained model
        self.is_fitted = False

        # trainer.py reads these after fit() to log the run to the database.
        # SQLAlchemy's Date column requires datetime.date objects, not strings,
        # so we store them as date() and never as strftime() strings.
        self.train_start = None
        self.train_end = None

        # the macro variables passed to Prophet as additional regressors.
        # every column listed here that is present in the incoming dataframe
        # will be wired into the model; missing columns are silently skipped.
        self.exog_cols = [
            "Inflation",
            "Foreign_Reserves",
            "Lending_Interest_Rate",
            "us_fed_rate",
            "inflation_diff",
            "interest_rate_diff",
        ]
        
        self.regressor_cols = []

    def fit(self, df: pd.DataFrame) -> None:
        logger.info("Prophet: Preparing data...")

        # Prophet is strict about column names: it needs 'ds' (datestamp) and 'y' (target).
        # validate early so the error message is useful rather than a cryptic KeyError later.
        if "date" not in df.columns or "rate" not in df.columns:
            raise ValueError(
                f"Missing required columns. Found: {df.columns.tolist()}"
            )

        # rename to the Prophet-expected column names before anything else
        df_prophet = df.copy().rename(columns={"date": "ds", "rate": "y"})

        # .date() returns a datetime.date object, which is what SQLAlchemy's
        # Date column type expects. using strftime() here would produce a string
        # and cause a TypeError on db.commit().
        self.train_start = df_prophet["ds"].min().date()
        self.train_end = df_prophet["ds"].max().date()

        # keep only ds, y, and whichever exog columns are actually in the dataframe.
        # dropping unrelated columns avoids Prophet warnings about unknown regressors.
        cols = ["ds", "y"] + [c for c in self.exog_cols if c in df_prophet.columns]
        df_prophet = df_prophet[cols]
        
        self.regressor_cols = [c for c in self.exog_cols if c in df_prophet.columns]

        # instantiate a fresh Prophet model for the final fit on the full dataset
        self.model = Prophet()

        # register each available exogenous variable as an additional regressor.
        # Prophet treats these as extra linear features on top of trend + seasonality.
        for col in self.exog_cols:
            if col in df_prophet.columns:
                self.model.add_regressor(col)

        logger.info(
            f"Prophet: Using exogenous variables: "
            f"{[c for c in self.exog_cols if c in df_prophet.columns]}"
        )

        # fit the full-dataset model; this is what gets saved and used for forecasting
        self.model.fit(df_prophet)

        # --- walk-forward evaluation on a held-out tail window ---
        # a separate eval_model is trained on everything before the window
        # so there is no data leakage into the reported metrics
        horizon = 60
        if len(df_prophet) > horizon:
            train = df_prophet.iloc[:-horizon].copy()
            test = df_prophet.iloc[-horizon:].copy()
            
            # ensure no missing values in the regressors
            train = train.dropna()
            test = test.dropna()

            eval_model = Prophet()
            
            # add regressors before any fitting happens
            for col in self.exog_cols:
                if col in train.columns:
                    eval_model.add_regressor(col)
                

            eval_model.fit(train)
            
            future =test.drop(columns=["y"])

            # Prophet's predict() expects 'ds' plus any regressors;
            # drop 'y' because that is the value the model is supposed to produce
            forecast = eval_model.predict(future)

            y_true = test["y"].values
            y_pred = forecast["yhat"].values

            rmse = np.sqrt(np.mean((y_true - y_pred) ** 2))
            mae = np.mean(np.abs(y_true - y_pred))
            mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100
            r2 = 1 - (
                np.sum((y_true - y_pred) ** 2)
                / np.sum((y_true - np.mean(y_true)) ** 2)
            )

            self.metrics = {
                "rmse": rmse,
                "mae": mae,
                "mape": mape,
                "r_squared": r2,
            }

            logger.info(
                f"Prophet evaluation: RMSE={rmse:.4f} MAE={mae:.4f} "
                f"MAPE={mape:.4f}% R2={r2:.4f}"
            )

        # mark the model as ready; predict() checks this before doing anything
        self.is_fitted = True

    def predict(self, df: pd.DataFrame, periods: int = 30) -> pd.DataFrame:
        if self.model is None:
            raise ValueError("Model not trained yet")

        # rename 'date' to 'ds'; the caller is expected to pass a future dataframe
        # that already contains the exog columns for the forecast horizon
        df_future = df.copy().rename(columns={"date": "ds"})

        # keep only ds and the regressors the model knows about
        cols = ["ds"] + [c for c in self.exog_cols if c in df_future.columns]
        df_future = df_future[cols]

        forecast = self.model.predict(df_future)

        # yhat is the point forecast; yhat_lower / yhat_upper are the 80% uncertainty bounds
        return forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]]

    def save(self, path: str = None):
        path = path or self.model_path

        # create the artifacts directory if it does not already exist
        os.makedirs(os.path.dirname(path), exist_ok=True)

        # store train_start / train_end as ISO strings inside the pickle so they
        # survive serialization cleanly. load() converts them back to date objects.
        joblib.dump(
            {
                "model": self.model,
                "metrics": self.metrics,
                "train_start": self.train_start.isoformat() if self.train_start else None,
                "train_end": self.train_end.isoformat() if self.train_end else None,
            },
            path,
        )

        logger.info(f"Prophet model saved to {path}")

    def load(self, path: str = None):
        path = path or self.model_path

        data = joblib.load(path)
        self.model = data["model"]
        self.metrics = data.get("metrics", {})

        # convert the ISO strings back to datetime.date objects so the loaded
        # object behaves identically to one that just finished training
        raw_start = data.get("train_start")
        raw_end = data.get("train_end")
        self.train_start = date.fromisoformat(raw_start) if raw_start else None
        self.train_end = date.fromisoformat(raw_end) if raw_end else None

        self.is_fitted = True

        logger.info(f"Prophet model loaded from {path}")