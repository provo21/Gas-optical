import os
import time
import json
import httpx

BASE_URL = os.environ.get("PUBLIC_URL", "https://gas-optical-production-30aa.up.railway.app")
ENDPOINTS = ["/gas", "/eth-price", "/block-number", "/.well-known/x402"]


def log(msg):
    print(json.dumps({"ts": int(time.time()), "agent": "health_reporter", "msg": msg}), flush=True)


async def check_once():
    status = {}
    async with httpx.AsyncClient(timeout=10.0) as client:
        for ep in ENDPOINTS:
            try:
                r = await client.get(f"{BASE_URL}{ep}")
                status[ep] = r.status_code
            except Exception as e:
                status[ep] = f"err:{e}"
    log({"health": status})


async def main():
    log("starting health reporter")
    while True:
        try:
            await check_once()
        except Exception as e:
            log({"error": str(e)})
        time.sleep(300)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
