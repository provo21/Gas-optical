import os
import time
import json
import httpx

BASE_URL = os.environ.get("PUBLIC_URL", "https://gas-optical-production-30aa.up.railway.app")
MANIFEST = f"{BASE_URL}/.well-known/x402"

BROADCAST_TARGETS = [
    "https://api.cdp.coinbase.com/x402/bazaar/register",  # placeholder
]


def log(msg):
    print(json.dumps({"ts": int(time.time()), "agent": "manifest_broadcaster", "msg": msg}), flush=True)


async def broadcast_once():
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            r = await client.get(MANIFEST)
            if r.status_code == 200:
                manifest = r.json()
                log({"manifest_ok": True, "resources": manifest.get("resources", [])})
                for t in BROADCAST_TARGETS:
                    try:
                        rr = await client.post(t, json=manifest)
                        log({"target": t, "status": rr.status_code})
                    except Exception as e:
                        log({"target": t, "error": str(e)})
            else:
                log({"manifest_status": r.status_code})
        except Exception as e:
            log({"error": str(e)})


async def main():
    log("starting manifest broadcaster")
    while True:
        try:
            await broadcast_once()
        except Exception as e:
            log({"error": str(e)})
        time.sleep(7200)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
