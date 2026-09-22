import os
import time
import json
import httpx

BASE_URL = os.environ.get("PUBLIC_URL", "https://gas-optical-production-30aa.up.railway.app")
LOG_DIR = os.environ.get("ORACLE_LOG_DIR", "/tmp/oracle_logs")

DIRECTORIES = [
    "https://www.x402scan.com/resources/register",
    "https://x402-list.com/submit",
    "https://x402.new/submit",
]

ENDPOINTS = [
    f"{BASE_URL}/gas",
    f"{BASE_URL}/eth-price",
    f"{BASE_URL}/block-number",
    f"{BASE_URL}/gas-predict",
    f"{BASE_URL}/whale-watch",
]


def log(msg):
    print(json.dumps({"ts": int(time.time()), "agent": "directory_submitter", "msg": msg}), flush=True)
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(os.path.join(LOG_DIR, "directory_submitter.json"), "w") as f:
            json.dump({"ts": int(time.time()), "status": "ok", "data": msg}, f)
    except Exception:
        pass


async def submit_once():
    payload = {
        "url": BASE_URL,
        "endpoints": ENDPOINTS,
        "price": "0.0001",
        "network": "base",
        "description": "Live Base gas price in gwei, updated from public RPC. Multi-chain gas oracle for agents.",
    }
    results = {}
    async with httpx.AsyncClient(timeout=20.0) as client:
        for d in DIRECTORIES:
            try:
                r = await client.post(d, json=payload)
                results[d] = r.status_code
                log({"dir": d, "status": r.status_code})
            except Exception as e:
                results[d] = f"err:{e}"
                log({"dir": d, "error": str(e)[:120]})
    return results


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
