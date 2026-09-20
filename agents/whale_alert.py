import os
import time
import json
import httpx

RPC = os.environ.get("BASE_RPC_URL", "https://mainnet.base.org")
THRESHOLD_WEI = 1000 * 10**18  # 1000 ETH
SEEN = set()

def get_latest_block():
    payload = {"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1}
    r = httpx.post(RPC, json=payload, timeout=10)
    return int(r.json()["result"], 16)

def get_block(n):
    payload = {"jsonrpc": "2.0", "method": "eth_getBlockByNumber", "params": [hex(n), True], "id": 1}
    r = httpx.post(RPC, json=payload, timeout=15)
    return r.json().get("result")

def scan():
    try:
        latest = get_latest_block()
        block = get_block(latest)
        if not block:
            return
        for tx in block.get("transactions", []):
            if not isinstance(tx, dict):
                continue
            val = int(tx.get("value", "0x0"), 16)
            if val >= THRESHOLD_WEI:
                key = tx.get("hash")
                if key in SEEN:
                    continue
                SEEN.add(key)
                alert = {
                    "type": "whale_alert",
                    "chain": "base",
                    "block": latest,
                    "tx": key,
                    "from": tx.get("from"),
                    "to": tx.get("to"),
                    "value_eth": val / 10**18,
                    "ts": int(time.time()),
                }
                print(json.dumps(alert), flush=True)
                # TODO: push to Telegram/Discord webhook when configured
    except Exception as e:
        print(json.dumps({"error": str(e)}), flush=True)

if __name__ == "__main__":
    print(json.dumps({"agent": "whale_alert", "status": "started"}), flush=True)
    while True:
        scan()
        time.sleep(12)
