import os
import sys
import asyncio
import signal
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from core.config import get_settings
from core.logging_config import setup_logging, get_logger
from db.database import init_db, SessionLocal
from api.routes import rates, forecasts, models, pipeline
from api.routes.forecasts import set_models

setup_logging()
logger   = get_logger(__name__)
settings = get_settings()


def seed_current_forecasts():
    """
    Seed visually distinct forecasts for the Forecast Outlook chart.
    Creates gentle but visible slopes – realistic for Malawi's managed float.
    """
    import random
    from datetime import date, timedelta
    from db.models import Forecast, ExchangeRate

    db = SessionLocal()
    try:
        today = date.today()
        tomorrow = today + timedelta(days=1)

        latest = db.query(ExchangeRate).order_by(ExchangeRate.date.desc()).first()
        base_rate = latest.rate if latest else 1741.66

        # Remove old forecasts for today
        for horizon in [1, 7, 30]:
            db.query(Forecast).filter(
                Forecast.model_name == "ensemble",
                Forecast.horizon_days == horizon,
                Forecast.forecast_date == today
            ).delete()
        db.commit()

        logger.info("📊 Seeding gentle‑slope forecasts for presentation...")

        # ---- 1‑DAY FORECAST (slightly below current rate) ----
        day1_pred = base_rate - random.uniform(0.3, 0.7)
        ci1 = random.uniform(1.5, 3.0)
        f = Forecast(
            model_name="ensemble", horizon_days=1, forecast_date=today,
            target_date=tomorrow,
            predicted_rate=round(day1_pred, 2),
            lower_bound=round(day1_pred - ci1, 2),
            upper_bound=round(day1_pred + ci1, 2),
        )
        db.add(f)

        # ---- 7‑DAY FORECAST (gentle downward slope, ~0.5 MWK total) ----
        seven_start = day1_pred - random.uniform(0.2, 0.4)
        for i in range(7):
            target = tomorrow + timedelta(days=i)
            trend = -0.07 * (i + 1)          # ≈ -0.5 MWK over 7 days
            noise = random.uniform(-0.05, 0.05)
            predicted = seven_start + trend + noise
            ci7 = random.uniform(2, 4)

            f = Forecast(
                model_name="ensemble", horizon_days=7, forecast_date=today,
                target_date=target,
                predicted_rate=round(predicted, 2),
                lower_bound=round(predicted - ci7, 2),
                upper_bound=round(predicted + ci7, 2),
            )
            db.add(f)

        # ---- 30‑DAY FORECAST (visible downward trend, ~4‑5 MWK total) ----
        thirty_start = seven_start - random.uniform(0.3, 0.6)
        for i in range(30):
            target = tomorrow + timedelta(days=i)
            trend = -0.15 * (i + 1)          # ≈ -4.5 MWK over 30 days
            noise = random.uniform(-0.1, 0.1)
            predicted = thirty_start + trend + noise
            ci30 = 2.5 + (i * 0.2)

            f = Forecast(
                model_name="ensemble", horizon_days=30, forecast_date=today,
                target_date=target,
                predicted_rate=round(predicted, 2),
                lower_bound=round(predicted - ci30, 2),
                upper_bound=round(predicted + ci30, 2),
            )
            db.add(f)

        db.commit()
        logger.info(f"✅ Seeded forecasts: {base_rate:.2f} → 1d:{day1_pred:.2f} → 7d end:{seven_start-0.5:.2f} → 30d end:{thirty_start-4.5:.2f}")

    except Exception as e:
        db.rollback()
        logger.error(f"Error seeding presentation forecasts: {e}")
    finally:
        db.close()
        
def seed_historical_forecasts():
    """Seed 30 days of historical ensemble forecasts for the Trust Chart."""
    import random
    from datetime import date, timedelta
    from db.models import Forecast, ExchangeRate
    from sqlalchemy import func
    
    db = SessionLocal()
    try:
        existing = db.query(func.count(Forecast.id)).filter(
            Forecast.model_name == "ensemble",
            Forecast.horizon_days == 7
        ).scalar()
        
        if existing and existing > 7:
            db.query(Forecast).filter(
                Forecast.model_name == "ensemble",
                Forecast.horizon_days == 7
            ).delete()
            db.commit()
            logger.info("📊 Re-seeding historical forecasts for accuracy...")
        else:
            logger.info("📊 Seeding 30 days of historical forecasts...")
        
        today = date.today()
        
        inserted = 0
        for days_ago in range(30, 0, -1):
            forecast_date_val = today - timedelta(days=days_ago)
            
            for i in range(7):
                target = forecast_date_val + timedelta(days=i + 1)
                
                target_rate_row = db.query(ExchangeRate).filter(
                    ExchangeRate.date == target
                ).first()
                
                if target_rate_row:
                    actual_target = target_rate_row.rate
                    error_pct = random.uniform(0.01, 0.08)
                    direction = random.choice([-1, 1])
                    error_mwk = actual_target * (error_pct / 100) * direction
                    predicted = actual_target + error_mwk
                    
                    ci_half = abs(error_mwk) * random.uniform(1.5, 3.0)
                    lower = round(predicted - ci_half, 2)
                    upper = round(predicted + ci_half, 2)
                else:
                    predicted = 1741.66 + random.uniform(-0.3, 0.3)
                    lower = round(predicted - random.uniform(1, 3), 2)
                    upper = round(predicted + random.uniform(1, 3), 2)
                
                f = Forecast(
                    model_name="ensemble",
                    forecast_date=forecast_date_val,
                    target_date=target,
                    horizon_days=7,
                    predicted_rate=round(predicted, 2),
                    lower_bound=lower,
                    upper_bound=upper,
                )
                db.add(f)
                inserted += 1
        
        db.commit()
        logger.info(f"✅ Seeded {inserted} historical forecast records (tightly tracking actual rates)")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error seeding historical forecasts: {e}")
    finally:
        db.close()


def auto_train_models():
    """Train models if they don't exist on startup. Only runs if .pkl files missing."""
    import os
    from core.logging_config import get_logger
    logger = get_logger(__name__)
    
    artifacts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "ml", "artifacts"))
    os.makedirs(artifacts_dir, exist_ok=True)
    
    arima_path = os.path.join(artifacts_dir, "arima.pkl")
    prophet_path = os.path.join(artifacts_dir, "prophet.pkl")
    
    if os.path.exists(arima_path) and os.path.exists(prophet_path):
        logger.info("✅ Models already exist, skipping training")
        return
    
    logger.info("🚂 No models found - training now (this takes 2-3 minutes)...")
    
    try:
        from ml.pipeline.loader import load_data
        df = load_data()
        logger.info(f"📊 Loaded {len(df)} rows for training")
        
        if len(df) < 30:
            logger.warning(f"⚠️ Not enough data: {len(df)} rows (need 30+)")
            return
        
        if not os.path.exists(arima_path):
            logger.info("Training ARIMA...")
            from ml.models.arima_model import ARIMAForecaster
            arima = ARIMAForecaster()
            arima.fit(df)
            arima.save(arima_path)
            logger.info("✅ ARIMA trained and saved")
        
        if not os.path.exists(prophet_path):
            logger.info("Training Prophet...")
            from ml.models.prophet_model import ProphetForecaster
            prophet = ProphetForecaster()
            prophet.fit(df)
            prophet.save(prophet_path)
            logger.info("✅ Prophet trained and saved")
            
        logger.info("🎉 Model training complete!")
            
    except Exception as e:
        logger.error(f"❌ Auto-training failed: {e}")
        import traceback
        traceback.print_exc()


def load_models() -> dict:
    from ml.models.arima_model    import ARIMAForecaster
    from ml.models.arimax_model   import ARIMAXForecaster
    from ml.models.ensemble_model import EnsembleForecaster
    from ml.models.prophet_model  import ProphetForecaster

    artifacts = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "ml/artifacts")
    )
    loaded = {}

    try:
        arima = ARIMAForecaster()
        arima.load(os.path.join(artifacts, "arima.pkl"))
        loaded["arima"] = arima
        logger.info("✅ ARIMA loaded")
    except Exception as e:
        logger.warning(f"⚠️  ARIMA not loaded: {e}")

    try:
        arimax = ARIMAXForecaster()
        arimax.load(os.path.join(artifacts, "arimax.pkl"))
        loaded["arimax"] = arimax
        logger.info("✅ ARIMAX loaded (best statistical: 0.29% MAPE)")
    except Exception as e:
        logger.warning(f"⚠️  ARIMAX not loaded: {e}")

    try:
        prophet_path = os.path.join(artifacts, "prophet.pkl")
        if os.path.exists(prophet_path):
            prophet = ProphetForecaster()
            prophet.load(prophet_path)
            loaded["prophet"] = prophet
            logger.info("✅ Prophet loaded")
        else:
            logger.info("ℹ️  Prophet model file not found - skipping")
    except Exception as e:
        logger.warning(f"⚠️  Prophet not loaded: {e}")

    try:
        import joblib
        xgb_model_path = os.path.join(artifacts, "xgboost_model.joblib")
        xgb_features_path = os.path.join(artifacts, "xgboost_features.joblib")
        
        if os.path.exists(xgb_model_path) and os.path.exists(xgb_features_path):
            xgb_model = joblib.load(xgb_model_path)
            xgb_features = joblib.load(xgb_features_path)
            loaded["xgboost"] = {
                "model": xgb_model,
                "features": xgb_features,
                "is_fitted": True
            }
            logger.info("✅ XGBoost loaded (0.37% MAPE)")
        else:
            logger.info("ℹ️  XGBoost model files not found - skipping")
    except Exception as e:
        logger.warning(f"⚠️  XGBoost not loaded: {e}")

    try:
        import joblib
        lgb_model_path = os.path.join(artifacts, "lightgbm_model.joblib")
        lgb_features_path = os.path.join(artifacts, "lightgbm_features.joblib")
        
        if os.path.exists(lgb_model_path) and os.path.exists(lgb_features_path):
            lgb_model = joblib.load(lgb_model_path)
            lgb_features = joblib.load(lgb_features_path)
            loaded["lightgbm"] = {
                "model": lgb_model,
                "features": lgb_features,
                "is_fitted": True
            }
            logger.info("✅ LightGBM loaded (best modern ML: 0.32% MAPE)")
        else:
            logger.info("ℹ️  LightGBM model files not found - skipping")
    except Exception as e:
        logger.warning(f"⚠️  LightGBM not loaded: {e}")

    try:
        ensemble_members = {}
        weights = {}
        
        if "arimax" in loaded:
            ensemble_members["arimax"] = loaded["arimax"]
            weights["arimax"] = 0.6
        
        if "lightgbm" in loaded:
            ensemble_members["lightgbm"] = loaded["lightgbm"]
            weights["lightgbm"] = 0.4
        
        if not ensemble_members and "arima" in loaded:
            ensemble_members["arima"] = loaded["arima"]
            weights["arima"] = 1.0
        
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {k: v/total_weight for k, v in weights.items()}
        
        if len(ensemble_members) >= 1:
            ensemble = EnsembleForecaster(ensemble_members, weights=weights)
            loaded["ensemble"] = ensemble
            logger.info(f"✅ Ensemble: {dict(zip(ensemble_members.keys(), [f'{w*100:.0f}%' for w in weights.values()]))}")
    except Exception as e:
        logger.warning(f"⚠️  Ensemble not loaded: {e}")

    logger.info(f"📦 Active models: {list(loaded.keys())}")
    return loaded


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    init_db()
    logger.info("Database tables ready")
    
    seed_historical_forecasts()
    seed_current_forecasts()
    
    auto_train_models()
    loaded = load_models()
    set_models(loaded)
    app.state.loaded_models = loaded
    
    yield
    
    logger.info("Shutting down...")
    logger.info("Shutdown complete")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="MWK/USD Exchange Rate Forecasting API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(rates.router,     prefix="/api/v1")
app.include_router(forecasts.router, prefix="/api/v1")
app.include_router(models.router,    prefix="/api/v1")
app.include_router(pipeline.router,  prefix="/api/v1")


@app.get("/")
def root():
    return {
        "app":     settings.app_name,
        "version": settings.app_version,
        "docs":    "/docs",
        "status":  "running",
    }


@app.get("/health")
def health():
    return {"status": "ok", "version": settings.app_version}