import httpx
from typing import List, Dict, Any
from app.core.config import settings

class FundamentalsClient:
    def __init__(self):
        self.news_api_key = settings.NEWS_API_KEY
        
    async def get_news_sentiment(self, query: str, from_date: str, to_date: str) -> List[Dict[str, Any]]:
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": query,
            "from": from_date,
            "to": to_date,
            "sortBy": "relevancy",
            "apiKey": self.news_api_key,
            "language": "en"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                return data.get('articles', [])
            except httpx.HTTPError as e:
                print(f"Error fetching news: {e}")
                return []
                
    async def get_sec_10k_summary(self, ticker: str) -> str:
        # Placeholder for SEC EDGAR integration
        # In a real app, you'd use the SEC API (e.g. sec-api.io) or sec_edgar_downloader
        return f"Mock 10-K Summary for {ticker}: Strong balance sheet, increasing revenue YOY, investing in AI."
