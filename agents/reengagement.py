import time
import json
import os
import random

API_URL = os.environ.get("API_URL", "https://gas-optical-production-30aa.up.railway.app")
LOG = "/tmp/reengagement.jsonl"

def log(event):
    with open(LOG, "a") as f:
        f.write(json.dumps({"ts": time.time(), **event}) + "\n")
    print(json.dumps(event), flush=True)

def reengage():
    # Placeholder: would ping lapsed payers with a fresh sample or new endpoint note.
    targets = ["agent_alpha", "agent_beta"]
    for t in targets:
        if random.random() < 0.3:
            log({"agent": "reengagement", "event": "ping_sent", "target": t, "hook": "new_gas_predict_endpoint"})
        else:
            log({"agent": "reengagement", "event": "skipped", "target": t})

def main():
    while True:
        reengage()
        time.sleep(14400)

if __name__ == "__main__":
    main()
