import httpx
import logging
import pandas as pd
from typing import Dict, Any, List
from app.core.config import settings
from app.core.cache import CacheClient
from app.core.resilience import rate_limit, retry_http_request

logger = logging.getLogger(__name__)

class MacroDataClient:
    """
    Macro and Geopolitical ingestion using FRED and GDELT 
    with aggressive Redis caching.
    """
    def __init__(self):
        self.fred_api_key = getattr(settings, "FRED_API_KEY", "")
        self.cache = CacheClient()

    @rate_limit("fred", requests_per_minute=120)
    @retry_http_request()
    async def get_fred_series(self, series_id: str) -> List[Dict[str, Any]]:
        """Fetches FRED economic data (e.g., T10Y2Y for yield curve)."""
        if not self.fred_api_key:
            return []
            
        cache_key = f"fred_series_{series_id}"
        cached_data = await self.cache.get_cached_response("fred", cache_key)
        if cached_data:
            return cached_data

        url = f"https://api.stlouisfed.org/fred/series/observations"
        params = {
            "series_id": series_id,
            "api_key": self.fred_api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": 100 # Last 100 observations
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                observations = data.get("observations", [])
                
                await self.cache.set_cached_response("fred", cache_key, observations)
                return observations
            except Exception as e:
                logger.error(f"FRED fetch failed for {series_id}: {e}")
        return []

    @rate_limit("gdelt", requests_per_minute=20)
    @retry_http_request()
    async def get_gdelt_sentiment(self, query: str) -> Dict[str, Any]:
        """
        Queries the GDELT 2.0 Doc API to quantify geopolitical events 
        and sentiment for a given term.
        """
        cache_key = f"gdelt_{query}"
        cached_data = await self.cache.get_cached_response("gdelt", cache_key)
        if cached_data:
            return cached_data

        url = f"https://api.gdeltproject.org/api/v2/doc/doc"
        params = {
            "query": query,
            "mode": "timelinevolinfo",
            "format": "json"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                await self.cache.set_cached_response("gdelt", cache_key, data)
                return data
            except Exception as e:
                logger.error(f"GDELT fetch failed for {query}: {e}")
        return {}
