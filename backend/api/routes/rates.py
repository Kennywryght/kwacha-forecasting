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
from ml.pipeline.google_rate_fetcher import get_google_rate

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
    Priority: Google (1h cache) → cache → today's DB → live fetch → latest DB.
    """
    now = datetime.utcnow()

    # 1. Serve from cache if still fresh (60 seconds)
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

    # 2. Try Google rate first (most accurate)
    google_rate = get_google_rate()
    if google_rate and google_rate.get("rate"):
        today = date.today()
        rate_val = google_rate["rate"]
        
        # Persist to database
        try:
            crud.upsert_rate(db, today, rate_val, source="google")
        except Exception as e:
            logger.warning(f"Could not persist Google rate: {e}")

        _live_rate_cache["rate"] = {
            "date": google_rate.get("date", str(today)),
            "rate": rate_val,
            "source": "google",
        }
        _live_rate_cache["timestamp"] = now
        
        return {
            "date": google_rate.get("date", str(today)),
            "rate": rate_val,
            "source": "google",
            "stale": False,
            "daily_return": None,
            "is_interpolated": False,
        }

    # 3. Fallback to live API fetchers (open.er-api, exchangerate.host, etc.)
    live_rate = fetch_current_rate()
    if live_rate and live_rate.get("rate"):
        today = date.today()
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

    # 4. Check today's DB row
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

    # 5. Fallback to most recent DB record
    record = crud.get_latest_rate(db)
    if not record:
        raise HTTPException(status_code=404, detail="No rates found in database")

    logger.warning(f"All fetchers failed, serving stale rate from {record.date}")
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
    
    
# ── Google Rate Refresh ──────────────────────────────────────────────────────
@router.post("/refresh-google")
def refresh_google_rate(db: Session = Depends(get_db)):
    """Force refresh the exchange rate from Google."""
    google_rate = get_google_rate(force_refresh=True)
    
    if not google_rate or not google_rate.get("rate"):
        raise HTTPException(status_code=502, detail="Failed to fetch rate from Google")
    
    today = date.today()
    rate_val = google_rate["rate"]
    
    # Persist to database
    try:
        crud.upsert_rate(db, today, rate_val, source="google")
    except Exception as e:
        logger.warning(f"Could not persist Google rate: {e}")
    
    _live_rate_cache["rate"] = {
        "date": str(today),
        "rate": rate_val,
        "source": "google",
    }
    _live_rate_cache["timestamp"] = datetime.utcnow()
    
    return {
        "status": "ok",
        "date": str(today),
        "rate": rate_val,
        "source": "google",
        "message": f"Rate refreshed from Google: {rate_val} MWK/USD"
    }