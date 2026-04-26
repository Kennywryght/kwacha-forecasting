import os
import sys

# Windows-safe path resolution
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend"))
sys.path.insert(0, backend_path)

from ml.utils.trainer import train_all_models
from core.logging_config import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)

if __name__ == "__main__":
    logger.info("Starting model training pipeline...")
    arima, arimax, ensemble = train_all_models()
    logger.info("Training complete.")
    logger.info("  ARIMA   RMSE: " + str(round(arima.metrics["rmse"],   2)) +
                "  MAPE: " + str(round(arima.metrics["mape"],   4)) + "%")
    logger.info("  ARIMAX  RMSE: " + str(round(arimax.metrics["rmse"],  2)) +
                "  MAPE: " + str(round(arimax.metrics["mape"],  4)) + "%")
    logger.info("  Ensemble RMSE: " + str(round(ensemble.metrics["rmse"],2)) +
                "  MAPE: " + str(round(ensemble.metrics["mape"],4)) + "%")