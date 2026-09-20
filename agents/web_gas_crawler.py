import os
import time
import json
import httpx
from datetime import datetime, timezone

BASE_URL = os.environ.get("BASE_URL", "https://gas-optical-production-30aa.up.railway.app")
INTERVAL = int(os.environ.get("WEB_CRAWL_INTERVAL", "1800"))  # 30 min

SOURCES = [
    "https://api.gasfeepredictor.com/api/gas-predictions?timeframe=24h",
    "https://api.gasfeepredictor.com/api/l2-gas",
    "https://www.dwellir.com/gas-tracker/base",
]

def crawl():
    report = {"ts": datetime.now(timezone.utc).isoformat(), "sources": []}
    with httpx.Client(timeout=20, follow_redirects=True) as c:
        for url in SOURCES:
            try:
                r = c.get(url, headers={"User-Agent": "GasOpticalBot/1.0"})
                report["sources"].append({"url": url, "status": r.status_code, "len": len(r.text)})
            except Exception as e:
                report["sources"].append({"url": url, "error": str(e)[:120]})
    print(json.dumps(report), flush=True)

if __name__ == "__main__":
    while True:
        crawl()
        time.sleep(INTERVAL)
