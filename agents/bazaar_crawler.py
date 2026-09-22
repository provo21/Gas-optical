import os
import time
import json
import httpx

BASE_URL = os.environ.get("PUBLIC_URL", "https://gas-optical-production-30aa.up.railway.app")
BAZAAR_SEARCH = os.environ.get(
    "BAZAAR_SEARCH_URL",
    "https://api.cdp.coinbase.com/platform/v2/x402/discovery/search",
)
BAZAAR_LIST = os.environ.get(
    "BAZAAR_LIST_URL",
    "https://api.cdp.coinbase.com/platform/v2/x402/discovery/resources",
)

QUERIES = ["base gas price", "ethereum gas oracle", "eth price feed", "base block number", "live gas gwei", "gas prediction"]

ENDPOINTS = {
    "gas": f"{BASE_URL}/gas",
    "eth-price": f"{BASE_URL}/eth-price",
    "block-number": f"{BASE_URL}/block-number",
    "gas-predict": f"{BASE_URL}/gas-predict",
    "whale-watch": f"{BASE_URL}/whale-watch",
}

LOG_DIR = os.environ.get("ORACLE_LOG_DIR", "/tmp/oracle_logs")


def log(msg):
    print(json.dumps({"ts": int(time.time()), "agent": "bazaar_crawler", "msg": msg}), flush=True)
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(os.path.join(LOG_DIR, "bazaar_crawler.json"), "w") as f:
            json.dump({"ts": int(time.time()), "status": "ok", "data": msg}, f)
    except Exception:
        pass


async def crawl_once():
    results = {}
    async with httpx.AsyncClient(timeout=20.0) as client:
        # List resources to see what's indexed
        try:
            r = await client.get(BAZAAR_LIST, params={"limit": 50, "offset": 0, "type": "http"})
            if r.status_code == 200:
                data = r.json()
                items = data.get("items", data.get("resources", []))
                results["listed"] = len(items)
                results["sample"] = [i.get("resource") for i in items[:5]]
            else:
                results["listed"] = {"status": r.status_code}
        except Exception as e:
            results["listed"] = {"error": str(e)[:120]}

        for q in QUERIES:
            try:
                r = await client.get(BAZAAR_SEARCH, params={"query": q, "network": "eip155:8453", "limit": 10})
                if r.status_code == 200:
                    data = r.json()
                    resources = data.get("resources", data.get("items", []))
                    results[q] = {
                        "count": len(resources),
                        "top": [res.get("resource") for res in resources[:3]],
                    }
                else:
                    results[q] = {"status": r.status_code, "note": "search endpoint not available or auth required"}
            except Exception as e:
                results[q] = {"error": str(e)[:120]}
    log(results)
    return results


async def main():
    log("starting bazaar crawler")
    while True:
        try:
            await crawl_once()
        except Exception as e:
            log({"error": str(e)[:200]})
        time.sleep(3600)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
