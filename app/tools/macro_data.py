import httpx
import pandas as pd
from typing import Optional, Dict, Any
from app.core.config import settings

class MacroDataClient:
    def __init__(self):
        self.fred_key = settings.FRED_API_KEY
        self.base_url = "https://api.stlouisfed.org/fred/series/observations"
        
    async def get_series(self, series_id: str, observation_start: str, observation_end: str) -> pd.DataFrame:
        params = {
            "series_id": series_id,
            "api_key": self.fred_key,
            "file_type": "json",
            "observation_start": observation_start,
            "observation_end": observation_end
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if 'observations' not in data:
                return pd.DataFrame()
                
            df = pd.DataFrame(data['observations'])
            df['date'] = pd.to_datetime(df['date'])
            # Filter out missing values indicated by '.'
            df = df[df['value'] != '.']
            df['value'] = df['value'].astype(float)
            df.set_index('date', inplace=True)
            df = df[['value']]
            df.rename(columns={'value': series_id}, inplace=True)
            
            return df
            
    async def get_yield_curve_inversion(self, start_date: str, end_date: str) -> pd.DataFrame:
        # Standard proxy: 10-Year Treasury Minus 2-Year Treasury
        t10y = await self.get_series("DGS10", start_date, end_date)
        t2y = await self.get_series("DGS2", start_date, end_date)
        
        if t10y.empty or t2y.empty:
            return pd.DataFrame()
            
        merged = t10y.join(t2y, how='inner')
        merged['inversion'] = merged['DGS10'] - merged['DGS2']
        return merged
