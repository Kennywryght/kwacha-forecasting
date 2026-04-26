import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from db.database import get_db
from db import crud
from datetime import date
from typing import Optional

router = APIRouter(prefix="/forecasts", tags=["Forecasts"])

# Models loaded once at startup — imported from main.py state
_models = {}

def set_models(models: dict):
    global _models
    _models = models


@router.get("/latest")
def get_latest_forecasts(
    horizon: int     = Query(default=7, description="1, 7, or 30"),
    model:   str     = Query(default="ensemble"),
    db:      Session = Depends(get_db),
):
    records = crud.get_latest_forecasts(db, model_name=model, horizon=horizon)

    if not records:
        # No stored forecasts — generate on the fly if model is loaded
        if model in _models and _models[model].is_fitted:
            raw = _models[model].predict(horizon)
            return {
                "model_name":    model,
                "forecast_date": str(date.today()),
                "horizon_days":  horizon,
                "forecasts": [
                    {
                        "target_date":   d,
                        "predicted_rate": p,
                        "lower_bound":   lo,
                        "upper_bound":   hi,
                        "horizon_days":  horizon,
                    }
                    for d, p, lo, hi in zip(
                        raw["dates"], raw["predicted"],
                        raw["lower_bound"], raw["upper_bound"]
                    )
                ],
                "metrics": _models[model].metrics,
            }
        raise HTTPException(status_code=404, detail="No forecasts found. Run /generate first.")

    return {
        "model_name":    model,
        "forecast_date": str(records[0].forecast_date),
        "horizon_days":  horizon,
        "forecasts": [
            {
                "target_date":    str(r.target_date),
                "predicted_rate": r.predicted_rate,
                "lower_bound":    r.lower_bound,
                "upper_bound":    r.upper_bound,
                "horizon_days":   r.horizon_days,
            }
            for r in records
        ],
    }


@router.post("/generate")
def generate_forecasts(
    horizon: int     = Query(default=7),
    db:      Session = Depends(get_db),
):
    if not _models:
        raise HTTPException(status_code=503, detail="Models not loaded")

    results = {}
    for model_name, model in _models.items():
        if not model.is_fitted:
            continue
        try:
            raw = model.predict(horizon)
            crud.save_forecasts(db, model_name, horizon, raw)
            results[model_name] = {
                "status":   "ok",
                "points":   len(raw["dates"]),
                "metrics":  model.metrics,
            }
        except Exception as e:
            results[model_name] = {"status": "error", "detail": str(e)}

    return {"horizon_days": horizon, "results": results, "generated_at": str(date.today())}


@router.get("/all")
def get_all_model_forecasts(
    horizon: int     = Query(default=7),
    db:      Session = Depends(get_db),
):
    result = {}
    for model_name in ["arima", "arimax", "lstm", "ensemble"]:
        records = crud.get_latest_forecasts(db, model_name, horizon)
        if records:
            result[model_name] = {
                "model_name":    model_name,
                "forecast_date": str(records[0].forecast_date),
                "horizon_days":  horizon,
                "forecasts": [
                    {
                        "target_date":    str(r.target_date),
                        "predicted_rate": r.predicted_rate,
                        "lower_bound":    r.lower_bound,
                        "upper_bound":    r.upper_bound,
                    }
                    for r in records
                ],
            }
    return result