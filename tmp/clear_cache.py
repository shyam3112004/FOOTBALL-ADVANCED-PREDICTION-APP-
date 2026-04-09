import asyncio
from backend.cache import cache_manager

async def main():
    print("Clearing cache...")
    await cache_manager.clear()
    print("Cache cleared.")

if __name__ == "__main__":
    asyncio.run(main())
