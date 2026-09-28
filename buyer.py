import os
from eth_account import Account
from x402 import x402ClientSync
from x402.http.clients import x402_requests
from x402.mechanisms.evm import EthAccountSigner
from x402.mechanisms.evm.exact.register import register_exact_evm_client

key = os.environ["PRIVATE_KEY"]
account = Account.from_key(key)
print(f"buyer using {account.address}", flush=True)

client = x402ClientSync().set_spend_controls({"max_amount_per_payment": "$0.01"})
register_exact_evm_client(client, EthAccountSigner(account))

url = os.environ.get(
    "BUY_URL", "https://gas-optical-production-30aa.up.railway.app/gas"
)
with x402_requests(client) as session:
    r = session.get(url)
print(r.status_code, flush=True)
print(r.text[:500], flush=True)
