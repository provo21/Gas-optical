import os
import time
import json
import httpx
from datetime import datetime, timezone

INTERVAL = int(os.environ.get("BROAD_INTERVAL", "1800"))  # 30 min

def broadcast():
    signal = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "type": "gas_opportunity",
        "message": "Base gas trending; check /gas-predict for forecast",
        "endpoint": "https://gas-optical-production-30aa.up.railway.app/gas-predict",
        "price_usd": 0.005,
    }
    print(json.dumps(signal), flush=True)

if __name__ == "__main__":
    while True:
        broadcast()
        time.sleep(INTERVAL)
