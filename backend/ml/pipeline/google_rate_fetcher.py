"""
Google Exchange Rate Fetcher
Scrapes the real-time MWK/USD rate from Google's currency widget.
"""

import requests
import re
from datetime import date, datetime
from typing import Optional, Dict, Any
from core.logging_config import get_logger

logger = get_logger(__name__)

# Google search URL for MWK to USD
GOOGLE_RATE_URL = "https://www.google.com/search?q=MWK+to+USD"
GOOGLE_RATE_URL_2 = "https://www.google.com/search?q=1+MWK+to+USD"


def _extract_rate_from_html(html: str) -> Optional[float]:
    """Extract exchange rate from Google's search result page."""
    
    # Pattern 1: Look for the currency converter widget
    # Google shows: "1 MWK = 0.00057 USD" or "1 USD = 1,733.87 MWK"
    
    # Try to find USD to MWK rate (1 USD = X MWK)
    patterns = [
        # Pattern: "1 USD = 1,733.87 MWK" or "1 United States Dollar = 1,733.87 Malawian Kwacha"
        r'1\s*(?:USD|United States Dollar)\s*=\s*([\d,]+\.?\d*)\s*(?:MWK|Malawian Kwacha)',
        # Pattern: In reverse - find MWK value when converting from USD
        r'([\d,]+\.?\d*)\s*(?:MWK|Malawian Kwacha)',
        # Pattern: From the currency converter input
        r'data-value="([\d.]+)"',
        # Pattern: Any number near MWK label
        r'(\d[\d,]*\.?\d*)\s*MWK',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, html, re.IGNORECASE)
        for match in matches:
            try:
                # Clean the number
                rate_str = match.replace(',', '')
                rate = float(rate_str)
                # MWK/USD should be between 1000 and 3000
                if 1000 < rate < 3000:
                    logger.info(f"Found rate: {rate} MWK/USD")
                    return rate
                # If rate is too small (like 0.00057), it's MWK per 1 USD in reverse
                # Convert: 1/0.00057 ≈ 1754
                if 0.0001 < rate < 0.01:
                    converted = 1.0 / rate
                    if 1000 < converted < 3000:
                        logger.info(f"Converted rate: {converted} MWK/USD")
                        return round(converted, 2)
            except (ValueError, ZeroDivisionError):
                continue
    
    return None


def fetch_google_rate() -> Optional[Dict[str, Any]]:
    """
    Fetch the current MWK/USD rate from Google search.
    
    Returns:
        Dict with 'rate' and 'date' keys, or None if failed
    """
    logger.info("🔍 Fetching MWK/USD rate from Google...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    # Try both URL formats
    urls = [GOOGLE_RATE_URL, GOOGLE_RATE_URL_2]
    
    for url in urls:
        try:
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                rate = _extract_rate_from_html(response.text)
                if rate:
                    logger.info(f"✅ Google rate: {rate} MWK/USD")
                    return {
                        "rate": rate,
                        "date": str(date.today()),
                        "source": "google_search"
                    }
                else:
                    logger.warning("Could not extract rate from Google page")
            elif response.status_code == 429:
                logger.warning("Google rate limited (429)")
            else:
                logger.warning(f"Google returned status {response.status_code}")
                
        except requests.RequestException as e:
            logger.warning(f"Google fetch failed: {e}")
    
    # Fallback: Try the Google Finance API
    try:
        fallback_url = "https://www.google.com/finance/quote/MWK-USD"
        response = requests.get(fallback_url, headers=headers, timeout=10)
        if response.status_code == 200:
            rate = _extract_rate_from_html(response.text)
            if rate:
                return {
                    "rate": rate,
                    "date": str(date.today()),
                    "source": "google_finance"
                }
    except Exception:
        pass
    
    logger.error("❌ All Google rate fetching methods failed")
    return None


# ── Cache ──────────────────────────────────────────────────────────────────────
_rate_cache = {
    "rate": None,
    "timestamp": None,
    "source": None,
}

CACHE_TTL_SECONDS = 3600  # 1 hour


def get_google_rate(force_refresh: bool = False) -> Optional[Dict[str, Any]]:
    """
    Get the Google exchange rate, with caching.
    
    Args:
        force_refresh: If True, bypass cache and fetch fresh rate
        
    Returns:
        Dict with 'rate', 'date', 'source' or None
    """
    now = datetime.utcnow()
    
    # Return cached rate if still valid
    if not force_refresh and _rate_cache["rate"] and _rate_cache["timestamp"]:
        age = (now - _rate_cache["timestamp"]).total_seconds()
        if age < CACHE_TTL_SECONDS:
            logger.info(f"📦 Using cached Google rate: {_rate_cache['rate']}")
            return {
                "rate": _rate_cache["rate"],
                "date": str(date.today()),
                "source": _rate_cache["source"] or "google_cached"
            }
    
    # Fetch fresh rate
    result = fetch_google_rate()
    
    if result:
        _rate_cache["rate"] = result["rate"]
        _rate_cache["timestamp"] = now
        _rate_cache["source"] = result.get("source", "google")
    
    return result