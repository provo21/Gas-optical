import asyncio
import json
import os
import time
from typing import Any, Dict, List

import httpx

BAZAAR_SEARCH = "https://api.cdp.coinbase.com/platform/v2/x402/discovery/search"
BAZAAR_LIST = "https://api.cdp.coinbase.com/platform/v2/x402/discovery/resources"

QUERIES = [
    "base gas price",
    "ethereum gas oracle",
    "live gas gwei",
    "eth price usd",
    "base block number",
    "chain state feed",
]

MY_ENDPOINTS = {
    "gas": "https://gas-optical-production-30aa.up.railway.app/gas",
    "eth-price": "https://gas-optical-production-30aa.up.railway.app/eth-price",
    "block-number": "https://gas-optical-production-30aa.up.railway.app/block-number",
}


async def search_bazaar(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    params = {"query": query, "network": "eip155:8453", "limit": limit}
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(BAZAAR_SEARCH, params=params)
        resp.raise_for_status()
        data = resp.json()
    return data.get("resources", [])


async def list_bazaar(limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    params = {"limit": limit, "offset": offset, "type": "http"}
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(BAZAAR_LIST, params=params)
        resp.raise_for_status()
        data = resp.json()
    return data.get("items", [])


def is_competitor(resource: Dict[str, Any]) -> bool:
    url = str(resource.get("resource", "")).lower()
    desc = str(resource.get("description", "")).lower()
    tags = [str(t).lower() for t in resource.get("tags", [])]
    keywords = ["gas", "gwei", "oracle", "eth price", "block number", "base chain"]
    hay = " ".join([url, desc] + tags)
    return any(k in hay for k in keywords) and MY_ENDPOINTS["gas"] not in url


async def run_once() -> Dict[str, Any]:
    seen = set()
    competitors: List[Dict[str, Any]] = []
    for q in QUERIES:
        try:
            results = await search_bazaar(q)
        except Exception as e:
            print(f"search failed for {q}: {e}")
            continue
        for r in results:
            url = r.get("resource")
            if not url or url in seen:
                continue
            seen.add(url)
            if is_competitor(r):
                competitors.append(
                    {
                        "query": q,
                        "resource": url,
                        "description": r.get("description"),
                        "price": r.get("accepts", [{}])[0].get("amount")
                        if r.get("accepts")
                        else None,
                        "tags": r.get("tags"),
                    }
                )
    report = {
        "timestamp": int(time.time()),
        "my_endpoints": MY_ENDPOINTS,
        "competitor_count": len(competitors),
        "competitors": competitors[:50],
    }
    print(json.dumps(report, indent=2)[:4000])
    return report


async def main():
    interval = int(os.environ.get("PROMOTER_INTERVAL", "3600"))
    while True:
        await run_once()
        await asyncio.sleep(interval)


if __name__ == "main":
    asyncio.run(main())
