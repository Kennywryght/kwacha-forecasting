"""Model training orchestration module.

This module handles training all forecasting models with proper validation,
artifact management, and result logging.
"""

import logging
import warnings
import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import joblib
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

from ml.models.arima_model import ARIMAForecaster
from ml.models.arimax_model import ARIMAXForecaster
from ml.models.prophet_model import ProphetForecaster
from ml.models.lstm_model import LSTMForecaster
from ml.models.ensemble_model import EnsembleForecaster
from ml.utils.io_utils import ensure_dirs
from ml.utils.metrics import compute_all_metrics
from ml.utils.evaluation import evaluate_prediction_dict
from ml.utils.mlflow_tracker import log_model_run as log_to_mlflow
from ml.utils.db_logger import log_model_run as log_to_db

warnings.filterwarnings("ignore")
logger = logging.getLogger(__name__)

# ============================================================
# Configuration
# ============================================================

OUTPUT_DIR = "outputs/metrics"
PLOT_DIR = "outputs/plots"
MODEL_DIR = "ml/artifacts"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(PLOT_DIR, exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)

# Model configuration
DEFAULT_MODELS = ["ARIMA", "ARIMAX", "Prophet", "LSTM", "Ensemble"]
TEST_SPLIT_RATIO = 0.85
MIN_TRAIN_ROWS = 100


def clean_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and prepare dataset for modeling.
    
    Args:
        df: Raw DataFrame
        
    Returns:
        Cleaned DataFrame
    """
    df = df.copy()
    
    # Ensure date column
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")
    
    # Remove invalid rates
    df = df.dropna(subset=["rate"])
    
    # Handle infinities
    df = df.replace([np.inf, -np.inf], np.nan)
    
    # Forward fill then backward fill for remaining NaNs
    df = df.ffill().bfill()
    
    return df


def time_series_split(
    df: pd.DataFrame,
    test_size: float = 0.15,
    min_train: int = MIN_TRAIN_ROWS
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Split data chronologically for time series.

    Args:
        df: Input DataFrame (sorted by date)
        test_size: Proportion for test set
        min_train: Minimum training samples

    Returns:
        Tuple of (train_df, test_df)
    """
    df = df.copy()
    
    if "date" in df.columns:
        df = df.sort_values("date")
    
    n = len(df)
    train_size = int(n * (1 - test_size))
    
    # Ensure minimum training size
    if train_size < min_train:
        train_size = min_train
        logger.warning(f"Adjusted train size to minimum: {train_size}")
    
    return df.iloc[:train_size], df.iloc[train_size:]


def train_model_with_validation(
    model_class,
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    model_name: str,
    **kwargs
) -> Tuple[Optional[object], Optional[Dict]]:
    """
    Train a single model with validation.

    Args:
        model_class: Model class to instantiate
        train_df: Training data
        test_df: Testing data
        model_name: Name for logging
        **kwargs: Additional arguments for model

    Returns:
        Tuple of (trained_model, metrics)
    """
    try:
        logger.info(f"Training {model_name}...")
        
        # Instantiate model
        model = model_class(**kwargs)
        
        # Train
        model.fit(train_df)
        
        # Evaluate on test set
        if model_name == "Prophet":
            # Prophet uses horizon prediction
            horizon = len(test_df)
            pred_dict = model.predict(horizon)
            y_true = test_df["rate"].values[:len(pred_dict["predicted"])]
            y_pred = pred_dict["predicted"]
            metrics = compute_all_metrics(y_true, y_pred)
        elif model_name == "Ensemble":
            # Ensemble uses horizon prediction
            horizon = len(test_df)
            pred_dict = model.predict(horizon)
            y_true = test_df["rate"].values[:len(pred_dict["predicted"])]
            y_pred = pred_dict["predicted"]
            metrics = compute_all_metrics(y_true, y_pred)
        else:
            # Standard models
            pred_dict = model.predict(test_df)
            metrics = evaluate_prediction_dict(pred_dict)
        
        # Store metrics
        model.metrics = metrics
        
        logger.info(f"✅ {model_name} - RMSE: {metrics.get('rmse', 'N/A'):.4f}")
        
        return model, metrics
        
    except Exception as e:
        logger.exception(f"❌ {model_name} failed: {e}")
        return None, None


def train_models(
    df: pd.DataFrame,
    models_to_train: Optional[List[str]] = None,
    test_size: float = TEST_SPLIT_RATIO,
    save_artifacts: bool = True,
    log_to_db_flag: bool = True,
    log_to_mlflow_flag: bool = True
) -> Optional[pd.DataFrame]:
    """
    Train all configured models.

    Args:
        df: Preprocessed DataFrame
        models_to_train: List of model names to train (None = all)
        test_size: Proportion for test set
        save_artifacts: Whether to save model artifacts
        log_to_db_flag: Whether to log to database
        log_to_mlflow_flag: Whether to log to MLflow

    Returns:
        DataFrame with model comparison results, or None if failed
    """
    logger.info("🚀 Forecast pipeline started")
    ensure_dirs()
    
    # Clean and split data
    df = clean_dataset(df)
    
    if len(df) < MIN_TRAIN_ROWS:
        logger.error(f"❌ Insufficient data: {len(df)} rows (need {MIN_TRAIN_ROWS})")
        return None
    
    train_df, test_df = time_series_split(df, test_size=test_size)
    
    logger.info(f"📊 Train: {len(train_df)} rows, Test: {len(test_df)} rows")
    
    # Model definitions
    model_definitions = {
        "ARIMA": {
            "class": ARIMAForecaster,
            "kwargs": {"use_auto_order": True}
        },
        "ARIMAX": {
            "class": ARIMAXForecaster,
            "kwargs": {"use_auto_order": True}
        },
        "Prophet": {
            "class": ProphetForecaster,
            "kwargs": {
                "weekly_seasonality": True,
                "yearly_seasonality": False
            }
        },
        "LSTM": {
            "class": LSTMForecaster,
            "kwargs": {
                "sequence_length": 30,
                "lstm_units": [64, 32],
                "epochs": 50
            }
        },
        "Ensemble": {
            "class": EnsembleForecaster,
            "kwargs": {
                "weighting_scheme": "rmse",
                "min_weight": 0.05
            }
        }
    }
    
    # Filter models
    if models_to_train:
        model_definitions = {
            k: v for k, v in model_definitions.items()
            if k in models_to_train
        }
    
    # Train each model
    results = []
    model_objects = {}
    
    for model_name, config in model_definitions.items():
        model, metrics = train_model_with_validation(
            config["class"],
            train_df,
            test_df,
            model_name,
            **config["kwargs"]
        )
        
        if model and metrics:
            results.append({"model": model_name, **metrics})
            model_objects[model_name] = model
            
            # Save model
            if save_artifacts:
                model_path = os.path.join(MODEL_DIR, f"{model_name.lower()}.pkl")
                try:
                    if model_name == "LSTM":
                        # LSTM has special saving
                        model.save(os.path.join(MODEL_DIR, "lstm_model"))
                    else:
                        joblib.dump(model, model_path)
                    logger.info(f"💾 Saved {model_name} to {model_path}")
                except Exception as e:
                    logger.warning(f"Failed to save {model_name}: {e}")
            
            # Log to database
            if log_to_db_flag:
                try:
                    log_to_db(model_name, metrics)
                except Exception as e:
                    logger.warning(f"DB logging failed for {model_name}: {e}")
            
            # Log to MLflow
            if log_to_mlflow_flag:
                try:
                    log_to_mlflow(
                        model_name,
                        params=config["kwargs"],
                        metrics=metrics,
                        artifacts_dir=MODEL_DIR if save_artifacts else None
                    )
                except Exception as e:
                    logger.warning(f"MLflow logging failed for {model_name}: {e}")
    
    if not results:
        logger.error("❌ No models trained successfully")
        return None
    
    # Create comparison DataFrame
    results_df = pd.DataFrame(results)
    
    # Sort by RMSE
    if "rmse" in results_df.columns:
        results_df = results_df.sort_values("rmse")
    
    # Save comparison
    results_df.to_csv(os.path.join(OUTPUT_DIR, "model_comparison.csv"), index=False)
    
    # Create comparison plot
    try:
        plt.figure(figsize=(10, 6))
        bars = plt.bar(results_df["model"], results_df["rmse"])
        plt.title("Model RMSE Comparison", fontsize=14)
        plt.ylabel("RMSE", fontsize=12)
        plt.xlabel("Model", fontsize=12)
        plt.xticks(rotation=45, ha="right")
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                    f'{height:.2f}', ha='center', va='bottom', fontsize=9)
        
        plt.tight_layout()
        plt.savefig(os.path.join(PLOT_DIR, "model_comparison.png"), dpi=150)
        plt.close()
        logger.info(f"📊 Comparison plot saved to {PLOT_DIR}/model_comparison.png")
    except Exception as e:
        logger.warning(f"Failed to create comparison plot: {e}")
    
    # Save best model
    best_name = results_df.iloc[0]["model"]
    best_model = model_objects.get(best_name)
    
    if best_model and save_artifacts:
        try:
            if best_name == "LSTM":
                # Copy LSTM directory
                import shutil
                src = os.path.join(MODEL_DIR, "lstm_model")
                dst = os.path.join(MODEL_DIR, "best_model")
                if os.path.exists(dst):
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
            else:
                joblib.dump(best_model, os.path.join(MODEL_DIR, "best_model.pkl"))
            
            # Save best model info
            best_info = {
                "model": best_name,
                "metrics": results_df.iloc[0].to_dict(),
                "saved_at": datetime.now().isoformat()
            }
            with open(os.path.join(MODEL_DIR, "best_model_info.json"), "w") as f:
                json.dump(best_info, f, indent=2)
            
            logger.info(f"🏆 Best model '{best_name}' saved")
        except Exception as e:
            logger.warning(f"Failed to save best model: {e}")
    
    # Print summary
    print("\n" + "="*50)
    print("🏆 BEST MODEL:", best_name)
    print("="*50)
    print(results_df.iloc[0].to_dict())
    print("="*50 + "\n")
    
    logger.info(f"✅ Pipeline complete. Best model: {best_name}")
    
    return results_df


def load_best_model() -> Optional[object]:
    """
    Load the best saved model.

    Returns:
        Loaded model or None if not found
    """
    best_model_path = os.path.join(MODEL_DIR, "best_model.pkl")
    best_model_dir = os.path.join(MODEL_DIR, "best_model")
    
    # Check if best_model.pkl exists
    if os.path.exists(best_model_path):
        try:
            return joblib.load(best_model_path)
        except Exception as e:
            logger.warning(f"Failed to load best_model.pkl: {e}")
    
    # Check if best_model directory exists (LSTM)
    if os.path.exists(best_model_dir):
        try:
            model = LSTMForecaster()
            model.load(best_model_dir)
            return model
        except Exception as e:
            logger.warning(f"Failed to load best_model directory: {e}")
    
    # Try to find any saved model
    for model_name in ["arima", "arimax", "prophet", "lstm", "ensemble"]:
        model_path = os.path.join(MODEL_DIR, f"{model_name}.pkl")
        if os.path.exists(model_path):
            try:
                if model_name == "lstm":
                    model = LSTMForecaster()
                    model.load(os.path.join(MODEL_DIR, "lstm_model"))
                    return model
                else:
                    return joblib.load(model_path)
            except Exception:
                continue
    
    logger.warning("No saved model found")
    return None