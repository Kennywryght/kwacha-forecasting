from sqlalchemy import (
    Column, Integer, Float, String, Boolean,
    DateTime, Date, Text, ForeignKey, Index
)
from sqlalchemy.orm import relationship
from datetime import datetime
from db.database import Base


class ExchangeRate(Base):
    __tablename__ = "exchange_rates"

    id              = Column(Integer, primary_key=True, index=True)
    date            = Column(Date, unique=True, nullable=False, index=True)
    rate            = Column(Float, nullable=False)
    open_rate       = Column(Float, nullable=True)
    high_rate       = Column(Float, nullable=True)
    low_rate        = Column(Float, nullable=True)
    daily_return    = Column(Float, nullable=True)
    is_interpolated = Column(Boolean, default=False)
    source          = Column(String(50), default="csv_import")
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_exchange_rates_date_source", "date", "source"),
    )


class MacroIndicator(Base):
    __tablename__ = "macro_indicators"

    id                      = Column(Integer, primary_key=True, index=True)
    date                    = Column(Date, nullable=False, index=True)
    inflation               = Column(Float, nullable=True)
    money_supply_m2         = Column(Float, nullable=True)
    foreign_reserves        = Column(Float, nullable=True)
    current_account_balance = Column(Float, nullable=True)
    lending_interest_rate   = Column(Float, nullable=True)
    real_interest_rate      = Column(Float, nullable=True)
    gdp_growth              = Column(Float, nullable=True)
    us_cpi                  = Column(Float, nullable=True)
    us_cpi_yoy              = Column(Float, nullable=True)
    us_fed_rate             = Column(Float, nullable=True)
    inflation_diff          = Column(Float, nullable=True)
    interest_rate_diff      = Column(Float, nullable=True)
    source                  = Column(String(50), default="csv_import")
    created_at              = Column(DateTime, default=datetime.utcnow)


class Forecast(Base):
    __tablename__ = "forecasts"

    id              = Column(Integer, primary_key=True, index=True)
    model_name      = Column(String(50), nullable=False)
    forecast_date   = Column(Date, nullable=False)
    target_date     = Column(Date, nullable=False)
    horizon_days    = Column(Integer, nullable=False)
    predicted_rate  = Column(Float, nullable=False)
    lower_bound     = Column(Float, nullable=True)
    upper_bound     = Column(Float, nullable=True)
    actual_rate     = Column(Float, nullable=True)
    error           = Column(Float, nullable=True)
    model_run_id    = Column(Integer, ForeignKey("model_runs.id"), nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)

    model_run = relationship("ModelRun", back_populates="forecasts")

    __table_args__ = (
        Index("ix_forecasts_model_date", "model_name", "forecast_date"),
        Index("ix_forecasts_target_date", "target_date"),
    )


class ModelRun(Base):
    __tablename__ = "model_runs"

    id            = Column(Integer, primary_key=True, index=True)
    model_name    = Column(String(50), nullable=False)
    mlflow_run_id = Column(String(100), nullable=True)
    mlflow_run_url= Column(String(255), nullable=True)
    train_start   = Column(Date, nullable=True)
    train_end     = Column(Date, nullable=True)
    rmse          = Column(Float, nullable=True)
    mae           = Column(Float, nullable=True)
    mape          = Column(Float, nullable=True)
    r_squared     = Column(Float, nullable=True)
    params        = Column(Text, nullable=True)
    is_active     = Column(Boolean, default=True)
    notes         = Column(Text, nullable=True)
    trained_at    = Column(DateTime, default=datetime.utcnow)

    forecasts = relationship("Forecast", back_populates="model_run")


class DataFetchLog(Base):
    __tablename__ = "data_fetch_logs"

    id           = Column(Integer, primary_key=True, index=True)
    fetch_type   = Column(String(50))
    source       = Column(String(100))
    status       = Column(String(20))
    rows_fetched = Column(Integer, default=0)
    error_msg    = Column(Text, nullable=True)
    fetched_at   = Column(DateTime, default=datetime.utcnow)