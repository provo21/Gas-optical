import time
import json
import os

API_URL = os.environ.get("API_URL", "https://gas-optical-production-30aa.up.railway.app")
LOG = "/tmp/churn_detector.jsonl"

def log(event):
    with open(LOG, "a") as f:
        f.write(json.dumps({"ts": time.time(), **event}) + "\n")
    print(json.dumps(event), flush=True)

def detect_churn():
    # Placeholder: compare current active payers vs previous snapshot.
    # Real version would diff /stats over a rolling window.
    churned = []
    if churned:
        log({"agent": "churn_detector", "event": "churn_detected", "lost": churned})
    else:
        log({"agent": "churn_detector", "event": "no_churn", "status": "healthy"})

def main():
    while True:
        detect_churn()
        time.sleep(7200)

if __name__ == "__main__":
    main()
