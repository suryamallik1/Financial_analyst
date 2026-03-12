import httpx
import asyncio
import json

async def test_api():
    async with httpx.AsyncClient() as client:
        print("Testing /health ...")
        res = await client.get('http://127.0.0.1:8000/health')
        print(res.json())
        
        print("\nTesting /api/v1/analyze ...")
        payload = {"user_request": "I need a balanced portfolio for the next 2 years"}
        res = await client.post('http://127.0.0.1:8000/api/v1/analyze', json=payload, timeout=120.0)
        
        print(f"Status: {res.status_code}")
        print(json.dumps(res.json(), indent=2))

if __name__ == "__main__":
    asyncio.run(test_api())
