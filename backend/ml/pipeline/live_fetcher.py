import pandas as pd
import requests
from datetime import datetime, timedelta
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from core.logging_config import get_logger

logger = get_logger(__name__)


def fetch_real_rates_exchangerate_host() -> pd.DataFrame:
    try:
        logger.info("🌍 Fetching MWK/USD from exchangerate.host...")

        end_date = datetime.today().strftime("%Y-%m-%d")
        start_date = (datetime.today() - timedelta(days=365 * 3)).strftime("%Y-%m-%d")

        url = (
            f"https://api.exchangerate.host/timeseries"
            f"?start_date={start_date}"
            f"&end_date={end_date}"
            f"&base=USD&symbols=MWK"
        )

        r = requests.get(url, timeout=15)

        if r.status_code != 200:
            raise ValueError(f"HTTP {r.status_code}")

        data = r.json()

        if not data.get("rates"):
            raise ValueError("No rates in response")

        rows = []
        for d, val in data["rates"].items():
            if "MWK" in val:
                rows.append({
                    "date": pd.to_datetime(d),
                    "rate": val["MWK"]
                })

        df = pd.DataFrame(rows)

        if df.empty:
            raise ValueError("Empty dataframe")

        df.sort_values("date", inplace=True)
        df.reset_index(drop=True, inplace=True)

        logger.info(f"✅ exchangerate.host: {len(df)} rows")
        return df

    except Exception as e:
        logger.warning(f"⚠️ exchangerate.host failed: {e}")
        return None


def fetch_real_rates_open_er_api() -> pd.DataFrame:
    """
    Fallback: reliable free API (latest only)
    """
    try:
        logger.info("🔁 Fallback: open.er-api.com...")

        url = "https://open.er-api.com/v6/latest/USD"
        r = requests.get(url, timeout=10)
        data = r.json()

        if data.get("result") != "success":
            raise ValueError("API failure")

        rate = data["rates"].get("MWK")
        if not rate:
            raise ValueError("MWK not found")

        df = pd.DataFrame({
            "date": [pd.Timestamp.today().normalize()],
            "rate": [rate]
        })

        logger.info(f"✅ open.er-api: {rate}")
        return df

    except Exception as e:
        logger.warning(f"⚠️ open.er-api failed: {e}")
        return None


def fetch_latest_data() -> pd.DataFrame:
    """
    MASTER FETCH FUNCTION
    """

    # 1. Try historical API
    df = fetch_real_rates_exchangerate_host()
    if df is not None and not df.empty:
        return df

    # 2. Fallback latest only
    df = fetch_real_rates_open_er_api()
    if df is not None and not df.empty:
        return df

    # 3. Fail gracefully
    raise ValueError("❌ All exchange rate sources failed.")


# ── NEW: Lightweight live fetcher for the /rates/latest endpoint ──
def fetch_current_rate() -> dict | None:
    """
    Fetch only today's MWK/USD rate from fast, free APIs.
    Returns {"date": "YYYY-MM-DD", "rate": float} or None if all fail.
    """
    # Primary: open.er-api (no API key, extremely fast)
    try:
        r = requests.get("https://open.er-api.com/v6/latest/USD", timeout=10)
        data = r.json()
        if data.get("result") == "success" and "MWK" in data["rates"]:
            rate = data["rates"]["MWK"]
            logger.info(f"✅ Live rate from open.er-api: {rate}")
            return {"date": datetime.today().strftime("%Y-%m-%d"), "rate": rate}
    except Exception as e:
        logger.warning(f"⚠️ open.er-api failed: {e}")

    # Fallback: exchangerate.host latest endpoint
    try:
        r = requests.get("https://api.exchangerate.host/latest?base=USD&symbols=MWK", timeout=10)
        data = r.json()
        if data.get("success") and "MWK" in data["rates"]:
            rate = data["rates"]["MWK"]
            logger.info(f"✅ Live rate from exchangerate.host: {rate}")
            return {"date": datetime.today().strftime("%Y-%m-%d"), "rate": rate}
    except Exception as e:
        logger.warning(f"⚠️ exchangerate.host latest failed: {e}")

    logger.error("❌ All live rate sources failed")
    return None