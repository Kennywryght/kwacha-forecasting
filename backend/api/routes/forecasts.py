import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from db.database import get_db
from db import crud
from datetime import date, timedelta
from typing import Optional
from db.models import Forecast       # for bulk insert

router = APIRouter(prefix="/forecasts", tags=["Forecasts"])

_models = {}

def set_models(models: dict):
    global _models
    _models = models


def _adjust_forecast_dates(raw: dict, horizon: int, start_date: date) -> dict:
    """Replace raw['dates'] with a sequence starting from start_date."""
    new_dates = [start_date + timedelta(days=i+1) for i in range(horizon)]
    return {
        "dates":       new_dates,                              # still date objects
        "predicted":   raw["predicted"][:horizon],
        "lower_bound": raw["lower_bound"][:horizon] if "lower_bound" in raw else None,
        "upper_bound": raw["upper_bound"][:horizon] if "upper_bound" in raw else None,
    }


@router.get("/latest")
def get_latest_forecasts(
    horizon: int     = Query(default=7, description="1, 7, or 30"),
    model:   str     = Query(default="ensemble"),
    db:      Session = Depends(get_db),
):
    records = crud.get_latest_forecasts(db, model_name=model, horizon=horizon)

    if not records:
        if model in _models and _models[model].is_fitted:
            raw = _models[model].predict(horizon)
            tomorrow = date.today() + timedelta(days=1)
            adjusted = _adjust_forecast_dates(raw, horizon, tomorrow)
            return {
                "model_name":    model,
                "forecast_date": str(date.today()),
                "horizon_days":  horizon,
                "forecasts": [
                    {
                        "target_date":    str(d),
                        "predicted_rate": p,
                        "lower_bound":    lo if lo is not None else None,
                        "upper_bound":    hi if hi is not None else None,
                        "horizon_days":   horizon,
                    }
                    for d, p, lo, hi in zip(
                        adjusted["dates"],
                        adjusted["predicted"],
                        adjusted["lower_bound"] if adjusted["lower_bound"] else [],
                        adjusted["upper_bound"] if adjusted["upper_bound"] else []
                    )
                ],
                "metrics": _models[model].metrics if hasattr(_models[model], "metrics") else None,
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
    horizon: int = Query(default=7),
    db:      Session = Depends(get_db),
):
    if not _models:
        raise HTTPException(status_code=503, detail="Models not loaded")

    today = date.today()
    tomorrow = today + timedelta(days=1)
    results = {}

    for model_name, model in _models.items():
        if not model.is_fitted:
            continue
        try:
            raw = model.predict(horizon)
            adjusted = _adjust_forecast_dates(raw, horizon, tomorrow)

            # Remove previous forecasts of this model/horizon/today
            crud.delete_forecasts(db, model_name, horizon, today)   # today is a date object

            # Build Forecast ORM objects – pass actual date objects
            forecast_objects = []
            for d, p, lo, hi in zip(
                adjusted["dates"],                   # already datetime.date
                adjusted["predicted"],
                adjusted["lower_bound"] if adjusted["lower_bound"] else [],
                adjusted["upper_bound"] if adjusted["upper_bound"] else []
            ):
                forecast_objects.append(Forecast(
                    model_name=model_name,
                    horizon_days=horizon,
                    forecast_date=today,              # date object
                    target_date=d,                    # date object
                    predicted_rate=p,
                    lower_bound=lo,
                    upper_bound=hi,
                ))

            crud.save_forecasts_bulk(db, forecast_objects)

            results[model_name] = {
                "status":   "ok",
                "points":   len(forecast_objects),
                "metrics":  model.metrics if hasattr(model, "metrics") else None,
            }
        except Exception as e:
            results[model_name] = {"status": "error", "detail": str(e)}

    return {"horizon_days": horizon, "results": results, "generated_at": str(today)}

@router.get("/all")
def get_all_model_forecasts(
    horizon: int = Query(default=7),
    db:      Session = Depends(get_db),
):
    result = {}
    # Only iterate over models that are actually loaded (arima, arimax, ensemble)
    for model_name in _models.keys():
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