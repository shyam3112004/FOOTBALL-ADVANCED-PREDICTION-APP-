import os
import httpx
import asyncio
from dotenv import load_dotenv

load_dotenv()

async def find_argentina():
    api_key = os.getenv("API_FOOTBALL_KEY")
    base_url = "https://v3.football.api-sports.io"
    headers = {"x-apisports-key": api_key}
    
    async with httpx.AsyncClient(headers=headers) as client:
        resp = await client.get(f"{base_url}/leagues", params={"country": "Argentina"})
        data = resp.json()
        print("Argentine Leagues:")
        for item in data.get("response", []):
            l = item["league"]
            print(f"ID: {l['id']} - Name: {l['name']}")
            # Check current season
            current = next((s for s in item["seasons"] if s["current"]), None)
            if current:
                print(f"  Current Season: {current['year']}")

if __name__ == "__main__":
    asyncio.run(find_argentina())
