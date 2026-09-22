import os
import time
import json
import httpx

RPC = os.environ.get("BASE_RPC_URL", "https://mainnet.base.org")
THRESHOLD_WEI = int(os.environ.get("WHALE_THRESHOLD_WEI", str(50 * 10**18)))  # 50 ETH default
SEEN = set()
LOG_DIR = os.environ.get("ORACLE_LOG_DIR", "/tmp/oracle_logs")


def get_latest_block():
    payload = {"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1}
    r = httpx.post(RPC, json=payload, timeout=10)
    return int(r.json()["result"], 16)


def get_block(n):
    payload = {"jsonrpc": "2.0", "method": "eth_getBlockByNumber", "params": [hex(n), True], "id": 1}
    r = httpx.post(RPC, json=payload, timeout=15)
    return r.json().get("result")


def write_log(data):
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(os.path.join(LOG_DIR, "whale_alert.json"), "w") as f:
            json.dump(data, f)
    except Exception:
        pass


def scan():
    try:
        latest = get_latest_block()
        block = get_block(latest)
        if not block:
            return
        alerts = []
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
                alerts.append(alert)
                print(json.dumps(alert), flush=True)
        write_log({"status": "ok", "block": latest, "alerts": alerts, "ts": int(time.time())})
    except Exception as e:
        err = {"status": "error", "error": str(e)[:200], "ts": int(time.time())}
        write_log(err)
        print(json.dumps(err), flush=True)


if __name__ == "__main__":
    print(json.dumps({"agent": "whale_alert", "status": "started", "threshold_eth": THRESHOLD_WEI / 10**18}), flush=True)
    while True:
        scan()
        time.sleep(12)
