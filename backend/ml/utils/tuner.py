"""Hyperparameter tuning module.

This module provides hyperparameter optimization for all models using Optuna.
"""

import optuna
import logging
import numpy as np
import pandas as pd
import os
import json
import joblib
from typing import Dict, Any, Optional, List
from sklearn.metrics import mean_squared_error

from ml.models.arima_model import ARIMAForecaster
from ml.models.arimax_model import ARIMAXForecaster
from ml.models.prophet_model import ProphetForecaster
from ml.models.lstm_model import LSTMForecaster
from ml.utils.metrics import compute_all_metrics

logger = logging.getLogger(__name__)

MODEL_DIR = "ml/artifacts"
TUNING_DIR = "outputs/tuning"
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(TUNING_DIR, exist_ok=True)

# ============================================================
# ARIMA Tuning
# ============================================================

def tune_arima_auto(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Find best ARIMA order using pmdarima auto_arima.

    Args:
        df: DataFrame with 'rate' column

    Returns:
        Dictionary with best order and metrics
    """
    try:
        from pmdarima import auto_arima
    except ImportError:
        logger.warning("pmdarima not installed, using default ARIMA order")
        return {"order": (1, 1, 1), "aic": None}
    
    series = df["rate"].values
    
    # Handle missing values
    series = series[~np.isnan(series)]
    
    if len(series) < 50:
        logger.warning("Too few data points for auto_arima")
        return {"order": (1, 1, 1), "aic": None}
    
    try:
        auto_model = auto_arima(
            series,
            seasonal=False,
            trace=False,
            error_action='ignore',
            suppress_warnings=True,
            stepwise=True,
            max_p=5,
            max_q=5,
            max_d=2,
            information_criterion='aic'
        )
        
        order = auto_model.order
        aic = auto_model.aic()
        
        logger.info(f"✅ Auto ARIMA order: {order}, AIC: {aic:.2f}")
        
        return {"order": order, "aic": aic}
        
    except Exception as e:
        logger.warning(f"Auto ARIMA failed: {e}")
        return {"order": (1, 1, 1), "aic": None}


def tune_arimax_auto(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Find best ARIMAX order with exogenous variables.

    Args:
        df: DataFrame with 'rate' and exogenous columns

    Returns:
        Dictionary with best order and metrics
    """
    try:
        from pmdarima import auto_arima
    except ImportError:
        logger.warning("pmdarima not installed, using default ARIMAX order")
        return {"order": (1, 1, 1), "aic": None}
    
    # Identify exogenous columns
    exclude_cols = ["date", "rate", "is_interpolated", "daily_return"]
    exog_cols = [c for c in df.columns if c not in exclude_cols]
    
    if not exog_cols:
        logger.warning("No exogenous columns found for ARIMAX")
        return {"order": (1, 1, 1), "aic": None}
    
    series = df["rate"].values
    exog = df[exog_cols].values
    
    # Handle missing values
    mask = ~np.isnan(series)
    series = series[mask]
    exog = exog[mask]
    
    if len(series) < 50:
        logger.warning("Too few data points for auto_arimax")
        return {"order": (1, 1, 1), "aic": None}
    
    try:
        auto_model = auto_arima(
            series,
            exogenous=exog,
            seasonal=False,
            trace=False,
            error_action='ignore',
            suppress_warnings=True,
            stepwise=True,
            max_p=5,
            max_q=5,
            max_d=2,
            information_criterion='aic'
        )
        
        order = auto_model.order
        aic = auto_model.aic()
        
        logger.info(f"✅ Auto ARIMAX order: {order}, AIC: {aic:.2f}")
        
        return {"order": order, "aic": aic}
        
    except Exception as e:
        logger.warning(f"Auto ARIMAX failed: {e}")
        return {"order": (1, 1, 1), "aic": None}


# ============================================================
# Prophet Tuning
# ============================================================

def tune_prophet(
    df: pd.DataFrame,
    n_trials: int = 20,
    timeout: Optional[int] = None
) -> Dict[str, Any]:
    """
    Tune Prophet hyperparameters using Optuna.

    Args:
        df: DataFrame with 'date' and 'rate' columns
        n_trials: Number of Optuna trials
        timeout: Timeout in seconds

    Returns:
        Dictionary with best parameters and metrics
    """
    try:
        from prophet import Prophet
    except ImportError:
        logger.warning("Prophet not installed")
        return {"best_params": {}, "best_rmse": None}
    
    # Prepare data
    prophet_df = df[["date", "rate"]].rename(columns={"date": "ds", "rate": "y"})
    prophet_df = prophet_df.dropna()
    
    if len(prophet_df) < 50:
        logger.warning("Too few data points for Prophet tuning")
        return {"best_params": {}, "best_rmse": None}
    
    # Split data
    train_size = int(len(prophet_df) * 0.8)
    train_df = prophet_df.iloc[:train_size]
    val_df = prophet_df.iloc[train_size:]
    
    if len(val_df) < 7:
        logger.warning("Validation set too small for Prophet tuning")
        return {"best_params": {}, "best_rmse": None}
    
    def objective(trial):
        params = {
            "changepoint_prior_scale": trial.suggest_float(
                "changepoint_prior_scale", 0.001, 0.5, log=True
            ),
            "seasonality_prior_scale": trial.suggest_float(
                "seasonality_prior_scale", 0.01, 10, log=True
            ),
            "holidays_prior_scale": trial.suggest_float(
                "holidays_prior_scale", 0.01, 10, log=True
            ),
            "seasonality_mode": trial.suggest_categorical(
                "seasonality_mode", ["additive", "multiplicative"]
            ),
            "weekly_seasonality": trial.suggest_categorical(
                "weekly_seasonality", [True, False]
            ),
        }
        
        try:
            model = Prophet(**params)
            model.fit(train_df)
            
            future = model.make_future_dataframe(
                periods=len(val_df),
                freq='D'
            )
            forecast = model.predict(future)
            
            preds = forecast.iloc[-len(val_df):]["yhat"].values
            actual = val_df["y"].values
            
            rmse = np.sqrt(mean_squared_error(actual, preds))
            return rmse
            
        except Exception:
            return float('inf')
    
    try:
        study = optuna.create_study(direction="minimize")
        study.optimize(objective, n_trials=n_trials, timeout=timeout)
        
        best_params = study.best_params
        best_rmse = study.best_value
        
        logger.info(f"✅ Prophet best RMSE: {best_rmse:.4f}")
        logger.info(f"   Parameters: {best_params}")
        
        # Save tuning results
        tuning_results = {
            "best_params": best_params,
            "best_rmse": best_rmse,
            "n_trials": n_trials
        }
        
        with open(os.path.join(TUNING_DIR, "prophet_tuning.json"), "w") as f:
            json.dump(tuning_results, f, indent=2)
        
        return tuning_results
        
    except Exception as e:
        logger.warning(f"Prophet tuning failed: {e}")
        return {"best_params": {}, "best_rmse": None}


# ============================================================
# LSTM Tuning
# ============================================================

def tune_lstm(
    df: pd.DataFrame,
    n_trials: int = 20,
    timeout: Optional[int] = None
) -> Dict[str, Any]:
    """
    Tune LSTM hyperparameters using Optuna.

    Args:
        df: DataFrame with 'rate' and features
        n_trials: Number of Optuna trials
        timeout: Timeout in seconds

    Returns:
        Dictionary with best parameters and metrics
    """
    # Split data
    split_idx = int(len(df) * 0.8)
    train_df = df.iloc[:split_idx]
    val_df = df.iloc[split_idx:]
    
    if len(train_df) < 100:
        logger.warning("Too few data points for LSTM tuning")
        return {"best_params": {}, "best_rmse": None}
    
    def objective(trial):
        params = {
            "sequence_length": trial.suggest_int("sequence_length", 10, 60, step=10),
            "lstm_units": [
                trial.suggest_int("lstm_units_1", 16, 128, step=16),
                trial.suggest_int("lstm_units_2", 8, 64, step=8)
            ],
            "dropout_rate": trial.suggest_float("dropout_rate", 0.0, 0.5),
            "dense_units": trial.suggest_int("dense_units", 8, 64, step=8),
            "learning_rate": trial.suggest_float(
                "learning_rate", 1e-4, 1e-2, log=True
            ),
            "batch_size": trial.suggest_categorical("batch_size", [16, 32, 64]),
            "epochs": trial.suggest_int("epochs", 20, 80, step=10),
            "use_bidirectional": trial.suggest_categorical(
                "use_bidirectional", [True, False]
            )
        }
        
        try:
            model = LSTMForecaster(**params)
            model.fit(train_df)
            
            pred_dict = model.predict(val_df)
            
            if not pred_dict or "y_pred" not in pred_dict:
                return float('inf')
            
            y_true = np.array(pred_dict["y_true"])
            y_pred = np.array(pred_dict["y_pred"])
            
            rmse = np.sqrt(mean_squared_error(y_true, y_pred))
            return rmse
            
        except Exception:
            return float('inf')
    
    try:
        study = optuna.create_study(direction="minimize")
        study.optimize(objective, n_trials=n_trials, timeout=timeout)
        
        best_params = study.best_params
        best_rmse = study.best_value
        
        logger.info(f"✅ LSTM best RMSE: {best_rmse:.4f}")
        logger.info(f"   Parameters: {best_params}")
        
        # Save tuning results
        tuning_results = {
            "best_params": best_params,
            "best_rmse": best_rmse,
            "n_trials": n_trials
        }
        
        with open(os.path.join(TUNING_DIR, "lstm_tuning.json"), "w") as f:
            json.dump(tuning_results, f, indent=2)
        
        return tuning_results
        
    except Exception as e:
        logger.warning(f"LSTM tuning failed: {e}")
        return {"best_params": {}, "best_rmse": None}


# ============================================================
# Ensemble Tuning
# ============================================================

def tune_ensemble(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Tune ensemble weights using validation data.

    Args:
        df: DataFrame with features

    Returns:
        Dictionary with best weights and metrics
    """
    # Split data
    split_idx = int(len(df) * 0.8)
    train_df = df.iloc[:split_idx]
    val_df = df.iloc[split_idx:]
    
    if len(train_df) < 50:
        logger.warning("Too few data points for ensemble tuning")
        return {"weights": {}, "best_rmse": None}
    
    try:
        # Train individual models
        models = {}
        
        # ARIMA
        arima = ARIMAForecaster(use_auto_order=True)
        arima.fit(train_df)
        models["arima"] = arima
        
        # ARIMAX
        arimax = ARIMAXForecaster(use_auto_order=True)
        arimax.fit(train_df)
        models["arimax"] = arimax
        
        # Prophet
        prophet = ProphetForecaster(weekly_seasonality=True)
        prophet.fit(train_df)
        models["prophet"] = prophet
        
        # Get validation predictions
        predictions = {}
        for name, model in models.items():
            if name in ["arima", "arimax"]:
                pred = model.predict(val_df)
                predictions[name] = np.array(pred["y_pred"])
            else:
                horizon = len(val_df)
                pred = model.predict(horizon)
                predictions[name] = np.array(pred["predicted"])
        
        # Get actual values
        y_true = val_df["rate"].values[:len(predictions["arima"])]
        
        # Find optimal weights
        from scipy.optimize import minimize
        
        n_models = len(predictions)
        pred_matrix = np.column_stack([predictions[name] for name in predictions])
        
        def objective(weights):
            weights = np.array(weights) / np.sum(weights)
            ensemble_pred = np.dot(pred_matrix, weights)
            return np.sqrt(mean_squared_error(y_true, ensemble_pred))
        
        # Initial weights
        initial_weights = np.ones(n_models) / n_models
        
        # Constraints: weights sum to 1, each weight >= 0
        constraints = {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}
        bounds = [(0, 1) for _ in range(n_models)]
        
        result = minimize(
            objective,
            initial_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )
        
        best_weights = result.x / np.sum(result.x)
        best_rmse = result.fun
        
        # Map weights to model names
        weights_dict = {
            name: float(best_weights[i])
            for i, name in enumerate(predictions.keys())
        }
        
        logger.info(f"✅ Ensemble best RMSE: {best_rmse:.4f}")
        logger.info(f"   Weights: {weights_dict}")
        
        return {
            "weights": weights_dict,
            "best_rmse": best_rmse
        }
        
    except Exception as e:
        logger.warning(f"Ensemble tuning failed: {e}")
        return {"weights": {}, "best_rmse": None}