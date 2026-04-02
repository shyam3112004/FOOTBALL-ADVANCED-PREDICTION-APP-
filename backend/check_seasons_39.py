import os
import httpx
import asyncio
from dotenv import load_dotenv

load_dotenv()

async def check_league(league_id):
    api_key = os.getenv("API_FOOTBALL_KEY")
    base_url = "https://v3.football.api-sports.io"
    headers = {"x-apisports-key": api_key}
    
    async with httpx.AsyncClient(headers=headers) as client:
        resp = await client.get(f"{base_url}/leagues", params={"id": league_id})
        data = resp.json()
        print(f"Seasons for {league_id}:")
        for s in data["response"][0]["seasons"]:
            print(f"Year: {s['year']} - Current: {s['current']}")

if __name__ == "__main__":
    asyncio.run(check_league(39))
