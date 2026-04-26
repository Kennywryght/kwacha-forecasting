import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db.database import get_db
from db import crud

router = APIRouter(prefix="/models", tags=["Models"])


@router.get("/performance")
def get_model_performance(db: Session = Depends(get_db)):
    runs = crud.get_active_model_runs(db)
    return {
        "models": [
            {
                "model_name":  r.model_name,
                "rmse":        r.rmse,
                "mae":         r.mae,
                "mape":        r.mape,
                "r_squared":   r.r_squared,
                "trained_at":  str(r.trained_at),
                "train_start": str(r.train_start),
                "train_end":   str(r.train_end),
                "is_active":   r.is_active,
            }
            for r in runs
        ]
    }