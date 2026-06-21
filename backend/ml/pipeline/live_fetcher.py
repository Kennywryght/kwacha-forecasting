"""Live exchange rate fetcher for MWK/USD.

This module fetches current and historical MWK/USD exchange rates
from various public APIs with fallback mechanisms and validation.
"""

import pandas as pd
import requests
from datetime import datetime, timedelta
import os
import sys
import json
import time
from typing import Optional, Dict, Any, Tuple
from functools import wraps

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from core.logging_config import get_logger
from db.database import SessionLocal
from db.models import ExchangeRate

logger = get_logger(__name__)

# ============================================================
# Configuration
# ============================================================
MWK_USD_MIN = 1500.0
MWK_USD_MAX = 2500.0
MAX_DAILY_CHANGE_PCT = 5.0  # Prevent unrealistic daily swings
CACHE_TTL = 3600  # 1 hour cache TTL

# Cache for live rates
_cache = {
    "rate": None,
    "timestamp": None,
    "source": None
}


def _is_plausible(rate: float) -> bool:
    """Check if rate is within plausible range."""
    return MWK_USD_MIN <= rate <= MWK_USD_MAX


def _get_last_rate_from_db() -> Optional[float]:
    """Get the most recent rate from database."""
    try:
        db = SessionLocal()
        try:
            result = db.query(ExchangeRate).order_by(
                ExchangeRate.date.desc()
            ).first()
            return result.rate if result else None
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Failed to get last rate from DB: {e}")
        return None


def _validate_rate_change(new_rate: float, last_rate: Optional[float]) -> bool:
    """
    Validate that rate change is not too extreme.

    Args:
        new_rate: New rate value
        last_rate: Previous rate value

    Returns:
        True if change is reasonable
    """
    if last_rate is None:
        return True

    pct_change = abs((new_rate - last_rate) / last_rate) * 100
    if pct_change > MAX_DAILY_CHANGE_PCT:
        logger.warning(
            f"Rate change {pct_change:.1f}% exceeds {MAX_DAILY_CHANGE_PCT}% threshold "
            f"({last_rate:.2f} → {new_rate:.2f})"
        )
        return False

    return True


def _update_cache(rate: float, source: str):
    """Update the rate cache."""
    _cache["rate"] = rate
    _cache["timestamp"] = datetime.now()
    _cache["source"] = source


def _get_from_cache() -> Optional[Dict[str, Any]]:
    """Get cached rate if still valid."""
    if _cache["timestamp"] is None:
        return None

    age = (datetime.now() - _cache["timestamp"]).total_seconds()
    if age < CACHE_TTL:
        return {
            "rate": _cache["rate"],
            "source": _cache["source"],
            "cached": True,
            "age_seconds": age
        }

    return None


# ============================================================
# Historical bulk fetchers
# ============================================================

def fetch_real_rates_exchangerate_host(
    days: int = 365 * 3
) -> Optional[pd.DataFrame]:
    """
    Fetch historical rates from exchangerate.host API.

    Args:
        days: Number of days of history to fetch

    Returns:
        DataFrame with historical rates
    """
    try:
        logger.info("🌍 Fetching MWK/USD from exchangerate.host...")

        end_date = datetime.today().strftime("%Y-%m-%d")
        start_date = (datetime.today() - timedelta(days=days)).strftime("%Y-%m-%d")

        url = (
            f"https://api.exchangerate.host/timeseries"
            f"?start_date={start_date}&end_date={end_date}"
            f"&base=USD&symbols=MWK"
        )

        response = requests.get(url, timeout=15)
        data = response.json()

        if not data.get("rates"):
            raise ValueError("No rates in response")

        rows = []
        for date_str, values in data["rates"].items():
            if "MWK" in values:
                rate = values["MWK"]
                if _is_plausible(rate):
                    rows.append({
                        "date": pd.to_datetime(date_str),
                        "rate": rate
                    })

        if not rows:
            raise ValueError("No plausible rates found")

        df = pd.DataFrame(rows)
        df.sort_values("date", inplace=True)
        df.reset_index(drop=True, inplace=True)

        logger.info(f"✅ exchangerate.host: {len(df)} rows")
        return df

    except Exception as e:
        logger.warning(f"⚠️ exchangerate.host failed: {e}")
        return None


def fetch_real_rates_open_er_api() -> Optional[pd.DataFrame]:
    """
    Fetch current rate from open.er-api.com.

    Returns:
        DataFrame with single rate
    """
    try:
        logger.info("🔁 Fetching from open.er-api.com...")

        response = requests.get("https://open.er-api.com/v6/latest/USD", timeout=10)
        data = response.json()

        if data.get("result") != "success":
            raise ValueError("API failure")

        rate = data["rates"].get("MWK")

        if not rate or not _is_plausible(rate):
            raise ValueError(f"MWK rate implausible or missing: {rate}")

        df = pd.DataFrame({
            "date": [pd.Timestamp.today().normalize()],
            "rate": [rate]
        })

        logger.info(f"✅ open.er-api: {rate:.2f}")
        return df

    except Exception as e:
        logger.warning(f"⚠️ open.er-api failed: {e}")
        return None


def fetch_historical_rates(
    days: int = 365 * 3
) -> Optional[pd.DataFrame]:
    """
    Fetch historical rates from primary source with fallback.

    Args:
        days: Number of days of history

    Returns:
        DataFrame with historical rates
    """
    # Try primary source
    df = fetch_real_rates_exchangerate_host(days)

    if df is not None and not df.empty:
        return df

    # Fallback to open.er-api (single day only)
    df = fetch_real_rates_open_er_api()

    return df


def fetch_latest_data() -> Optional[pd.DataFrame]:
    """
    Fetch latest exchange rate data from primary source with fallback.

    Returns:
        DataFrame with latest rate(s)
    """
    # Try primary source
    df = fetch_real_rates_exchangerate_host(days=7)  # Last 7 days

    if df is not None and not df.empty:
        return df

    # Fallback to open.er-api
    df = fetch_real_rates_open_er_api()

    if df is not None and not df.empty:
        return df

    logger.error("❌ All exchange rate sources failed.")
    return None


# ============================================================
# Live single-rate fetcher
# ============================================================

def fetch_current_rate(use_cache: bool = True) -> Optional[Dict[str, Any]]:
    """
    Fetch current MWK/USD mid-market rate.

    Priority:
    1. Cache (if still valid)
    2. Frankfurter.app (ECB-backed, reliable)
    3. Open.er-api.com (free tier, decent)
    4. ExchangeRate-API (public endpoint)

    Args:
        use_cache: Whether to use cached value

    Returns:
        Dictionary with rate, date, source, and metadata
    """
    # Check cache first
    if use_cache:
        cached = _get_from_cache()
        if cached:
            logger.info(f"✅ Using cached rate: {cached['rate']:.2f} (source: {cached['source']})")
            return cached

    today = datetime.today().strftime("%Y-%m-%d")
    last_rate = _get_last_rate_from_db()

    # ============================================================
    # 1. Frankfurter (most reliable)
    # ============================================================
    try:
        response = requests.get(
            "https://api.frankfurter.app/latest?from=USD&to=MWK",
            timeout=8
        )
        data = response.json()
        rate = data.get("rates", {}).get("MWK")

        if rate and _is_plausible(rate) and _validate_rate_change(rate, last_rate):
            logger.info(f"✅ Live rate from frankfurter.app: {rate:.2f}")
            result = {"date": today, "rate": float(rate), "source": "frankfurter"}
            _update_cache(rate, "frankfurter")
            return result
        else:
            logger.warning(f"⚠️ frankfurter MWK rate invalid: {rate}")

    except Exception as e:
        logger.warning(f"⚠️ frankfurter.app failed: {e}")

    # ============================================================
    # 2. open.er-api.com
    # ============================================================
    try:
        response = requests.get("https://open.er-api.com/v6/latest/USD", timeout=10)
        data = response.json()

        if data.get("result") == "success":
            rate = data["rates"].get("MWK")
            if rate and _is_plausible(rate) and _validate_rate_change(rate, last_rate):
                logger.info(f"✅ Live rate from open.er-api: {rate:.2f}")
                result = {"date": today, "rate": float(rate), "source": "open.er-api"}
                _update_cache(rate, "open.er-api")
                return result
            else:
                logger.warning(f"⚠️ open.er-api MWK rate invalid: {rate}")

    except Exception as e:
        logger.warning(f"⚠️ open.er-api failed: {e}")

    # ============================================================
    # 3. ExchangeRate-API (fallback)
    # ============================================================
    try:
        response = requests.get(
            "https://api.exchangerate-api.com/v4/latest/USD",
            timeout=8
        )
        data = response.json()
        rate = data.get("rates", {}).get("MWK")

        if rate and _is_plausible(rate) and _validate_rate_change(rate, last_rate):
            logger.info(f"✅ Live rate from exchangerate-api.com: {rate:.2f}")
            result = {"date": today, "rate": float(rate), "source": "exchangerate-api"}
            _update_cache(rate, "exchangerate-api")
            return result
        else:
            logger.warning(f"⚠️ exchangerate-api MWK rate invalid: {rate}")

    except Exception as e:
        logger.warning(f"⚠️ exchangerate-api.com failed: {e}")

    # ============================================================
    # 4. Return last known rate if available
    # ============================================================
    if last_rate is not None:
        logger.info(f"⚠️ Using last known rate from DB: {last_rate:.2f}")
        return {
            "date": today,
            "rate": float(last_rate),
            "source": "database_fallback",
            "stale": True
        }

    logger.error("❌ All live rate sources failed, and no fallback available")
    return None


def fetch_rate_history(
    days: int = 30
) -> Optional[pd.DataFrame]:
    """
    Fetch historical rates for display.

    Args:
        days: Number of days of history

    Returns:
        DataFrame with historical rates
    """
    df = fetch_latest_data()

    if df is None or df.empty:
        # Try to get from database
        db = SessionLocal()
        try:
            cutoff = datetime.now() - timedelta(days=days)
            results = db.query(ExchangeRate).filter(
                ExchangeRate.date >= cutoff
            ).order_by(ExchangeRate.date.asc()).all()

            if results:
                df = pd.DataFrame([{
                    "date": r.date,
                    "rate": r.rate
                } for r in results])
                df['date'] = pd.to_datetime(df['date'])
        finally:
            db.close()

    if df is not None and not df.empty:
        df.sort_values('date', inplace=True)
        df.reset_index(drop=True, inplace=True)

    return df