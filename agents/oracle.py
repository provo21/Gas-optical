import json
import os
import subprocess
import time
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

LOG_DIR = os.environ.get("ORACLE_LOG_DIR", "/tmp/oracle_logs")
SUMMARY_FILE = os.path.join(LOG_DIR, "daily_summary.json")
INTERVAL = int(os.environ.get("ORACLE_INTERVAL", "3600"))
PUBLIC_URL = os.environ.get(
    "PUBLIC_URL", "https://gas-optical-production-30aa.up.railway.app"
)
LAST_PAY_FILE = os.path.join(LOG_DIR, "last_self_pay.json")
PAY_COOLDOWN = 6 * 3600

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

PAID = ["/gas", "/eth-price", "/block-number", "/gas-predict", "/whale-watch"]
FREE = ["/oracle", "/.well-known/x402"]


def ensure_log_dir():
    os.makedirs(LOG_DIR, exist_ok=True)


def write_agent_log(agent, data):
    path = os.path.join(LOG_DIR, f"{agent}.json")
    try:
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Oracle: failed to write log for {agent}: {e}", flush=True)


def read_agent_logs(agent):
    path = os.path.join(LOG_DIR, f"{agent}.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def http_get(path, timeout=15):
    url = PUBLIC_URL.rstrip("/") + path
    req = Request(url, headers={"User-Agent": "GasOptical-Oracle/1.0"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            body = resp.read()[:4000].decode("utf-8", errors="replace")
            return {"url": url, "status": resp.status, "ok": True, "body": body}
    except HTTPError as e:
        body = e.read()[:4000].decode("utf-8", errors="replace") if e.fp else ""
        return {"url": url, "status": e.code, "ok": False, "body": body}
    except (URLError, Exception) as e:
        return {"url": url, "status": None, "ok": False, "error": str(e)}


def check_endpoints():
    results = {}
    for path in FREE:
        hit = http_get(path)
        results[path] = {"expect": "200", "got": hit.get("status"), "ok": hit.get("status") == 200}
    for path in PAID:
        hit = http_get(path)
        # Healthy paywall is 402. 200 means we accidentally made it free.
        results[path] = {
            "expect": "402",
            "got": hit.get("status"),
            "ok": hit.get("status") == 402,
        }
    return results


def run_validate():
    script = os.path.join(os.path.dirname(__file__), "..", "validate.py")
    script = os.path.abspath(script)
    if not os.path.exists(script):
        return {"ran": False, "reason": "validate.py missing"}
    if not (os.environ.get("CDP_API_KEY_ID") or os.environ.get("CDP_API_KEY")):
        return {"ran": False, "reason": "no CDP key in env"}
    try:
        out = subprocess.run(
            ["python", script], capture_output=True, text=True, timeout=45
        )
        return {
            "ran": True,
            "returncode": out.returncode,
            "stdout": (out.stdout or "")[-500:],
            "stderr": (out.stderr or "")[-500:],
        }
    except Exception as e:
        return {"ran": False, "error": str(e)}


def maybe_self_pay():
    if not os.environ.get("PRIVATE_KEY"):
        return {"ran": False, "reason": "PRIVATE_KEY not set — cannot seed first settle"}
    now = int(time.time())
    last = 0
    if os.path.exists(LAST_PAY_FILE):
        try:
            with open(LAST_PAY_FILE) as f:
                last = int(json.load(f).get("ts") or 0)
        except Exception:
            last = 0
    if now - last < PAY_COOLDOWN:
        return {"ran": False, "reason": "cooldown", "seconds_left": PAY_COOLDOWN - (now - last)}
    buyer = os.path.join(os.path.dirname(__file__), "..", "buyer.py")
    buyer = os.path.abspath(buyer)
    if not os.path.exists(buyer):
        return {"ran": False, "reason": "buyer.py missing"}
    try:
        out = subprocess.run(
            ["python", buyer], capture_output=True, text=True, timeout=90
        )
        record = {"ts": now, "returncode": out.returncode}
        with open(LAST_PAY_FILE, "w") as f:
            json.dump(record, f)
        return {
            "ran": True,
            "returncode": out.returncode,
            "stdout": (out.stdout or "")[-500:],
            "stderr": (out.stderr or "")[-500:],
        }
    except Exception as e:
        return {"ran": False, "error": str(e)}


def synthesize(extra):
    now = datetime.now(timezone.utc).isoformat()
    findings = {}
    for agent in AGENTS:
        data = read_agent_logs(agent)
        findings[agent] = data if data is not None else {"status": "no_data"}

    alerts = []
    for agent, data in findings.items():
        if isinstance(data, dict):
            if data.get("status") == "down" or data.get("healthy") is False:
                alerts.append(f"{agent} reports unhealthy")

    health = extra.get("endpoints") or {}
    for path, info in health.items():
        if not info.get("ok"):
            alerts.append(f"endpoint {path} expected {info.get('expect')} got {info.get('got')}")

    summary = {
        "generated_at": now,
        "mandate": "autonomous_traction",
        "agents_checked": len(AGENTS),
        "alerts": alerts,
        "actions": extra,
        "findings": findings,
    }
    with open(SUMMARY_FILE, "w") as f:
        json.dump(summary, f, indent=2)
    print(json.dumps(summary, indent=2), flush=True)
    return summary


def nudge_agents():
    restarted = []
    for agent in AGENTS:
        data = read_agent_logs(agent)
        idle = data is None or (
            isinstance(data, dict) and data.get("status") in (None, "no_data", "idle", "error")
        )
        if idle:
            script = f"agents/{agent}.py"
            if os.path.exists(script):
                try:
                    subprocess.Popen(
                        ["python", script],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        start_new_session=True,
                    )
                    restarted.append(agent)
                    write_agent_log(agent, {"status": "nudged", "ts": int(time.time())})
                except Exception as e:
                    print(f"Oracle: failed to nudge {agent}: {e}", flush=True)
    return restarted


def tick():
    endpoints = check_endpoints()
    validate = run_validate()
    pay = maybe_self_pay()
    restarted = nudge_agents()
    return {
        "endpoints": endpoints,
        "validate": validate,
        "self_pay": pay,
        "nudged": restarted,
    }


def main():
    ensure_log_dir()
    print("Oracle autonomous mandate active. Interval=%ss" % INTERVAL, flush=True)
    print("Oracle will act without asking within agents/ORACLE_MANDATE.md", flush=True)
    while True:
        try:
            extra = tick()
            synthesize(extra)
        except Exception as e:
            print(f"Oracle error: {e}", flush=True)
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
