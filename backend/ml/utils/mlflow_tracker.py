"""MLflow tracking module for experiment management.

This module provides utilities for logging experiments, models,
and artifacts to MLflow.
"""

import os
import sys
import mlflow
import mlflow.sklearn
from typing import Dict, Any, Optional
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from core.config import get_settings
from core.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()


def setup_mlflow() -> None:
    """
    Configure MLflow tracking URI and experiment.
    """
    try:
        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
        mlflow.set_experiment(settings.mlflow_experiment_name)
        logger.info(f"✅ MLflow tracking: {settings.mlflow_tracking_uri}")
        logger.info(f"   Experiment: {settings.mlflow_experiment_name}")
    except Exception as e:
        logger.warning(f"MLflow setup failed: {e}")


def log_model_run(
    model_name: str,
    params: Dict[str, Any],
    metrics: Dict[str, float],
    artifacts_dir: Optional[str] = None,
    model_object: Optional[Any] = None
) -> Optional[str]:
    """
    Log a model run to MLflow.

    Args:
        model_name: Name of the model
        params: Model parameters
        metrics: Model metrics
        artifacts_dir: Directory containing artifacts to log
        model_object: Model object to log

    Returns:
        MLflow run ID, or None if failed
    """
    try:
        setup_mlflow()
        
        with mlflow.start_run(run_name=f"{model_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}") as run:
            # Log parameters
            if params:
                mlflow.log_params(params)
            
            # Log metrics
            if metrics:
                mlflow.log_metrics(metrics)
            
            # Log artifacts
            if artifacts_dir and os.path.exists(artifacts_dir):
                mlflow.log_artifacts(artifacts_dir)
            
            # Log model
            if model_object is not None:
                try:
                    # Try to log with sklearn if compatible
                    mlflow.sklearn.log_model(model_object, "model")
                except Exception:
                    # Fallback: just log as artifact
                    import tempfile
                    import joblib
                    with tempfile.NamedTemporaryFile(suffix='.pkl', delete=False) as f:
                        joblib.dump(model_object, f.name)
                        mlflow.log_artifact(f.name, "model")
                    os.unlink(f.name)
            
            run_id = run.info.run_id
            logger.info(f"✅ MLflow run logged | model={model_name} | run_id={run_id}")
            
            if metrics:
                logger.info(f"   RMSE={metrics.get('rmse', 'N/A'):.4f} | "
                          f"MAE={metrics.get('mae', 'N/A'):.4f} | "
                          f"MAPE={metrics.get('mape', 'N/A'):.4f}%")
            
            return run_id
            
    except Exception as e:
        logger.warning(f"MLflow logging failed: {e}")
        return None


def get_latest_run(model_name: str) -> Optional[Dict[str, Any]]:
    """
    Get the latest run for a given model.

    Args:
        model_name: Name of the model

    Returns:
        Dictionary with run info, or None if not found
    """
    try:
        setup_mlflow()
        
        # Search for runs
        runs = mlflow.search_runs(
            experiment_names=[settings.mlflow_experiment_name],
            filter_string=f"tags.mlflow.runName LIKE '{model_name}%'",
            order_by=["start_time DESC"],
            max_results=1
        )
        
        if len(runs) == 0:
            return None
        
        run = runs.iloc[0]
        return {
            "run_id": run.get("run_id"),
            "experiment_id": run.get("experiment_id"),
            "metrics": {
                col.replace("metrics.", ""): run[col]
                for col in run.index
                if col.startswith("metrics.")
            },
            "start_time": run.get("start_time")
        }
        
    except Exception as e:
        logger.warning(f"Failed to get latest run: {e}")
        return None


def register_model(
    run_id: str,
    model_name: str,
    version: Optional[str] = None
) -> Optional[str]:
    """
    Register a model in MLflow Model Registry.

    Args:
        run_id: MLflow run ID
        model_name: Name for the registered model
        version: Model version (optional)

    Returns:
        Registered model version, or None if failed
    """
    try:
        setup_mlflow()
        
        # Register model
        model_uri = f"runs:/{run_id}/model"
        result = mlflow.register_model(model_uri, model_name)
        
        logger.info(f"✅ Model registered: {model_name} (version {result.version})")
        return result.version
        
    except Exception as e:
        logger.warning(f"Model registration failed: {e}")
        return None