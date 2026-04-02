import os
import httpx
import asyncio
from dotenv import load_dotenv

load_dotenv()

async def check_fd():
    api_key = os.getenv("FOOTBALL_DATA_API_KEY")
    base_url = "https://api.football-data.org/v4"
    headers = {"X-Auth-Token": api_key}
    
    async with httpx.AsyncClient(headers=headers) as client:
        resp = await client.get(f"{base_url}/competitions/PL/matches", params={"status": "SCHEDULED"})
        data = resp.json()
        print(f"Status Code: {resp.status_code}")
        print(f"Count: {len(data.get('matches', []))}")

if __name__ == "__main__":
    asyncio.run(check_fd())
