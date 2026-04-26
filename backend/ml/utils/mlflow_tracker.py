import mlflow
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from core.config import get_settings
from core.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()


def setup_mlflow():
    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    mlflow.set_experiment(settings.mlflow_experiment_name)
    logger.info(f"MLflow tracking: {settings.mlflow_tracking_uri}")


def log_model_run(model_name: str, params: dict, metrics: dict, artifacts_dir: str = None):
    setup_mlflow()
    with mlflow.start_run(run_name=model_name) as run:
        mlflow.log_params(params)
        mlflow.log_metrics(metrics)
        if artifacts_dir and os.path.exists(artifacts_dir):
            mlflow.log_artifacts(artifacts_dir)
        run_id = run.info.run_id
        logger.info(f"MLflow run logged | model={model_name} | run_id={run_id}")
        logger.info(f"  RMSE={metrics.get('rmse', 'N/A'):.4f} | "
                    f"MAE={metrics.get('mae', 'N/A'):.4f} | "
                    f"MAPE={metrics.get('mape', 'N/A'):.4f}%")
        return run_id