import os
import httpx
import asyncio
from dotenv import load_dotenv

load_dotenv()

async def check_fixtures(league_id, season):
    api_key = os.getenv("API_FOOTBALL_KEY")
    base_url = "https://v3.football.api-sports.io"
    headers = {"x-apisports-key": api_key}
    
    async with httpx.AsyncClient(headers=headers) as client:
        resp = await client.get(f"{base_url}/fixtures", params={"league": league_id, "season": season})
        data = resp.json()
        print(f"Fixtures for {league_id} in {season}:")
        count = len(data.get("response", []))
        print(f"Count: {count}")
        if count > 0:
            print(f"Example: {data['response'][0]['teams']['home']['name']} vs {data['response'][0]['teams']['away']['name']}")

if __name__ == "__main__":
    asyncio.run(check_fixtures(130, 2026))
    asyncio.run(check_fixtures(39, 2025)) # Premier League
