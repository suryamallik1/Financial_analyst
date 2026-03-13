import httpx
import re
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from app.core.config import settings
from app.core.cache import CacheClient
from app.core.resilience import rate_limit, retry_http_request

class FundamentalsClient:
    def __init__(self):
        self.news_api_key = settings.NEWS_API_KEY
        self.user_agent = "MultiAssetPlatform contact@example.com"
        self.cache = CacheClient()
        
    @rate_limit("news_api", requests_per_minute=20)
    @retry_http_request()
    async def get_news_sentiment(self, ticker: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Fetches real news articles related to the ticker with caching."""
        cache_key = f"{ticker}_news_{start_date}_{end_date}"
        cached_data = await self.cache.get_cached_response("news_api", cache_key)
        if cached_data:
            return cached_data

        url = "https://newsapi.org/v2/everything"
        params = {
            "q": ticker,
            "from": start_date,
            "to": end_date,
            "sortBy": "relevancy",
            "apiKey": self.news_api_key,
            "language": "en"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                articles = data.get('articles', [])
                await self.cache.set_cached_response("news_api", cache_key, articles)
                return articles
            except httpx.HTTPError as e:
                print(f"Error fetching news: {e}")
                return []
                
    @rate_limit("sec_edgar", requests_per_minute=10)
    @retry_http_request()
    async def get_sec_10k_summary(self, ticker: str) -> str:
        """Fetches and summarizes the latest 10-K from SEC EDGAR with caching."""
        cache_key = f"{ticker}_10k_summary"
        cached_data = await self.cache.get_cached_response("sec", cache_key)
        if cached_data:
            return cached_data

        headers = {
            "User-Agent": self.user_agent,
            "Accept-Encoding": "gzip, deflate",
            "Host": "www.sec.gov"
        }
        
        async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
            try:
                # 1. Search for 10-K
                search_url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={ticker}&type=10-K&owner=exclude&count=1"
                response = await client.get(search_url)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'lxml')
                doc_link = soup.find('a', id='documentsbutton')
                if not doc_link:
                    return f"No 10-K found for {ticker}."
                
                filing_detail_url = "https://www.sec.gov" + doc_link['href']
                
                # 2. Detail page
                detail_res = await client.get(filing_detail_url)
                detail_soup = BeautifulSoup(detail_res.text, 'lxml')
                table = detail_soup.find('table', summary='Document Format Files')
                if not table:
                    return f"Could not find filing table for {ticker}."
                
                htm_link = table.find('a', href=re.compile(r'\.htm$'))
                if not htm_link:
                    return f"Could not find .htm filing for {ticker}."
                
                ten_k_url = "https://www.sec.gov" + htm_link['href']
                
                # 3. Content
                content_res = await client.get(ten_k_url)
                body_text = content_res.text
                
                start_marker = re.search(r'Item 1\. Business', body_text, re.IGNORECASE)
                if start_marker:
                    start_idx = start_marker.start()
                    summary_raw = body_text[start_idx : start_idx + 8000]
                    clean_text = BeautifulSoup(summary_raw, "lxml").get_text(separator=' ')
                    summary = f"Latest 10-K Chunk for {ticker}:\n" + " ".join(clean_text.split())[:3000] + "..."
                    await self.cache.set_cached_response("sec", cache_key, summary)
                    return summary
                
                result = f"Fetched 10-K for {ticker} but could not find Item 1 segment."
                await self.cache.set_cached_response("sec", cache_key, result)
                return result
                
            except Exception as e:
                print(f"Error fetching SEC data: {e}")
                return f"Failed to fetch SEC 10-K for {ticker}."
