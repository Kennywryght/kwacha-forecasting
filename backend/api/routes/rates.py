import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from db.database import get_db
from db import crud
from datetime import date, timedelta
from typing import Optional

router = APIRouter(prefix="/rates", tags=["Exchange Rates"])


@router.get("/latest")
def get_latest_rate(db: Session = Depends(get_db)):
    record = crud.get_latest_rate(db)
    if not record:
        raise HTTPException(status_code=404, detail="No rates found in database")
    return {
        "date":         str(record.date),
        "rate":         record.rate,
        "daily_return": record.daily_return,
        "source":       record.source,
        "is_interpolated": record.is_interpolated,
    }


@router.get("/history")
def get_rate_history(
    start: Optional[date] = Query(default=None),
    end:   Optional[date] = Query(default=None),
    limit: int            = Query(default=365, le=3000),
    db:    Session        = Depends(get_db),
):
    if not start:
        start = date.today() - timedelta(days=365)
    if not end:
        end = date.today()

    records = crud.get_rates_by_range(db, start, end)
    if not records:
        raise HTTPException(status_code=404, detail="No data for given range")

    return {
        "start_date":  str(start),
        "end_date":    str(end),
        "total":       len(records),
        "latest_rate": records[-1].rate,
        "data": [
            {
                "date":         str(r.date),
                "rate":         r.rate,
                "daily_return": r.daily_return,
                "is_interpolated": r.is_interpolated,
            }
            for r in records
        ],
    }


@router.get("/status")
def get_data_status(db: Session = Depends(get_db)):
    latest = crud.get_latest_rate(db)
    total  = crud.get_rate_count(db)
    if not latest:
        raise HTTPException(status_code=404, detail="No data found")

    days_since = (date.today() - latest.date).days
    return {
        "latest_date":       str(latest.date),
        "total_records":     total,
        "days_since_update": days_since,
        "is_stale":          days_since > 3,
    }