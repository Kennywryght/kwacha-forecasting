import os
import sys
import pandas as pd
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, text
from db.models import ExchangeRate, MacroIndicator, Forecast, ModelRun, DataFetchLog
from datetime import date, datetime
from typing import List, Optional
import json
from contextlib import contextmanager


@contextmanager
def safe_transaction(db: Session, operation: str = "unknown"):
    """Context manager for safe database transactions with rollback."""
    try:
        yield
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Transaction failed [{operation}]: {e}")
        raise


# ── Exchange Rates ─────────────────────────────────────────────────────────────

def get_latest_rate(db: Session) -> Optional[ExchangeRate]:
    try:
        return db.query(ExchangeRate).order_by(desc(ExchangeRate.date)).first()
    except Exception:
        db.rollback()
        return None


def get_rates_by_range(db: Session, start: date, end: date) -> List[ExchangeRate]:
    try:
        return (
            db.query(ExchangeRate)
            .filter(ExchangeRate.date >= start, ExchangeRate.date <= end)
            .order_by(asc(ExchangeRate.date))
            .all()
        )
    except Exception:
        db.rollback()
        return []


def get_all_rates(db: Session, limit: int = 1000) -> List[ExchangeRate]:
    try:
        return (
            db.query(ExchangeRate)
            .order_by(desc(ExchangeRate.date))
            .limit(limit)
            .all()
        )
    except Exception:
        db.rollback()
        return []


def get_rate_count(db: Session) -> int:
    try:
        return db.query(ExchangeRate).count()
    except Exception:
        db.rollback()
        return 0


def upsert_rate(db: Session, date_val: date, rate: float,
                daily_return: float = None, is_interpolated: bool = False,
                source: str = "api") -> ExchangeRate:
    with safe_transaction(db, "upsert_rate"):
        existing = db.query(ExchangeRate).filter(ExchangeRate.date == date_val).first()
        if existing:
            existing.rate = rate
            existing.daily_return = daily_return
            existing.source = source
            existing.updated_at = datetime.utcnow()
            return existing
        record = ExchangeRate(
            date=date_val, rate=rate, daily_return=daily_return,
            is_interpolated=is_interpolated, source=source
        )
        db.add(record)
        db.flush()
        return record


# ── Forecasts ──────────────────────────────────────────────────────────────────

def delete_forecasts(db: Session, model_name: str, horizon: int, forecast_date: date):
    """Remove existing forecasts for this model/horizon/forecast_date (date object)."""
    with safe_transaction(db, f"delete_forecasts_{model_name}"):
        db.query(Forecast).filter(
            Forecast.model_name == model_name,
            Forecast.horizon_days == horizon,
            Forecast.forecast_date == forecast_date
        ).delete()


def save_forecasts_bulk(db: Session, forecasts: list):
    """Bulk insert a list of Forecast ORM objects."""
    with safe_transaction(db, "save_forecasts_bulk"):
        db.add_all(forecasts)
        db.flush()


# Legacy save_forecasts – kept for backward compatibility
def save_forecasts(db: Session, model_name: str, horizon: int,
                   forecast_data: dict, model_run_id: int = None):
    """
    forecast_data expected: {
        "dates": list[str]   e.g. "2026-04-18",
        "predicted": list[float],
        "lower_bound": list[float],
        "upper_bound": list[float]
    }
    """
    forecast_date = date.today()
    with safe_transaction(db, f"save_forecasts_{model_name}"):
        db.query(Forecast).filter(
            Forecast.model_name == model_name,
            Forecast.horizon_days == horizon,
            Forecast.forecast_date == forecast_date.isoformat()
        ).delete()

        records = []
        for d, p, lo, hi in zip(
            forecast_data["dates"],
            forecast_data["predicted"],
            forecast_data["lower_bound"],
            forecast_data["upper_bound"],
        ):
            records.append(Forecast(
                model_name=model_name,
                forecast_date=forecast_date,
                target_date=date.fromisoformat(d),
                horizon_days=horizon,
                predicted_rate=p,
                lower_bound=lo,
                upper_bound=hi,
                model_run_id=model_run_id,
            ))
        db.bulk_save_objects(records)


def get_latest_forecasts(db: Session, model_name: str,
                         horizon: int) -> List[Forecast]:
    try:
        latest_date = (
            db.query(Forecast.forecast_date)
            .filter(Forecast.model_name == model_name,
                    Forecast.horizon_days == horizon)
            .order_by(desc(Forecast.forecast_date))
            .first()
        )
        if not latest_date:
            return []
        return (
            db.query(Forecast)
            .filter(
                Forecast.model_name == model_name,
                Forecast.horizon_days == horizon,
                Forecast.forecast_date == latest_date[0],
            )
            .order_by(asc(Forecast.target_date))
            .all()
        )
    except Exception:
        db.rollback()
        return []


def create_forecast(db: Session, forecast_data: dict):
    """Helper to create a single forecast entry from a dict of field values."""
    with safe_transaction(db, "create_forecast"):
        db_forecast = Forecast(**forecast_data)
        db.add(db_forecast)
        db.flush()
        db.refresh(db_forecast)
        return db_forecast


# ── Model Runs ─────────────────────────────────────────────────────────────────

def save_model_run(db: Session, model_name: str, metrics: dict,
                   params: dict, mlflow_run_id: str = None,
                   train_start: date = None, train_end: date = None) -> ModelRun:
    with safe_transaction(db, f"save_model_run_{model_name}"):
        # Deactivate old runs for this model
        db.query(ModelRun).filter(
            ModelRun.model_name == model_name
        ).update({"is_active": False})

        run = ModelRun(
            model_name=model_name,
            mlflow_run_id=mlflow_run_id,
            train_start=train_start,
            train_end=train_end,
            rmse=metrics.get("rmse"),
            mae=metrics.get("mae"),
            mape=metrics.get("mape"),
            r_squared=metrics.get("r_squared"),
            params=json.dumps(params),
            is_active=True,
        )
        db.add(run)
        db.flush()
        db.refresh(run)
        return run


def get_active_model_runs(db: Session) -> List[ModelRun]:
    try:
        return db.query(ModelRun).filter(ModelRun.is_active == True).all()
    except Exception:
        db.rollback()
        return []


# ── Data Fetch Log ─────────────────────────────────────────────────────────────

def log_fetch(db: Session, fetch_type: str, source: str,
              status: str, rows: int = 0, error: str = None):
    with safe_transaction(db, "log_fetch"):
        record = DataFetchLog(
            fetch_type=fetch_type, source=source,
            status=status, rows_fetched=rows, error_msg=error
        )
        db.add(record)
        db.flush()


# ── Utility for trainer ────────────────────────────────────────────────────────

def get_all_rates_as_dataframe(db: Session) -> pd.DataFrame:
    """Return a DataFrame with columns 'date' and 'rate' sorted ascending."""
    try:
        rates = db.query(ExchangeRate).order_by(asc(ExchangeRate.date)).all()
        if not rates:
            return pd.DataFrame(columns=["date", "rate"])
        data = [{"date": r.date, "rate": r.rate} for r in rates]
        return pd.DataFrame(data)
    except Exception:
        db.rollback()
        return pd.DataFrame(columns=["date", "rate"])