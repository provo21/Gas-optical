# server.py
import os
import time

import httpx
from cdp.x402 import create_facilitator_config
from fastapi import FastAPI
from x402.http import HTTPFacilitatorClient, PaymentOption
from x402.http.middleware.fastapi import PaymentMiddlewareASGI
from x402.http.types import RouteConfig
from x402.mechanisms.evm.exact import ExactEvmServerScheme
from x402.server import x402ResourceServer

NETWORK = "eip155:8453"  # Base mainnet
PAY_TO = os.environ["X402_PAY_TO"]

# create_facilitator_config() reads your CDP API key and authenticates verify
# and settle against the CDP Facilitator. It does not create a receiving wallet.
server = x402ResourceServer(HTTPFacilitatorClient(create_facilitator_config()))
server.register(NETWORK, ExactEvmServerScheme())

routes = {
    "GET /gas": RouteConfig(
        accepts=[
            PaymentOption(
                scheme="exact", pay_to=PAY_TO, price="$0.001", network=NETWORK
            )
        ],
        mime_type="application/json",
        description="Live Base gas price in gwei",
    ),
}

app = FastAPI()
app.add_middleware(PaymentMiddlewareASGI, routes=routes, server=server)

BASE_RPC = "https://mainnet.base.org"


async def fetch_gas_gwei() -> float:
    payload = {"jsonrpc": "2.0", "method": "eth_gasPrice", "params": [], "id": 1}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(BASE_RPC, json=payload)
        resp.raise_for_status()
        wei = int(resp.json()["result"], 16)
    return wei / 1e9


@app.get("/gas")
async def gas():
    try:
        gwei = await fetch_gas_gwei()
    except Exception:
        gwei = None
    return {"gas_gwei": gwei, "timestamp": int(time.time())}


if __name__ == "__main__":
    import uvicorn

    print(f"Receiving payments at {PAY_TO}")
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
