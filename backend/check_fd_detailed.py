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
        # Check both scheduled and finished to see if it works at all
        resp = await client.get(f"{base_url}/competitions/PL/matches", params={"status": "FINISHED"})
        data = resp.json()
        print(f"Status Code: {resp.status_code}")
        print(f"Finished matches count: {len(data.get('matches', []))}")
        if data.get('matches'):
            print(f"Latest: {data['matches'][-1]['homeTeam']['name']} vs {data['matches'][-1]['awayTeam']['name']}")

if __name__ == "__main__":
    asyncio.run(check_fd())
