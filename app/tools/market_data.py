import httpx
import yfinance as yf
import pandas as pd
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from app.core.config import settings
from app.core.cache import CacheClient
from app.core.resilience import rate_limit, retry_http_request

logger = logging.getLogger(__name__)

class MarketDataClient:
    """
    Quantitative Market Data ingestion using free-tier tools (yfinance, Tiingo) 
    with aggressive Redis caching.
    """
    def __init__(self):
        self.tiingo_api_key = getattr(settings, "TIINGO_API_KEY", "")
        self.cache = CacheClient()
        self.default_lookback_years = 5
    
    async def get_historical_ohlcv(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Fetches OHLCV data primarily from yfinance."""
        # yfinance caching at network level or custom
        cache_key = f"yfinance_ohlcv_{symbol}_{start_date}_{end_date}"
        cached_data = await self.cache.get_cached_response("market_data", cache_key)
        
        if cached_data:
            df = pd.DataFrame(cached_data)
            df['Date'] = pd.to_datetime(df['Date'])
            df.set_index('Date', inplace=True)
            return df
            
        logger.info(f"Fetching yfinance data for {symbol}")
        # yfinance is synchronous but fast, wrap in thread or run directly
        # For simplicity in this demo, running directly
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date)
            
            if not df.empty:
                # Clean up timezone to naive for standard processing
                df.index = df.index.tz_localize(None) 
                
                # Cache results
                cache_df = df.reset_index()
                cache_df['Date'] = cache_df['Date'].astype(str)
                await self.cache.set_cached_response(
                    "market_data", 
                    cache_key, 
                    cache_df.to_dict(orient="records")
                )
            return df
        except Exception as e:
            logger.error(f"yfinance failed for {symbol}: {e}")
            return pd.DataFrame()

    @rate_limit("tiingo", requests_per_minute=20)
    @retry_http_request()
    async def validate_eod_price(self, symbol: str, date: str) -> Optional[float]:
        """Cross-validate exact EOD pricing using Tiingo API."""
        if not self.tiingo_api_key:
            return None
            
        cache_key = f"tiingo_eod_{symbol}_{date}"
        cached = await self.cache.get_cached_response("tiingo", cache_key)
        if cached:
            return cached.get('adjClose')

        url = f"https://api.tiingo.com/tiingo/daily/{symbol}/prices"
        params = {
            "startDate": date,
            "endDate": date,
            "token": self.tiingo_api_key
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                if data:
                    await self.cache.set_cached_response("tiingo", cache_key, data[0])
                    return data[0].get('adjClose')
            except Exception as e:
                logger.error(f"Tiingo fetch failed for {symbol}: {e}")
        return None
