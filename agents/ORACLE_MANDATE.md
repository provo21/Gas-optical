# Oracle mandate

Authorized by the operator. Oracle may act without asking on the following.

## Goal
Get paying agent traffic to the x402 API. Do not wait for a chat message.

## Allowed without asking
- Health-check `/oracle`, `/.well-known/x402`, and paid routes (expect 402 on paid routes).
- Re-hit CDP validate if `CDP_API_KEY_ID` / `CDP_API_KEY_SECRET` are set.
- Re-hit x402scan-style discovery URLs already in the repo.
- Restart idle local agent scripts.
- Run `buyer.py` / a $0.0001 self-pay **only if** `PRIVATE_KEY` is set. Cap: one paid call per 6 hours.
- Write status to `/tmp/oracle_logs/daily_summary.json` and stdout.

## Not allowed without asking
- Change prices.
- Make paid routes free.
- Spend more than $0.001 USDC per day.
- Post from the operator's social accounts unless those tokens exist in env.
- Delete env vars, wallets, or the API.

## Report to the operator only when
- The API is down.
- A paid settle succeeded.
- Daily spend cap would be exceeded.
- A required secret is missing for a high-value action (e.g. no PRIVATE_KEY for first settle).
