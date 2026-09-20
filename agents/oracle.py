import time
import json
import os
from datetime import datetime, timezone

LOG_DIR = os.environ.get("ORACLE_LOG_DIR", "/tmp/oracle_logs")
SUMMARY_FILE = os.path.join(LOG_DIR, "daily_summary.json")
INTERVAL = int(os.environ.get("ORACLE_INTERVAL", "3600"))  # hourly by default

AGENTS = [
    "bazaar_crawler",
    "directory_submitter",
    "manifest_broadcaster",
    "competitor_monitor",
    "price_optimizer",
    "health_reporter",
    "web_gas_crawler",
    "gas_drop_speculator",
    "cheapest_finder",
    "trend_watcher",
    "competitor_pricer",
    "signal_broadcaster",
    "payer_tracker",
    "churn_detector",
    "reengagement",
    "whale_alert",
]


def ensure_log_dir():
    os.makedirs(LOG_DIR, exist_ok=True)


def read_agent_logs(agent):
    """Best-effort read of an agent's recent output.

    In this environment most agents just print to stdout, which Railway
    captures. We look for a small JSON sidecar file each agent may write.
    """
    path = os.path.join(LOG_DIR, f"{agent}.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def synthesize():
    now = datetime.now(timezone.utc).isoformat()
    findings = {}
    for agent in AGENTS:
        data = read_agent_logs(agent)
        if data is None:
            findings[agent] = {"status": "no_data"}
        else:
            findings[agent] = data

    # Simple pattern detection
    alerts = []
    for agent, data in findings.items():
        if isinstance(data, dict):
            if data.get("status") == "down" or data.get("healthy") is False:
                alerts.append(f"{agent} reports unhealthy")
            if data.get("churn_risk") is True:
                alerts.append(f"{agent} flagged churn risk")
            if data.get("whale_alert"):
                alerts.append(f"whale activity: {data.get('whale_alert')}")

    summary = {
        "generated_at": now,
        "agents_checked": len(AGENTS),
        "alerts": alerts,
        "findings": findings,
    }

    with open(SUMMARY_FILE, "w") as f:
        json.dump(summary, f, indent=2)

    print(json.dumps(summary, indent=2), flush=True)
    return summary


def main():
    ensure_log_dir()
    print(f"Oracle synthesis agent starting. Interval={INTERVAL}s", flush=True)
    while True:
        try:
            synthesize()
        except Exception as e:
            print(f"Oracle error: {e}", flush=True)
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
