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
from db.models import Forecast, ExchangeRate
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
    """
    Adjust forecast dates to ensure they start from start_date and have exactly horizon points.
    Generates sequential dates from start_date and maps predictions to them.
    """
    dates = raw.get("dates", [])
    predicted = raw.get("predicted", [])
    lower = raw.get("lower_bound", []) or raw.get("lower", [])
    upper = raw.get("upper_bound", []) or raw.get("upper", [])

    # Normalize to lists
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

    # Parse all dates to date objects
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

    # Build output: generate exact horizon dates starting from start_date
    new_dates = []
    new_predicted = []
    new_lower = []
    new_upper = []

    for i in range(horizon):
        target_date = start_date + timedelta(days=i)

        # Try to find matching date in model output
        if target_date in clean_dates:
            idx = clean_dates.index(target_date)
        elif len(clean_dates) > i:
            # Use the i-th prediction if dates don't match exactly
            idx = i
        elif len(predicted) > 0:
            # Use last available prediction as fallback
            idx = len(predicted) - 1
        else:
            continue

        new_dates.append(target_date)
        new_predicted.append(
            float(predicted[idx]) if idx < len(predicted) and predicted[idx] is not None else 0.0
        )
        new_lower.append(
            float(lower[idx]) if idx < len(lower) and lower[idx] is not None else None
        )
        new_upper.append(
            float(upper[idx]) if idx < len(upper) and upper[idx] is not None else None
        )

    return {
        "dates": new_dates,
        "predicted": new_predicted,
        "lower_bound": new_lower,
        "upper_bound": new_upper,
    }


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

        # Models to include in ensemble (excluding prophet which gives inflated predictions)
        ensemble_model_names = ["arima", "arimax", "xgboost", "lightgbm"]
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

                # Only delete if today's forecasts already exist
                existing_today = db.query(Forecast).filter(
                    Forecast.model_name == model_name,
                    Forecast.horizon_days == horizon,
                    Forecast.forecast_date == today
                ).first()
                if existing_today:
                    crud.delete_forecasts(db, model_name, horizon, today)

                objects = [
                    Forecast(model_name=model_name, horizon_days=horizon, forecast_date=today,
                             target_date=d, predicted_rate=round(p, 2), lower_bound=round(lo, 2) if lo else None, upper_bound=round(hi, 2) if hi else None)
                    for d, p, lo, hi in zip(adjusted["dates"], adjusted["predicted"], lowers, uppers)
                ]
                crud.save_forecasts_bulk(db, objects)
                generated_models.append(model_name)
                logger.info(f"  ✅ {model_name}: saved {len(objects)} points")
            except Exception as e:
                logger.error(f"  ❌ {model_name} generation failed: {e}")

        # Ensemble
        ensemble_candidates = [m for m in generated_models if m in ensemble_model_names]
        if len(ensemble_candidates) >= 2:
            try:
                logger.info(f"  Generating ensemble forecast from: {ensemble_candidates}")
                model_forecasts = {}
                for name in ensemble_candidates:
                    recs = crud.get_latest_forecasts(db, name, horizon)
                    if recs and recs[0].forecast_date == today:
                        model_forecasts[name] = recs

                if model_forecasts:
                    first_model = list(model_forecasts.keys())[0]
                    all_dates = sorted([r.target_date for r in model_forecasts[first_model]])
                    all_dates = [d for d in all_dates if d >= tomorrow]

                    ensemble_objects = []
                    for d in all_dates:
                        preds, lowers, uppers = [], [], []
                        for name, recs in model_forecasts.items():
                            r = next((r for r in recs if r.target_date == d), None)
                            if r:
                                preds.append(r.predicted_rate)
                                if r.lower_bound is not None:
                                    lowers.append(r.lower_bound)
                                if r.upper_bound is not None:
                                    uppers.append(r.upper_bound)

                        if preds:
                            ensemble_objects.append(Forecast(
                                model_name="ensemble", horizon_days=horizon, forecast_date=today,
                                target_date=d, predicted_rate=round(sum(preds)/len(preds), 2),
                                lower_bound=round(sum(lowers)/len(lowers), 2) if lowers else None,
                                upper_bound=round(sum(uppers)/len(uppers), 2) if uppers else None,
                            ))

                    if ensemble_objects:
                        existing_ensemble = db.query(Forecast).filter(
                            Forecast.model_name == "ensemble",
                            Forecast.horizon_days == horizon,
                            Forecast.forecast_date == today
                        ).first()
                        if existing_ensemble:
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
        "forecasts": [{"target_date": str(r.target_date), "predicted_rate": round(r.predicted_rate, 2),
                        "lower_bound": round(r.lower_bound, 2) if r.lower_bound else None, "upper_bound": round(r.upper_bound, 2) if r.upper_bound else None} for r in records],
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
                "forecasts": [{"target_date": str(r.target_date), "predicted_rate": round(r.predicted_rate, 2),
                                "lower_bound": round(r.lower_bound, 2) if r.lower_bound else None, "upper_bound": round(r.upper_bound, 2) if r.upper_bound else None} for r in records],
            }
    return result


@router.get("/1-day")
def get_1day_forecast(db: Session = Depends(get_db)):
    """Get the latest 1-day forecast from Ensemble."""
    records = crud.get_latest_forecasts(db, model_name="ensemble", horizon=1)
    if not records:
        raise HTTPException(status_code=404, detail="No 1-day forecast. Run POST /generate first.")
    r = records[0]
    return {
        "horizon": 1, "forecast_date": str(r.forecast_date),
        "target_date": str(r.target_date), "predicted_rate": round(r.predicted_rate, 2),
        "lower_bound": round(r.lower_bound, 2) if r.lower_bound else None,
        "upper_bound": round(r.upper_bound, 2) if r.upper_bound else None,
    }


@router.get("/7-day")
def get_7day_forecast(db: Session = Depends(get_db)):
    """Get the latest 7-day forecasts from Ensemble."""
    records = crud.get_latest_forecasts(db, model_name="ensemble", horizon=7)
    if not records:
        raise HTTPException(status_code=404, detail="No 7-day forecast. Run POST /generate first.")
    return {
        "horizon": 7, "forecast_date": str(records[0].forecast_date),
        "forecasts": [{"target_date": str(r.target_date), "predicted_rate": round(r.predicted_rate, 2),
                        "lower_bound": round(r.lower_bound, 2) if r.lower_bound else None, "upper_bound": round(r.upper_bound, 2) if r.upper_bound else None} for r in records],
    }


@router.get("/30-day")
def get_30day_forecast(db: Session = Depends(get_db)):
    """Get the latest 30-day forecasts from Ensemble."""
    records = crud.get_latest_forecasts(db, model_name="ensemble", horizon=30)
    if not records:
        raise HTTPException(status_code=404, detail="No 30-day forecast. Run POST /generate first.")
    return {
        "horizon": 30, "forecast_date": str(records[0].forecast_date),
        "forecasts": [{"target_date": str(r.target_date), "predicted_rate": round(r.predicted_rate, 2),
                        "lower_bound": round(r.lower_bound, 2) if r.lower_bound else None, "upper_bound": round(r.upper_bound, 2) if r.upper_bound else None} for r in records],
    }


@router.get("/summary")
def get_forecast_summary(db: Session = Depends(get_db)):
    """Get a summary of all forecast horizons for the dashboard."""
    today = date.today()

    def get_horizon_data(horizon):
        records = crud.get_latest_forecasts(db, model_name="ensemble", horizon=horizon)
        if records and records[0].forecast_date == today:
            last = records[-1]
            return {"predicted_rate": round(last.predicted_rate, 2), "target_date": str(last.target_date),
                    "lower_bound": round(last.lower_bound, 2) if last.lower_bound else None, "upper_bound": round(last.upper_bound, 2) if last.upper_bound else None}
        return None

    latest_rate = crud.get_latest_rate(db)
    return {
        "current_rate": round(latest_rate.rate, 2) if latest_rate else None,
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

            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            artifacts_dir = os.path.join(base_dir, 'ml', 'artifacts')
            os.makedirs(artifacts_dir, exist_ok=True)

            if "arima" in _models:
                try:
                    logger.info("  Retraining ARIMA...")
                    _models["arima"].fit(rates)
                    logger.info("  ✅ ARIMA retrained")
                except Exception as e:
                    logger.error(f"  ❌ ARIMA retraining failed: {e}")

            if "arimax" in _models:
                try:
                    logger.info("  Retraining ARIMAX...")
                    from ml.pipeline.feature_engineer import engineer_features
                    _models["arimax"].fit(engineer_features(rates.copy(), verbose=False))
                    logger.info("  ✅ ARIMAX retrained")
                except Exception as e:
                    logger.error(f"  ❌ ARIMAX retraining failed: {e}")

            if "xgboost" in _models:
                try:
                    logger.info("  Retraining XGBoost...")
                    from ml.pipeline.feature_engineer import engineer_features
                    import joblib
                    xgb_data = _models["xgboost"]
                    features = xgb_data.get("features", [])
                    if features:
                        rates_eng = engineer_features(rates.copy(), verbose=False)
                        available = [c for c in features if c in rates_eng.columns]
                        if available:
                            X = rates_eng[available].fillna(0)
                            y = rates_eng['rate']
                            xgb_data["model"].fit(X, y)
                            joblib.dump(xgb_data["model"], os.path.join(artifacts_dir, 'xgboost_model.joblib'))
                            logger.info("  ✅ XGBoost retrained and saved")
                except Exception as e:
                    logger.error(f"  ❌ XGBoost retraining failed: {e}")

            if "lightgbm" in _models:
                try:
                    logger.info("  Retraining LightGBM...")
                    from ml.pipeline.feature_engineer import engineer_features
                    import joblib
                    lgb_data = _models["lightgbm"]
                    features = lgb_data.get("features", [])
                    if features:
                        rates_eng = engineer_features(rates.copy(), verbose=False)
                        available = [c for c in features if c in rates_eng.columns]
                        if available:
                            X = rates_eng[available].fillna(0)
                            y = rates_eng['rate']
                            lgb_data["model"].fit(X, y)
                            joblib.dump(lgb_data["model"], os.path.join(artifacts_dir, 'lightgbm_model.joblib'))
                            logger.info("  ✅ LightGBM retrained and saved")
                except Exception as e:
                    logger.error(f"  ❌ LightGBM retraining failed: {e}")

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
    
    # Get ALL historical ensemble 7-day forecasts, not just the latest
    today = date.today()
    thirty_days_ago = today - timedelta(days=30)
    
    records = db.query(Forecast).filter(
        Forecast.model_name == "ensemble",
        Forecast.horizon_days == 7,
        Forecast.forecast_date >= thirty_days_ago,
        Forecast.forecast_date < today  # Exclude today's forecasts
    ).order_by(Forecast.forecast_date.asc()).all()

    if not records:
        return {"message": "No historical forecasts to compare yet.", "comparisons": []}

    results = []
    for f in records:
        actual = db.query(ExchangeRate).filter(ExchangeRate.date == f.target_date).first()
        if actual:
            error = abs(f.predicted_rate - actual.rate)
            results.append({
                "target_date": str(f.target_date),
                "forecast_date": str(f.forecast_date),
                "predicted": round(f.predicted_rate, 2),
                "actual": round(actual.rate, 2),
                "error_mwk": round(error, 2),
                "error_pct": round(error / actual.rate * 100, 4),
                "within_range": f.lower_bound <= actual.rate <= f.upper_bound if f.lower_bound and f.upper_bound else None,
            })

    if not results:
        return {"message": "No matching actual rates found for comparison yet.", "comparisons": []}

    return {
        "model": "ensemble",
        "comparisons": results,
        "total_comparisons": len(results),
        "avg_error_mwk": round(sum(r["error_mwk"] for r in results) / len(results), 2),
        "avg_error_pct": round(sum(r["error_pct"] for r in results) / len(results), 4),
        "within_range_pct": round(sum(1 for r in results if r["within_range"]) / len(results) * 100, 1),
    }

@router.get("/quick")
def get_quick_forecast(db: Session = Depends(get_db)):
    """Get a quick one-line forecast summary."""
    records = crud.get_latest_forecasts(db, model_name="ensemble", horizon=7)
    if not records:
        return {"message": "No forecasts available. Generate first."}

    today_rate = crud.get_latest_rate(db)
    last = records[-1]
    diff = last.predicted_rate - today_rate.rate
    direction = "↗" if diff > 0 else "↘"

    return {
        "message": f"MWK/USD: {today_rate.rate:,.2f} | 7-day: {last.predicted_rate:,.2f} ({direction} {abs(diff):,.2f})",
        "current_rate": round(today_rate.rate, 2) if today_rate else None,
        "forecast_7d": round(last.predicted_rate, 2),
        "change_mwk": round(diff, 2),
        "change_pct": round(diff / today_rate.rate * 100, 2),
    }


@router.get("/export")
def export_forecasts(horizon: int = Query(default=7), format: str = Query(default="json"), db: Session = Depends(get_db)):
    """Export forecasts in JSON or CSV format."""
    records = crud.get_latest_forecasts(db, model_name="ensemble", horizon=horizon)
    if not records:
        raise HTTPException(status_code=404, detail="No forecasts available. Run POST /generate first.")

    data = [{"forecast_date": str(r.forecast_date), "target_date": str(r.target_date),
             "predicted_rate": round(r.predicted_rate, 2), "lower_bound": round(r.lower_bound, 2) if r.lower_bound else None, "upper_bound": round(r.upper_bound, 2) if r.upper_bound else None} for r in records]

    if format == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["forecast_date", "target_date", "predicted_rate", "lower_bound", "upper_bound"])
        writer.writeheader()
        writer.writerows(data)
        return Response(content=output.getvalue(), media_type="text/csv",
                       headers={"Content-Disposition": f"attachment; filename=kwachacast_forecast_{horizon}d.csv"})

    return {"model": "ensemble", "horizon": horizon, "forecasts": data}


@router.get("/historical")
def get_historical_forecasts(
    start_date: str = Query(default=None),
    end_date: str = Query(default=None),
    model: str = Query(default="ensemble"),
    horizon: int = Query(default=7),
    db: Session = Depends(get_db)
):
    """Get historical forecasts for a date range (for Trust Chart)."""
    try:
        query = db.query(Forecast).filter(
            Forecast.model_name == model,
            Forecast.horizon_days == horizon
        )
        
        if start_date:
            query = query.filter(Forecast.forecast_date >= date.fromisoformat(start_date))
        if end_date:
            query = query.filter(Forecast.forecast_date <= date.fromisoformat(end_date))
        
        records = query.order_by(Forecast.forecast_date.asc(), Forecast.target_date.asc()).all()
        
        if not records:
            return {"message": "No historical forecasts found for this range.", "forecast_dates": {}}
        
        from collections import defaultdict
        grouped = defaultdict(list)
        for r in records:
            grouped[str(r.forecast_date)].append({
                "target_date": str(r.target_date),
                "predicted_rate": round(r.predicted_rate, 2),
                "lower_bound": round(r.lower_bound, 2) if r.lower_bound else None,
                "upper_bound": round(r.upper_bound, 2) if r.upper_bound else None,
            })
        
        return {
            "model": model,
            "horizon": horizon,
            "forecast_dates": {k: v for k, v in sorted(grouped.items())},
            "total_forecast_days": len(grouped)
        }
    except Exception as e:
        return {"message": str(e), "forecast_dates": {}}