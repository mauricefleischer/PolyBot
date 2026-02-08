
import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from app.services.polymarket import gamma_client

async def check_slugs_detailed():
    print("Fetching markets...")
    markets = await gamma_client.fetch_markets(limit=5, active=True)
    
    for m in markets:
        print(f"Question: {m.get('question')}")
        # Print all keys with 'slug' or 'event'
        slug_keys = [k for k in m.keys() if 'slug' in k.lower() or 'event' in k.lower()]
        for k in slug_keys:
            print(f"  {k}: {m[k]}")
        print("-" * 20)

if __name__ == "__main__":
    asyncio.run(check_slugs_detailed())
