import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from db.database import get_db
from db import crud
from core.logging_config import get_logger

router = APIRouter(prefix="/pipeline", tags=["Pipeline"])
logger = get_logger(__name__)


@router.post("/retrain")
def trigger_retrain(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    background_tasks.add_task(_run_retrain, db)
    return {"status": "retraining started in background"}


def _run_retrain(db: Session):
    try:
        from ml.utils.trainer import train_all_models
        logger.info("Background retrain triggered via API")
        train_all_models()
        logger.info("Background retrain complete")
    except Exception as e:
        logger.error(f"Background retrain failed: {e}")


@router.get("/status")
def pipeline_status(db: Session = Depends(get_db)):
    latest = crud.get_latest_rate(db)
    runs   = crud.get_active_model_runs(db)
    return {
        "data_latest_date": str(latest.date) if latest else None,
        "total_rates":      crud.get_rate_count(db),
        "active_models":    [r.model_name for r in runs],
        "models_trained":   len(runs) > 0,
    }