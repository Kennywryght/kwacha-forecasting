from pydantic_settings import BaseSettings
from typing import List
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = "MWK/USD Forecasting System"
    app_version: str = "1.0.0"
    debug: bool = True
    environment: str = "development"

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    allowed_origins: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ]

    database_url: str = "sqlite:///./mwk_forecasting.db"

    mlflow_tracking_uri: str = "./mlruns"
    mlflow_experiment_name: str = "mwk_usd_forecasting"

    exchange_rate_api_key: str = ""
    exchange_rate_api_url: str = "https://v6.exchangerate-api.com/v6"

    model_artifacts_dir: str = "./backend/ml/artifacts"
    forecast_horizons: List[int] = [1, 7, 30]

    retrain_schedule: str = "0 2 * * 0"
    data_update_schedule: str = "0 6 * * *"

    raw_data_path: str = "./data/raw/mwk_usd_final_dataset.csv"
    processed_data_path: str = "./data/processed/mwk_usd_clean.csv"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()