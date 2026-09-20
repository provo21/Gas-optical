# server.py
import os

from cdp.x402 import create_facilitator_config
from fastapi import FastAPI
from x402.http import HTTPFacilitatorClient, PaymentOption
from x402.http.middleware.fastapi import PaymentMiddlewareASGI
from x402.http.types import RouteConfig
from x402.mechanisms.evm.exact import ExactEvmServerScheme
from x402.server import x402ResourceServer

NETWORK = "eip155:8453"  # Base mainnet
PAY_TO = os.environ # create_facilitator_config() reads your CDP API key and authenticates verify
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

@app.get("/gas")
async def gas():
    return {"gas_gwei": 12.4, "timestamp": 0}

if __name__ == "__main__":
    import uvicorn
    print(f"Receiving payments at {PAY_TO}")
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
