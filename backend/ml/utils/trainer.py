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


def load_processed_data() -> pd.DataFrame:
    path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../../data/processed/mwk_usd_clean.csv")
    )
    df = pd.read_csv(path, parse_dates=["date"])
    df.sort_values("date", inplace=True)
    df.reset_index(drop=True, inplace=True)

    logger.info(f"Full dataset loaded: {len(df)} rows | {df['date'].min().date()} to {df['date'].max().date()}")
    return df


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


def train_all_models():
    df = load_processed_data()

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

    arima = ARIMAForecaster()
    arima.fit(train_df)
    arima.save(os.path.join(ARTIFACTS, "arima.pkl"))

    mid = log_model_run("arima", {"order": str(arima.order)}, arima.metrics)
    _save_to_db("arima", arima.metrics, {"order": str(arima.order)}, mid,
                arima.train_start, arima.train_end)

    # ── ARIMAX ────────────────────────────
    logger.info("=" * 55)
    logger.info("Training ARIMAX (FIXED)")

    arimax = ARIMAXForecaster()
    arimax.fit(train_df)
    arimax.save(os.path.join(ARTIFACTS, "arimax.pkl"))

    mid = log_model_run("arimax",
                        {"order": str(arimax.order), "exog": str(arimax.exog_cols)},
                        arimax.metrics)

    _save_to_db("arimax", arimax.metrics,
                {"order": str(arimax.order), "exog": str(arimax.exog_cols)},
                mid, arimax.train_start, arimax.train_end)

    # ── STACKING ENSEMBLE ─────────────────
    logger.info("=" * 55)
    logger.info("Building Ensemble (STACKING)")

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

    logger.info("=" * 55)
    logger.info("ALL MODELS TRAINED")
    logger.info(f"ARIMA    RMSE: {round(arima.metrics['rmse'],4)}")
    logger.info(f"ARIMAX   RMSE: {round(arimax.metrics['rmse'],4)}")
    logger.info(f"Ensemble RMSE: {round(ensemble.metrics['rmse'],4)}")
    logger.info("=" * 55)

    return arima, arimax, ensemble