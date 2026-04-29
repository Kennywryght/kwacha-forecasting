import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from core.config import get_settings
from core.logging_config import setup_logging, get_logger
from db.database import create_all_tables
from api.routes import rates, forecasts, models, pipeline
from api.routes.forecasts import set_models

setup_logging()
logger   = get_logger(__name__)
settings = get_settings()

# ── Load ML models at startup ──────────────────────────────────────────────────

def load_models() -> dict:
    from ml.models.arima_model    import ARIMAForecaster
    from ml.models.arimax_model   import ARIMAXForecaster
    from ml.models.ensemble_model import EnsembleForecaster

    artifacts = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "ml/artifacts")
    )
    loaded = {}

    try:
        arima = ARIMAForecaster()
        arima.load(os.path.join(artifacts, "arima.pkl"))
        loaded["arima"] = arima
        logger.info("ARIMA loaded ")
    except Exception as e:
        logger.warning(f"ARIMA not loaded: {e}")

    try:
        arimax = ARIMAXForecaster()
        arimax.load(os.path.join(artifacts, "arimax.pkl"))
        loaded["arimax"] = arimax
        logger.info("ARIMAX loaded ")
    except Exception as e:
        logger.warning(f"ARIMAX not loaded: {e}")

    # Updated: Ensemble only depends on ARIMA + ARIMAX
    try:
        if "arima" in loaded and "arimax" in loaded:
            ensemble = EnsembleForecaster(
                loaded["arima"], loaded["arimax"]
            )
            ensemble.load(os.path.join(artifacts, "ensemble.pkl"))
            loaded["ensemble"] = ensemble
            logger.info("Ensemble loaded ")
    except Exception as e:
        logger.warning(f"Ensemble not loaded: {e}")

    return loaded


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    create_all_tables()
    logger.info("Database tables ready ")
    loaded = load_models()
    set_models(loaded)
    logger.info(f"Models loaded: {list(loaded.keys())}")
    yield
    # Shutdown
    logger.info("Shutting down...")


# ── App ────────────────────────────────────────────────────────────────────────

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

# ── Routes ─────────────────────────────────────────────────────────────────────

app.include_router(rates.router,    prefix="/api/v1")
app.include_router(forecasts.router, prefix="/api/v1")
app.include_router(models.router,   prefix="/api/v1")
app.include_router(pipeline.router, prefix="/api/v1")


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