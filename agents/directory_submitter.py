import os
import time
import json
import httpx

BASE_URL = os.environ.get("PUBLIC_URL", "https://gas-optical-production-30aa.up.railway.app")

DIRECTORIES = [
    "https://www.x402scan.com/resources/register",
    "https://x402-list.com/submit",
    "https://x402.new/submit",
]

ENDPOINTS = [f"{BASE_URL}/gas", f"{BASE_URL}/eth-price", f"{BASE_URL}/block-number"]


def log(msg):
    print(json.dumps({"ts": int(time.time()), "agent": "directory_submitter", "msg": msg}), flush=True)


async def submit_once():
    payload = {"url": BASE_URL, "endpoints": ENDPOINTS, "price": "0.0001", "network": "base"}
    async with httpx.AsyncClient(timeout=20.0) as client:
        for d in DIRECTORIES:
            try:
                r = await client.post(d, json=payload)
                log({"dir": d, "status": r.status_code})
            except Exception as e:
                log({"dir": d, "error": str(e)})


async def main():
    log("starting directory submitter")
    while True:
        try:
            await submit_once()
        except Exception as e:
            log({"error": str(e)})
        time.sleep(21600)  # every 6 hours


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
