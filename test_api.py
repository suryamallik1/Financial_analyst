import httpx
import asyncio
import json

async def test_api():
    async with httpx.AsyncClient() as client:
        print("Testing /health ...")
        res = await client.get('http://127.0.0.1:8000/health')
        print(res.json())
        
        print("\nTesting /api/v1/analyze (Streaming) ...")
        payload = {"user_request": "I need a balanced portfolio for the next 2 years"}
        async with client.stream('POST', 'http://127.0.0.1:8000/api/v1/analyze', json=payload, timeout=150.0) as response:
            print(f"Status: {response.status_code}")
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    event_type = data.get("type")
                    if event_type == "agent_start":
                        print(f"  [Agent] {data.get('agent')} started Thinking...")
                    elif event_type == "tool_start":
                        print(f"  [Tool] {data.get('tool')} with input: {data.get('input')}")
                    elif event_type == "final_result":
                        print("\nFinal Analysis Result:")
                        print(json.dumps(data, indent=2))
                    elif event_type == "error":
                        print(f"\nError: {data.get('detail')}")

if __name__ == "__main__":
    asyncio.run(test_api())
