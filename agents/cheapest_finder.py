import os
import time
import json
import httpx
from datetime import datetime, timezone

INTERVAL = int(os.environ.get("CHEAP_INTERVAL", "3600"))  # hourly

CANDIDATES = [
    "https://gas-optical-production-30aa.up.railway.app/gas",
    "https://api.gasfeepredictor.com/api/l2-gas",
    "https://www.dwellir.com/gas-tracker/base",
]

def probe(url):
    try:
        with httpx.Client(timeout=15, follow_redirects=True) as c:
            r = c.get(url, headers={"User-Agent": "GasOpticalBot/1.0"})
        price = None
        if r.status_code == 402:
            price = 0.001
        elif r.status_code == 200:
            try:
                data = r.json()
                price = data.get("gas_gwei") or data.get("price")
            except Exception:
                price = None
        return {"url": url, "status": r.status_code, "price": price}
    except Exception as e:
        return {"url": url, "error": str(e)[:120]}

def rank(results):
    paid = [x for x in results if x.get("price") is not None]
    paid.sort(key=lambda x: x["price"])
    return paid[:3]

if __name__ == "__main__":
    while True:
        results = [probe(u) for u in CANDIDATES]
        top = rank(results)
        print(json.dumps({"ts": datetime.now(timezone.utc).isoformat(), "top_cheapest": top}), flush=True)
        time.sleep(INTERVAL)
