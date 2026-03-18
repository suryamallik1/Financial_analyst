import httpx
import logging
from typing import List, Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)

class SearchClient:
    """
    Search client using Serper.dev or similar API to find current market candidates.
    """
    def __init__(self):
        self.api_key = getattr(settings, "SERPER_API_KEY", None)
        self.enabled = self.api_key is not None

    async def search_candidates(self, query: str) -> List[Dict[str, Any]]:
        """
        Executes a web search to find relevant tickers and recent context.
        """
        if not self.enabled:
            logger.warning("SERPER_API_KEY not found. Search is disabled.")
            return []

        url = "https://google.serper.dev/search"
        headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json"
        }
        payload = {"q": f"investment ideas and ticker symbols for: {query}"}
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                return data.get("organic", [])
            except Exception as e:
                logger.error(f"Search failed: {e}")
                return []
