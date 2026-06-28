import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from db.database import get_db
from db import crud
from db.models import ExchangeRate
from datetime import date, timedelta, datetime
from typing import Optional
import io, csv

from ml.pipeline.live_fetcher import fetch_current_rate
from core.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/rates", tags=["Exchange Rates"])

_live_rate_cache = {"rate": None, "timestamp": None}
CACHE_TTL_SECONDS = 60


@router.get("/latest")
def get_latest_rate(db: Session = Depends(get_db)):
    """Returns the most recent exchange rate."""
    now = datetime.utcnow()

    if (_live_rate_cache["rate"] and _live_rate_cache["timestamp"] and 
        (now - _live_rate_cache["timestamp"]).total_seconds() < CACHE_TTL_SECONDS):
        cached = _live_rate_cache["rate"]
        return {"date": cached["date"], "rate": cached["rate"], "source": cached.get("source", "cache"),
                "stale": False, "daily_return": None, "is_interpolated": False}

    live_rate = fetch_current_rate()
    if live_rate and live_rate.get("rate"):
        today = date.today()
        try:
            crud.upsert_rate(db, today, live_rate["rate"], source="live")
        except Exception as e:
            logger.warning(f"Could not persist live rate: {e}")
        _live_rate_cache["rate"] = {"date": live_rate.get("date", str(today)), "rate": live_rate["rate"], "source": "live"}
        _live_rate_cache["timestamp"] = now
        return {"date": live_rate.get("date", str(today)), "rate": live_rate["rate"], "source": "live",
                "stale": False, "daily_return": None, "is_interpolated": False}

    today = date.today()
    today_record = db.query(ExchangeRate).filter(ExchangeRate.date == today).first()
    if today_record:
        _live_rate_cache["rate"] = {"date": str(today_record.date), "rate": today_record.rate, "source": today_record.source or "db"}
        _live_rate_cache["timestamp"] = now
        return {"date": str(today_record.date), "rate": today_record.rate, "daily_return": today_record.daily_return,
                "source": today_record.source, "is_interpolated": today_record.is_interpolated, "stale": False}

    record = crud.get_latest_rate(db)
    if not record:
        raise HTTPException(status_code=404, detail="No rates found in database")
    logger.warning(f"Serving stale rate from {record.date}")
    return {"date": str(record.date), "rate": record.rate, "daily_return": record.daily_return,
            "source": record.source, "is_interpolated": record.is_interpolated, "stale": True}


@router.get("/history")
def get_rate_history(start: Optional[date] = Query(default=None), end: Optional[date] = Query(default=None),
                     limit: int = Query(default=365, le=3000), db: Session = Depends(get_db)):
    if not start: start = date.today() - timedelta(days=365)
    if not end: end = date.today()
    records = crud.get_rates_by_range(db, start, end)
    if not records:
        raise HTTPException(status_code=404, detail="No data for given range")
    return {
        "start_date": str(start), "end_date": str(end), "total": len(records), "latest_rate": records[-1].rate,
        "data": [{"date": str(r.date), "rate": r.rate, "daily_return": r.daily_return, "is_interpolated": r.is_interpolated} for r in records],
    }


@router.get("/status")
def get_data_status(db: Session = Depends(get_db)):
    latest = crud.get_latest_rate(db)
    total = crud.get_rate_count(db)
    if not latest: raise HTTPException(status_code=404, detail="No data found")
    return {"latest_date": str(latest.date), "total_records": total, "days_since_update": (date.today() - latest.date).days, "is_stale": (date.today() - latest.date).days > 3}


# ═══════════════════════════════════════════════════════════════════════════════
# NEW ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/stats")
def get_rate_statistics(db: Session = Depends(get_db)):
    """Get statistical summary of exchange rates for dashboard."""
    rates = db.query(ExchangeRate).order_by(ExchangeRate.date.desc()).limit(365).all()
    if not rates: raise HTTPException(status_code=404, detail="No rates found")
    
    rate_values = [r.rate for r in rates]
    current = rate_values[0]
    week_ago = rate_values[6] if len(rate_values) > 6 else rate_values[-1]
    month_ago = rate_values[29] if len(rate_values) > 29 else rate_values[-1]
    
    return {
        "current": current,
        "min_7d": min(rate_values[:7]),
        "max_7d": max(rate_values[:7]),
        "avg_7d": round(sum(rate_values[:7]) / min(7, len(rate_values)), 2),
        "change_7d": round(current - week_ago, 2),
        "change_pct_7d": round((current - week_ago) / week_ago * 100, 4),
        "min_30d": min(rate_values[:30]) if len(rate_values) >= 30 else None,
        "max_30d": max(rate_values[:30]) if len(rate_values) >= 30 else None,
        "avg_30d": round(sum(rate_values[:30]) / 30, 2) if len(rate_values) >= 30 else None,
        "change_30d": round(current - month_ago, 2) if len(rate_values) >= 30 else None,
        "change_pct_30d": round((current - month_ago) / month_ago * 100, 4) if len(rate_values) >= 30 else None,
    }


@router.get("/alerts")
def get_rate_alerts(threshold: float = Query(default=1.0), db: Session = Depends(get_db)):
    """Check if rate has changed significantly for alert system."""
    rates = db.query(ExchangeRate).order_by(ExchangeRate.date.desc()).limit(7).all()
    if len(rates) < 2: return {"alert": False, "message": "Not enough data"}
    
    current = rates[0].rate
    week_ago = rates[-1].rate
    change_pct = abs((current - week_ago) / week_ago * 100)
    
    return {
        "alert": change_pct > threshold,
        "current_rate": current,
        "week_ago_rate": week_ago,
        "change_pct": round(change_pct, 4),
        "message": f"Rate changed by {change_pct:.2f}% in the last 7 days" if change_pct > threshold else "Rate is stable"
    }


@router.get("/export")
def export_rates(format: str = Query(default="json"), start: Optional[date] = Query(default=None), 
                 end: Optional[date] = Query(default=None), db: Session = Depends(get_db)):
    """Export exchange rates in JSON or CSV format."""
    if not start: start = date.today() - timedelta(days=90)
    if not end: end = date.today()
    
    records = crud.get_rates_by_range(db, start, end)
    if not records: raise HTTPException(status_code=404, detail="No data for given range")
    
    data = [{"date": str(r.date), "rate": r.rate, "source": r.source} for r in records]
    
    if format == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["date", "rate", "source"])
        writer.writeheader()
        writer.writerows(data)
        return Response(content=output.getvalue(), media_type="text/csv",
                       headers={"Content-Disposition": f"attachment; filename=mwk_usd_rates_{start}_{end}.csv"})
    
    return {"start_date": str(start), "end_date": str(end), "total": len(records), "rates": data}