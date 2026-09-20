import os
import time
import json
import httpx
from datetime import datetime, timezone

RPC = os.environ.get("BASE_RPC", "https://mainnet.base.org")
INTERVAL = int(os.environ.get("SPEC_INTERVAL", "300"))  # 5 min

def sample():
    payload = {"jsonrpc": "2.0", "id": 1, "method": "eth_gasPrice", "params": []}
    with httpx.Client(timeout=15) as c:
        r = c.post(RPC, json=payload)
        r.raise_for_status()
        wei = int(r.json()["result"], 16)
    return wei / 1e9

def speculate(history):
    if len(history) < 3:
        return {"action": "hold", "reason": "insufficient samples"}
    recent = history[-3:]
    avg = sum(recent) / len(recent)
    last = recent[-1]
    if last < avg * 0.85:
        return {"action": "buy_now", "confidence": 0.7, "reason": "gas below recent average"}
    if last > avg * 1.15:
        return {"action": "wait", "confidence": 0.65, "reason": "gas above recent average, likely to drop"}
    return {"action": "neutral", "confidence": 0.5, "reason": "stable"}

if __name__ == "__main__":
    history = []
    while True:
        try:
            g = sample()
            history.append(g)
            history = history[-12:]
            out = {"ts": datetime.now(timezone.utc).isoformat(), "gas_gwei": round(g, 4), **speculate(history)}
            print(json.dumps(out), flush=True)
        except Exception as e:
            print(json.dumps({"error": str(e)[:160]}), flush=True)
        time.sleep(INTERVAL)
