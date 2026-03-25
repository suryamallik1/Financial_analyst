import httpx
import logging
from typing import Dict, Any, List
from app.core.config import settings
from app.core.cache import CacheClient
from app.core.resilience import rate_limit, retry_http_request

logger = logging.getLogger(__name__)

class FundamentalsClient:
    """
    Fundamentals data ingestion using Financial Modeling Prep (FMP) 
    and SEC EDGAR REST API with aggressive Redis caching.
    """
    def __init__(self):
        self.fmp_api_key = getattr(settings, "FMP_API_KEY", "")
        self.user_agent = "QuantPlatform contact@example.com"
        self.cache = CacheClient()

    @rate_limit("fmp", requests_per_minute=250)
    @retry_http_request()
    async def get_key_metrics(self, symbol: str) -> Dict[str, Any]:
        """Fetches structured ratios (PE, PB, ROE) from FMP."""
        if not self.fmp_api_key:
            return {}
            
        cache_key = f"fmp_metrics_{symbol}"
        cached_data = await self.cache.get_cached_response("fmp", cache_key)
        if cached_data:
            return cached_data

        url = f"https://financialmodelingprep.com/api/v3/key-metrics/{symbol}?period=annual&apikey={self.fmp_api_key}"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                if data:
                    metric_data = data[0]
                    await self.cache.set_cached_response("fmp", cache_key, metric_data)
                    return metric_data
            except Exception as e:
                logger.error(f"FMP metrics failed for {symbol}: {e}")
        return {}

    @rate_limit("sec_edgar", requests_per_minute=10)
    @retry_http_request()
    async def get_sec_filings_metadata(self, cik: str) -> List[Dict[str, Any]]:
        """
        Fetches metadata for recent SEC filings using the official SEC REST JSON API.
        Input `cik` must be 10 digits padded with zeros.
        """
        cache_key = f"sec_filings_{cik}"
        cached_data = await self.cache.get_cached_response("sec", cache_key)
        if cached_data:
            return cached_data

        headers = {
            "User-Agent": self.user_agent,
            "Accept-Encoding": "gzip, deflate"
        }
        
        url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        
        async with httpx.AsyncClient(headers=headers) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                
                # Extract recent filings
                filings = data.get("filings", {}).get("recent", {})
                if filings:
                    await self.cache.set_cached_response("sec", cache_key, filings)
                    return filings
            except Exception as e:
                logger.error(f"SEC metadata failed for {cik}: {e}")
        return []
