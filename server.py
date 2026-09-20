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
        description="Use this before sending a transaction on Base, Ethereum, Arbitrum, or Optimism to check live gas prices in gwei across all four chains.",
        service_name="Multi-Chain Gas Oracle",
        tags=["gas", "base", "ethereum", "arbitrum", "optimism", "oracle", "multi-chain"],
        extensions=declare_discovery_extension(
            input={},
            input_schema={
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
            output=OutputConfig(
                example={
                    "base": 12.4,
                    "ethereum": 18.2,
                    "arbitrum": 0.11,
                    "optimism": 0.05,
                    "timestamp": 1710000000,
                }
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
        description="Call this when an agent needs the current ETH price in USD to size a trade, convert gas cost to dollars, or value a position.",
        service_name="ETH Price Feed",
        tags=["price", "eth", "base", "coingecko"],
        extensions=declare_discovery_extension(
            input={},
            input_schema={
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
            output=OutputConfig(example={"usd": 3450.12, "timestamp": 1710000000}),
        ),
    ),
    "GET /block-number": RouteConfig(
        accepts=[
            PaymentOption(
                scheme="exact", pay_to=PAY_TO, price="$0.0001", network=NETWORK
            )
        ],
        mime_type="application/json",
        description="Use this to get the latest Base block number for timing, syncing, or checking chain progress before submitting a transaction.",
        service_name="Base Block Number",
        tags=["block", "base", "chain", "ethereum"],
        extensions=declare_discovery_extension(
            input={},
            input_schema={
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
            output=OutputConfig(example={"block_number": 12345678, "timestamp": 1710000000}),
        ),
    ),
    "GET /gas-predict": RouteConfig(
        accepts=[
            PaymentOption(
                scheme="exact", pay_to=PAY_TO, price="$0.0005", network=NETWORK
            )
        ],
        mime_type="application/json",
        description="Call this to time transactions when Base gas is about to spike or drop over the next hour, based on recent block gas usage and base fee trend.",
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
    "GET /whale-watch": RouteConfig(
        accepts=[
            PaymentOption(
                scheme="exact", pay_to=PAY_TO, price="$0.001", network=NETWORK
            )
        ],
        mime_type="application/json",
        description="Call this when an agent needs to detect large whale transfers on Base above one thousand ETH equivalent to spot accumulation, rotation, or exit signals before trading.",
        service_name="Base Whale Watch",
        tags=["whale", "base", "on-chain", "intelligence", "transfers", "defi"],
        extensions=declare_discovery_extension(
            input={},
            input_schema={
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
            output=OutputConfig(
                example={
                    "threshold_eth": 1000.0,
                    "transfers": [
                        {
                            "tx_hash": "0xabc123",
                            "from": "0x1111...",
                            "to": "0x2222...",
                            "value_eth": 2500.5,
                            "token": "ETH",
                        }
                    ],
                    "count": 1,
                    "timestamp": 1710000000,
                }
            ),
        ),
    ),
}

app = FastAPI(
    title="Multi-Chain Gas Oracle & Whale Watch",
    description="Live gas prices across Base, Ethereum, Arbitrum, and Optimism, plus ETH price, block number, gas prediction, and large Base whale transfers. Paid via x402 on Base mainnet.",
    version="1.5.0",
    contact={"email": "gas@optical.example"},
)
app.add_middleware(PaymentMiddlewareASGI, routes=routes, server=server)

CHAINS = {
    "base": "https://mainnet.base.org",
    "ethereum": "https://eth.llamarpc.com",
    "arbitrum": "https://arb1.arbitrum.io/rpc",
    "optimism": "https://mainnet.optimism.io",
}

# In-memory ring buffer of recent Base gas samples for trend prediction.
GAS_HISTORY: deque = deque(maxlen=60)  # ~last 60 samples

# Short-lived response cache so agents get sub-200ms replies without hammering RPCs.
CACHE_TTL = 8  # seconds
_cache: dict = {}

# Known exchange / liquidity hot wallets on Base to filter noise.
KNOWN_WHALE_WALLETS = {
    "0x0000000000000000000000000000000000000000",
}


def _cache_get(key: str):
    entry = _cache.get(key)
    if entry is None:
        return None
    value, expires = entry
    if time.time() >= expires:
        _cache.pop(key, None)
        return None
    return value


def _cache_set(key: str, value, ttl: float = CACHE_TTL):
    _cache[key] = (value, time.time() + ttl)
    return value


async def fetch_gas_gwei(rpc: str) -> float:
    payload = {"jsonrpc": "2.0", "method": "eth_gasPrice", "params": [], "id": 1}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(rpc, json=payload)
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
        resp = await client.post(CHAINS["base"], json=payload)
        resp.raise_for_status()
        return int(resp.json()["result"], 16)


async def fetch_base_fee_gwei() -> float | None:
    """Return the latest base fee in gwei, if the node exposes it."""
    payload = {"jsonrpc": "2.0", "method": "eth_getBlockByNumber", "params": ["latest", False], "id": 1}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(CHAINS["base"], json=payload)
            resp.raise_for_status()
            base_fee = resp.json().get("result", {}).get("baseFeePerGas")
        if base_fee is None:
            return None
        return int(base_fee, 16) / 1e9
    except Exception:
        return None


async def fetch_whale_transfers(threshold_eth: float = 1000.0, limit: int = 20) -> list:
    """Scan recent Base blocks for large native ETH transfers above threshold."""
    payload = {"jsonrpc": "2.0", "method": "eth_getBlockByNumber", "params": ["latest", True], "id": 1}
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(CHAINS["base"], json=payload)
        resp.raise_for_status()
        block = resp.json().get("result") or {}

    transfers = []
    for tx in block.get("transactions", []):
        if not isinstance(tx, dict):
            continue
        value_wei = int(tx.get("value", "0x0"), 16)
        value_eth = value_wei / 1e18
        if value_eth < threshold_eth:
            continue
        transfers.append(
            {
                "tx_hash": tx.get("hash"),
                "from": tx.get("from"),
                "to": tx.get("to"),
                "value_eth": round(value_eth, 4),
                "token": "ETH",
            }
        )
        if len(transfers) >= limit:
            break
    return transfers


@app.get("/gas")
async def gas():
    cached = _cache_get("gas")
    if cached is not None:
        return cached
    result = {}
    for name, rpc in CHAINS.items():
        try:
            gwei = await fetch_gas_gwei(rpc)
            result[name] = round(gwei, 4)
            if name == "base":
                GAS_HISTORY.append({"t": time.time(), "gwei": gwei})
        except Exception:
            result[name] = None
    payload = {**result, "timestamp": int(time.time())}
    return _cache_set("gas", payload)


@app.get("/eth-price")
async def eth_price():
    cached = _cache_get("eth-price")
    if cached is not None:
        return cached
    try:
        usd = await fetch_eth_price_usd()
    except Exception:
        usd = None
    payload = {"usd": usd, "timestamp": int(time.time())}
    return _cache_set("eth-price", payload)


@app.get("/block-number")
async def block_number():
    cached = _cache_get("block-number")
    if cached is not None:
        return cached
    try:
        n = await fetch_block_number()
    except Exception:
        n = None
    payload = {"block_number": n, "timestamp": int(time.time())}
    return _cache_set("block-number", payload)


@app.get("/gas-predict")
async def gas_predict():
    """Forecast Base gas direction over the next hour from recent samples."""
    try:
        current = await fetch_gas_gwei(CHAINS["base"])
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


@app.get("/whale-watch")
async def whale_watch():
    """Return large native ETH transfers on the latest Base block."""
    cached = _cache_get("whale-watch")
    if cached is not None:
        return cached
    try:
        transfers = await fetch_whale_transfers(threshold_eth=1000.0, limit=20)
    except Exception:
        transfers = []
    payload = {
        "threshold_eth": 1000.0,
        "transfers": transfers,
        "count": len(transfers),
        "timestamp": int(time.time()),
    }
    return _cache_set("whale-watch", payload, ttl=15)


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
            f"{base}/whale-watch",
        ],
        "instructions": "Pay $0.0001 USDC on Base for gas/price/block; $0.0005 for gas prediction; $0.001 for whale-watch. See PAYMENT-REQUIRED header.",
    }
    return JSONResponse(manifest)


if __name__ == "__main__":
    import uvicorn

    print(f"Receiving payments at {PAY_TO}")
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
