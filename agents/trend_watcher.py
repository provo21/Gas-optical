import os
import time
import json
import httpx
from datetime import datetime, timezone

RPC = os.environ.get("BASE_RPC", "https://mainnet.base.org")
INTERVAL = int(os.environ.get("TREND_INTERVAL", "600"))  # 10 min

def block_base_fee():
    payload = {"jsonrpc": "2.0", "id": 1, "method": "eth_getBlockByNumber", "params": ["latest", False]}
    with httpx.Client(timeout=15) as c:
        r = c.post(RPC, json=payload)
        r.raise_for_status()
        b = r.json()["result"]
    base = int(b.get("baseFeePerGas", "0x0"), 16) / 1e9
    return base

if __name__ == "__main__":
    prev = None
    while True:
        try:
            cur = block_base_fee()
            direction = "flat"
            if prev is not None:
                if cur > prev * 1.05:
                    direction = "rising"
                elif cur < prev * 0.95:
                    direction = "falling"
            out = {"ts": datetime.now(timezone.utc).isoformat(), "base_fee_gwei": round(cur, 4), "direction": direction, "prev": prev}
            print(json.dumps(out), flush=True)
            prev = cur
        except Exception as e:
            print(json.dumps({"error": str(e)[:160]}), flush=True)
        time.sleep(INTERVAL)
