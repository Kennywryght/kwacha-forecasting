import optuna
import logging
import numpy as np
import pandas as pd
import os
import joblib
from sklearn.metrics import mean_squared_error

# Import your own model classes
from ml.models.arima_model import ARIMAForecaster
from ml.models.arimax_model import ARIMAXForecaster
from ml.models.prophet_model import ProphetForecaster
from ml.models.lstm_model import LSTMForecaster

logger = logging.getLogger(__name__)
MODEL_DIR = "ml/artifacts"
os.makedirs(MODEL_DIR, exist_ok=True)


def tune_arima_auto(df: pd.DataFrame) -> dict:
    """Find best ARIMA order using pmdarima auto_arima."""
    from pmdarima import auto_arima
    series = df["rate"].values
    auto_model = auto_arima(
        series, seasonal=False, trace=False,
        error_action='ignore', suppress_warnings=True,
        stepwise=True, max_p=5, max_q=5
    )
    order = auto_model.order
    logger.info(f"Auto ARIMA order: {order}")
    return {"order": order, "aic": auto_model.aic()}


def tune_arimax_auto(df: pd.DataFrame) -> dict:
    """Find best ARIMAX order with exogenous variables."""
    from pmdarima import auto_arima
    exog_cols = [c for c in df.columns if c not in ["date", "rate", "is_interpolated", "daily_return"]]
    exog = df[exog_cols].values if exog_cols else None
    series = df["rate"].values
    auto_model = auto_arima(
        series, exogenous=exog, seasonal=False, trace=False,
        error_action='ignore', suppress_warnings=True,
        stepwise=True, max_p=5, max_q=5
    )
    order = auto_model.order
    logger.info(f"Auto ARIMAX order: {order}")
    return {"order": order, "aic": auto_model.aic()}


def tune_prophet(df: pd.DataFrame, n_trials: int = 20) -> dict:
    """Tune Prophet hyperparameters using Optuna and time series split."""
    # Prophet requires 'ds' and 'y' columns
    prophet_df = df[["date", "rate"]].rename(columns={"date": "ds", "rate": "y"})
    train_size = int(len(prophet_df) * 0.8)
    train_df = prophet_df.iloc[:train_size]
    val_df = prophet_df.iloc[train_size:]

    def objective(trial):
        params = {
            "changepoint_prior_scale": trial.suggest_float("changepoint_prior_scale", 0.001, 0.5, log=True),
            "seasonality_prior_scale": trial.suggest_float("seasonality_prior_scale", 0.01, 10, log=True),
            "holidays_prior_scale": trial.suggest_float("holidays_prior_scale", 0.01, 10, log=True),
            "seasonality_mode": trial.suggest_categorical("seasonality_mode", ["additive", "multiplicative"]),
        }
        from prophet import Prophet
        model = Prophet(**params)
        model.fit(train_df)
        future = model.make_future_dataframe(periods=len(val_df), freq='D')
        forecast = model.predict(future)
        preds = forecast.iloc[-len(val_df):]["yhat"].values
        rmse = np.sqrt(mean_squared_error(val_df["y"].values, preds))
        return rmse

    study = optuna.create_study(direction="minimize")
    study.optimize(objective, n_trials=n_trials, show_progress_bar=True)
    best_params = study.best_params
    # Retrain best on full data
    from prophet import Prophet
    best_model = Prophet(**best_params)
    best_model.fit(prophet_df)
    # Save the model using its own serialisation
    import json
    model_path = os.path.join(MODEL_DIR, "prophet_tuned.json")
    with open(model_path, 'w') as f:
        json.dump(best_model.to_json(), f)  # Prophet models can be serialised to JSON
    logger.info(f"Tuned Prophet saved to {model_path}")
    return {"best_params": best_params, "best_rmse": study.best_value}


def tune_lstm(df: pd.DataFrame, n_trials: int = 20) -> dict:
    """Tune LSTM hyperparameters with Optuna."""
    # We'll assume LSTMForecaster can be instantiated with parameters
    # like hidden_units, dropout, learning_rate, epochs, etc.
    # Adjust according to your actual LSTM class.
    split_idx = int(len(df) * 0.8)
    train_df = df.iloc[:split_idx]
    val_df = df.iloc[split_idx:]

    def objective(trial):
        params = {
            "hidden_units": trial.suggest_int("hidden_units", 32, 256, step=32),
            "dropout": trial.suggest_float("dropout", 0.0, 0.5),
            "learning_rate": trial.suggest_float("learning_rate", 1e-4, 1e-2, log=True),
            "epochs": trial.suggest_int("epochs", 20, 100),
            "batch_size": trial.suggest_categorical("batch_size", [16, 32, 64]),
        }
        model = LSTMForecaster(**params)
        model.fit(train_df)
        pred_dict = model.predict(val_df)
        y_true = np.array(pred_dict["y_true"])
        y_pred = np.array(pred_dict["y_pred"])
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        return rmse

    study = optuna.create_study(direction="minimize")
    study.optimize(objective, n_trials=n_trials, show_progress_bar=True)
    best_params = study.best_params
    # Retrain best model on full data
    best_model = LSTMForecaster(**best_params)
    best_model.fit(df)
    # Save model (assuming torch.save or joblib)
    joblib.dump(best_model, os.path.join(MODEL_DIR, "lstm_tuned.pkl"))
    logger.info("Tuned LSTM saved.")
    return {"best_params": best_params, "best_rmse": study.best_value}