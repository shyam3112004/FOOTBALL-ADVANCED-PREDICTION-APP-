import os
import httpx
import asyncio
from dotenv import load_dotenv

load_dotenv()

async def check_seasons(league_id):
    api_key = os.getenv("API_FOOTBALL_KEY")
    base_url = "https://v3.football.api-sports.io"
    headers = {"x-apisports-key": api_key}
    
    async with httpx.AsyncClient(headers=headers) as client:
        # Check league info and seasons
        resp = await client.get(f"{base_url}/leagues", params={"id": league_id})
        data = resp.json()
        print(f"League Info for {league_id}:")
        if data.get("response"):
            leagues = data["response"]
            for item in leagues:
                l = item["league"]
                seasons = item["seasons"]
                print(f"Name: {l['name']}")
                for s in seasons:
                    if s["current"]:
                        print(f"Current Season: {s['year']}")
        else:
            print("No response from API")

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

if __name__ == "__main__":
    asyncio.run(check_seasons(128))
    asyncio.run(check_fixtures(128, 2026))
    asyncio.run(check_fixtures(128, 2025))
