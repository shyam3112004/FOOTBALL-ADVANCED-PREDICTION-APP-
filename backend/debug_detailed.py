import os
import httpx
import asyncio
from dotenv import load_dotenv

load_dotenv()

async def debug_fixtures(league_id, season):
    api_key = os.getenv("API_FOOTBALL_KEY")
    headers = {"x-apisports-key": api_key}
    
    async with httpx.AsyncClient(headers=headers) as client:
        resp = await client.get(f"https://v3.football.api-sports.io/fixtures", params={"league": league_id, "season": season})
        data = resp.json()
        print(f"Status Code: {resp.status_code}")
        print(f"Errors: {data.get('errors')}")
        print(f"Results: {data.get('results')}")
        if data.get('response'):
            print(f"Example Match: {data['response'][0]['teams']['home']['name']} vs {data['response'][0]['teams']['away']['name']}")

if __name__ == "__main__":
    asyncio.run(debug_fixtures(39, 2025))
