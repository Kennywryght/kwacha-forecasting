import os
import sys
import pandas as pd
from datetime import date, timedelta, datetime
from prophet import Prophet

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from db.database import get_db
from db import crud
from db.models import Forecast
from core.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/forecasts", tags=["Forecasts"])

_models = {}

def set_models(models: dict):
    global _models
    _models = models


def _safe_date(d):
    """Convert Timestamp or datetime to date."""
    if hasattr(d, 'date'):
        return d.date()
    return d


def _adjust_forecast_dates(raw: dict, horizon: int, start_date: date) -> dict:
    """Ensure forecasts start from start_date and limit to horizon points."""
    dates = raw.get("dates", [])
    predicted = raw.get("predicted", [])
    lower = raw.get("lower_bound", []) or raw.get("lower", [])
    upper = raw.get("upper_bound", []) or raw.get("upper", [])

    clean_dates = [_safe_date(d) for d in dates]
    filtered = [(d, p, l, u) for d, p, l, u in zip(clean_dates, predicted, lower, upper) if d >= start_date]
    filtered = filtered[:horizon]

    if filtered:
        new_dates, predicted, lower, upper = zip(*filtered)
        return {
            "dates": list(new_dates),
            "predicted": list(predicted),
            "lower_bound": list(lower),
            "upper_bound": list(upper),
        }
    else:
        return {
            "dates": [],
            "predicted": [],
            "lower_bound": [],
            "upper_bound": [],
        }


# ── Prophet helpers ────────────────────────────────────────────────────
def _generate_prophet_future(prophet_model, horizon: int) -> dict:
    """Use a **loaded** Prophet model to generate future forecasts without refitting."""
    future = prophet_model.make_future_dataframe(periods=horizon, freq='D')
    forecast = prophet_model.predict(future)
    last_date = prophet_model.history["ds"].max()
    future_forecast = forecast[forecast['ds'] > last_date]
    return {
        "dates":      [_safe_date(d) for d in pd.to_datetime(future_forecast["ds"]).tolist()],
        "predicted":  future_forecast["yhat"].tolist(),
        "lower":      future_forecast["yhat_lower"].tolist(),
        "upper":      future_forecast["yhat_upper"].tolist(),
    }


# ── Forecast endpoints ─────────────────────────────────────────────────

@router.get("/latest")
def get_latest_forecasts(
    horizon: int = Query(default=7, description="1, 7, or 30"),
    model:   str = Query(default="ensemble"),
    db:      Session = Depends(get_db),
):
    today = date.today()

    # Only serve forecasts from DB if they were generated today
    records = crud.get_latest_forecasts(db, model_name=model, horizon=horizon)
    if records and records[0].forecast_date == today:
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
                }
                for r in records
            ],
        }

    # No fresh forecasts → tell the client to generate them
    raise HTTPException(
        status_code=404,
        detail=f"No {model} forecasts for today. Please run POST /api/v1/forecasts/generate?horizon={horizon}"
    )


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

    # ---- Individual models (ARIMA, Prophet, etc.) ----
    for model_name, model in _models.items():
        if model_name == "ensemble":
            continue

        try:
            # --- Prophet ---
            if model_name == "prophet":
                raw = _generate_prophet_future(model, horizon)
            else:
                # ARIMA or other – must have a forecast() method
                if not hasattr(model, 'is_fitted') or not model.is_fitted:
                    continue
                raw = model.forecast(horizon)

            adjusted = _adjust_forecast_dates(raw, horizon, tomorrow)

            # Save to DB
            crud.delete_forecasts(db, model_name, horizon, today)
            forecast_objects = []
            for d, p, lo, hi in zip(
                adjusted["dates"],
                adjusted["predicted"],
                adjusted["lower_bound"] if adjusted["lower_bound"] else [],
                adjusted["upper_bound"] if adjusted["upper_bound"] else []
            ):
                forecast_objects.append(Forecast(
                    model_name=model_name,
                    horizon_days=horizon,
                    forecast_date=today,
                    target_date=d,
                    predicted_rate=p,
                    lower_bound=lo,
                    upper_bound=hi,
                ))
            crud.save_forecasts_bulk(db, forecast_objects)

            results[model_name] = {
                "status": "ok",
                "points": len(forecast_objects),
                "metrics": getattr(model, "metrics", None),
            }
        except Exception as e:
            results[model_name] = {"status": "error", "detail": str(e)}

    # ---- Ensemble (average of today's forecasts) ----
    try:
        model_forecasts = {}
        for name in _models.keys():
            if name == "ensemble":
                continue
            recs = crud.get_latest_forecasts(db, name, horizon)
            if recs and recs[0].forecast_date == today:
                model_forecasts[name] = recs

        if model_forecasts:
            date_sets = [set(r.target_date for r in recs) for recs in model_forecasts.values()]
            common_dates = sorted(set.intersection(*date_sets))[:horizon]

            forecast_objects = []
            for d in common_dates:
                preds, lowers, uppers = [], [], []
                for recs in model_forecasts.values():
                    r = next(r for r in recs if r.target_date == d)
                    preds.append(r.predicted_rate)
                    if r.lower_bound is not None:
                        lowers.append(r.lower_bound)
                    if r.upper_bound is not None:
                        uppers.append(r.upper_bound)
                forecast_objects.append(Forecast(
                    model_name="ensemble",
                    horizon_days=horizon,
                    forecast_date=today,
                    target_date=d,
                    predicted_rate=sum(preds) / len(preds),
                    lower_bound=sum(lowers) / len(lowers) if lowers else None,
                    upper_bound=sum(uppers) / len(uppers) if uppers else None,
                ))

            crud.delete_forecasts(db, "ensemble", horizon, today)
            crud.save_forecasts_bulk(db, forecast_objects)
            results["ensemble"] = {
                "status": "ok",
                "points": len(forecast_objects),
                "metrics": None,
            }
        else:
            results["ensemble"] = {"status": "error", "detail": "No individual forecasts to combine"}
    except Exception as e:
        results["ensemble"] = {"status": "error", "detail": str(e)}

    return {"horizon_days": horizon, "results": results, "generated_at": str(today)}


@router.get("/all")
def get_all_model_forecasts(
    horizon: int = Query(default=7),
    db:      Session = Depends(get_db),
):
    result = {}
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