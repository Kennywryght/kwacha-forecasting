import pandas as pd
import numpy as np
import requests
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from core.logging_config import get_logger

logger = get_logger(__name__)


def fetch_real_rates_yfinance() -> pd.DataFrame:
    """
    Fetch real MWK/USD rates using yfinance.
    Ticker: MWK=X gives USD/MWK, we invert to get MWK/USD.
    """
    try:
        import yfinance as yf
        logger.info("Fetching real MWK/USD rates from Yahoo Finance...")
        ticker = yf.Ticker("MWK=X")
        df = ticker.history(start="2024-01-01", end="2026-04-20")
        if df.empty:
            logger.warning("yfinance returned empty data for MWK=X")
            return None
        df.reset_index(inplace=True)
        df.rename(columns={"Date": "date", "Close": "rate"}, inplace=True)
        df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
        df = df[["date", "rate"]].copy()
        df = df[df["rate"] > 0]
        df.sort_values("date", inplace=True)
        df.reset_index(drop=True, inplace=True)
        logger.info(f"Fetched {len(df)} real rows | "
                    f"{df['date'].min().date()} to {df['date'].max().date()}")
        logger.info(f"Latest real rate: {df['rate'].iloc[-1]:.2f} MWK")
        return df
    except Exception as e:
        logger.error(f"yfinance fetch failed: {e}")
        return None


def fetch_real_rates_exchangerate_api(api_key: str = "") -> pd.DataFrame:
    """
    Fallback: exchangerate-api.com free tier.
    Only gives current rate, not history.
    """
    try:
        url = f"https://open.er-api.com/v6/latest/USD"
        r = requests.get(url, timeout=10)
        data = r.json()
        if data.get("result") == "success":
            rate = data["rates"].get("MWK")
            if rate:
                today = pd.Timestamp.today().normalize()
                df = pd.DataFrame({"date": [today], "rate": [rate]})
                logger.info(f"Live rate from open.er-api.com: {rate:.2f} MWK")
                return df
    except Exception as e:
        logger.error(f"open.er-api fetch failed: {e}")
    return None