import pandas as pd
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from db.database import SessionLocal
from db.crud import save_model_run
from ml.models.arima_model    import ARIMAForecaster
from ml.models.arimax_model   import ARIMAXForecaster
from ml.models.ensemble_model import EnsembleForecaster
from ml.utils.mlflow_tracker  import log_model_run
from core.config import get_settings
from core.logging_config import get_logger

logger   = get_logger(__name__)
settings = get_settings()

ARTIFACTS  = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../ml/artifacts"))
TRAIN_FROM = "2020-01-01"

def _save_to_db(model_name, metrics, params, mlflow_id, train_start, train_end):
    db = SessionLocal()
    try:
        save_model_run(
            db, model_name, metrics, params, mlflow_id,
            train_start.date() if hasattr(train_start, "date") else train_start,
            train_end.date()   if hasattr(train_end,   "date") else train_end,
        )
    finally:
        db.close()

# FIX: Added 'df' parameter to accept dataframe from pipeline
def train_models(df: pd.DataFrame):
    
    # Check for empty data
    if df.empty:
        logger.error("❌ Cannot train: DataFrame is empty.")
        return None, None, None

    df = df[df["date"] >= TRAIN_FROM].copy()
    df.reset_index(drop=True, inplace=True)

    logger.info(f"Training window: {df['date'].min().date()} to {df['date'].max().date()}")
    logger.info(f"Total rows: {len(df)}")

    train_end_idx = int(len(df) * 0.70)
    val_end_idx   = int(len(df) * 0.85)

    train_df = df.iloc[:train_end_idx].copy()
    val_df   = df.iloc[train_end_idx:val_end_idx].copy()
    test_df  = df.iloc[val_end_idx:].copy()

    os.makedirs(ARTIFACTS, exist_ok=True)

    # ── ARIMA ─────────────────────────────
    logger.info("=" * 55)
    logger.info("Training ARIMA")

    try:
        arima = ARIMAForecaster()
        arima.fit(train_df)
        
        MODEL_DIR = os.getenv("MODEL_DIR", "backend/ml/artifacts")
        arima.save(os.path.join(MODEL_DIR, "arima.pkl"))

        mid = log_model_run("arima", {"order": str(arima.order)}, arima.metrics)
        _save_to_db("arima", arima.metrics, {"order": str(arima.order)}, mid,
                    arima.train_start, arima.train_end)
    except Exception as e:
        logger.error(f"ARIMA Failed: {e}")
        arima = None

    # ── ARIMAX ────────────────────────────
    logger.info("=" * 55)
    logger.info("Training ARIMAX (FIXED)")

    try:
        arimax = ARIMAXForecaster()
        arimax.fit(train_df)
        arimax.save(os.path.join(ARTIFACTS, "arimax.pkl"))

        mid = log_model_run("arimax",
                            {"order": str(arimax.order), "exog": str(arimax.exog_cols)},
                            arimax.metrics)

        _save_to_db("arimax", arimax.metrics,
                    {"order": str(arimax.order), "exog": str(arimax.exog_cols)},
                    mid, arimax.train_start, arimax.train_end)
    except Exception as e:
        logger.error(f"ARIMAX Failed: {e}")
        arimax = None

    # ── STACKING ENSEMBLE ─────────────────
    logger.info("=" * 55)
    logger.info("Building Ensemble (STACKING)")
    
    ensemble = None
    if arima and arimax:
        try:
            ensemble = EnsembleForecaster(arima, arimax)
            ensemble.fit(train_df)
            ensemble.save(os.path.join(ARTIFACTS, "ensemble.pkl"))

            mid = log_model_run("ensemble",
                                {"type": "stacking"},
                                ensemble.metrics)

            _save_to_db("ensemble", ensemble.metrics,
                        {"type": "stacking"},
                        mid,
                        train_df["date"].iloc[0],
                        train_df["date"].iloc[-1])
        except Exception as e:
            logger.error(f"Ensemble Failed: {e}")

    logger.info("=" * 55)
    logger.info("TRAINING COMPLETE")
    if arima: logger.info(f"ARIMA    RMSE: {round(arima.metrics['rmse'],4)}")
    if arimax: logger.info(f"ARIMAX   RMSE: {round(arimax.metrics['rmse'],4)}")
    if ensemble: logger.info(f"Ensemble RMSE: {round(ensemble.metrics['rmse'],4)}")
    logger.info("=" * 55)

    return arima, arimax, ensemble
