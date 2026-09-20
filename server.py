# server.py
import os
import time

import httpx
from cdp.x402 import create_facilitator_config
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from x402.extensions.bazaar import (
    OutputConfig,
    bazaar_resource_server_extension,
    declare_discovery_extension,
)
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
# Enriches each route's Bazaar declaration with its HTTP method and path params.
server.register_extension(bazaar_resource_server_extension)

routes = {
    "GET /gas": RouteConfig(
        accepts=[
            PaymentOption(
                scheme="exact", pay_to=PAY_TO, price="$0.0001", network=NETWORK
            )
        ],
        mime_type="application/json",
        description="Live Base gas price in gwei, updated from public RPC. Cheap on-chain gas oracle for agents.",
        service_name="Base Gas Oracle",
        tags=["gas", "base", "oracle", "ethereum"],
        extensions=declare_discovery_extension(
            service_name="Base Gas Oracle",
            tags=["gas", "base", "oracle", "ethereum"],
            input={},
            input_schema={
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
            output=OutputConfig(
                example={"gas_gwei": 12.4, "timestamp": 1710000000}
            ),
        ),
    ),
    "GET /eth-price": RouteConfig(
        accepts=[
            PaymentOption(
                scheme="exact", pay_to=PAY_TO, price="$0.0001", network=NETWORK
            )
        ],
        mime_type="application/json",
        description="Live ETH price in USD from CoinGecko public API. Cheap price feed for agents.",
        service_name="ETH Price Feed",
        tags=["price", "eth", "base", "coingecko"],
        extensions=declare_discovery_extension(
            service_name="ETH Price Feed",
            tags=["price", "eth", "base", "coingecko"],
            input={},
            input_schema={
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
            output=OutputConfig(
                example={"usd": 3450.12, "timestamp": 1710000000}
            ),
        ),
    ),
    "GET /block-number": RouteConfig(
        accepts=[
            PaymentOption(
                scheme="exact", pay_to=PAY_TO, price="$0.0001", network=NETWORK
            )
        ],
        mime_type="application/json",
        description="Latest Base block number from public RPC. Cheap chain-state feed for agents.",
        service_name="Base Block Number",
        tags=["block", "base", "chain", "ethereum"],
        extensions=declare_discovery_extension(
            service_name="Base Block Number",
            tags=["block", "base", "chain", "ethereum"],
            input={},
            input_schema={
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
            output=OutputConfig(
                example={"block_number": 12345678, "timestamp": 1710000000}
            ),
        ),
    ),
}

app = FastAPI(
    title="Base Gas Oracle",
    description="Live Base gas price, ETH price, and block number. Paid via x402 on Base mainnet.",
    version="1.1.0",
    contact={"email": "gas@optical.example"},
)
app.add_middleware(PaymentMiddlewareASGI, routes=routes, server=server)

BASE_RPC = "https://mainnet.base.org"


async def fetch_gas_gwei() -> float:
    payload = {"jsonrpc": "2.0", "method": "eth_gasPrice", "params": [], "id": 1}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(BASE_RPC, json=payload)
        resp.raise_for_status()
        wei = int(resp.json()["result"], 16)
    return wei / 1e9


async def fetch_eth_price_usd() -> float:
    url = "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return float(resp.json()["ethereum"]["usd"])


async def fetch_block_number() -> int:
    payload = {"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(BASE_RPC, json=payload)
        resp.raise_for_status()
        return int(resp.json()["result"], 16)


@app.get("/gas")
async def gas():
    try:
        gwei = await fetch_gas_gwei()
    except Exception:
        gwei = None
    return {"gas_gwei": gwei, "timestamp": int(time.time())}


@app.get("/eth-price")
async def eth_price():
    try:
        usd = await fetch_eth_price_usd()
    except Exception:
        usd = None
    return {"usd": usd, "timestamp": int(time.time())}


@app.get("/block-number")
async def block_number():
    try:
        n = await fetch_block_number()
    except Exception:
        n = None
    return {"block_number": n, "timestamp": int(time.time())}


@app.get("/.well-known/x402")
async def well_known_x402():
    base = os.environ.get("PUBLIC_URL", "https://gas-optical-production-30aa.up.railway.app")
    manifest = {
        "version": 1,
        "resources": [f"{base}/gas", f"{base}/eth-price", f"{base}/block-number"],
        "instructions": "Pay $0.0001 USDC on Base to access live gas price, ETH price, or block number. See PAYMENT-REQUIRED header.",
    }
    return JSONResponse(manifest)


@app.get("/favicon.ico")
async def favicon():
    return FileResponse("favicon.ico")


if __name__ == "__main__":
    import uvicorn

    print(f"Receiving payments at {PAY_TO}")
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
