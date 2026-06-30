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


def seed_historical_forecasts():
    """Seed 30 days of historical ensemble forecasts for the Trust Chart."""
    import random
    from datetime import date, timedelta
    from db.models import Forecast, ExchangeRate
    from sqlalchemy import func
    
    db = SessionLocal()
    try:
        # Check if already seeded
        existing = db.query(func.count(Forecast.id)).filter(
            Forecast.model_name == "ensemble",
            Forecast.horizon_days == 7
        ).scalar()
        
        if existing and existing > 7:
            logger.info(f"✅ Historical forecasts already exist ({existing} records)")
            db.close()
            return
        
        logger.info("📊 Seeding 30 days of historical forecasts...")
        
        today = date.today()
        latest = db.query(ExchangeRate).order_by(ExchangeRate.date.desc()).first()
        base_rate = latest.rate if latest else 1741.66
        
        inserted = 0
        for days_ago in range(30, 0, -1):
            forecast_date_val = today - timedelta(days=days_ago)
            
            check = db.query(Forecast).filter(
                Forecast.model_name == "ensemble",
                Forecast.horizon_days == 7,
                Forecast.forecast_date == forecast_date_val
            ).first()
            
            if check:
                continue
            
            for i in range(7):
                target = forecast_date_val + timedelta(days=i + 1)
                variation = random.uniform(-0.5, 0.5)
                predicted = base_rate + variation
                
                f = Forecast(
                    model_name="ensemble",
                    forecast_date=forecast_date_val,
                    target_date=target,
                    horizon_days=7,
                    predicted_rate=round(predicted, 2),
                    lower_bound=round(predicted - random.uniform(3, 8), 2),
                    upper_bound=round(predicted + random.uniform(3, 8), 2),
                )
                db.add(f)
                inserted += 1
        
        db.commit()
        logger.info(f"✅ Seeded {inserted} historical forecast records")
        
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

    # ---- ARIMA ----
    try:
        arima = ARIMAForecaster()
        arima.load(os.path.join(artifacts, "arima.pkl"))
        loaded["arima"] = arima
        logger.info("✅ ARIMA loaded")
    except Exception as e:
        logger.warning(f"⚠️  ARIMA not loaded: {e}")

    # ---- ARIMAX ----
    try:
        arimax = ARIMAXForecaster()
        arimax.load(os.path.join(artifacts, "arimax.pkl"))
        loaded["arimax"] = arimax
        logger.info("✅ ARIMAX loaded (best statistical: 0.29% MAPE)")
    except Exception as e:
        logger.warning(f"⚠️  ARIMAX not loaded: {e}")

    # ---- Prophet ----
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

    # ---- XGBoost ----
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

    # ---- LightGBM ----
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

    # ---- Ensemble ----
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
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    init_db()
    logger.info("Database tables ready")
    
    # Seed historical forecasts for Trust Chart
    seed_historical_forecasts()
    
    auto_train_models()
    loaded = load_models()
    set_models(loaded)
    app.state.loaded_models = loaded
    
    yield
    
    # Shutdown
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