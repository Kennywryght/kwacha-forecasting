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
    if hasattr(d, 'date'):
        return d.date()
    return d


def _adjust_forecast_dates(raw: dict, horizon: int, start_date: date) -> dict:
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


# ── ARIMA light refit ──────────────────────────────────────────────────
def _refresh_arima(db: Session):
    """
    Re‑fit the ARIMA model on all available rates using its already‑tuned order.
    This brings its internal state up to today without a full hyperparameter search.
    """
    if "arima" not in _models:
        return
    arima = _models["arima"]
    rates = crud.get_all_rates_as_dataframe(db)
    if rates.empty:
        raise HTTPException(status_code=500, detail="No rate data for ARIMA")
    # Use the order that was already determined during training
    if not hasattr(arima, 'order'):
        raise HTTPException(status_code=500, detail="ARIMA order not set")
    arima.fit(rates)                # This will call ARIMA's fit() with the fixed order
    logger.info("ARIMA refreshed on latest data")
    _models["arima"] = arima


# ── Prophet history update ─────────────────────────────────────────────
def _refresh_prophet(db: Session):
    """
    Update the loaded Prophet model's history with all rates from the DB,
    so future forecasts start from tomorrow without retraining.
    """
    if "prophet" not in _models:
        return
    prophet = _models["prophet"]
    rates = crud.get_all_rates_as_dataframe(db)
    if rates.empty:
        raise HTTPException(status_code=500, detail="No rate data for Prophet")
    df = rates.rename(columns={"date": "ds", "rate": "y"})
    df["ds"] = pd.to_datetime(df["ds"])
    df = df.sort_values("ds")
    # Replace the internal history; the model parameters stay the same
    prophet.history = df
    logger.info(f"Prophet history updated up to {df['ds'].max()}")
    _models["prophet"] = prophet


# ── Prophet future generation ──────────────────────────────────────────
def _generate_prophet_future(prophet_model, horizon: int) -> dict:
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


# ── Endpoints ──────────────────────────────────────────────────────────

@router.get("/latest")
def get_latest_forecasts(
    horizon: int = Query(default=7, description="1, 7, or 30"),
    model:   str = Query(default="ensemble"),
    db:      Session = Depends(get_db),
):
    today = date.today()
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

    # Refresh models with current data
    _refresh_arima(db)
    _refresh_prophet(db)

    # ---- Individual models ----
    for model_name, model in _models.items():
        if model_name == "ensemble":
            continue
        try:
            if model_name == "prophet":
                raw = _generate_prophet_future(model, horizon)
            else:
                if not hasattr(model, 'is_fitted') or not model.is_fitted:
                    continue
                raw = model.forecast(horizon)

            adjusted = _adjust_forecast_dates(raw, horizon, tomorrow)

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

    # ---- Ensemble ----
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