import os
import time
import json
import httpx
from datetime import datetime, timezone

INTERVAL = int(os.environ.get("COMP_PRICE_INTERVAL", "7200"))  # 2h

RIVALS = [
    {"name": "gasfeepredictor", "url": "https://api.gasfeepredictor.com/api/l2-gas", "free": True},
    {"name": "dwellir", "url": "https://www.dwellir.com/gas-tracker/base", "free": True},
    {"name": "ours", "url": "https://gas-optical-production-30aa.up.railway.app/gas", "free": False, "price_usd": 0.001},
]

def assess():
    report = {"ts": datetime.now(timezone.utc).isoformat(), "rivals": []}
    for r in RIVALS:
        entry = {"name": r["name"], "free": r.get("free", False)}
        if not r.get("free"):
            entry["our_price_usd"] = r.get("price_usd")
        report["rivals"].append(entry)
    free_count = sum(1 for x in report["rivals"] if x["free"])
    report["suggestion"] = "lower_price" if free_count >= 2 else "hold"
    print(json.dumps(report), flush=True)

if __name__ == "__main__":
    while True:
        assess()
        time.sleep(INTERVAL)
