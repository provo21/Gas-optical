import os
import time
import json
import httpx

BASE_URL = os.environ.get("PUBLIC_URL", "https://gas-optical-production-30aa.up.railway.app")
BAZAAR_URL = "https://api.cdp.coinbase.com/x402/bazaar/search"  # placeholder; real endpoint may vary

QUERIES = ["base gas price", "ethereum gas oracle", "eth price feed", "base block number", "live gas gwei"]

ENDPOINTS = {
    "gas": f"{BASE_URL}/gas",
    "eth-price": f"{BASE_URL}/eth-price",
    "block-number": f"{BASE_URL}/block-number",
}


def log(msg):
    print(json.dumps({"ts": int(time.time()), "agent": "bazaar_crawler", "msg": msg}), flush=True)


async def crawl_once():
    results = {}
    async with httpx.AsyncClient(timeout=15.0) as client:
        for q in QUERIES:
            try:
                # Best-effort: many Bazaar deployments expose a search or list endpoint.
                r = await client.get(BAZAAR_URL, params={"q": q})
                if r.status_code == 200:
                    data = r.json()
                    results[q] = data
                else:
                    results[q] = {"status": r.status_code, "note": "search endpoint not available or auth required"}
            except Exception as e:
                results[q] = {"error": str(e)}
    log({"queries": QUERIES, "results_summary": {k: ("ok" if isinstance(v, dict) and v.get("status") != 401 else "err") for k, v in results.items()}})
    return results


async def main():
    log("starting bazaar crawler")
    while True:
        try:
            await crawl_once()
        except Exception as e:
            log({"error": str(e)})
        time.sleep(3600)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
