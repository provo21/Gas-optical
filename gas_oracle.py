# gas_oracle.py
import os
import time
from cdp.x402 import create_facilitator_config
from fastapi import FastAPI
from web3 import Web3
from x402.http import HTTPFacilitatorClient, PaymentOption
from x402.http.middleware.fastapi import PaymentMiddlewareASGI
from x402.http.types import RouteConfig
from x402.mechanisms.evm.exact import ExactEvmServerScheme
from x402.server import x402ResourceServer

NETWORK = "eip155:8453"  # Base mainnet
PAY_TO = os.environ RPC = os.environ.get("RPC_URL", "https://mainnet.base.org")

w3 = Web3(Web3.HTTPProvider(RPC))

server = x402ResourceServer(HTTPFacilitatorClient(create_facilitator_config()))
server.register(NETWORK, ExactEvmServerScheme())

routes = {
    "GET /gas": RouteConfig(
        accepts=[
            PaymentOption(
                scheme="exact",
                price="$0.001",
                network=NETWORK,
                pay_to=PAY_TO,
            )
        ],
        mime_type="application/json",
        description="Live Base gas price in gwei",
    ),
}

app = FastAPI()
app.add_middleware(PaymentMiddlewareASGI, routes=routes, server=server)

@app.get("/gas")
async def gas():
    wei = w3.eth.gas_price
    return {"gas_gwei": wei / 1e9, "timestamp": int(time.time())}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8402)
