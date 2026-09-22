import os
import time
import json
import httpx
from datetime import datetime, timezone

BASE_URL = os.environ.get("BASE_URL", "https://gas-optical-production-30aa.up.railway.app")
INTERVAL = int(os.environ.get("WEB_CRAWL_INTERVAL", "1800"))  # 30 min
LOG_DIR = os.environ.get("ORACLE_LOG_DIR", "/tmp/oracle_logs")

SOURCES = [
    "https://api.gasfeepredictor.com/api/gas-predictions?timeframe=24h",
    "https://api.gasfeepredictor.com/api/l2-gas",
    "https://www.dwellir.com/gas-tracker/base",
    "https://gas.blocknative.com/check?chainid=8453",
]


def crawl():
    report = {"ts": datetime.now(timezone.utc).isoformat(), "sources": [], "status": "ok"}
    with httpx.Client(timeout=20, follow_redirects=True) as c:
        for url in SOURCES:
            try:
                r = c.get(url, headers={"User-Agent": "GasOpticalBot/1.0"})
                entry = {"url": url, "status": r.status_code, "len": len(r.text)}
                # Try to extract a useful gas number
                try:
                    data = r.json()
                    if isinstance(data, dict):
                        for k in ("gasPrice", "gas_price", "baseFee", "base_fee", "gwei"):
                            if k in data:
                                entry["value"] = data[k]
                                break
                except Exception:
                    pass
                report["sources"].append(entry)
            except Exception as e:
                report["sources"].append({"url": url, "error": str(e)[:120]})
                report["status"] = "partial"
    print(json.dumps(report), flush=True)
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(os.path.join(LOG_DIR, "web_gas_crawler.json"), "w") as f:
            json.dump(report, f)
    except Exception:
        pass


if __name__ == "__main__":
    while True:
        crawl()
        time.sleep(INTERVAL)
