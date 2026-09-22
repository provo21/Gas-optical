import os
import time
import json
import httpx

BASE_URL = os.environ.get("PUBLIC_URL", "https://gas-optical-production-30aa.up.railway.app")
ENDPOINTS = ["/gas", "/eth-price", "/block-number", "/gas-predict", "/whale-watch", "/.well-known/x402"]
LOG_DIR = os.environ.get("ORACLE_LOG_DIR", "/tmp/oracle_logs")


def log(msg):
    print(json.dumps({"ts": int(time.time()), "agent": "health_reporter", "msg": msg}), flush=True)
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(os.path.join(LOG_DIR, "health_reporter.json"), "w") as f:
            json.dump({"ts": int(time.time()), "status": "ok", "data": msg}, f)
    except Exception:
        pass


async def check_once():
    status = {}
    async with httpx.AsyncClient(timeout=10.0) as client:
        for ep in ENDPOINTS:
            try:
                r = await client.get(f"{BASE_URL}{ep}")
                status[ep] = r.status_code
            except Exception as e:
                status[ep] = f"err:{e}"
    log({"health": status})


async def main():
    log("starting health reporter")
    while True:
        try:
            await check_once()
        except Exception as e:
            log({"error": str(e)})
        time.sleep(300)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
