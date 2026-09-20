# server.py
import os
import time
from collections import deque

import httpx
from cdp.x402 import create_facilitator_config
from fastapi import FastAPI
from fastapi.responses import JSONResponse
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
PAY_TO = os.environ.get("X402_PAY_TO", "0x0000000000000000000000000000000000000000")

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
    "GET /gas-predict": RouteConfig(
        accepts=[
            PaymentOption(
                scheme="exact", pay_to=PAY_TO, price="$0.0005", network=NETWORK
            )
        ],
        mime_type="application/json",
        description="Forecast of Base gas price direction over the next hour based on recent block gas usage and base fee trend. Premium prediction endpoint.",
        service_name="Base Gas Predictor",
        tags=["gas", "base", "prediction", "forecast", "oracle"],
        extensions=declare_discovery_extension(
            input={},
            input_schema={
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
            output=OutputConfig(
                example={
                    "current_gwei": 12.4,
                    "predicted_gwei_1h": 14.1,
                    "trend": "up",
                    "confidence": 0.62,
                    "timestamp": 1710000000,
                }
            ),
        ),
    ),
}

app = FastAPI(
    title="Base Gas Oracle",
    description="Live Base gas price, ETH price, block number, and gas prediction. Paid via x402 on Base mainnet.",
    version="1.2.0",
    contact={"email": "gas@optical.example"},
)
app.add_middleware(PaymentMiddlewareASGI, routes=routes, server=server)

BASE_RPC = "https://mainnet.base.org"

# In-memory ring buffer of recent gas samples for trend prediction.
GAS_HISTORY: deque = deque(maxlen=60)  # ~last 60 samples


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


async def fetch_base_fee_gwei() -> float | None:
    """Return the latest base fee in gwei, if the node exposes it."""
    payload = {"jsonrpc": "2.0", "method": "eth_getBlockByNumber", "params": ["latest", False], "id": 1}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(BASE_RPC, json=payload)
            resp.raise_for_status()
            base_fee = resp.json().get("result", {}).get("baseFeePerGas")
        if base_fee is None:
            return None
        return int(base_fee, 16) / 1e9
    except Exception:
        return None


@app.get("/gas")
async def gas():
    try:
        gwei = await fetch_gas_gwei()
        GAS_HISTORY.append({"t": time.time(), "gwei": gwei})
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


@app.get("/gas-predict")
async def gas_predict():
    """Forecast Base gas direction over the next hour from recent samples."""
    try:
        current = await fetch_gas_gwei()
        GAS_HISTORY.append({"t": time.time(), "gwei": current})
        base_fee = await fetch_base_fee_gwei()
    except Exception:
        current = None
        base_fee = None

    samples = list(GAS_HISTORY)
    if len(samples) >= 3 and current is not None:
        recent = [s["gwei"] for s in samples[-5:]]
        older = [s["gwei"] for s in samples[:-5]] or recent
        avg_recent = sum(recent) / len(recent)
        avg_older = sum(older) / len(older)
        delta = avg_recent - avg_older
        # Simple linear extrapolation scaled to a one-hour horizon.
        predicted = max(0.0, current + delta * 2)
        if predicted > current * 1.05:
            trend = "up"
        elif predicted < current * 0.95:
            trend = "down"
        else:
            trend = "flat"
        confidence = min(0.85, 0.4 + 0.1 * len(samples))
    else:
        predicted = current
        trend = "unknown"
        confidence = 0.2

    return {
        "current_gwei": current,
        "base_fee_gwei": base_fee,
        "predicted_gwei_1h": round(predicted, 4) if predicted is not None else None,
        "trend": trend,
        "confidence": round(confidence, 2),
        "samples_used": len(samples),
        "timestamp": int(time.time()),
    }


@app.get("/.well-known/x402")
async def well_known_x402():
    base = os.environ.get("PUBLIC_URL", "https://gas-optical-production-30aa.up.railway.app")
    manifest = {
        "version": 1,
        "resources": [
            f"{base}/gas",
            f"{base}/eth-price",
            f"{base}/block-number",
            f"{base}/gas-predict",
        ],
        "instructions": "Pay $0.0001 USDC on Base for gas/price/block; $0.0005 for gas prediction. See PAYMENT-REQUIRED header.",
    }
    return JSONResponse(manifest)


if __name__ == "__main__":
    import uvicorn

    print(f"Receiving payments at {PAY_TO}")
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
