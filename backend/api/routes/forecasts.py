import os
import sys
import pandas as pd
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

# Global state management
_models = {}
_training_lock = Lock()

# Generation state tracking to prevent duplicate generations
_generation_state = {
    "in_progress": False,
    "started_at": None,
    "horizon": None,
    "completed_at": None,
    "error": None,
}


def set_models(models: dict):
    """Set the loaded models in memory"""
    global _models
    _models = models


def get_loaded_model_names() -> list:
    """Returns names of models currently loaded in memory."""
    return list(_models.keys())


def _safe_date(d):
    """Convert various date types to date object"""
    if hasattr(d, 'date'):
        return d.date()
    return d


def _adjust_forecast_dates(raw: dict, horizon: int, start_date: date) -> dict:
    """Take first 'horizon' predictions and convert dates to date objects for SQLite."""
    dates = raw.get("dates", [])
    predicted = raw.get("predicted", [])
    lower = raw.get("lower_bound", []) or raw.get("lower", [])
    upper = raw.get("upper_bound", []) or raw.get("upper", [])

    # Convert predictions to lists
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

    # Convert dates to date objects (SQLite requires date objects, not strings)
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

    # Pad lower/upper
    while len(lower) < len(predicted):
        lower.append(None)
    while len(upper) < len(predicted):
        upper.append(None)

    # Take first 'horizon' items
    n = min(horizon, len(clean_dates), len(predicted))
    
    if n > 0:
        return {
            "dates": clean_dates[:n],
            "predicted": [float(p) if p is not None else 0.0 for p in predicted[:n]],
            "lower_bound": [float(l) if l is not None else None for l in lower[:n]],
            "upper_bound": [float(u) if u is not None else None for u in upper[:n]],
        }
    return {"dates": [], "predicted": [], "lower_bound": [], "upper_bound": []}


def _run_generate(horizon: int):
    """
    Generate forecasts using already-trained models.
    No retraining happens here - models use their existing fitted state.
    Owns its own DB session — critical because the request-scoped session
    is closed by FastAPI before this background task finishes.
    """
    global _generation_state
    
    # Update generation state
    _generation_state.update({
        "in_progress": True,
        "started_at": datetime.now(),
        "horizon": horizon,
        "error": None,
    })
    
    db = SessionLocal()
    try:
        today = date.today()
        tomorrow = today + timedelta(days=1)

        logger.info(f"📊 Generating {horizon}-day forecasts using pre-trained models")
        
        # ---- Individual models (NO retraining, just predict) ----
        generated_models = []
        for model_name, model in _models.items():
            if model_name == "ensemble":
                continue
            try:
                # Skip if model isn't fitted
                if not getattr(model, 'is_fitted', False):
                    logger.warning(f"{model_name} not fitted — skipping")
                    continue
                
                logger.info(f"  Generating {model_name} forecast...")
                
                if model_name == "prophet":
                    # ProphetForecaster.predict() returns dates/predicted/lower/upper
                    if hasattr(model, 'predict'):
                        raw = model.predict(horizon)
                    else:
                        logger.warning("Prophet has no predict() — skipping")
                        continue
                else:
                    # ARIMA, ARIMAX, etc.
                    raw = model.predict(horizon)

                adjusted = _adjust_forecast_dates(raw, horizon, tomorrow)
                if not adjusted["dates"]:
                    logger.warning(f"{model_name}: no dates after adjustment — skipping")
                    continue

                lowers = adjusted["lower_bound"] or [None] * len(adjusted["dates"])
                uppers = adjusted["upper_bound"] or [None] * len(adjusted["dates"])

                # Delete old forecasts for today and save new ones
                crud.delete_forecasts(db, model_name, horizon, today)
                objects = [
                    Forecast(
                        model_name=model_name,
                        horizon_days=horizon,
                        forecast_date=today,
                        target_date=d,
                        predicted_rate=p,
                        lower_bound=lo,
                        upper_bound=hi,
                    )
                    for d, p, lo, hi in zip(
                        adjusted["dates"], adjusted["predicted"], lowers, uppers
                    )
                ]
                crud.save_forecasts_bulk(db, objects)
                generated_models.append(model_name)
                logger.info(f"  ✅ {model_name}: saved {len(objects)} points")
            except Exception as e:
                logger.error(f"  ❌ {model_name} generation failed: {e}")

        # ---- Ensemble (combines individual model forecasts) ----
        if len(generated_models) >= 2:
            try:
                logger.info("  Generating ensemble forecast...")
                model_forecasts = {}
                for name in generated_models:
                    recs = crud.get_latest_forecasts(db, name, horizon)
                    if recs and recs[0].forecast_date == today:
                        model_forecasts[name] = recs

                if not model_forecasts:
                    logger.warning("  ⚠️ Ensemble: no individual forecasts for today")
                else:
                    date_sets = [set(r.target_date for r in recs) for recs in model_forecasts.values()]
                    common_dates = sorted(set.intersection(*date_sets))[:horizon]

                    ensemble_objects = []
                    for d in common_dates:
                        preds, lowers, uppers = [], [], []
                        for recs in model_forecasts.values():
                            r = next((r for r in recs if r.target_date == d), None)
                            if r:
                                preds.append(r.predicted_rate)
                                if r.lower_bound is not None:
                                    lowers.append(r.lower_bound)
                                if r.upper_bound is not None:
                                    uppers.append(r.upper_bound)

                        if preds:
                            ensemble_objects.append(Forecast(
                                model_name="ensemble",
                                horizon_days=horizon,
                                forecast_date=today,
                                target_date=d,
                                predicted_rate=sum(preds) / len(preds),
                                lower_bound=sum(lowers) / len(lowers) if lowers else None,
                                upper_bound=sum(uppers) / len(uppers) if uppers else None,
                            ))

                    if ensemble_objects:
                        crud.delete_forecasts(db, "ensemble", horizon, today)
                        crud.save_forecasts_bulk(db, ensemble_objects)
                        logger.info(f"  ✅ ensemble: saved {len(ensemble_objects)} points")
            except Exception as e:
                logger.error(f"  ❌ ensemble generation failed: {e}")

        logger.info(f"🎯 Forecast generation complete for horizon={horizon}")
        
        # Mark as completed successfully
        _generation_state.update({
            "completed_at": datetime.now(),
        })

    except Exception as e:
        logger.error(f"❌ Forecast generation failed: {e}")
        _generation_state["error"] = str(e)
    finally:
        db.close()
        _generation_state["in_progress"] = False


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/status")
def get_forecast_status(
    horizon: int = Query(default=7),
    db: Session = Depends(get_db),
):
    """
    Enhanced status endpoint with generation progress tracking.
    Returns is_fresh=true when today's ensemble forecast exists for
    the requested horizon — avoids polling the wrong horizon.
    """
    if _generation_state["in_progress"]:
        elapsed = 0
        if _generation_state["started_at"]:
            elapsed = int((datetime.now() - _generation_state["started_at"]).total_seconds())
        
        return {
            "horizon_days": horizon,
            "is_fresh": False,
            "forecast_date": None,
            "loaded_models": get_loaded_model_names(),
            "status": "generating",
            "generation_elapsed_seconds": elapsed,
            "generation_horizon": _generation_state["horizon"],
            "message": f"Generating forecasts for {_generation_state['horizon']}d horizon ({elapsed}s elapsed)..."
        }
    
    try:
        today = date.today()
        records = crud.get_latest_forecasts(db, model_name="ensemble", horizon=horizon)
        is_fresh = bool(records and records[0].forecast_date == today)
        
        response = {
            "horizon_days": horizon,
            "is_fresh": is_fresh,
            "forecast_date": str(records[0].forecast_date) if records else None,
            "loaded_models": get_loaded_model_names(),
            "status": "ready",
        }
        
        if _generation_state.get("error"):
            response["last_error"] = _generation_state["error"]
            _generation_state["error"] = None
        
        return response
        
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return {
            "horizon_days": horizon,
            "is_fresh": False,
            "forecast_date": None,
            "loaded_models": get_loaded_model_names(),
            "status": "error",
            "message": f"Status check failed: {str(e)}"
        }


@router.get("/latest")
def get_latest_forecasts(
    horizon: int = Query(default=7),
    model: str = Query(default="ensemble"),
    db: Session = Depends(get_db),
):
    """
    Get the latest forecasts for a specific model and horizon.
    """
    records = crud.get_latest_forecasts(db, model_name=model, horizon=horizon)
    if not records:
        raise HTTPException(
            status_code=404,
            detail=f"No forecasts for model='{model}' horizon={horizon}. Run POST /generate first."
        )
    
    today = date.today()
    forecast_date = records[0].forecast_date
    is_stale = forecast_date != today

    return {
        "model_name": model,
        "forecast_date": str(forecast_date),
        "is_stale": is_stale,
        "horizon_days": horizon,
        "forecasts": [
            {
                "target_date": str(r.target_date),
                "predicted_rate": r.predicted_rate,
                "lower_bound": r.lower_bound,
                "upper_bound": r.upper_bound,
            }
            for r in records
        ],
    }


@router.post("/generate")
def generate_forecasts(
    background_tasks: BackgroundTasks,
    horizon: int = Query(default=7),
    db: Session = Depends(get_db),
):
    """
    Generate forecasts using already-loaded & trained models.
    Prevents duplicate generation requests.
    No model retraining happens here - models must be pre-trained.
    """
    if not _models:
        raise HTTPException(status_code=503, detail="Models not loaded yet")
    
    if _generation_state["in_progress"]:
        elapsed = 0
        if _generation_state["started_at"]:
            elapsed = int((datetime.now() - _generation_state["started_at"]).total_seconds())
        
        if elapsed > 300:
            logger.warning(f"Generation appears stuck after {elapsed}s - allowing restart")
            _generation_state["in_progress"] = False
        else:
            return {
                "status": "already_generating",
                "message": f"Forecast generation is already in progress for {_generation_state['horizon']}d horizon ({elapsed}s elapsed). Please wait.",
                "generated_at": str(date.today()),
            }

    today = date.today()
    existing = crud.get_latest_forecasts(db, model_name="ensemble", horizon=horizon)
    if existing and existing[0].forecast_date == today:
        return {
            "status": "already_fresh",
            "message": f"Today's {horizon}-day forecasts already exist.",
            "generated_at": str(today),
        }

    background_tasks.add_task(_run_generate, horizon)
    
    return {
        "status": "generating",
        "message": f"Generation started for horizon={horizon}. Poll /forecasts/status?horizon={horizon} to check progress.",
        "generated_at": str(today),
    }


@router.post("/retrain")
def retrain_models(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    SEPARATE endpoint for retraining models with latest data.
    This is where actual model training happens.
    """
    if not _models:
        raise HTTPException(status_code=503, detail="Models not loaded yet")
    
    if _generation_state["in_progress"]:
        return {
            "status": "already_training",
            "message": "Training is already in progress. Please wait.",
        }
    
    def _run_retrain():
        """Background task for model retraining"""
        _generation_state.update({
            "in_progress": True,
            "started_at": datetime.now(),
            "horizon": None,
            "error": None,
        })
        
        db_session = SessionLocal()
        try:
            logger.info("🔄 Starting model retraining...")
            rates = crud.get_all_rates_as_dataframe(db_session)
            
            if rates.empty:
                logger.warning("No rate data for retraining")
                return
            
            if "arima" in _models:
                try:
                    logger.info("  Retraining ARIMA...")
                    _models["arima"].fit(rates)
                    logger.info("  ✅ ARIMA retrained")
                except Exception as e:
                    logger.error(f"  ❌ ARIMA retraining failed: {e}")
            
            if "prophet" in _models:
                try:
                    logger.info("  Retraining Prophet...")
                    if hasattr(_models["prophet"], 'refit'):
                        _models["prophet"].refit(rates)
                    elif hasattr(_models["prophet"], 'fit'):
                        df = rates.rename(columns={"date": "ds", "rate": "y"})
                        df["ds"] = pd.to_datetime(df["ds"])
                        _models["prophet"].fit(df.sort_values("ds"))
                    logger.info("  ✅ Prophet retrained")
                except Exception as e:
                    logger.error(f"  ❌ Prophet retraining failed: {e}")
            
            if "arimax" in _models:
                try:
                    logger.info("  Retraining ARIMAX...")
                    # Add engineered features for ARIMAX
                    from ml.pipeline.feature_engineer import engineer_features
                    rates_eng = engineer_features(rates.copy(), verbose=False)
                    _models["arimax"].fit(rates_eng)
                    logger.info("  ✅ ARIMAX retrained")
                except Exception as e:
                    logger.error(f"  ❌ ARIMAX retraining failed: {e}")
            
            logger.info("🎯 Model retraining complete")
            
        except Exception as e:
            logger.error(f"❌ Retraining failed: {e}")
            _generation_state["error"] = str(e)
        finally:
            db_session.close()
            _generation_state.update({
                "in_progress": False,
                "completed_at": datetime.now(),
            })
    
    background_tasks.add_task(_run_retrain)
    return {
        "status": "training_started",
        "message": "Model retraining started. Check status endpoint for progress."
    }


@router.get("/all")
def get_all_model_forecasts(
    horizon: int = Query(default=7),
    db: Session = Depends(get_db),
):
    """
    Get forecasts from all loaded models for a specific horizon.
    """
    if _generation_state["in_progress"]:
        return {
            "status": "generating",
            "message": "Forecasts are currently being generated",
            "models": {}
        }
    
    result = {}
    for model_name in _models:
        records = crud.get_latest_forecasts(db, model_name, horizon)
        if records:
            result[model_name] = {
                "model_name": model_name,
                "forecast_date": str(records[0].forecast_date),
                "horizon_days": horizon,
                "forecasts": [
                    {
                        "target_date": str(r.target_date),
                        "predicted_rate": r.predicted_rate,
                        "lower_bound": r.lower_bound,
                        "upper_bound": r.upper_bound,
                    }
                    for r in records
                ],
            }
    
    return result


@router.get("/generation-status")
def get_generation_status():
    """
    Get current generation state for monitoring.
    """
    elapsed = 0
    if _generation_state["started_at"] and _generation_state["in_progress"]:
        elapsed = int((datetime.now() - _generation_state["started_at"]).total_seconds())
    
    return {
        "in_progress": _generation_state["in_progress"],
        "started_at": str(_generation_state["started_at"]) if _generation_state["started_at"] else None,
        "horizon": _generation_state["horizon"],
        "elapsed_seconds": elapsed,
        "completed_at": str(_generation_state["completed_at"]) if _generation_state["completed_at"] else None,
        "error": _generation_state["error"],
        "loaded_models": get_loaded_model_names(),
    }