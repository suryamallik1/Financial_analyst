import httpx
import pandas as pd
from typing import Optional, Dict, Any
from datetime import datetime
from app.core.config import settings
from app.core.cache import CacheClient
from app.core.resilience import rate_limit, retry_http_request

class MarketDataClient:
    def __init__(self):
        self.alpha_vantage_key = settings.ALPHA_VANTAGE_API_KEY
        self.polygon_key = settings.POLYGON_API_KEY
        self.cache = CacheClient()
    
    @rate_limit("polygon", requests_per_minute=5)
    @retry_http_request()
    async def get_historical_ohlcv(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        cache_key = f"{symbol}_{start_date}_{end_date}_ohlcv"
        cached_data = await self.cache.get_cached_response("polygon", cache_key)
        if cached_data:
            df = pd.DataFrame(cached_data)
            df['Timestamp'] = pd.to_datetime(df['Timestamp'])
            df.set_index('Timestamp', inplace=True)
            return df

        # Placeholder for actual API call, defaulting to Polygon as example
        url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/{start_date}/{end_date}"
        params = {"apiKey": self.polygon_key}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if 'results' not in data:
                return pd.DataFrame()
                
            df = pd.DataFrame(data['results'])
            
            # Prepare for cache: Convert Timestamp to string or ISO for JSON
            cache_friendly_results = results.copy()
            for r in cache_friendly_results:
                r['Timestamp'] = datetime.fromtimestamp(r['t']/1000).isoformat()
            
            await self.cache.set_cached_response("polygon", cache_key, cache_friendly_results)

            # Return original DF format
            df = pd.DataFrame(results)
            df['Timestamp'] = pd.to_datetime(df['t'], unit='ms')
            df.set_index('Timestamp', inplace=True)
            df.rename(columns={'c': 'Close', 'o': 'Open', 'h': 'High', 'l': 'Low', 'v': 'Volume'}, inplace=True)
            return df

    @rate_limit("alpha_vantage", requests_per_minute=5)
    @retry_http_request()
    async def get_alpha_vantage_sentiment(self, ticker: str) -> Dict[str, Any]:
        """Fetches sentiment data from Alpha Vantage with caching."""
        cache_key = f"{ticker}_sentiment"
        cached_data = await self.cache.get_cached_response("alpha_vantage", cache_key)
        if cached_data:
            return cached_data

        url = f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={ticker}&apikey={self.alpha_vantage_key}"
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            await self.cache.set_cached_response("alpha_vantage", cache_key, data)
            return data

    @rate_limit("alpha_vantage", requests_per_minute=5)
    @retry_http_request()
    async def get_alpha_vantage_indicators(self, ticker: str, function: str = "RSI") -> Dict[str, Any]:
        """Fetches technical indicators from Alpha Vantage (e.g., RSI, EMA, SMA) with caching."""
        cache_key = f"{ticker}_{function}_indicator"
        cached_data = await self.cache.get_cached_response("alpha_vantage", cache_key)
        if cached_data:
            return cached_data

        url = f"https://www.alphavantage.co/query?function={function}&symbol={ticker}&interval=daily&time_period=14&series_type=close&apikey={self.alpha_vantage_key}"
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            await self.cache.set_cached_response("alpha_vantage", cache_key, data)
            return data
