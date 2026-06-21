import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from db.database import get_db
from db import crud
from db.models import ExchangeRate
from datetime import date, timedelta, datetime
from typing import Optional

from ml.pipeline.live_fetcher import fetch_current_rate
from core.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/rates", tags=["Exchange Rates"])

# ── In-memory cache for live rates (60 seconds only) ──
_live_rate_cache = {
    "rate": None,
    "timestamp": None
}
CACHE_TTL_SECONDS = 60   # was 600 — reduced so rate stays accurate


@router.get("/latest")
def get_latest_rate(db: Session = Depends(get_db)):
    """
    Returns the most recent exchange rate.
    Priority: cache (60s) → today's DB row → live fetch → latest DB row (stale).
    """
    now = datetime.utcnow()

    # 1. Serve from cache if still fresh
    if (
        _live_rate_cache["rate"]
        and _live_rate_cache["timestamp"]
        and (now - _live_rate_cache["timestamp"]).total_seconds() < CACHE_TTL_SECONDS
    ):
        cached = _live_rate_cache["rate"]
        return {
            "date": cached["date"],
            "rate": cached["rate"],
            "source": cached.get("source", "cache"),
            "stale": False,
            "daily_return": None,
            "is_interpolated": False,
        }

    # 2. Try live fetch first — always prefer fresh data
    live_rate = fetch_current_rate()
    if live_rate and live_rate.get("rate"):
        today = date.today()
        # Persist so the ML pipeline sees today's rate
        try:
            crud.upsert_rate(db, today, live_rate["rate"], source="live")
        except Exception as e:
            logger.warning(f"Could not persist live rate: {e}")

        _live_rate_cache["rate"] = {
            "date": live_rate.get("date", str(today)),
            "rate": live_rate["rate"],
            "source": "live",
        }
        _live_rate_cache["timestamp"] = now
        return {
            "date": live_rate.get("date", str(today)),
            "rate": live_rate["rate"],
            "source": "live",
            "stale": False,
            "daily_return": None,
            "is_interpolated": False,
        }

    # 3. Live fetch failed — check today's DB row
    today = date.today()
    today_record = db.query(ExchangeRate).filter(ExchangeRate.date == today).first()
    if today_record:
        _live_rate_cache["rate"] = {
            "date": str(today_record.date),
            "rate": today_record.rate,
            "source": today_record.source or "db",
        }
        _live_rate_cache["timestamp"] = now
        return {
            "date": str(today_record.date),
            "rate": today_record.rate,
            "daily_return": today_record.daily_return,
            "source": today_record.source,
            "is_interpolated": today_record.is_interpolated,
            "stale": False,
        }

    # 4. Fallback to most recent DB record
    record = crud.get_latest_rate(db)
    if not record:
        raise HTTPException(status_code=404, detail="No rates found in database")

    logger.warning(f"Live fetch failed, serving stale rate from {record.date}")
    return {
        "date": str(record.date),
        "rate": record.rate,
        "daily_return": record.daily_return,
        "source": record.source,
        "is_interpolated": record.is_interpolated,
        "stale": True,
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
                "date":            str(r.date),
                "rate":            r.rate,
                "daily_return":    r.daily_return,
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