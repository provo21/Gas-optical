import time
import json
import os
import random

API_URL = os.environ.get("API_URL", "https://gas-optical-production-30aa.up.railway.app")
LOG = "/tmp/payer_tracker.jsonl"

def log(event):
    with open(LOG, "a") as f:
        f.write(json.dumps({"ts": time.time(), **event}) + "\n")
    print(json.dumps(event), flush=True)

def simulate_payers():
    # In production this would read real /stats or payment logs.
    # Here we simulate a small set of recurring payers.
    payers = ["agent_alpha", "agent_beta", "agent_gamma", "agent_delta"]
    active = random.sample(payers, k=random.randint(2, 4))
    return {"active_payers": active, "count": len(active)}

def main():
    while True:
        data = simulate_payers()
        log({"agent": "payer_tracker", "event": "snapshot", **data})
        time.sleep(3600)

if __name__ == "__main__":
    main()
