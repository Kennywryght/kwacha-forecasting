import os
import sys
import io, csv
from fastapi import Response
import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta
from threading import Lock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from db.database import get_db, SessionLocal
from db import crud
from db.models import Forecast
from core.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/forecasts", tags=["Forecasts"])

# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL STATE
# ═══════════════════════════════════════════════════════════════════════════════

_models = {}
_training_lock = Lock()

_generation_state = {
    "in_progress": False,
    "started_at": None,
    "horizon": None,
    "completed_at": None,
    "error": None,
}


def set_models(models: dict):
    global _models
    _models = models


def get_loaded_model_names() -> list:
    return list(_models.keys())


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def _safe_date(d):
    if hasattr(d, 'date'):
        return d.date()
    return d


def _adjust_forecast_dates(raw: dict, horizon: int, start_date: date) -> dict:
    dates = raw.get("dates", [])
    predicted = raw.get("predicted", [])
    lower = raw.get("lower_bound", []) or raw.get("lower", [])
    upper = raw.get("upper_bound", []) or raw.get("upper", [])

    if hasattr(predicted, 'tolist'):
        predicted = predicted.tolist()
    elif hasattr(predicted, 'values'):
        predicted = predicted.values.tolist()
    predicted = list(predicted) if not isinstance(predicted, list) else predicted
    
    if hasattr(lower, 'tolist'):
        lower = lower.tolist()
    elif hasattr(lower, 'values'):
        lower = lower.values.tolist()
    lower = list(lower) if not isinstance(lower, list) else lower
    
    if hasattr(upper, 'tolist'):
        upper = upper.tolist()
    elif hasattr(upper, 'values'):
        upper = upper.values.tolist()
    upper = list(upper) if not isinstance(upper, list) else upper

    clean_dates = []
    for d in dates:
        if isinstance(d, str):
            clean_dates.append(datetime.strptime(d, '%Y-%m-%d').date())
        elif isinstance(d, datetime):
            clean_dates.append(d.date())
        elif hasattr(d, 'date'):
            clean_dates.append(d.date())
        else:
            clean_dates.append(d)

    while len(lower) < len(predicted):
        lower.append(None)
    while len(upper) < len(predicted):
        upper.append(None)

    n = min(horizon, len(clean_dates), len(predicted))
    
    if n > 0:
        return {
            "dates": clean_dates[:n],
            "predicted": [float(p) if p is not None else 0.0 for p in predicted[:n]],
            "lower_bound": [float(l) if l is not None else None for l in lower[:n]],
            "upper_bound": [float(u) if u is not None else None for u in upper[:n]],
        }
    return {"dates": [], "predicted": [], "lower_bound": [], "upper_bound": []}


def _predict_ml_model(model_data: dict, horizon: int) -> dict:
    from db.database import SessionLocal
    from db.models import ExchangeRate
    
    model = model_data.get("model")
    feature_cols = model_data.get("features", [])
    
    if model is None:
        raise ValueError("No model loaded")
    
    db = SessionLocal()
    rates = db.query(ExchangeRate).order_by(ExchangeRate.date.desc()).limit(90).all()
    db.close()
    
    if len(rates) < 30:
        raise ValueError("Not enough data for ML prediction")
    
    recent_df = pd.DataFrame([{'date': r.date, 'rate': float(r.rate)} for r in rates])
    recent_df['date'] = pd.to_datetime(recent_df['date'])
    recent_df = recent_df.sort_values('date')
    
    from ml.pipeline.feature_engineer import engineer_features
    df_eng = engineer_features(recent_df, verbose=False)
    
    available_features = [c for c in feature_cols if c in df_eng.columns]
    if not available_features:
        raise ValueError("No matching features found")
    
    last_features = df_eng[available_features].iloc[-1:].fillna(0)
    
    predictions = []
    current_features = last_features.copy()
    
    for i in range(horizon):
        pred = model.predict(current_features)[0]
        predictions.append(float(pred))
        if i + 1 < horizon:
            for col in available_features:
                if 'lag' in col or 'momentum' in col or 'rolling' in col:
                    current_features[col] = current_features[col].values[0] * 0.999
    
    today = date.today()
    dates = [(today + timedelta(days=i+1)) for i in range(horizon)]
    
    std_pred = np.std(predictions) if len(predictions) > 1 else abs(predictions[0]) * 0.01
    lower = [p - 1.96 * std_pred for p in predictions]
    upper = [p + 1.96 * std_pred for p in predictions]
    
    return {
        "dates": dates,
        "predicted": predictions,
        "lower_bound": lower,
        "upper_bound": upper,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# FORECAST GENERATION ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

def _run_generate(horizon: int):
    global _generation_state
    
    _generation_state.update({
        "in_progress": True, "started_at": datetime.now(),
        "horizon": horizon, "error": None,
    })
    
    db = SessionLocal()
    try:
        today = date.today()
        tomorrow = today + timedelta(days=1)

        logger.info(f"📊 Generating {horizon}-day forecasts using pre-trained models")
        
        generated_models = []
        for model_name, model in _models.items():
            if model_name == "ensemble":
                continue
            try:
                is_fitted = model.get("is_fitted", False) if isinstance(model, dict) else getattr(model, 'is_fitted', False)
                if not is_fitted:
                    logger.warning(f"{model_name} not fitted — skipping")
                    continue
                
                logger.info(f"  Generating {model_name} forecast...")
                
                if model_name in ["xgboost", "lightgbm"]:
                    raw = _predict_ml_model(model, horizon)
                elif model_name == "prophet":
                    if hasattr(model, 'predict'):
                        raw = model.predict(horizon)
                    else:
                        continue
                else:
                    raw = model.predict(horizon)

                adjusted = _adjust_forecast_dates(raw, horizon, tomorrow)
                if not adjusted["dates"]:
                    continue

                lowers = adjusted["lower_bound"] or [None] * len(adjusted["dates"])
                uppers = adjusted["upper_bound"] or [None] * len(adjusted["dates"])

                crud.delete_forecasts(db, model_name, horizon, today)
                objects = [
                    Forecast(model_name=model_name, horizon_days=horizon, forecast_date=today,
                             target_date=d, predicted_rate=p, lower_bound=lo, upper_bound=hi)
                    for d, p, lo, hi in zip(adjusted["dates"], adjusted["predicted"], lowers, uppers)
                ]
                crud.save_forecasts_bulk(db, objects)
                generated_models.append(model_name)
                logger.info(f"  ✅ {model_name}: saved {len(objects)} points")
            except Exception as e:
                logger.error(f"  ❌ {model_name} generation failed: {e}")

        # Ensemble
        if len(generated_models) >= 2:
            try:
                logger.info("  Generating ensemble forecast...")
                model_forecasts = {}
                for name in generated_models:
                    recs = crud.get_latest_forecasts(db, name, horizon)
                    if recs and recs[0].forecast_date == today:
                        model_forecasts[name] = recs

                if model_forecasts:
                    date_sets = [set(r.target_date for r in recs) for recs in model_forecasts.values()]
                    common_dates = sorted(set.intersection(*date_sets))[:horizon]

                    ensemble_objects = []
                    for d in common_dates:
                        preds, lowers, uppers = [], [], []
                        for recs in model_forecasts.values():
                            r = next((r for r in recs if r.target_date == d), None)
                            if r:
                                preds.append(r.predicted_rate)
                                if r.lower_bound is not None: lowers.append(r.lower_bound)
                                if r.upper_bound is not None: uppers.append(r.upper_bound)

                        if preds:
                            ensemble_objects.append(Forecast(
                                model_name="ensemble", horizon_days=horizon, forecast_date=today,
                                target_date=d, predicted_rate=sum(preds)/len(preds),
                                lower_bound=sum(lowers)/len(lowers) if lowers else None,
                                upper_bound=sum(uppers)/len(uppers) if uppers else None,
                            ))

                    if ensemble_objects:
                        crud.delete_forecasts(db, "ensemble", horizon, today)
                        crud.save_forecasts_bulk(db, ensemble_objects)
                        logger.info(f"  ✅ ensemble: saved {len(ensemble_objects)} points")
            except Exception as e:
                logger.error(f"  ❌ ensemble generation failed: {e}")

        logger.info(f"🎯 Forecast generation complete for horizon={horizon}")
        _generation_state.update({"completed_at": datetime.now()})

    except Exception as e:
        logger.error(f"❌ Forecast generation failed: {e}")
        _generation_state["error"] = str(e)
    finally:
        db.close()
        _generation_state["in_progress"] = False


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS — QUERY (GET)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/status")
def get_forecast_status(horizon: int = Query(default=7), db: Session = Depends(get_db)):
    """Check if today's forecasts are fresh."""
    if _generation_state["in_progress"]:
        elapsed = int((datetime.now() - _generation_state["started_at"]).total_seconds()) if _generation_state["started_at"] else 0
        return {
            "horizon_days": horizon, "is_fresh": False, "forecast_date": None,
            "loaded_models": get_loaded_model_names(), "status": "generating",
            "generation_elapsed_seconds": elapsed, "generation_horizon": _generation_state["horizon"],
        }
    
    try:
        today = date.today()
        records = crud.get_latest_forecasts(db, model_name="ensemble", horizon=horizon)
        is_fresh = bool(records and records[0].forecast_date == today)
        return {
            "horizon_days": horizon, "is_fresh": is_fresh,
            "forecast_date": str(records[0].forecast_date) if records else None,
            "loaded_models": get_loaded_model_names(), "status": "ready",
        }
    except Exception as e:
        return {"horizon_days": horizon, "is_fresh": False, "forecast_date": None, "status": "error", "message": str(e)}


@router.get("/latest")
def get_latest_forecasts(horizon: int = Query(default=7), model: str = Query(default="ensemble"), db: Session = Depends(get_db)):
    """Get latest forecasts for a specific model and horizon."""
    records = crud.get_latest_forecasts(db, model_name=model, horizon=horizon)
    if not records:
        raise HTTPException(status_code=404, detail=f"No forecasts for model='{model}' horizon={horizon}. Run POST /generate first.")
    
    today = date.today()
    return {
        "model_name": model, "forecast_date": str(records[0].forecast_date),
        "is_stale": records[0].forecast_date != today, "horizon_days": horizon,
        "forecasts": [{"target_date": str(r.target_date), "predicted_rate": r.predicted_rate,
                        "lower_bound": r.lower_bound, "upper_bound": r.upper_bound} for r in records],
    }


@router.get("/all")
def get_all_model_forecasts(horizon: int = Query(default=7), db: Session = Depends(get_db)):
    """Get forecasts from all loaded models."""
    if _generation_state["in_progress"]:
        return {"status": "generating", "message": "Forecasts are currently being generated", "models": {}}
    
    result = {}
    for model_name in _models:
        records = crud.get_latest_forecasts(db, model_name, horizon)
        if records:
            result[model_name] = {
                "model_name": model_name, "forecast_date": str(records[0].forecast_date), "horizon_days": horizon,
                "forecasts": [{"target_date": str(r.target_date), "predicted_rate": r.predicted_rate,
                                "lower_bound": r.lower_bound, "upper_bound": r.upper_bound} for r in records],
            }
    return result


@router.get("/1-day")
def get_1day_forecast(db: Session = Depends(get_db)):
    """Get the latest 1-day forecast from ARIMAX."""
    records = crud.get_latest_forecasts(db, model_name="arimax", horizon=1)
    if not records:
        raise HTTPException(status_code=404, detail="No 1-day forecast. Run POST /generate first.")
    return {
        "horizon": 1, "forecast_date": str(records[0].forecast_date),
        "target_date": str(records[0].target_date), "predicted_rate": records[0].predicted_rate,
        "lower_bound": records[0].lower_bound, "upper_bound": records[0].upper_bound,
    }


@router.get("/7-day")
def get_7day_forecast(db: Session = Depends(get_db)):
    """Get the latest 7-day forecasts from ARIMAX."""
    records = crud.get_latest_forecasts(db, model_name="arimax", horizon=7)
    if not records:
        raise HTTPException(status_code=404, detail="No 7-day forecast. Run POST /generate first.")
    return {
        "horizon": 7, "forecast_date": str(records[0].forecast_date),
        "forecasts": [{"target_date": str(r.target_date), "predicted_rate": r.predicted_rate,
                        "lower_bound": r.lower_bound, "upper_bound": r.upper_bound} for r in records],
    }


@router.get("/30-day")
def get_30day_forecast(db: Session = Depends(get_db)):
    """Get the latest 30-day forecasts from ARIMAX."""
    records = crud.get_latest_forecasts(db, model_name="arimax", horizon=30)
    if not records:
        raise HTTPException(status_code=404, detail="No 30-day forecast. Run POST /generate first.")
    return {
        "horizon": 30, "forecast_date": str(records[0].forecast_date),
        "forecasts": [{"target_date": str(r.target_date), "predicted_rate": r.predicted_rate,
                        "lower_bound": r.lower_bound, "upper_bound": r.upper_bound} for r in records],
    }


@router.get("/summary")
def get_forecast_summary(db: Session = Depends(get_db)):
    """Get a summary of all forecast horizons for the dashboard."""
    today = date.today()
    
    def get_horizon_data(horizon):
        records = crud.get_latest_forecasts(db, model_name="arimax", horizon=horizon)
        if records and records[0].forecast_date == today:
            last = records[-1]
            return {"predicted_rate": last.predicted_rate, "target_date": str(last.target_date),
                    "lower_bound": last.lower_bound, "upper_bound": last.upper_bound}
        return None
    
    latest_rate = crud.get_latest_rate(db)
    return {
        "current_rate": latest_rate.rate if latest_rate else None,
        "current_date": str(today),
        "forecasts": {"1_day": get_horizon_data(1), "7_day": get_horizon_data(7), "30_day": get_horizon_data(30)},
    }


@router.get("/generation-status")
def get_generation_status():
    """Get current generation state for monitoring."""
    elapsed = int((datetime.now() - _generation_state["started_at"]).total_seconds()) if _generation_state["started_at"] and _generation_state["in_progress"] else 0
    return {
        "in_progress": _generation_state["in_progress"],
        "started_at": str(_generation_state["started_at"]) if _generation_state["started_at"] else None,
        "horizon": _generation_state["horizon"], "elapsed_seconds": elapsed,
        "completed_at": str(_generation_state["completed_at"]) if _generation_state["completed_at"] else None,
        "error": _generation_state["error"], "loaded_models": get_loaded_model_names(),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS — ACTIONS (POST)
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/generate")
def generate_forecasts(background_tasks: BackgroundTasks, horizon: int = Query(default=7), db: Session = Depends(get_db)):
    """Generate forecasts using pre-trained models."""
    if not _models:
        raise HTTPException(status_code=503, detail="Models not loaded yet")
    
    if _generation_state["in_progress"]:
        elapsed = int((datetime.now() - _generation_state["started_at"]).total_seconds()) if _generation_state["started_at"] else 0
        if elapsed > 300:
            _generation_state["in_progress"] = False
        else:
            return {"status": "already_generating", "message": f"Already in progress ({elapsed}s elapsed).", "generated_at": str(date.today())}

    today = date.today()
    existing = crud.get_latest_forecasts(db, model_name="ensemble", horizon=horizon)
    if existing and existing[0].forecast_date == today:
        return {"status": "already_fresh", "message": f"Today's {horizon}-day forecasts already exist.", "generated_at": str(today)}

    background_tasks.add_task(_run_generate, horizon)
    return {"status": "generating", "message": f"Generation started for horizon={horizon}.", "generated_at": str(today)}


@router.post("/retrain")
def retrain_models(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Retrain models with latest data."""
    if not _models:
        raise HTTPException(status_code=503, detail="Models not loaded yet")
    
    if _generation_state["in_progress"]:
        return {"status": "already_training", "message": "Training is already in progress."}
    
    def _run_retrain():
        _generation_state.update({"in_progress": True, "started_at": datetime.now(), "horizon": None, "error": None})
        db_session = SessionLocal()
        try:
            logger.info("🔄 Starting model retraining...")
            rates = crud.get_all_rates_as_dataframe(db_session)
            if rates.empty:
                return
            
            for model_name in ["arima", "arimax"]:
                if model_name in _models:
                    try:
                        logger.info(f"  Retraining {model_name.upper()}...")
                        if model_name == "arimax":
                            from ml.pipeline.feature_engineer import engineer_features
                            _models[model_name].fit(engineer_features(rates.copy(), verbose=False))
                        else:
                            _models[model_name].fit(rates)
                        logger.info(f"  ✅ {model_name.upper()} retrained")
                    except Exception as e:
                        logger.error(f"  ❌ {model_name} retraining failed: {e}")
            
            logger.info("🎯 Model retraining complete")
        except Exception as e:
            logger.error(f"❌ Retraining failed: {e}")
            _generation_state["error"] = str(e)
        finally:
            db_session.close()
            _generation_state.update({"in_progress": False, "completed_at": datetime.now()})
    
    background_tasks.add_task(_run_retrain)
    return {"status": "training_started", "message": "Model retraining started."}

# ═══════════════════════════════════════════════════════════════════════════════
# ADVANCED ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/accuracy")
def get_forecast_accuracy(db: Session = Depends(get_db)):
    """Compare past forecasts against actual rates to show model accuracy."""
    # Get forecasts from 7 days ago
    past_date = date.today() - timedelta(days=7)
    records = crud.get_latest_forecasts(db, model_name="arimax", horizon=7)
    
    if not records:
        return {"message": "No historical forecasts to compare yet. Generate forecasts daily for 7+ days."}
    
    results = []
    for f in records:
        actual = db.query(ExchangeRate).filter(ExchangeRate.date == f.target_date).first()
        if actual:
            error = abs(f.predicted_rate - actual.rate)
            results.append({
                "target_date": str(f.target_date),
                "predicted": f.predicted_rate,
                "actual": actual.rate,
                "error_mwk": round(error, 2),
                "error_pct": round(error / actual.rate * 100, 4),
                "within_range": f.lower_bound <= actual.rate <= f.upper_bound if f.lower_bound and f.upper_bound else None,
            })
    
    if not results:
        return {"message": "No matching actual rates found for comparison yet."}
    
    return {
        "model": "arimax",
        "forecast_date": str(records[0].forecast_date),
        "comparisons": results,
        "avg_error_mwk": round(sum(r["error_mwk"] for r in results) / len(results), 2),
        "avg_error_pct": round(sum(r["error_pct"] for r in results) / len(results), 4),
        "within_range_pct": round(sum(1 for r in results if r["within_range"]) / len(results) * 100, 1),
    }


@router.get("/quick")
def get_quick_forecast(db: Session = Depends(get_db)):
    """Get a quick one-line forecast summary - perfect for bots and notifications."""
    records = crud.get_latest_forecasts(db, model_name="arimax", horizon=7)
    if not records:
        return {"message": "No forecasts available. Generate first."}
    
    today_rate = crud.get_latest_rate(db)
    last = records[-1]
    diff = last.predicted_rate - today_rate.rate
    direction = "↗" if diff > 0 else "↘"
    
    return {
        "message": f"MWK/USD: {today_rate.rate:,.2f} | 7-day: {last.predicted_rate:,.2f} ({direction} {abs(diff):,.2f})",
        "current_rate": today_rate.rate,
        "forecast_7d": last.predicted_rate,
        "change_mwk": round(diff, 2),
        "change_pct": round(diff / today_rate.rate * 100, 2),
    }


@router.get("/export")
def export_forecasts(horizon: int = Query(default=7), format: str = Query(default="json"), db: Session = Depends(get_db)):
    """Export forecasts in JSON or CSV format."""
    records = crud.get_latest_forecasts(db, model_name="arimax", horizon=horizon)
    if not records:
        raise HTTPException(status_code=404, detail="No forecasts available. Run POST /generate first.")
    
    data = [{"forecast_date": str(r.forecast_date), "target_date": str(r.target_date),
             "predicted_rate": r.predicted_rate, "lower_bound": r.lower_bound, "upper_bound": r.upper_bound} for r in records]
    
    if format == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["forecast_date", "target_date", "predicted_rate", "lower_bound", "upper_bound"])
        writer.writeheader()
        writer.writerows(data)
        return Response(content=output.getvalue(), media_type="text/csv",
                       headers={"Content-Disposition": f"attachment; filename=kwachacast_forecast_{horizon}d.csv"})
    
    return {"model": "arimax", "horizon": horizon, "forecasts": data}