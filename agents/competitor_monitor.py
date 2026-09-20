import os
import time
import json
import httpx

BASE_URL = os.environ.get("PUBLIC_URL", "https://gas-optical-production-30aa.up.railway.app")
COMPETITOR_QUERIES = ["gas oracle", "eth price api", "base gas"]


def log(msg):
    print(json.dumps({"ts": int(time.time()), "agent": "competitor_monitor", "msg": msg}), flush=True)


async def monitor_once():
    found = []
    async with httpx.AsyncClient(timeout=15.0) as client:
        for q in COMPETITOR_QUERIES:
            try:
                r = await client.get("https://www.x402scan.com/api/search", params={"q": q})
                if r.status_code == 200:
                    data = r.json()
                    found.append({"q": q, "count": len(data) if isinstance(data, list) else "n/a"})
            except Exception as e:
                found.append({"q": q, "error": str(e)})
    log({"competitors": found})


async def main():
    log("starting competitor monitor")
    while True:
        try:
            await monitor_once()
        except Exception as e:
            log({"error": str(e)})
        time.sleep(14400)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
