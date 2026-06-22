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
from db.database import init_db
from api.routes import rates, forecasts, models, pipeline
from api.routes.forecasts import set_models

setup_logging()
logger   = get_logger(__name__)
settings = get_settings()


def auto_train_models():
    """Train models if they don't exist on startup."""
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
        logger.info("✅ ARIMAX loaded")
    except Exception as e:
        logger.warning(f"⚠️  ARIMAX not loaded: {e}")

    # ---- Prophet — load via ProphetForecaster so .refit() is available ----
    try:
        prophet_path = os.path.join(artifacts, "prophet.pkl")
        prophet = ProphetForecaster()
        prophet.load(prophet_path)
        loaded["prophet"] = prophet
        logger.info("✅ Prophet loaded via ProphetForecaster")
    except Exception as e:
        logger.warning(f"⚠️  Prophet not loaded: {e}")

    # ---- Ensemble ----
    try:
        members = {k: v for k, v in loaded.items() if k != "ensemble"}
        if len(members) >= 1:
            ensemble = EnsembleForecaster(members)
            ens_path = os.path.join(artifacts, "ensemble.pkl")
            if os.path.exists(ens_path):
                ensemble.load(ens_path)
            loaded["ensemble"] = ensemble
            logger.info(f"✅ Ensemble loaded with members: {list(members.keys())}")
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
    allow_origins=settings.allowed_origins,
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