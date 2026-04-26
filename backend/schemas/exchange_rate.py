from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional, List
from enum import Enum


class ForecastHorizon(str, Enum):
    next_day  = "1"
    one_week  = "7"
    one_month = "30"


class ExchangeRateBase(BaseModel):
    date:         date
    rate:         float = Field(..., gt=0)
    daily_return: Optional[float] = None
    source:       Optional[str] = "api"


class ExchangeRateCreate(ExchangeRateBase):
    pass


class ExchangeRateResponse(ExchangeRateBase):
    id:              int
    is_interpolated: bool
    created_at:      datetime

    class Config:
        from_attributes = True


class ExchangeRateHistory(BaseModel):
    data:        List[ExchangeRateResponse]
    total:       int
    start_date:  date
    end_date:    date
    latest_rate: float


class ForecastPoint(BaseModel):
    target_date:    date
    predicted_rate: float
    lower_bound:    Optional[float] = None
    upper_bound:    Optional[float] = None
    horizon_days:   int


class ForecastResponse(BaseModel):
    model_name:    str
    forecast_date: date
    horizon_days:  int
    forecasts:     List[ForecastPoint]
    rmse:          Optional[float] = None
    mape:          Optional[float] = None
    mae:           Optional[float] = None
    model_run_id:  Optional[int] = None


class AllModelsForecasts(BaseModel):
    arima:        Optional[ForecastResponse] = None
    arimax:       Optional[ForecastResponse] = None
    lstm:         Optional[ForecastResponse] = None
    ensemble:     Optional[ForecastResponse] = None
    generated_at: datetime


class ModelMetrics(BaseModel):
    model_name:  str
    rmse:        Optional[float]
    mae:         Optional[float]
    mape:        Optional[float]
    r_squared:   Optional[float]
    trained_at:  Optional[datetime]
    train_start: Optional[date]
    train_end:   Optional[date]
    is_active:   bool


class ModelComparisonResponse(BaseModel):
    models: List[ModelMetrics]


class DataStatusResponse(BaseModel):
    latest_date:       date
    total_records:     int
    days_since_update: int
    is_stale:          bool
    last_fetch_status: Optional[str]