import asyncio
import os
from app.tools.search import SearchClient
from app.core.config import settings

async def debug_search():
    client = SearchClient()
    print(f"Serper API Key present: {client.api_key is not None}")
    if not client.api_key:
        print("Error: SERPER_API_KEY is missing in .env")
        return
        
    print("Testing search...")
    results = await client.search_candidates("best AI stocks March 2026")
    print(f"Found {len(results)} results.")
    for res in results[:3]:
        print(f"- {res.get('title')}")

if __name__ == "__main__":
    asyncio.run(debug_search())
